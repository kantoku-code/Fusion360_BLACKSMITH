import os

# ==============================================================================
# DEBUG MODE
# ==============================================================================
# Set to True to enable verbose logging in the Text Commands window (Py).
DEBUG = False

# ==============================================================================
# NAMES AND IDENTIFIERS
# ==============================================================================
# ADDIN_NAME is derived from the folder name containing this file.
ADDIN_NAME = os.path.basename(os.path.dirname(__file__))
COMPANY_NAME = "KANTOKU"

# ==============================================================================
# UI HIERARCHY (Workspaces, Tabs, Panels)
# ==============================================================================
# Design Workspace ID
design_workspace = "FusionSolidEnvironment"

# Tab Definitions
# Including COMPANY_NAME in the ID ensures uniqueness across different add-ins.
design_tab_id = f"{COMPANY_NAME}_{ADDIN_NAME}_design_tab"
design_tab_name = f"{ADDIN_NAME}"

# Panel IDs
doc_panel_id = f"{ADDIN_NAME}_doc_panel"
create_panel_id = f"{ADDIN_NAME}_create_panel"
modify_panel_id = f"{ADDIN_NAME}_modify_panel"
construction_panel_id = f"{ADDIN_NAME}_construction_panel"
inspect_panel_id = f"{ADDIN_NAME}_Inspect_panel"

# Panel Display Names (Japanese)
doc_panel_name = "ドキュメント"
create_panel_name = "作成"
modify_panel_name = "修正"
construction_panel_name = "構築"
inspect_panel_name = "検査"

# Panel Positioning (Empty string defaults to end of the tab)
doc_panel_after = ""
create_panel_after = ""
modify_panel_after = ""
construction_panel_after = ""
inspect_panel_after = ""

# ==============================================================================
# WORKSPACE REFERENCE LIST
# ==============================================================================
all_workspace_names = [
    "FusionSolidEnvironment",
    "GenerativeEnvironment",
    "PCBEnvironment",
    "PCB3DEnvironment",
    "Package3DEnvironment",
    "FusionRenderEnvironment",
    "Publisher3DEnvironment",
    "SimulationEnvironment",
    "CAMEnvironment",
    "DebugEnvironment",
    "FusionDocumentationEnvironment",
    "ElectronEmptyLbrEnvironment",
    "ElectronDeviceEnvironment",
    "ElectronFootprintEnvironment",
    "ElectronSymbolEnvironment",
    "ElectronPackageEnvironment",
]

# ==============================================================================
# PALETTE DEFINITIONS
# ==============================================================================
sample_palette_id = f"{COMPANY_NAME}_{ADDIN_NAME}_palette_id"
fullsize_palette_id = f"{COMPANY_NAME}_{ADDIN_NAME}_fullsize_id"

# ==============================================================================
# GLOBAL STATE / CACHE
# ==============================================================================
# These dictionaries are used to keep references alive in memory
# to prevent Python's garbage collector from deleting your handlers.
convert2SolidBody_dict = {
    "handler": None,
    "body": None,
}

# General global storage for other command handlers or event pointers
my_handlers = []
