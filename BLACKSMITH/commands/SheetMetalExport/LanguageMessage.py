import adsk.core as core
import adsk.fusion as fusion
import pathlib
import json

# ** debug **
DEBUG_LANG_MODE = False
LANGS = [
    "de-DE",
    "en-US",
    "es-ES",
    "fr-FR",
    "it-IT",
    "ja-JP",
    "ko-KR",
    "zh-CN",
    "pl-PL",# ポーランド
    "pt-BR",# ポルトガル-ブラジル
    "tr-TR",# トルコ
]
DEBUG_LANG = LANGS[7]

THIS_DIR = pathlib.Path(__file__).resolve().parent
JSON_PATH = THIS_DIR / 'message.json'


class LanguageMessage():
    def __init__(self) -> None:
        self.langMsg: dict = self._get_languge_dict()


    def s(self, txt: str) -> str:
        '''
        言語変換
        '''
        if txt in self.langMsg:
            return self.langMsg[txt]

        return txt


    def _get_languge_dict(self) -> dict:
        '''
        言語のメッセージ辞書
        '''
        all_dict: dict = self._load_dict()

        app: core.Application = core.Application.get()
        lang: str = app.executeTextCommand(u'Options.GetUserLanguage')

        if DEBUG_LANG_MODE:
            lang = DEBUG_LANG

        return all_dict[lang]


    def _load_dict(self) -> dict:
        '''
        json読み込み
        '''
        with open(str(JSON_PATH), encoding="utf-8") as f:
            jsn = json.load(f)

        return jsn