# exchange.py
# Versión 3.0 – 2026-06-24

import time
import json
import hashlib
import hmac
import base64
import requests
from config import MAX_RETRIES_PER_ORDER, ORDER_TIMEOUT, SYNC_TIME_ENABLED, TRAILING_ENABLED, TRAILING_MODE, TRAILING_DISTANCE_ATR
from telemetry import telemetry

class Exchange:
    def __init__(self, api_key: str, secret_key: str, passphrase: str, demo: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.demo = demo
        self.base_url = "https://www.okx.com" if not demo else "https://www.okx.com"
        self.session = requests.Session()
        self._connected = False
        self._time_offset = 0

    def _sync_time(self) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/api/v5/public/time", timeout=5)
            data = resp.json()
            if data.get("code") == "0":
                server_ts = int(data['data'][0]['ts'])
                local_ts = int(time.time() * 1000)
                self._time_offset = server_ts - local_ts
                telemetry.log_debug("exchange", f"Offset horario: {self._time_offset} ms")
                return True
        except Exception as e:
            telemetry.log_error("exchange", f"Error en _sync_time: {e}")
        return False

    def _sign_request(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        if self._time_offset != 0:
            timestamp = str(int((time.time() * 1000) + self._time_offset))
        else:
            timestamp = str(int(time.time() * 1000))
        if body:
            body_str = json.dumps(body)
        else:
            body_str = ""
        if params:
            query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            full_path = f"{path}?{query}"
        else:
            full_path = path
        sign_str = timestamp + method + full_path + body_str
        signature = base64.b64encode(
            hmac.new(self.secret_key.encode(), sign_str.encode(), hashlib.sha256).digest()
        ).decode()
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        return headers

    def _handle_response(self, response: requests.Response) -> dict:
        try:
            data = response.json()
        except:
            return {"ok": False, "error": "Invalid JSON response"}
        if data.get("code") != "0":
            return {"ok": False, "error": data.get("msg", "Unknown error"), "raw": data}
        return {"ok": True, "data": data.get("data", [])}

    def _retry(self, func, *args, **kwargs):
        for attempt in range(MAX_RETRIES_PER_ORDER):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                telemetry.log_warning("exchange", f"Intento {attempt+1} fallido: {e}")
                time.sleep(2 ** attempt)
        return {"ok": False, "error": "Max retries exceeded"}

    def connect(self) -> bool:
        try:
            if SYNC_TIME_ENABLED:
                self._sync_time()
            resp = self.session.get(f"{self.base_url}/api/v5/public/time", timeout=ORDER_TIMEOUT)
            data = resp.json()
            if data.get("code") == "0":
                self._connected = True
                telemetry.log_info("exchange", "Conectado a OKX correctamente")
                return True
            else:
                telemetry.log_error("exchange", f"Error de conexión: {data}")
                return False
        except Exception as e:
            telemetry.log_error("exchange", f"Excepción en connect: {e}")
            return False

    def get_balance(self) -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/account/balance"
        headers = self._sign_request("GET", path)
        resp = self._retry(self.session.get, f"{self.base_url}{path}", headers=headers, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def get_positions(self, symbol: str = None) -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/account/positions"
        params = {}
        if symbol:
            params["instId"] = symbol
        headers = self._sign_request("GET", path, params=params)
        resp = self._retry(self.session.get, f"{self.base_url}{path}", headers=headers, params=params, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def get_pending_algo_orders(self, symbol: str = None) -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/trade/orders-algo-pending"
        params = {"ordType": "conditional,oco,trigger"}
        if symbol:
            params["instId"] = symbol
        headers = self._sign_request("GET", path, params=params)
        resp = self._retry(self.session.get, f"{self.base_url}{path}", headers=headers, params=params, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def place_market_order(self, symbol: str, side: str, size: float) -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/trade/order"
        body = {
            "instId": symbol,
            "tdMode": "cross",
            "side": side.lower(),
            "ordType": "market",
            "sz": str(size),
        }
        headers = self._sign_request("POST", path, body=body)
        resp = self._retry(self.session.post, f"{self.base_url}{path}", headers=headers, json=body, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def place_algo_order(self, symbol: str, side: str, trigger_price: float, order_price: float,
                         size: float, order_type: str = "conditional") -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/trade/order-algo"
        body = {
            "instId": symbol,
            "tdMode": "cross",
            "side": side.lower(),
            "ordType": order_type,
            "sz": str(size),
            "triggerPx": str(trigger_price),
            "orderPx": str(order_price),
        }
        headers = self._sign_request("POST", path, body=body)
        resp = self._retry(self.session.post, f"{self.base_url}{path}", headers=headers, json=body, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def place_trailing_order(self, symbol: str, side: str, size: float, callback_rate: float) -> dict:
        """Coloca una orden trailing stop nativa (OKX)."""
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        if not TRAILING_ENABLED or TRAILING_MODE != 'native':
            return {"ok": False, "error": "Trailing nativo deshabilitado"}
        path = "/api/v5/trade/order-algo"
        body = {
            "instId": symbol,
            "tdMode": "cross",
            "side": side.lower(),
            "ordType": "move_order_stop",
            "sz": str(size),
            "callbackRatio": str(callback_rate),  # Ej: "0.008" para 0.8% de trailing
            "triggerPx": "-1",                    # -1 indica activación inmediata
        }
        headers = self._sign_request("POST", path, body=body)
        resp = self._retry(self.session.post, f"{self.base_url}{path}", headers=headers, json=body, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def cancel_order(self, order_id: str, symbol: str) -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/trade/cancel-order"
        body = {"ordId": order_id, "instId": symbol}
        headers = self._sign_request("POST", path, body=body)
        resp = self._retry(self.session.post, f"{self.base_url}{path}", headers=headers, json=body, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def cancel_algo_order(self, algo_id: str, symbol: str) -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/trade/cancel-algos"
        body = {"algoId": algo_id, "instId": symbol}
        headers = self._sign_request("POST", path, body=body)
        resp = self._retry(self.session.post, f"{self.base_url}{path}", headers=headers, json=body, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)

    def get_order(self, order_id: str, symbol: str) -> dict:
        if not self._connected:
            return {"ok": False, "error": "No conectado"}
        path = "/api/v5/trade/order"
        params = {"ordId": order_id, "instId": symbol}
        headers = self._sign_request("GET", path, params=params)
        resp = self._retry(self.session.get, f"{self.base_url}{path}", headers=headers, params=params, timeout=ORDER_TIMEOUT)
        return self._handle_response(resp)
