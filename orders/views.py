import json
import logging
import hmac
import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Order, OrderItem, Product, Variant
from .wompi_redirect import validate_redirect_hash_payment_link

logger = logging.getLogger(__name__)

SIZES = ["S", "M", "L", "XL", "XXL"]


# =========================
# Helpers
# =========================
def staff_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def build_men_cards():
    """
    Construye cards (agrupadas) desde Variant:
    - agrupa por producto + sleeve + color + img + price + compare_at
    - genera sku_map por talla
    """
    variants = Variant.objects.filter(active=True, inventory__gt=0).select_related("product")


    groups = {}
    for v in variants:
        key = (v.product_id, v.sleeve, v.color, v.img, str(v.price), str(v.compare_at))
        groups.setdefault(key, []).append(v)

    cards = []
    for (_, sleeve, color, img, _, _), group in groups.items():
        sku_map = {g.size: g.sku for g in group}
        cards.append({
            "title": group[0].product.title if group and group[0].product else "Producto",
            "sleeve": sleeve,
            "color": color,
            "fabric": group[0].fabric if group else "",
            "img": img,
            "price": group[0].price if group else 0,
            "compare": group[0].compare_at if group else 0,
            "sizes": SIZES,
            "sku_map": sku_map,
        })

    def order_key(c):
        sleeve = (c["sleeve"] or "").lower()
        return (0 if "larga" in sleeve else 1, c["color"] or "")
    cards.sort(key=order_key)

    return cards


# =========================
# Public pages
# =========================
def home(request):
    return render(request, "index.html", {"men_cards": build_men_cards()})


def catalogo(request):
    return render(request, "catalogo.html", {"men_cards": build_men_cards()})

def nocturne(request):
    return render(request, "nocturne.html", {"men_cards": build_men_cards()})


# =========================
# Payments / Webhooks
# =========================
@csrf_exempt
def wompi_callback(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    raw = request.body  # bytes exactos
    signature = (request.headers.get("wompi_hash", "") or "").lower()

    expected = hmac.new(
        key=settings.WOMPI_CLIENT_SECRET.encode("utf-8"),
        msg=raw,
        digestmod=hashlib.sha256,
    ).hexdigest().lower()

    if not signature or not hmac.compare_digest(expected, signature):
        logger.warning("❌ Webhook inválido: wompi_hash no coincide.")
        return HttpResponse(status=401)

    try:
        data = json.loads(raw.decode("utf-8"))
        ref = data.get("IdExterno")
        if not ref:
            logger.warning(
                "⚠️ Webhook sin IdExterno. Keys recibidas: %s | data=%s",
                list(data.keys()),
                data,
                )
            return HttpResponse(status=200)


        order = Order.objects.filter(
            order_number=ref,
            status__in=["pending", "payment_link_created"],
        ).first()

        if not order:
            logger.info("ℹ️ Orden no encontrada o ya procesada ref=%s", ref)
            return HttpResponse(status=200)

        order.status = "paid"
        order.save(update_fields=["status", "updated_at"])
        logger.info("✅ Orden %s confirmada vía webhook.", ref)

    except Exception as e:
        logger.exception("💥 Error procesando webhook: %s", e)

    return HttpResponse(status=200)


def payment_success(request):
    q = request.GET

    ref = q.get("identificadorEnlaceComercio") or q.get("ref")
    order = Order.objects.filter(order_number=ref).first() if ref else None

    redirect_ok = False
    if q.get("hash") and q.get("identificadorEnlaceComercio"):
        redirect_ok = validate_redirect_hash_payment_link(q)

    return render(request, "payment_success.html", {
        "order": order,
        "redirect_ok": redirect_ok,
        "idTransaccion": q.get("idTransaccion"),
        "idEnlace": q.get("idEnlace"),
        "monto": q.get("monto"),
    })


# =========================
# Dashboard Auth
# =========================
def dashboard_login(request):
    if request.user.is_authenticated:
        return redirect("orders:dashboard_orders")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)

        if user and staff_required(user):
            login(request, user)
            return redirect("orders:dashboard_orders")

        messages.error(request, "Credenciales inválidas o sin permisos.")

    return render(request, "dashboard/login.html")


@login_required
def dashboard_logout(request):
    logout(request)
    return redirect("orders:dashboard_login")


