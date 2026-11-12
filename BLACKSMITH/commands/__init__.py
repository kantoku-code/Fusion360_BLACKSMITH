# Here you define the commands that will be added to your add-in.

# TODO Import the modules corresponding to the commands you created.
# If you want to add an additional command, duplicate one of the existing directories and import it here.
# You need to use aliases (import "entry" as "my_module") assuming you have the default module named "entry".

# FlatPatternExport is retired but retained in the repository for reference.
# Do not import or start it unless it is deliberately restored.
from .Convert2SolidBody import entry as Convert2SolidBody
from .SheetMetalExport import entry as SheetMetalExport

# TODO add your imported modules to this list.
# Fusion will automatically call the start() and stop() functions.
commands = [
    SheetMetalExport,
    Convert2SolidBody,
]


# Assumes you defined a "start" function in each of your modules.
# The start function will be run when the add-in is started.
def start() -> None:
    """Fusion のツールバーにコマンドを登録する。"""
    started = []
    try:
        for command in commands:
            command.start()
            started.append(command)
    except Exception:
        for command in reversed(started):
            try:
                command.stop()
            except Exception:
                from ..lib import fusion360utils as futil
                futil.handle_error(f'{command.__name__}.stop')
        raise


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop() -> None:
    """アドインのコマンドとイベントハンドラを解除する。"""
    from ..lib import fusion360utils as futil
    for command in reversed(commands):
        try:
            command.stop()
        except Exception:
            futil.handle_error(f'{command.__name__}.stop')
