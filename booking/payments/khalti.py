import requests
import json
from typing import Dict, Any
from . import PaymentProvider, PaymentRequest, PaymentResponse, VerifyRequest, VerifyResponse

class KhaltiProvider(PaymentProvider):
    def __init__(self, secret_key: str, website_url: str, sandbox: bool = True):
        self.secret_key = secret_key
        self.website_url = website_url
        self.sandbox = sandbox
        self.base_url = "https://a.khalti.com/api/v2/epayment/initiate/"
        self.lookup_url = "https://a.khalti.com/api/v2/epayment/lookup/"

    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        # Amount in Paisa (1 NPR = 100 Paisa)
        amount_paisa = int(request.amount * 100)
        
        payload = {
            "return_url": request.callback_url,
            "website_url": self.website_url,
            "amount": amount_paisa,
            "purchase_order_id": request.order_id,
            "purchase_order_name": request.description,
            "customer_info": {
                "name": "Ticket Sathi User",
                "email": request.customer_email or "test@example.com",
                "phone": request.customer_phone or "9800000000"
            }
        }
        
        headers = {
            'Authorization': f'Key {self.secret_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return PaymentResponse(
                is_form_post=False,
                target_url=data.get("payment_url"),
                form_fields={},
                transaction_id=data.get("pid"),
                raw_response=data
            )
        except Exception as e:
            # Fallback/Error handling
            print(f"Khalti Init Error: {e}")
            if hasattr(e, 'response') and e.response:
                print(e.response.text)
            return PaymentResponse(
                is_form_post=False,
                target_url="",
                form_fields={},
                transaction_id="",
                raw_response={"error": str(e)}
            )

    def verify_payment(self, request: VerifyRequest) -> VerifyResponse:
        # Khalti callback params: pidx, txnId, amount, mobile, purchase_order_id, purchase_order_name, transaction_id
        pidx = request.encoded_params.get("pidx")
        
        if not pidx:
             return VerifyResponse(success=False, transaction_id="", amount=0, status="FAILED", raw_response={"error": "Missing pidx"})

        payload = {"pidx": pidx}
        headers = {
            'Authorization': f'Key {self.secret_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(self.lookup_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status")
            success = status == "Completed"
            
            return VerifyResponse(
                success=success,
                transaction_id=data.get("transaction_id", ""),
                amount=float(data.get("total_amount", 0)) / 100, # Convert back to NPR
                status=status,
                gateway_ref=pidx,
                raw_response=data
            )
        except Exception as e:
             return VerifyResponse(success=False, transaction_id="", amount=0, status="ERROR", raw_response={"error": str(e)})