# =========================
# Dashboard Orders
# =========================
@login_required
@user_passes_test(staff_required)
def dashboard_orders(request):
    qs = Order.objects.all().order_by("-created_at")

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()

    if q:
        qs = qs.filter(
            Q(order_number__icontains=q)
            | Q(full_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(city__icontains=q)
            | Q(department__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    base = Order.objects.all()
    stats = {
        "pending": base.filter(status="pending").count(),
        "payment_link_created": base.filter(status="payment_link_created").count(),
        "paid": base.filter(status="paid").count(),
        "processing": base.filter(status="processing").count(),
        "shipped": base.filter(status="shipped").count(),
        "delivered": base.filter(status="delivered").count(),
        "cancelled": base.filter(status="cancelled").count(),
        "total": base.count(),
    }

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "dashboard/orders_list.html", {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "STATUS_CHOICES": Order.STATUS_CHOICES,
        "stats": stats,
    })


@login_required
@user_passes_test(staff_required)
def dashboard_order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    items = order.items.all().order_by("id")

    flow = ["pending", "payment_link_created", "paid", "processing", "shipped", "delivered"]
    current = order.status
    current_index = flow.index(current) if current in flow else -1

    timeline = []
    for i, key in enumerate(flow):
        timeline.append({
            "key": key,
            "label": dict(Order.STATUS_CHOICES).get(key, key),
            "is_active": (key == current),
            "is_done": (current_index != -1 and i < current_index),
        })

    return render(request, "dashboard/order_detail.html", {
        "order": order,
        "items": items,
        "STATUS_CHOICES": Order.STATUS_CHOICES,
        "timeline": timeline,
    })


@login_required
@user_passes_test(staff_required)
@require_POST
def dashboard_order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)

    new_status = (request.POST.get("status") or "").strip()
    tracking = (request.POST.get("tracking_code") or "").strip()

    valid_status = dict(Order.STATUS_CHOICES)
    if new_status and new_status in valid_status:
        order.status = new_status

    order.tracking_code = tracking
    order.save(update_fields=["status", "tracking_code", "updated_at"])

    return redirect("orders:dashboard_order_detail", pk=order.pk)


@login_required
@user_passes_test(staff_required)
@require_POST
def dashboard_order_quick_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = (request.POST.get("status") or "").strip()

    if new_status and new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

    return redirect("orders:dashboard_orders")


@login_required
@user_passes_test(staff_required)
@require_POST
def dashboard_orderitem_qty(request, pk):
    item = get_object_or_404(OrderItem, pk=pk)
    qty = request.POST.get("qty")

    try:
        qty_int = int(qty)
        if qty_int >= 1:
            item.qty = qty_int
            item.save()  # recalcula line_total en save()
    except (TypeError, ValueError):
        pass

    return redirect("orders:dashboard_order_detail", pk=item.order_id)


# =========================
# Dashboard Inventory
# =========================
@login_required
@user_passes_test(staff_required)
def dashboard_inventory(request):
    qs = Variant.objects.select_related("product").order_by("product__title", "sleeve", "color", "size")

    q = (request.GET.get("q") or "").strip()
    low = (request.GET.get("low") or "").strip()

    if q:
        qs = qs.filter(
            Q(sku__icontains=q)
            | Q(product__title__icontains=q)
            | Q(color__icontains=q)
            | Q(size__icontains=q)
            | Q(sleeve__icontains=q)
        )

    if low == "1":
        qs = qs.filter(inventory__lte=models.F("low_stock_threshold"))

    return render(request, "dashboard/inventory_list.html", {
        "variants": qs[:300],  # luego lo paginamos
        "q": q,
        "low": low,
    })


@login_required
@user_passes_test(staff_required)
def dashboard_variant_detail(request, pk):
    v = get_object_or_404(Variant.objects.select_related("product"), pk=pk)
    return render(request, "dashboard/variant_detail.html", {"v": v})


@login_required
@user_passes_test(staff_required)
@require_POST
def dashboard_variant_set_stock(request, pk):
    v = get_object_or_404(Variant, pk=pk)
    val = request.POST.get("inventory")

    try:
        v.inventory = int(val)
        v.save(update_fields=["inventory", "updated_at"])
    except (TypeError, ValueError):
        pass

    return redirect("orders:dashboard_variant_detail", pk=v.pk)
