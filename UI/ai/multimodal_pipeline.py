# Import required libraries
from __future__ import annotations
import gc, math, re, subprocess, tempfile, os
from pathlib import Path
from statistics import mean, median
import cv2
import imageio_ffmpeg
import librosa
import mediapipe as mp
import torch
from nltk.tokenize import wordpunct_tokenize
from PIL import Image
from PySide6.QtCore import QThread, Signal
from transformers import AutoModelForAudioClassification, AutoProcessor, pipeline as hf_pipeline
from UI.ui.translations import translate_text
import sys as _sys
import torch.nn.functional as _F
from torchvision import transforms as _transforms
import urllib.request as _urllib

# configured DDAMFN paths or the project defaults
_DDAMFN_DIR = os.environ.get("SOLACE_DDAMFN_DIR", str(Path(__file__).resolve().parents[2] / "models" / "DDAMFN++"))
_DDAMFN_CKPT = os.environ.get("SOLACE_DDAMFN_CHECKPOINT", str(Path(_DDAMFN_DIR) / "checkpoints_ver2.0" / "affecnet7_epoch19_acc0.671.pth"))

# source address and required network files together
_DDAMFN_BASE = "https://raw.githubusercontent.com/SainingZhang/DDAMFN/main"
_DDAMFN_CODE_FILES = ["networks/DDAM.py", "networks/MixedFeatureNet.py", "networks/__init__.py"]

# both the repository root and the DDAMFN++ folder
_DDAMFN_PREFIXES = ["", "DDAMFN%2B%2B/"]


# Download DDAMFN file when it is missing locally
def _ddamfn_fetch(remote_relpath, local_path, optional=False):
    local_path = Path(local_path)
    # Reuse files that are already available
    if local_path.exists():
        return True
    local_path.parent.mkdir(parents=True, exist_ok=True)
    # available source folders until a download succeeds
    for prefix in _DDAMFN_PREFIXES:
        url = f"{_DDAMFN_BASE}/{prefix}{remote_relpath}"
        try:
            # print statements
            print(f"[DDAMFN] Trying {url}")
            # retrieve the model
            _urllib.urlretrieve(url, str(local_path))
            print(f"[DDAMFN] Saved {local_path} ({local_path.stat().st_size} bytes)")
            return True
        except Exception as error:
            print(f"[DDAMFN]   not here ({error})")
            continue
    # optional file to be missing
    if optional:
        print(f"[DDAMFN] Skipping optional file {remote_relpath}")
        return False
    raise RuntimeError(f"Could not download DDAMFN file: {remote_relpath}")


# checkpoint size and file header before loading
def _ddamfn_verify_checkpoint(local_path):
    local_path = Path(local_path)
    size = local_path.stat().st_size
    with open(local_path, "rb") as handle:
        head = handle.read(64)
    # Reject Git LFS pointers, small files and files without a ZIP header
    if head.startswith(b"version https://git-lfs") or size < 100_000 or head[:2] != b"PK":
        # unusable file so it can be downloaded again
        local_path.unlink(missing_ok=True)
        raise RuntimeError(f"The DDAMFN checkpoint did not download as a valid model file (size {size} bytes). Download 'affecnet7_epoch19_acc0.671.pth' manually from the DDAMFN++ repository and place it at {local_path}, then restart Solace.")


# DDAMFN code and checkpoint for use
def _ensure_ddamfn():
    for relpath in _DDAMFN_CODE_FILES:
        # optional and found
        optional = relpath.endswith("__init__.py")
        found = _ddamfn_fetch(relpath, Path(_DDAMFN_DIR) / relpath, optional=optional)
        # empty package file if it is unavailable online
        if not found and optional:
            init_path = Path(_DDAMFN_DIR) / relpath
            init_path.parent.mkdir(parents=True, exist_ok=True)
            init_path.write_text("")

    # Download and check trained weights
    _ddamfn_fetch("DDAMFN%2B%2B/checkpoints_ver2.0/affecnet7_epoch19_acc0.671.pth", _DDAMFN_CKPT)
    _ddamfn_verify_checkpoint(_DDAMFN_CKPT)

    # Allow Python to import downloaded network code
    if _DDAMFN_DIR not in _sys.path:
        _sys.path.insert(0, _DDAMFN_DIR)

