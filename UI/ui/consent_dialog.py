# Import required libraries
from pathlib import Path
from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout
from UI.ui.translations import ENGLISH_TEXT, get_text

# Locate the project folder
ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "UI" / "images"

# English privacy and consent wording
CONSENT_TEXT = {
    "consent_window": "Disclaimer and consent",
    "consent_title": "Before you continue",
    "consent_subtitle": "Please read this information before using Solace.",
    "disclaimer_main":"Solace is a wellbeing support tool, not a medical diagnostic service.",
    "disclaimer_ai":
        "During a check-in, Solace may analyse text, voice and facial-expression "
        "signals together with supporting signals such as blink rate, head position, "
        "speech rate, disfluency and lexical variety. AI results may be inaccurate "
        "and should not replace advice from a qualified healthcare professional.",

    "disclaimer_privacy":
        "Your account and saved check-in history are stored locally on this device. "
        "You choose whether to use audio or video for each check-in.",

    "disclaimer_emergency":
        "Solace is not an emergency service. Seek immediate professional or emergency "
        "support if you or another person may be in danger.",

    "consent_checkbox":"I have read and understood the information above, and I consent to continue.",
    "consent_agree": "I agree and continue",
    "consent_decline": "I do not agree",
    "thank_you_title": "Thank you for visiting",
    "thank_you_message":"You need to accept the disclaimer before using Solace."
}

# consent wording available to the translation system
ENGLISH_TEXT.update(CONSENT_TEXT)

# heart image label
def heart_image(size):
    heart = QLabel()
    heart.setFixedSize(size, size)
    heart.setAlignment(Qt.AlignCenter)
    # heart image smoothly inside its label
    heart.setPixmap(QPixmap(str(IMAGES / "heart.png")).scaled(size - 8,size - 8,Qt.KeepAspectRatio,Qt.SmoothTransformation,))
    return heart

