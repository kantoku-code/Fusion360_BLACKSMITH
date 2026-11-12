"""Fusion API の代替を使い、アドインの保守処理を検証する。"""

import importlib.util
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


ROOT = pathlib.Path(__file__).resolve().parents[1] / "BLACKSMITH"


def load_module(name: str, path: pathlib.Path) -> types.ModuleType:
    """指定されたファイルからテスト対象モジュールを読み込む。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Event:
    """Fusion イベントの登録と解除を模擬する。"""
    def __init__(self) -> None:
        """登録済みハンドラの一覧を初期化する。"""
        self.handlers = []

    def add(self, handler: object) -> None:
        """ハンドラを登録する。"""
        self.handlers.append(handler)

    def remove(self, handler: object) -> None:
        """ハンドラを解除する。"""
        self.handlers.remove(handler)


class MaintenanceTests(unittest.TestCase):
    """アドインの保守処理を Fusion API の代替で検証する。"""
    @classmethod
    def setUpClass(cls) -> None:
        """テストで使う Fusion API の代替を用意する。"""
        core = types.ModuleType("adsk.core")
        fusion = types.ModuleType("adsk.fusion")
        adsk = types.ModuleType("adsk")
        adsk.core = core
        adsk.fusion = fusion
        sys.modules.update({"adsk": adsk, "adsk.core": core, "adsk.fusion": fusion})
        for name in ("Application", "BRepBody", "Component", "FlatPattern", "FlatPatternProduct",
                     "BRepFace", "Design", "ExportManager", "DXFFlatPatternExportOptions",
                     "TemporaryBRepManager", "SelectionCommandInput", "Command",
                     "CommandEventArgs", "ApplicationCommandEventArgs", "UserInterface",
                     "CommandDefinition", "Selections", "TableCommandInput", "BoolValueCommandInput",
                     "TextBoxCommandInput", "ButtonRowCommandInput", "ListItems", "CommandCreatedEventArgs",
                     "ValidateInputsEventArgs", "InputChangedEventArgs", "SelectionEventArgs", "Occurrence"):
            setattr(core if name not in ("BRepBody", "Component", "FlatPattern", "FlatPatternProduct",
                                         "BRepFace", "Design", "ExportManager", "DXFFlatPatternExportOptions",
                                         "TemporaryBRepManager", "Occurrence") else fusion, name, type(name, (), {}))
        core.Plane = type("Plane", (), {"classType": staticmethod(lambda: "plane")})
        core.ApplicationCommandEventHandler = type("ApplicationCommandEventHandler", (), {})
        core.CommandTerminationReason = types.SimpleNamespace(CompletedTerminationReason="completed")
        cls.app = Mock()
        cls.app.userInterface.commandTerminated = Event()
        core.Application.get = staticmethod(lambda: cls.app)

        for name, path in (("BLACKSMITH", ROOT), ("BLACKSMITH.commands", ROOT / "commands"),
                           ("BLACKSMITH.commands.SheetMetalExport", ROOT / "commands" / "SheetMetalExport"),
                           ("BLACKSMITH.commands.Convert2SolidBody", ROOT / "commands" / "Convert2SolidBody")):
            package = types.ModuleType(name)
            package.__path__ = [str(path)]
            sys.modules[name] = package
        lib = types.ModuleType("BLACKSMITH.lib")
        lib.fusion360utils = types.SimpleNamespace(app=cls.app, handle_error=Mock(), add_handler=Mock())
        sys.modules["BLACKSMITH.lib"] = lib
        for command in ("SheetMetalExport", "Convert2SolidBody"):
            language = types.ModuleType(f"BLACKSMITH.commands.{command}.LanguageMessage")
            language.LanguageMessage = lambda: types.SimpleNamespace(s=lambda text: text)
            sys.modules[language.__name__] = language
        cls.config = load_module("BLACKSMITH.config", ROOT / "config.py")
        cls.export = load_module("BLACKSMITH.commands.SheetMetalExport.SheetMetalExportFactry",
                                 ROOT / "commands" / "SheetMetalExport" / "SheetMetalExportFactry.py")
        cls.convert = load_module("BLACKSMITH.commands.Convert2SolidBody.Convert2SolidBodyFactry",
                                  ROOT / "commands" / "Convert2SolidBody" / "Convert2SolidBodyFactry.py")
        cls.export_entry = load_module("BLACKSMITH.commands.SheetMetalExport.entry",
                                       ROOT / "commands" / "SheetMetalExport" / "entry.py")
        cls.convert_entry = load_module("BLACKSMITH.commands.Convert2SolidBody.entry",
                                        ROOT / "commands" / "Convert2SolidBody" / "entry.py")

    def setUp(self) -> None:
        """各テストの前に共有状態を初期化する。"""
        self.app.reset_mock()
        self.app.userInterface.commandTerminated.handlers.clear()
        self.config.convert2SolidBody_dict.update(handler=None, body=None)

    def make_exporter(self) -> object:
        """テスト用の板金エクスポータを作る。"""
        factory = self.export.SheetMetalExportFactry.__new__(self.export.SheetMetalExportFactry)
        factory.app = self.app
        body = types.SimpleNamespace(name="body", parentComponent=types.SimpleNamespace(name="part"))
        factory.sheetInfos = [{"native": body}]
        factory._create_flatPattern = Mock(return_value=object())
        return factory

    def test_path_sanitization_and_collision(self) -> None:
        """使用できない文字の置換と同名ファイルの連番を確認する。"""
        factory = self.make_exporter()
        body = factory.sheetInfos[0]["native"]
        body.name = 'a*b?'
        body.parentComponent.name = 'part|one'
        body.parentComponent.activeSheetMetalRule = types.SimpleNamespace(
            name='rule', thickness=types.SimpleNamespace(expression='1.5 mm'))
        with tempfile.TemporaryDirectory() as directory:
            first = pathlib.Path(factory._get_path(factory.sheetInfos[0], directory, '.dxf', True))
            self.assertEqual(first.name, 'a_b_-part_one-rule-1.5 mm.dxf')
            first.touch()
            second = pathlib.Path(factory._get_path(factory.sheetInfos[0], directory, '.dxf', True))
            self.assertEqual(second.stem, first.stem + '_1')

    def test_export_false_and_exception_are_reported_per_format(self) -> None:
        """各形式の失敗が個別に報告されることを確認する。"""
        factory = self.make_exporter()
        with tempfile.TemporaryDirectory() as directory:
            factory._get_path = lambda info, folder, suffix, use_name: str(pathlib.Path(directory) / ('out' + suffix))
            def failed_dxf(path: str, flat: object) -> None:
                """DXF の部分出力後に失敗を模擬する。"""
                pathlib.Path(path).write_text('partial')
                raise RuntimeError('DXF export returned false')
            factory._export_dxf = failed_dxf
            factory._export_sat = Mock(side_effect=RuntimeError('SAT failed'))
            failures = factory.export_sheetMetal_flatPattern([0], ['DXF', 'SAT'], directory, True)
            self.assertEqual(len(failures), 2)
            self.assertIn('DXF export returned false', failures[0])
            self.assertIn('SAT failed', failures[1])
            self.assertFalse((pathlib.Path(directory) / 'out.dxf').exists())
            self.app.executeTextCommand.assert_any_call('Transaction.Abort')

    def test_flat_pattern_failure_reports_each_requested_format(self) -> None:
        """展開失敗が指定形式ごとに報告されることを確認する。"""
        factory = self.make_exporter()
        factory._create_flatPattern.side_effect = RuntimeError('cannot flatten')
        failures = factory.export_sheetMetal_flatPattern([0], ['DXF', 'SAT'], 'unused', True)
        self.assertEqual(len(failures), 2)
        self.assertTrue(all('cannot flatten' in item for item in failures))

    def test_export_api_false_is_a_failure(self) -> None:
        """Fusion API の失敗結果を例外として扱うことを確認する。"""
        factory = self.make_exporter()
        self.app.activeProduct.exportManager.execute.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'DXF export returned false'):
            factory._export_dxf('unused.dxf', object())

        manager = Mock()
        manager.exportToFile.return_value = False
        self.export.fusion.TemporaryBRepManager.get = staticmethod(lambda: manager)
        flat = types.SimpleNamespace(bodies=[object()])
        with self.assertRaisesRegex(RuntimeError, 'SAT export returned false'):
            factory._export_sat('unused.sat', flat)

    def test_conversion_followup_only_after_successful_termination(self) -> None:
        """正常終了時だけ後続コマンドが動くことを確認する。"""
        face = types.SimpleNamespace(geometry=types.SimpleNamespace(objectType='plane'), area=1)
        body = types.SimpleNamespace(isValid=True, faces=[face])
        command = Mock()
        self.app.userInterface.commandDefinitions.itemById.return_value = command
        event = self.app.userInterface.commandTerminated

        self.convert.set_pending_conversion(body)
        event.handlers[0].notify(types.SimpleNamespace(commandId='other', terminationReason='completed'))
        self.assertEqual(len(event.handlers), 1)
        event.handlers[0].notify(types.SimpleNamespace(
            commandId='KANTOKU_BLACKSMITH_conv2solid', terminationReason='cancelled'))
        self.assertEqual(len(event.handlers), 0)
        command.execute.assert_not_called()

        self.convert.set_pending_conversion(body)
        event.handlers[0].notify(types.SimpleNamespace(
            commandId='KANTOKU_BLACKSMITH_conv2solid', terminationReason='completed'))
        self.assertEqual(len(event.handlers), 0)
        command.execute.assert_called_once()

    def test_conversion_preview_requires_selection_and_success(self) -> None:
        """プレビューには選択と変換成功が必要なことを確認する。"""
        entry = self.convert_entry
        entry._bodyIpt = types.SimpleNamespace(selectionCount=0)
        entry._compIpt = types.SimpleNamespace(value=True)
        args = types.SimpleNamespace(isValidResult=True)
        with patch.object(entry, 'convert_solidBody') as convert:
            entry.command_executePreview(args)
            convert.assert_not_called()
        self.assertFalse(args.isValidResult)

        body = types.SimpleNamespace(isSheetMetal=True)
        entry._bodyIpt = types.SimpleNamespace(
            selectionCount=1, selection=lambda index: types.SimpleNamespace(entity=body))
        with patch.object(entry, 'convert_solidBody', return_value=(None, None)), \
             patch.object(entry, 'set_pending_conversion') as pending:
            entry.command_executePreview(args)
            pending.assert_not_called()
        self.assertFalse(args.isValidResult)

        converted = types.SimpleNamespace(isValid=True)
        with patch.object(entry, 'convert_solidBody', return_value=(converted, converted)), \
             patch.object(entry, 'set_pending_conversion') as pending:
            entry.command_executePreview(args)
            pending.assert_called_once_with(converted)
        self.assertTrue(args.isValidResult)

    def test_folder_cancel_keeps_previous_choice(self) -> None:
        """フォルダ選択の取消し時に以前の選択を保持することを確認する。"""
        entry = self.export_entry
        entry._pathButtonIpt = object()
        entry._pathTxtIpt = types.SimpleNamespace(text='previous-folder')
        with patch.object(entry, 'get_folder_path', return_value=''):
            entry.command_inputChanged(types.SimpleNamespace(input=entry._pathButtonIpt))
        self.assertEqual(entry._pathTxtIpt.text, 'previous-folder')

    def test_start_failure_removes_only_new_definition(self) -> None:
        """起動失敗時に作成途中の定義を削除することを確認する。"""
        for entry in (self.export_entry, self.convert_entry):
            with self.subTest(command=entry.CMD_ID):
                definition = Mock()
                self.app.userInterface.commandDefinitions.addButtonDefinition.return_value = definition
                self.app.userInterface.workspaces.itemById.return_value = None
                with self.assertRaisesRegex(RuntimeError, 'Workspace unavailable'):
                    entry.start()
                definition.deleteMe.assert_called_once()


if __name__ == '__main__':
    unittest.main()
