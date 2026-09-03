from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Customer:
    customer_id: str
    signup_date: datetime
    kyc_status: str
    home_address_id: str
    label: str = "NORMAL"
    ring_id: Optional[str] = None

@dataclass
class Device:
    device_id: str
    device_fingerprint: str
    first_seen_date: datetime

@dataclass
class Address:
    address_id: str
    lat: float
    lon: float
    address_type: str

@dataclass
class PaymentInstrument:
    instrument_id: str
    type: str
    masked_identifier: str
    issuing_bank: str
