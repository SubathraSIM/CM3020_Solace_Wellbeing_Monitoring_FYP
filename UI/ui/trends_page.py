# Import required libraries
from matplotlib import image
from UI.ui.account_widgets import add_avatar
import re
from pathlib import Path
from PySide6.QtCore import QDate, QLocale, QRectF, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QCalendarWidget, QComboBox, QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from UI.database.database import get_check_in_dates, get_check_in_for_date, get_month_check_ins
from UI.ui.check_in_page import MiniTrendGraph
from UI.ui.home_page import HoverSidebar
from UI.ui.ui_components import float_in
from UI.ui.translations import ENGLISH_TEXT, get_text, translate_texts

# project folder
ROOT = Path(__file__).resolve().parents[2]

# images folder
IMAGES = ROOT / 'UI' / 'images'

# Match each language to its date format
LOCALES = {'English': 'en_SG', 'Malay': 'ms_MY', 'Chinese': 'zh_CN', 'Tamil': 'ta_IN'}

# Keep the English wording for the history page
TREND_TEXT = {'history_title': 'Wellbeing history', 'history_subtitle': 'Select a date to review the wellbeing summary saved for that check-in.', 'monthly_trend': "This month's trend", 'trend_note': 'Each point represents a saved check-in.', 'trend_empty': 'Complete at least 7 check-ins to unlock your monthly trend.', 'checkin_calendar': 'Check-in calendar', 'calendar_note': 'A grey dot marks a date with a saved check-in.', 'saved_checkin': 'Saved check-in', 'select_date': 'Select a date', 'select_date_note': 'Select a date with a grey dot to review a saved wellbeing summary.', 'no_checkin': 'No check-in was completed on this date.', 'latest_checkin': 'Latest check-in at', 'input_used': 'Input used', 'history_transcript': 'Transcript', 'history_recommendations': 'Supportive recommendations', 'history_signals': 'Supporting signals'}

# history page wording to shared translations
ENGLISH_TEXT.update(TREND_TEXT)

# Translate saved check-in text in the background
class HistoryTranslationWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, check_in, language, request_id, parent=None):
        super().__init__(parent)
        # separate copy of the saved check-in
        self.check_in = dict(check_in)
        self.language = language
        # translation request this worker belongs to
        self.request_id = request_id

    # run this task in the background
    def run(self):
        try:
            # Collect saved summary, explanation and recommendations
            texts = [self.check_in.get('summary', ''), self.check_in.get('explanation', ''), self.check_in.get('recommendation', '')]

            # Check whether the original transcript needs translation
            translate_transcript = self.language != self.check_in.get('original_language')
            if translate_transcript:
                texts.append(self.check_in.get('transcript', ''))

            # Translate the selected history text
            translated = translate_texts(texts, self.language)
            transcript = translated[3] if translate_transcript else self.check_in.get('transcript_original', self.check_in.get('transcript', ''))

            # Send translated text with its request details
            self.completed.emit({'request_id': self.request_id, 'language': self.language, 'phrase': translated[0], 'explanation': translated[1], 'recommendation': translated[2], 'transcript': transcript})
        except Exception as error:
            self.failed.emit(str(error))

