# Import required libraries
from UI.ui.account_widgets import add_avatar
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import QFrame,QHBoxLayout,QLabel,QLineEdit,QPushButton,QScrollArea,QSizePolicy,QStackedWidget,QVBoxLayout,QWidget
from UI.ai.solace_agent import SolaceAgent
from UI.ui.home_page import HoverSidebar
from UI.ui.ui_components import float_in
from UI.ui.translations import ENGLISH_TEXT, get_text

# English wording for the assistant page
ASSISTANT_TEXT = {
    "assistant": "Assistant",
    "assistant_title": "Solace Assistant",
    "assistant_subtitle": "Ask about Solace or your saved wellbeing history.",
    "assistant_hero_prompt": "How can I help you today?",
    "assistant_private": "Private by design — the Assistant only reads your locally saved Solace information.",
    "assistant_welcome": "Hi! I can explain how Solace works or help you understand your saved wellbeing history.",
    "assistant_disclaimer":"Solace is an experimental wellbeing support tool and does not provide medical diagnoses.",
    "assistant_placeholder": "Ask Solace a question...",
    "assistant_send": "Send",
    "assistant_clear": "Clear chat",
    "assistant_thinking": "Solace AI is thinking...",
    "assistant_error": "I could not answer that question. Please try again.",
    "assistant_suggestions": "Suggested questions",
    "assistant_suggestion_help": "How does Solace work?",
    "assistant_suggestion_latest": "What was my latest wellbeing score?",
    "assistant_suggestion_trend": "How have my recent scores changed?",
    "assistant_information_used": "Information used",
    "assistant_tool_solace_help": "Solace help",
    "assistant_tool_latest_check_in": "Latest check-in",
    "assistant_tool_recent_scores": "Recent scores",
    "assistant_tool_wellbeing_context": "Wellbeing context",
    "assistant_tool_recent_history": "Recent history",
    "assistant_tool_date_check_in": "Dated check-in",
    "assistant_tool_check_in_count": "Check-in count",
    "assistant_tool_safety_support": "Safety support",
    "assistant_tool_general": "General conversation"
}

# page wording to the shared translations
ENGLISH_TEXT.update(ASSISTANT_TEXT)

# assistant tools to their display labels
TOOL_TEXT_KEYS = {
    "solace_help": "assistant_tool_solace_help",
    "latest_check_in": "assistant_tool_latest_check_in",
    "recent_scores": "assistant_tool_recent_scores",
    "wellbeing_context": "assistant_tool_wellbeing_context",
    "recent_history": "assistant_tool_recent_history",
    "date_check_in": "assistant_tool_date_check_in",
    "check_in_count": "assistant_tool_check_in_count",
    "safety_support": "assistant_tool_safety_support",
    "general": "assistant_tool_general"
}

# assistant replies without blocking the interface
class AssistantWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self,question,user_id,language_name,history,parent=None):
        super().__init__(parent)
        self.question = question
        self.user_id = user_id
        self.language_name = (language_name)
        # separate copy of the chat history
        self.history = list(history)

    # Run task in the background
    def run(self):
        try:
            agent = SolaceAgent(user_id=self.user_id,language_name=(self.language_name))
            # assistant to answer using the chat history
            result = agent.answer(self.question,self.history)
            self.completed.emit(result)
        # error
        except Exception as error:
            self.failed.emit(str(error))