# privacy information and collect consent
class ConsentDialog(QDialog):
    def __init__(self,parent=None,initial_language="English",view_only=False,):
        super().__init__(parent)

        # chosen language and whether consent is view only
        self.selected_language = initial_language
        self.view_only = view_only

        # modal card without the normal window frame
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # read only privacy dialog to fit its contents
        self.setFixedWidth(680)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_consent_page())

        # layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(self.stack)
        self.show_consent()

        # Fit the dialog height to its contents
        self.ensurePolished()
        self.layout().activate()
        content_height = self.layout().totalHeightForWidth(self.width())

        if content_height > 0:
            self.setFixedHeight(content_height)
        else:
            self.adjustSize()

    # Build consent page
    def build_consent_page(self):
        card = QFrame()
        card.setObjectName("consentCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        # close button using the cross image
        self.close_button = QPushButton()
        self.close_button.setObjectName("consentCloseButton")
        self.close_button.setFixedSize(36, 36)
        self.close_button.setIcon(QIcon(str(IMAGES / "cross.png")))
        self.close_button.setIconSize(QSize(24, 24))
        self.close_button.setStyleSheet("padding: 0px;")
        self.close_button.setAutoDefault(False)
        self.close_button.setToolTip(self.t("resource_close"))
        self.close_button.setAccessibleName(self.t("resource_close"))
        self.close_button.setCursor(Qt.PointingHandCursor)
        # Close the read-only privacy dialog when clicked
        self.close_button.clicked.connect(self.accept)

        # close row
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(self.close_button)

        # Only show cross in read only mode
        self.close_button.setVisible(self.view_only)

        # Create centred heading and introductory text
        self.title = QLabel()
        self.title.setObjectName("consentTitle")
        self.title.setAlignment(Qt.AlignCenter)

        # subtitle
        self.subtitle = QLabel()
        self.subtitle.setObjectName("consentSubtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setWordWrap(True)

        # Highlight the medical disclaimer
        self.medical_notice = QLabel()
        self.medical_notice.setObjectName("medicalDisclaimer")
        self.medical_notice.setWordWrap(True)
        self.medical_notice.setTextFormat(Qt.PlainText)

        # Allow formatted paragraphs in the privacy explanation
        self.disclaimer = QLabel()
        self.disclaimer.setObjectName("disclaimerText")
        self.disclaimer.setWordWrap(True)
        self.disclaimer.setTextFormat(Qt.RichText)

        # Create checkbox used to confirm consent
        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("consentCheckBox")
        self.checkbox.setCursor(Qt.PointingHandCursor)

        # Create decline and agreement buttons
        self.decline = QPushButton()
        self.decline.setObjectName("secondaryButton")
        self.decline.setFixedHeight(48)
        self.decline.setCursor(Qt.PointingHandCursor)
        self.decline.clicked.connect(self.reject)

        # agree
        self.agree = QPushButton()
        self.agree.setObjectName("primaryButton")
        self.agree.setFixedHeight(48)
        self.agree.setCursor(Qt.PointingHandCursor)
        self.agree.setEnabled(False)
        self.agree.clicked.connect(self.accept)

        # Enable agreement only when the checkbox is ticked
        self.checkbox.toggled.connect(self.agree.setEnabled)

        # buttons
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addWidget(self.decline)
        buttons.addWidget(self.agree)

        # Keep consent content closely spaced and aligned at the top
        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 16, 36, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop)
        layout.addLayout(close_row)

        # Add heart image above heading
        heart = heart_image(80)

        # Reduce heart label height in read only mode
        if self.view_only:
            heart.setFixedHeight(44)

        # add widget
        layout.addWidget(heart, 0, Qt.AlignCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.medical_notice)
        layout.addWidget(self.disclaimer)
        layout.addWidget(self.checkbox)
        layout.addLayout(buttons)

        # Hide consent controls when viewing privacy information only
        if self.view_only:
            self.checkbox.hide()
            self.decline.hide()
            self.agree.hide()
            layout.addSpacing(36)

        return card

    # Get text in the selected language
    def t(self, key):
        return get_text(self.selected_language, key)

    # Show consent wording for the current mode
    def show_consent(self):
        # Choose privacy or consent title for the current mode
        self.setWindowTitle(self.t("privacy_settings_title" if self.view_only else "consent_window"))
        self.title.setText(self.t("privacy_settings_title" if self.view_only else "consent_title"))
        self.subtitle.setText(self.t("consent_subtitle"))
        self.checkbox.setText(self.t("consent_checkbox"))
        self.agree.setText(self.t("consent_agree"))
        self.decline.setText(self.t("consent_decline"))

        # Show the main disclaimer in its highlighted box
        self.medical_notice.setText(self.t("disclaimer_main"))

        # Show the remaining privacy information
        self.disclaimer.setText(
            f"<p>{self.t('disclaimer_ai')}</p>"
            f"<p>{self.t('disclaimer_privacy')}</p>"
            f"<p>{self.t('disclaimer_emergency')}</p>"
        )

        # tamil fonts 
        self.tamil_fonts()
        self.stack.setCurrentIndex(0)

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = self.selected_language == "Tamil"

        # Use readable font sizes when Tamil is selected
        widgets = [
            (self.title, 17),
            (self.subtitle, 9),
            (self.medical_notice, 9),
            (self.disclaimer, 9),
            (self.checkbox, 9),
            (self.agree, 9),
            (self.decline, 9)
        ]

        # tamil font size
        for widget, size in widgets:
            widget.setStyleSheet(f"font-size:{max(size, 12)}px;" if tamil else "")


# short message when consent is declined
class ThankYouDialog(QDialog):
    def __init__(self, language="English", parent=None):
        super().__init__(parent)

        # card style for thank you dialog
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(420, 220)

        # card
        card = QFrame()
        card.setObjectName("thankYouCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        # translated title and explanation
        title = QLabel(get_text(language, "thank_you_title"))
        title.setObjectName("thankYouTitle")
        title.setAlignment(Qt.AlignCenter)

        # message
        message = QLabel(get_text(language, "thank_you_message"))
        message.setObjectName("thankYouText")
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)

        # thank you text for Tamil
        if language == "Tamil":
            title.setStyleSheet("font-size:15px;")
            message.setStyleSheet("font-size:12px;")

        # layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 24, 34, 24)
        layout.setSpacing(8)
        layout.addWidget(heart_image(48), 0, Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(message)

        # outer
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(card)

        # thank you dialog after short delay
        QTimer.singleShot(1700, self.accept)