"""Round-trip de cifragem de campo (Fernet)."""
from app.security.crypto import decrypt_str, encrypt_str


def test_round_trip():
    plain = "João da Silva · 000.000.000-00"
    cipher = encrypt_str(plain)
    assert cipher is not None
    assert cipher != plain.encode()  # não é texto claro
    assert decrypt_str(cipher) == plain


def test_none_passthrough():
    assert encrypt_str(None) is None
    assert decrypt_str(None) is None


def test_ciphertext_nao_deterministico():
    # Fernet inclui IV/timestamp: dois cifrados do mesmo texto diferem.
    a = encrypt_str("mesmo texto")
    b = encrypt_str("mesmo texto")
    assert a != b
    assert decrypt_str(a) == decrypt_str(b) == "mesmo texto"
