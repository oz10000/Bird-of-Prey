# models.py
# Versión 3.0 – 2026-06-24

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Signal:
    symbol: str
    direction: str          # "Long" o "Short"
    timestamp: datetime
    entry_price: float
    target_price: float
    stop_loss: float
    confidence: float
    speed_score: float
    speed_level: str
    notional: float

@dataclass
class Position:
    symbol: str
    side: str               # "long" o "short"
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: float
    repair_attempts: int = 0
    trailing_activation_price: Optional[float] = None   # Precio para activar trailing

@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    price: float
    size: float
    status: str
    filled_size: float
    avg_price: float

@dataclass
class Balance:
    total: float
    free: float
    frozen: float

@dataclass
class ProtectionStatus:
    tp_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    trailing_order_id: Optional[str] = None
    trailing_activation: Optional[float] = None
    virtual_trailing: Optional[float] = None

@dataclass
class MarketData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