# anger, fear, sadness and disgust class indexes
_DDAMFN_NEG = [6, 4, 2, 5]

# Resize and normalise each face for DDAMFN
_DDAMFN_TF = _transforms.Compose([ _transforms.Resize((112, 112)), _transforms.ToTensor(), _transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])

#  pretrained model names in one place
TEXT_MODEL_ID = "j-hartmann/emotion-english-roberta-large"
AUDIO_MODEL_ID = "MERaLiON/MERaLiON-SER-v1"
WHISPER_MODEL_ID = "openai/whisper-small"
RECOMMENDATION_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

# supported languages to Whisper language codes
WHISPER_LANGUAGES = {"English": "en","Malay": "ms","Chinese": "zh","Tamil": "ta"}

# emotion labels contribute to the strain estimate
NEGATIVE_LABELS = {"anger", "fear", "sadness", "disgust"}

# audio model output order to its emotion labels
MERALION_LABELS = ["Neutral", "Happy", "Sad", "Angry","Fearful", "Disgusted", "Surprised"]

# equivalent emotion labels the same name
LABEL_ALIASES = {
    "angry": "anger", "anger": "anger",
    "fearful": "fear", "fear": "fear",
    "sad": "sadness", "sadness": "sadness",
    "disgusted": "disgust", "disgust": "disgust",
    "happy": "happy", "happiness": "happy", "joy": "happy",
    "neutral": "neutral",
    "surprised": "surprise", "surprise": "surprise"
}

# speech rate ranges used for each language
SPEECH_RANGES = {"English": (100, 190), "Malay": (100, 190), "Chinese": (180, 320), "Tamil": (90, 180)}

# filler words counted in each language
FILLERS = {
    "English": {"um", "uh", "erm", "hmm"},
    "Malay": {"erm", "hmm", "anu", "macam"},
    "Chinese": {"嗯", "呃", "那个", "这个"},
    "Tamil": {"ம்", "ஆம்", "அதாவது", "அப்புறம்"}
}

# eight frames for facial emotion model
VIDEO_FRAME_COUNT = 8

# each supporting signal a small share of the final score
AUXILIARY_WEIGHT = 0.004

# Text distress floor values
TEXT_DISTRESS_THRESHOLD = 0.60
TEXT_DISTRESS_FLOOR = 0.70

# score between zero and one
def clamp(value):
    return max(0.0, min(1.0, float(value)))

# Convert emotion label to the shared name
def label_name(name):
    name = str(name).lower().strip()
    return LABEL_ALIASES.get(name, name)

# Unwrap predictions when the model returns a nested list
def predictions(output):
    return output[0] if output and isinstance(output[0], list) else output

# probabilities of the selected negative emotions
def negative_score(output):
    return clamp(sum(
        float(item["score"])
        for item in predictions(output)
        if label_name(item["label"]) in NEGATIVE_LABELS
    ))

