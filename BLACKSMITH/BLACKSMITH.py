# Assuming you have not changed the general structure of the template no modification is needed in this file.
from . import commands
from .lib import fusion360utils as futil


def run(context: dict[str, object]) -> None:
    """アドインの各コマンドを起動する。"""
    try:
        # This will run the start function in each of your commands as defined in commands/__init__.py
        commands.start()

    except:
        futil.handle_error('run')
        futil.clear_handlers()


def stop(context: dict[str, object]) -> None:
    """アドインのコマンドとイベントハンドラを解除する。"""
    try:
        # Remove command controls and their application-level handlers first.
        commands.stop()

    except:
        futil.handle_error('stop')
    finally:
        futil.clear_handlers()
