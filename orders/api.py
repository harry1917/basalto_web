import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Order, OrderItem, Variant
from .utils import generate_order_number
from .wompi import create_payment_link

SHIPPING_FLAT = Decimal("3.00")

PREORDER_NOTICE = (
    "Pre-order — producción por lote.\n"
    "Tu pedido se confecciona especialmente para vos.\n"
    "Producción: 10–15 días.\n"
    "Envío: San Salvador 3 días · departamentos 4–5 días hábiles.\n"
)

TRANSFER_INFO = (
    "Transferencia bancaria:\n"
    "Banco: BANCO AGRICOLA\n"
    "Cuenta de ahorro: 3550507559\n"
    "A nombre de: WILDER DIAZ\n"
    "Referencia: {ref}\n"
    "Enviá tu comprobante por este chat para confirmar tu pre-order.\n"
)


def build_message(order: Order) -> str:
    lines = []
    lines.append(f"Pedido BASALTO: {order.order_number}")
    lines.append("")
    for it in order.items.all():
        sku_txt = f" | SKU {it.variant.sku}" if getattr(it, "variant", None) else ""
        lines.append(
            f"- {it.title} | {it.sleeve} | {it.color} | Talla {it.size} | x{it.qty} — ${it.unit_price}{sku_txt}"
        )
    lines.append("")
    lines.append(f"Subtotal: ${order.subtotal}")
    lines.append(f"Envío (El Salvador): ${order.shipping}")
    lines.append(f"Total: ${order.total}")
    lines.append("")
    lines.append("Datos de envío:")
    lines.append(f"Nombre: {order.full_name}")
    lines.append(f"Tel: {order.phone}")
    addr = f"{order.address_line1} {order.address_line2}".strip()
    lines.append(f"Dirección: {addr}")
    if order.city:
        lines.append(f"Ciudad/Municipio: {order.city}")
    if order.department:
        lines.append(f"Departamento: {order.department}")
    lines.append("")
    lines.append(f"Método de pago: {order.payment_method.upper()}")
    lines.append("")
    lines.append(PREORDER_NOTICE.strip())
    if order.payment_method == "transfer":
        lines.append("")
        lines.append(TRANSFER_INFO.format(ref=order.order_number).strip())
    if order.payment_link:
        lines.append("")
        lines.append(f"Link de pago (Wompi): {order.payment_link}")
    return "\n".join(lines)


