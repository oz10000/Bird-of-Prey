# config.py
# ============================================================
# CONFIGURACIÓN OPTIMIZADA – BIRD-OF-PREY
# Cambios mínimos para máxima mejora estadística
# ============================================================

# ---- Símbolos y operativa ----
SYMBOLS = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']
TRADE_NOTIONAL = 1000.0          # USDT por operación
LEVERAGE = 10                    # Apalancamiento fijo

# ---- Parámetros de estrategia (OPTIMIZADOS) ----
TP_MULT = 1.0                    # Take Profit = ATR * 1.0 (antes 1.2)
SL_MULT = 1.2                    # Stop Loss = ATR * 1.2 (antes 1.5)
ATR_PERIOD = 14
BE_GAIN = 0.0005
BE_UMBRAL = 0.30

# ---- Trailing Stop ----
TRAILING_ENABLED = False
TRAILING_MODE = 'native'
TRAILING_DISTANCE_ATR = 0.8

# ---- Niveles de velocidad (AutoSpeed) ----
SPEED_LEVELS = [
    {"nivel": 1, "raw_min": 0.45, "roc_min": 0.30},
    {"nivel": 2, "raw_min": 0.40, "roc_min": 0.25},
    {"nivel": 3, "raw_min": 0.35, "roc_min": 0.20},
    {"nivel": 4, "raw_min": 0.30, "roc_min": 0.15},
    {"nivel": 5, "raw_min": 0.25, "roc_min": 0.10},
    {"nivel": 6, "raw_min": 0.20, "roc_min": 0.05},
]
DEFAULT_SPEED_LEVEL = SPEED_LEVELS[0]   # Nivel 1 (más restrictivo, óptimo)

# ---- Filtros horarios ----
TIME_FILTER_ENABLED = False
TIME_FILTER_START = 12
TIME_FILTER_END = 18
TIME_FILTER_WEEKDAYS = [0, 1, 2, 3, 4]

# ---- Filtros por activo ----
FILTERS = {
    'BTC': {'Long': {'ker_min': 0.55, 'zscore_min': 1.2},
            'Short': {'zscore_max': -1.8, 'vol_rel_min': 1.8}},
    'ETH': {'Long': {'ker_min': 0.50, 'atr_percent_min': 0.75},
            'Short': {'zscore_max': -1.5, 'ker_min': 0.50}},
    'SOL': {'Long': {'vol_rel_min': 1.8, 'ema_pend_min': 0.0015},
            'Short': {'ker_min': 0.60, 'zscore_max': -1.2}},
    'ADA': {'Long': {'ker_min': 0.45, 'vol_rel_min': 1.5, 'atr_percent_min': 0.80},
            'Short': {'ker_min': 0.45, 'zscore_max': -1.0, 'vol_rel_min': 1.5}},
    'XRP': {'Long': {'ker_min': 0.40, 'vol_rel_min': 1.5, 'zscore_min': 0.8},
            'Short': {'ker_min': 0.40, 'zscore_max': -0.8, 'vol_rel_min': 1.5}}
}

# ---- Recuperación y reintentos (CONSTANTES FALTANTES) ----
MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_BACKOFF = 5
BACKOFF_BASE = 5
MAX_RETRIES_PER_ORDER = 3
ORDER_TIMEOUT = 15
LOCK_FILE = '.lock'
LOCK_TIMEOUT = 10
SYNC_TIME_ENABLED = True
MAX_CONSECUTIVE_ERRORS = 5
MAX_REPAIR_ATTEMPTS = 3

# ---- Control de Riesgo ----
MAX_DAILY_LOSS_PERCENT = 2.0
MAX_WEEKLY_LOSS_PERCENT = 4.0
MAX_OPEN_POSITIONS = 3

# ---- Backtesting (REDUCIDO para evitar timeout) ----
BACKTEST_DAYS = 2                # Valor pequeño para que el backtest sea rápido
BACKTEST_FEE_MAKER = 0.0005
BACKTEST_FEE_TAKER = 0.0007
BACKTEST_SLIPPAGE = 0.0002

# ---- Logging ----
LOG_DIR = 'logs'
LOG_LEVEL = 'INFO'
LOG_CONSOLE = True
LOG_FILE = True
LOG_JSON = True
MAX_LOG_SIZE_MB = 10
MAX_LOG_FILES = 5

# ---- Modo demo ----
OKX_DEMO = True

# ============================================================
# VERIFICACIÓN DE CONFIGURACIÓN
# ============================================================
if __name__ == "__main__":
    required = ['SYMBOLS', 'TRADE_NOTIONAL', 'LEVERAGE',
                'TP_MULT', 'SL_MULT', 'ATR_PERIOD',
                'DEFAULT_SPEED_LEVEL', 'FILTERS',
                'MAX_REPAIR_ATTEMPTS', 'BACKOFF_BASE', 'SYNC_TIME_ENABLED',
                'BACKTEST_DAYS', 'LOG_DIR']
    for var in required:
        assert var in globals(), f"❌ Falta: {var}"
        print(f"✅ {var}")
    print("✅ Configuración correcta")
