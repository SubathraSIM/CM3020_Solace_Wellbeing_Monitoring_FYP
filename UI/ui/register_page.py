# Import required libraries
from PySide6.QtGui import QPixmap
from pathlib import Path
from UI.ui.account_widgets import PasswordEdit, PasswordRequirementsBar
import re
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from UI.ui.login_page import BrandPanel
from UI.ui.ui_components import FloatCard
from UI.ui.translations import ENGLISH_TEXT, get_text

# English registration labels and validation messages
REGISTER_TEXT = {
    "register_title": "Create your account",
    "register_subtitle": "Start your private wellbeing journey",
    "full_name": "Full name",
    "full_name_placeholder": "Enter your full name",
    "username": "Username",
    "choose_username": "Choose a username",
    "password": "Password",
    "create_password": "Create a password",
    "confirm_password": "Confirm password",
    "confirm_password_placeholder": "Enter your password again",
    "password_rule":"Use at least 8 characters with uppercase, lowercase, number and symbol.",
    "create_account": "Create account",
    "back_login": "Back to login",
    "register_empty": "Enter a username, password and password confirmation.",
    "password_weak":"Password must contain at least 8 characters, uppercase, lowercase, number and symbol.",
    "password_mismatch": "The passwords do not match.",
    "username_exists": "This username is already registered.",
    "account_created": "Account created successfully."
}

# images directory
IMAGES_DIR = Path(__file__).resolve().parents[2] / "UI" / "images"

# registration wording to the shared translations
ENGLISH_TEXT.update(REGISTER_TEXT)


