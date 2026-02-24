# orders/wompi.py
import time
import requests
from django.conf import settings

def wompi_app_ping():
    token = get_wompi_token()
    r = requests.get(
        f"{settings.WOMPI_API_BASE}/Aplicativo",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )
    return r.status_code, r.text


_token_cache = {"token": None, "exp": 0}

def get_wompi_token() -> str:
    print("WOMPI DEBUG:",
          "ID=", settings.WOMPI_CLIENT_ID[:6] + "..." if settings.WOMPI_CLIENT_ID else "EMPTY",
          "SECRET=", "SET" if settings.WOMPI_CLIENT_SECRET else "EMPTY",
          "AUD=", settings.WOMPI_AUDIENCE,
          "TOKEN_URL=", settings.WOMPI_TOKEN_URL
    )
    
    now = int(time.time())
    if _token_cache["token"] and now < _token_cache["exp"] - 30:
        return _token_cache["token"]

    token_data = {
        "grant_type": "client_credentials",
        "client_id": settings.WOMPI_CLIENT_ID,
        "client_secret": settings.WOMPI_CLIENT_SECRET,
        "audience": settings.WOMPI_AUDIENCE,
    }

    r = requests.post(
        settings.WOMPI_TOKEN_URL,
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )

    if not r.ok:
        raise Exception(f"TOKEN {r.status_code}: {r.text}")

    data = r.json()
    token = data.get("access_token")
    if not token:
        raise Exception(f"No se recibió access_token. Respuesta: {data}")

    expires_in = int(data.get("expires_in", 3600))
    _token_cache["token"] = token
    _token_cache["exp"] = now + expires_in
    return token


def create_payment_link(order_number: str, amount_usd: float, success_url: str, webhook_url: str) -> str:
    token = get_wompi_token()

    payload = {
        "identificadorEnlaceComercio": order_number,
        "monto": float(amount_usd),
        "nombreProducto": f"BASALTO · Orden {order_number}",
        "configuracion": {
            "urlRedirect": success_url,
            "urlWebhook": webhook_url,
        },
    }

    r = requests.post(
        f"{settings.WOMPI_API_BASE}/EnlacePago",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Basalto/1.0",
        },
        timeout=30
    )

    if not r.ok:
        # 👇 esto te dirá EXACTAMENTE por qué es 403
        raise Exception(f"ENLACE {r.status_code}: {r.text}")

    data = r.json()
    link = data.get("urlEnlace") or data.get("UrlEnlace")
    if not link:
        raise Exception(f"No se recibió urlEnlace. Respuesta: {data}")
    return link
