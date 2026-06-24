# main.py
# ============================================================
# PUNTAL PRINCIPAL DEL BOT – VERSIÓN COMPLETA
# Basada en Bot-Privado-verifyed-and-certifyed-, adaptada para Bird-of-Prey
# ============================================================

import os
import sys
import time
import json
import fcntl
import traceback
import numpy as np
from datetime import datetime, timedelta
from enum import Enum

# ============================================================
# IMPORTACIONES DESDE MÓDULOS PROPIOS
# ============================================================
from config import *
from telemetry import telemetry
from exchange import Exchange
from signals import (
    fetch_okx_candles,
    fetch_historical,
    calc_pidelta_score,
    generate_signal,
    check_filters,
    calculate_atr,         # 🔥 CORREGIDO: importación explícita
    calculate_ker,
    calculate_vwap_zscore
)
from strategy import get_best_signal
from monitor import monitor_position
from repair import repair_protections
from utils import acquire_lock, release_lock, validate_config, is_trading_time, health_check
from models import Position

# ============================================================
# PERSISTENCIA DE ESTADO
# ============================================================

STATE_FILE = 'state.json'

def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'trades': [],
            'stats': {'total_trades': 0, 'winrate': 0.0, 'profit_factor': 0.0,
                      'sharpe': 0.0, 'drawdown': 0.0, 'expectancy': 0.0},
            'daily_pnl': {},
            'weekly_pnl': {},
            'speed_levels': {},
            'positions': {},
            'cooldown_until': None,
            'last_run': None
        }

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)

def update_stats(state, new_trade):
    state['trades'].append(new_trade)
    total = len(state['trades'])
    wins = [t for t in state['trades'] if t['pnl'] > 0]
    losses = [t for t in state['trades'] if t['pnl'] <= 0]
    winrate = len(wins) / total if total > 0 else 0
    sum_wins = sum([t['pnl'] for t in wins]) if wins else 0
    sum_losses = abs(sum([t['pnl'] for t in losses])) if losses else 1e-6
    profit_factor = sum_wins / sum_losses if sum_losses > 0 else 0
    avg_win = sum_wins / len(wins) if wins else 0
    avg_loss = sum_losses / len(losses) if losses else 0
    expectancy = (winrate * avg_win) - ((1 - winrate) * avg_loss)
    equity = np.cumsum([t['pnl'] for t in state['trades']])
    drawdown = max(0, np.max(np.maximum.accumulate(equity) - equity)) if len(equity) > 0 else 0
    sharpe = np.mean(equity) / (np.std(equity) + 1e-6) if len(equity) > 1 else 0
    state['stats'] = {
        'total_trades': total,
        'winrate': winrate,
        'profit_factor': profit_factor,
        'sharpe': sharpe,
        'drawdown': drawdown,
        'expectancy': expectancy
    }
    return state

# ============================================================
# CONTROL DE RIESGO
# ============================================================

def risk_check(state, equity):
    """Verifica límites de pérdida diaria, semanal y cooldown."""
    today = datetime.utcnow().date().isoformat()
    daily_pnl = state['daily_pnl'].get(today, 0.0)
    daily_loss_pct = abs(daily_pnl) / equity * 100 if equity > 0 else 0
    if daily_loss_pct > MAX_DAILY_LOSS_PERCENT:
        telemetry.log_warning("risk", "Límite de pérdida diaria superado", {'daily_loss': daily_loss_pct})
        return False

    week_start = (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).date().isoformat()
    weekly_pnl = sum([v for k, v in state['daily_pnl'].items() if k >= week_start])
    weekly_loss_pct = abs(weekly_pnl) / equity * 100 if equity > 0 else 0
    if weekly_loss_pct > MAX_WEEKLY_LOSS_PERCENT:
        telemetry.log_warning("risk", "Límite de pérdida semanal superado", {'weekly_loss': weekly_loss_pct})
        return False

    if state.get('cooldown_until'):
        cooldown_until = datetime.fromisoformat(state['cooldown_until'])
        if datetime.utcnow() < cooldown_until:
            telemetry.log_warning("risk", "Cooldown activo", {'hasta': state['cooldown_until']})
            return False

    # Health check
    health = health_check()
    if not health.get('ok', False):
        telemetry.log_warning("risk", "Health check fallido", health)
        return False

    return True

# ============================================================
# BACKTESTING PARA AUTOSPEED
# ============================================================

