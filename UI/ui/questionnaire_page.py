# Import required libraries
from statistics import mean
from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtWidgets import QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel,QPushButton, QStackedWidget, QVBoxLayout, QWidget
from UI.ui.account_widgets import add_avatar
from UI.ui.home_page import HoverSidebar
from UI.ui.ui_components import float_in
from UI.ui.translations import ENGLISH_TEXT, get_text
from UI.database.database import save_questionnaire, set_questionnaire_reminders, questionnaire_reminder_due

# English wording for the questionnaire page and the CBI items
QUESTIONNAIRE_TEXT = {
    "questionnaire": "Questionnaire",
    "cbi_title": "Wellbeing questionnaire",
    "cbi_subtitle": "A short, validated burnout check-in (Copenhagen Burnout Inventory).",
    "cbi_intro": "This questionnaire is optional. If you choose to take it, please answer every question, then submit. Your answers are private and stored only on this device.",
    "cbi_progress": "Questions {start}-{end} of 13",
    "cbi_back": "Back",
    "cbi_next": "Next",
    "cbi_submit": "Submit",
    "cbi_done_title": "Thank you",
    "cbi_done_message": "Your questionnaire has been saved on this device.",
    "cbi_reminder_title": "Weekly reminders",
    "cbi_reminder_message": "Would you like a weekly reminder to complete this questionnaire?",
    "cbi_reminder_yes": "Yes",
    "cbi_reminder_no": "No, thanks",
    "cbi_reminder_due": "It has been a week since your last questionnaire. You can complete it again when you are ready.",
    # thirteen CBI items in order
    "cbi_q1": "How often do you feel tired?",
    "cbi_q2": "How often are you physically exhausted?",
    "cbi_q3": "How often are you emotionally exhausted?",
    "cbi_q4": "How often do you think: \"I can't take it anymore\"?",
    "cbi_q5": "How often do you feel worn out?",
    "cbi_q6": "How often do you feel weak and susceptible to illness?",
    "cbi_q7": "Is your work emotionally exhausting?",
    "cbi_q8": "Do you feel burnt out because of your work?",
    "cbi_q9": "Does your work frustrate you?",
    "cbi_q10": "Do you feel worn out at the end of the working day?",
    "cbi_q11": "Are you exhausted in the morning at the thought of another day at work?",
    "cbi_q12": "Do you feel that every working hour is tiring for you?",
    "cbi_q13": "Do you have enough energy for family and friends during leisure time?",
    # two five point answer scales
    "cbi_opt_always": "Always",
    "cbi_opt_often": "Often",
    "cbi_opt_sometimes": "Sometimes",
    "cbi_opt_seldom": "Seldom",
    "cbi_opt_never": "Never or almost never",
    "cbi_opt_vhigh": "To a very high degree",
    "cbi_opt_high": "To a high degree",
    "cbi_opt_somewhat": "Somewhat",
    "cbi_opt_low": "To a low degree",
    "cbi_opt_vlow": "To a very low degree",
}

# questionnaire wording to shared translations
ENGLISH_TEXT.update(QUESTIONNAIRE_TEXT)

# frequency scale
FREQ_SCALE = [
    ("cbi_opt_always", "Always", 100),
    ("cbi_opt_often", "Often", 75),
    ("cbi_opt_sometimes", "Sometimes", 50),
    ("cbi_opt_seldom", "Seldom", 25),
    ("cbi_opt_never", "Never or almost never", 0),
]

# degree scale
DEGREE_SCALE = [
    ("cbi_opt_vhigh", "To a very high degree", 100),
    ("cbi_opt_high", "To a high degree", 75),
    ("cbi_opt_somewhat", "Somewhat", 50),
    ("cbi_opt_low", "To a low degree", 25),
    ("cbi_opt_vlow", "To a very low degree", 0),
]

# Each item
CBI_ITEMS = [
    ("cbi_q1", FREQ_SCALE), ("cbi_q2", FREQ_SCALE), ("cbi_q3", FREQ_SCALE),
    ("cbi_q4", FREQ_SCALE), ("cbi_q5", FREQ_SCALE), ("cbi_q6", FREQ_SCALE),
    ("cbi_q7", DEGREE_SCALE), ("cbi_q8", DEGREE_SCALE), ("cbi_q9", DEGREE_SCALE),
    ("cbi_q10", FREQ_SCALE), ("cbi_q11", FREQ_SCALE), ("cbi_q12", FREQ_SCALE),
    ("cbi_q13", FREQ_SCALE),
]

