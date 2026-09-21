# Import required libraies
from UI.ui.profile_panel import ProfilePanel
from UI.ui.ui_components import scroll_page, float_in
from UI.ui.account_widgets import add_avatar
from pathlib import Path
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QTabWidget, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout,QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from UI.ui.home_page import HoverSidebar
from UI.ui.translations import ENGLISH_TEXT, get_text

# logout confirmation wording to shared translations
ENGLISH_TEXT.update({
    "logout_dialog_title": "Log out of Solace?",
    "logout_dialog_message": "You'll need to sign in again to continue. Your current chat will be cleared.",
    "logout_cancel": "Cancel",
    "logout_confirm": "Log out"
})

# project folder
ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "UI" / "images"

# profile, language and account preferences
class SettingsPage(QWidget):
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    logout_requested = Signal()
    language_changed = Signal(str)
    privacy_requested = Signal()
    delete_account_requested = Signal()

    def __init__(self):
        super().__init__()
        # settings page in English
        self.current_language = "English"

        # sidebar navigation for this page
        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.trends_requested.connect(self.trends_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        self.set_active_sidebar()

        # layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.content = self.build_content()
        layout.addWidget(self.sidebar)
        layout.addWidget(self.content, 1)

        self.set_language("English")

    # Update page when appears
    def showEvent(self, event):
        super().showEvent(event)
        self.sidebar.set_expanded(HoverSidebar._shared_expanded)
        float_in(self.content)

    # current sidebar page
    def set_active_sidebar(self):
        # previous sidebar highlight and select settings
        buttons = (self.sidebar.home_button,self.sidebar.check_in_button,self.sidebar.trends_button,self.sidebar.settings_button,)
        for button in buttons:
            # active button
            button.setProperty("active", False)

        self.sidebar.settings_button.setProperty("active", True)

        for button in buttons:
            # buttons style
            button.style().unpolish(button)
            button.style().polish(button)

    # Build content
    def build_content(self):
        content = QWidget()
        content.setObjectName("homeContent")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # title
        self.title = QLabel()
        self.title.setObjectName("settingsPageTitle")

        # subtitle
        self.subtitle = QLabel()
        self.subtitle.setObjectName("settingsPageSubtitle")
        self.subtitle.setWordWrap(True)

        # Arrange language, privacy and deletion cards
        cards = QGridLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setHorizontalSpacing(20)
        cards.setVerticalSpacing(20)
        cards.addWidget(self.build_language_card(), 0, 0)
        cards.addWidget(self.build_privacy_card(), 0, 1)
        cards.addWidget(self.build_delete_account_card(), 1, 0, 1, 2)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)

        # page header above the account tabs
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 18, 32, 30)
        layout.setSpacing(0)
        layout.addLayout(self.build_header())
        layout.addSpacing(8)
        layout.addWidget(self.title)
        layout.addSpacing(5)
        layout.addWidget(self.subtitle)
        layout.addSpacing(8)

        # preferences separate from the profile form
        preferences=QWidget()
        preferences.setObjectName("preferencesPanel")
        prefs_layout=QVBoxLayout(preferences)
        prefs_layout.setContentsMargins(0, 4, 0, 0)
        prefs_layout.addLayout(cards)
        prefs_layout.addStretch()

        # scrollable profile and preference tabs
        self.profile_panel=ProfilePanel()
        self.account_tabs=QTabWidget()
        self.account_tabs.tabBar().setDrawBase(False)
        self.account_tabs.addTab(scroll_page(self.profile_panel), "Profile")
        self.account_tabs.addTab(scroll_page(preferences), "Preferences")
        layout.addWidget(self.account_tabs, 1)

        return content

    # Build the header
    def build_header(self):
        heart = QLabel()
        heart.setFixedSize(42, 42)
        heart.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        heart.setPixmap(QPixmap(str(IMAGES / "heart.png")).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # brand
        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        # layout
        layout = QHBoxLayout()
        layout.setSpacing(2)
        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()
        add_avatar(layout)
        return layout

    # Build language card
    def build_language_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(220)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # langauge heading
        self.language_heading = QLabel()
        self.language_heading.setObjectName("featureTitle")

        # langauge description
        self.language_description = QLabel()
        self.language_description.setObjectName("featureDescription")
        self.language_description.setWordWrap(True)

        # language label
        self.language_label = QLabel()
        self.language_label.setObjectName("fieldLabel")

        # Offer supported languages in the preferences card
        self.language_combo = QComboBox()
        self.language_combo.setFixedHeight(44)
        self.language_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.language_combo.setCursor(Qt.PointingHandCursor)
        self.language_combo.addItem("English", "English")
        self.language_combo.addItem("Bahasa Melayu", "Malay")
        self.language_combo.addItem("简体中文", "Chinese")
        self.language_combo.addItem("தமிழ்", "Tamil")

        # Apply new language when the selection changes
        self.language_combo.currentIndexChanged.connect(self.language_selected)

        # Explain how chosen language will be used
        self.language_note = QLabel()
        self.language_note.setObjectName("privacyNote")
        self.language_note.setWordWrap(True)

        # layout 
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(9)
        layout.addWidget(self.language_heading)
        layout.addWidget(self.language_description)
        layout.addStretch()
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)
        layout.addWidget(self.language_note)
        return card

    # Build privacy card
    def build_privacy_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(220)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # privacy heading
        self.privacy_heading = QLabel()
        self.privacy_heading.setObjectName("featureTitle")

        # privacy description
        self.privacy_description = QLabel()
        self.privacy_description.setObjectName("featureDescription")
        self.privacy_description.setWordWrap(True)

        # Create button for reviewing privacy information
        self.privacy_button = QPushButton()
        self.privacy_button.setObjectName("secondaryButton")
        self.privacy_button.setFixedHeight(44)
        self.privacy_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.privacy_button.setCursor(Qt.PointingHandCursor)

        # Ask main window to open privacy dialog
        self.privacy_button.clicked.connect(self.privacy_requested.emit)

        # layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(9)
        layout.addWidget(self.privacy_heading)
        layout.addWidget(self.privacy_description)
        layout.addStretch()
        layout.addWidget(self.privacy_button)

        return card

    # Build delete account card
    def build_delete_account_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(220)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Explain that account deletion is permanent
        self.delete_heading = QLabel()
        self.delete_heading.setObjectName("dangerTitle")

        # delete description
        self.delete_description = QLabel()
        self.delete_description.setObjectName("featureDescription")
        self.delete_description.setWordWrap(True)

        # Create the account deletion button
        self.delete_button = QPushButton()
        self.delete_button.setObjectName("deleteAccountButton")
        self.delete_button.setFixedHeight(44)
        self.delete_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.delete_button.setCursor(Qt.PointingHandCursor)

        # Ask main window to start deletion confirmation
        self.delete_button.clicked.connect(self.delete_account_requested.emit)

        # layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(8)
        layout.addWidget(self.delete_heading)
        layout.addWidget(self.delete_description)
        layout.addSpacing(6)
        layout.addWidget(self.delete_button)
        return card

    # Apply language selected in the menu
    def language_selected(self):
        language = self.language_combo.currentData()
        self.set_language(language)
        self.language_changed.emit(language)

    # Get text in the selected language
    def t(self, key):
        return get_text(self.current_language, key)

    # Update the page for the selected language
    def set_language(self, language):
        self.current_language = language
        self.sidebar.set_language(language)

        # translate headings, notes and action buttons
        self.title.setText(self.t("settings_title"))
        self.subtitle.setText(self.t("settings_subtitle"))
        self.language_heading.setText(self.t("language"))
        self.language_description.setText(self.t("language_description"))
        self.language_label.setText(self.t("application_language"))
        self.language_note.setText(self.t("language_note"))
        self.privacy_heading.setText(self.t("privacy_settings_title"))
        self.privacy_description.setText(self.t("privacy_settings_description"))
        self.privacy_button.setText(self.t("view_privacy"))
        self.delete_heading.setText(self.t("delete_account_title"))
        self.delete_description.setText(self.t("delete_account_description"))
        self.delete_button.setText(self.t("delete_account"))

        # update language menu
        index = self.language_combo.findData(language)
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)

        # translate the profile form and account tab labels
        self.profile_panel.set_language(language)
        self.account_tabs.setTabText(0,self.t("profile_tab"))
        self.account_tabs.setTabText(1,self.t("preferences_tab"))
        self.tamil_fonts()

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"
        # adjust settings text sizes for Tamil
        sizes = [
            (self.title, 18), (self.subtitle, 10),
            (self.language_heading, 11), (self.language_description, 10),
            (self.language_label, 10), (self.language_combo, 10),
            (self.language_note, 9), (self.privacy_heading, 11),
            (self.privacy_description, 10), (self.privacy_button, 10),
            (self.delete_heading, 11), (self.delete_description, 10),
            (self.delete_button, 10),
        ]

        # widget font size
        for widget, size in sizes:
            widget.setStyleSheet(f"font-size:{max(size, 12)}px;" if tamil else "")

