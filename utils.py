# utils.py
# Versión 3.0 – 2026-06-24

import os
import time
import fcntl
from datetime import datetime
from telemetry import telemetry

def acquire_lock(lock_file: str, timeout: float = 10) -> bool:
    try:
        fd = open(lock_file, 'w')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError, OSError):
        return False

def release_lock(lock_file: str):
    try:
        fd = open(lock_file, 'w')
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
    except:
        pass

def validate_config(config_dict: dict) -> bool:
    required = ["SYMBOLS", "TRADE_NOTIONAL", "LEVERAGE", "TP_MULT", "SL_MULT",
                "MAX_REPAIR_ATTEMPTS", "BACKOFF_BASE", "SYNC_TIME_ENABLED"]
    for key in required:
        if key not in config_dict:
            telemetry.log_error("utils", f"Configuración faltante: {key}")
            return False
    return True

def is_trading_time() -> bool:
    """Verifica si la hora actual está dentro del filtro horario."""
    from config import TIME_FILTER_ENABLED, TIME_FILTER_START, TIME_FILTER_END, TIME_FILTER_WEEKDAYS
    if not TIME_FILTER_ENABLED:
        return True
    now = datetime.utcnow()
    if now.weekday() not in TIME_FILTER_WEEKDAYS:
        return False
    hour = now.hour + now.minute / 60.0
    return TIME_FILTER_START <= hour <= TIME_FILTER_END

def health_check() -> dict:
    try:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "memory_used_percent": mem.percent,
            "disk_used_percent": disk.percent,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "ok": mem.percent < 90 and disk.percent < 90
        }
    except:
        return {"ok": True, "memory_used_percent": 0, "disk_used_percent": 0, "cpu_percent": 0}