def run_backtest(symbol, direction, speed_level, days=90):
    """Ejecuta backtest para un símbolo, dirección y nivel de velocidad."""
    df = fetch_historical(symbol, days=days)
    if df.empty:
        return None

    trades = []
    for i in range(30, len(df)):
        window = df.iloc[max(0, i-50):i+1]
        raw_score, senal = calc_pidelta_score(window)
        if senal == 0:
            continue
        if direction == 'Long' and senal != 1:
            continue
        if direction == 'Short' and senal != -1:
            continue

        if not check_filters(df, i, direction, symbol):
            continue

        roc_val = (df['c'].iloc[i] / df['c'].iloc[i-1] - 1) * 100 if i > 0 else 0
        raw_th = speed_level['raw_min']
        roc_th = speed_level['roc_min']
        if direction == 'Long':
            if not (abs(raw_score) > raw_th and roc_val > roc_th):
                continue
        else:
            if not (abs(raw_score) > raw_th and roc_val < -roc_th):
                continue

        # Anti-chase
        high, low, close = df['h'].iloc[i], df['l'].iloc[i], df['c'].iloc[i]
        if high - low <= 0:
            continue
        pos = (close - low) / (high - low)
        if direction == 'Long' and pos > 0.70:
            continue
        if direction == 'Short' and pos < 0.30:
            continue

        entry = close
        atr = calculate_atr(df, period=14).iloc[i]  # 🔥 CORREGIDO: calculate_atr ahora está importado
        if direction == 'Long':
            tp = entry + atr * TP_MULT
            sl = entry - atr * SL_MULT
        else:
            tp = entry - atr * TP_MULT
            sl = entry + atr * SL_MULT

        # Simular evolución (máximo 30 velas)
        exit_price = entry
        be_activated = False
        be_price = entry * (1 + 0.0005) if direction == 'Long' else entry * (1 - 0.0005)
        for j in range(i+1, min(i+30, len(df))):
            if direction == 'Long':
                if df['h'].iloc[j] >= tp:
                    exit_price = tp
                    break
                if not be_activated and df['h'].iloc[j] >= entry + (tp - entry) * 0.30:
                    be_activated = True
                    sl = entry * (1 + 0.0005)
                if df['l'].iloc[j] <= sl:
                    exit_price = sl
                    break
            else:
                if df['l'].iloc[j] <= tp:
                    exit_price = tp
                    break
                if not be_activated and df['l'].iloc[j] <= entry - (entry - tp) * 0.30:
                    be_activated = True
                    sl = entry * (1 - 0.0005)
                if df['h'].iloc[j] >= sl:
                    exit_price = sl
                    break

        pnl = (exit_price - entry) / entry if direction == 'Long' else (entry - exit_price) / entry
        pnl -= BACKTEST_SLIPPAGE + BACKTEST_FEE_TAKER
        trades.append({'pnl': pnl, 'result': 'TP' if (direction=='Long' and exit_price>=tp) or (direction=='Short' and exit_price<=tp) else 'BE' if be_activated else 'SL'})

    if not trades:
        return None

    total = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    winrate = len(wins) / total if total > 0 else 0
    sum_wins = sum([t['pnl'] for t in wins]) if wins else 0
    sum_losses = abs(sum([t['pnl'] for t in losses])) if losses else 1e-6
    pf = sum_wins / sum_losses if sum_losses > 0 else 0
    expectancy = (sum_wins + sum([t['pnl'] for t in losses])) / total if total > 0 else 0
    return {'total_trades': total, 'winrate': winrate, 'profit_factor': pf, 'expectancy': expectancy}

def select_speed_level(symbol, direction):
    """Selecciona el nivel de velocidad óptimo basado en backtest."""
    best_level = None
    best_score = -float('inf')
    for level in SPEED_LEVELS:
        metrics = run_backtest(symbol, direction, level, days=BACKTEST_DAYS)
        if metrics is None:
            continue
        score = metrics['winrate'] * metrics['profit_factor']
        if score > best_score:
            best_score = score
            best_level = level
    if best_level is None:
        best_level = DEFAULT_SPEED_LEVEL
    telemetry.log_info("autospeed", f"Nivel seleccionado para {symbol} {direction}: N{best_level['nivel']}", {'score': best_score})
    return best_level

# ============================================================
# CLASE BOT – MÁQUINA DE ESTADOS
# ============================================================

class BotState(Enum):
    INIT = 1
    LOAD_CONFIG = 2
    CONNECT_OKX = 3
    SYNC_EXCHANGE = 4
    SELECT_SPEED = 5
    SEARCH_SIGNAL = 6
    VERIFY_POSITION = 7
    OPEN_POSITION = 8
    CREATE_PROTECTIONS = 9
    WAIT_NEXT_CYCLE = 10
    ERROR_RECOVERY = 11
    SHUTDOWN = 12

