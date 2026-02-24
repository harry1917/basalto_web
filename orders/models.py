from django.db import models

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("payment_link_created", "Link de pago creado"),
        ("paid", "Pagada"),
        ("processing", "En proceso"),
        ("shipped", "Enviada"),
        ("delivered", "Entregada"),
        ("cancelled", "Cancelada"),
    ]
    

    PAYMENT_CHOICES = [("card","Tarjeta"), ("transfer","Transferencia")]

    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")

    country = models.CharField(max_length=50, default="El Salvador")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    address_line1 = models.CharField(max_length=180)
    address_line2 = models.CharField(max_length=180, blank=True, default="")
    department = models.CharField(max_length=80, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_method = models.CharField(max_length=20, default="card", choices=PAYMENT_CHOICES)
    payment_link = models.URLField(blank=True, default="")

    tracking_code = models.CharField(max_length=80, blank=True, default="")  # opcional
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # 👈 nuevo

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)

    title = models.CharField(max_length=120)
    sleeve = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=10)
    fabric = models.CharField(max_length=50, default="Manta hindú")
    img = models.CharField(max_length=255, blank=True, default="")

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    variant = models.ForeignKey("Variant", null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items")


    def save(self, *args, **kwargs):
        self.line_total = (self.unit_price or 0) * self.qty
        super().save(*args, **kwargs)

from django.db import models
from django.utils.text import slugify

class Product(models.Model):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True, default="")
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:120] or "product"
            s = base
            i = 2
            while Product.objects.filter(slug=s).exists():
                s = f"{base}-{i}"
                i += 1
            self.slug = s
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title



class Variant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)

    sku = models.CharField(max_length=60, unique=True)
    sleeve = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=10)
    fabric = models.CharField(max_length=50, default="Manta hindú")

    img = models.CharField(max_length=255, blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    inventory = models.IntegerField(default=0)  # stock actual
    low_stock_threshold = models.IntegerField(default=3)

    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    compare_at = models.DecimalField(max_digits=10, decimal_places=2, default=0)


    @property
    def is_low_stock(self):
        return self.inventory <= self.low_stock_threshold

    def __str__(self):
        return f"{self.product.title} · {self.sleeve}/{self.color}/{self.size} ({self.sku})"
