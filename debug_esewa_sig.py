import hmac
import hashlib
import base64

def generate_signature(secret_key: str, message: str) -> str:
    secret = secret_key.encode('utf-8')
    message_bytes = message.encode('utf-8')
    hmac_sha256 = hmac.new(secret, message_bytes, hashlib.sha256)
    digest = hmac_sha256.digest()
    return base64.b64encode(digest).decode('utf-8')

key = "8gBm/:&EnhH.1/q"
msg = "100,11-201-13,EPAYTEST"
sig = generate_signature(key, msg)
print(f"Message: {msg}")
print(f"Signature: {sig}")