# final item is reverse-scored
REVERSE_ITEM = 12
STEPS = [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12]]

class ReminderDialog(QDialog):
    def __init__(self, language="English", parent=None):
        super().__init__(parent)
        # Frameless card
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(440, 240)
        card = QFrame()
        card.setObjectName("thankYouCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        # Translated title and question
        title = QLabel(get_text(language, "cbi_reminder_title"))
        title.setObjectName("thankYouTitle")
        title.setAlignment(Qt.AlignCenter)
        message = QLabel(get_text(language, "cbi_reminder_message"))
        message.setObjectName("thankYouText")
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)

        # No and Yes buttons in the shared button styles
        no = QPushButton(get_text(language, "cbi_reminder_no"))
        no.setObjectName("secondaryButton")
        no.setFixedHeight(44)
        no.setCursor(Qt.PointingHandCursor)
        no.clicked.connect(self.reject)
        yes = QPushButton(get_text(language, "cbi_reminder_yes"))
        yes.setObjectName("primaryButton")
        yes.setFixedHeight(44)
        yes.setCursor(Qt.PointingHandCursor)
        yes.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addWidget(no)
        buttons.addWidget(yes)

        # Larger Tamil text when needed
        if language == "Tamil":
            title.setStyleSheet("font-size:15px;")
            message.setStyleSheet("font-size:12px;")

        # Card and outer layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addStretch()
        layout.addLayout(buttons)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(card)

