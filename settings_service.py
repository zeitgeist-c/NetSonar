"""Validated settings and Windows user-bound secret protection."""

from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes

DPAPI_PREFIX = "dpapi:"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _crypt32():
    library = ctypes.windll.crypt32
    library.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.POINTER(_DataBlob),
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob),
    ]
    library.CryptProtectData.restype = wintypes.BOOL
    library.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(_DataBlob),
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob),
    ]
    library.CryptUnprotectData.restype = wintypes.BOOL
    return library


def protect_secret(secret: str) -> str:
    value = str(secret or "")
    if not value or value.startswith(DPAPI_PREFIX):
        return value
    if os.name != "nt":
        raise OSError("DPAPI is available only on Windows")
    source, keepalive = _blob(value.encode("utf-8"))
    output = _DataBlob()
    if not _crypt32().CryptProtectData(
        ctypes.byref(source), "NetSonar API key", None, None, None, 0x1, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return DPAPI_PREFIX + base64.b64encode(
            ctypes.string_at(output.pbData, output.cbData)
        ).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del keepalive


def unprotect_secret(secret: str) -> str:
    value = str(secret or "")
    if not value.startswith(DPAPI_PREFIX):
        return value
    if os.name != "nt":
        raise OSError("DPAPI is available only on Windows")
    source, keepalive = _blob(base64.b64decode(value[len(DPAPI_PREFIX):], validate=True))
    output = _DataBlob()
    if not _crypt32().CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del keepalive


def validate_settings(data: dict, defaults: dict) -> dict:
    result = dict(defaults)
    result.update(data if isinstance(data, dict) else {})
    for key, default in (("AUTO_ANALYSIS_ENABLED", True), ("AUTO_BLOCK_ENABLED", False),
                         ("MINIMIZE_TO_TRAY", True), ("autostart", False)):
        result[key] = bool(result.get(key, default))
    try:
        result["ANALYSIS_INTERVAL_MINUTES"] = max(
            1, min(1440, int(result.get("ANALYSIS_INTERVAL_MINUTES", 60))))
    except (TypeError, ValueError):
        result["ANALYSIS_INTERVAL_MINUTES"] = 60
    try:
        result["HIGH_TRAFFIC_THRESHOLD_BYTES"] = max(
            1024**2, min(10 * 1024**3, int(result.get("HIGH_TRAFFIC_THRESHOLD_BYTES", 50 * 1024**2))))
    except (TypeError, ValueError):
        result["HIGH_TRAFFIC_THRESHOLD_BYTES"] = 50 * 1024**2
    try:
        result["AUTO_BLOCK_MIN_RISK_SCORE"] = max(
            0.0, min(10.0, float(result.get("AUTO_BLOCK_MIN_RISK_SCORE", 7.0))))
    except (TypeError, ValueError):
        result["AUTO_BLOCK_MIN_RISK_SCORE"] = 7.0
    return result
