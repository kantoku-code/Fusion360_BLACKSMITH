from re import S
import adsk.core as core
import adsk.fusion as fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .Convert2SolidBodyFactry import to_solidBody
import pathlib
from .LanguageMessage import LanguageMessage

app = core.Application.get()
ui = app.userInterface

# lang msg
_lm = LanguageMessage()


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_conv2solid'
CMD_NAME = _lm.s('Convert to Solid')
CMD_Description = _lm.s('Convert sheet metal body to solid body')

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
_bodyIpt: core.SelectionCommandInput = None

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

    # **inputs**
    inputs: core.CommandInputs = cmd.commandInputs

    global _bodyIpt
    _bodyIpt = inputs.addSelectionInput(
        '_bodyIptId',
        _lm.s('Sheet Metal Body'),
        _lm.s('Select sheet metal body to convert'),
    )
    _bodyIpt.addSelectionFilter(core.SelectionCommandInput.SolidBodies)


    # **event**
    futil.add_handler(
        cmd.destroy,
        command_destroy,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.executePreview,
        command_executePreview,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.preSelect,
        command_preSelect,
        local_handlers=local_handlers)


def command_preSelect(args: core.SelectionEventArgs):

    body: fusion.BRepBody = args.selection.entity
    if not body.isSheetMetal:
        args.isSelectable = False
        return

    occ: fusion.Occurrence = body.assemblyContext
    if not occ:
        return

    if has_referenced_component(occ):
        args.isSelectable = False
        return


def command_destroy(args: core.CommandEventArgs):

    global local_handlers
    local_handlers = []


def command_executePreview(args: core.CommandEventArgs):

    global _bodyIpt
    to_solidBody(_bodyIpt.selection(0).entity)

    args.isValidResult = True


def has_referenced_component(
    occ: fusion.Occurrence,
) -> bool:

    occNames = occ.fullPathName.split('+')
    comp: fusion.Component = occ.sourceComponent
    occs = [comp.allOccurrences.itemByName(n) for n in occNames]

    return any([o.isReferencedComponent for o in occs])