class Bot:
    def __init__(self, api_key, secret_key, passphrase, demo=True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.demo = demo
        self.state = BotState.INIT
        self.exchange = None
        self.position = None
        self.signal = None
        self.error_count = 0
        self.max_errors = MAX_CONSECUTIVE_ERRORS
        self.running = True
        self.cycle_interval = 60
        self.repair_failures = 0
        self.state_data = load_state()
        telemetry.log_info("main", "Bot inicializado")

    def run(self):
        while self.running:
            try:
                self._step()
                if self.state == BotState.SHUTDOWN:
                    break
                time.sleep(self.cycle_interval)
            except KeyboardInterrupt:
                telemetry.log_info("main", "Interrupción del usuario")
                break
            except Exception as e:
                telemetry.log_error("main", f"Error inesperado en bucle: {e}", {'traceback': traceback.format_exc()})
                self.state = BotState.ERROR_RECOVERY

    def _step(self):
        telemetry.log_debug("main", f"Estado actual: {self.state.name}")
        if self.state == BotState.INIT:
            self._init()
        elif self.state == BotState.LOAD_CONFIG:
            self._load_config()
        elif self.state == BotState.CONNECT_OKX:
            self._connect_okx()
        elif self.state == BotState.SYNC_EXCHANGE:
            self._sync_exchange()
        elif self.state == BotState.SELECT_SPEED:
            self._select_speed()
        elif self.state == BotState.SEARCH_SIGNAL:
            self._search_signal()
        elif self.state == BotState.VERIFY_POSITION:
            self._verify_position()
        elif self.state == BotState.OPEN_POSITION:
            self._open_position()
        elif self.state == BotState.CREATE_PROTECTIONS:
            self._create_protections()
        elif self.state == BotState.WAIT_NEXT_CYCLE:
            self._wait_next_cycle()
        elif self.state == BotState.ERROR_RECOVERY:
            self._error_recovery()
        elif self.state == BotState.SHUTDOWN:
            self._shutdown()

    # ============================================================
    # MÉTODOS DE ESTADO
    # ============================================================

    def _init(self):
        telemetry.log_info("main", "Inicializando...")
        self.state = BotState.LOAD_CONFIG

    def _load_config(self):
        telemetry.log_info("main", "Cargando configuración...")
        if validate_config(globals()):
            self.state = BotState.CONNECT_OKX
        else:
            self.state = BotState.ERROR_RECOVERY

    def _connect_okx(self):
        telemetry.log_info("main", "Conectando a OKX...")
        self.exchange = Exchange(self.api_key, self.secret_key, self.passphrase, self.demo)
        if self.exchange.connect():
            self.error_count = 0
            self.state = BotState.SYNC_EXCHANGE
        else:
            self.error_count += 1
            if self.error_count >= self.max_errors:
                self.state = BotState.SHUTDOWN
            else:
                self.state = BotState.ERROR_RECOVERY

    def _sync_exchange(self):
        telemetry.log_info("main", "Sincronizando estado...")
        positions = self.exchange.get_positions()
        if positions.get('ok') and positions.get('data'):
            pos_data = positions['data'][0]
            if self.position is None:
                self.position = Position(
                    symbol=pos_data['instId'].replace('-USDT-SWAP', ''),
                    side=pos_data['posSide'],
                    size=float(pos_data['pos']),
                    entry_price=float(pos_data['avgPx']),
                    mark_price=float(pos_data['markPx']),
                    unrealized_pnl=float(pos_data['upl']),
                    leverage=float(pos_data['lever']),
                    repair_attempts=0
                )
            else:
                self.position.mark_price = float(pos_data['markPx'])
                self.position.unrealized_pnl = float(pos_data['upl'])
            telemetry.log_info("main", f"Posición activa: {self.position.symbol} {self.position.side} | PnL: {self.position.unrealized_pnl:.2f}")
            self.state = BotState.VERIFY_POSITION
        else:
            self.position = None
            self.repair_failures = 0
            self.state = BotState.SELECT_SPEED

    def _select_speed(self):
        telemetry.log_info("main", "Seleccionando niveles de velocidad (AutoSpeed)...")
        if 'speed_levels' not in self.state_data or not self.state_data['speed_levels']:
            speed_levels = {}
            for symbol in SYMBOLS:
                speed_levels[symbol] = {}
                for direction in ['Long', 'Short']:
                    level = select_speed_level(symbol, direction)
                    speed_levels[symbol][direction] = level
            self.state_data['speed_levels'] = speed_levels
            save_state(self.state_data)
        self.state = BotState.SEARCH_SIGNAL

    def _search_signal(self):
        telemetry.log_info("main", "Buscando señal...")
        if not is_trading_time():
            telemetry.log_info("main", "Fuera de horario de trading, esperando")
            self.state = BotState.WAIT_NEXT_CYCLE
            return

        if len([p for p in self.state_data['positions'].values() if p.get('entry')]) >= MAX_OPEN_POSITIONS:
            telemetry.log_warning("main", "Límite de posiciones abiertas alcanzado")
            self.state = BotState.WAIT_NEXT_CYCLE
            return

        signal = get_best_signal()
        if signal:
            self.signal = signal
            telemetry.log_info("main", f"Señal encontrada: {signal.direction} {signal.symbol} (confianza {signal.confidence:.2f})")
            self.state = BotState.OPEN_POSITION
        else:
            self.signal = None
            telemetry.log_info("main", "No se encontró señal")
            self.state = BotState.WAIT_NEXT_CYCLE

    def _verify_position(self):
        telemetry.log_info("main", "Verificando posición activa...")
        if self.position:
            monitor_result = monitor_position(self.exchange, self.position)
            telemetry.log_info("main", "Monitoreo completado", monitor_result)
            if monitor_result.get('repair'):
                telemetry.log_info("main", "Reparación ejecutada")
            if monitor_result.get('repair') is False and self.position.repair_attempts > 0:
                self.repair_failures += 1
                if self.repair_failures >= MAX_REPAIR_ATTEMPTS:
                    telemetry.log_error("main", "Demasiados fallos de reparación, apagando")
                    self.state = BotState.SHUTDOWN
                    return
            self.state = BotState.WAIT_NEXT_CYCLE
        else:
            self.state = BotState.SEARCH_SIGNAL

    def _open_position(self):
        telemetry.log_info("main", f"Abriendo posición: {self.signal.symbol} {self.signal.direction}")
        size = self.signal.notional / self.signal.entry_price
        side = "buy" if self.signal.direction == "Long" else "sell"
        order = self.exchange.place_market_order(self.signal.symbol, side, size)
        if order.get('ok'):
            telemetry.log_info("main", "Orden ejecutada", order)
            self.state_data['positions'][self.signal.symbol] = {
                'entry': self.signal.entry_price,
                'size': size,
                'direction': self.signal.direction.lower(),
                'timestamp': datetime.utcnow().isoformat()
            }
            save_state(self.state_data)
            time.sleep(2)
            self.state = BotState.SYNC_EXCHANGE
        else:
            telemetry.log_error("main", "Fallo al abrir posición", order)
            self.error_count += 1
            if self.error_count >= self.max_errors:
                self.state = BotState.SHUTDOWN
            else:
                self.state = BotState.ERROR_RECOVERY

    def _create_protections(self):
        telemetry.log_info("main", "Creando protecciones...")
        if self.position:
            repair_result = repair_protections(self.exchange, self.position)
            telemetry.log_info("main", "Protecciones creadas/verificadas", repair_result)
        self.state = BotState.WAIT_NEXT_CYCLE

    def _wait_next_cycle(self):
        telemetry.log_info("main", "Esperando siguiente ciclo...")
        self.error_count = 0
        self.state = BotState.SEARCH_SIGNAL

    def _error_recovery(self):
        wait_time = RECONNECT_BACKOFF * (2 ** self.error_count)
        telemetry.log_warning("main", f"Recuperando error, esperando {wait_time}s (intento {self.error_count})")
        time.sleep(wait_time)
        self.state = BotState.CONNECT_OKX

    def _shutdown(self):
        telemetry.log_info("main", "Apagando bot...")
        self.running = False
        self.state = BotState.SHUTDOWN

# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    # Leer credenciales de variables de entorno
    api_key = os.environ.get('OKX_API_KEY')
    secret = os.environ.get('OKX_SECRET_KEY')
    passphrase = os.environ.get('OKX_PASSPHRASE')
    demo = os.environ.get('OKX_DEMO', 'true').lower() == 'true'

    if not api_key or not secret or not passphrase:
        telemetry.log_error("main", "Faltan credenciales de OKX en variables de entorno")
        sys.exit(1)

    # Lock para evitar ejecuciones simultáneas
    if not acquire_lock(LOCK_FILE, LOCK_TIMEOUT):
        telemetry.log_warning("main", "Otra instancia está ejecutándose, saliendo.")
        sys.exit(0)

    try:
        bot = Bot(api_key, secret, passphrase, demo)
        bot.run()
    except Exception as e:
        telemetry.log_error("main", f"Error crítico: {e}", {'traceback': traceback.format_exc()})
    finally:
        release_lock(LOCK_FILE)
        telemetry.log_info("main", "Fin de la ejecución")
