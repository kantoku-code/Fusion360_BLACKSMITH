import adsk.core as core
import adsk.fusion as fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .SheetMetalExportFactry import SheetMetalExportFactry
import pathlib
from .LanguageMessage import LanguageMessage
import platform
import subprocess

app = core.Application.get()
ui = app.userInterface

# lang msg
_lm = LanguageMessage()

# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_sheetmetal_export_dxf'
CMD_NAME = _lm.s('Export')
CMD_Description = _lm.s('Create and export a flat pattern from a SheetMetal Body.')

# パネルにコマンドを昇格させることを指定します。
IS_PROMOTED = True

# TODO *** コマンドボタンが作成される場所を定義します。 ***
# これは、ワークスペース、タブ、パネル、および 
# コマンドの横に挿入されます。配置するコマンドを指定しない場合は
# 最後に挿入されます。

WORKSPACE_ID = 'FusionSolidEnvironment'
TAB_ID = config.design_tab_id
# TAB_NAME = config.design_tab_name

PANEL_ID = 'SheetMetalModifyPanel'
# PANEL_NAME = config.create_panel_name
# PANEL_AFTER = config.create_panel_after

COMMAND_BESIDE_ID = ''

# コマンドアイコンのリソースの場所、ここではこのディレクトリの中に
# "resources" という名前のサブフォルダを想定しています。
ICON_FOLDER = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    'resources',
    ''
)

# イベントハンドラのローカルリストで、参照を維持するために使用されます。
# それらは解放されず、ガベージコレクションされません。
local_handlers = []

# inputs
_pathButtonIpt: core.BoolValueCommandInput = None
_pathTxtIpt: core.TextBoxCommandInput = None
_useBodyNameIpt: core.BoolValueCommandInput = None
_optButtonIpt: core.ButtonRowCommandInput = None
_options = (
    ('DXF', True, str(pathlib.Path(ICON_FOLDER) / 'dxf')),
    # ('STEP', False, str(pathlib.Path(ICON_FOLDER) / 'stp')),
    # ('IGES', False, str(pathlib.Path(ICON_FOLDER) / 'igs')),
    ('SAT', False, str(pathlib.Path(ICON_FOLDER) / 'sat')),
)
_table: core.TableCommandInput = None
_fact: 'SheetMetalExportFactry' = None

# アドイン実行時に実行されます。
def start() -> None:
    """Fusion のツールバーにコマンドを登録する。"""
    cmd_def = None
    control = None
    try:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_Description, str(pathlib.Path(ICON_FOLDER) / 'cmd'))
        futil.add_handler(cmd_def.commandCreated, command_created)
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        if not workspace:
            raise RuntimeError(f'Workspace unavailable: {WORKSPACE_ID}')
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        if not panel:
            raise RuntimeError(f'Panel unavailable: {PANEL_ID}')
        control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
        control.isPromoted = IS_PROMOTED
    except Exception:
        if control:
            control.deleteMe()
        if cmd_def:
            cmd_def.deleteMe()
        raise


# アドイン停止時に実行されます。
def stop() -> None:
    # このコマンドのさまざまなUI要素を取得する
    """アドインのコマンドとイベントハンドラを解除する。"""
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    command_control = panel.controls.itemById(CMD_ID) if panel else None
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # ボタンコマンドの制御を削除する。
    if command_control:
        command_control.deleteMe()

    # コマンドの定義を削除します。
    if command_definition:
        command_definition.deleteMe()


def command_created(args: core.CommandCreatedEventArgs) -> None:

    """コマンドの入力欄とイベントハンドラを作成する。"""
    cmd: core.Command = core.Command.cast(args.command)
    cmd.isPositionDependent = True

    # factry
    global _fact
    _fact = SheetMetalExportFactry()

    # **inputs**
    inputs: core.CommandInputs = cmd.commandInputs

    # フォルダ
    tableFolder: core.TableCommandInput = inputs.addTableCommandInput(
        'tableFolderId',
        'Table',
        0,
        '5:1'
    )
    tableFolder.hasGrid = False
    tableStyle = core.TablePresentationStyles
    tableFolder.tablePresentationStyle = tableStyle.itemBorderTablePresentationStyle
    tableFolder.minimumVisibleRows = 1

    global _pathTxtIpt
    _pathTxtIpt = inputs.addTextBoxCommandInput(
        '_pathTxtIptId',
        '',
        '',
        1,
        True,
    )
    tableFolder.addCommandInput(_pathTxtIpt, 1, 0)

    global _pathButtonIpt
    _pathButtonIpt = inputs.addBoolValueInput(
        '_pathButtonIptId',
        _lm.s('Folder'),
        False,
        str(pathlib.Path(ICON_FOLDER) / 'folder'),
        False
    )
    tableFolder.addCommandInput(_pathButtonIpt, 1, 1)

    # ボディ名の使用
    global _useBodyNameIpt
    _useBodyNameIpt = inputs.addBoolValueInput(
        "_useBodyNameIptId",
        _lm.s("Use the body name as the export file name."),
        True,
        "",
        True,
    )

    # フォーマット
    global _optButtonIpt, _options
    _optButtonIpt = inputs.addButtonRowCommandInput(
        '_optButtonIptId',
        _lm.s('Format'),
        True
    )
    optItems: core.ListItems = _optButtonIpt.listItems
    for opt in _options:
         optItems.add(opt[0], opt[1], opt[2])

    # フラットパターン
    groupFlatIpt: core.GroupCommandInput = inputs.addGroupCommandInput(
        'groupFlatIptId',
        _lm.s('Place a check mark in the body/component to be exported'),
    )
    groupFlatIpt.isExpanded = True
    flatInputs = groupFlatIpt.children

    global _table
    _table = flatInputs.addTableCommandInput(
        '_tableId',
        'Table',
        0,
        '1:3:3'
    )
    _table.hasGrid = False
    tableStyle = core.TablePresentationStyles
    _table.tablePresentationStyle = tableStyle.itemBorderTablePresentationStyle
    rowCount = len(_fact.sheetInfos)
    if rowCount > 10:
        _table.maximumVisibleRows = 10
    elif rowCount > 4:
        _table.maximumVisibleRows = rowCount

    for idx, info in enumerate(_fact.sheetInfos):
        chk: core.BoolValueCommandInput = flatInputs.addBoolValueInput(
            f'check_{idx}',
            'Checkbox',
            True,
            '',
            info["show"]
        )
        _table.addCommandInput(chk, idx, 0)

        bodyName: core.StringValueCommandInput = flatInputs.addStringValueInput(
            f'body_{idx}',
            'body name',
            info["native"].name,)
        bodyName.isReadOnly = True
        _table.addCommandInput(bodyName, idx, 1)

        compName: core.StringValueCommandInput = flatInputs.addStringValueInput(
            f'comp_{idx}',
            'comp name',
           info["native"].parentComponent.name,)
        compName.isReadOnly = True
        _table.addCommandInput(compName, idx, 2)

    # **event**
    futil.add_handler(
        cmd.destroy,
        command_destroy,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.execute,
        command_execute,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.inputChanged,
        command_inputChanged,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.validateInputs,
        command_validateInputs,
        local_handlers=local_handlers
    )


