# Import required libraries
import os
from UI.ui.account_widgets import add_avatar
from pathlib import Path
from PySide6.QtCore import QDateTime, QEasingCurve, QLocale, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,QSizePolicy, QVBoxLayout, QWidget, QScrollArea
from UI.ui.ui_components import GardenArtwork, AnimatedIllustration, scroll_page, reveal, float_in
from UI.ui.resources import RESOURCES, ResourceDialog, home_resources_for_language
from UI.ui.translations import ENGLISH_TEXT, get_text

# Locate the project folder
ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "UI" / "images"

# language to its date format
LOCALES = {"English": "en_SG","Malay": "ms_MY","Chinese": "zh_CN","Tamil": "ta_IN",}

# English wording for the home page
HOME_TEXT = {
    "support_copy": "Copy number",
    "support_copied": "Copied",
    "support_hint": "Call 1771 from your phone for mental health support in Singapore",
    "assistant": "Assistant",
    "questionnaire": "Questionnaire",
    "home_questionnaire_title": "Your wellbeing questionnaire",
    "home_questionnaire_desc": "Take a moment to reflect on how you have been feeling.",
    "home_eyebrow": "PRIVATE WELLBEING CHECK-IN",
    "home_description": "Take a short check-in to reflect on how you are feeling today.",
    "good_morning": "Good morning",
    "good_afternoon": "Good afternoon",
    "good_evening": "Good evening",
    "today": "Today",
    "wellbeing_reminders": "Wellbeing reminders",
    "tip_pause_title": "Pause and reset",
    "tip_pause_text":"Take one quiet minute between demanding tasks to slow down and reset.",
    "tip_hydrate_title": "Hydrate and refuel",
    "tip_hydrate_text":"Remember water and regular meals during long or busy shifts.",
    "tip_pattern_title": "Notice your patterns",
    "tip_pattern_text":"Regular check-ins can help you notice changes in how you have been feeling.",
    "home_private_note": "Your check-in history is stored locally on this device.",
}

# home page wording to shared translations
ENGLISH_TEXT.update(HOME_TEXT)

