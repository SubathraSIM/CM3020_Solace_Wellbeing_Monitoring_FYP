# Import required libraries
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy
from UI.ui.translations import ENGLISH_TEXT, get_text

# resource descriptions and related interface wording
ENGLISH_TEXT.update({
    'resources_title': 'A little space for yourself',
    'resources_subtitle': 'Explore practical resources at your own pace.',
    'resource_watch': 'WATCH  ·  NHS',
    'resource_read': 'READ  ·  NHS',
    'resource_guide': 'GUIDE + AUDIO  ·  WHO',
    'resource_breathe': 'Take a breathing break',
    'resource_breathe_desc': 'A guided box-breathing video from the NHS Waiting Room resource collection.',
    'resource_stress': 'Find a calmer rhythm',
    'resource_stress_desc': 'A simple breathing exercise you can read and practise at your own pace.',
    'resource_ground': 'Make room for what matters',
    'resource_ground_desc': 'An illustrated stress-management guide, with accompanying audio exercises.',
    'resource_mindline': 'Explore mindline.sg',
    'resource_mindline_desc': "Singapore's national mental health platform, with a self-assessment tool and guided self-care exercises.",
    'resource_hpb': 'Everyday wellbeing tools',
    'resource_hpb_desc': "Self-care tools and resources from Singapore's Health Promotion Board to understand and manage your wellbeing.",
    'resource_helpline': 'Talk to someone (mindline 1771)',
    'resource_helpline_desc': "Singapore's national 24/7 mental health helpline and textline — reach support by call, text or online chat.",
    'resource_open': 'Open resource',
    'resource_close': 'Close',
    'resource_external': 'Opens an external resource in your browser.',
    'resource_failed': 'Your browser could not be opened. Copy the link below into your browser.',
    'resource_general': 'General wellbeing information, not a personalised treatment recommendation.',
    'home_trends_title': 'See the bigger picture',
    'home_trends_desc': 'Explore your saved check-ins and notice patterns over time.',
    'home_assistant_title': 'A place for your questions',
    'home_assistant_desc': 'Ask the Solace Assistant about your saved wellbeing history.',
    'home_overview': 'Your wellbeing, in focus',
    'home_care_line': 'A moment for you, between caring for others.',
    'home_resource_link': 'Explore resource',
    'nav_workspace': 'YOUR SPACE',
    'home_step_note': 'Reflect. Understand. Take your next step.'
})

# resources shown on the home page
RESOURCES = [
    ('resource_watch', 'resource_breathe', 'resource_breathe_desc', 'https://londonwaitingroom.nhs.uk/box-breathing-stress', 'mint'),
    ('resource_read', 'resource_stress', 'resource_stress_desc', 'https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/', 'sand'),
    ('resource_guide', 'resource_ground', 'resource_ground_desc', 'https://www.who.int/publications/i/item/9789240003927', 'blue')
]

# resource details and open links
class ResourceDialog(QDialog):
    def __init__(self, resource, language, parent=None):
        super().__init__(parent)
        t = lambda key: get_text(language, key)
        # resource label keys, link and colour theme
        kind, title, description, self.url, tone = resource

        # Frameless translucent card, matching the other Solace dialogs
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(t(title))
        self.setFixedWidth(600)

        # Card that holds the content
        card = QFrame()
        card.setObjectName('resourceDialogCard')
        card.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(10)

        # resource category using its colour theme
        tag = QLabel(t(kind))
        tag.setObjectName('resourceTag')
        tag.setProperty('tone', tone)
        tag.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(tag)

        # Add title, description and external resource notes
        for text, name in [(t(title),'resourceDialogTitle'),
                           (t(description),'resourceDialogBody'),
                           (t('resource_general'),'resourceDialogNote'),
                           (t('resource_external'),'resourceDialogNote')]:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setObjectName(name)
            layout.addWidget(label)

        # selectable error message if the browser cannot open
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.error.hide()
        layout.addWidget(self.error)
        row = QHBoxLayout()

        # button to close the resource dialog
        close = QPushButton(t('resource_close'))
        close.clicked.connect(self.reject)

        # button that opens the resource link
        open_button = QPushButton(t('resource_open'))
        open_button.setObjectName('primaryButton')
        open_button.clicked.connect(lambda: self.open_resource(t))
        for button in [close, open_button]:
            button.setMinimumHeight(44)
            button.setCursor(Qt.PointingHandCursor)
            row.addWidget(button)
        layout.addLayout(row)

        # Outer layout so the card sits inside the translucent window
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(card)

    # Open resource in the browser
    def open_resource(self, t):
        # Check whether browser could not open the link
        if not QDesktopServices.openUrl(QUrl(self.url)):
            self.error.setText(t('resource_failed') + '\n' + self.url)
            self.error.show()