# account registration form
class RegisterPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.ClickFocus)
        self.current_language = "English"

        # main registration card
        card = QFrame()
        card.setObjectName("appCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setFixedSize(940, 630)

        # shared brand panel beside the form
        self.brand = BrandPanel()
        form = self.build_form()
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card_layout.addWidget(self.brand, 47)
        card_layout.addWidget(form, 53)

        # Wrap card for its entrance animation
        self.card_host = FloatCard(card)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.card_host)
        row.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch()
        layout.addLayout(row)
        layout.addStretch()
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

        # validation message text
        self.status_label = QLabel()
        self.status_label.setObjectName("statusMessage")
        self.status_label.setWordWrap(True)

        # icon and message in one row show hide as a unit
        self.status_row = QWidget()
        self.status_row.setObjectName("statusRow")
        status_row_layout = QHBoxLayout(self.status_row)
        status_row_layout.setContentsMargins(0, 0, 0, 0)
        status_row_layout.setSpacing(8)
        status_row_layout.addWidget(self.status_icon)
        status_row_layout.addWidget(self.status_label, 1)
        self.status_row.setMinimumHeight(38)
        self.status_row.hide()

        # optional name and required username fields
        self.name_label = self.field_label()
        self.name_input = self.field()

        self.username_label = self.field_label()
        self.username_input = self.field()

        # password field with a visibility toggle
        self.password_label = self.field_label()
        self.password_input = self.field(True)
        # Show progress towards the password requirements
        self.password_bar = PasswordRequirementsBar(self.password_input)

        # password requirements below the field
        self.password_rule = QLabel()
        self.password_rule.setObjectName("privacyNote")
        self.password_rule.setWordWrap(True)

        # field for confirming the password
        self.confirm_label = self.field_label()
        self.confirm_password_input = self.field(True)

        # account submission button
        self.create_button = QPushButton()
        self.create_button.setObjectName("primaryButton")
        self.create_button.setFixedHeight(44)
        self.create_button.setCursor(Qt.PointingHandCursor)

        # button for returning to login
        self.back_button = QPushButton()
        self.back_button.setObjectName("secondaryButton")
        self.back_button.setFixedHeight(44)
        self.back_button.setCursor(Qt.PointingHandCursor)

        # Enter in the confirmation field to submit the form
        self.confirm_password_input.returnPressed.connect(self.create_button.click)

        # layout
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(44, 24, 44, 24)
        layout.setSpacing(0)
        layout.addWidget(self.heading)
        layout.addSpacing(3)
        layout.addWidget(self.subtitle)
        layout.addSpacing(5)
        layout.addWidget(self.status_row)
        layout.addSpacing(6)

        # each field label above its input
        for field_label, field in ((self.name_label, self.name_input),(self.username_label, self.username_input),(self.password_label, self.password_input)):
            layout.addWidget(field_label)
            layout.addSpacing(2)
            layout.addWidget(field)

            # password guidance below the password field
            if field is self.password_input:
                layout.addSpacing(3)
                layout.addWidget(self.password_bar)
                layout.addWidget(self.password_rule)

            layout.addSpacing(5)

        # layout
        layout.addWidget(self.confirm_label)
        layout.addSpacing(2)
        layout.addWidget(self.confirm_password_input)
        layout.addSpacing(10)
        layout.addWidget(self.create_button)
        layout.addSpacing(6)
        layout.addWidget(self.back_button)

        return panel

    # form field label
    @staticmethod
    def field_label():
        widget = QLabel()
        widget.setObjectName("fieldLabel")
        return widget

    # normal or password input field
    @staticmethod
    def field(password=False):
        # password field only when requested
        widget = PasswordEdit() if password else QLineEdit()
        widget.setFixedHeight(44)

        if password:
            widget.setEchoMode(QLineEdit.Password)

        return widget

    # Get text in the selected language
    def t(self, key):
        return get_text(self.current_language, key)

    # Update page for the selected language
    def set_language(self, language):
        self.current_language = language
        self.brand.set_language(language)

        # Translate all form labels, hints and buttons
        self.heading.setText(self.t("register_title"))
        self.subtitle.setText(self.t("register_subtitle"))

        # name
        self.name_label.setText(self.t("register_name_optional"))
        self.name_input.setPlaceholderText(self.t("full_name_placeholder"))

        # username
        self.username_label.setText(self.t("username"))
        self.username_input.setPlaceholderText(self.t("choose_username"))

        # password
        self.password_label.setText(self.t("password"))
        self.password_input.setPlaceholderText(self.t("create_password"))
        self.password_rule.setText(self.t("password_rule"))
        self.password_bar.set_language(language)

        # confirmation
        self.confirm_label.setText(self.t("confirm_password"))
        self.confirm_password_input.setPlaceholderText(self.t("confirm_password_placeholder"))

        # buttons
        self.create_button.setText(self.t("create_account"))
        self.back_button.setText(self.t("back_login"))

        self.tamil_fonts()

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        # Adjust form text sizes for Tamil
        widgets = [
            (self.heading, 20),
            (self.subtitle, 10),
            (self.name_label, 10),
            (self.username_label, 10),
            (self.password_label, 10),
            (self.confirm_label, 10),
            (self.name_input, 10),
            (self.username_input, 10),
            (self.password_input, 10),
            (self.confirm_password_input, 10),
            (self.password_rule, 9),
            (self.create_button, 10),
            (self.back_button, 10)
        ]

        for widget, size in widgets:
            widget.setStyleSheet(f"font-size:{max(size, 12)}px;" if tamil else "")

    # Check password length and character requirements
    @staticmethod
    def valid_password(password):
        # Require eight characters, both letter cases, a number and a symbol
        return bool(
            len(password) >= 8
            and re.search(r"[A-Z]", password)
            and re.search(r"[a-z]", password)
            and re.search(r"[0-9]", password)
            and re.search(r"[^A-Za-z0-9]", password)
        )

    # Show a success or error message
    def show_status(self, message, status_type):
        # status image
        icon_file = "success.png" if status_type == "success" else "error.png"
        self.status_icon.setPixmap(QPixmap(str(IMAGES_DIR / icon_file)))

        # Message text only
        self.status_label.setText(message)

        # success or error style before showing message
        for widget in (self.status_row, self.status_label, self.status_icon):
            widget.setProperty("statusType", status_type)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        self.status_row.show()

    # Clear and hide status message
    def clear_status(self):
        self.status_label.clear()
        self.status_row.hide()

    # Clear all registration fields
    def clear_fields(self):
        self.name_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()

    # Update the page when it appears
    def showEvent(self, event):
        super().showEvent(event)
        self.card_host.play()
        # Keep focus off the fields when the page opens
        QTimer.singleShot(0, self.setFocus)