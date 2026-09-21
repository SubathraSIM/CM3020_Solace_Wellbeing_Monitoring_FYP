# Import required libraies
from UI.ui.account_widgets import PasswordEdit
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,QPushButton, QVBoxLayout, QWidget
from UI.ui.ui_components import GardenArtwork, FloatCard
from UI.ui.translations import ENGLISH_TEXT, get_text

# project folder
ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "UI" / "images"

# English wording for the login form
LOGIN_TEXT = {
    "brand_tagline": "WELLBEING WITH CARE",
    "login_title": "Welcome back",
    "login_subtitle": "Sign in to your dashboard",
    "username": "Username",
    "username_placeholder": "Enter your username",
    "password": "Password",
    "password_placeholder": "Enter your password",
    "login_button": "Log in",
    "new_here": "New here?",
    "create_account": "Create account",
    "login_empty": "Please enter your username and password.",
    "login_incorrect": "The username or password is incorrect.",
    "account_created_login": "Account created. You can log in now.",
}

# login wording to shared translations
ENGLISH_TEXT.update(LOGIN_TEXT)

# brand text and garden artwork
class BrandPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('brandPanel')
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Place garden artwork behind the brand text
        self.ecg = GardenArtwork(self)
        name = QLabel('SOLACE'); name.setObjectName('brandName')
        self.tagline = QLabel(); self.tagline.setObjectName('brandTagline'); self.tagline.setWordWrap(True)
        layout = QVBoxLayout(self); layout.setContentsMargins(34,38,34,38)
        layout.addWidget(name); layout.addWidget(self.tagline); layout.addStretch()

    # Update page for the selected language
    def set_language(self, language):
        self.tagline.setText(get_text(language, "brand_tagline"))
        self.tagline.setStyleSheet("font-size:12px;" if language == "Tamil" else "")

    # Update layout when the size changes
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Resize garden artwork to stay behind the brand text
        self.ecg.setGeometry(self.rect())
        self.ecg.lower()