def _to_int(value, default=1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_money(value) -> str:
    """
    Deja solo dígitos y punto. Ej:
      "$30" -> "30"
      "30.00" -> "30.00"
      "Q30" -> "30"
      "30,00" -> "30.00"
    """
    s = str(value or "").strip()
    s = s.replace(",", ".")
    s = re.sub(r"[^0-9.]", "", s)
    # si queda vacío, devolvemos "0"
    return s if s else "0"


def _to_decimal(value, default="0") -> Decimal:
    try:
        return Decimal(_clean_money(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


@csrf_exempt
@require_POST
def create_order(request):
    # ---- Parse JSON ----
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    # ---- Country lock ----
    country = (payload.get("country") or "El Salvador").strip()
    if country.lower() != "el salvador":
        return HttpResponseBadRequest("Solo enviamos a El Salvador")

    # ---- Payment method ----
    payment_method = (payload.get("payment_method") or "card").strip().lower()
    if payment_method not in ["card", "transfer"]:
        return HttpResponseBadRequest("Método de pago inválido")

    # ---- Shipping fields ----
    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    address_line1 = (payload.get("address_line1") or "").strip()

    if not full_name or not phone or not address_line1:
        return HttpResponseBadRequest("Faltan datos de envío")

    items = payload.get("items") or []
    if not isinstance(items, list) or len(items) == 0:
        return HttpResponseBadRequest("Carrito vacío")

    valid_sizes = {"S", "M", "L", "XL", "XXL"}

    # ---- Pre-clean + agrupar SKUs ----
    cleaned = []
    skus_needed = {}

    for it in items:
        size = (it.get("size") or "").strip().upper()
        if size not in valid_sizes:
            return HttpResponseBadRequest("Talla inválida")

        qty = max(1, _to_int(it.get("qty"), 1))

        sku = (it.get("sku") or "").strip()
        if sku:
            skus_needed[sku] = skus_needed.get(sku, 0) + qty

        cleaned.append({
            "title": (it.get("title") or "Camisa cuello chino").strip(),
            "sleeve": (it.get("sleeve") or "").strip(),
            "color": (it.get("color") or "").strip(),
            "size": size,
            "fabric": (it.get("fabric") or "").strip(),
            "img": (it.get("img") or "").strip(),
            "qty": qty,
            "sku": sku,
            "raw_price": it.get("unit_price") or it.get("price") or "0",
        })

    # ---- Persist + inventory (atomic) ----
    with transaction.atomic():
        variants_by_sku = {}

        # ✅ Si hay SKU, bloqueamos, validamos stock y obtenemos precio real
        if skus_needed:
            variants = (
                Variant.objects
                .select_for_update()
                .filter(sku__in=list(skus_needed.keys()), active=True)
            )
            variants_by_sku = {v.sku: v for v in variants}

            missing = [sku for sku in skus_needed.keys() if sku not in variants_by_sku]
            if missing:
                return HttpResponseBadRequest(f"SKU no existe o inactivo: {', '.join(missing)}")

            for sku, need_qty in skus_needed.items():
                v = variants_by_sku[sku]
                if v.inventory < need_qty:
                    return HttpResponseBadRequest(
                        f"Sin stock para {sku} (stock {v.inventory}, requerido {need_qty})"
                    )

        # ---- Calcular totales (ya con precio real si hay SKU) ----
        subtotal = Decimal("0.00")
        for row in cleaned:
            if row["sku"]:
                v = variants_by_sku[row["sku"]]
                unit_price = Decimal(v.price)  # ✅ precio real desde DB
                # opcional: sincronizar display
                row["title"] = v.product.title
                row["sleeve"] = v.sleeve
                row["color"] = v.color
                row["fabric"] = v.fabric
                row["img"] = v.img
            else:
                unit_price = _to_decimal(row["raw_price"], "0")

            if unit_price <= 0:
                return HttpResponseBadRequest("Precio inválido")

            row["unit_price"] = unit_price
            row["line_total"] = unit_price * row["qty"]
            subtotal += row["line_total"]

        shipping = SHIPPING_FLAT
        total = subtotal + shipping

        # ---- Crear Order ----
        order = Order.objects.create(
            order_number=generate_order_number("BAS"),
            status="pending",
            payment_method=payment_method,
            country="El Salvador",
            full_name=full_name,
            phone=phone,
            address_line1=address_line1,
            address_line2=(payload.get("address_line2") or "").strip(),
            department=(payload.get("department") or "").strip(),
            city=(payload.get("city") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            subtotal=subtotal,
            shipping=shipping,
            total=total,
        )

        # ---- Descontar inventario (si hay SKU) ----
        if skus_needed:
            for sku, need_qty in skus_needed.items():
                v = variants_by_sku[sku]
                v.inventory -= need_qty
                v.save(update_fields=["inventory", "updated_at"])

        # ---- Crear items ----
        for row in cleaned:
            variant = variants_by_sku.get(row["sku"]) if row["sku"] else None

            OrderItem.objects.create(
                order=order,
                variant=variant,
                title=row["title"],
                sleeve=row["sleeve"],
                color=row["color"],
                size=row["size"],
                fabric=row["fabric"] or (variant.fabric if variant else ""),
                img=row["img"],
                qty=row["qty"],
                unit_price=row["unit_price"],
                line_total=row["line_total"],
            )

        # ---- Wompi: only for card ----
        order.payment_link = ""
        if payment_method == "card":
            success_url = f"{settings.FRONTEND_DOMAIN.rstrip('/')}/payment/success/"
            webhook_url = settings.WOMPI_WEBHOOK_URL

            try:
                payment_link = create_payment_link(
                    order_number=order.order_number,
                    amount_usd=float(order.total),
                    success_url="https://www.basalto1530.com/payment/success/",
                    webhook_url="https://web-production-844fb.up.railway.app/wompi/callback/",

                )
                order.payment_link = payment_link or ""
                order.status = "payment_link_created" if order.payment_link else "pending"
            except Exception as e:
                # No botar toda la orden si Wompi falla
                order.payment_link = ""
                order.status = "pending"
                order.save(update_fields=["payment_link", "status", "updated_at"])
                return JsonResponse({
                    "ok": False,
                    "error": "WOMPI_ERROR",
                    "detail": str(e),
                    "order_number": order.order_number,
                }, status=502)
        else:
            # Transferencia
            order.status = "pending"

        order.save(update_fields=["payment_link", "status", "updated_at"])

    # ---- WhatsApp message ----
    wa_phone = getattr(settings, "BASALTO_WHATSAPP_NUMBER", "50300000000")
    message = build_message(order)
    whatsapp_url = f"https://wa.me/{wa_phone}?text={quote(message, safe='')}"

    return JsonResponse({
        "ok": True,
        "order_number": order.order_number,
        "payment_method": order.payment_method,
        "subtotal": str(order.subtotal),
        "shipping": str(order.shipping),
        "total": str(order.total),
        "payment_link": order.payment_link,
        "whatsapp_url": whatsapp_url,
        "preorder_notice": PREORDER_NOTICE,
    })
