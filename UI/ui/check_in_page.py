# Import required libraries
from UI.ui.account_widgets import add_avatar
import math, random, re, struct, sys, tempfile, wave
from datetime import datetime
from pathlib import Path
import librosa
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal, QDate
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioFormat, QAudioInput, QAudioOutput, QAudioSource, QCamera,QMediaCaptureSession, QMediaDevices, QMediaFormat, QMediaPlayer,QMediaRecorder
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QMessageBox, QTabWidget, QSplitter, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout,QLabel, QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy,QStackedWidget, QVBoxLayout, QWidget, QToolTip
from UI.ai.multimodal_pipeline import AnalysisWorker, TranscriptionWorker
from UI.database.database import get_recent_scores, get_previous_strain_scores, save_check_in
from UI.ui.home_page import HoverSidebar
from UI.ui.ui_components import float_in
from UI.ui.translations import ENGLISH_TEXT, get_text
from statistics import mean, pstdev

# project and image folders
ROOT = Path(__file__).resolve().parents[2]
# app recordings in a temporary Solace folder
RECORDINGS = Path(tempfile.gettempdir()) / "Solace" / "recordings"

# images folder
IMAGES = ROOT / "UI" / "images"
RECORDINGS.mkdir(parents=True, exist_ok=True)

# English check in labels and progress messages
CHECKIN_TEXT = {
    "record_check_in": "Record your check-in",
    "record_instruction": "Record video or audio. Your transcript appears after you stop.",
    "video_check_in": "Video check-in",
    "camera_off": "Camera is off",
    "audio_check_in": "Audio-only check-in",
    "audio_note": "The bars respond to your voice and replay.",
    "automatic_transcript": "Automatic transcript",
    "transcript_note": "Whisper creates this after recording stops. You may correct it before submission.",
    "transcript_placeholder": "Your transcript will appear here.",

    "not_recorded": "Not recorded",
    "start_video": "Start video",
    "start_audio": "Start audio",
    "recording": "Recording",
    "stop_video": "Stop video",
    "stop_audio": "Stop audio",
    "record_again": "Record again",
    "record_instead": "Record instead",
    "video_recorded": "Video recorded",
    "audio_recorded": "Audio recorded",
    "uploaded": "Uploaded",
    "upload": "Upload",
    "delete": "Delete",
    "submit": "Submit",

    "upload_recording": "Upload recording",
    "upload_recording_title": "Upload a recording",
    "upload_recording_note": "Choose the recording type, then select one file.",
    "recording_type": "Recording type",
    "audio": "Audio",
    "video": "Video",
    "no_file_selected": "No file selected",
    "choose_file": "Choose file",
    "cancel": "Cancel",
    "use_file": "Use this file",
    "select_audio_file": "Select audio file",
    "select_video_file": "Select video file",

    "creating_transcript": "Creating transcript...",
    "transcription_extract_audio": "Extracting audio for transcription...",
    "transcription_whisper": "Creating transcript with Whisper...",
    "transcript_unavailable": "Transcript unavailable. Record or upload another file.",
    "transcription_failed": "Transcription failed. Please try another recording.",

    "stop_before_submit": "Stop the recording before submitting.",
    "record_first": "Record or upload video or audio first.",
    "wait_transcript": "Please wait for the transcript to finish.",
    "transcript_required": "A transcript is required before analysis.",
    "no_camera": "No camera was found.",
    "no_microphone": "No microphone was found.",
    "microphone_failed": "The microphone could not be started.",
    "video_failed": "Video recording failed.",
    "analysis_failed": "Analysis could not be completed. Please try again.",

    "processing_title": "Processing your check-in",
    "processing_note": "Please keep the application open while the selected models run.",
    "processing_loading": "Loading the selected AI models...",
    "processing_extract_audio": "Extracting audio...",
    "processing_transcription": "Transcribing speech...",
    "processing_text": "Analysing text emotion...",
    "processing_audio": "Analysing voice emotion...",
    "processing_vision": "Analysing facial expression...",
    "processing_signals": "Calculating supporting signals...",
    "processing_fusion": "Combining the available signals...",
    "processing_recommendation": "Generating supportive recommendations...",

    "wellbeing_summary": "Your wellbeing summary",
    "experimental_note": "This is an experimental wellbeing estimate, not a diagnosis.",
    "summary_note": "The summary combines the available AI and supporting signals.",
    "wellbeing_score": "Wellbeing score",
    "score_caveat": "An indicative signal, not a diagnosis.",
    "supporting_signals": "Supporting signals",
    "blink_rate": "Blink rate",
    "head_position": "Head position",
    "speech_rate": "Speech rate",
    "disfluency": "Disfluency",
    "lexical_variety": "Lexical variety",
    "not_available": "Not available",
    "head_centred": "Centred",
    "head_slightly_off": "Slightly off-centre",
    "head_off": "Off-centre",
    "supportive_recommendations": "Supportive recommendations",
    "qwen_note": "Generated from this check-in using Qwen.",
    "rec_link_disclaimer": "Links are AI-generated and may occasionally be outdated or unavailable (404). Open with care.",
    "rec_open_link": "Open resource  ↗",
    "saved_history": "Your check-in has been saved locally.",
    "done": "Done",

    "first_high_phrase": "Today feels steady",
    "first_high_text": "Your first check-in shows a higher wellbeing range.",
    "first_mid_phrase": "Today feels mixed",
    "first_mid_text": "Your first check-in shows a moderate wellbeing range.",
    "first_low_phrase": "Today needs more care",
    "first_low_text": "Your first check-in shows a lower wellbeing range.",
    "improved_phrase": "You're moving forward",
    "improved_text": "Your wellbeing score has improved compared with your previous check-in.",
    "lower_phrase": "A little more care may help",
    "lower_text": "Your wellbeing score is lower than your previous check-in.",
    "steady_phrase": "Today feels steady",
    "steady_text": "Your wellbeing score is close to your previous check-in.",

    "baseline_above": "Above your recent range.",
    "baseline_below": "Below your recent range.",
    "baseline_within": "Within your recent range.",
}

# check in wording to the shared translation system
ENGLISH_TEXT.update(CHECKIN_TEXT)

ENGLISH_TEXT.update({
    "trend_band_high": "High wellbeing",
    "trend_band_mid": "Moderate wellbeing",
    "trend_band_low": "Low wellbeing",
})

# label with the requested options
def label(name="", wrap=False, align=None):
    w = QLabel()
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    # if align is not none
    if align is not None:
        w.setAlignment(align)
    return w

# styled frame
def frame(name):
    w = QFrame()
    w.setObjectName(name)
    w.setAttribute(Qt.WA_StyledBackground, True)
    return w

# button with the requested size
def button(name, height=44, width=None):
    w = QPushButton()
    w.setObjectName(name)
    # height and width
    w.setFixedHeight(height)
    w.setCursor(Qt.PointingHandCursor)
    if width:
        w.setFixedWidth(width)
    return w

# guidance for switching recording tabs
ENGLISH_TEXT.update({
    "video_tab": "Video check-in",
    "video_position_note": "Keep your face in view and speak naturally. Review your recording before you submit.",
    "audio_tab": "Audio check-in",
    "capture_tab_note": "Switching tabs keeps your recording. Use Delete below to clear it.",
    "stop_before_switch": "Stop your recording before switching tabs.",
})

# Display audio levels as moving bars
class WaveformWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("waveformWidget")

        # forty silent waveform bars
        self.levels = [0.0] * 40
        self.setMinimumHeight(92)

    # Reset waveform bars
    def clear(self):
        self.levels = [0.0] * 40
        self.update()

    # Update the bars from audio level
    def add_level(self, level):
        # incoming level between zero and one
        level = max(0, min(1, float(level)))
        for i in range(40):
            # Shape bars around the centre and vary slightly
            shape = 0.55 + 0.45 * math.sin(math.pi * i / 39)
            target = level * shape * random.uniform(0.75, 1.05)

            # Blend old and new levels for smooth movement
            self.levels[i] = self.levels[i] * 0.5 + target * 0.5
        self.update()

    # Draw bars for current audio levels
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # fill rectangles
        p.fillRect(self.rect(), QColor("#F7F9FD"))

        # Leave space between bars and around the waveform
        gap, padding = 3, 14

        # bar width that fits the widget
        width = max(2.5, (self.width() - padding * 2 - gap * 39) / 40)
        middle, x = self.height() / 2, float(padding)
        p.setPen(Qt.NoPen)

        for value in self.levels:
            # Scale each bar and keep silence visible
            height = max(3, value * self.height() * 0.78)

            # colour for the bars
            p.setBrush(QColor("#5579BE" if value > 0.06 else "#CCD9EE"))
            p.drawRoundedRect(QRectF(x, middle - height / 2, width, height), 3, 3)
            x += width + gap