# resources available for score based suggestions
WELLBEING_RESOURCES = [
    ('resource_breathe', 'resource_breathe_desc','https://londonwaitingroom.nhs.uk/box-breathing-stress'),
    ('resource_stress', 'resource_stress_desc','https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/'),
    ('resource_ground', 'resource_ground_desc','https://www.who.int/publications/i/item/9789240003927'),
    ('resource_mindline', 'resource_mindline_desc','https://www.mindline.sg'),
    ('resource_hpb', 'resource_hpb_desc','https://www.hpb.gov.sg/healthy-living/mental-well-being/'),
    ('resource_helpline', 'resource_helpline_desc','https://www.moh.gov.sg/seeking-healthcare/find-a-facility-or-service/mental-health-services/')
]

# wording for each reading resource
def _reading(key, title, description, url):
    title_key = f"{key}_title"
    desc_key = f"{key}_desc"
    ENGLISH_TEXT[title_key] = title
    ENGLISH_TEXT[desc_key] = description
    return title_key, desc_key, url


# provider and colour for a home card
def _home_reading(key, title, description, url, provider, tone):
    title_key, desc_key, url = _reading(key, title, description, url)
    kind_key = f"{key}_kind"
    ENGLISH_TEXT[kind_key] = f"READ  ·  {provider}"
    return kind_key, title_key, desc_key, url, tone