# calendar dates with saved check-ins
class CheckInCalendar(QCalendarWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        # saved dates
        self.saved_dates = set()

    # Update the calendar dates that have check-ins
    def set_saved_dates(self, dates):
        # Keep the saved dates in a consistent text format
        self.saved_dates = {date.toString('yyyy-MM-dd') for date in dates}
        self.updateCells()

    # Draw a calendar day and its saved check in marker
    def paintCell(self, painter, rect, date):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(rect, QColor('#FFFFFF'))
        # Check whether this is the selected date
        selected = date == self.selectedDate()
        current_month = date.year() == self.yearShown() and date.month() == self.monthShown()
        # highlight the selected date
        if selected:
            diameter = min(38, rect.width() - 8, rect.height() - 6)
            centre = rect.center()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#0875CE'))
            painter.drawEllipse(QRectF(centre.x() - diameter / 2, centre.y() - diameter / 2 - 1, diameter, diameter))
            painter.setPen(QColor('#FFFFFF'))

        # normal text colour for this month
        elif current_month:
            painter.setPen(QColor('#111827'))
        else:
            painter.setPen(QColor('#9CA3AF'))
        painter.drawText(rect.adjusted(0, -2, 0, -2), Qt.AlignCenter, str(date.day()))

        # saved dates unless they are already selected
        if date.toString('yyyy-MM-dd') in self.saved_dates and (not selected):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#9CA3AF'))
            painter.drawEllipse(QRectF(rect.center().x() - 2.5, rect.bottom() - 7, 5, 5))
        painter.restore()

# saved check-ins and recent wellbeing trends
class TrendsPage(QWidget):
    home_requested = Signal()
    check_in_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()
        # start without a selected user and use English text
        self.user_id = None
        self.current_language = 'English'

        # Track translation requests, workers and cached results
        self.translation_request = 0
        self.translation_workers = set()
        self.translation_cache = {}
        self.locale = QLocale(LOCALES['English'])

        # Connect the shared sidebar to history navigation
        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        self.set_active_sidebar()

        # Place sidebar beside the history content
        content = self.build_content()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(content, 1)
        self.set_language('English')

    # current sidebar page
    def set_active_sidebar(self):
        # old navigation highlights and select trends
        buttons = (self.sidebar.home_button, self.sidebar.check_in_button, self.sidebar.trends_button)
        for button in buttons:
            button.setProperty('active', False)
        self.sidebar.trends_button.setProperty('active', True)
        for button in buttons:
            button.style().unpolish(button)
            button.style().polish(button)

    # Build content
    def build_content(self):
        content = QWidget()
        content.setObjectName('trendsPageContent')
        self.title = QLabel()
        self.title.setObjectName('trendsPageTitle')
        self.subtitle = QLabel()
        self.subtitle.setObjectName('trendsPageSubtitle')
        self.subtitle.setWordWrap(True)

        # graph and calendar beside saved summary
        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(18)
        left.addWidget(self.build_graph_card())
        left.addWidget(self.build_calendar_card())
        body.addLayout(left, 2)
        body.addWidget(self.build_summary_panel(), 3)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 18, 28, 26)
        layout.setSpacing(14)
        layout.addLayout(self.build_header())
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(body, 1)
        self.content = content

        # return the content
        return content

    # Build the header
    def build_header(self):
        # Build the heart and Solace header
        heart = QLabel()
        heart.setFixedSize(42, 42)
        heart.setPixmap(QPixmap(str(IMAGES / "heart.png")).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        heart.setAlignment(Qt.AlignCenter)
        brand = QLabel('Solace')
        brand.setObjectName('homeBrand')
        self.user_label = QLabel()
        self.user_label.setObjectName('welcomeLabel')
        self.user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout = QHBoxLayout()
        layout.setSpacing(7)
        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()
        layout.addWidget(self.user_label)

        # Add the profile avatar to the header
        add_avatar(layout)
        return layout

    # build the graph card
    def build_graph_card(self):
        # Create the card that holds the trend graph
        card = QFrame()
        card.setObjectName('trendsGraphCard')
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumWidth(335)
        card.setMaximumWidth(390)
        self.graph_title = QLabel()
        self.graph_title.setObjectName('trendsCardTitle')
        self.graph_note = QLabel()
        self.graph_note.setObjectName('trendsCardNote')
        self.graph_note.setWordWrap(True)

        # Create the graph and its missing history message
        self.trend_graph = MiniTrendGraph()

        # graph needs more saved check-ins
        self.trend_empty = QLabel()
        self.trend_empty.setObjectName('trendRequirement')
        self.trend_empty.setAlignment(Qt.AlignCenter)
        self.trend_empty.setWordWrap(True)
        self.trend_empty.hide()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        layout.addWidget(self.graph_title)
        layout.addWidget(self.graph_note)
        layout.addWidget(self.trend_graph, 1)
        layout.addWidget(self.trend_empty)
        return card

    # Build the calendar card
    def build_calendar_card(self):
        card = QFrame()
        card.setObjectName('trendsCalendarCard')
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumWidth(335)
        card.setMaximumWidth(390)
        self.calendar_title = QLabel()
        self.calendar_title.setObjectName('trendsCardTitle')
        self.calendar_note = QLabel()
        self.calendar_note.setObjectName('trendsCardNote')
        self.calendar_note.setWordWrap(True)

        # calendar used to select saved check-ins
        self.calendar = CheckInCalendar()
        self.calendar.setObjectName('wellbeingCalendar')
        self.calendar.setGridVisible(False)
        self.calendar.setMaximumHeight(270)

        # built-in calendar navigation with custom controls
        self.calendar.setNavigationBarVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)

        # Prevent selecting future dates
        self.calendar.setMaximumDate(QDate.currentDate())
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # saved information when the month or date changes
        self.calendar.currentPageChanged.connect(self.calendar_page_changed)
        self.calendar.selectionChanged.connect(self.load_selected_date)

        # create buttons for moving between months
        self.nav_prev = QPushButton('<')
        self.nav_next = QPushButton('>')
        for button in (self.nav_prev, self.nav_next):
            button.setObjectName('calNavArrow')
            button.setFixedSize(34, 30)
            button.setCursor(Qt.PointingHandCursor)
        self.nav_prev.clicked.connect(lambda: self.move_month(-1))
        self.nav_next.clicked.connect(lambda: self.move_month(1))

        # menus for selecting the month and year
        self.month_combo = QComboBox()
        self.month_combo.setObjectName('calNavCombo')
        self.month_combo.setCursor(Qt.PointingHandCursor)
        self.year_combo = QComboBox()
        self.year_combo.setObjectName('calNavCombo')
        self.year_combo.setCursor(Qt.PointingHandCursor)

        # current year and the previous ten years
        year = QDate.currentDate().year()
        for value in range(year - 10, year + 1):
            self.year_combo.addItem(str(value), value)

        # calendar in sync with both menus
        self.month_combo.currentIndexChanged.connect(self.nav_changed)
        self.year_combo.currentIndexChanged.connect(self.nav_changed)
        nav = QHBoxLayout()
        nav.setContentsMargins(6, 4, 6, 4)
        nav.setSpacing(6)
        nav.addWidget(self.nav_prev)
        nav.addWidget(self.month_combo, 1)
        nav.addWidget(self.year_combo, 1)
        nav.addWidget(self.nav_next)
        nav_bar = QFrame()
        nav_bar.setObjectName('calNavBar')
        nav_bar.setAttribute(Qt.WA_StyledBackground, True)
        nav_bar.setLayout(nav)

        # legend for dates that contain a saved check in
        dot = QLabel()
        dot.setObjectName('calendarLegendDot')
        dot.setFixedSize(16, 16)
        dot.setAlignment(Qt.AlignCenter)
        dot.setPixmap(QPixmap(str(IMAGES / "dot.png")).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.legend_text = QLabel()
        self.legend_text.setObjectName('calendarLegendText')
        legend = QHBoxLayout()
        legend.setSpacing(7)
        legend.addWidget(dot)
        legend.addWidget(self.legend_text)
        legend.addStretch()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(self.calendar_title)
        layout.addWidget(self.calendar_note)
        layout.addWidget(nav_bar)
        layout.addWidget(self.calendar, 1)
        layout.addLayout(legend)
        return card

    # summary panel
    def build_summary_panel(self):
        panel = QFrame()
        panel.setObjectName('historyPanel')
        panel.setAttribute(Qt.WA_StyledBackground, True)

        # empty view and saved summary
        self.summary_stack = QStackedWidget()
        self.empty_state = self.build_empty_state()
        self.summary_state = self.build_summary_state()
        self.summary_stack.addWidget(self.empty_state)
        self.summary_stack.addWidget(self.summary_state)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.summary_stack)
        return panel

    # empty state
    def build_empty_state(self):
        page = QWidget()
        page.setObjectName('historyEmptyState')

        # selected date and an empty history message
        self.empty_date = QLabel()
        self.empty_date.setObjectName('historyEmptyTitle')
        self.empty_date.setAlignment(Qt.AlignCenter)
        self.empty_message = QLabel()
        self.empty_message.setObjectName('historyEmptyMessage')
        self.empty_message.setAlignment(Qt.AlignCenter)
        self.empty_message.setWordWrap(True)

        # empty history message inside the panel
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 42, 42, 42)
        layout.addStretch()
        layout.addWidget(self.empty_date)
        layout.addWidget(self.empty_message)
        layout.addStretch()
        return page

    # summary state
    def build_summary_state(self):
        page = QWidget()
        page.setObjectName('historySummaryState')

        # long saved summaries to scroll
        scroll = QScrollArea()
        scroll.setObjectName('historyScrollArea')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName('historyScrollContent')

        # saved check in date and time
        self.selected_date = QLabel()
        self.selected_date.setObjectName('historySelectedDate')
        self.selected_time = QLabel()
        self.selected_time.setObjectName('historySelectedTime')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.selected_date)
        layout.addWidget(self.selected_time)

        # summary, signals, transcript and recommendations
        layout.addWidget(self.build_saved_summary_card())
        layout.addWidget(self.build_signals_card())
        layout.addWidget(self.build_transcript_card())
        layout.addWidget(self.build_recommendation_card())
        layout.addStretch()
        scroll.setWidget(content)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return page

    # saved summary card
    def build_saved_summary_card(self):
        card = QFrame()
        card.setObjectName('historySummaryCard')
        card.setAttribute(Qt.WA_StyledBackground, True)

        # result image and summary text
        self.history_image = QLabel()
        self.history_image.setObjectName('historyResultImage')
        self.history_image.setFixedSize(QSize(150, 150))
        self.history_image.setAlignment(Qt.AlignCenter)
        self.history_phrase = QLabel()
        self.history_phrase.setObjectName('historyPhrase')
        self.history_phrase.setWordWrap(True)
        self.history_explanation = QLabel()
        self.history_explanation.setObjectName('historyExplanation')
        self.history_explanation.setWordWrap(True)

        # saved score on a bar from 0 to 100
        self.history_progress = QProgressBar()
        self.history_progress.setObjectName('trendHistoryProgress')
        self.history_progress.setRange(0, 100)
        self.history_input = QLabel()
        self.history_input.setObjectName('historyInputType')
        text = QVBoxLayout()
        text.setSpacing(8)
        text.addWidget(self.history_phrase)
        text.addWidget(self.history_explanation)
        text.addWidget(self.history_progress)
        text.addWidget(self.history_input)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)
        layout.addWidget(self.history_image, 0, Qt.AlignTop)
        layout.addLayout(text, 1)
        return card

    # signals card
    def build_signals_card(self):
        card = QFrame()
        card.setObjectName('historyDetailsCard')
        card.setAttribute(Qt.WA_StyledBackground, True)
        self.signals_title = QLabel()
        self.signals_title.setObjectName('trendsCardTitle')

        # references to the supporting signal labels and values
        self.signal_names = {}
        self.signal_values = {}
        rows = QVBoxLayout()
        rows.setSpacing(6)

        # display row for each supporting signal
        for key in ('blink_rate', 'head_position', 'speech_rate', 'disfluency', 'lexical_variety'):
            name = QLabel()
            name.setObjectName('scoreCaveat')
            value = QLabel()
            value.setObjectName('scoreLabel')
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.signal_names[key] = name
            self.signal_values[key] = value
            row = QHBoxLayout()
            row.addWidget(name)
            row.addStretch()
            row.addWidget(value)
            rows.addLayout(row)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self.signals_title)
        layout.addLayout(rows)
        return card

    # transcript card
    def build_transcript_card(self):
        card = QFrame()
        card.setObjectName('historyDetailsCard')
        card.setAttribute(Qt.WA_StyledBackground, True)
        self.transcript_title = QLabel()
        self.transcript_title.setObjectName('trendsCardTitle')

        # saved transcript without allowing edits
        self.history_transcript = QPlainTextEdit()
        self.history_transcript.setObjectName('historyTranscript')
        self.history_transcript.setReadOnly(True)
        self.history_transcript.setMinimumHeight(92)
        self.history_transcript.setMaximumHeight(125)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self.transcript_title)
        layout.addWidget(self.history_transcript)
        return card

    # recommendation card
    def build_recommendation_card(self):
        card = QFrame()
        card.setObjectName('historyDetailsCard')
        card.setAttribute(Qt.WA_StyledBackground, True)
        self.recommendation_title = QLabel()
        self.recommendation_title.setObjectName('trendsCardTitle')

        # separate layout for recommendation cards
        self.recommendation_layout = QVBoxLayout()
        self.recommendation_layout.setSpacing(8)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self.recommendation_title)
        layout.addLayout(self.recommendation_layout)
        return card

    # Get text in selected language
    def t(self, key):
        return get_text(self.current_language, key)

    # Update the page for the selected language
    def set_language(self, language):
        # Make earlier translation requests out of date
        self.translation_request += 1
        self.current_language = language
        self.locale = QLocale(LOCALES[language])
        self.sidebar.set_language(language)
        self.calendar.setLocale(self.locale)

        # translate the static history labels
        self.title.setText(self.t('history_title'))
        self.subtitle.setText(self.t('history_subtitle'))
        self.graph_title.setText(self.t('monthly_trend'))
        self.graph_note.setText(self.t('trend_note'))
        self.trend_empty.setText(self.t('trend_empty'))
        self.calendar_title.setText(self.t('checkin_calendar'))
        self.calendar_note.setText(self.t('calendar_note'))
        self.legend_text.setText(self.t('saved_checkin'))
        self.signals_title.setText(self.t('history_signals'))
        self.transcript_title.setText(self.t('history_transcript'))
        self.recommendation_title.setText(self.t('history_recommendations'))
        for key, label in self.signal_names.items():
            label.setText(self.t(key))

        # month names and Tamil font sizes
        self.update_month_names()
        self.tamil_fonts()

    # month names in the chosen language
    def update_month_names(self):
        month = self.calendar.monthShown()

        # Pause menu signals while replacing the month names
        self.month_combo.blockSignals(True)
        self.month_combo.clear()
        for number in range(1, 13):
            self.month_combo.addItem(self.locale.monthName(number, QLocale.FormatType.LongFormat))
        self.month_combo.setCurrentIndex(month - 1)
        self.month_combo.blockSignals(False)

    # Adjust text sizes for Tamil
    def tamil_fonts(self):
        tamil = self.current_language == 'Tamil'

        # history widgets with Tamil font sizes
        sizes = [(self.title, 18), (self.subtitle, 10), (self.graph_title, 11), (self.graph_note, 9), (self.trend_empty, 9), (self.calendar_title, 11), (self.calendar_note, 9), (self.legend_text, 9), (self.signals_title, 11), (self.transcript_title, 11), (self.recommendation_title, 11), (self.history_phrase, 17), (self.history_explanation, 10), (self.history_input, 9)]
        for widget, size in sizes:
            widget.setStyleSheet(f'font-size:{max(size, 12)}px;' if tamil else '')
        for widget in self.signal_names.values():
            widget.setStyleSheet('font-size:12px;' if tamil else '')
        for widget in self.signal_values.values():
            widget.setStyleSheet('font-size:12px;' if tamil else '')

    # user shown on this page
    def set_user(self, full_name, user_id=None):
        self.user_label.setText(full_name.split()[0] if full_name else '')
        self.user_id = user_id

    # Refresh the page contents
    def refresh_page(self):
        # Start the refreshed history view on today date
        today = QDate.currentDate()
        self.calendar.setCurrentPage(today.year(), today.month())
        self.calendar.setSelectedDate(today)
        self.year_combo.setCurrentIndex(self.year_combo.findData(today.year()))
        self.load_month_markers(today.year(), today.month())
        self.load_selected_date()
        self.load_trend_graph()

    # update the page when it appears
    def showEvent(self, event):
        super().showEvent(event)
        self.sidebar.set_expanded(HoverSidebar._shared_expanded)
        float_in(self.content)

    # Load recent scores when enough check-ins are saved
    def load_trend_graph(self):
        points = get_month_check_ins(self.user_id, 31)

        # Wait until at least seven check-ins are available
        if len(points) < 7:
            self.trend_graph.hide()
            self.trend_empty.show()
            return
        self.trend_empty.hide()
        self.trend_graph.set_points(points)
        self.trend_graph.show()

    # Show the month and year chosen in the menus
    def nav_changed(self):
        # Read the year selected in the menu
        year = self.year_combo.currentData()
        month = self.month_combo.currentIndex() + 1
        if month > 0:
            self.calendar.setCurrentPage(year, month)

    # Move to the previous or next allowed month
    def move_month(self, amount):
        # first day of this month by the requested amount
        date = QDate(self.calendar.yearShown(), self.calendar.monthShown(), 1).addMonths(amount)
        if date <= QDate.currentDate():
            self.calendar.setCurrentPage(date.year(), date.month())

    # calendar controls in sync
    def calendar_page_changed(self, year, month):
        self.load_month_markers(year, month)
        # Update the month and year menus without repeated signals
        self.month_combo.blockSignals(True)
        self.year_combo.blockSignals(True)
        self.month_combo.setCurrentIndex(month - 1)
        self.year_combo.setCurrentIndex(self.year_combo.findData(year))
        self.month_combo.blockSignals(False)
        self.year_combo.blockSignals(False)

        # find the first day of the next month
        next_month = QDate(year, month, 1).addMonths(1)
        self.nav_next.setEnabled(next_month <= QDate.currentDate())

    # saved check-in dates for this month
    def load_month_markers(self, year, month):
        # Convert saved date strings into calendar dates
        dates = [QDate.fromString(text, 'yyyy-MM-dd') for text in get_check_in_dates(self.user_id, year, month)]
        self.calendar.set_saved_dates(dates)

    # Load the check-in for the selected date
    def load_selected_date(self):
        # Read the selected calendar date
        date = self.calendar.selectedDate()
        formatted = self.locale.toString(date, 'dddd, d MMMM yyyy')

        # Load the saved check-in for that date
        check_in = get_check_in_for_date(self.user_id, date.toString('yyyy-MM-dd'))

        # Show the empty view if nothing was saved that day
        if check_in is None:
            self.translation_request += 1
            self.empty_date.setText(formatted)
            self.empty_message.setText(self.t('no_checkin'))
            self.summary_stack.setCurrentWidget(self.empty_state)
            return
        self.show_check_in(formatted, check_in)

    # Show selected saved check-in
    def show_check_in(self, formatted_date, check_in):
        self.selected_date.setText(formatted_date)

        # read hour and minute from the saved local time
        time = str(check_in['created_at_local'])[11:16]
        self.selected_time.setText(f"{self.t('latest_checkin')} {time}")

        # Show saved score and its matching colour range
        score = round(float(check_in['wellbeing_score']))
        self.history_progress.setValue(score)
        self.history_progress.setFormat(f'{score} / 100')
        self.history_progress.setProperty('zone', self.score_zone(score))
        self.refresh_style(self.history_progress)
        self.history_input.setText(f"{self.t('input_used')}: {self.t(check_in['input_type'])}")
        self.set_result_image(score)
        self.set_signals(check_in)

        # saved English text directly
        if self.current_language == 'English':
            self.apply_history_text(check_in['summary'], check_in['explanation'], check_in['transcript'], check_in['recommendation'])
        else:
            # cache key from the check-in and language
            cache_key = (check_in['id'], str(check_in['created_at_local']), self.current_language)
            cached = self.translation_cache.get(cache_key)
            # translated text that is already cached
            if cached:
                self.apply_history_text(cached['phrase'], cached['explanation'], cached['transcript'], cached['recommendation'])
            else:
                # original transcript when its language matches
                transcript = check_in['transcript_original'] if self.current_language == check_in['original_language'] else check_in['transcript']
                self.apply_history_text(check_in['summary'], check_in['explanation'], transcript, check_in['recommendation'])
                self.start_history_translation(check_in, cache_key)

        self.summary_stack.setCurrentWidget(self.summary_state)

    # saved check-in in the background
    def start_history_translation(self, check_in, cache_key):
        # translation request a new number
        self.translation_request += 1
        request_id = self.translation_request

        # worker for this check in translation
        worker = HistoryTranslationWorker(check_in, self.current_language, request_id, self)
        self.translation_workers.add(worker)

        # translated results and errors to their original request
        worker.completed.connect(lambda data, key=cache_key: self.history_translation_done(data, key))
        worker.failed.connect(lambda message, rid=request_id: self.history_translation_failed(message, rid))
        worker.finished.connect(lambda w=worker: self.translation_worker_finished(w))
        worker.start()

    # translation if the request is still current
    def history_translation_done(self, data, cache_key):
        # Cache translated text for later use
        self.translation_cache[cache_key] = data

        # Ignore result from an old request or another language
        if data['request_id'] != self.translation_request or data['language'] != self.current_language:
            return
        self.apply_history_text(data['phrase'], data['explanation'], data['transcript'], data['recommendation'])

    # failure for the current translation request
    def history_translation_failed(self, message, request_id):
        # Only report an error for the current request
        if request_id == self.translation_request:
            print('HISTORY TRANSLATION ERROR:', message)

    # completed translation worker
    def translation_worker_finished(self, worker):
        # Remove finished worker and release it
        self.translation_workers.discard(worker)
        worker.deleteLater()

    # saved summary and transcript text
    def apply_history_text(self, phrase, explanation, transcript, recommendation):
        self.history_phrase.setText(phrase or '')
        self.history_explanation.setText(explanation or '')
        self.history_transcript.setPlainText(transcript or '')
        self.set_recommendations(recommendation or '')

    # available supporting signals
    def set_signals(self, check_in):
        na = self.t('not_available')

        # match stored head positions to translated labels
        head_keys = {'Centred': 'head_centred', 'Slightly off-centre': 'head_slightly_off', 'Off-centre': 'head_off'}
        blink = check_in['blink_rate']
        head = check_in['head_position']
        speech = check_in['speech_rate']
        disfluency = check_in['disfluency_rate']
        lexical = check_in['lexical_variety']

        # format available signals and label missing values
        values = {'blink_rate': f'{blink:.1f}/min' if blink is not None else na, 'head_position': self.t(head_keys[head]) if head is not None else na, 'speech_rate': f'{speech:.0f}/min' if speech is not None else na, 'disfluency': f'{disfluency * 100:.1f}%' if disfluency is not None else na, 'lexical_variety': f'{lexical:.2f}' if lexical is not None else na}
        for key, value in values.items():
            self.signal_values[key].setText(value)

    # image for the saved score
    def set_result_image(self, score):
        # result image for the saved score range
        if score >= 67:
            image = 'wellbeing_high.png'
        elif score >= 34:
            image = 'wellbeing_mid.png'
        else:
            image = 'wellbeing_low.png'
        pixmap = QPixmap(str(IMAGES / image))
        self.history_image.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # widgets from a layout
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    # recommendations into separate cards
    def set_recommendations(self, text):
        # clear the old cards before adding new recommendations
        self._clear_layout(self.recommendation_layout)
        tones = ['', 'mint', 'sand']
        row = QHBoxLayout()
        row.setSpacing(14)
        index = 0

        # split the numbered recommendation text into cards
        for chunk in re.split(r'(?=\b[1-3][.)]\s*)', text):
            chunk = chunk.strip().replace('**', '')
            if not chunk:
                continue

            # remove the leading recommendation number
            body = re.sub(r'^[1-3][.)]\s*', '', chunk)

            # cycle through the card colour themes
            tone = tones[index % len(tones)]

            # create card using the chosen colour theme
            card = QFrame()
            card.setObjectName('recCard')
            card.setAttribute(Qt.WA_StyledBackground, True)
            card.setProperty('tone', tone)
            card.setMinimumHeight(170)

            inside = QVBoxLayout(card)
            inside.setContentsMargins(22, 22, 22, 22)
            inside.setSpacing(14)

            # create numbered badge for this recommendation
            number = QLabel(f'{index + 1}')
            number.setObjectName('recCardNumber')
            number.setProperty('tone', tone)
            number.setFixedSize(44, 44)
            number.setAlignment(Qt.AlignCenter)

            text_label = QLabel(body)
            text_label.setObjectName('recCardText')
            text_label.setWordWrap(True)
            text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

            inside.addStretch()
            inside.addWidget(number, 0, Qt.AlignHCenter)
            inside.addWidget(text_label)
            inside.addStretch()

            if self.current_language == 'Tamil':
                text_label.setStyleSheet('font-size:13px;')

            row.addWidget(card, 1)
            index += 1

        self.recommendation_layout.addLayout(row)

    # score range used for styling
    @staticmethod
    def score_zone(score):
        if score >= 67:
            return 'high'
        if score >= 34:
            return 'mid'
        return 'low'

    # refresh widget after a style property changes
    @staticmethod
    def refresh_style(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