# sidebar across the app pages
class HoverSidebar(QFrame):
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    assistant_requested = Signal()
    questionnaire_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    # two sidebar widths together
    COLLAPSED = 76
    EXPANDED = 196
    _shared_expanded = True

    # open or closed state across pages
    _shared_expanded = True

    def __init__(self):
        super().__init__()
        self.current_language = "English"
        #sidebar state shared by the other pages
        self.expanded = HoverSidebar._shared_expanded
        self.setObjectName("sideBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(self.EXPANDED if self.expanded else self.COLLAPSED)

        # smooth animation when changing the sidebar width
        self.width_animation = QVariantAnimation(self)
        self.width_animation.setDuration(280)
        self.width_animation.setEasingCurve(QEasingCurve.InOutCubic)

        # Resize sidebar as the animation progresses
        self.width_animation.valueChanged.connect(lambda width: self.setFixedWidth(int(width)))

        # Always land exactly on the final width, even if interrupted
        self.width_animation.finished.connect(
            lambda: self.setFixedWidth(self.EXPANDED if self.expanded else self.COLLAPSED)
        )
        # sidebar toggle button
        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("navToggle")
        self.toggle_button.setIcon(QIcon(str(IMAGES / "close_icon.png")))
        self.toggle_button.setIconSize(QSize(40, 40))
        self.toggle_button.setFixedHeight(48)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.clicked.connect(self.toggle)

        # main navigation buttons
        self.home_button = self.make_button("home_icon.png", "home", True)
        self.check_in_button = self.make_button("check_in_icon.png", "check_in")
        self.trends_button = self.make_button("trends_icon.png", "trends")
        self.assistant_button = self.make_button("white_heart.png", "assistant")
        self.questionnaire_button = self.make_button("questionnaire_icon.png", "questionnaire")
        self.settings_button = self.make_button("settings_icon.png", "settings")
        self.logout_button = self.make_button("logout.png", "logout")

        # Forward button clicks through the navigation signals
        self.home_button.clicked.connect(self.home_requested.emit)
        self.check_in_button.clicked.connect(self.check_in_requested.emit)
        self.trends_button.clicked.connect(self.trends_requested.emit)
        self.assistant_button.clicked.connect(self.assistant_requested.emit)
        self.questionnaire_button.clicked.connect(self.questionnaire_requested.emit)
        self.settings_button.clicked.connect(self.settings_requested.emit)
        self.logout_button.clicked.connect(self.logout_requested.emit)

        # small card Singapore mental health support
        self.support_card = QFrame()
        self.support_card.setObjectName("sidebarSupportCard")
        self.support_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # support layout
        support_layout = QVBoxLayout(self.support_card)
        support_layout.setContentsMargins(12, 10, 12, 10)
        support_layout.setSpacing(6)

        # support name
        support_name = QLabel("national mindline")
        support_name.setObjectName("sidebarSupportName")

        # support number
        support_number = QLabel("1771")
        support_number.setObjectName("sidebarSupportNumber")
        support_number.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # support hours
        support_hours = QLabel("24/7")
        support_hours.setObjectName("sidebarSupportHours")

        # number and availability apart
        support_row = QHBoxLayout()
        support_row.addWidget(support_number)
        support_row.addStretch()
        support_row.addWidget(support_hours)

        # copy button
        self.support_copy = QPushButton()
        self.support_copy.setObjectName("sidebarSupportCopy")
        self.support_copy.setCursor(Qt.PointingHandCursor)
        self.support_copy.clicked.connect(self.copy_support_number)

        # layout
        support_layout.addWidget(support_name)
        support_layout.addLayout(support_row)
        support_layout.addWidget(self.support_copy)

        # Restore button text after copying
        self.support_timer = QTimer(self)
        self.support_timer.setSingleShot(True)
        self.support_timer.setInterval(2000)
        self.support_timer.timeout.connect(
            lambda: self.support_copy.setText(
                get_text(self.current_language, "support_copy")
            )
        )

        # remove focus highlight when message resets
        self.support_timer.timeout.connect(self.support_copy.clearFocus)

        # settings and logout below the main navigation links
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 20)
        layout.setSpacing(4)
        layout.addWidget(self.toggle_button)
        layout.addSpacing(8)
        layout.addWidget(self.home_button)
        layout.addWidget(self.check_in_button)
        layout.addWidget(self.trends_button)
        layout.addWidget(self.assistant_button)
        layout.addWidget(self.questionnaire_button)
        layout.addStretch()
        layout.addWidget(self.support_card)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.logout_button)
        self.set_expanded(self.expanded)

    # Copy helpline number without starting a call
    def copy_support_number(self):
        QApplication.clipboard().setText("1771")
        self.support_copy.setText(get_text(self.current_language, "support_copied"))
        self.support_timer.start()

    # sidebar button
    def make_button(self, image, key, active=False):
        button = QPushButton()
        button.setObjectName("navButton")
        button.setIcon(QIcon(str(IMAGES / image)))
        button.setIconSize(QSize(40, 40))
        button.setFixedHeight(48)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button.setProperty("active", active)
        button.setProperty("expanded", True)
        button.setProperty("textKey", key)
        return button

    # sidebar navigation buttons
    def buttons(self):
        return (self.home_button,self.check_in_button,self.trends_button,self.assistant_button,self.questionnaire_button,self.settings_button,self.logout_button)

    # page for the selected language
    def set_language(self, language):
        self.current_language = language
        tamil = language == "Tamil"

        # support wording in selected language
        self.support_timer.stop()
        self.support_copy.setText(get_text(language, "support_copy"))
        self.support_copy.setToolTip(get_text(language, "support_hint"))
        self.support_card.setToolTip(get_text(language, "support_hint"))

        for button in self.buttons():
            # each button label and its accessible name
            text = get_text(language, button.property("textKey"))
            button.setToolTip(text)
            button.setAccessibleName(text)
            # show the button text when the sidebar is expanded
            button.setText(f"{text}" if self.expanded else "")
            # adjusted font size
            button.setStyleSheet("font-size:10px;" if tamil else "")

    # selected sidebar button
    def set_active(self, key):
        for button in self.buttons():
            # selected page and refresh the button styles
            active = button.property("textKey") == key
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)

    # Open or close the sidebar
    def toggle(self):
        self.set_expanded(not self.expanded, animate=False)

    # Set sidebar width with optional animation
    def set_expanded(self, expanded, animate=False):
        # Stop previous animation before changing direction
        self.width_animation.stop()
        self.expanded = bool(expanded)

        # Hide support card when sidebar closes
        self.support_card.setVisible(self.expanded)

        # new state with the other pages
        HoverSidebar._shared_expanded = self.expanded
        target_width = (self.EXPANDED if self.expanded else self.COLLAPSED)
        self.set_language(self.current_language)
        for button in self.buttons():
            # Refresh button styling for new sidebar state
            button.setProperty("collapsed", not self.expanded)
            button.style().unpolish(button)
            button.style().polish(button)

        # Check reduced motion setting
        reduced_motion = (os.environ.get("SOLACE_REDUCED_MOTION") == "1")
        if (not animate or reduced_motion or self.width() == target_width):
            self.setFixedWidth(target_width)
            return

        # Animate from current width to requested width
        self.width_animation.setStartValue(self.width())
        self.width_animation.setEndValue(target_width)
        self.width_animation.start()


