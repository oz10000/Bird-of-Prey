# strategy.py
# Versión 3.0 – 2026-06-24

from typing import List, Dict, Optional
from models import Signal
from signals import fetch_okx_candles, generate_signal
from config import SYMBOLS, SPEED_LEVELS

def get_best_signal(symbols: List[str] = None, speed_levels: List[Dict] = None) -> Optional[Signal]:
    if symbols is None:
        symbols = SYMBOLS
    if speed_levels is None:
        speed_levels = SPEED_LEVELS

    best_signal = None
    best_score = -1.0

    for symbol in symbols:
        df = fetch_okx_candles(symbol, limit=150)
        if df.empty:
            continue
        for level in speed_levels:
            for direction in ["Long", "Short"]:
                sig = generate_signal(df, symbol, direction, level)
                if sig and sig.speed_score > best_score:
                    best_score = sig.speed_score
                    best_signal = sig
    return best_signal
