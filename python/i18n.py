"""Interface text for the supported languages (English and Simplified Chinese)."""
from locales import LOCALE_MODULES

INSTRUCTIONS = {language: module.INSTRUCTIONS for language, module in LOCALE_MODULES.items()}
LANGUAGE_UI = {
    language: {**module.UI, "tool_text": dict(module.TOOL_TEXT)}
    for language, module in LOCALE_MODULES.items()
}


def ui_text(lang):
    return dict(LANGUAGE_UI.get(lang, LANGUAGE_UI["English"]))