# assistant chat page
class AssistantPage(QWidget):
    # all the pages request
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()
        # Start empty conversation and no active worker
        self.current_language = ("English")
        self.user_id = None
        self.first_name = ""
        self.history = []
        self.worker = None

        # shared sidebar to this page navigation signals
        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.trends_requested.connect(self.trends_requested.emit)
        self.sidebar.settings_requested.connect(self.settings_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        self.set_active_sidebar()
        self.content = self.build_content()

        # layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0,)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.content,1)

        # set langauge to english and clear chat
        self.set_language("English")
        self.clear_chat()

    # Update page when it appears
    def showEvent(self, event):
        super().showEvent(event)
        self.sidebar.set_expanded(HoverSidebar._shared_expanded)
        float_in(self.content)

    # Get text in the selected language
    def t(self,key):
        return get_text(self.current_language,key)

    # Update page for the selected language
    def set_language(self,language):
        previous_language = (self.current_language)
        self.current_language = (language)
        self.sidebar.set_language(language)
        self.title.setText(self.t("assistant_title"))
        self.subtitle.setText(self.t("assistant_subtitle"))
        self.empty_prompt.setText(self.t("assistant_hero_prompt"))
        self.private_note.setText(self.t("assistant_private"))
        self.suggestions_title.setText(self.t("assistant_suggestions"))
        self.help_button.setText(self.t("assistant_suggestion_help"))
        self.latest_button.setText(self.t("assistant_suggestion_latest"))
        self.trend_button.setText(self.t("assistant_suggestion_trend"))
        self.question_input.setPlaceholderText(self.t("assistant_placeholder"))
        self.send_button.setText(self.t("assistant_send"))
        self.clear_button.setText(self.t("assistant_clear"))
        self.disclaimer.setText(self.t("assistant_disclaimer"))

        # Clear old language messages when the assistant is idle
        if (previous_language != language and self.history and not self.worker_running()):
            self.clear_chat()
        self.tamil_fonts()

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = (self.current_language == "Tamil")
        # widgets
        widgets = [
            (self.title,19),
            (self.subtitle,10),
            (self.private_note,9),
            (self.suggestions_title,10),
            (self.help_button,9),
            (self.latest_button,9),
            (self.trend_button,9),
            (self.question_input,10),
            (self.send_button,10),
            (self.clear_button,9),
            (self.disclaimer,9),
        ]

        # tamil font size
        for widget, size in widgets:
            widget.setStyleSheet(
                f"font-size:{max(size, 12)}px;"
                if tamil
                else ""
            )

    # Set user shown on this page
    def set_user(self,full_name,user_id=None):
        # Check different account has been selected
        changed_user = (self.user_id is not None and self.user_id != user_id)
        self.user_id = user_id
        self.first_name = (
            full_name.split()[0]
            if full_name
            else ""
        )

        # user label
        if hasattr(self, "user_label"):
            self.user_label.setText(self.first_name)

        # Clear previous account chat when the assistant is idle
        if (changed_user and not self.worker_running()):
            self.clear_chat()

    # current sidebar page
    def set_active_sidebar(self):
        buttons = [self.sidebar.home_button, self.sidebar.check_in_button, self.sidebar.trends_button, self.sidebar.settings_button]

        # assistant button if the sidebar has one
        assistant_button = getattr(self.sidebar, "assistant_button", None)

        if assistant_button:
            buttons.append(assistant_button)

        # Clear old sidebar highlight before selecting the assistant
        for button in buttons:
            button.setProperty("active", False)

        # assistant buttons
        if assistant_button:
            assistant_button.setProperty("active", True)

        for button in buttons:
            button.style().unpolish(button)
            button.style().polish(button)


    # Build content
    def build_content(self):
        content = QWidget()
        content.setObjectName("assistantContent")
        content.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)

        # assistant heading and introductory text
        self.title = QLabel("Solace Assistant")
        self.title.setObjectName("assistantTitle")
        self.subtitle = QLabel("Ask about Solace or your saved wellbeing history.")
        self.subtitle.setObjectName("assistantSubtitle")
        self.subtitle.setWordWrap(True)
        self.private_note = QLabel("Private by design — the Assistant only reads your locally saved Solace information.")
        self.private_note.setObjectName("assistantPrivateNote")
        self.private_note.setWordWrap(True)
        self.clear_button = QPushButton("Clear chat")
        self.clear_button.setObjectName("assistantClearButton")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setFixedHeight(38)
        self.clear_button.clicked.connect(self.clear_chat)

        # introduction and clear chat button in a card
        hero = QFrame()
        hero.setObjectName("assistantHeroCard")
        hero.setAttribute(Qt.WA_StyledBackground,True)
        hero.setMinimumHeight(124)
        hero_text = QVBoxLayout()
        hero_text.setContentsMargins(0, 0, 0, 0)
        hero_text.setSpacing(5)
        hero_text.addWidget(self.title)
        hero_text.addWidget(self.subtitle)
        hero_text.addWidget(self.private_note)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28,20,24,20)
        hero_layout.setSpacing(20)
        hero_layout.addLayout(hero_text,1)
        hero_layout.addWidget(self.clear_button,0,Qt.AlignTop)
        
        # disclaimer and a label for status messages
        self.disclaimer = QLabel("Solace is an experimental wellbeing support tool and does not provide medical diagnoses.")
        self.disclaimer.setObjectName("assistantDisclaimer")
        self.disclaimer.setAlignment(Qt.AlignCenter)
        self.disclaimer.setWordWrap(True)
        self.status_label = QLabel("")
        self.status_label.setObjectName("assistantStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        self.hero_card_widget = hero

        # build chat area suggested questions and message input
        chat_area = self.build_chat_area()
        suggestions = self.build_suggestions()
        composer = self.build_input()
        self.empty_prompt = QLabel()
        self.empty_prompt.setObjectName("assistantHeroPrompt")
        self.empty_prompt.setAlignment(Qt.AlignCenter)
        self.empty_prompt.setWordWrap(True)

        # welcome prompt and input before first message
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setContentsMargins(60, 0, 60, 0)
        empty_layout.setSpacing(18)
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_prompt)
        self.empty_slot = QVBoxLayout()
        self.empty_slot.setSpacing(14)
        empty_layout.addLayout(self.empty_slot)
        empty_layout.addStretch()

        # conversation with input at bottom
        active_page = QWidget()
        active_layout = QVBoxLayout(active_page)
        active_layout.setContentsMargins(0, 0, 0, 0)
        active_layout.setSpacing(10)
        active_layout.addWidget(chat_area, 1)
        self.active_slot = QVBoxLayout()
        self.active_slot.setSpacing(10)
        active_layout.addLayout(self.active_slot)

        # welcome and conversation layouts in separate pages
        self.state_stack = QStackedWidget()
        self.state_stack.addWidget(empty_page)
        self.state_stack.addWidget(active_page)

        # references so input and suggestions can move between pages
        self._suggestions_layout = suggestions
        self._composer = composer

        # old hero card hidden
        hero.hide()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 18, 38, 22)
        layout.setSpacing(12)
        layout.addLayout(self.build_header())
        layout.addSpacing(2)
        layout.addWidget(self.state_stack, 1)
        layout.addWidget(self.disclaimer)
        self.show_empty_state()
        return content

    # Move layout into another layout
    def _move_layout(self, child_layout, target_layout):
        parent = child_layout.parent()
        # remove layout from its old vertical container
        if isinstance(parent, QVBoxLayout):
            parent.removeItem(child_layout)
        target_layout.addLayout(child_layout)

    # Move widget into another layout
    def _move_widget(self, widget, target_layout):
        widget.setParent(None)
        target_layout.addWidget(widget)

    # Show starting chat layout
    def show_empty_state(self):
        # centered prompt and input and suggestions
        self._move_widget(self._composer, self.empty_slot)
        self._move_layout(self._suggestions_layout, self.empty_slot)
        self.state_stack.setCurrentIndex(0)

    # Show layout for an active chat
    def show_active_state(self):
        # fills the page input pinned to bottom
        self._move_widget(self._composer, self.active_slot)
        self._move_layout(self._suggestions_layout, self.active_slot)
        self.state_stack.setCurrentIndex(1)

    # Build header
    def build_header(self):
        heart = QLabel()
        heart.setFixedSize(42,42)
        heart.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        from pathlib import Path
        # root and image path
        root = (Path(__file__).resolve().parents[2])
        image_path = (root / "UI" / "images" / "heart.png")

        # heart image
        heart.setPixmap(QPixmap(str(image_path)).scaled(60,60,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        # user label
        self.user_label = QLabel(self.first_name)
        self.user_label.setObjectName("welcomeLabel")
        self.user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # row
        row = QHBoxLayout()
        row.setSpacing(2)
        row.addWidget(heart)
        row.addWidget(brand)
        row.addStretch()
        row.addWidget(self.user_label)
        add_avatar(row)
        return row

    # Build chat area
    def build_chat_area(self):
        # scrollable area for the conversation
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("assistantChatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_container = QWidget()
        self.chat_container.setObjectName("assistantChatContainer")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(20,20,20,20)
        self.chat_layout.setSpacing(12)

        # flexible space below the chat messages
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_container)
        self.chat_scroll.setMinimumHeight(320)
        return self.chat_scroll


    # Build suggestions
    def build_suggestions(self):
        layout = QVBoxLayout()
        layout.setSpacing(7)
        self.suggestions_title = QLabel("Suggested questions")
        self.suggestions_title.setObjectName("assistantSuggestionsTitle")
        layout.addWidget(self.suggestions_title)

        # three suggested question buttons
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.help_button = (self.make_suggestion_button("How does Solace work?"))
        self.latest_button = (self.make_suggestion_button("What was my latest wellbeing score?"))
        self.trend_button = (self.make_suggestion_button("How have my recent scores changed?"))

        # translated question when a suggestion is selected
        self.help_button.clicked.connect(lambda:self.ask_suggestion(self.t("assistant_suggestion_help")))
        self.latest_button.clicked.connect(lambda:self.ask_suggestion(self.t("assistant_suggestion_latest")))
        self.trend_button.clicked.connect(lambda:self.ask_suggestion(self.t("assistant_suggestion_trend")))
        buttons.addWidget(self.help_button)
        buttons.addWidget(self.latest_button)
        buttons.addWidget(self.trend_button)
        layout.addLayout(buttons)
        return layout

    # suggested question button
    def make_suggestion_button(self,text):
        button = QPushButton(text)
        button.setObjectName("assistantSuggestionButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        return button

    # Build input
    def build_input(self):
        composer = QFrame()
        composer.setObjectName("assistantComposer")
        composer.setAttribute(Qt.WA_StyledBackground,True)
        layout = QHBoxLayout(composer)
        layout.setContentsMargins(8,8,8,8)
        layout.setSpacing(9)

        # Create question input and send button
        self.question_input = QLineEdit()
        self.question_input.setObjectName("assistantQuestionInput")
        self.question_input.setPlaceholderText("Ask Solace a question...")
        self.question_input.setClearButtonEnabled(True)
        self.question_input.setFixedHeight(44)

        # Enter to send typed question
        self.question_input.returnPressed.connect(self.send_question)
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("assistantSendButton")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.setFixedSize(112,44)
        self.send_button.clicked.connect(self.send_question)
        layout.addWidget(self.question_input,1)
        layout.addWidget(self.send_button)
        return composer

    # add user or assistant message bubble
    def add_message(self,text,role,tool=None):
        frame = QFrame()
        frame.setAttribute(Qt.WA_StyledBackground,True)

        # message bubble fit its contents
        frame.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)

        # if user
        if role == "user":
            frame.setObjectName("assistantUserMessage")
        else:
            frame.setObjectName("assistantBotMessage")
        message = QLabel(str(text))

        # user input plain and allow Markdown in assistant replies
        message.setTextFormat(Qt.PlainText if role == "user" else Qt.MarkdownText)
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message.setObjectName("assistantUserMessageText" if role == "user" else "assistantBotMessageText")
        message.setMaximumWidth(620 if role == "user" else 720)
        message.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)

        # bubble layout
        bubble_layout = QVBoxLayout(frame)
        bubble_layout.setContentsMargins(16,11,16,11)
        bubble_layout.setSpacing(7)
        bubble_layout.addWidget(message)

        # source when a reply used a known tool
        if (role == "assistant" and tool and tool in TOOL_TEXT_KEYS):
            tool_label = QLabel((
                    f"{self.t('assistant_information_used')}: "
                    f"{self.t(TOOL_TEXT_KEYS[tool])}"
                )
            )
            tool_label.setObjectName("assistantToolLabel")
            bubble_layout.addWidget(tool_label)

        # row widget
        row_widget = QWidget()
        row_widget.setObjectName("assistantMessageRow")
        row_widget.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Maximum)
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(2,0,2,0)
        row.setSpacing(0)

        # user messages on the right
        if role == "user":
            row.addStretch(1)
            row.addWidget(frame,0,Qt.AlignRight | Qt.AlignTop)
            metrics = QFontMetrics(message.font())

            # widest line in the message
            longest_line = max((metrics.horizontalAdvance(line) for line in str(text).splitlines()),default=0)
            bubble_width = min(max(longest_line + 44, 72),660)
            frame.setFixedWidth(bubble_width)
        else:
            row.addWidget(frame,0,Qt.AlignLeft | Qt.AlignTop)
            row.addStretch(1)
            frame.setMinimumWidth(390)
            frame.setMaximumWidth(760)
        # new messages above bottom spacer
        self.chat_layout.insertWidget(self.chat_layout.count() - 1,row_widget,)
        # text label available for the typing effect
        row_widget.message_label = message
        QTimer.singleShot(0, self.scroll_to_bottom)
        return row_widget

    # Show assistant is working
    def add_thinking_message(self):
        self.remove_thinking_message()
        frame = QFrame()
        frame.setObjectName("assistantThinkingMessage")
        frame.setAttribute(Qt.WA_StyledBackground,True)
        frame.setMinimumWidth(230)
        frame.setMaximumWidth(320)

        # text
        text = QLabel(self.t("assistant_thinking"))
        text.setObjectName("assistantThinkingText")
        text.setWordWrap(False)

        # bubble layout
        bubble_layout = QVBoxLayout(frame)
        bubble_layout.setContentsMargins(16,10,16,10)
        bubble_layout.addWidget(text)

        # row widget
        row_widget = QWidget()
        row_widget.setObjectName("assistantMessageRow")
        row_widget.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Maximum)

        # row
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(2,0,2,0)
        row.addWidget(frame,0, Qt.AlignLeft | Qt.AlignTop,)
        row.addStretch(1)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1,row_widget)

        # remember thinking message so it can be removed later
        self.thinking_row = row_widget
        QTimer.singleShot(0,self.scroll_to_bottom)

    # Remove thinking message
    def remove_thinking_message(self):
        row_widget = getattr(self,"thinking_row",None)

        # if row widget is none
        if row_widget is None:
            return

        # Remove and release thinking message widget
        self.chat_layout.removeWidget(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()
        self.thinking_row = None

    # assistant welcome message
    def add_welcome_message(self):
        return self.add_message(self.t("assistant_welcome"),"assistant")

    # Clear current chat when the assistant is idle
    def clear_chat(self):
        # current answer before clearing chat
        if self.worker_running():
            return

        self.history = []

        # remove messages while keeping the bottom spacer
        while (self.chat_layout.count() > 1):
            item = (self.chat_layout.takeAt(0))
            widget = (item.widget())

            if widget:
                widget.deleteLater()

        self.show_empty_state()
        self.status_message("")

    # suggested questions
    def ask_suggestion(self,question,):
        if self.worker_running():
            return

        self.question_input.setText(question)
        self.send_question()

    # typed question
    def send_question(self):
        if self.worker_running():
            return

        # read question without surrounding spaces
        question = (self.question_input.text().strip())

        if not question:
            return

        # switch from welcome view for first question
        if self.state_stack.currentIndex() == 0:
            self.show_active_state()

        # earlier messages before adding this question
        previous_history = list(self.history)
        self.add_message(question,"user")
        self.history.append({"role": "user","content": question})

        # Limit chat history to most recent messages
        self.trim_history()
        self.question_input.clear()

        # disable input and show progress while the assistant answers
        self.set_busy(True)
        self.add_thinking_message()

        # worker and connect its result, error and cleanup handlers
        self.worker = AssistantWorker(question,self.user_id,self.current_language,previous_history,self)
        self.worker.completed.connect(self.answer_ready)
        self.worker.failed.connect(self.answer_failed)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    # reply returned by assistant
    def answer_ready(self,result):
        # read answer and remove surrounding spaces
        answer = str(result.get("answer","")).strip()
        tool = result.get("tool")

        # fallback message for an empty answer
        if not answer:
            answer = self.t("assistant_error")
        self.remove_thinking_message()
        self.type_out_message(answer, tool)

        # assistant reply to chat history
        self.history.append({"role": "assistant","content": answer})
        self.trim_history()
        self.status_message("")

    # reveal reply a little at a time
    def type_out_message(self, answer, tool):
        row_widget = self.add_message("", "assistant", tool)
        label = getattr(row_widget, "message_label", None)

        # if label is none
        if label is None:
            return

        # plain text while the reply is appearing
        label.setTextFormat(Qt.PlainText)
        self._type_full_text = answer
        self._type_label = label
        self._type_index = 0

        # how many characters to show at each tick
        self._type_step = max(1, len(answer) // 90)

        # timer to reveal the reply gradually
        self._type_timer = QTimer(self)
        self._type_timer.setInterval(18)
        self._type_timer.timeout.connect(self._type_tick)
        self._type_timer.start()

    # Show next part of the reply
    def _type_tick(self):
        self._type_index += self._type_step
        # Check whether the whole reply has appeared
        if self._type_index >= len(self._type_full_text):
            self._type_label.setTextFormat(Qt.MarkdownText)
            self._type_label.setText(self._type_full_text)
            self._type_timer.stop()
            self._type_timer.deleteLater()
        else:
            self._type_label.setText(self._type_full_text[: self._type_index])
        self.scroll_to_bottom()


    # Show message if the assistant fails
    def answer_failed(self,message):
        # Print error
        print("ASSISTANT ERROR:",message)
        error_text = self.t("assistant_error")
        self.remove_thinking_message()
        self.add_message(error_text,"assistant")
        self.history.append(
            {
                "role": "assistant",
                "content": error_text,
            }
        )
        # trim history and status message
        self.trim_history()
        self.status_message("")

    # Release finished background worker
    def worker_finished(self):
        self.set_busy(False)

        # Clear and release finished worker before accepting more input
        worker = (self.worker)
        self.worker = None
        if worker:
            worker.deleteLater()
        # set focus
        self.question_input.setFocus()

    # Check whether assistant is still working
    def worker_running(self):
        return (self.worker is not None and self.worker.isRunning())
    
    # Update controls while a task is running
    def set_busy(self,busy):
        # enable controls only when assistant is idle
        enabled = not busy
        self.sidebar.setEnabled(enabled)
        self.question_input.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.help_button.setEnabled(enabled)
        self.latest_button.setEnabled(enabled)
        self.trend_button.setEnabled(enabled)
        
        # Hide suggestions while a reply is being generated
        suggestions_visible = not busy
        self.suggestions_title.setVisible(suggestions_visible)
        self.help_button.setVisible(suggestions_visible)
        self.latest_button.setVisible(suggestions_visible)
        self.trend_button.setVisible(suggestions_visible)

    # Keep only the latest chat messages
    def trim_history(self):
        self.history = (self.history[-10:])

    # Update the assistant status text
    def status_message(self,text):
        self.status_label.setText(text)
        self.status_label.hide()

    # Scroll down to the newest message
    def scroll_to_bottom(self):
        bar = (self.chat_scroll.verticalScrollBar())
        bar.setValue(bar.maximum())

    # Refresh the page contents
    def refresh_page(self):
        self.set_active_sidebar()
        if not self.worker_running():
            self.question_input.setFocus()