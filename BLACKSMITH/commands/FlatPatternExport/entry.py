import adsk.core as core
import adsk.fusion as fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .FlatPatternExportFactry import FlatPatternExportFactry
import pathlib
from .LanguageMessage import LanguageMessage
import platform
import subprocess

app = core.Application.get()
ui = app.userInterface

# lang msg
_lm = LanguageMessage()

# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_flat_export_dxf'
CMD_NAME = _lm.s('Exportsssssss')
CMD_Description = _lm.s('Export flat pattern')

# パネルにコマンドを昇格させることを指定します。
IS_PROMOTED = False

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
_optButtonIpt: core.ButtonRowCommandInput = None
_options = (
    ('DXF', True, str(pathlib.Path(ICON_FOLDER) / 'dxf')),
    # ('STEP', False, str(pathlib.Path(ICON_FOLDER) / 'stp')),
    # ('IGES', False, str(pathlib.Path(ICON_FOLDER) / 'igs')),
    ('SAT', False, str(pathlib.Path(ICON_FOLDER) / 'sat')),
)
_table: core.TableCommandInput = None
_fact: 'FlatPatternExportFactry' = None

# アドイン実行時に実行されます。
def start():
    # コマンドの定義を作成する。
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID,
        CMD_NAME,
        CMD_Description,
        str(pathlib.Path(ICON_FOLDER) / 'cmd'),
    )

    # コマンド作成イベントのイベントハンドラを定義します。
    # このハンドラは、ボタンがクリックされたときに呼び出されます。
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** ユーザーがコマンドを実行できるように、UIにボタンを追加します。 ********
    # ボタンが作成される対象のワークスペースを取得します。
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    toolbar_tab = workspace.toolbarTabs.itemById(TAB_ID)
    # if toolbar_tab is None:
    #     toolbar_tab = workspace.toolbarTabs.add(TAB_ID, TAB_NAME)

    # ボタンが作成されるパネルを取得します。
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    # if panel is None:
    #     panel = toolbar_tab.toolbarPanels.add(PANEL_ID, PANEL_NAME, PANEL_AFTER, False)

    # 指定された既存のコマンドの後に、UI のボタンコマンド制御を作成します。
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # コマンドをメインツールバーに昇格させるかどうかを指定します。
    control.isPromoted = IS_PROMOTED


# アドイン停止時に実行されます。
def stop():
    # このコマンドのさまざまなUI要素を取得する
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # ボタンコマンドの制御を削除する。
    if command_control:
        command_control.deleteMe()

    # コマンドの定義を削除します。
    if command_definition:
        command_definition.deleteMe()


def command_created(args: core.CommandCreatedEventArgs):

    cmd: core.Command = core.Command.cast(args.command)
    cmd.isPositionDependent = True

    # factry
    global _fact
    _fact = FlatPatternExportFactry()

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

    # フォーマット
    global _optButtonIpt, _options
    _optButtonIpt = inputs.addButtonRowCommandInput(
        '_optButtonIptId',
        'フォーマット',
        True
    )
    optItems: core.ListItems = _optButtonIpt.listItems
    for opt in _options:
         optItems.add(opt[0], opt[1], opt[2])

    # フラットパターン
    groupFlatIpt: core.GroupCommandInput = inputs.addGroupCommandInput(
        'groupFlatIptId',
        _lm.s('Check on components to export'),
    )
    groupFlatIpt.isExpanded = True
    flatInputs = groupFlatIpt.children

    global _table
    _table = flatInputs.addTableCommandInput(
        '_tableId',
        'Table',
        0,
        '1:5'
    )
    _table.hasGrid = False
    tableStyle = core.TablePresentationStyles
    _table.tablePresentationStyle = tableStyle.itemBorderTablePresentationStyle
    rowCount = len(_fact.flatInfos)
    if rowCount > 10:
        _table.maximumVisibleRows = 10
    elif rowCount > 4:
        _table.maximumVisibleRows = rowCount

    for idx, info in enumerate(_fact.flatInfos):
        chk: core.BoolValueCommandInput = flatInputs.addBoolValueInput(
            f'check_{idx}',
            'Checkbox',
            True,
            '',
            info["show"]
        )
        _table.addCommandInput(chk, idx, 0)

        compName: core.StringValueCommandInput = flatInputs.addStringValueInput(
            f'comp_{idx}',
            'comp name',
            info["comp"].name,)
        compName.isReadOnly = True
        _table.addCommandInput(compName, idx, 1)

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


def command_validateInputs(args: core.ValidateInputsEventArgs):

    global _optButtonIpt
    if len(get_check_on_option_indexs(_optButtonIpt)) < 1:
        args.areInputsValid = False
        return

    global _table
    if len(get_check_on_indexs(_table)) < 1:
        args.areInputsValid = False
        return

    global _pathTxtIpt
    if len(_pathTxtIpt.text) < 1:
        args.areInputsValid = False
        return


def command_destroy(args: core.CommandEventArgs):

    global local_handlers
    local_handlers = []


def command_execute(args: core.CommandEventArgs):

    global _table
    global _optButtonIpt
    global _fact, _pathTxtIpt
    _fact.exec_export(
        get_check_on_indexs(_table),
        get_check_on_option_indexs(_optButtonIpt),
        # ['DXF'],
        _pathTxtIpt.text,
    )

    open_folder(_pathTxtIpt.text)

def get_check_on_indexs(table: core.TableCommandInput) -> list:
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


def get_check_on_option_indexs(dropIpt: core.ButtonRowCommandInput) -> list:
    '''
    チェックONのフォーマットを取得
    '''
    optLst = []
    for opt in dropIpt.listItems:
        if opt.isSelected:
            optLst.append(opt.name)

    return optLst


def command_inputChanged(args: core.InputChangedEventArgs):

    global _pathButtonIpt
    if args.input != _pathButtonIpt:
        return

    global _pathTxtIpt
    _pathTxtIpt.text = get_folder_path()


def get_folder_path():
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

    if not path.exists():
        return

    if platform.system() == 'Windows':
        os.startfile(str(path))
    else:
        subprocess.check_call(["open", "--", str(path)])