# Coordinate the models and combine the check in results
class MultimodalPipeline:
    def __init__(self):
        # GPU when available and load models only when needed
        self.device = 0 if torch.cuda.is_available() else -1
        self.whisper = None
        self.text_model = None
        self.audio_processor = None
        self.audio_model = None
        self.qwen = None

    # Load Whisper once and reuse it for speech recognition
    def load_whisper(self):
        if self.whisper is None:
            self.whisper = hf_pipeline("automatic-speech-recognition",model=WHISPER_MODEL_ID,device=self.device,chunk_length_s=30)
        return self.whisper

    # Load the text emotion model when it is needed
    def load_text_model(self):
        if self.text_model is None:
            self.text_model = hf_pipeline("text-classification",model=TEXT_MODEL_ID,device=self.device,top_k=None)
        return self.text_model

    # Load the audio processor and emotion model together
    def load_audio_model(self):
        if self.audio_model is None:
            self.audio_processor = AutoProcessor.from_pretrained(AUDIO_MODEL_ID)
            self.audio_model = (AutoModelForAudioClassification.from_pretrained(AUDIO_MODEL_ID,trust_remote_code=True))
            # audio model to the GPU when available
            if torch.cuda.is_available():
                self.audio_model.to("cuda")
            # evaluation mode for predictions
            self.audio_model.eval()
        return self.audio_processor, self.audio_model
    
    # Load DDAMFN with the saved facial expression weights
    def load_ddamfn(self):
        if getattr(self, "ddamfn_model", None) is None:
            device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            # local files before importing the network
            _ensure_ddamfn()
            from networks.DDAM import DDAMNet as _DDAMNet
            # Build the seven-class network and restore its weights
            model = _DDAMNet(num_class=7, num_head=2, pretrained=False)
            # load state dictionary
            model.load_state_dict(torch.load(_DDAMFN_CKPT, map_location=device)["model_state_dict"])
            model.to(device).eval()
            # model and its device for later predictions
            self.ddamfn_model = model
            self.ddamfn_device = device
        return self.ddamfn_model
    
    # Load Qwen when recommendation is needed
    def load_qwen(self):
        if self.qwen is None:
            self.qwen = hf_pipeline("text-generation",model=RECOMMENDATION_MODEL_ID,device_map="auto",dtype="auto")
        return self.qwen

    # Run Whisper using selected language and task
    def whisper_text(self, audio_path, language_name, task):
        # recording as mono audio at 16000 Hz
        audio, _ = librosa.load(audio_path,sr=16000,mono=True)
        # load whisper model
        result = self.load_whisper()(
            {"array": audio,"sampling_rate": 16000},
            return_timestamps=True,
            generate_kwargs={"language": WHISPER_LANGUAGES[language_name],"task": task}
        )
        # return result
        return result["text"].strip()

    # Transcribe speech in the selected language
    def transcribe(self, audio_path, language_name):
        return self.whisper_text(audio_path,language_name,"transcribe")

    # English transcript for the text emotion model
    def translate_to_english(self, audio_path, language_name):
        if language_name == "English":
            return self.transcribe(audio_path,language_name)
        return self.whisper_text(audio_path,language_name,"translate")

    # negative emotion from the English transcript
    def text_score(self, text):
        output = self.load_text_model()(text,truncation=True,max_length=512,top_k=None)
        return negative_score(output)

    # negative emotion from recording voice signals
    def audio_score(self, audio_path):
        processor, model = self.load_audio_model()
        # Prepare mono audio in the format expected by the model
        audio, _ = librosa.load(audio_path,sr=16000,mono=True)
        inputs = processor(audio,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
        device = next(model.parameters()).device
        # only supported inputs to the model device
        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
            if key in {"input_features","attention_mask"}
        }

        # prediction without storing gradients
        with torch.inference_mode():
            logits = model(**inputs)["logits"]

        # Convert model output into emotion probabilities
        probabilities = (torch.softmax(logits, dim=-1)[0].detach().cpu().tolist())
        # Pair each probability with its emotion label
        output = [
            {"label": label,"score": score}
            for label, score
            in zip(MERALION_LABELS,probabilities)
        ]
        # return negative scores
        return negative_score(output)

    # Average negative emotion scores across sampled faces
    def vision_score(self, video_path):
            frames = self.sample_faces(video_path)
            # no usable face crops were found stop
            if not frames:
                # runtime error
                raise RuntimeError("No face detected in the video")
            # model load and scores
            model = self.load_ddamfn()
            scores = []
            with torch.inference_mode():
                for image in frames:
                    # Prepare each face and add batch dimension
                    tensor = _DDAMFN_TF(image).unsqueeze(0).to(self.ddamfn_device)
                    out, _, _ = model(tensor)
                    probs = _F.softmax(out, dim=1)[0]
                    # Combine four negative emotion probabilities
                    scores.append(float(sum(probs[i] for i in _DDAMFN_NEG)))
            return mean(scores)

    # face crops from evenly spaced video frames
    def sample_faces(self, video_path):
        capture = cv2.VideoCapture(video_path)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        # OpenCV frontal face detector
        detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        # images list
        images = []
        # Spread samples across the full video
        for index in range(VIDEO_FRAME_COUNT):
            position = int(index * max(frame_count - 1, 0) / max(VIDEO_FRAME_COUNT - 1, 1))
            capture.set(cv2.CAP_PROP_POS_FRAMES, position,)
            ok, frame = capture.read()
            # skip frames that could not be read
            if not ok:
                continue
            # grey colour
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY,)
            # detect faces
            faces = detector.detectMultiScale(grey, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            # Skip frames with no detected face
            if len(faces) == 0:
                continue
            # largest face and leave a small margin around it
            x, y, width, height = max(faces,key=lambda box:box[2] * box[3])
            margin = int(max(width, height) * 0.18)
            # x1,x2,y1y2
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(frame.shape[1],x + width + margin,)
            y2 = min(frame.shape[0],y + height + margin,)
            # Convert crop to RGB for the image model
            face = cv2.cvtColor(frame[y1:y2, x1:x2],cv2.COLOR_BGR2RGB,)
            images.append(Image.fromarray(face))
        # Release video after collecting the crops
        capture.release()
        return images

    # Measure distance between two face landmarks
    @staticmethod
    def distance(a, b):
        return math.hypot(a.x - b.x,a.y - b.y,)

    # Compare eye height with eye width to estimate eye openness
    def eye_ratio(self, landmarks, indexes):
        p1, p2, p3, p4, p5, p6 = [landmarks[index] for index in indexes]
        # horizontal and vertical
        horizontal = self.distance(p1,p4)
        vertical = (self.distance(p2, p6) + self.distance(p3, p5))
        # return results
        return (vertical / (2 * horizontal) if horizontal else 0)

    # Measure blink rate and horizontal face position
    def visual_signals(self, video_path):
        capture = cv2.VideoCapture(video_path)
        # frame rate to estimate the recording length
        fps = (capture.get(cv2.CAP_PROP_FPS) or 30)
        duration = (int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) / fps)
        # six landmarks around each eye
        left_eye = [33, 160, 158,133, 153, 144]
        right_eye = [362, 385, 387,263, 373, 380]
        blink_count = 0
        eye_closed = False
        head_offsets = []
        frame_number = 0

        # Track one face with refined eye landmarks
        with mp.solutions.face_mesh.FaceMesh(max_num_faces=1,refine_landmarks=True) as face_mesh:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_number += 1
                # Process every third frame to reduce workload
                if frame_number % 3:
                    continue

                result = face_mesh.process(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
                # skip frames without visible face landmarks
                if (not result.multi_face_landmarks):
                    continue
                landmarks = (result.multi_face_landmarks[0].landmark)
                # Average openness measurements from both eyes
                eye = (self.eye_ratio(landmarks,left_eye) + self.eye_ratio(landmarks,right_eye)) / 2

                # Remember when eyes cross the closed eye threshold
                if (eye < 0.20 and not eye_closed):
                    eye_closed = True

                # Count one blink when the eyes reopen
                elif (eye >= 0.20 and eye_closed):
                    blink_count += 1
                    eye_closed = False

                # Measure how far nose sits from the frame centre
                head_offsets.append(abs(landmarks[1].x - 0.5))
        capture.release()

        # Stop no face position measurements were collected
        if not head_offsets:
            # error
            raise RuntimeError("Face landmarks could not be measured")

        # Convert blink count into blinks per minute
        blink_rate = (blink_count / duration * 60 if duration else 0)
        head_offset = mean(head_offsets)

        # face position using its average horizontal offset
        if head_offset <= 0.08:
            head_position = "Centred"

        elif head_offset <= 0.18:
            head_position = ("Slightly off-centre")

        else:
            head_position = "Off-centre"

        # blink rates outside chosen range into a supporting signal
        if blink_rate < 8:
            blink_signal = clamp((8 - blink_rate) / 8)

        elif blink_rate > 25:
            blink_signal = clamp((blink_rate - 25) / 25)

        else:
            blink_signal = 0

        # Return measurements and their supporting scores
        return {
            "blink_rate": round(blink_rate, 2),
            "head_position": head_position,
            "blink_signal": blink_signal,
            "head_signal":clamp((head_offset - 0.08) / 0.25)
        }

    # Measure speech pace, filler use and word variety
    def speech_signals(self,transcript,audio_path,language_name):
        duration = librosa.get_duration(path=audio_path)
        # count Chinese characters as speech units
        if language_name == "Chinese":
            words = re.findall(r"[\u4e00-\u9fff]",transcript)

        else:
            # Count word tokens and leave out punctuation
            words = [
                token.lower()
                for token
                in wordpunct_tokenize(transcript)
                if any(letter.isalpha() for letter in token)
            ]

        # speech units per minute and the share of unique units
        speech_rate = (len(words) / duration * 60 if duration else 0)
        lexical_variety = (len(set(words)) / len(words) if words else 0)
        fillers = FILLERS[language_name]
        # Find Chinese and Tamil fillers directly in the transcript
        if language_name in {"Chinese","Tamil",}:
            disfluencies = sum(transcript.count(word) for word in fillers)
        else:
            # Match whole tokens for English and Malay fillers
            disfluencies = sum(word in fillers for word in words)
        disfluency_rate = (disfluencies / len(words) if words else 0)
        # speech pace with the selected language range
        low, high = SPEECH_RANGES[language_name]
        if speech_rate < low:
            speech_signal = clamp((low - speech_rate) / low)
        # speech rate high
        elif speech_rate > high:
            speech_signal = clamp((speech_rate - high) / high)

        else:
            speech_signal = 0

        # speech measurements and their supporting scores
        return {
            "speech_rate": round(speech_rate, 2),
            "disfluency_rate": round(disfluency_rate, 3),
            "lexical_variety": round(lexical_variety, 3),
            "speech_signal": speech_signal,
            "disfluency_signal": clamp(disfluency_rate / 0.10),
            "lexical_signal": clamp((0.45 - lexical_variety) / 0.45)
        }


    # Combine model scores with the supporting signals
    def fuse(self, primary_scores, supporting_scores,):
        # median to reduce the effect of one extreme model score
        primary = median(primary_scores)
        supporting = (mean(supporting_scores) if supporting_scores else 0)
        # each supporting score its small fixed contribution
        supporting_contribution = sum(score * AUXILIARY_WEIGHT for score in supporting_scores)
        # remaining weight for the main model score
        primary_weight = (1.0 - len(supporting_scores) * AUXILIARY_WEIGHT)
        strain = clamp(primary * primary_weight + supporting_contribution)
        return (primary,supporting, strain, primary_weight)


    # Extract video audio into a temporary WAV file
    def extract_audio(self,video_path,):
        output = (tempfile.NamedTemporaryFile(suffix=".wav",delete=False))
        output.close()
        try:
            # FFmpeg for mono audio at 16000 Hz
            subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", video_path, "-vn", "-ac", "1", "-ar",
                    "16000", "-c:a", "pcm_s16le", output.name],
                capture_output=True, check=True, timeout=120
            )
    
        # Remove temporary file and explain extraction failures
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
            Path(output.name).unlink(missing_ok=True)
            # error
            raise RuntimeError("The video audio could not be extracted. Check that the video has an audio track and that FFmpeg is available.") from error
        return output.name


    # three recommendations and translate them for the user
    def recommendation(self,english_text,wellbeing_score,summary,language_name,trend):
        generator = self.load_qwen()
        support_note = ""
        # Ask for support contact suggestion when the score is low
        if wellbeing_score < 35:
            support_note = ("Include one recommendation to contact a trusted person or qualified healthcare professional.")
        # Give Qwen transcript score summary and recent trend
        messages = [
            {
                # system
                "role": "system",
                "content": ("You are a workplace wellbeing support assistant. Do not diagnose medical conditions.")
            },
            {
                # user
                "role": "user",
                "content": ("Write exactly 3 short wellbeing recommendations in English.\n"
                    "Write each recommendation on a separate numbered line.\n"
                    "Make each recommendation different and practical.\n"
                    "Do not repeat ideas.\n"
                    f"{support_note}\n\n"
                    f"Wellbeing score: "
                    f"{wellbeing_score:.0f}/100\n"
                    f"Summary: {summary}\n"
                    f"Trend: {trend}\n"
                    f"Transcript: "
                    f"{english_text[:1200]}"
                )
            }
        ]

        # prompt with Qwen thinking mode disabled
        prompt = generator.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        # short reply without random sampling
        english = generator(prompt,max_new_tokens=180,do_sample=False,return_full_text=False,pad_token_id=generator.tokenizer.eos_token_id,)[0]["generated_text"].strip()
        # Release Qwen before running translation
        self.release_qwen()
        translated = translate_text(english, language_name)
        # return results
        return english, translated

    # Run full check in analysis and prepare the results
    def analyse(self, recording_path, recording_type, progress, transcript=None, *, language_name="English",trend=( "No previous check-in trend is available."),):
        temporary_audio = None
        try:
            # Extract separate audio track when input is video
            if recording_type == "video":
                progress("processing_extract_audio")
                temporary_audio = (self.extract_audio(recording_path))
                audio_path = (temporary_audio)
            else:
                audio_path = (recording_path)
            # Create transcript only when one was not supplied
            if not transcript:
                progress("processing_transcription")
                transcript = self.transcribe(audio_path,language_name,)
            progress("processing_text")
            # English text for text emotion model
            if language_name == "English":
                english_text = transcript
            else:
                english_text = (self.translate_to_english(audio_path,language_name))
            # Score transcript, then release speech model
            text = self.text_score(english_text)
            self.release_whisper()
            progress("processing_audio")
            # Score audio and start list of main model results
            audio = self.audio_score(audio_path)
            primary_scores = [text, audio]
            vision = None
            visual = {}

            # Add facial emotion and visual signals for video check ins
            if recording_type == "video":
                progress("processing_vision")
                vision = self.vision_score(recording_path)
                primary_scores.append(vision)
                progress("processing_signals")
                visual = (self.visual_signals(recording_path))
            else:
                progress("processing_signals")
            # Measure speech signals using the original transcript
            speech = self.speech_signals(transcript, audio_path, language_name,)
            # Collect supporting scores available for this recording
            supporting = [speech["speech_signal"], speech["disfluency_signal"],speech["lexical_signal"]]
            if recording_type == "video":
                supporting += [visual["blink_signal"], visual["head_signal"]]
            progress("processing_fusion")
            # Fuse scores and convert strain into wellbeing
            (primary_strain, supporting_strain, strain,primary_weight) = self.fuse(primary_scores, supporting)
            # Text-distress floor
            if text >= TEXT_DISTRESS_THRESHOLD:
                strain = clamp(max(strain, TEXT_DISTRESS_FLOOR * text))
            strain_score = (strain * 100)
            wellbeing_score = (100 - strain_score)
            phrase, explanation = (self.summary(wellbeing_score))
            # Release analysis models before generating recommendations
            self.release_analysis_models()
            progress("processing_recommendation")
            recommendation_english, recommendation = self.recommendation(english_text,wellbeing_score,phrase,language_name,trend)
            # Return transcripts, scores, signals and recommendation text
            return {
                "recording_type": recording_type,
                "language": language_name,
                "transcript": transcript,
                "transcript_english": english_text,
                "text_score": round(text * 100, 2),
                "audio_score":round(audio * 100, 2),
                "vision_score":(round(vision * 100, 2)
                        if vision
                        is not None
                        else None
                    ),
                "blink_rate": visual.get( "blink_rate"),
                "head_position":visual.get( "head_position"),
                "speech_rate": speech["speech_rate"],
                "disfluency_rate":speech[ "disfluency_rate"],
                "lexical_variety":speech["lexical_variety"],
                "primary_strain_score":round(primary_strain* 100, 2),
                "auxiliary_strain_score":round(supporting_strain* 100,2),
                "strain_score":round(strain_score, 2),
                "wellbeing_score": round(wellbeing_score,2),
                "primary_weight": round(primary_weight * 100, 2),
                "phrase": phrase,
                "explanation": explanation,
                "recommendation": recommendation,
                "recommendation_english": recommendation_english,
            }

        # Always remove audio extracted from a video
        finally:
            if temporary_audio:
                Path(temporary_audio).unlink(missing_ok=True)

    # short explanation for the wellbeing score range
    @staticmethod
    def summary(score):
        if score >= 67:
            return (
                "Today feels steady",
                "Your signals suggest a higher wellbeing range."
            )

        if score >= 34:
            return (
                "Today feels mixed",
                "Your signals suggest a moderate wellbeing range."
            )

        return (
            "Today needs more care",
            "Your signals suggest a lower wellbeing range."
        )

    # Release Whisper and clear unused memory
    def release_whisper(self):
        self.whisper = None
        self.clean_memory()

    # Release emotion models and their processors
    def release_analysis_models(self):
        self.text_model = None
        self.audio_processor = None
        self.audio_model = None
        self.ddamfn_model = None
        self.clean_memory()

    # Release Qwen and clear unused memory
    def release_qwen(self):
        self.qwen = None
        self.clean_memory()

    # unused objects and clear GPU unused cache
    @staticmethod
    def clean_memory():
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# one pipeline between the background workers
_PIPELINE = MultimodalPipeline()