# confirmation before deleting an account
class DeleteAccountDialog(QDialog):
    def __init__(self, language="English", parent=None):
        super().__init__(parent)
        self.language = language

        # modal card without normal window frame
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(get_text(language, "delete_dialog_title"))
        self.setFixedSize(580, 430)
        card = QFrame()
        card.setObjectName("deleteAccountDialogCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        # deletion warning and what will be removed
        title = QLabel(get_text(language, "delete_dialog_title"))
        title.setObjectName("deleteDialogTitle")

        # warning dialog
        warning = QLabel(get_text(language, "delete_dialog_warning"))
        warning.setObjectName("deleteDialogWarning")
        warning.setWordWrap(True)

        # details dialog
        details = QLabel(get_text(language, "delete_dialog_details"))
        details.setObjectName("deleteDialogDetails")
        details.setWordWrap(True)

        # Require user to acknowledge permanent deletion
        self.confirm_checkbox = QCheckBox(get_text(language, "delete_dialog_confirm"))

        # cross button to dismiss deletion dialog
        close_button = QPushButton()
        close_button.setObjectName("deleteDialogCloseButton")
        close_button.setFixedSize(36, 36)
        close_button.setIcon(QIcon(str(IMAGES / "cross_delete.png")))
        close_button.setIconSize(QSize(24, 24))
        close_button.setStyleSheet("padding: 0px;")
        close_button.setAutoDefault(False)
        close_button.setToolTip(get_text(language, "resource_close"))
        close_button.setAccessibleName(get_text(language, "resource_close"))
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.reject)

        # close row
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_button)

        # delete button disabled until confirmation is checked
        self.delete_button = QPushButton(get_text(language, "delete_account_confirm"))
        self.delete_button.setObjectName("deleteAccountButton")
        self.delete_button.setFixedHeight(44)
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.accept)

        # deletion only after the checkbox is ticked
        self.confirm_checkbox.toggled.connect(self.delete_button.setEnabled)

        # layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addLayout(close_row)
        layout.addWidget(title)
        layout.addWidget(warning)
        layout.addWidget(details)
        layout.addWidget(self.confirm_checkbox)
        layout.addStretch()

        # delete button across the card
        self.delete_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.delete_button)

        # outer
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(card)

