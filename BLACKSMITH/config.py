# アプリケーショングローバル変数
# このモジュールは、さまざまな変数間で変数を共有する方法として機能します。
# モジュール（グローバル変数）です。

import os

# デバッグモードで動作させるかどうかを示すフラグ。
# バッグモードで実行する場合 テキストコマンドウィンドウに、より多くの情報が書き込まれます。
# 一般に、以下のような場合に便利です。
# アドイン開発中はTrueに設定し、開発終了後にFalseに設定し、配布することができます。
DEBUG = False

# pyファイルがあるフォルダの名前からアドインの名前を取得します。
# これは、ユニークな名前を必要とする様々なUI要素のために、
# ユニークな内部名を定義するときに使用されます。
# また、IDの一意性をより確実にするために、
# IDの一部として会社名を使用することが推奨される。
ADDIN_NAME = os.path.basename(os.path.dirname(__file__))
COMPANY_NAME = 'KANTOKU'

# Name for a directory in user home to store data
# user_dir_name = f'{ADDIN_NAME}'

# Design Workspace
design_workspace = 'FusionSolidEnvironment'

# Tabs
design_tab_id = f'{ADDIN_NAME}_design_tab'
design_tab_name = f'{ADDIN_NAME}'

# Panels
doc_panel_name = 'ドキュメント'
doc_panel_id = f'{ADDIN_NAME}_doc_panel'
doc_panel_after = ''

create_panel_name = '作成'
create_panel_id = f'{ADDIN_NAME}_create_panel'
create_panel_after = ''

modify_panel_name = '修正'
modify_panel_id = f'{ADDIN_NAME}_modify_panel'
modify_panel_after = ''

construction_panel_name = '構築'
construction_panel_id = f'{ADDIN_NAME}_construction_panel'
construction_panel_after = ''

inspect_panel_name = '検査'
inspect_panel_id = f'{ADDIN_NAME}_Inspect_panel'
inspect_panel_after = ''


# Reference for use in some commands
all_workspace_names = [
    'FusionSolidEnvironment', 'GenerativeEnvironment', 'PCBEnvironment', 'PCB3DEnvironment', 'Package3DEnvironment',
    'FusionRenderEnvironment', 'Publisher3DEnvironment', 'SimulationEnvironment', 'CAMEnvironment', 'DebugEnvironment',
    'FusionDocumentationEnvironment', 'ElectronEmptyLbrEnvironment', 'ElectronDeviceEnvironment',
    'ElectronFootprintEnvironment', 'ElectronSymbolEnvironment', 'ElectronPackageEnvironment'
]

# Palettes
sample_palette_id = f'{COMPANY_NAME}_{ADDIN_NAME}_palette_id'

fullsize_palette_id = f'{COMPANY_NAME}_{ADDIN_NAME}_fullsize_id'