# signals.py
# ============================================================
# SEÑALES – VERSIÓN CORREGIDA Y OPTIMIZADA
# ============================================================

import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from config import TP_MULT, SL_MULT, TRADE_NOTIONAL, FILTERS, BACKTEST_SLIPPAGE
from models import Signal
from telemetry import telemetry

# ============================================================
# 1. INDICADORES
# ============================================================

def calculate_ker(series: pd.Series, period: int = 10) -> pd.Series:
    change = series.diff()
    net_change = series.diff(period)
    abs_change = change.abs().rolling(period).sum()
    ker = net_change / (abs_change + 1e-6)
    ker = ker.clip(-1, 1)
    return (ker + 1) / 2  # escalar a [0,1]

def calculate_vwap_zscore(df: pd.DataFrame, period: int = 20) -> pd.Series:
    vwap = (df['c'] * df['vol']).rolling(period).sum() / (df['vol'].rolling(period).sum() + 1e-6)
    std = df['c'].rolling(period).std()
    zscore = (df['c'] - vwap) / (std + 1e-6)
    return zscore.fillna(0)

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df['h'], df['l'], df['c']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr.fillna(0)

def calculate_roc(series: pd.Series, period: int = 10) -> pd.Series:
    roc = (series / series.shift(period) - 1) * 100
    return roc.fillna(0)

def calculate_macro(df: pd.DataFrame) -> float:
    atr = calculate_atr(df, 14).iloc[-1]
    close = df['c'].iloc[-1]
    vol_ratio = atr / (close + 1e-6)
    trend = calculate_ker(df['c'], 20).iloc[-1]
    macro = 0.5 * trend + 0.5 * (1 - min(vol_ratio, 1))
    return max(0, min(1, macro))

# ============================================================
# 2. DESCARGA DE DATOS (OKX)
# ============================================================

def fetch_okx_candles(symbol: str, bar: str = "5m", limit: int = 150) -> pd.DataFrame:
    inst_id = f"{symbol}-USDT-SWAP"
    url = f"https://www.okx.com/api/v5/market/candles?instId={inst_id}&bar={bar}&limit={min(limit, 300)}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get('code') != '0':
            telemetry.log_warning("signals", f"Error descargando {symbol}: {data}")
            return pd.DataFrame()
        raw = data['data']
        if not raw:
            return pd.DataFrame()
        df = pd.DataFrame(raw, columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'ccy', 'volccy', 'confirm'])
        df['ts'] = pd.to_datetime(df['ts'].astype(int), unit='ms')
        for col in ['o', 'h', 'l', 'c', 'vol']:
            df[col] = df[col].astype(float)
        return df.sort_values('ts').reset_index(drop=True)
    except Exception as e:
        telemetry.log_error("signals", f"Excepción en fetch_okx_candles: {e}", {'symbol': symbol})
        return pd.DataFrame()

def fetch_historical(symbol: str, days: int = 90) -> pd.DataFrame:
    """Descarga velas históricas con paginación."""
    base_url = "https://www.okx.com/api/v5/market/history-candles"
    inst_id = f"{symbol}-USDT-SWAP"
    all_candles = []
    end_ts = int(datetime.now().timestamp() * 1000)
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    after = end_ts
    while after > start_ts:
        params = {'instId': inst_id, 'bar': '5m', 'limit': 100, 'after': after}
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            data = resp.json()
            if data.get('code') != '0':
                break
            candles = data.get('data', [])
            if not candles:
                break
            all_candles.extend(candles)
            after = int(candles[-1][0])
            time.sleep(0.1)
        except Exception as e:
            telemetry.log_error("signals", f"Error en fetch_historical: {e}", {'symbol': symbol})
            break
    if not all_candles:
        return pd.DataFrame()
    df = pd.DataFrame(all_candles, columns=['ts', 'o', 'h', 'l', 'c', 'vol', 't1', 't2', 't3'])
    df['ts'] = pd.to_datetime(df['ts'].astype(int), unit='ms')
    for col in ['o', 'h', 'l', 'c', 'vol']:
        df[col] = df[col].astype(float)
    return df.sort_values('ts').reset_index(drop=True)

# ============================================================
# 3. CÁLCULO DEL SCORE PiDelta
# ============================================================

