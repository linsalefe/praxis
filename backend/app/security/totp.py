"""TOTP (RFC 6238) para 2FA."""
import base64
from io import BytesIO

import pyotp
import qrcode

from app.config import get_settings


def generate_secret() -> str:
    return pyotp.random_base32()


def build_uri(secret: str, email: str) -> str:
    s = get_settings()
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=s.totp_issuer)


def qr_png_datauri(uri: str) -> str:
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def verify(secret: str, code: str) -> bool:
    if not code or not secret:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