# animated ring while processing
class LoadingSpinner(QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0
        self.setFixedSize(90, 90)

        # timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)

    # Start the loading animation
    def start(self):
        self.timer.start(40)

    # Stop the loading animation
    def stop(self):
        self.timer.stop()

    # Move the loading spinner to its next angle
    def rotate(self):
        # spinner and wrap the angle at a full turn
        self.angle = (self.angle - 12) % 360
        self.update()

    # Draw current spinner position
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # colour
        pen = QPen(QColor("#5579BE"), 7)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        # visible arc of the spinner
        p.drawArc(QRectF(10, 10, 70, 70), self.angle * 16, 275 * 16)

# Plot recent wellbeing scores
class MiniTrendGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.plot_points = []
        self.current_language = "English"

        # Track the pointer without needing a click
        self.setMouseTracking(True)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # Update scores shown in the graph
    def set_points(self, points):
        self.points = points
        self.plot_points = []
        QToolTip.hideText()
        self.update()

    # Draw saved scores and date labels
    def paintEvent(self, event):
        # Need at least two scores to draw a line
        if len(self.points) < 2:
            return

        # paint
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # graph labels around the plotting area
        left, right, top, bottom = 35, 15, 15, 25
        width = self.width() - left - right
        height = self.height() - top - bottom

        # Space the check in points evenly across the graph
        step = width / (len(self.points) - 1)
        p.setPen(QPen(QColor("#E2E8F0"), 1))

        # guide lines behind the score points
        for row in range(3):
            y = top + row * height / 2
            p.drawLine(left, int(y), self.width() - right, int(y))

        # list for points
        points = []

        # each saved score into a graph position
        for i, item in enumerate(self.points):
            score = float(item["score"])
            points.append(QPointF(left + i * step, top + (100 - score) / 100 * height))

        # Keep marker positions for the hover tooltip
        self.plot_points = points

        # set pen colour
        p.setPen(QPen(QColor("#5579BE"), 3))

        # neighbouring scores with lines
        for i in range(len(points) - 1):
            p.drawLine(points[i], points[i + 1])

        # set brush and pen with colour
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor("#5579BE"), 2))

        # marker at each saved score
        for point in points:
            p.drawEllipse(point, 4, 4)

        # set pen with colour
        p.setPen(QColor("#94A3B8"))

        # Show the day and month at three positions
        middle = (len(self.points) - 1) // 2
        labels = [
            (0, left, Qt.AlignLeft),
            (middle, points[middle].x() - width / 6, Qt.AlignCenter),
            (len(self.points) - 1, left + 2 * width / 3, Qt.AlignRight)
        ]

        for index, x, alignment in labels:
            date = QDate.fromString(self.points[index]["date"], "yyyy-MM-dd")
            text = self.locale().toString(date, "d MMM")
            p.drawText(QRectF(x, self.height() - 20, width / 3, 18), alignment, text)

        # Show the date and wellbeing band near a marker
    def mouseMoveEvent(self, event):
        if not self.plot_points:
            QToolTip.hideText()
            return

        position = event.position()

        # Find the closest marker
        index = min(
            range(len(self.plot_points)),
            key=lambda i: (
                (position.x() - self.plot_points[i].x()) ** 2 + (position.y() - self.plot_points[i].y()) ** 2
            )
        )

        point = self.plot_points[index]
        distance = ((position.x() - point.x()) ** 2 + (position.y() - point.y()) ** 2)

        # Hide the tooltip when the pointer moves away
        if distance > 12 ** 2:
            QToolTip.hideText()
            return

        item = self.points[index]
        score = float(item["score"])

        if score >= 67:
            band_key = "trend_band_high"
        elif score >= 34:
            band_key = "trend_band_mid"
        else:
            band_key = "trend_band_low"

        date = QDate.fromString(item["date"], "yyyy-MM-dd")
        date_text = self.locale().toString(date, "d MMM yyyy")
        band = get_text(self.current_language, band_key)

        QToolTip.showText(event.globalPosition().toPoint(), f"{date_text}\n{band}", self)

    # Clear the tooltip when leaving the graph
    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)

# audio or video recording to upload
class UploadDialog(QDialog):
    def __init__(self, language, parent=None):
        super().__init__(parent)

        # selected recording type and file
        self.language = language
        self.selected_path = ""
        self.selected_type = "audio"
        # Show a frameless card like the privacy dialog
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(560)

        # card title and type label
        card = frame("uploadCard")
        self.title = label("uploadTitle")
        self.note = label("uploadNote", True)
        self.type_label = label("fieldLabel")

        # user choose between audio and video uploads
        self.type_combo = QComboBox()
        self.type_combo.setObjectName("uploadTypeCombo")
        self.type_combo.setFixedHeight(46)
        self.type_combo.addItem("", "audio")
        self.type_combo.addItem("", "video")
        self.type_combo.currentIndexChanged.connect(self.change_type)

        # file label
        self.file_label = label("uploadFileLabel", True)
        self.file_label.setMinimumHeight(24)

        # file selection and confirmation buttons
        self.choose_button = button("uploadChooseButton", 46)
        # Close the upload card without selecting a file
        self.close_button = QPushButton()
        self.close_button.setObjectName("uploadCloseButton")
        self.close_button.setFixedSize(36, 36)
        self.close_button.setIcon(QIcon(str(ROOT / "UI" / "images" / "cross.png")))
        self.close_button.setIconSize(QSize(24, 24))
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.reject)
        self.use_button = button("primaryButton", 44, 150)
        self.use_button.setEnabled(False)

        # file picker, cancel and confirmation actions
        self.choose_button.clicked.connect(self.choose_file)
        self.use_button.clicked.connect(self.accept)

        # Place the cross at the top right
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(self.close_button)

        # Keep the confirmation button at the bottom
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.use_button)

        # layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 14, 24, 16)
        layout.setSpacing(8)
        layout.addLayout(close_row)

        # addwidgets
        for w in (self.title, self.note, self.type_label,self.type_combo, self.file_label, self.choose_button):
            layout.addWidget(w)

        # add stretch and layout
        layout.addLayout(buttons)

        # outer
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.addWidget(card)

        # translate
        self.translate()
        # Fit the card to its contents
        self.ensurePolished()
        self.adjustSize()

    # text in the selected language
    def t(self, key):
        return get_text(self.language, key)

    # Update the upload dialog wording
    def translate(self):
        self.setWindowTitle(self.t("upload_recording"))
        self.close_button.setToolTip(self.t("cancel"))
        self.close_button.setAccessibleName(self.t("cancel"))

        # Translate upload labels and action buttons
        texts = {
            self.title: "upload_recording_title",
            self.note: "upload_recording_note",
            self.type_label: "recording_type",
            self.file_label: "no_file_selected",
            self.choose_button: "choose_file",
            self.use_button: "use_file"
        }

        for w, key in texts.items():
            w.setText(self.t(key))

        # set item text audio or video
        self.type_combo.setItemText(0, self.t("audio"))
        self.type_combo.setItemText(1, self.t("video"))

        # tamil font size small
        if self.language == "Tamil":
            for w in texts:
                w.setStyleSheet("font-size:12px;")

    # Reset file choice when the recording type changes
    def change_type(self):
        self.selected_type = self.type_combo.currentData()
        self.selected_path = ""
        self.file_label.setText(self.t("no_file_selected"))
        self.use_button.setEnabled(False)

    # user choose an audio or video file
    def choose_file(self):
        # Check whether the user chose audio
        audio = self.selected_type == "audio"
        caption = self.t("select_audio_file" if audio else "select_video_file")
        # allowed file types
        file_filter = (
            "Audio files (*.wav *.mp3 *.m4a *.flac *.ogg)"
            if audio else
            "Video files (*.mp4 *.mov *.avi *.mkv *.webm)"
        )

        # file picker and read the chosen path
        path, _ = QFileDialog.getOpenFileName(self, caption, "", file_filter)

        # Use file only if one was selected
        if path:
            self.selected_path = path
            self.file_label.setText(Path(path).name)
            self.use_button.setEnabled(True)