def calc_pidelta_score(df: pd.DataFrame) -> tuple:
    """Devuelve (raw_score, senal) donde senal = 1 (Long), -1 (Short) o 0."""
    if len(df) < 50:
        return 0, 0
    close = df['c']
    ema20 = close.ewm(span=20, adjust=False).mean()
    slope = ema20.diff(5).iloc[-1]
    atr = calculate_atr(df, period=14).iloc[-1]
    micro = slope / (atr + 1e-6)
    ker = calculate_ker(close, period=10).iloc[-1]
    macro = calculate_macro(df)
    raw_score = np.tanh(micro * ker * macro)
    senal = 1 if raw_score > 0.20 else (-1 if raw_score < -0.20 else 0)
    return raw_score, senal

# ============================================================
# 4. VERIFICACIÓN DE FILTROS POR ACTIVO (CORREGIDO)
# ============================================================

def check_filters(df: pd.DataFrame, idx: int, direccion: str, symbol: str) -> bool:
    if idx < 30:
        return False
    cfg = FILTERS.get(symbol, {}).get(direccion, {})
    if not cfg:
        return True

    # 🔥 CORRECCIÓN: calcular atr antes de usarlo
    atr = calculate_atr(df, period=14).iloc[idx]
    ker = calculate_ker(df['c'], 10).iloc[idx]
    zscore = calculate_vwap_zscore(df, 20).iloc[idx]
    atr_pct = (atr / df['c'].iloc[idx]) * 100 if df['c'].iloc[idx] > 0 else 0
    vol_rel = df['vol'].iloc[idx] / (df['vol'].rolling(20).mean().iloc[idx] + 1e-6)
    ema20 = df['c'].ewm(span=20).mean().iloc[idx]
    ema_pend = (df['c'].iloc[idx] / ema20 - 1) if ema20 > 0 else 0

    if direccion == 'Long':
        if 'ker_min' in cfg and ker < cfg['ker_min']:
            return False
        if 'zscore_min' in cfg and zscore < cfg['zscore_min']:
            return False
        if 'atr_percent_min' in cfg and atr_pct < cfg['atr_percent_min']:
            return False
        if 'vol_rel_min' in cfg and vol_rel < cfg['vol_rel_min']:
            return False
        if 'ema_pend_min' in cfg and ema_pend < cfg['ema_pend_min']:
            return False
    else:  # Short
        if 'ker_min' in cfg and ker < cfg['ker_min']:
            return False
        if 'zscore_max' in cfg and zscore > cfg['zscore_max']:
            return False
        if 'vol_rel_min' in cfg and vol_rel < cfg['vol_rel_min']:
            return False
        # Nota: atr_percent_min se puede aplicar a ambas direcciones, pero no está en Short por defecto
    return True

# ============================================================
# 5. GENERACIÓN DE SEÑAL (CORREGIDO)
# ============================================================

def generate_signal(df: pd.DataFrame, symbol: str, direction: str, speed_level: dict) -> Optional[Signal]:
    if df.empty or len(df) < 30:
        return None

    last = df.iloc[-1]
    raw_score, senal = calc_pidelta_score(df)
    if senal == 0:
        return None
    if direction == 'Long' and senal != 1:
        return None
    if direction == 'Short' and senal != -1:
        return None

    if not check_filters(df, len(df)-1, direction, symbol):
        return None

    raw_th = speed_level['raw_min']
    roc_th = speed_level['roc_min']
    roc_val = calculate_roc(df['c'], 1).iloc[-1]
    if direction == 'Long':
        if not (abs(raw_score) > raw_th and roc_val > roc_th):
            return None
    else:
        if not (abs(raw_score) > raw_th and roc_val < -roc_th):
            return None

    # Anti-Chase
    high, low, close = df['h'].iloc[-1], df['l'].iloc[-1], df['c'].iloc[-1]
    if high - low <= 0:
        return None
    pos = (close - low) / (high - low)
    if direction == 'Long' and pos > 0.70:
        return None
    if direction == 'Short' and pos < 0.30:
        return None

    atr = calculate_atr(df, 14).iloc[-1]
    entry = close
    if direction == 'Long':
        tp = entry + atr * TP_MULT
        sl = entry - atr * SL_MULT
    else:
        tp = entry - atr * TP_MULT
        sl = entry + atr * SL_MULT

    confidence = min(1.0, abs(raw_score) * 1.2 + 0.1)
    speed_score = abs(raw_score) * (1 + abs(roc_val) / 10)

    # 🔥 CORRECCIÓN: usar 'nivel' en lugar de 'name'
    return Signal(
        symbol=symbol,
        direction=direction,
        timestamp=datetime.utcnow(),
        entry_price=entry,
        target_price=tp,
        stop_loss=sl,
        confidence=confidence,
        speed_score=speed_score,
        speed_level=f"N{speed_level['nivel']}",
        notional=TRADE_NOTIONAL
    )