# CBI questionnaire used for validation and ongoing self checks
class QuestionnairePage(QWidget):
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    assistant_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()
        # Start with no user English text and an empty set of answers
        self.current_language = "English"
        self.user_id = None
        self.first_name = ""
        self.answers = {}
        self.answer_labels = {}
        self.item_labels = {}
        self.item_buttons = {}
        self.item_groups = {}
        self.submitted = False

        # Shared sidebar wired to this page navigation signals
        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.trends_requested.connect(self.trends_requested.emit)
        self.sidebar.assistant_requested.connect(self.assistant_requested.emit)
        self.sidebar.settings_requested.connect(self.settings_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        self.set_active_sidebar()

        # Sidebar beside questionnaire content
        self.content = self.build_content()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.content, 1)
        self.set_language("English")

    # questionnaire button in the sidebar
    def set_active_sidebar(self):
        # highlights and select the questionnaire button
        buttons = list(self.sidebar.buttons())
        for button in buttons:
            button.setProperty("active", button is self.sidebar.questionnaire_button)
            button.style().unpolish(button)
            button.style().polish(button)

    # page content
    def build_content(self):
        content = QWidget()
        content.setObjectName("questionnaireContent")

        # Page heading and introduction
        self.title = QLabel()
        self.title.setObjectName("settingsPageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("settingsPageSubtitle")
        self.subtitle.setWordWrap(True)
        self.intro = QLabel()
        self.intro.setObjectName("privacyNote")
        self.intro.setWordWrap(True)

        # reminder shown when a weekly check in is due
        self.reminder_note = QLabel()
        self.reminder_note.setObjectName("questionnaireReminderNote")
        self.reminder_note.setWordWrap(True)
        self.reminder_note.hide()

        # One question card that holds the paginated steps
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(14)

        #five question steps followed by a thank you
        self.step_stack = QStackedWidget()
        for indices in STEPS:
            self.step_stack.addWidget(self.build_step(indices))
        self.step_stack.addWidget(self.build_done_step())

        # Progress text and navigation buttons
        self.progress_label = QLabel()
        self.progress_label.setObjectName("featureDescription")
        self.back_button = QPushButton()
        self.back_button.setObjectName("secondaryButton")
        self.back_button.setFixedHeight(44)
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.go_back)
        self.next_button = QPushButton()
        self.next_button.setObjectName("primaryButton")
        self.next_button.setFixedHeight(44)
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(self.go_next)

        # Navigation row under the steps
        self.nav_row = QHBoxLayout()
        self.nav_row.addWidget(self.progress_label)
        self.nav_row.addStretch()
        self.nav_row.addWidget(self.back_button)
        self.nav_row.addWidget(self.next_button)

        card_layout.addWidget(self.step_stack)
        card_layout.addLayout(self.nav_row)

        # page from header, headings and question card
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 18, 32, 24)
        layout.setSpacing(8)
        layout.addLayout(self.build_header())
        layout.addSpacing(4)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.intro)
        layout.addWidget(self.reminder_note)
        layout.addSpacing(6)
        layout.addWidget(card)
        # card hugging its content
        layout.addStretch() 
        return content
    
    # shared page header
    def build_header(self):
        from pathlib import Path
        from PySide6.QtGui import QPixmap
        # heart image beside the Solace name
        images = Path(__file__).resolve().parents[1] / "images"
        heart = QLabel()
        heart.setFixedSize(42, 42)
        heart.setAlignment(Qt.AlignCenter)
        heart.setPixmap(QPixmap(str(images / "heart.png")).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")
        # user label
        self.user_label = QLabel(self.first_name)
        self.user_label.setObjectName("welcomeLabel")
        self.user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(heart)
        row.addWidget(brand)
        row.addStretch()
        row.addWidget(self.user_label)
        # avatar
        add_avatar(row)
        return row

    # three questions
    def build_step(self, indices):
        page = QWidget()
        layout = QVBoxLayout(page)
        # layout spacing
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        for item_index in indices:
            layout.addWidget(self.build_question(item_index))
        return page

    # one question with its five answer options
    def build_question(self, item_index):
        question_key, scale = CBI_ITEMS[item_index]
        holder = QWidget()
        column = QVBoxLayout(holder)
        # columns spacing
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(8)

        # question text
        label = QLabel()
        label.setObjectName("cbiQuestion")
        label.setWordWrap(True)
        self.item_labels[item_index] = label
        column.addWidget(label)

        # five options as one exclusive group so only one can be chosen
        group = QButtonGroup(holder)
        group.setExclusive(True)
        options_row = QHBoxLayout()
        options_row.setSpacing(8)
        buttons = []
        for option_key, canonical, points in scale:
            option = QPushButton()
            option.setObjectName("questionnaireOption")
            option.setCheckable(True)
            option.setCursor(Qt.PointingHandCursor)
            # answer and refresh the Next button when chosen
            option.clicked.connect(lambda _=False, i=item_index, p=points, c=canonical: self.record_answer(i, p, c))
            group.addButton(option)
            options_row.addWidget(option, 1)
            buttons.append((option, option_key))
        self.item_buttons[item_index] = buttons
        # reset can un-check it
        self.item_groups[item_index] = group
        column.addLayout(options_row)
        return holder

    # thank you step shown after submitting
    def build_done_step(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        self.done_title = QLabel()
        self.done_title.setObjectName("historyEmptyTitle")
        self.done_title.setAlignment(Qt.AlignCenter)
        # done message
        self.done_message = QLabel()
        self.done_message.setObjectName("historyEmptyMessage")
        self.done_message.setAlignment(Qt.AlignCenter)
        self.done_message.setWordWrap(True)
        layout.addWidget(self.done_title)
        layout.addWidget(self.done_message)
        layout.addStretch()
        return page

    # chosen answer and update Next button state
    def record_answer(self, item_index, points, canonical):
        self.answers[item_index] = points
        self.answer_labels[item_index] = canonical
        self.update_nav()

    # text in the selected language
    def t(self, key):
        return get_text(self.current_language, key)

    # user shown on this page
    def set_user(self, full_name, user_id=None):
        # different user opens it, or after a completed submit
        changed = user_id != self.user_id
        self.user_id = user_id
        self.first_name = full_name.split()[0] if full_name else ""
        if hasattr(self, "user_label"):
            self.user_label.setText(self.first_name)
        # if user changed reset questionnaire
        if changed or self.submitted:
            self.submitted = False
            self.reset_questionnaire()
        else:
            # answers so user continues where they left off
            self.update_nav()
        due = user_id is not None and questionnaire_reminder_due(user_id)
        self.reminder_note.setVisible(bool(due))

    # Clear all answers and return to first step
    def reset_questionnaire(self):
        self.answers = {}
        self.answer_labels = {}
        # drop exclusivity so selected button can be unchecked
        for group in self.item_groups.values():
            group.setExclusive(False)
            for button in group.buttons():
                button.setChecked(False)
            group.setExclusive(True)
        self.step_stack.setCurrentIndex(0)
        self.update_nav()

    # progress text and  Back and Next buttons
    def update_nav(self):
        index = self.step_stack.currentIndex()
        last_step = len(STEPS) - 1

        # thank you step hides the navigation controls
        if index > last_step:
            for widget in (self.progress_label, self.back_button, self.next_button):
                widget.hide()
            return
        for widget in (self.progress_label, self.back_button, self.next_button):
            widget.show()

        # Progress text for current step
        indices = STEPS[index]
        self.progress_label.setText(self.t("cbi_progress").format(start=indices[0] + 1, end=indices[-1] + 1))
        # Back is available after first step
        self.back_button.setEnabled(index > 0)
        # final step submits
        self.next_button.setText(self.t("cbi_submit") if index == last_step else self.t("cbi_next"))
        # allow moving on once every question on this step is answered
        answered = all(item_index in self.answers for item_index in indices)
        self.next_button.setEnabled(answered)

    # Move to previous step
    def go_back(self):
        index = self.step_stack.currentIndex()
        if index > 0:
            self.step_stack.setCurrentIndex(index - 1)
            self.update_nav()

    # next step or submit on the final step
    def go_next(self):
        index = self.step_stack.currentIndex()
        # Submit when last question step is complete
        if index == len(STEPS) - 1:
            self.submit()
            return
        self.step_stack.setCurrentIndex(index + 1)
        self.update_nav()

    # Score the answers save and show thank you
    def submit(self):
        # every item to be answered before saving
        if len(self.answers) != len(CBI_ITEMS):
            return

        # Reverse score final item then average the CBI subscores
        points = [self.answers[i] for i in range(len(CBI_ITEMS))]
        points[REVERSE_ITEM] = 100 - points[REVERSE_ITEM]
        personal = round(mean(points[:6]), 2)
        work = round(mean(points[6:]), 2)
        overall = round(mean(points), 2)

        # canonical English answers so scoring stays language independent
        labels = [self.answer_labels[i] for i in range(len(CBI_ITEMS))]
        try:
            save_questionnaire(self.user_id, labels, personal, work, overall)
        # error
        except Exception as error:
            print("QUESTIONNAIRE SAVE ERROR:", error)

        # thank you and offer weekly reminders
        self.submitted = True
        self.step_stack.setCurrentIndex(len(STEPS))
        self.update_nav()
        self.offer_reminders()

    # user wants weekly reminders
    def offer_reminders(self):
        if self.user_id is None:
            return
        # Card styled yes no dialog in selected language
        dialog = ReminderDialog(self.current_language, self)
        set_questionnaire_reminders(self.user_id, dialog.exec() == QDialog.Accepted)

    # update page when it appears
    def showEvent(self, event):
        super().showEvent(event)
        self.sidebar.set_expanded(HoverSidebar._shared_expanded)
        float_in(self.content)

    # Update page for the selected language
    def set_language(self, language):
        self.current_language = language
        self.sidebar.set_language(language)

        # Translate headings, intro and reminder note
        self.title.setText(self.t("cbi_title"))
        self.subtitle.setText(self.t("cbi_subtitle"))
        self.intro.setText(self.t("cbi_intro"))
        self.back_button.setText(self.t("cbi_back"))
        self.reminder_note.setText(self.t("cbi_reminder_due"))
        self.done_title.setText(self.t("cbi_done_title"))
        self.done_message.setText(self.t("cbi_done_message"))

        # Translate every question and every option label
        for item_index, (question_key, _) in enumerate(CBI_ITEMS):
            self.item_labels[item_index].setText(self.t(question_key))
            for option, option_key in self.item_buttons[item_index]:
                option.setText(self.t(option_key))

        self.tamil_fonts()
        self.update_nav()

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"
        # main widgets with readable Tamil font sizes
        sizes = [(self.title, 18), (self.subtitle, 10), (self.intro, 10),(self.back_button, 10), (self.next_button, 10), (self.progress_label, 10)]
        for widget, size in sizes:
            widget.setStyleSheet(f"font-size:{max(size, 12)}px;" if tamil else "")
        # Questions and options need a slightly larger Tamil size
        for label in self.item_labels.values():
            label.setStyleSheet("font-size:13px;" if tamil else "")
        for buttons in self.item_buttons.values():
            for option, _ in buttons:
                option.setStyleSheet("font-size:12px;" if tamil else "")
