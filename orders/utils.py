from django.utils import timezone
import random

def generate_order_number(prefix="BAS"):
    d = timezone.now().strftime("%Y%m%d")
    r = random.randint(1000, 9999)
    return f"{prefix}-{d}-{r}"