# Compare score with the recent personal range
def classify_baseline(score, previous_scores, min_history=7):
    # wait until enough previous scores are available
    if len(previous_scores) < min_history:
        return None

    # Calculate recent average and score variation
    personal_mean = mean(previous_scores)
    personal_sd = pstdev(previous_scores)

    # Handle history with no variation
    if personal_sd == 0:
        if score > personal_mean:
            return "baseline_above"

        if score < personal_mean:
            return "baseline_below"

        return "baseline_within"

    # whether the score is above the usual range
    if score > personal_mean + personal_sd:
        return "baseline_above"

    # whether the score is below the usual range
    if score < personal_mean - personal_sd:
        return "baseline_below"

    return "baseline_within"

# Manage recording transcription and check in results
class CheckInPage(QWidget):
    home_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()

        # Remember current user and interface language
        self.user_id = None
        self.current_language = "English"
        self.user_labels = []

        # Track recording paths ownership and active recording state
        self.video_file = ""
        self.audio_file = ""
        self.video_local = False
        self.audio_local = False
        self.video_recording = False
        self.audio_recording = False
        self.recording_mode = ""
        self.elapsed = 0

        # raw audio samples and levels for waveform playback
        self.audio_pcm = bytearray()
        self.audio_levels = []

        # Track transcription and analysis workers
        self.transcription_worker = None
        self.analysis_worker = None
        self.processing_key = "processing_loading"

        # Start without an active camera recording session
        self.capture_session = None
        self.camera = None
        self.camera_audio = None
        self.recorder = None

        # Start without an active microphone input
        self.audio_source = None
        self.audio_device = None
        self.audio_format = None

        # Load playback button icons
        self.play_icon = QIcon(str(IMAGES / "play.png"))
        self.pause_icon = QIcon(str(IMAGES / "pause.png"))

        # separate players and audio outputs for video and audio
        self.video_player = QMediaPlayer(self)
        self.video_output = QAudioOutput(self)
        self.video_player.setAudioOutput(self.video_output)
        self.audio_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_player.setAudioOutput(self.audio_output)

        # playback icons, durations and waveforms in sync
        self.video_player.playbackStateChanged.connect(self.video_state)
        self.video_player.durationChanged.connect(lambda ms: self.set_duration(self.video_time, ms))
        self.audio_player.playbackStateChanged.connect(self.audio_state)
        self.audio_player.durationChanged.connect(lambda ms: self.set_duration(self.audio_time, ms))
        self.audio_player.positionChanged.connect(self.sync_waveform)

        # timer to update the recording length
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)

        # shared sidebar and highlight check in
        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        self.sidebar.home_button.setProperty("active", False)
        self.sidebar.check_in_button.setProperty("active", True)

        # style unpolish and polish
        for w in (self.sidebar.home_button, self.sidebar.check_in_button):
            w.style().unpolish(w)
            w.style().polish(w)

        # separate recording, processing and result views
        self.stack = QStackedWidget()
        self.capture_page = self.build_capture()
        self.processing_page = self.build_processing()
        self.result_page = self.build_result()

        # Hide the recording status message automatically after a few seconds
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.capture_status.hide)

        # stack widget
        for page in (self.capture_page, self.processing_page, self.result_page):
            self.stack.addWidget(page)

        # layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)

        # set language english
        self.set_language("English")

    # Update page when it appears
    def showEvent(self, event):
        super().showEvent(event)
        self.sidebar.set_expanded(HoverSidebar._shared_expanded)
        float_in(self.stack)

    # Build page header
    def header(self):
        # heart image
        heart = QLabel()
        heart.setFixedSize(42, 42)
        heart.setAlignment(Qt.AlignCenter)
        heart.setPixmap(QPixmap(str(IMAGES / "heart.png")).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # brand
        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        # user labels available for account updates
        user = label("welcomeLabel", align=Qt.AlignRight | Qt.AlignVCenter)
        self.user_labels.append(user)

        # row
        row = QHBoxLayout()
        row.setSpacing(7)
        row.addWidget(heart)
        row.addWidget(brand)
        row.addStretch()
        row.addWidget(user)
        add_avatar(row)
        return row

    # Build capture
    def build_capture(self):
        page = QWidget()
        page.setObjectName("checkInPageContent")

        # recording heading and status message
        self.capture_title = label("checkInIntroTitle", True)
        self.capture_subtitle = label("checkInIntroText", True)
        self.capture_status = label("captureStatus")
        self.capture_status.hide()

        # title
        title = QHBoxLayout()
        title.addWidget(self.capture_title, 1)
        title.addWidget(self.capture_status)

        # Place video and audio recording in separate tabs
        self.capture_tabs = QTabWidget()
        self.capture_tabs.setObjectName("captureTabs")
        self.capture_tabs.setDocumentMode(False)
        self.capture_tabs.tabBar().setDrawBase(False)
        self.capture_tabs.setAutoFillBackground(False)
        self.capture_tabs.addTab(self.build_video(), "Video check-in")
        self.capture_tabs.addTab(self.build_audio(), "Audio check-in")

        # active tab before handling tab changes
        self._capture_tab_index = 0
        self.capture_tabs.currentChanged.connect(self.capture_tab_changed)
        self.capture_tabs.setMinimumHeight(290)

        # users resize the recording and transcript panels
        workspace = QSplitter(Qt.Vertical)
        workspace.setObjectName("captureWorkspace")
        workspace.setChildrenCollapsible(False)
        workspace.setHandleWidth(10)
        workspace.addWidget(self.capture_tabs)
        workspace.addWidget(self.build_transcript())
        workspace.setSizes([290, 180])
        workspace.setStretchFactor(0, 0)
        workspace.setStretchFactor(1, 1)

        # layout
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 18, 28, 22)
        layout.setSpacing(10)
        layout.addLayout(self.header())
        layout.addLayout(title)
        layout.addWidget(self.capture_subtitle)
        layout.addWidget(workspace, 1)
        layout.addWidget(self.build_actions())
        return page

    # Keep current tab while recording
    def capture_tab_changed(self, index):
        # Keep the current tab while transcription is running
        if self.transcription_worker and self.transcription_worker.isRunning():
            self.capture_tabs.blockSignals(True)
            self.capture_tabs.setCurrentIndex(self._capture_tab_index)
            self.capture_tabs.blockSignals(False)
            self.status(self.t("wait_transcript"))
            return
        self._capture_tab_index = index

    # Build video
    def build_video(self):
        card = frame("videoCaptureCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # video title 
        self.video_title = label("captureCardTitle", True)
        self.video_title.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)

        # Switch between camera placeholder and video display
        self.video_stack = QStackedWidget()
        self.video_stack.setObjectName("videoPreviewStack")
        self.video_stack.setMinimumSize(0, 175)
        self.video_stack.setMaximumHeight(16777215)

        # placeholder before camera or video is available
        placeholder = QWidget()
        placeholder.setObjectName("videoPlaceholder")
        self.camera_off = label("videoPreviewText", align=Qt.AlignCenter)

        # holder
        holder = QVBoxLayout(placeholder)
        holder.setContentsMargins(0, 0, 0, 0)
        holder.addWidget(self.camera_off)

        # video display without stretching the picture
        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("videoWidget")
        self.video_widget.setMinimumSize(0, 175)
        self.video_widget.setMaximumHeight(16777215)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)

        # video stack
        self.video_stack.addWidget(placeholder)
        self.video_stack.addWidget(self.video_widget)

        # video status
        self.video_status = label("recordingStatus")
        self.video_status.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)

        # video time
        self.video_time = QLabel("00:00")
        self.video_time.setObjectName("recordingTimeSmall")
        self.video_time.setFixedWidth(42)

        # video playback button and start it disabled
        self.video_play = button("playMediaButton", 42, 56)
        self.video_play.setIconSize(QSize(18, 18))
        self.video_play.setEnabled(False)
        self.video_play.clicked.connect(self.toggle_video_play)
        self.set_play_icon(self.video_play, False)

        # Connect video recording button to start and stop
        self.video_button = button("recordButton", 42, 150)
        self.video_button.clicked.connect(self.toggle_video)

        # controls
        controls = QHBoxLayout()
        controls.addWidget(self.video_play)
        controls.addWidget(self.video_button)
        self.video_note = label("captureCardText", True)
        self.video_note.setText(self.t("video_position_note"))

        # recording details and controls beside the video
        details = QWidget()
        details.setMinimumWidth(224)
        details.setMaximumWidth(280)
        info = QVBoxLayout(details)
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(10)
        info.addWidget(self.video_title)
        info.addWidget(self.video_note)
        info.addStretch()
        info.addWidget(self.video_status)
        info.addWidget(self.video_time)
        info.addLayout(controls)

        # layout
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(20)
        layout.addWidget(self.video_stack, 1)
        layout.addWidget(details)
        return card

    # Build audio
    def build_audio(self):
        card = frame("checkInLowerCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Create audio heading and recording status
        self.audio_title = label("captureCardTitle", True)
        self.audio_title.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)

        # Show microphone and playback levels in the waveform
        self.waveform = WaveformWidget()
        self.waveform.setMinimumHeight(175)
        self.waveform.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)

        # audio status
        self.audio_status = label("recordingStatus")
        self.audio_status.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)

        # audio tiem
        self.audio_time = QLabel("00:00")
        self.audio_time.setObjectName("recordingTimeSmall")
        self.audio_time.setFixedWidth(42)

        # audio playback button and start it disabled
        self.audio_play = button("audioPlayButton", 42, 56)
        self.audio_play.setIconSize(QSize(18, 18))
        self.audio_play.setEnabled(False)
        self.audio_play.clicked.connect(self.toggle_audio_play)
        self.set_play_icon(self.audio_play, False)

        # audio recording button to start and stop
        self.audio_button = button("recordButton", 42, 150)
        self.audio_button.clicked.connect(self.toggle_audio)

        # controls
        controls = QHBoxLayout()
        controls.addWidget(self.audio_play)
        controls.addWidget(self.audio_button)

        # audio note
        self.audio_note = label("captureCardText", True)

        # audio details and controls beside the waveform
        details = QWidget()
        details.setMinimumWidth(224)
        details.setMaximumWidth(280)
        info = QVBoxLayout(details)
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(10)
        info.addWidget(self.audio_title)
        info.addWidget(self.audio_note)
        info.addStretch()
        info.addWidget(self.audio_status)
        info.addWidget(self.audio_time)
        info.addLayout(controls)

        # layout
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(20)
        layout.addWidget(self.waveform, 1)
        layout.addWidget(details)
        return card

    # Build transcript
    def build_transcript(self):
        card = frame("transcriptCard")
        self.transcript_title = label("captureCardTitle", True)
        self.transcript_note = label("captureCardText", True)

        # transcript read only until transcription finishes
        self.transcript = QPlainTextEdit()
        self.transcript.setObjectName("transcriptEditor")
        self.transcript.setReadOnly(True)

        # layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(7)
        layout.addWidget(self.transcript_title)
        layout.addWidget(self.transcript_note)
        layout.addWidget(self.transcript, 1)
        return card

    # Build actions
    def build_actions(self):
        card = frame("checkInActionCard")

        # upload, delete and submit actions
        self.upload_button = button("uploadCheckInButton")
        self.delete_button = button("deleteCheckInButton")
        self.submit_button = button("submitCheckInButton")
        self.submit_button.setEnabled(False)

        # actions to recording cleanup and analysis
        self.upload_button.clicked.connect(self.open_upload)
        self.delete_button.clicked.connect(self.reset_recordings)
        self.submit_button.clicked.connect(self.submit_check_in)

        # layout
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 11, 18, 11)
        layout.setSpacing(16)

        # add widgets
        for w in (self.upload_button, self.delete_button, self.submit_button):
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(w, 1)

        return card

    # Build processing
    def build_processing(self):
        page = QWidget()
        page.setObjectName("processingPage")

        # Create card shown while analysis is running
        card = frame("processingCard")
        card.setFixedWidth(500)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Add spinner and translated progress labels
        self.spinner = LoadingSpinner()
        self.processing_title = label("processingTitle", align=Qt.AlignCenter)
        self.processing_message = label("processingMessage", True, Qt.AlignCenter)
        self.processing_note = label("processingNote", True, Qt.AlignCenter)

        # inside
        inside = QVBoxLayout(card)
        inside.setContentsMargins(28, 24, 28, 24)
        inside.setSpacing(12)
        inside.addWidget(self.spinner, 0, Qt.AlignCenter)
        inside.addWidget(self.processing_title)
        inside.addWidget(self.processing_message)
        inside.addWidget(self.processing_note)

        # layout
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 22)
        layout.addLayout(self.header())
        layout.addStretch()
        layout.addWidget(card, 0, Qt.AlignCenter)
        layout.addStretch()
        return page

    # Build result
    def build_result(self):
        page = QWidget()
        page.setObjectName("resultPage")

        # results title and subtitle
        self.result_title = label("resultPageTitle", True)
        self.result_subtitle = label("checkInIntroText", True)

        # Create result image and summary explanation
        summary = frame("resultSummaryCard")
        self.result_image = label("resultEmoji", align=Qt.AlignCenter)
        self.result_image.setFixedHeight(120)
        self.result_phrase = label("resultPhrase", True)
        self.result_explanation = label("resultExplanation", True)
        self.summary_note = label("resultReminder", True)

        # summary layout
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(28, 20, 28, 20)
        summary_layout.addWidget(self.result_image)
        summary_layout.addWidget(self.result_phrase)
        summary_layout.addWidget(self.result_explanation)
        summary_layout.addStretch()
        summary_layout.addWidget(self.summary_note)

        # wellbeing score and supporting signals card
        score_card = frame("resultScoreCard")
        self.score_label = label("scoreLabel")

        # wellbeing on a scale from 0 to 100
        self.score = QProgressBar()
        self.score.setObjectName("wellbeingProgress")
        self.score.setRange(0, 100)
        self.score.setFormat("-- / 100")

        # score note and signals title
        self.score_note = label("scoreCaveat", True)
        self.signals_title = label("captureCardTitle")

        # references to each supporting signal label and value
        self.signal_names, self.signal_values = {}, {}

        # grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)

        # keys
        keys = ("blink_rate", "head_position", "speech_rate","disfluency", "lexical_variety")

        # each signal name beside its value
        for row, key in enumerate(keys):
            name = label("scoreCaveat")
            value = label("scoreLabel", align=Qt.AlignRight | Qt.AlignVCenter)
            self.signal_names[key] = name
            self.signal_values[key] = value
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)

        # score layout
        score_layout = QVBoxLayout(score_card)
        score_layout.setContentsMargins(24, 18, 24, 18)
        score_layout.addWidget(self.score_label)
        score_layout.addWidget(self.score)
        score_layout.addWidget(self.score_note)
        score_layout.addSpacing(5)
        score_layout.addWidget(self.signals_title)
        score_layout.addLayout(grid)
        score_layout.addStretch()

        # top
        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(summary, 1)
        top.addWidget(score_card, 1)

        # area for supportive recommendations
        rec = frame("recommendationCard")
        self.rec_title = label("captureCardTitle")
        self.rec_note = label("captureCardText", True)

        # record area and layout
        self.rec_area = QWidget()
        self.rec_layout = QVBoxLayout(self.rec_area)
        self.rec_layout.setContentsMargins(0, 0, 0, 0)
        self.rec_layout.setSpacing(7)

        # record layout
        rec_layout = QVBoxLayout(rec)
        rec_layout.setContentsMargins(20, 14, 20, 14)
        rec_layout.addWidget(self.rec_title)
        rec_layout.addWidget(self.rec_note)
        rec_layout.addWidget(self.rec_area, 1)

        # saved-history note and return button
        actions = frame("checkInActionCard")
        self.done_note = label("checkInInformation", False)
        self.done_button = button("submitCheckInButton", 44, 160)
        self.done_button.clicked.connect(self.finish)

        # action layout
        action_layout = QHBoxLayout(actions)
        action_layout.addWidget(self.done_note)
        action_layout.addStretch()
        action_layout.addWidget(self.done_button)

        # layout
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 22)
        layout.setSpacing(10)
        layout.addLayout(self.header())
        layout.addWidget(self.result_title)
        layout.addWidget(self.result_subtitle)
        layout.addLayout(top, 2)
        layout.addWidget(rec, 3)
        layout.addWidget(actions)
        return page

    # Update controls while task is running
    def set_busy(self, busy):
        self.sidebar.setEnabled(not busy)

    # Start or stop video recording
    def toggle_video(self):
        self.stop_video() if self.video_recording else self.start_video()

    # Start recording from camera and microphone
    def start_video(self):
        # start after old recordings can be cleared
        if not self.reset_recordings():
            return

        # Find default camera and microphone
        camera = QMediaDevices.defaultVideoInput()
        mic = QMediaDevices.defaultAudioInput()

        # Check for missing camera
        if camera.isNull():
            return self.status(self.t("no_camera"))

        # Check for missing microphone
        if mic.isNull():
            return self.status(self.t("no_microphone"))

        self.set_busy(True)

        # Create devices and recorder for video session
        self.capture_session = QMediaCaptureSession(self)
        self.camera = QCamera(camera)
        self.camera_audio = QAudioInput(mic)
        self.recorder = QMediaRecorder()

        # capture session to its inputs and preview
        self.capture_session.setCamera(self.camera)
        self.capture_session.setAudioInput(self.camera_audio)
        self.capture_session.setRecorder(self.recorder)
        self.capture_session.setVideoOutput(self.video_widget)

        # video format and handle recording errors
        self.recorder.setMediaFormat(QMediaFormat(QMediaFormat.FileFormat.MPEG4))
        self.recorder.setQuality(QMediaRecorder.Quality.NormalQuality)
        self.recorder.errorOccurred.connect(self.video_error)

        # timestamped path for the video recording
        path = RECORDINGS / f"video_{datetime.now():%Y%m%d_%H%M%S}.mp4"
        self.video_file = str(path)
        self.video_local = True

        # recording to its output file and show the preview
        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))
        self.video_stack.setCurrentWidget(self.video_widget)

        # Start camera before recording the video
        self.camera.start()
        self.recorder.record()

        # Reset timer and mark video recording as active
        self.video_recording = True
        self.recording_mode = "video"
        self.elapsed = 0

        # video time status buttong
        self.video_time.setText("00:00")
        self.video_status.setText(self.t("recording"))
        self.video_button.setText(self.t("stop_video"))

        # video play button
        self.video_play.setEnabled(False)
        self.audio_button.setEnabled(False)
        self.timer.start(1000)
        self.capture_status.hide()

    # Stop recording and wait for the video file to finish
    def stop_video(self, discard=False):
        self.timer.stop()
        self.video_recording = False
        self.recording_mode = ""

        # Remember whether this recording should be discarded
        self.video_discard = discard

        # stop recording
        if self.camera:
            self.camera.stop()

        # Detach live preview before releasing the capture session
        if self.capture_session:
            self.capture_session.setVideoOutput(None)

        if self.recorder:
            # Wait recorder to finish before using the file
            self.recorder.recorderStateChanged.connect(self.video_stopped)
            self.recorder.stop()

    # Prepare or discard finished video
    def video_stopped(self, state):
        # Wait until recorder has fully stopped
        if state != QMediaRecorder.RecorderState.StoppedState:
            return

        # path and discard
        path = self.video_file
        discard = self.video_discard

        # Release recording objects and re-enable audio controls
        self.recorder = None
        self.camera = None
        self.camera_audio = None
        self.capture_session = None
        self.audio_button.setEnabled(True)

        # Handle recording that should be discarded
        if discard:
            self.release_players()

            # delete a file created by the app
            if self.video_local and path:
                Path(path).unlink(missing_ok=True)

            # clear video and set busy
            self.clear_video()
            self.set_busy(False)
            return

        # video status, button and play
        self.video_status.setText(self.t("video_recorded"))
        self.video_button.setText(self.t("record_again"))
        self.video_play.setEnabled(True)

        # Allow video file to settle before preview and transcription
        QTimer.singleShot(250, lambda: self.show_video(path))
        QTimer.singleShot(500, lambda: self.start_transcription(path, "video"))

    # Handle video recording error
    def video_error(self, *args):
        self.status(self.t("video_failed"))
        self.stop_video(True)

    # Start or stop audio recording
    def toggle_audio(self):
        self.stop_audio() if self.audio_recording else self.start_audio()

    # Start recording from the microphone
    def start_audio(self):
        # start after the old recordings can be cleared
        if not self.reset_recordings():
            return

        # mic
        mic = QMediaDevices.defaultAudioInput()

        # if mic null no microphone
        if mic.isNull():
            return self.status(self.t("no_microphone"))

        # Start microphone using its preferred audio format
        self.audio_format = mic.preferredFormat()
        self.audio_source = QAudioSource(mic, self.audio_format, self)
        self.audio_device = self.audio_source.start()

        # Check whether microphone could be started
        if self.audio_device is None:
            return self.status(self.t("microphone_failed"))

        self.set_busy(True)

        # Clear sample buffer and listen for incoming audio
        self.audio_pcm = bytearray()
        self.audio_device.readyRead.connect(self.read_audio)

        # Reset timer and mark audio recording as active
        self.audio_recording = True
        self.recording_mode = "audio"
        self.elapsed = 0

        # audio time, status and button
        self.audio_time.setText("00:00")
        self.audio_status.setText(self.t("recording"))
        self.audio_button.setText(self.t("stop_audio"))

        # audio play button 
        self.audio_play.setEnabled(False)
        self.video_button.setEnabled(False)
        self.timer.start(1000)
        self.capture_status.hide()

    #microphone samples and update the waveform
    def read_audio(self):
        # decode the available microphone samples
        raw = bytes(self.audio_device.readAll())
        samples = self.decode_audio(raw)
        # if not samples return
        if not samples:
            return

        # Measure audio loudness and update the waveform
        rms = math.sqrt(sum(x * x for x in samples) / len(samples))
        self.waveform.add_level(min(1, rms * 4.5))

        # Clamp and store samples as signed 16 bit audio
        for sample in samples:
            value = int(max(-1, min(1, sample)) * 32767)
            self.audio_pcm.extend(struct.pack("<h", value))

    # Convert microphone bytes to mono samples
    def decode_audio(self, raw):
        # sample format and channel count
        fmt = self.audio_format.sampleFormat()
        channels = max(1, self.audio_format.channelCount())
        # byte order of the current computer
        endian = "<" if sys.byteorder == "little" else ">"

        # Map each sample format to its size and scaling
        formats = {
            QAudioFormat.SampleFormat.Int16: (2, "h", 32768.0),
            QAudioFormat.SampleFormat.Int32: (4, "i", 2147483648.0),
            QAudioFormat.SampleFormat.Float: (4, "f", 1.0)
        }

        # Handle unsigned 8 bit samples separately
        if fmt == QAudioFormat.SampleFormat.UInt8:
            values = [(x - 128) / 128 for x in raw]
        else:
            size, code, scale = formats[fmt]
            # unpack complete samples and scale their values
            usable = len(raw) - len(raw) % size
            values = [x[0] / scale for x in struct.iter_unpack(endian + code, raw[:usable])]

        # Keep mono audio as it is
        if channels == 1:
            return values

        # Average complete channel groups into mono samples
        usable = len(values) - len(values) % channels
        return [sum(values[i:i + channels]) / channels for i in range(0, usable, channels)]

    # Stop and save or discard the audio recording
    def stop_audio(self, discard=False):
        self.timer.stop()

        # if audio source stop
        if self.audio_source:
            self.audio_source.stop()

        # audio recording false
        self.audio_recording = False
        self.recording_mode = ""
        self.video_button.setEnabled(True)

        # Discard audio when requested or when nothing was recorded
        if discard or not self.audio_pcm:
            self.clear_audio()
            self.set_busy(False)

        else:
            # timestamped path for the audio recording
            path = RECORDINGS / f"audio_{datetime.now():%Y%m%d_%H%M%S}.wav"

            # mono samples to a WAV file
            with wave.open(str(path), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(self.audio_format.sampleRate())
                f.writeframes(bytes(self.audio_pcm))

            # saved audio path and mark it as app owned
            self.audio_file = str(path)
            self.audio_local = True

            # audio status, button and play
            self.audio_status.setText(self.t("audio_recorded"))
            self.audio_button.setText(self.t("record_again"))
            self.audio_play.setEnabled(True)

            # replay levels before starting transcription
            self.prepare_waveform(str(path))
            self.start_transcription(str(path), "audio")

        # microphone references and clear the sample buffer
        self.audio_source = self.audio_device = self.audio_format = None
        self.audio_pcm = bytearray()

    # Update timer and stop at one minute
    def update_time(self):
        # Update recording time in minutes and seconds
        self.elapsed += 1
        text = f"{self.elapsed // 60:02d}:{self.elapsed % 60:02d}"

        # if recording more in video
        if self.recording_mode == "video":
            self.video_time.setText(text)
        else:
            self.audio_time.setText(text)

        # Stop recording after one minute
        if self.elapsed >= 60:
            self.stop_video() if self.recording_mode == "video" else self.stop_audio()

    # Stop playback and release media files
    def release_players(self):
        self.video_player.stop()
        self.video_player.setSource(QUrl())
        self.video_player.setVideoOutput(None)
        self.audio_player.stop()
        self.audio_player.setSource(QUrl())

    # Show play or pause icon
    def set_play_icon(self, btn, playing):
        btn.setText("")
        btn.setIcon(self.pause_icon if playing else self.play_icon)

    # Play or pause the selected video
    def toggle_video_play(self):
        # Pause the video if it is already playing
        if self.video_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return self.video_player.pause()

        # audio player stop
        self.audio_player.stop()
        self.video_player.setVideoOutput(self.video_widget)
        self.video_player.setSource(QUrl.fromLocalFile(self.video_file))
        self.video_stack.setCurrentWidget(self.video_widget)
        self.video_player.play()

    #preview of the selected video
    def show_video(self, path):
        self.video_player.setVideoOutput(self.video_widget)
        self.video_player.setSource(QUrl.fromLocalFile(path))
        self.video_stack.setCurrentWidget(self.video_widget)
        self.video_player.play()
        # Pause shortly after preview starts
        QTimer.singleShot(450, self.video_player.pause)

    # Update video playback icon
    def video_state(self, state):
        self.set_play_icon(self.video_play,state == QMediaPlayer.PlaybackState.PlayingState,)

    # Play or pause selected audio
    def toggle_audio_play(self):
        # Pause audio if it is already playing
        if self.audio_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return self.audio_player.pause()

        # video player stop
        self.video_player.stop()
        self.audio_player.setSource(QUrl.fromLocalFile(self.audio_file))
        self.audio_player.play()

    # Update audio icon and waveform
    def audio_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.set_play_icon(self.audio_play, playing)

        # Clear waveform when playback is not active
        if not playing:
            self.waveform.clear()

    # recording length in minutes and seconds
    @staticmethod
    def set_duration(widget, ms):
        if ms > 0:
            seconds = ms // 1000
            widget.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")

    # Prepare audio levels for the replay waveform
    def prepare_waveform(self, path):
        # Load audio as mono at 16000 samples per second
        audio, _ = librosa.load(path, sr=16000, mono=True)
        # Measure and scale loudness values for the replay waveform
        levels = librosa.feature.rms(y=audio)[0].tolist()
        maximum = max(levels) if levels else 1
        self.audio_levels = [x / maximum for x in levels]

    # waveform to playback position
    def sync_waveform(self, position):
        if not self.audio_levels:
            return

        # playback position to a valid waveform sample
        duration = max(1, self.audio_player.duration())
        index = min(len(self.audio_levels) - 1,int(position / duration * len(self.audio_levels)),)
        self.waveform.add_level(self.audio_levels[index])

    # Choose and prepare an uploaded recording
    def open_upload(self):
        # Wait if transcript is already being created
        if self.transcription_worker and self.transcription_worker.isRunning():
            return self.status(self.t("wait_transcript"))

        # dialog for upload
        dialog = UploadDialog(self.current_language, self)

        # Stop if the upload dialog was cancelled
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # reset recordings
        if self.reset_recordings() is False:
            return
        path = dialog.selected_path

        # Show the selected recording tab before processing
        self.capture_tabs.setCurrentIndex(1 if dialog.selected_type == "audio" else 0)

        # Prepare uploaded audio file
        if dialog.selected_type == "audio":
            self.audio_file = path
            # Keep uploaded audio marked as user owned
            self.audio_local = False
            self.audio_status.setText(f"{self.t('uploaded')}: {Path(path).name}")
            self.audio_button.setText(self.t("record_instead"))
            self.audio_play.setEnabled(True)
            self.video_button.setEnabled(False)
            # Start transcription in the existing background worker
            self.start_transcription(path, "audio")

        else:
            self.video_file = path
            # Keep uploaded video marked as user owned
            self.video_local = False
            self.video_status.setText(f"{self.t('uploaded')}: {Path(path).name}")
            self.video_button.setText(self.t("record_instead"))
            self.video_play.setEnabled(True)
            self.audio_button.setEnabled(False)
            self.show_video(path)
            self.start_transcription(path, "video")

    # transcript in the background
    def start_transcription(self, path, recording_type):
        # Disable submission and clear the old transcript while working
        self.set_busy(True)
        self.submit_button.setEnabled(False)
        self.transcript.clear()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(self.t("creating_transcript"))

        # Start transcription and connect progress, result and error signals
        self.transcription_worker = TranscriptionWorker(path,recording_type,self,language_name=self.current_language,)
        self.transcription_worker.progress.connect(lambda key: self.transcript.setPlaceholderText(self.t(key)))
        self.transcription_worker.completed.connect(self.transcription_done)
        self.transcription_worker.failed.connect(self.transcription_failed)

        # exact worker reference for safe cleanup
        worker = self.transcription_worker
        worker.finished.connect(lambda w=worker: self.worker_finished("transcription_worker", w))
        self.transcription_worker.start()

    # transcript and allow corrections
    def transcription_done(self, text):
        # transcript and allow corrections before submission
        self.transcript.setPlainText(text)
        self.transcript.setReadOnly(False)
        self.submit_button.setEnabled(True)
        self.set_busy(False)

    # Show why transcription could not finish
    def transcription_failed(self, message):
        # Clear unusable text and explain the transcription failure
        self.transcript.clear()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(self.t("transcript_unavailable"))
        self.submit_button.setEnabled(False)
        self.status(self.t("transcription_failed"))
        # show failure details
        self.show_failure_details("transcription_failed", message)
        self.set_busy(False)

    # input and start the analysis
    def submit_check_in(self):
        # Require recording to stop before submission
        if self.video_recording or self.audio_recording:
            return self.status(self.t("stop_before_submit"))

        # Require an audio or video file
        if not self.video_file and not self.audio_file:
            return self.status(self.t("record_first"))

        # current transcript to finish
        if self.transcription_worker and self.transcription_worker.isRunning():
            return self.status(self.t("wait_transcript"))

        # corrected transcript without surrounding spaces
        text = self.transcript.toPlainText().strip()

        # if no text transcript is required
        if not text:
            return self.status(self.t("transcript_required"))

        # available recording and its media type
        path = self.video_file or self.audio_file
        recording_type = "video" if self.video_file else "audio"

        # previous score for recommendation context
        previous = get_recent_scores(self.user_id, 1)
        previous_score = previous[-1] if previous else None

        # short note about the previous score
        trend = (
            f"Previous wellbeing score: {previous_score:.0f}/100."
            if previous_score is not None
            else "No previous check-in trend is available."
        )

        # release players
        self.release_players()

        # Switch to processing view and start the spinner
        self.processing_key = "processing_loading"
        self.processing_message.setText(self.t(self.processing_key))
        self.stack.setCurrentWidget(self.processing_page)
        self.spinner.start()

        # analysis worker and connect its result handlers
        self.analysis_worker = AnalysisWorker(path,recording_type,text,self,language_name=self.current_language,trend=trend)
        self.analysis_worker.progress.connect(self.analysis_progress)
        self.analysis_worker.completed.connect(self.analysis_done)
        self.analysis_worker.failed.connect(self.analysis_failed)
        self.set_busy(True)

        # Keep exact analysis worker reference for cleanup
        worker = self.analysis_worker
        worker.finished.connect(lambda w=worker: self.worker_finished("analysis_worker", w))
        self.analysis_worker.start()

    # current analysis step
    def analysis_progress(self, key):
        self.processing_key = key
        self.processing_message.setText(self.t(key))

    # Save finished check in and show its results
    def analysis_done(self, result):
        self.spinner.stop()

        try:
            # Read previous score before choosing the new summary
            previous = get_recent_scores(self.user_id, 1)
            previous_score = previous[-1] if previous else None
            score = round(result["wellbeing_score"])
    
            # Choose result wording and image from the score change
            phrase_key, explanation_key, image = self.result_text(score, previous_score)

            # Compare new strain score with personal baseline
            baseline = self.baseline_status(result["strain_score"])
            result["phrase"] = self.t(phrase_key)
            result["explanation"] = self.t(explanation_key)
    
            # English summary text for the saved history
            result["phrase_english"] = ENGLISH_TEXT[phrase_key]
            result["explanation_english"] = ENGLISH_TEXT[explanation_key]
            result["image_name"] = image
            result["baseline"] = baseline
    
            # completed check in for this user
            save_check_in(self.user_id, result)
            # remove only recordings created by the app after saving
            for f, owned in ((self.video_file, self.video_local), (self.audio_file, self.audio_local)):
                if f and owned:
                    try:
                        Path(f).unlink(missing_ok=True)
                    # Allow cleanup to continue if a file cannot be removed
                    except OSError:
                        pass
    
            # result view and restore navigation
            self.populate_result(result)
            self.stack.setCurrentWidget(self.result_page)
            self.set_busy(False)

        # error
        except Exception as error:
            self.analysis_failed(str(error))

    # failure and return to the recording page
    def analysis_failed(self, message):
        # Report failure and return to the recording view
        print("ANALYSIS ERROR:", message)

        # show the status 
        self.spinner.stop()
        self.stack.setCurrentWidget(self.capture_page)
        self.status(self.t("analysis_failed"))
        self.show_failure_details("analysis_failed", message)

        # Restore video preview when one is available
        if self.video_file:
            self.show_video(self.video_file)

        self.set_busy(False)

    # summary wording and image
    def result_text(self, score, previous):
        # first check in wording when there is no previous score
        if previous is None:
            if score >= 67:
                keys = "first_high_phrase", "first_high_text", "wellbeing_high.png"
            elif score >= 34:
                keys = "first_mid_phrase", "first_mid_text", "wellbeing_mid.png"
            else:
                keys = "first_low_phrase", "first_low_text", "wellbeing_low.png"

        # improvement after a rise of at least five points
        elif score - previous >= 5:
            keys = "improved_phrase", "improved_text", "wellbeing_high.png"

        # lower result after a fall of at least five points
        elif score - previous <= -5:
            keys = "lower_phrase", "lower_text", "wellbeing_low.png"

        else:
            keys = "steady_phrase", "steady_text", "wellbeing_mid.png"

        return keys[0], keys[1], keys[2]
    

    # Compare strain with the previous seven check-ins
    def baseline_status(self, strain_score):
        # Load previous seven strain scores
        previous_scores = get_previous_strain_scores(self.user_id, 7)
        label = classify_baseline(strain_score, previous_scores)
        return self.t(label) if label else None
        
    # result page with the check in details
    def populate_result(self, result):
        score = round(result["wellbeing_score"])

        # Load and scale the image chosen for this result
        pixmap = QPixmap(str(IMAGES / result["image_name"]))
        self.result_image.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.result_phrase.setText(result["phrase"])
        explanation_text = result["explanation"]

        # Add baseline message when enough history is available
        if result.get("baseline"):
            self.result_explanation.setTextFormat(Qt.RichText)
            self.result_explanation.setText(
                f"{explanation_text}<br>"
                f"Baseline level: <b>{result['baseline']}</b>"
            )
        else:
            # result explanation
            self.result_explanation.setTextFormat(Qt.PlainText)
            self.result_explanation.setText(explanation_text)

        # Update displayed score and its colour range
        self.score.setValue(score)
        self.score.setFormat(f"{score} / 100")
        self.score.setProperty("zone", "high" if score >= 67 else "mid" if score >= 34 else "low")
        self.score.style().unpolish(self.score)
        self.score.style().polish(self.score)

        # set signals and recommendations
        self.set_signals(result)
        self.set_recommendations(result["recommendation"])

    # available supporting signals
    def set_signals(self, result):
        na = self.t("not_available")

        # Match head positions to translated descriptions
        heads = {
            "Centred": self.t("head_centred"),
            "Slightly off-centre": self.t("head_slightly_off"),
            "Off-centre": self.t("head_off"),
        }

        # blink and head
        blink = result.get("blink_rate")
        head = result.get("head_position")

        # Format supporting signal for display
        values = {
            "blink_rate": f"{blink:.1f}/min" if blink is not None else na,
            "head_position": heads.get(head, na),
            "speech_rate": f"{result['speech_rate']:.0f}/min",
            "disfluency": f"{result['disfluency_rate'] * 100:.1f}%",
            "lexical_variety": f"{result['lexical_variety']:.2f}",
        }

        # signal value key and value
        for key, value in values.items():
            self.signal_values[key].setText(value)

    # Remove widgets from a layout
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                # delete later
                item.widget().deleteLater()
            elif item.layout():
                # clear layout
                self._clear_layout(item.layout())

    # Turn recommendations into separate cards
    def set_recommendations(self, text):
        # Clear previous recommendation cards
        self._clear_layout(self.rec_layout)

        # tones
        tones = ["", "mint", "sand"]
        row = QHBoxLayout()
        row.setSpacing(14)
        index = 0

        # Split numbered recommendation text into cards
        for chunk in re.split(r"(?=\b[1-3][.)]\s*)", text):
            chunk = chunk.strip().replace("**", "")
            if not chunk:
                continue

            # Remove leading recommendation number
            body = re.sub(r"^[1-3][.)]\s*", "", chunk)

            # Cycle through the card colour themes
            tone = tones[index % len(tones)]

            # Create each recommendation card with its colour theme
            card = QFrame()
            card.setObjectName("recCard")
            card.setAttribute(Qt.WA_StyledBackground, True)
            card.setProperty("tone", tone)
            card.setMinimumHeight(170)

            # inside
            inside = QVBoxLayout(card)
            inside.setContentsMargins(22, 22, 22, 22)
            inside.setSpacing(14)

            # numbered badge for this recommendation
            number = QLabel(f"{index + 1}")
            number.setObjectName("recCardNumber")
            number.setProperty("tone", tone)
            number.setFixedSize(44, 44)
            number.setAlignment(Qt.AlignCenter)

            # text label
            text_label = QLabel(body)
            text_label.setObjectName("recCardText")
            text_label.setWordWrap(True)
            text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

            # inside
            inside.addStretch()
            inside.addWidget(number, 0, Qt.AlignHCenter)
            inside.addWidget(text_label)
            inside.addStretch()

            # tamil font small size
            if self.current_language == "Tamil":
                text_label.setStyleSheet("font-size:13px;")

            # row add widget
            row.addWidget(card, 1)
            index += 1

        # record layout
        self.rec_layout.addLayout(row)

    # Get text in the selected language
    def t(self, key):
        return get_text(self.current_language, key)

    # Update the page for the selected language
    def set_language(self, language):
        self.current_language = language
        self.sidebar.set_language(language)

        # Match check in controls to their translated wording
        texts = {
            self.capture_title: "record_check_in",
            self.capture_subtitle: "record_instruction",
            self.video_title: "video_check_in",
            self.camera_off: "camera_off",
            self.audio_title: "audio_check_in",
            self.audio_note: "audio_note",
            self.transcript_title: "automatic_transcript",
            self.transcript_note: "transcript_note",
            self.upload_button: "upload",
            self.delete_button: "delete",
            self.submit_button: "submit",
            self.processing_title: "processing_title",
            self.processing_note: "processing_note",
            self.result_title: "wellbeing_summary",
            self.result_subtitle: "experimental_note",
            self.summary_note: "summary_note",
            self.score_label: "wellbeing_score",
            self.score_note: "score_caveat",
            self.signals_title: "supporting_signals",
            self.rec_title: "supportive_recommendations",
            self.rec_note: "qwen_note",
            self.done_note: "saved_history",
            self.done_button: "done",
        }

        # set text
        for w, key in texts.items():
            w.setText(self.t(key))

        # Update translated labels on the page
        for key, w in self.signal_names.items():
            w.setText(self.t(key))

        # processing message
        self.processing_message.setText(self.t(self.processing_key))

        # Restore empty transcript hint when no text is present
        if not self.transcript.toPlainText():
            self.transcript.setPlaceholderText(self.t("transcript_placeholder"))

        # refresh recording text
        self.refresh_recording_text()
        self.video_note.setText(self.t("video_position_note"))

        # capture tabs
        self.capture_tabs.setTabText(0, self.t("video_tab"))
        self.capture_tabs.setTabText(1, self.t("audio_tab"))
        self.capture_tabs.setTabToolTip(0, self.t("capture_tab_note"))
        self.capture_tabs.setTabToolTip(1, self.t("capture_tab_note"))

        # tamil fonts
        self.tamil_fonts()

    # Update recording labels for the current state
    def refresh_recording_text(self):
        if self.video_recording:
            self.video_status.setText(self.t("recording"))
            self.video_button.setText(self.t("stop_video"))

        # video file status and button 
        elif self.video_file:
            self.video_status.setText(self.t("video_recorded") if self.video_local else f"{self.t('uploaded')}: {Path(self.video_file).name}")
            self.video_button.setText(self.t("record_again") if self.video_local else self.t("record_instead"))

        # not recorded status and button
        else:
            self.video_status.setText(self.t("not_recorded"))
            self.video_button.setText(self.t("start_video"))

        # audio recording status and button
        if self.audio_recording:
            self.audio_status.setText(self.t("recording"))
            self.audio_button.setText(self.t("stop_audio"))

        # audio recording status and button record again
        elif self.audio_file:
            self.audio_status.setText(self.t("audio_recorded") if self.audio_local else f"{self.t('uploaded')}: {Path(self.audio_file).name}")
            self.audio_button.setText(self.t("record_again") if self.audio_local else self.t("record_instead"))

        # not recorded status and button
        else:
            self.audio_status.setText(self.t("not_recorded"))
            self.audio_button.setText(self.t("start_audio"))

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"
        # widgets
        widgets = [
            (self.capture_title, 18), (self.capture_subtitle, 10),
            (self.video_title, 12),
            (self.audio_title, 12), (self.audio_note, 9),
            (self.transcript_title, 12), (self.transcript_note, 9),
            (self.transcript, 10), (self.video_button, 10),
            (self.audio_button, 10), (self.upload_button, 10),
            (self.delete_button, 10), (self.submit_button, 10),
            (self.processing_title, 18), (self.processing_message, 11),
            (self.processing_note, 10), (self.result_title, 18),
            (self.result_subtitle, 10), (self.result_phrase, 21),
            (self.result_explanation, 11), (self.signals_title, 12),
            (self.rec_title, 12), (self.rec_note, 9),
            (self.done_note, 9), (self.done_button, 10),
        ]

        # font size for tamil small
        for w, size in widgets:
            w.setStyleSheet(f"font-size:{max(size, 12)}px;" if tamil else "")

        # user labels font size small
        for w in self.user_labels:
            w.setStyleSheet("font-size:11px;" if tamil else "")

        # signal names font size small
        for w in list(self.signal_names.values()) + list(self.signal_values.values()):
            w.setStyleSheet("font-size:12px;" if tamil else "")

        # extra recording button width for Tamil
        record_width = 200 if tamil else 150
        self.video_button.setFixedWidth(record_width)
        self.audio_button.setFixedWidth(record_width)

    # recording status message
    def status(self, text):
        self.capture_status.setText(text)
        self.capture_status.show()
        self.status_timer.start(4000)   # gone again after 4 seconds

    # Reset video controls
    def clear_video(self):
        self.video_file = ""
        self.video_local = False
        self.video_status.setText(self.t("not_recorded"))
        self.video_time.setText("00:00")
        self.video_button.setText(self.t("start_video"))
        self.video_play.setEnabled(False)
        self.set_play_icon(self.video_play, False)
        self.video_stack.setCurrentIndex(0)

    # Reset audio controls
    def clear_audio(self):
        self.audio_file = ""
        self.audio_local = False
        self.audio_status.setText(self.t("not_recorded"))
        self.audio_time.setText("00:00")
        self.audio_button.setText(self.t("start_audio"))
        self.audio_play.setEnabled(False)
        self.audio_levels = []
        self.waveform.clear()
        self.set_play_icon(self.audio_play, False)

    # Clear recordings and reset input controls
    def reset_recordings(self):
        # Wait for transcription before clearing recording
        if self.transcription_worker and self.transcription_worker.isRunning():
            self.status(self.t("wait_transcript"))
            return False

        # release players
        self.release_players()

        # finished video only if the app owns it
        old_video = self.video_file if self.video_local and not self.video_recording else ""
        old_audio = self.audio_file if self.audio_local and not self.audio_recording else ""

        # Stop and discard any active video recording
        if self.video_recording:
            self.stop_video(True)

        # Stop and discard any active audio recording
        if self.audio_recording:
            self.stop_audio(True)

        # Delete old video only when the app owns it
        if old_video:
            Path(old_video).unlink(missing_ok=True)

        # Delete old audio only when the app owns it
        if old_audio:
            Path(old_audio).unlink(missing_ok=True)

        # clear video and audio
        self.clear_video()
        self.clear_audio()

        # video button and audio button
        self.video_button.setEnabled(True)
        self.audio_button.setEnabled(True)

        # Reset transcript and disable submission after clearing
        self.transcript.clear()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(self.t("transcript_placeholder"))

        # submit button and capture status
        self.submit_button.setEnabled(False)
        self.capture_status.hide()
        return True

    # Set user shown on this page
    def set_user(self, full_name, user_id=None):
        first = full_name.split()[0] if full_name else ""
        # user label text
        for w in self.user_labels:
            w.setText(first)

        self.user_id = user_id

    # Return to recording page when no analysis is running
    def reset_page(self):
        # Wait until analysis finishes before resetting the page
        if self.analysis_worker and self.analysis_worker.isRunning():
            return False

        # if not reset recording return false
        if not self.reset_recordings():
            return False

        # set current widgets
        self.stack.setCurrentWidget(self.capture_page)
        return True

    # Return to the recording page but keep the current recording
    def resume_page(self):
        # Do not disturb the page while analysis is still running
        if self.analysis_worker and self.analysis_worker.isRunning():
            return False
        # After a finished check-in start fresh, otherwise keep the recording
        if self.stack.currentWidget() is self.result_page:
            return self.reset_page()
        self.stack.setCurrentWidget(self.capture_page)
        return True

    # Return to home page
    def finish(self):
        self.home_requested.emit()

    # Show dialog with the error details
    def show_failure_details(self, key, message):
        # Show error in a message dialog
        dialog = QMessageBox(self)
        dialog.setWindowTitle(self.t(key))
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText(self.t(key))

        # Keep short explanation readable and retain full details
        dialog.setInformativeText(str(message)[:800] or "No error details were returned.")
        dialog.setDetailedText(str(message))
        dialog.exec()

    # Release finished background worker
    def worker_finished(self, attribute, worker):
        # Only clear the reference if it still points to this worker
        if getattr(self, attribute, None) is worker:
            setattr(self, attribute, None)
        worker.deleteLater()