# Six assistant resources for each language
ASSISTANT_RESOURCES_BY_LANGUAGE = {
    "English": WELLBEING_RESOURCES,

    "Tamil": [
        _reading(
            "assistant_ta_sleep",
            "Make time for restful sleep",
            "A Tamil information sheet about sleep from Phoenix Australia.",
            "https://www.phoenixaustralia.org/disaster-hub/wp-content/uploads/2022/03/Sleep-handout-Tamil.pdf"
        ),
        _reading(
            "assistant_ta_breathing",
            "Understand breathing and emotions",
            "A Tamil guide explaining how breathing relates to emotions.",
            "https://www.phoenixaustralia.org/disaster-hub/wp-content/uploads/2022/03/The-effect-of-breathing-on-emotions-Tamil.pdf"
        ),
        _reading(
            "assistant_ta_grounding",
            "Reconnect with the present",
            "Tamil grounding exercises for managing strong emotions.",
            "https://www.phoenixaustralia.org/disaster-hub/wp-content/uploads/2022/03/Managing-strong-emotions-with-here-and-now-exercises-Tamil.pdf"
        ),
        _reading(
            "assistant_ta_wellbeing",
            "Understand your mental wellbeing",
            "An introduction to mental health and wellbeing in Tamil.",
            "https://embracementalhealth.org.au/images/translated-information/mental-health-and-wellbeing/tamil-mental-health-and-wellbeing-information.pdf"
        ),
        _reading(
            "assistant_ta_anxiety",
            "Learn about anxiety",
            "Tamil information about anxiety, coping and available support.",
            "https://www.rcpsych.ac.uk/mental-health/translations/tamil/anxiety-and-generalised-anxiety-disorder-GAD"
        ),
        _reading(
            "assistant_ta_physical_health",
            "Care for body and mind",
            "Tamil information about physical illness and mental health.",
            "https://www.rcpsych.ac.uk/mental-health/translations/tamil/physical-illness-and-mental-health"
        ),
    ],

    "Malay": [
        _reading(
            "assistant_ms_walking",
            "Make room for a walk",
            "A Malay article about the health benefits of walking.",
            "https://www.pantai.com.my/ms/health-pulse/walking-health-benefits"
        ),
        _reading(
            "assistant_ms_selfcare",
            "Take care of your mental wellbeing",
            "Practical mental health self-care tips in Malay.",
            "https://infosihat.moh.gov.my/images/media_sihat/lain_lain/pdf/Tips%20Penjagaan%20Kesihatan%20Mental%20OL.pdf"
        ),
        _reading(
            "assistant_ms_takefive",
            "Explore everyday wellbeing habits",
            "Malay information about connection, activity and the TAKE 5 wellbeing messages.",
            "https://infosihat.moh.gov.my/let-s-talk-minda-sihat.html"
        ),
        _reading(
            "assistant_ms_mental_health",
            "Understand mental health",
            "A Malay mental health leaflet from Malaysia's Ministry of Health.",
            "https://infosihat.moh.gov.my/images/media_sihat/risalah/pdf/02_Ris_Kes_%20Mental.pdf"
        ),
        _reading(
            "assistant_ms_positive_steps",
            "Take positive steps",
            "A Malay poster about positive steps for mental wellbeing.",
            "https://infosihat.moh.gov.my/images/media_sihat/poster/pdf/22_POSTER%20MENTAL_002.pdf"
        ),
        _reading(
            "assistant_ms_misconceptions",
            "Understand common misconceptions",
            "A Malay leaflet addressing misconceptions about mental illness.",
            "https://infosihat.moh.gov.my/images/media_sihat/risalah/pdf/01_Ris_Salah%20Fhm%20kes%20Mental.pdf"
        ),
    ],

    "Chinese": [
        _reading(
            "assistant_zh_walking",
            "Make room for a walk",
            "A Chinese article about the health benefits of walking.",
            "https://www.pantai.com.my/zh-cn/health-pulse/walking-health-benefits"
        ),
        _reading(
            "assistant_zh_stress",
            "Understand everyday stress",
            "WHO information in Chinese about stress and ways to cope.",
            "https://www.who.int/zh/news-room/questions-and-answers/item/stress"
        ),
        _reading(
            "assistant_zh_sleep",
            "Make time for restful sleep",
            "A Simplified Chinese information sheet about sleep.",
            "https://www.phoenixaustralia.org/disaster-hub/wp-content/uploads/2022/01/Sleep-handout-Simplified-Chinese.pdf"
        ),
        _reading(
            "assistant_zh_breathing",
            "Understand breathing and emotions",
            "A Simplified Chinese guide about breathing and emotions.",
            "https://www.phoenixaustralia.org/disaster-hub/wp-content/uploads/2022/01/The-effect-of-breathing-on-emotions-Simplified-Chinese.pdf"
        ),
        _reading(
            "assistant_zh_grounding",
            "Reconnect with the present",
            "Simplified Chinese grounding exercises for managing strong emotions.",
            "https://www.phoenixaustralia.org/disaster-hub/wp-content/uploads/2022/01/Managing-strong-emotions-with-here-and-now-exercises-Simplified-Chinese.pdf"
        ),
        _reading(
            "assistant_zh_wellbeing",
            "Understand your mental wellbeing",
            "An introduction to mental health and wellbeing in Simplified Chinese.",
            "https://embracementalhealth.org.au/images/translated-information/mental-health-and-wellbeing/chinese-simplified-mental-health-and-wellbeing-information.pdf"
        ),
    ],
}