def command_validateInputs(args: core.ValidateInputsEventArgs) -> None:

    """選択項目と出力先を確認する。"""
    global _optButtonIpt
    if len(get_check_on_option_indexs(_optButtonIpt)) < 1:
        args.areInputsValid = False
        return

    global _table
    if len(get_check_on_indexs(_table)) < 1:
        args.areInputsValid = False
        return

    global _pathTxtIpt
    if not _pathTxtIpt.text or not pathlib.Path(_pathTxtIpt.text).is_dir():
        args.areInputsValid = False
        return


def command_destroy(args: core.CommandEventArgs) -> None:

    """コマンド終了後にローカルハンドラを解放する。"""
    global local_handlers
    local_handlers = []


def command_execute(args: core.CommandEventArgs) -> None:

    """選択した対象を指定形式で書き出す。"""
    global _table
    global _optButtonIpt
    global _fact, _pathTxtIpt
    global _useBodyNameIpt
    folder = pathlib.Path(_pathTxtIpt.text)
    if not _pathTxtIpt.text or not folder.is_dir():
        show_report([f'Invalid export folder: {folder}'])
        return
    ngLst = _fact.export_sheetMetal_flatPattern(
        get_check_on_indexs(_table),
        get_check_on_option_indexs(_optButtonIpt),
        _pathTxtIpt.text,
        _useBodyNameIpt.value,
    )

    if len(ngLst) > 0:
        show_report(ngLst)

    open_folder(_pathTxtIpt.text)


def get_check_on_indexs(table: core.TableCommandInput) -> list[int]:
    '''
    テーブル内のチェックONのインデックス取得
    '''
    indexs = []
    inputsType = core.BoolValueCommandInput.classType()
    for inputs in table.parentCommandInput.commandInputs:
        if inputs.objectType != inputsType:
            continue
        if not 'check_' in inputs.id:
            continue
        inputs = core.BoolValueCommandInput.cast(inputs)
        if inputs.value:
            indexs.append(int(inputs.id.split('_')[-1]))

    return indexs


def get_check_on_option_indexs(dropIpt: core.ButtonRowCommandInput) -> list[str]:
    '''
    チェックONのフォーマットを取得
    '''
    optLst = []
    for opt in dropIpt.listItems:
        if opt.isSelected:
            optLst.append(opt.name)

    return optLst


def command_inputChanged(args: core.InputChangedEventArgs) -> None:

    """出力先選択ボタンの変更を反映する。"""
    global _pathButtonIpt
    if args.input != _pathButtonIpt:
        return

    global _pathTxtIpt
    selected_path = get_folder_path()
    if selected_path:
        _pathTxtIpt.text = selected_path


def get_folder_path() -> str:
    '''
    フォルダパスの取得
    '''
    ui: core.UserInterface = futil.app.userInterface
    dialog: core.FolderDialog = ui.createFolderDialog()
    res: core.DialogResults = dialog.showDialog()

    if res == core.DialogResults.DialogOK:
        return dialog.folder

    return ''


def open_folder(folderPath: str) -> None:
    '''
    フォルダーを開く
    '''
    path = pathlib.Path(folderPath)

    if not path.is_dir():
        return

    if platform.system() == 'Windows':
        os.startfile(str(path))
    else:
        subprocess.check_call(["open", "--", str(path)])

def show_report(lst: list[str]) -> None:

    """書き出し失敗の一覧を Fusion のログに記録する。"""
    app: core.Application = core.Application.get()
    app.log('** export error **\n{}'.format("\n".join(lst)))
