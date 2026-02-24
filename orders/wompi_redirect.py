import hmac
import hashlib
from django.conf import settings

def validate_redirect_hash_payment_link(querydict) -> bool:
    """
    Enlace de pago:
      identificadorEnlaceComercio + idTransaccion + idEnlace + monto
    comparar con ?hash
    """
    received = (querydict.get("hash") or "").lower()
    if not received:
        return False

    concat = (
        (querydict.get("identificadorEnlaceComercio") or "") +
        (querydict.get("idTransaccion") or "") +
        (querydict.get("idEnlace") or "") +
        (querydict.get("monto") or "")
    )

    calc = hmac.new(
        key=settings.WOMPI_CLIENT_SECRET.encode("utf-8"),
        msg=concat.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest().lower()

    return hmac.compare_digest(calc, received)
