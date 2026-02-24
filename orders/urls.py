from django.urls import path
from .api import create_order
from .views import wompi_callback, payment_success
from . import views

app_name = "orders"

urlpatterns = [
    # API / pagos
    path("api/orders/create/", create_order, name="create_order"),
    path("wompi/callback/", wompi_callback, name="wompi_callback"),
    path("payment/success/", payment_success, name="payment_success"),

    # Dashboard auth
    path("dashboard/login/", views.dashboard_login, name="dashboard_login"),
    path("dashboard/logout/", views.dashboard_logout, name="dashboard_logout"),

    # Dashboard
    path("dashboard/orders/", views.dashboard_orders, name="dashboard_orders"),
    path("dashboard/orders/<int:pk>/", views.dashboard_order_detail, name="dashboard_order_detail"),
    path("dashboard/orders/<int:pk>/update/", views.dashboard_order_update, name="dashboard_order_update"),
    path("dashboard/order-items/<int:pk>/qty/", views.dashboard_orderitem_qty, name="dashboard_orderitem_qty"),
    path("dashboard/orders/<int:pk>/status/", views.dashboard_order_quick_status, name="dashboard_order_quick_status"),
    
    path("dashboard/inventory/", views.dashboard_inventory, name="dashboard_inventory"),
    path("dashboard/inventory/<int:pk>/", views.dashboard_variant_detail, name="dashboard_variant_detail"),
    path("dashboard/inventory/<int:pk>/set/", views.dashboard_variant_set_stock, name="dashboard_variant_set_stock"),
    
    path("catalogo/", views.catalogo, name="catalogo"),
    path("nocturne/", views.nocturne, name="nocturne"),


]
