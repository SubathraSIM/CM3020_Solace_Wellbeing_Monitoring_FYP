# Import required libraies
import gc, json
from pathlib import Path
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# data folder
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
DATA.mkdir(parents=True, exist_ok=True)

# translated interface text in local JSON file
TRANSLATION_FILE = DATA / 'ui_translations.json'

# model used for translation
TRANSLATION_MODEL = 'facebook/nllb-200-distilled-600M'

# supported languages to model codes
LANGUAGE_CODES = {'Malay': 'zsm_Latn', 'Chinese': 'zho_Hans', 'Tamil': 'tam_Taml'}

# English wording as the fallback for missing translations
ENGLISH_TEXT = {'home': 'Home', 'check_in': 'Check-in', 'trends': 'Trends', 'settings': 'Settings', 'logout': 'Log out', 'welcome': 'Welcome', 'start_check_in': 'Start check-in', 'settings_title': 'Settings', 'settings_subtitle': 'Manage your application preferences.', 'language': 'Language', 'language_description': 'Choose the language used for the interface, speech recognition and wellbeing recommendations.', 'application_language': 'Application language', 'language_note': 'The selected language will be used for future check-ins.', 'privacy_settings_title': 'Privacy and consent', 'privacy_settings_description': 'Review the privacy, AI and consent information for Solace.', 'view_privacy': 'View privacy and consent', 'delete_account_title': 'Delete account', 'delete_account_description': 'Permanently delete your Solace account and all saved wellbeing history.', 'delete_account': 'Delete my account', 'delete_dialog_title': 'Permanently delete your account?', 'delete_dialog_warning': 'This action cannot be undone.', 'delete_dialog_details': 'Your Solace account, consent information and all saved check-in history will be permanently removed from this device. Solace will not keep a copy of this information after deletion. Temporary recordings created by Solace will also be cleared. Files that you originally uploaded from your computer are not deleted from their original location.', 'delete_dialog_confirm': 'I understand that my account and saved information will be permanently deleted.', 'delete_account_confirm': 'Permanently delete account'}
TRANSLATIONS = {}

# saved interface translations
def load_translations():
    if TRANSLATION_FILE.exists():
        # saved translations as UTF-8 text
        with open(TRANSLATION_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# interface translations to disk
def save_translations(data):
    # translation file for writing
    with open(TRANSLATION_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Translate the text in small batches
def translate_batch(model, tokenizer, texts, language, device):
    # English as source and choose target language token
    tokenizer.src_lang = 'eng_Latn'
    target_id = tokenizer.convert_tokens_to_ids(LANGUAGE_CODES[language])
    translated = []

    # Translate fur entries at a time
    for start in range(0, len(texts), 4):
        batch = texts[start:start + 4]
        # Tokenize the batch and move it to the selected device
        inputs = tokenizer(batch, return_tensors='pt', padding=True, truncation=True, max_length=512)
        inputs = {key: value.to(device) for key, value in inputs.items()}
        # Generate translations without tracking gradients
        with torch.inference_mode():
            output = model.generate(**inputs, forced_bos_token_id=target_id, max_length=512)

        # results and remove special tokens
        translated.extend(tokenizer.batch_decode(output, skip_special_tokens=True))
    return translated

# Create translations for missing or changed wording
def prepare_translations():
    global TRANSLATIONS

    # translations already saved
    saved = load_translations()
    old_english = saved.get('English', {})

    # find English entries that have changed
    changed = {key for key, value in ENGLISH_TEXT.items() if old_english.get(key) != value}
    saved['English'] = dict(ENGLISH_TEXT)

    # Find missing or outdated translations for each supported language
    missing = {language: [key for key in ENGLISH_TEXT if key in changed or key not in saved.get(language, {})] for language in LANGUAGE_CODES}
    missing = {language: keys for language, keys in missing.items() if keys}
    if missing:
        # Use the GPU if one is available
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # tokenizer and model only when updates are needed
        tokenizer = AutoTokenizer.from_pretrained(TRANSLATION_MODEL, src_lang='eng_Latn')
        model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_MODEL).to(device)
        model.eval()

        # translate each language and save results under the original keys
        for language, keys in missing.items():
            results = translate_batch(model, tokenizer, [ENGLISH_TEXT[key] for key in keys], language, device)
            saved.setdefault(language, {})
            for key, text in zip(keys, results):
                saved[language][key] = text.strip()
        # Release translation model
        gc.collect()

        # GPU memory can be released
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # updated cache and make it available to the interface
    save_translations(saved)
    TRANSLATIONS = saved

# Get translated text with an English fallback
def get_text(language, key):
    return TRANSLATIONS.get(language, {}).get(key) or ENGLISH_TEXT.get(key, key)

# Translate a list of text entries
def translate_texts(texts, language):
    # Convert the entries to text and replace missing values
    texts = [str(text or '') for text in texts]

    # keep English text as it is
    if language == 'English':
        return texts
    
    # GPU when one is available
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tokenizer = AutoTokenizer.from_pretrained(TRANSLATION_MODEL, src_lang='eng_Latn')
    model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_MODEL).to(device)
    model.eval()
    try:
        return [text.strip() for text in translate_batch(model, tokenizer, texts, language, device)]

    # cached GPU memory after translation
    finally:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

# Translate one text entry
def translate_text(text, language):
    return translate_texts([text], language)[0]