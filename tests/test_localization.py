"""稼働中のコマンドと manifest の翻訳範囲を検証する。"""

import ast
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "BLACKSMITH"
COMMANDS = ("SheetMetalExport", "Convert2SolidBody")
LCID_TO_LOCALE = {
    "2052": "zh-CN", "1028": "zh-TW", "1029": "cs-CZ",
    "1033": "en-US", "1036": "fr-FR", "1031": "de-DE",
    "1038": "hu-HU", "1040": "it-IT", "1041": "ja-JP",
    "1042": "ko-KR", "1045": "pl-PL", "1046": "pt-BR",
    "1049": "ru-RU", "1034": "es-ES", "1055": "tr-TR",
}


class LocalizationTests(unittest.TestCase):
    def test_manifest_and_active_command_translations_match(self) -> None:
        manifest = json.loads((ROOT / "BLACKSMITH.manifest").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["description"]), {"", *LCID_TO_LOCALE})
        self.assertEqual(manifest["description"][""], manifest["description"]["1033"])
        self.assertTrue(all(manifest["description"].values()))

        for command in COMMANDS:
            with self.subTest(command=command):
                folder = ROOT / "commands" / command
                translations = json.loads((folder / "message.json").read_text(encoding="utf-8"))
                self.assertEqual(set(translations), set(LCID_TO_LOCALE.values()))

                tree = ast.parse((folder / "entry.py").read_text(encoding="utf-8"))
                used_keys = {
                    node.args[0].value
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "_lm"
                    and node.func.attr == "s"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                }
                self.assertTrue(used_keys)
                for language, messages in translations.items():
                    with self.subTest(language=language):
                        self.assertFalse(used_keys - messages.keys())
                        self.assertTrue(all(messages[key] for key in used_keys))

    def test_fusion_language_selection_and_english_fallback(self) -> None:
        core = types.ModuleType("adsk.core")
        adsk = types.ModuleType("adsk")
        adsk.core = core
        app = Mock()
        core.Application = types.SimpleNamespace(get=lambda: app)

        with patch.dict(sys.modules, {"adsk": adsk, "adsk.core": core}):
            spec = importlib.util.spec_from_file_location("localization_under_test", ROOT / "localization.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            resource = ROOT / "commands" / "Convert2SolidBody" / "message.json"
            app.executeTextCommand.return_value = "ja-JP"
            self.assertEqual(module.LanguageMessage(resource).s("Convert to Solid"), "ソリッドへ変換")

            app.executeTextCommand.return_value = "xx-XX"
            self.assertEqual(module.LanguageMessage(resource).s("Convert to Solid"), "Convert to Solid")

            app.executeTextCommand.side_effect = RuntimeError("language unavailable")
            self.assertEqual(module.LanguageMessage(resource).s("Convert to Solid"), "Convert to Solid")


if __name__ == "__main__":
    unittest.main()
