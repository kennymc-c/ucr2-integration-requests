"""Defines internationalization logic and strings for the integration"""

import logging
from enum import StrEnum

_LOG = logging.getLogger(__name__)



class Languages(StrEnum):
    """Defines all supported language codes for the integration"""

    ENGLISH = "en_US"
    GERMAN = "de_DE"

    @classmethod
    def get_values(cls):
        """Get a list of all language codes defined in this class"""
        return [lang.value for lang in cls]



class Messages(StrEnum):
    """Defines all messages used in the integration"""

    NO_MATCH = "no_match_found"



class Strings:
    """Defines all localized strings for the integration"""

    class en_US:
        """Defines localized strings for English (United States)"""
        messages = {
            Messages.NO_MATCH: "No match found"
        }

    class de_DE:
        """Defines localized strings for German (Germany)"""
        messages = {
            Messages.NO_MATCH: "Keine Übereinstimmung gefunden"
            }



class Handler:
    """Handles internationalization for the integration"""

    _fallback_language = Languages.ENGLISH
    _language = _fallback_language

    @classmethod
    def set_language(cls, language: Languages):
        """Sets the language for the integration"""
        cls._language = language

    @classmethod
    def _get_lookups(cls, language: Languages) -> list[dict]:
        strings = getattr(Strings, language, Strings.en_US)
        return [strings.messages]

    @classmethod
    def localize(cls, key: str | list[str], force_language: Languages = None, reverse: bool = False) -> str:
        """Localizes a given key. Uses the currently set language unless force_language is explicitly provided.
        Falls back to the English value if no translation is found for the given language,
        and to the normalized key itself if no English value is found either.

        :param key: The key(s) to look up (enum member, plain string or list of keys).
        :param force_language: (Optional) Language to use instead of the currently set language.
        :param reverse: (Optional) If True, attempt to find a reverse mapping to get the enum from the localized string.
        :return: The localized string, English fallback, or normalized key as last resort.
        """
        if isinstance(key, list):
            return [cls.localize(k, force_language, reverse) for k in key]

        normalized_key = key.value.replace("\"", "") if hasattr(key, "value") else key.replace("\"", "")
        quoted_key = f'"{normalized_key}"'
        language = force_language if force_language is not None else cls._language

        lookups = cls._get_lookups(language)
        fallback_lookups = cls._get_lookups(cls._fallback_language)

        if reverse:
            for lookup in lookups:
                for k, v in lookup.items():
                    if v == normalized_key:
                        return k

        for lookup in lookups:
            if normalized_key in lookup:
                return lookup[normalized_key]
            if quoted_key in lookup:
                return lookup[quoted_key]

        # Fallback 1: Fallback_language
        if language != cls._fallback_language:
            for lookup in fallback_lookups:
                if normalized_key in lookup:
                    _LOG.debug(f'No translation for "{normalized_key}" in "{language}". Falling back to "{cls._fallback_language}"')
                    return lookup[normalized_key]
                if quoted_key in lookup:
                    _LOG.debug(f'No translation for "{quoted_key}" in "{language}". Falling back to "{cls._fallback_language}"')
                    return lookup[quoted_key]

        # Fallback 2: Key itself
        _LOG.warning(f'No localization string found for key "{normalized_key}" in language "{language}" or "{cls._fallback_language}". Returning key as fallback')
        return normalized_key
