# Import required libraries
import hashlib
import re
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QLineEdit, QLabel, QToolButton, QProgressBar
from UI.ui.translations import ENGLISH_TEXT, get_text

# shared password and profile labels
ENGLISH_TEXT.update({'show_password':'Show password', 'hide_password':'Hide password', 'profile':'Profile', 'password_progress': 'Password requirements','password_approved': 'Requirements met','password_requirements_hint': 'Use at least 8 characters with uppercase, lowercase, a number and a symbol'})

# images folder
IMAGES_DIR = Path(__file__).resolve().parents[2] / "UI" / "images"

# initials and a consistent colour for each user
class AvatarButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('profileAvatar')
        self.setFixedSize(42,42)
        self.setCursor(Qt.PointingHandCursor)
        self.set_identity('')

    # profile initials and colour
    def set_identity(self, username):
        # Split the username into words
        parts = re.findall(r'[^\W_]+', str(username), flags=re.UNICODE)
        # two initials or a question mark
        initials = ''.join(p[0] for p in parts[:2]).upper() or '?'
        colors = ['#456AA3', '#756393', '#3F7E85', '#A56859', '#687A4D']
        # consistent colour from the username hash
        index = int(hashlib.sha256(str(username).casefold().encode()).hexdigest()[:8],16) % len(colors)
        self.setText(initials)
        self.setToolTip(str(username) or 'Profile')
        self.setAccessibleName('Profile: ' + str(username))
        self.setStyleSheet(f'#profileAvatar {{ background: {colors[index]}; }}')

# profile button to the header
def add_avatar(layout):
    # available to existing setters but remove them
    for i in range(layout.count()):
        widget=layout.itemAt(i).widget()
        if isinstance(widget,QLabel) and widget.objectName()=='welcomeLabel':
            widget.hide()
    # avatar and layout
    avatar=AvatarButton()
    layout.addWidget(avatar)
    return avatar

# show or hide button to password fields
class PasswordEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        # password visibility button
        self.setTextMargins(0, 0, 44, 0)

        # eye buttons
        self.eye = QToolButton(self)
        self.eye.setObjectName("passwordEyeButton")
        self.eye.setFixedSize(36, 36)
        self.eye.setIconSize(QSize(36, 36))
        self.eye.setCursor(Qt.PointingHandCursor)
        self.eye.setFocusPolicy(Qt.StrongFocus)

        # visibility toggle and reset it when field is empty
        self.eye.clicked.connect(self.toggle_visibility)
        self.textChanged.connect(self.reset_if_empty)
        self.refresh_eye()

    # Update layout when size changes
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # visibility button at right edge
        self.eye.move(self.width() - self.eye.width() - 7,(self.height() - self.eye.height()) // 2,)

    # Update password visibility icon and label
    def refresh_eye(self):
        visible = self.echoMode() == QLineEdit.Normal
        # read window language with an English fallback
        language = getattr(self.window(), "current_language", "English")

        # show or hide password label
        label = get_text(language, "hide_password" if visible else "show_password")
        self.eye.setToolTip(label)
        self.eye.setAccessibleName(label)

        # eye image that matches the current display mode
        filename = "eye_off.png" if visible else "eye.png"
        icon = QIcon(str(IMAGES_DIR / filename))

        # Use text button if the eye image is missing
        if icon.isNull():
            self.eye.setIcon(QIcon())
            self.eye.setText("Hide" if visible else "Show")
        else:
            self.eye.setText("")
            self.eye.setIcon(icon)

    # Switch showing and hiding the password
    def toggle_visibility(self):
        visible = self.echoMode() == QLineEdit.Normal
        # Switch password display mode
        self.setEchoMode(QLineEdit.Password if visible else QLineEdit.Normal)
        self.refresh_eye()
        self.setFocus()

    # Hide password again when the field is empty
    def reset_if_empty(self, text):
        if not text:
            self.setEchoMode(QLineEdit.Password)
            self.refresh_eye()

# show how many password requirements are met
class PasswordRequirementsBar(QProgressBar):
    def __init__(self, field, parent=None):
        super().__init__(parent)
        # requirements
        self.field = field
        self.setObjectName('passwordRequirementsBar')
        self.setRange(0, 5)
        self.setFixedHeight(8)
        self.setTextVisible(False)
        self.set_language('English')
        field.textChanged.connect(self.update_requirements)
        self.update_requirements(field.text())

    # refresh wording when language changes
    def set_language(self, language):
        self.progress_text = get_text(language, 'password_progress')
        self.approved_text = get_text(language, 'password_approved')
        self.setToolTip(get_text(language, 'password_requirements_hint'))
        self.setAccessibleName(self.progress_text)
        self.update_requirements(self.field.text())

    # five existing password rules
    def update_requirements(self, password):
        # checks and counts
        checks = [
            len(password) >= 8,
            bool(re.search(r'[A-Z]', password)),
            bool(re.search(r'[a-z]', password)),
            bool(re.search(r'[0-9]', password)),
            bool(re.search(r'[^A-Za-z0-9]', password)),
        ]
        count = sum(checks)
        self.setValue(count)
        # approve
        self.setFormat(
            self.approved_text if count == 5
            else f'{self.progress_text}: {count}/5'
        )

        # colour when the result changes
        self.setProperty('approved', count == 5)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()