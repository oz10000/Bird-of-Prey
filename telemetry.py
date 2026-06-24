# telemetry.py
# Versión 3.0 – 2026-06-24

import logging
import json
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

class Telemetry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.logger = logging.getLogger("PiDelta")
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Consola
        if LOG_CONSOLE:
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        # Archivo de logs (texto)
        if LOG_FILE:
            os.makedirs(LOG_DIR, exist_ok=True)
            fh = RotatingFileHandler(
                os.path.join(LOG_DIR, 'bot.log'),
                maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
                backupCount=MAX_LOG_FILES
            )
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        # Archivo JSON estructurado (para análisis)
        if LOG_JSON:
            self.json_logger = logging.getLogger("PiDeltaJSON")
            self.json_logger.setLevel(logging.INFO)
            json_handler = RotatingFileHandler(
                os.path.join(LOG_DIR, 'runtime.json'),
                maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
                backupCount=MAX_LOG_FILES
            )
            json_handler.setFormatter(logging.Formatter('%(message)s'))
            self.json_logger.addHandler(json_handler)

    def _log(self, level, module, message, data=None):
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'module': module,
            'level': level,
            'message': message,
            'data': data or {}
        }
        # Log en texto
        getattr(self.logger, level)(f"[{module}] {message} {json.dumps(data) if data else ''}")
        # Log JSON
        if LOG_JSON:
            getattr(self.json_logger, level)(json.dumps(entry))

    def log_info(self, module, message, data=None):
        self._log('info', module, message, data)

    def log_warning(self, module, message, data=None):
        self._log('warning', module, message, data)

    def log_error(self, module, message, data=None):
        self._log('error', module, message, data)

    def log_debug(self, module, message, data=None):
        self._log('debug', module, message, data)

# Importar configuración para logging
from config import LOG_DIR, LOG_CONSOLE, LOG_FILE, LOG_JSON, MAX_LOG_SIZE_MB, MAX_LOG_FILES

telemetry = Telemetry()