# login form and language selector
class LoginPage(QWidget):
    language_changed = Signal(str)

    def __init__(self):
        super().__init__()
        # page in English
        self.current_language = "English"

        # language selector
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("loginLanguageCombo")
        self.language_combo.setFixedHeight(36)
        self.language_combo.setCursor(Qt.PointingHandCursor)
        self.language_combo.setToolTip("Language")
        self.language_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        # four supported interface languages
        self.language_combo.addItem("English", "English")
        self.language_combo.addItem("Malay", "Malay")
        self.language_combo.addItem("Chinese", "Chinese")
        self.language_combo.addItem("Tamil", "Tamil")

        # language change when the selection changes
        self.language_combo.currentIndexChanged.connect(self.language_selected)

        # card shared by the brand and login form
        card = QFrame()
        card.setObjectName("appCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setFixedSize(940, 630)

        # brand area and login fields side by side
        self.brand = BrandPanel()
        form = self.build_form()

        # card layout
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card_layout.addWidget(self.brand, 47)
        card_layout.addWidget(form, 53)

        # Wrap card so it can animate into place
        self.card_host = FloatCard(card)

        # row
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.card_host)
        row.addStretch()

        # Place language selector below the main card
        language_row = QHBoxLayout()
        language_row.setContentsMargins(0, 0, 0, 0)
        language_row.addStretch()
        language_row.addWidget(self.language_combo)

        # layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        layout.addLayout(language_row)

        self.set_language("English")

    # Build form
    def build_form(self):
        panel = QFrame()
        panel.setObjectName("formPanel")
        panel.setAttribute(Qt.WA_StyledBackground, True)

        # heading
        self.heading = QLabel()
        self.heading.setObjectName("formTitle")

        # subtitle
        self.subtitle = QLabel()
        self.subtitle.setObjectName("formSubtitle")
        self.subtitle.setWordWrap(True)

        # status icon shown beside the message
        self.status_icon = QLabel()
        self.status_icon.setObjectName("statusIcon")
        self.status_icon.setScaledContents(True)

        # status message text
        self.status_label = QLabel()
        self.status_label.setObjectName("statusMessage")
        self.status_label.setWordWrap(True)

        # icon and message in one row show hide as a unit
        self.status_row = QWidget()
        self.status_row.setObjectName("statusRow")
        self.status_row.setAttribute(Qt.WA_StyledBackground, True)
        status_row_layout = QHBoxLayout(self.status_row)
        status_row_layout.setContentsMargins(0, 0, 0, 0)
        status_row_layout.setSpacing(8)
        status_row_layout.addWidget(self.status_icon)
        status_row_layout.addWidget(self.status_label, 1)
        self.status_row.setMinimumHeight(42)
        self.status_row.hide()

        # Create username label and input field
        self.username_label = QLabel()
        self.username_label.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setFixedHeight(50)

        # username label to its input field
        self.username_label.setBuddy(self.username_input)

        # password label
        self.password_label = QLabel()
        self.password_label.setObjectName("fieldLabel")

        # Use password field with a visibility toggle
        self.password_input = PasswordEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(50)

        # Link password label to its input field
        self.password_label.setBuddy(self.password_input)

        # Create login button
        self.login_button = QPushButton()
        self.login_button.setObjectName("primaryButton")
        self.login_button.setFixedHeight(48)
        self.login_button.setCursor(Qt.PointingHandCursor)

        # Create button for opening registration
        self.register_button = QPushButton()
        self.register_button.setObjectName("secondaryButton")
        self.register_button.setFixedHeight(48)
        self.register_button.setCursor(Qt.PointingHandCursor)

        # Enter in the password field to trigger login
        self.password_input.returnPressed.connect(self.login_button.click)

        # divider between login and registration
        self.divider_label = QLabel()
        self.divider_label.setObjectName("dividerLabel")
        self.divider_label.setAlignment(Qt.AlignCenter)

        # left line
        left_line = QFrame()
        left_line.setObjectName("dividerLine")
        left_line.setFixedHeight(1)

        # right line
        right_line = QFrame()
        right_line.setObjectName("dividerLine")
        right_line.setFixedHeight(1)

        # divider
        divider = QHBoxLayout()
        divider.addWidget(left_line, 1)
        divider.addWidget(self.divider_label)
        divider.addWidget(right_line, 1)

        # Arrange login fields and actions with consistent gaps
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(44, 30, 44, 30)
        layout.addStretch()
        layout.addWidget(self.heading)
        layout.addSpacing(6)
        layout.addWidget(self.subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.status_row)
        layout.addSpacing(14)
        layout.addWidget(self.username_label)
        layout.addSpacing(5)
        layout.addWidget(self.username_input)
        layout.addSpacing(14)
        layout.addWidget(self.password_label)
        layout.addSpacing(5)
        layout.addWidget(self.password_input)
        layout.addSpacing(20)
        layout.addWidget(self.login_button)
        layout.addSpacing(16)
        layout.addLayout(divider)
        layout.addSpacing(16)
        layout.addWidget(self.register_button)
        layout.addStretch()

        # return panel
        return panel

    # Apply language selected in menu
    def language_selected(self):
        # language selected in the menu
        language = self.language_combo.currentData()

        # if not language return
        if not language:
            return

        # clear old messages before applying new language
        self.clear_status()
        self.set_language(language)
        self.language_changed.emit(language)

    # room for selected language name
    def resize_language_combo(self):
        # width of selected language name
        text_width = self.language_combo.fontMetrics().horizontalAdvance(self.language_combo.currentText())
        self.language_combo.setFixedWidth(max(140, text_width + 76))

    # Get text in the selected language
    def t(self, key):
        return get_text(self.current_language, key)

    # Update the page for the selected language
    def set_language(self, language):
        self.current_language = language
        self.brand.set_language(language)

        # translate form labels, hints and buttons
        self.heading.setText(self.t("login_title"))
        self.subtitle.setText(self.t("login_subtitle"))
        self.username_label.setText(self.t("username"))
        self.username_input.setPlaceholderText(self.t("username_placeholder"))
        self.password_label.setText(self.t("password"))
        self.password_input.setPlaceholderText(self.t("password_placeholder"))
        self.login_button.setText(self.t("login_button"))
        self.register_button.setText(self.t("create_account"))
        self.divider_label.setText(self.t("new_here"))

        # menu item for language
        index = self.language_combo.findData(language)
        if index >= 0:
            # Avoid triggering another language change while updating menu
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(index)
            self.language_combo.blockSignals(False)

        # suitable text sizes for Tamil
        tamil = language == "Tamil"

        # widgets
        widgets = [
            (self.heading, 20),
            (self.subtitle, 10),
            (self.username_label, 10),
            (self.password_label, 10),
            (self.username_input, 10),
            (self.password_input, 10),
            (self.login_button, 10),
            (self.register_button, 10),
            (self.divider_label, 9),
            (self.language_combo, 10),
        ]

        # font size for tamil
        for widget, size in widgets:
            widget.setStyleSheet(f"font-size:{max(size, 12)}px;" if tamil else "")
        # resize
        self.resize_language_combo()

    # Update page when it appears
    def showEvent(self, event):
        super().showEvent(event)
        self.card_host.play()

    # Show success or error message
    def show_status(self, message, status_type):
        # Choose status image
        icon_file = "success.png" if status_type == "success" else "error.png"
        self.status_icon.setPixmap(QPixmap(str(IMAGES / icon_file)))

        # Message text only
        self.status_label.setText(message)

        # Apply matching success or error style
        for widget in (self.status_row, self.status_label, self.status_icon):
            widget.setProperty("statusType", status_type)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        self.status_row.show()

    # Clear and hide the status message
    def clear_status(self):
        self.status_label.clear()
        self.status_row.hide()

    # Clear the password field
    def clear_password(self):
        self.password_input.clear()