# Import translation functions and settings
import UI.ui.translations as translations

# Test case 1: Check that the selected translation model is NLLB-200
def test_translation_model():
    assert translations.TRANSLATION_MODEL == ("facebook/nllb-200-distilled-600M")


# Test case 2: Check that Malay uses the correct NLLB language code
def test_malay_language_code():
    assert translations.LANGUAGE_CODES["Malay"] == "zsm_Latn"


# Test case 3: Check that Chinese uses the correct NLLB language code
def test_chinese_language_code():
    assert translations.LANGUAGE_CODES["Chinese"] == "zho_Hans"


# Test case 4: Check that Tamil uses the correct NLLB language code
def test_tamil_language_code():
    assert translations.LANGUAGE_CODES["Tamil"] == "tam_Taml"


# Test case 5: Check that all supported translation languages are available
def test_supported_languages():
    assert set(translations.LANGUAGE_CODES.keys()) == {"Malay", "Chinese", "Tamil",}


# Test case 6: Check that important English interface text is registered
def test_english_interface_text():
    # English label for Home
    assert translations.ENGLISH_TEXT["home"] == "Home"
    # English label for Check-in
    assert translations.ENGLISH_TEXT["check_in"] == "Check-in"
    # English label for Trends
    assert translations.ENGLISH_TEXT["trends"] == "Trends"
    # English label for Settings
    assert translations.ENGLISH_TEXT["settings"] == "Settings"
    # English label for Log out
    assert translations.ENGLISH_TEXT["logout"] == "Log out"


# Test case 7: Check that English text does not go through translation
def test_english_translation_bypass():
    # sample English sentence
    text = ("Take a short break after your shift.")
    # English version of the sentence
    result = translations.translate_text(text, "English")
    assert result == text


# Test case 8: Check that English interface text can be retrieved correctly
def test_get_english_text():
    # current translations to restore later
    original_translations = (translations.TRANSLATIONS)
    # copy of the English interface text
    translations.TRANSLATIONS = {"English": dict(translations.ENGLISH_TEXT)}
    # English Home label
    result = translations.get_text("English", "home")
    # Restore original translations
    translations.TRANSLATIONS = (original_translations)
    assert result == "Home"


# Test case 9: Check that translated interface text can be retrieved correctly
def test_get_translated_text():
    # current translations to restore later
    original_translations = (translations.TRANSLATIONS)
    # sample Malay translation for Home
    translations.TRANSLATIONS = {"Malay": {"home": "Laman utama"}}
    # Malay Home label
    result = translations.get_text("Malay","home")
    # original translations
    translations.TRANSLATIONS = (original_translations)
    assert result == "Laman utama"

# Test case 10: Check that a missing translation falls back to English text
def test_get_text_fallback_to_english():
    # current translations to restore later
    original_translations = (translations.TRANSLATIONS)
    # translations being empty or a language missing its keys
    translations.TRANSLATIONS = {}
    # Malay Home label
    result = translations.get_text("Malay", "home")
    # original translations
    translations.TRANSLATIONS = (original_translations)
    assert result == "Home"
    assert translations.get_text("Malay", "not_a_real_key") == "not_a_real_key"