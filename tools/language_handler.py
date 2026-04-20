import os
import json
from langdetect import detect
import langid
from deep_translator import GoogleTranslator

CONFIG_PATH = os.path.join("data", "user_config.json")

SUPPORTED_LANGUAGES = [
    "auto",
    "zh",
    "en",
    "pl",
    "cs",
    "sk",
    "de",
    "fr",
    "es",
    "it",
    "pt",
    "ru",
    "uk",
    "nl",
    "sv",
    "fi",
    "no",
    "da",
    "tr",
    "ja",
    "ko",
    "ar",
    "he",
]

LANGUAGE_LABELS = {
    "auto": "自动检测",
    "zh": "中文",
    "en": "英语 (English)",
    "pl": "波兰语 (Polski)",
    "cs": "捷克语 (Čeština)",
    "sk": "斯洛伐克语 (Slovenčina)",
    "de": "德语 (Deutsch)",
    "fr": "法语 (Français)",
    "es": "西班牙语 (Español)",
    "it": "意大利语 (Italiano)",
    "pt": "葡萄牙语 (Português)",
    "ru": "俄语 (Русский)",
    "uk": "乌克兰语 (Українська)",
    "nl": "荷兰语 (Nederlands)",
    "sv": "瑞典语 (Svenska)",
    "fi": "芬兰语 (Suomi)",
    "no": "挪威语 (Norsk)",
    "da": "丹麦语 (Dansk)",
    "tr": "土耳其语 (Türkçe)",
    "ja": "日语 (日本語)",
    "ko": "韩语 (한국어)",
    "ar": "阿拉伯语 (العربية)",
    "he": "希伯来语 (עברית)",
}


class LanguageHandler:
    """High level helpers for language detection and translation."""

    @staticmethod
    def detect_language(text: str) -> str:
        """Return a language code detected from ``text``.

        ``langid`` is tried first with a limited set of supported languages to
        improve accuracy. If that fails, ``langdetect`` is used as a fallback
        and defaults to English when detection is impossible.
        """
        try:
            langid.set_languages([l for l in SUPPORTED_LANGUAGES if l != "auto"])
            lang, _ = langid.classify(text)
        except Exception:
            try:
                lang = detect(text)
            except Exception:
                lang = "en"
        return lang

    @staticmethod
    def set_language(lang_code: str) -> None:
        """Persist the user's preferred language code."""
        os.makedirs("data", exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"language": lang_code}, f)

    @staticmethod
    def get_language() -> str:
        """Return the stored preferred language or ``"auto"`` if unset."""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, encoding="utf-8") as f:
                config = json.load(f)
                return config.get("language", "auto")
        return "auto"

    @staticmethod
    def choose_or_detect(text: str = None) -> str:
        """Return the configured language or detect it from ``text``."""
        user_lang = LanguageHandler.get_language()
        if user_lang == "auto" and text:
            return LanguageHandler.detect_language(text)
        return user_lang

    @staticmethod
    def translate(text: str, target: str) -> str:
        """Translate text to the target language using deep-translator."""

        if not text or target == "auto":
            return text
        try:
            return GoogleTranslator(source="auto", target=target).translate(text)
        except Exception:
            return text

    @staticmethod
    def ensure_language(text: str, language: str) -> str:
        """Ensure the text is in the specified language, translating if needed."""
        if language == "auto" or not text:
            return text
        detected = LanguageHandler.detect_language(text)
        if detected != language:
            return LanguageHandler.translate(text, language)
        return text

    @staticmethod
    def supported_languages() -> list[str]:
        """Return the list of supported language codes."""
        return SUPPORTED_LANGUAGES

    @staticmethod
    def dropdown_choices() -> list[str]:
        """Return display strings for the language dropdown."""
        return [LANGUAGE_LABELS[code] for code in SUPPORTED_LANGUAGES]

    @staticmethod
    def code_from_display(display: str) -> str:
        """Map a dropdown display label back to its language code."""
        for code, label in LANGUAGE_LABELS.items():
            if label == display:
                return code
        return "auto"
