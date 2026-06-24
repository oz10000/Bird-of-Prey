# repair.py
# Versión 3.0 – 2026-06-24

import traceback
from config import TP_MULT, SL_MULT, MAX_REPAIR_ATTEMPTS, TRAILING_ENABLED, TRAILING_MODE, TRAILING_DISTANCE_ATR
from telemetry import telemetry

def repair_protections(exchange, position) -> dict:
    telemetry.log_info("repair", f"Iniciando reparación para {position.symbol} (intento {position.repair_attempts+1}/{MAX_REPAIR_ATTEMPTS})")
    result = {"tp": False, "sl": False, "trail": False, "error": None}

    if position.repair_attempts >= MAX_REPAIR_ATTEMPTS:
        msg = f"Límite de intentos de reparación alcanzado ({MAX_REPAIR_ATTEMPTS}) para {position.symbol}"
        telemetry.log_error("repair", msg)
        result["error"] = msg
        return result

    try:
        # 1. Consultar órdenes pendientes
        telemetry.log_debug("repair", f"Consultando órdenes pendientes para {position.symbol}")
        pending = exchange.get_pending_algo_orders(position.symbol)
        if not pending.get('ok'):
            telemetry.log_error("repair", "No se pudieron obtener órdenes pendientes", pending)
            result["error"] = pending.get("error", "Error desconocido")
            return result

        orders = pending.get('data', [])
        telemetry.log_debug("repair", f"Órdenes pendientes encontradas: {len(orders)}")

        # 2. Determinar qué protecciones existen
        has_tp = any(o.get('ordType') == 'conditional' and o.get('side') != position.side for o in orders)
        has_sl = any(o.get('ordType') == 'conditional' and o.get('side') == position.side for o in orders)
        has_trail = any(o.get('ordType') in ['move_order_stop', 'trigger'] for o in orders)

        telemetry.log_debug("repair", f"Estado actual: TP={has_tp}, SL={has_sl}, Trail={has_trail}")

        # 3. Crear TP si no existe
        if not has_tp:
            tp_price = position.entry_price * (1 + TP_MULT * (position.mark_price / position.entry_price - 1))
            side = "sell" if position.side == "long" else "buy"
            telemetry.log_info("repair", f"Creando TP para {position.symbol} a {tp_price:.2f}")
            tp_resp = exchange.place_algo_order(position.symbol, side, tp_price, tp_price, position.size, "conditional")
            if tp_resp.get('ok'):
                result['tp'] = True
                telemetry.log_info("repair", "TP creado exitosamente", {"order": tp_resp.get('data')})
            else:
                telemetry.log_error("repair", "Fallo al crear TP", tp_resp)
                result["error"] = tp_resp.get("error", "Error creando TP")

        # 4. Crear SL si no existe
        if not has_sl:
            sl_price = position.entry_price * (1 - SL_MULT * (position.entry_price / position.mark_price - 1))
            side = "sell" if position.side == "long" else "buy"
            telemetry.log_info("repair", f"Creando SL para {position.symbol} a {sl_price:.2f}")
            sl_resp = exchange.place_algo_order(position.symbol, side, sl_price, sl_price, position.size, "conditional")
            if sl_resp.get('ok'):
                result['sl'] = True
                telemetry.log_info("repair", "SL creado exitosamente", {"order": sl_resp.get('data')})
            else:
                telemetry.log_error("repair", "Fallo al crear SL", sl_resp)
                if not result["error"]:
                    result["error"] = sl_resp.get("error", "Error creando SL")

        # 5. Trailing stop (solo si está habilitado y es nativo)
        if TRAILING_ENABLED and TRAILING_MODE == 'native' and not has_trail:
            # Solo para posiciones long (se puede extender a short)
            if position.side == "long":
                callback_rate = TRAILING_DISTANCE_ATR * 0.01  # convertir a porcentaje
                telemetry.log_info("repair", f"Creando trailing stop nativo para {position.symbol} con callback {callback_rate*100:.2f}%")
                trail_resp = exchange.place_trailing_order(position.symbol, "sell", position.size, callback_rate)
                if trail_resp.get('ok'):
                    result['trail'] = True
                    telemetry.log_info("repair", "Trailing stop nativo creado", {"order": trail_resp.get('data')})
                else:
                    telemetry.log_error("repair", "Fallo al crear trailing nativo", trail_resp)
                    if not result["error"]:
                        result["error"] = trail_resp.get("error", "Error creando trailing")

        # 6. Incrementar contador
        position.repair_attempts += 1

        if any([result['tp'], result['sl'], result['trail']]):
            telemetry.log_info("repair", "Reparación completada con éxito parcial", result)
        else:
            telemetry.log_warning("repair", "No se creó ninguna protección", result)

    except Exception as e:
        telemetry.log_error("repair", f"Excepción en repair_protections: {e}", {"traceback": traceback.format_exc()})
        result["error"] = str(e)

    return result
