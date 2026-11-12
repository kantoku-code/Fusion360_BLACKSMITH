"""ソリッド変換用の翻訳ファイルを指定する。"""

from pathlib import Path

from ...localization import LanguageMessage as _LanguageMessage


class LanguageMessage(_LanguageMessage):
    def __init__(self) -> None:
        super().__init__(Path(__file__).with_name("message.json"))
