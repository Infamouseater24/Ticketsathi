from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Any

@dataclass
class PaymentRequest:
    amount: float
    order_id: str
    description: str
    callback_url: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_id: Optional[str] = None

@dataclass
class PaymentResponse:
    is_form_post: bool
    target_url: str
    form_fields: Dict[str, str]
    transaction_id: str = ""
    # For debugging/logging
    raw_response: Optional[Dict[str, Any]] = None

@dataclass
class VerifyRequest:
    encoded_params: Dict[str, Any]
    expected_amount: float
    expected_order_id: str

@dataclass
class VerifyResponse:
    success: bool
    transaction_id: str
    amount: float
    status: str
    gateway_ref: str = ""
    raw_response: Optional[Dict[str, Any]] = None

class PaymentProvider(ABC):
    @abstractmethod
    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        pass

    @abstractmethod
    def verify_payment(self, request: VerifyRequest) -> VerifyResponse:
        pass

from .esewa import EsewaProvider
from .khalti import KhaltiProvider
from .fonepay import FonepayProvider

