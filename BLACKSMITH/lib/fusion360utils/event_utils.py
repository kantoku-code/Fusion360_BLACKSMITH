#  Copyright 2022 by Autodesk, Inc.
#  Permission to use, copy, modify, and distribute this software in object code form
#  for any purpose and without fee is hereby granted, provided that the above copyright
#  notice appears in all copies and that both that copyright notice and the limited
#  warranty and restricted rights notice below appear in all supporting documentation.
#
#  AUTODESK PROVIDES THIS PROGRAM "AS IS" AND WITH ALL FAULTS. AUTODESK SPECIFICALLY
#  DISCLAIMS ANY IMPLIED WARRANTY OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR USE.
#  AUTODESK, INC. DOES NOT WARRANT THAT THE OPERATION OF THE PROGRAM WILL BE
#  UNINTERRUPTED OR ERROR FREE.

import sys
from typing import Callable

import adsk.core
from .general_utils import handle_error


# Global Variable to hold Event Handlers
_handlers = []


def add_handler(
        event: adsk.core.Event,
        callback: Callable,
        *,
        name: str | None = None,
        local_handlers: list[object] | None = None
) -> object:
    """Fusion のイベントにコールバックを登録する。"""
    module = sys.modules[event.__module__]
    handler_type = module.__dict__[event.add.__annotations__['handler']]
    handler = _create_handler(handler_type, callback, event, name, local_handlers)
    event.add(handler)
    return handler


def clear_handlers() -> None:
    """保持しているグローバルイベントハンドラを解放する。"""
    global _handlers
    _handlers = []


def _create_handler(
        handler_type: type,
        callback: Callable,
        event: adsk.core.Event,
        name: str | None = None,
        local_handlers: list[object] | None = None
) -> object:
    """コールバック用ハンドラを生成して参照を保持する。"""
    handler = _define_handler(handler_type, callback, name)()
    (local_handlers if local_handlers is not None else _handlers).append(handler)
    return handler


def _define_handler(handler_type: type, callback: Callable, name: str | None = None) -> type:
    """イベントをコールバックへ渡すハンドラクラスを定義する。"""
    name = name or handler_type.__name__

    class Handler(handler_type):
        """Fusion イベントをコールバックへ中継する。"""
        def __init__(self) -> None:
            """Fusion のイベントハンドラを初期化する。"""
            super().__init__()

        def notify(self, args: object) -> None:
            """イベント引数をコールバックに渡し、例外を記録する。"""
            try:
                callback(args)
            except:
                handle_error(name)

    return Handler
