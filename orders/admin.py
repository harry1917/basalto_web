from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("title","sleeve","color","size","fabric","unit_price","qty","line_total","img")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.action(description="Marcar como EN PROCESO")
def mark_processing(modeladmin, request, queryset):
    queryset.update(status="processing")

@admin.action(description="Marcar como ENVIADA")
def mark_shipped(modeladmin, request, queryset):
    queryset.update(status="shipped")

@admin.action(description="Marcar como ENTREGADA")
def mark_delivered(modeladmin, request, queryset):
    queryset.update(status="delivered")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]

    list_display = (
        "order_number",
        "status",
        "payment_method",
        "total",
        "full_name",
        "phone",
        "department",
        "city",
        "created_at",
    )

    list_filter = ("status", "payment_method", "department", "created_at")
    search_fields = ("order_number", "full_name", "phone", "address_line1", "city", "department")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at", "subtotal", "shipping", "total", "payment_link")

    fieldsets = (
        ("Estado", {"fields": ("order_number", "status", "payment_method", "payment_link", "tracking_code")}),
        ("Cliente", {"fields": ("full_name", "phone")}),
        ("Envío", {"fields": ("country", "address_line1", "address_line2", "department", "city", "notes")}),
        ("Totales", {"fields": ("subtotal", "shipping", "total")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    actions = [mark_processing, mark_shipped, mark_delivered]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "sleeve", "color", "size", "qty", "unit_price", "line_total")
    list_filter = ("sleeve", "color", "size")
    search_fields = ("order__order_number", "title", "color", "size")
    ordering = ("-id",)