# Ask user to confirm logout
class LogoutDialog(QDialog):
    def __init__(self, language="English", parent=None):
        super().__init__(parent)
        # frameless style for logout confirmation
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(440, 240)
        card = QFrame()
        card.setObjectName("thankYouCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        # translated logout title and explanation
        title = QLabel(get_text(language, "logout_dialog_title"))
        title.setObjectName("thankYouTitle")
        title.setAlignment(Qt.AlignCenter)

        # message for the user
        message = QLabel(get_text(language, "logout_dialog_message"))
        message.setObjectName("thankYouText")
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)

        # user cancel logout
        cancel = QPushButton(get_text(language, "logout_cancel"))
        cancel.setObjectName("secondaryButton")
        cancel.setFixedHeight(44)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)

        # Accept dialog only when logout is confirmed
        confirm = QPushButton(get_text(language, "logout_confirm"))
        confirm.setObjectName("primaryButton")
        confirm.setFixedHeight(44)
        confirm.setCursor(Qt.PointingHandCursor)
        confirm.clicked.connect(self.accept)

        # buttons for the cancel
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)

        # Adjust logout text for Tamil
        if language == "Tamil":
            title.setStyleSheet("font-size:15px;")
            message.setStyleSheet("font-size:12px;")

        # layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addStretch()
        layout.addLayout(buttons)

        # outer
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(card)