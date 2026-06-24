# config.py
# ============================================================
# CONFIGURACIÓN CENTRAL DEL BOT PiDelta – BIRD-OF-PREY
# Versión completa y corregida para garantizar importaciones
# ============================================================

# ---- Símbolos y operativa ----
SYMBOLS = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']
TRADE_NOTIONAL = 1000.0          # USDT por operación
LEVERAGE = 10                    # Apalancamiento fijo

# ---- TP, SL y Trailing ----
TP_MULT = 1.2                    # Take Profit = ATR * TP_MULT
SL_MULT = 1.5                    # Stop Loss = ATR * SL_MULT
TRAILING_ENABLED = False         # Activar/desactivar trailing stop (por defecto desactivado)
TRAILING_MODE = 'native'         # 'native' (OKX) o 'virtual'
TRAILING_DISTANCE_ATR = 0.8      # Múltiplos de ATR para trailing
TRAILING_ACTIVATION_PROFIT = 0.8 # % beneficio para activar trailing

# ---- Niveles de velocidad (AutoSpeed) ----
SPEED_LEVELS = [
    {"nivel": 1, "raw_min": 0.45, "roc_min": 0.30},
    {"nivel": 2, "raw_min": 0.40, "roc_min": 0.25},
    {"nivel": 3, "raw_min": 0.35, "roc_min": 0.20},
    {"nivel": 4, "raw_min": 0.30, "roc_min": 0.15},
    {"nivel": 5, "raw_min": 0.25, "roc_min": 0.10},
    {"nivel": 6, "raw_min": 0.20, "roc_min": 0.05},
]
DEFAULT_SPEED_LEVEL = SPEED_LEVELS[2]  # Nivel 3 por defecto

# ---- Parámetros optimizados (Walk-Forward 1 año) ----
# Estos niveles sustituyen al backtest en tiempo real
OPTIMIZED_LEVELS = {
    'BTC': {'Long': SPEED_LEVELS[1], 'Short': SPEED_LEVELS[2]},
    'ETH': {'Long': SPEED_LEVELS[0], 'Short': SPEED_LEVELS[1]},
    'SOL': {'Long': SPEED_LEVELS[3], 'Short': SPEED_LEVELS[3]},
    'ADA': {'Long': SPEED_LEVELS[3], 'Short': SPEED_LEVELS[4]},
    'XRP': {'Long': SPEED_LEVELS[3], 'Short': SPEED_LEVELS[4]},
}

# ---- Filtro horario ----
TIME_FILTER_ENABLED = True
TIME_FILTER_START = 12           # UTC (hora de inicio)
TIME_FILTER_END = 18             # UTC (hora de fin)
TIME_FILTER_WEEKDAYS = [0, 1, 2, 3, 4]  # Lunes a Viernes

# ---- Filtros por activo y dirección (optimizados en backtest) ----
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
RECONNECT_BACKOFF = 5            # Base para backoff exponencial (segundos)
BACKOFF_BASE = 5                 # Alias para compatibilidad
MAX_RETRIES_PER_ORDER = 3        # Reintentos por orden
ORDER_TIMEOUT = 15               # Timeout para llamadas API (segundos)
LOCK_FILE = '.lock'              # Archivo de bloqueo
LOCK_TIMEOUT = 10                # Timeout para adquirir el bloqueo
SYNC_TIME_ENABLED = True         # Sincronización horaria con OKX
MAX_CONSECUTIVE_ERRORS = 5       # Fallos consecutivos antes de apagar

# ---- Límites de riesgo global ----
MAX_DAILY_LOSS_PERCENT = 2.0     # Pérdida diaria máxima (% del equity)
MAX_WEEKLY_LOSS_PERCENT = 4.0    # Pérdida semanal máxima (% del equity)
MAX_OPEN_POSITIONS = 3           # Número máximo de posiciones simultáneas

# ---- Backtesting (necesario para signals.py, aunque no se use en producción) ----
BACKTEST_DAYS = 30
BACKTEST_FEE_MAKER = 0.0005
BACKTEST_FEE_TAKER = 0.0007
BACKTEST_SLIPPAGE = 0.0002       # IMPORTANTE: usado por signals.py

# ---- Logging ----
LOG_DIR = 'logs'
LOG_LEVEL = 'INFO'
LOG_CONSOLE = True
LOG_FILE = True
LOG_JSON = True
MAX_LOG_SIZE_MB = 10
MAX_LOG_FILES = 5

# ---- Modo demo / live (se lee de variable de entorno) ----
OKX_DEMO = True

# ============================================================
# VERIFICACIÓN DE CONFIGURACIÓN (autodiagnóstico)
# ============================================================
if __name__ == "__main__":
    print("="*70)
    print("🧪 VERIFICACIÓN DE CONFIGURACIÓN")
    print("="*70)

    required = [
        'SYMBOLS', 'TRADE_NOTIONAL', 'LEVERAGE',
        'TP_MULT', 'SL_MULT',
        'TRAILING_ENABLED', 'TRAILING_MODE', 'TRAILING_DISTANCE_ATR',
        'SPEED_LEVELS', 'DEFAULT_SPEED_LEVEL',
        'OPTIMIZED_LEVELS',
        'TIME_FILTER_ENABLED', 'TIME_FILTER_START', 'TIME_FILTER_END', 'TIME_FILTER_WEEKDAYS',
        'FILTERS',
        'MAX_RECONNECT_ATTEMPTS', 'RECONNECT_BACKOFF', 'BACKOFF_BASE',
        'MAX_RETRIES_PER_ORDER', 'ORDER_TIMEOUT', 'LOCK_FILE', 'LOCK_TIMEOUT',
        'SYNC_TIME_ENABLED', 'MAX_CONSECUTIVE_ERRORS',
        'MAX_DAILY_LOSS_PERCENT', 'MAX_WEEKLY_LOSS_PERCENT', 'MAX_OPEN_POSITIONS',
        'BACKTEST_DAYS', 'BACKTEST_FEE_MAKER', 'BACKTEST_FEE_TAKER', 'BACKTEST_SLIPPAGE',
        'LOG_DIR', 'LOG_LEVEL', 'LOG_CONSOLE', 'LOG_FILE', 'LOG_JSON',
        'MAX_LOG_SIZE_MB', 'MAX_LOG_FILES',
        'OKX_DEMO'
    ]

    all_ok = True
    for var in required:
        if var not in globals():
            print(f"  ❌ FALTA: {var}")
            all_ok = False
        else:
            print(f"  ✅ {var} = {globals()[var]}")

    if all_ok:
        print("\n✅ CONFIGURACIÓN COMPLETA Y CORRECTA")
    else:
        print("\n❌ FALTAN CONSTANTES – REVISAR CONFIGURACIÓN")
