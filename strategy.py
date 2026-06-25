# strategy.py
# ============================================================
# ESTRATEGIA – VERSIÓN CORREGIDA (acepta speed_levels_override)
# ============================================================

from typing import List, Dict, Optional
from models import Signal
from signals import fetch_okx_candles, generate_signal
from config import SYMBOLS, SPEED_LEVELS

def get_best_signal(symbols: List[str] = None, 
                    speed_levels: List[Dict] = None,
                    speed_levels_override: Dict[str, Dict] = None) -> Optional[Signal]:
    """
    Selecciona la mejor señal entre todos los símbolos y direcciones.
    - symbols: lista de símbolos a evaluar (por defecto usa SYMBOLS de config).
    - speed_levels: lista de niveles de velocidad (por defecto usa SPEED_LEVELS de config).
    - speed_levels_override: diccionario con niveles específicos por activo/dirección.
                           Si se proporciona, se usa en lugar de speed_levels para cada activo.
    """
    if symbols is None:
        symbols = SYMBOLS
    if speed_levels is None and speed_levels_override is None:
        speed_levels = SPEED_LEVELS

    best_signal = None
    best_score = -1.0

    for symbol in symbols:
        df = fetch_okx_candles(symbol, limit=150)
        if df.empty:
            continue

        # Determinar qué niveles usar para este símbolo
        if speed_levels_override and symbol in speed_levels_override:
            # Para cada dirección, usar el nivel específico del override
            for direction, level in speed_levels_override[symbol].items():
                sig = generate_signal(df, symbol, direction, level)
                if sig and sig.speed_score > best_score:
                    best_score = sig.speed_score
                    best_signal = sig
        else:
            # Usar los niveles generales (speed_levels o SPEED_LEVELS)
            levels = speed_levels if speed_levels is not None else SPEED_LEVELS
            for level in levels:
                for direction in ["Long", "Short"]:
                    sig = generate_signal(df, symbol, direction, level)
                    if sig and sig.speed_score > best_score:
                        best_score = sig.speed_score
                        best_signal = sig

    return best_signal
