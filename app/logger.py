from __future__ import annotations

import functools
import inspect
import logging
import traceback
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "log.txt"

_logger = logging.getLogger("medical_ner")
if not _logger.handlers:
    _logger.setLevel(logging.DEBUG)
    _file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _file_handler.setLevel(logging.DEBUG)
    _formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _file_handler.setFormatter(_formatter)
    _logger.addHandler(_file_handler)


def get_logger() -> logging.Logger:
    return _logger


def _record_exception(func, exc: BaseException) -> None:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _logger.error(
        "Exception in function '%s': %s\n%s",
        getattr(func, "__qualname__", repr(func)),
        exc,
        tb,
    )


def log_exceptions(_func=None, *, reraise: bool = True):
    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    _record_exception(func, exc)
                    if reraise:
                        raise
                    return None

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                _record_exception(func, exc)
                if reraise:
                    raise
                return None

        return wrapper

    if _func is not None and callable(_func):
        return decorator(_func)
    return decorator
