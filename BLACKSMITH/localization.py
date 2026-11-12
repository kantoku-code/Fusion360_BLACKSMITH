"""Fusion の表示言語に応じてコマンドの文言を選ぶ。"""

import json
from pathlib import Path

import adsk.core as core


DEFAULT_LANGUAGE = "en-US"


class LanguageMessage:
    """コマンド固有の翻訳ファイルを共通の方法で読み込む。"""

    def __init__(self, path: Path) -> None:
        with path.open(encoding="utf-8") as source:
            translations: dict[str, dict[str, str]] = json.load(source)

        try:
            language = core.Application.get().executeTextCommand(
                "Options.GetUserLanguage"
            )
        except Exception:
            language = DEFAULT_LANGUAGE

        self._english = translations[DEFAULT_LANGUAGE]
        self._selected = translations.get(language, self._english)

    def s(self, text: str) -> str:
        """対象言語の訳を返し、欠落していれば英語を使う。"""
        return self._selected.get(text, self._english.get(text, text))
