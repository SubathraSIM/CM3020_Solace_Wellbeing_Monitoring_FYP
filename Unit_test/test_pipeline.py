# Import required libraries
import tempfile
import wave
from pathlib import Path
from UI.ai.multimodal_pipeline import MultimodalPipeline,clamp,label_name,negative_score,predictions

# Helper function to create a temporary silent WAV file
def create_test_wav(path, duration, sample_rate=16000):
    # Work out how many audio samples are needed
    frame_count = int(duration * sample_rate)
    # Open a WAV file for writing
    with wave.open(str(path), "wb") as wav_file:
        # one audio channel
        wav_file.setnchannels(1)
        # Store each sample using two bytes
        wav_file.setsampwidth(2)
        # Set the number of audio samples per second
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)


# Test case 1: Check that clamp keeps values between 0 and 1
def test_clamp():
    assert clamp(-0.5) == 0.0
    assert clamp(0.0) == 0.0
    assert clamp(0.5) == 0.5
    assert clamp(1.0) == 1.0
    assert clamp(1.5) == 1.0


# Test case 2: Check that emotion labels are converted to the common labels
def test_label_name():
    assert label_name("Angry") == "anger"
    assert label_name("Fearful") == "fear"
    assert label_name("Sad") == "sadness"
    assert label_name("Disgusted") == "disgust"
    assert label_name("Happy") == "happy"
    assert label_name("Joy") == "happy"
    assert label_name("Neutral") == "neutral"
    assert label_name("label_0") == "anger"
    assert label_name("label_3") == "happy"
    assert label_name("label_6") == "neutral"


# Test case 3: Check that flat and nested model outputs are handled correctly
def test_predictions():
    # model result in a plain list
    flat_output = [{"label": "anger", "score": 0.4}]
    # same result inside an extra list
    nested_output = [[{"label": "anger", "score": 0.4}]]
    assert predictions(flat_output) == flat_output
    assert predictions(nested_output) == nested_output[0]


# Test case 4: Check that only negative emotions are added to the strain score
def test_negative_score():
    # Start the sample output with an anger score
    output = [{"label": "anger", "score": 0.20},
        {"label": "fear", "score": 0.10},
        {"label": "sadness", "score": 0.25},
        {"label": "disgust", "score": 0.05},
        {"label": "happy", "score": 0.30},
        {"label": "neutral", "score": 0.10}]

    # combined negative emotion score
    result = negative_score(output)
    assert round(result, 2) == 0.60


# Test case 5: Check that the negative emotion score cannot go above 1
def test_negative_score_limit():
    # Build output whose negative scores exceed one
    output = [
        {"label": "anger", "score": 0.70},
        {"label": "fear", "score": 0.60}
    ]

    # combined negative emotion score
    result = negative_score(output)
    assert result == 1.0


# Test case 6: Check the eye ratio calculation used for blink detection
def test_eye_ratio():
    # simple point for the eye landmarks
    class Point:
        def __init__(self, x, y):
            # horizontal position
            self.x = x
            # vertical position
            self.y = y

    # Build six sample points around an eye
    landmarks = [
        Point(0.0, 0.0),
        Point(0.5, 0.5),
        Point(1.5, 0.5),
        Point(2.0, 0.0),
        Point(1.5, -0.5),
        Point(0.5, -0.5)
    ]

    # pipeline for test
    pipeline = MultimodalPipeline()
    # eye ratio from all six points
    result = pipeline.eye_ratio(landmarks, [0, 1, 2, 3, 4, 5])
    assert round(result, 2) == 0.50


# Test case 7: Check English speech rate, disfluency and lexical variety
def test_english_speech_signals():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # temporary folder for the test audio
    with tempfile.TemporaryDirectory() as folder:
        # path for the English test audio
        audio_path = Path(folder) / "english.wav"
        # six seconds of silent audio
        create_test_wav(audio_path, duration=6)
        # English sentence with a filler word
        transcript = ("I feel tired um after a long shift but I feel okay")
        # English speech signals
        result = pipeline.speech_signals(transcript, str(audio_path),"English")

    assert result["speech_rate"] == 120.0
    assert result["disfluency_rate"] == 0.083
    assert result["lexical_variety"] == 0.833
    assert result["speech_signal"] == 0
    assert round(result["disfluency_signal"], 3) == 0.833
    assert result["lexical_signal"] == 0


