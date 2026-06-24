# config.py
# ============================================================
# CONFIGURACIÓN CENTRAL DEL BOT PiDelta – BIRD-OF-PREY
# Versión completa y corregida
# ============================================================

# ---- Símbolos y operativa ----
SYMBOLS = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']
TRADE_NOTIONAL = 1000.0
LEVERAGE = 10

# ---- TP, SL y Trailing ----
TP_MULT = 1.2
SL_MULT = 1.5
TRAILING_ENABLED = False
TRAILING_MODE = 'native'
TRAILING_DISTANCE_ATR = 0.8
TRAILING_ACTIVATION_PROFIT = 0.8

# ---- Niveles de velocidad (AutoSpeed) ----
SPEED_LEVELS = [
    {"nivel": 1, "raw_min": 0.45, "roc_min": 0.30},
    {"nivel": 2, "raw_min": 0.40, "roc_min": 0.25},
    {"nivel": 3, "raw_min": 0.35, "roc_min": 0.20},
    {"nivel": 4, "raw_min": 0.30, "roc_min": 0.15},
    {"nivel": 5, "raw_min": 0.25, "roc_min": 0.10},
    {"nivel": 6, "raw_min": 0.20, "roc_min": 0.05},
]
DEFAULT_SPEED_LEVEL = SPEED_LEVELS[2]

# ---- Parámetros optimizados (Walk-Forward 1 año) ----
OPTIMIZED_LEVELS = {
    'BTC': {'Long': SPEED_LEVELS[1], 'Short': SPEED_LEVELS[2]},
    'ETH': {'Long': SPEED_LEVELS[0], 'Short': SPEED_LEVELS[1]},
    'SOL': {'Long': SPEED_LEVELS[3], 'Short': SPEED_LEVELS[3]},
    'ADA': {'Long': SPEED_LEVELS[3], 'Short': SPEED_LEVELS[4]},
    'XRP': {'Long': SPEED_LEVELS[3], 'Short': SPEED_LEVELS[4]},
}

# ---- Filtro horario ----
TIME_FILTER_ENABLED = True
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

# ---- Recuperación, reintentos y timeouts ----
MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_BACKOFF = 5
BACKOFF_BASE = 5
MAX_RETRIES_PER_ORDER = 3
ORDER_TIMEOUT = 15
LOCK_FILE = '.lock'
LOCK_TIMEOUT = 10
SYNC_TIME_ENABLED = True
MAX_CONSECUTIVE_ERRORS = 5

# ---- Reparación de protecciones ----
MAX_REPAIR_ATTEMPTS = 3          # <--- AÑADIDA

# ---- Límites de riesgo ----
MAX_DAILY_LOSS_PERCENT = 2.0
MAX_WEEKLY_LOSS_PERCENT = 4.0
MAX_OPEN_POSITIONS = 3

# ---- Backtesting (para signals.py) ----
BACKTEST_DAYS = 30
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
# VERIFICACIÓN AUTOMÁTICA (opcional)
# ============================================================
if __name__ == "__main__":
    required = [
        'SYMBOLS', 'TRADE_NOTIONAL', 'LEVERAGE',
        'TP_MULT', 'SL_MULT',
        'TRAILING_ENABLED', 'TRAILING_MODE',
        'SPEED_LEVELS', 'DEFAULT_SPEED_LEVEL',
        'OPTIMIZED_LEVELS',
        'TIME_FILTER_ENABLED', 'TIME_FILTER_START', 'TIME_FILTER_END', 'TIME_FILTER_WEEKDAYS',
        'FILTERS',
        'MAX_RECONNECT_ATTEMPTS', 'RECONNECT_BACKOFF', 'BACKOFF_BASE',
        'MAX_RETRIES_PER_ORDER', 'ORDER_TIMEOUT', 'LOCK_FILE', 'LOCK_TIMEOUT',
        'SYNC_TIME_ENABLED', 'MAX_CONSECUTIVE_ERRORS',
        'MAX_REPAIR_ATTEMPTS',   # <--- INCLUIDA EN LA VERIFICACIÓN
        'MAX_DAILY_LOSS_PERCENT', 'MAX_WEEKLY_LOSS_PERCENT', 'MAX_OPEN_POSITIONS',
        'BACKTEST_DAYS', 'BACKTEST_FEE_MAKER', 'BACKTEST_FEE_TAKER', 'BACKTEST_SLIPPAGE',
        'LOG_DIR', 'LOG_LEVEL', 'LOG_CONSOLE', 'LOG_FILE', 'LOG_JSON',
        'MAX_LOG_SIZE_MB', 'MAX_LOG_FILES', 'OKX_DEMO'
    ]
    for var in required:
        assert var in globals(), f"❌ Falta: {var}"
        print(f"✅ {var}")
    print("✅ Configuración completa")