# Separate resources for the home page
HOME_RESOURCES_BY_LANGUAGE = {
    "English": RESOURCES,

    "Tamil": [
        _home_reading(
            "home_ta_coping",
            "Coping after a traumatic event",
            "Tamil information about emotional reactions, recovery and seeking support.",
            "https://www.rcpsych.ac.uk/mental-health/translations/tamil/coping-after-a-traumatic-event",
            "RCPsych",
            "mint"
        ),
        _home_reading(
            "home_ta_bereavement",
            "Understanding grief and loss",
            "Tamil information about bereavement and support after losing someone.",
            "https://www.rcpsych.ac.uk/mental-health/translations/tamil/bereavement",
            "RCPsych",
            "sand"
        ),
        _home_reading(
            "home_ta_depression",
            "Understanding depression",
            "Tamil information about depression, self-care and professional support.",
            "https://www.rcpsych.ac.uk/mental-health/translations/tamil/depression-in-adults",
            "RCPsych",
            "blue"
        ),
    ],

    "Malay": [
        _home_reading(
            "home_ms_relaxation",
            "Learn about relaxation",
            "A Malay poster about neck and shoulder massage for stress.",
            "https://infosihat.moh.gov.my/images/media_sihat/poster/pdf/24_Pos_Tangani%20stress%20dgn%20Urutan.pdf",
            "KKM",
            "mint"
        ),
        _home_reading(
            "home_ms_healthy_mind",
            "Nurture a healthy mind",
            "A Malay poster about habits and support that contribute to a healthy mind.",
            "https://infosihat.moh.gov.my/images/media_sihat/poster/pdf/27_Pos_Pokok%20Minda%20Sihat.pdf",
            "KKM",
            "sand"
        ),
        _home_reading(
            "home_ms_stress",
            "Recognise and manage stress",
            "A Malay poster about signs of stress, common causes and ways to cope.",
            "https://infosihat.moh.gov.my/images/media_sihat/poster/pdf/26_Pos_Stress_BM.pdf",
            "KKM",
            "blue"
        ),
    ],

    "Chinese": [
        _home_reading(
            "home_zh_mental_health",
            "Explore mental wellbeing",
            "WHO information in Chinese about mental health and support.",
            "https://www.who.int/zh/news-room/fact-sheets/detail/mental-health-strengthening-our-response",
            "WHO",
            "mint"
        ),
        _home_reading(
            "home_zh_activity",
            "Bring movement into your day",
            "WHO information in Chinese about physical activity and its benefits.",
            "https://www.who.int/zh/news-room/fact-sheets/detail/physical-activity",
            "WHO",
            "sand"
        ),
        _home_reading(
            "home_zh_depression",
            "Understanding depression",
            "WHO information in Chinese about depression and available care.",
            "https://www.who.int/zh/news-room/fact-sheets/detail/depression",
            "WHO",
            "blue"
        ),
    ],
}

# home resources for the selected language
def home_resources_for_language(language):
    return HOME_RESOURCES_BY_LANGUAGE.get(language, HOME_RESOURCES_BY_LANGUAGE["English"])

# resource priorities for each score range
RESOURCES_BY_BAND = {
    'low':  [5, 3, 1],
    'mid':  [3, 1, 2],
    'high': [2, 4, 0]
}

# three resources for the score range
def resources_for_score(score, language="English"):
    # middle range when no score is available
    if score is None:
        band = 'mid'
    elif score >= 67:
        band = 'high'
    elif score >= 34:
        band = 'mid'
    else:
        band = 'low'

    # resources in the selected language
    available = ASSISTANT_RESOURCES_BY_LANGUAGE.get(language, WELLBEING_RESOURCES)
    # resource order for the selected range
    order = RESOURCES_BY_BAND.get(band, [0, 1, 2])
    picked = []
    # three valid resources in the chosen order
    for i in order[:3]:
        if 0 <= i < len(available):
            title_key, desc_key, url = available[i]
            picked.append({'title_key': title_key,'desc_key': desc_key,'url': url})
    return {'band': band, 'resources': picked}