# Test case 8: Check Chinese speech signals use Chinese characters correctly
def test_chinese_speech_signals():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # temporary folder for the test audio
    with tempfile.TemporaryDirectory() as folder:
        # path for the Chinese test audio
        audio_path = Path(folder) / "chinese.wav"
        # two seconds of silent audio
        create_test_wav(audio_path, duration=2)
        # Chinese sentence with a filler sound
        transcript = "我今天很累嗯但是还好"
        # Chinese speech signals
        result = pipeline.speech_signals(transcript, str(audio_path), "Chinese")

    assert result["speech_rate"] == 300.0
    assert result["disfluency_rate"] == 0.1
    assert result["lexical_variety"] == 1.0
    assert result["speech_signal"] == 0
    assert result["disfluency_signal"] == 1.0
    assert result["lexical_signal"] == 0


# Test case 9: Check that slow speech produces a supporting strain signal
def test_slow_speech_signal():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # temporary folder for the test audio
    with tempfile.TemporaryDirectory() as folder:
        # path for the slow speech test audio
        audio_path = Path(folder) / "slow.wav"
        # six seconds of silent audio
        create_test_wav(audio_path, duration=6)
        # short sentence for the slow speech test
        transcript = ("I feel very tired")
        # English speech signals
        result = pipeline.speech_signals(transcript, str(audio_path),"English")

    assert result["speech_rate"] == 40.0
    assert round(result["speech_signal"],2) == 0.60


# Test case 10: Check audio fusion uses median primary score with 0.4% allocated to each supporting signal
def test_audio_fusion():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # two primary scores for the test
    primary_scores = [0.40, 0.60]
    # three supporting scores for audio
    supporting_scores = [0.20, 0.40, 0.60]
    # Combine audio scores and keep each result
    (primary,supporting,strain,primary_weight) = pipeline.fuse(primary_scores,supporting_scores)

    assert round(primary, 2) == 0.50
    assert round(supporting, 2) == 0.40
    assert primary_weight == 0.988
    assert round(strain, 4) == 0.4988


# Test case 11: Check video fusion uses median primary score with 2% total supporting-signal contribution
def test_video_fusion():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # three primary scores including a high value
    primary_scores = [0.10, 0.20, 0.90]
    # five supporting scores for video
    supporting_scores = [0.10, 0.20, 0.30, 0.40, 0.50]
    # Combine video scores and keep each result
    (primary, supporting, strain, primary_weight) = pipeline.fuse(primary_scores, supporting_scores)

    assert round(primary, 2) == 0.20
    assert round(supporting, 2) == 0.30
    assert primary_weight == 0.98
    assert round(strain, 3) == 0.202


# Test case 12: Check fusion works when no supporting signals are supplied
def test_fusion_without_supporting_signals():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # two primary scores for the test
    primary_scores = [0.40, 0.60]
    # Combine primary scores without supporting scores
    (primary,supporting,strain,primary_weight) = pipeline.fuse(primary_scores,[])

    assert round(primary, 2) == 0.50
    assert supporting == 0
    assert primary_weight == 1.0
    assert round(strain, 2) == 0.50

# Test fusion when all scores are at their maximum
def test_fusion_maximum_strain():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # three primary scores to one
    primary_scores = [1.0, 1.0, 1.0]
    # five supporting scores to one
    supporting_scores = [1.0, 1.0, 1.0, 1.0, 1.0]
    # Combine maximum scores
    (primary,supporting,strain,primary_weight) = pipeline.fuse(primary_scores, supporting_scores)

    assert primary == 1.0
    assert supporting == 1.0
    assert primary_weight == 0.98
    assert strain == 1.0
    
# Test case 13: Check the higher wellbeing score boundary
def test_high_wellbeing_summary():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # summary for a wellbeing score of 67
    phrase, explanation = pipeline.summary(67)
    assert phrase == "Today feels steady"
    assert ("higher wellbeing range" in explanation)

# Test case 14: Check the moderate wellbeing score boundary
def test_moderate_wellbeing_summary():
    # pipeline for this test
    pipeline = MultimodalPipeline()
    # summary for a wellbeing score of 34
    phrase, explanation = pipeline.summary(34)
    assert phrase == "Today feels mixed"
    assert ("moderate wellbeing range" in explanation)


# Test case 15: Check the lower wellbeing score boundary
def test_low_wellbeing_summary():
    # pipeline for test
    pipeline = MultimodalPipeline()
    # summary for a wellbeing score of 33
    phrase, explanation = pipeline.summary(33)
    assert phrase == "Today needs more care"
    assert ("lower wellbeing range" in explanation)