# home dashboard and resource cards
class HomePage(QWidget):
    check_in_requested = Signal()
    trends_requested = Signal()
    assistant_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()

        # current language, user name and date format
        self.current_language = "English"
        self.first_name = ""
        self.locale = QLocale(LOCALES["English"])

        # Connect sidebar actions to the home page signals
        self.sidebar = HoverSidebar()
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.trends_requested.connect(self.trends_requested.emit)
        self.sidebar.assistant_requested.connect(self.assistant_requested.emit)
        self.sidebar.settings_requested.connect(self.settings_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)

        # layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.content = self.build_content()
        layout.addWidget(self.sidebar)
        layout.addWidget(self.content, 1)

        # Refresh greeting and date once per second
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        # language to english
        self.set_language("English")

    # Update page when it appears
    def showEvent(self, event):
        super().showEvent(event)
        # Restore shared sidebar state when this page appears
        self.sidebar.set_active("home")
        self.sidebar.set_expanded(HoverSidebar._shared_expanded)
        float_in(self.content)
        
    # Build content
    def build_content(self):
        content = QWidget()
        content.setObjectName("homeContent")
        # Arrange header, welcome card and resources vertically
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(10)
        layout.addLayout(self.build_header())
        self.overview_label = QLabel()
        self.overview_label.setObjectName("pageEyebrow")
        layout.addWidget(self.overview_label)
        layout.addWidget(self.build_hero())

        # quick links to trends and the assistant
        quick = QHBoxLayout()
        quick.setSpacing(16)
        self.quick_labels = []

        # Quick links to trends, the assistant and questionnaire
        for title, description, signal, icon in [
            ('home_trends_title', 'home_trends_desc', self.trends_requested, 'trends_icon'),
            ('home_assistant_title', 'home_assistant_desc', self.assistant_requested, 'white_heart'),
            ('home_questionnaire_title', 'home_questionnaire_desc', self.sidebar.questionnaire_requested, 'questionnaire_icon'),
        ]:
            #card
            card = QPushButton()
            card.setObjectName('quickCard')
            card.setCursor(Qt.PointingHandCursor)
            card.setMinimumHeight(72)
            card.clicked.connect(signal.emit)

            # inside card
            inside = QVBoxLayout(card)
            inside.setContentsMargins(16, 12, 16, 12)

            # heading
            heading = QLabel()
            heading.setObjectName('featureTitle')
            heading.setWordWrap(True)
            note = QLabel(); note.setObjectName('featureDescription'); note.setWordWrap(True)
            for label in (heading, note):
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
                inside.addWidget(label)
            # Keep card and label keys for translation
            self.quick_labels.append((card, heading, note, title, description))
            quick.addWidget(card, 1)
        layout.addLayout(quick)

        # title and subtitle
        self.resources_title = QLabel(); self.resources_title.setObjectName('sectionTitle')
        self.resources_subtitle = QLabel(); self.resources_subtitle.setObjectName('featureDescription')

        # add widget
        layout.addWidget(self.resources_title)
        layout.addWidget(self.resources_subtitle)

        # row of resource cards
        resource_row = QHBoxLayout(); resource_row.setSpacing(16)
        self.resource_labels = []

        # Build card for each available resource
        for index, resource in enumerate(RESOURCES):
            card = QPushButton(); card.setObjectName('resourceCard')
            card.setCursor(Qt.PointingHandCursor)
            card.setMinimumHeight(300)

            # selected resource dialog when clicked
            card.clicked.connect(lambda checked=False, i=index: ResourceDialog(home_resources_for_language(self.current_language)[i],self.current_language,self).exec())
            inside = QVBoxLayout(card); inside.setContentsMargins(16, 12, 16, 12); inside.setSpacing(6)
            kind = QLabel(); kind.setObjectName('resourceTag'); kind.setProperty('tone',resource[4])
            title = QLabel(); title.setObjectName('resourceTitle'); title.setWordWrap(True)
            description = QLabel(); description.setObjectName('featureDescription'); description.setWordWrap(True)
            link = QLabel(); link.setObjectName('resourceLink'); link.hide()

            # matching illustration for this resource
            art = AnimatedIllustration(['yoga.jpg', 'stretch.jpg', 'reading.jpg'][len(self.resource_labels)], fit=True)
            art.setFixedHeight(190)
            inside.addWidget(art)

            # clicks on the labels reach the resource card button
            for label in (kind, title, description):
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
                inside.addWidget(label)
            inside.addStretch()

            # resource card and its labels for translation
            self.resource_labels.append((card, kind, title, description, link, resource))
            resource_row.addWidget(card, 1)
        layout.addLayout(resource_row)
        layout.addStretch()
        return content

    # Build header
    def build_header(self):
        # heart image beside the Solace name
        heart = QLabel()
        heart.setFixedSize(42, 42)
        heart.setPixmap(QPixmap(str(IMAGES / "heart.png")).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        heart.setAlignment(Qt.AlignCenter)

        # brand
        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        # legacy welcome label available to existing code
        self.welcome_label = QLabel()
        self.welcome_label.setObjectName("welcomeLabel")
        self.welcome_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # layout
        layout = QHBoxLayout()
        layout.setSpacing(7)
        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()
        layout.addWidget(self.welcome_label)

        # profile avatar to the header
        add_avatar(layout)
        return layout

    # Build hero
    def build_hero(self):
        # main welcome card
        card = QFrame(); card.setObjectName('heroCard')
        card.setMinimumHeight(230)
        row = QHBoxLayout(card); row.setContentsMargins(0,0,0,0); row.setSpacing(0)

        # Arrange greeting and supporting text beside the artwork
        text = QVBoxLayout(); text.setContentsMargins(24,20,18,20); text.setSpacing(8)
        self.hero_eyebrow = QLabel(); self.hero_eyebrow.setObjectName('heroEyebrow')
        self.hero_title = QLabel(); self.hero_title.setObjectName('heroTitle'); self.hero_title.setWordWrap(True)
        self.hero_description = QLabel(); self.hero_description.setObjectName('heroDescription'); self.hero_description.setWordWrap(True)

        # button that starts a check-in
        self.start_button = QPushButton(); self.start_button.setObjectName('startCheckInButton')
        self.start_button.setFixedHeight(46); self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.check_in_requested.emit)

        # Explain check-in history stays on this device
        self.private_note = QLabel(); self.private_note.setObjectName('privacyNote'); self.private_note.setWordWrap(True)
        for widget in (self.hero_eyebrow,self.hero_title,self.hero_description): text.addWidget(widget)
        text.addSpacing(10)
        text.addWidget(self.start_button,0,Qt.AlignLeft)
        text.addWidget(self.private_note)
        text.addStretch()

        # card width between the text and illustration
        row.addLayout(text, 3)

        # care illustration with enough width
        artwork = AnimatedIllustration("care.jpg", fit=True); artwork.setMinimumWidth(340)
        row.addWidget(artwork, 3)
        self.hero_card = card
        return card

    # Get text in selected language
    def t(self, key):
        return get_text(self.current_language, key)

    # Update page for selected language
    def set_language(self, language):
        self.current_language = language
        # date format for this language
        self.locale = QLocale(LOCALES[language])
        self.sidebar.set_language(language)
        # Translate main home page labels
        for widget, key in [(self.hero_eyebrow,'home_eyebrow'),(self.hero_description,'home_care_line'),
                            (self.start_button,'start_check_in'),(self.private_note,'home_private_note'),
                            (self.overview_label,'home_overview'),(self.resources_title,'resources_title'),
                            (self.resources_subtitle,'resources_subtitle')]:
            widget.setText(self.t(key))

        # quick link card
        for card, heading, note, title, description in self.quick_labels:
            heading.setText(self.t(title)); note.setText(self.t(description))
            card.setAccessibleName(self.t(title))

        # Show resources for the selected language
        resources = home_resources_for_language(self.current_language)

        for index, item in enumerate(self.resource_labels):
            # card and title and link for selected languages
            card, kind, title, description, link, _ = item
            resource = resources[index]
            kind.setText(self.t(resource[0]))
            title.setText(self.t(resource[1]))
            description.setText(self.t(resource[2]))
            link.setText(self.t("home_resource_link"))
            card.setAccessibleName(self.t(resource[1]))
            card.setToolTip(resource[3])

        # tamil fonts and update clock
        self.tamil_fonts()
        self.update_clock()

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        # Adjust main labels for Tamil text
        sizes = [
            (self.hero_eyebrow, 9),
            (self.hero_title, 22),
            (self.hero_description, 12),
            (self.start_button, 11),
            (self.private_note, 10),
            (self.overview_label, 11),
            (self.resources_title, 16),
            (self.resources_subtitle, 11),
        ]

        # font size for tamil
        for widget, size in sizes:
            widget.setStyleSheet(f"font-size:{size}px;" if tamil else "")

        # card styles
        for card, heading, note, title, description in self.quick_labels:
            heading.setStyleSheet("font-size:13px;" if tamil else "")
            note.setStyleSheet("font-size:11px;" if tamil else "")

        # card description and title
        for card, kind, title, description, link, resource in self.resource_labels:
            kind.setStyleSheet("font-size:9px;" if tamil else "")
            title.setStyleSheet("font-size:13px;" if tamil else "")
            description.setStyleSheet("font-size:11px;" if tamil else "")

    # user shown on this page
    def set_user(self, full_name):
        # first word of the name when available
        self.first_name = full_name.split()[0] if full_name else ""
        self.update_clock()

    # greeting and date
    def update_clock(self):
        # current date and time
        now = QDateTime.currentDateTime()
        hour = now.time().hour()

        # morning greeting before noon
        if hour < 12:
            greeting = self.t("good_morning")
        elif hour < 18:
            greeting = self.t("good_afternoon")
        else:
            greeting = self.t("good_evening")

        # Show greeting with first name available
        self.hero_title.setText(f"{greeting}, {self.first_name}" if self.first_name else greeting)
        self.welcome_label.setText(self.locale.toString(now.date(), "dddd, d MMMM yyyy"))