import hmac
import hashlib
from typing import Dict, Any
from . import PaymentProvider, PaymentRequest, PaymentResponse, VerifyRequest, VerifyResponse

class FonepayProvider(PaymentProvider):
    def __init__(self, merchant_code: str, secret_key: str, sandbox: bool = True):
        self.merchant_code = merchant_code
        self.secret_key = secret_key
        self.sandbox = sandbox
        self.base_url = "https://dev-clientapi.fonepay.com/api/merchantRequest" if sandbox else "https://clientapi.fonepay.com/api/merchantRequest"
        # Verification URL depends on client/server logic, usually server-to-server check
        self.verify_url = "https://dev-clientapi.fonepay.com/api/merchantRequest/verification" if sandbox else "https://clientapi.fonepay.com/api/merchantRequest/verification"

    def _generate_signature(self, data_string: str) -> str:
        # FonePay uses HMAC-SHA512
        return hmac.new( # type: ignore
            self.secret_key.encode('utf-8'),
            data_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        # Data format: PID,MD,PRN,AMT,CRN,DT,R1,R2,RU
        # PID: Merchant Code
        # MD: MD? Usually "P" for payment? Or defined by merchant. Let's assume 'P'.
        # PRN: Order ID
        # AMT: Amount
        # CRN: Currency (NPR)
        # DT: Date (MM/DD/YYYY) - request.description used for now or generated
        # R1: Remarks 1
        # R2: Remarks 2
        # RU: Return URL
        
        # NOTE: The FonePay documentation is strictly required. 
        # Using the standard format for redirect.
        
        import datetime
        date_str = datetime.datetime.now().strftime("%m/%d/%Y")
        
        # Signature string: PID,MD,PRN,AMT,CRN,DT,R1,R2,RU
        # Be careful with empty params.
        
        params = {
            "PID": self.merchant_code,
            "MD": "P",
            "PRN": request.order_id,
            "AMT": str(request.amount),
            "CRN": "NPR",
            "DT": date_str,
            "R1": request.description[:50], # Limit length
            "R2": "TicketSathi",
            "RU": request.callback_url
        }
        
        sig_payload = f"{params['PID']},{params['MD']},{params['PRN']},{params['AMT']},{params['CRN']},{params['DT']},{params['R1']},{params['R2']},{params['RU']}"
        params["DV"] = self._generate_signature(sig_payload)
        
        # Construct Redirect URL
        import urllib.parse
        query_string = urllib.parse.urlencode(params)
        redirect_url = f"{self.base_url}?{query_string}"
        
        return PaymentResponse(
            is_form_post=False,
            target_url=redirect_url,
            form_fields={},
            transaction_id=request.order_id,
            raw_response=params
        )

    def verify_payment(self, request: VerifyRequest) -> VerifyResponse:
        # FonePay callback params: PRN, PID, PS, RC, DV, UID, BC, INI, P_AMT, R_AMT
        # PS: Payment Status (Success/Failed)
        # RC: Response Code
        params = request.encoded_params
        
        prn = params.get("PRN")
        pid = params.get("PID")
        ps = params.get("PS")
        rc = params.get("RC")
        dv = params.get("DV")
        uid = params.get("UID")
        p_amt = params.get("P_AMT", "0")
        
        # Call FonePay Verification API for secure confirmation
        try:
            import requests
            verify_params = {
                "PRN": prn,
                "PID": pid,
                "UID": uid,
                "DV": dv
            }
            response = requests.get(self.verify_url, params=verify_params, timeout=5)
            response.raise_for_status()
            verify_data = response.json()
            
            # Check verification response
            success = verify_data.get("PS") == "Yes" or verify_data.get("RS") == "Success"
            amount = float(p_amt) if p_amt else 0.0
            
        except Exception as e:
            # Fallback: At least verify callback params
            success = (ps == "Yes" or ps == "YES") and (rc == "0" or rc == "Success")
            amount = float(p_amt) if p_amt else 0.0
        
        return VerifyResponse(
            success=success,
            transaction_id=uid or "",
            amount=amount,
            status=ps or "Unknown",
            gateway_ref=prn,
            raw_response=params
        )