# Transcribe recordings without blocking the interface
class TranscriptionWorker(QThread):
    # Send progress, finished text or errors back to the interface
    progress = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self,recording_path,recording_type,parent=None,*,language_name="English"):
        super().__init__(parent)
        # recording and chosen language for this job
        self.recording_path = (recording_path)
        self.recording_type = (recording_type)
        self.language_name = (language_name)

    # audio and run transcription in the background
    def run(self):
        temporary_audio = None
        try:
            # Extract audio first when user supplied a video
            if self.recording_type == "video":
                self.progress.emit("transcription_extract_audio")
                temporary_audio = (_PIPELINE.extract_audio(self.recording_path))
                audio_path = (temporary_audio)

            else:
                # audio path
                audio_path = (self.recording_path)
            self.progress.emit("transcription_whisper")
            # transcript
            transcript = (_PIPELINE.transcribe(audio_path,self.language_name,))
            # Send finished transcript to interface
            self.completed.emit(transcript)

        # Report transcription failures as readable text
        except Exception as error:
            self.failed.emit(str(error))

        # Remove temporary audio and release Whisper after the job
        finally:
            if temporary_audio:
                Path(temporary_audio).unlink(missing_ok=True)

            # release whisper
            _PIPELINE.release_whisper()


# Analyse check ins without blocking the interface
class AnalysisWorker(QThread):
    # Send progress, finished results or errors back to the interface
    progress = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self,recording_path,recording_type,transcript,parent=None,*,language_name="English",trend=("No previous check-in trend is available.")):
        super().__init__(parent)
        # Remember recording, transcript, language and recent trend
        self.recording_path = (recording_path)
        self.recording_type = (recording_type)
        self.transcript = transcript
        self.language_name = language_name
        self.trend = trend

    # Run analysis while keeping track of the current stage
    def run(self):
        stage = "initialisation"
        # Remember each stage and forward its progress message
        def report_stage(key):
            nonlocal stage
            stage = key.removeprefix("processing_").replace("_", " ")
            self.progress.emit(key)
        try:
            # Pass recording and its context to shared pipeline
            result = _PIPELINE.analyse(
                self.recording_path,
                self.recording_type,
                report_stage,
                self.transcript,
                language_name=self.language_name,
                trend=self.trend
            )

            # completed results to the interface
            self.completed.emit(result)

        # failed stage in the error message
        except Exception as error:
            self.failed.emit(f"Stage: {stage}\n{type(error).__name__}: {error}")

        # Release loaded models after the worker finishes
        finally:
            _PIPELINE.release_whisper()
            _PIPELINE.release_analysis_models()
            _PIPELINE.release_qwen()