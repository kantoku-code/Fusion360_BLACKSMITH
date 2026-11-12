import adsk.core as core
import adsk.fusion as fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .Convert2SolidBodyFactry import (
    clear_pending_conversion, convert_solidBody, set_pending_conversion,
)
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
_compIpt: core.BoolValueCommandInput = None

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
    """アドインのコマンドとイベントハンドラを解除する。"""
    clear_pending_conversion()
    # このコマンドのさまざまなUI要素を取得する
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

    # **inputs**
    inputs: core.CommandInputs = cmd.commandInputs

    global _bodyIpt
    _bodyIpt = inputs.addSelectionInput(
        '_bodyIptId',
        _lm.s('Sheet Metal Body'),
        _lm.s('Select sheet metal body to convert'),
    )
    _bodyIpt.addSelectionFilter(core.SelectionCommandInput.SolidBodies)

    global _compIpt
    _compIpt = inputs.addBoolValueInput(
        '_compIptId',
        _lm.s('Create Components from Bodies'),
        True,
        '',
        True
    )

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


def command_preSelect(args: core.SelectionEventArgs) -> None:

    """選択候補が変換対象の板金ボディか確認する。"""
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


def command_destroy(args: core.CommandEventArgs) -> None:

    """コマンド終了後にローカルハンドラを解放する。"""
    global local_handlers
    local_handlers = []
    if args.terminationReason != core.CommandTerminationReason.CompletedTerminationReason:
        clear_pending_conversion()


def command_executePreview(args: core.CommandEventArgs) -> None:

    """選択した板金ボディの変換をプレビューする。"""
    global _bodyIpt, _compIpt
    clear_pending_conversion()
    args.isValidResult = False
    if _bodyIpt.selectionCount < 1:
        return
    body: fusion.BRepBody = _bodyIpt.selection(0).entity
    if body is None or not body.isSheetMetal:
        return
    try:
        solid, followup_body = convert_solidBody(body, _compIpt.value)
        if solid is None or not solid.isValid:
            return
        set_pending_conversion(followup_body)
        args.isValidResult = True
    except Exception:
        futil.handle_error('convert preview')


def has_referenced_component(
    occ: fusion.Occurrence,
) -> bool:

    """オカレンスの経路に参照コンポーネントがあるか調べる。"""
    occNames = occ.fullPathName.split('+')
    comp: fusion.Component = occ.sourceComponent
    occs = [comp.allOccurrences.itemByName(n) for n in occNames]

    return any([o.isReferencedComponent for o in occs])
