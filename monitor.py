# monitor.py
# Versión 3.0 – 2026-06-24

from signals import fetch_okx_candles, calculate_atr
from repair import repair_protections
from telemetry import telemetry
from config import TRAILING_ENABLED, TRAILING_MODE, TRAILING_DISTANCE_ATR, TRAILING_ACTIVATION_PROFIT

def monitor_position(exchange, position) -> dict:
    telemetry.log_info("monitor", f"Monitoreando {position.symbol}")
    result = {
        "symbol": position.symbol,
        "side": position.side,
        "pnl_pct": 0.0,
        "repair": False,
        "trailing_updated": False
    }

    try:
        # 1. Actualizar precio de mercado
        df = fetch_okx_candles(position.symbol, limit=1)
        if not df.empty:
            mark = df['c'].iloc[-1]
            position.mark_price = mark
            pnl = (mark - position.entry_price) / position.entry_price
            if position.side == "short":
                pnl = -pnl
            result["pnl_pct"] = pnl * 100
        else:
            result["pnl_pct"] = position.unrealized_pnl

        # 2. Verificar protecciones
        pending = exchange.get_pending_algo_orders(position.symbol)
        if pending.get('ok') and not pending.get('data'):
            telemetry.log_info("monitor", "No hay protecciones, ejecutando reparación")
            repair_result = repair_protections(exchange, position)
            result["repair"] = any(repair_result.values())
            telemetry.log_info("monitor", "Reparación ejecutada", repair_result)
        else:
            telemetry.log_debug("monitor", "Protecciones existentes, no se requiere reparación")

        # 3. Trailing virtual (si está habilitado y no se usa nativo)
        if TRAILING_ENABLED and TRAILING_MODE == 'virtual':
            atr = calculate_atr(df, 14).iloc[-1] if not df.empty else 0
            activation_profit = TRAILING_ACTIVATION_PROFIT / 100.0  # convertir a fracción
            if position.side == "long":
                if position.mark_price > position.entry_price * (1 + activation_profit):
                    new_trail = position.mark_price - atr * TRAILING_DISTANCE_ATR
                    if position.trailing_activation_price is None or new_trail > position.trailing_activation_price:
                        position.trailing_activation_price = new_trail
                        result["trailing_updated"] = True
                        telemetry.log_info("monitor", f"Trailing virtual actualizado a {new_trail:.2f}")
            elif position.side == "short":
                if position.mark_price < position.entry_price * (1 - activation_profit):
                    new_trail = position.mark_price + atr * TRAILING_DISTANCE_ATR
                    if position.trailing_activation_price is None or new_trail < position.trailing_activation_price:
                        position.trailing_activation_price = new_trail
                        result["trailing_updated"] = True
                        telemetry.log_info("monitor", f"Trailing virtual actualizado a {new_trail:.2f}")

    except Exception as e:
        telemetry.log_error("monitor", f"Error en monitor_position: {e}")

    return result
