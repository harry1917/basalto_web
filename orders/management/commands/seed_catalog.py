from django.core.management.base import BaseCommand
from orders.models import Product, Variant

SIZES = ["S", "M", "L", "XL", "XXL"]

def sku(slug_sleeve: str, color_code: str, size: str):
    # BAS-CC-ML-NGR-S
    return f"BAS-CC-{slug_sleeve}-{color_code}-{size}"

class Command(BaseCommand):
    help = "Seed Basalto catalog (Camisa cuello chino) with variants + stock."

    def handle(self, *args, **options):
        product, _ = Product.objects.get_or_create(
            title="Camisa cuello chino",
            defaults={"active": True, "description": "Camisas cuello chino en manta hindú. Producción por lote."},
        )

        cards = [
            # Manga larga $30 / $35
            {"img":"images/catalogo/1.webp", "sleeve":"Manga larga", "sl":"ML", "color":"Negro",       "cc":"NGR", "price":"30", "compare":"35"},
            {"img":"images/catalogo/2.webp", "sleeve":"Manga larga", "sl":"ML", "color":"Azul",        "cc":"AZL", "price":"30", "compare":"35"},
            {"img":"images/catalogo/3.webp", "sleeve":"Manga larga", "sl":"ML", "color":"Blanco",      "cc":"BLN", "price":"30", "compare":"35"},
            {"img":"images/catalogo/4.webp", "sleeve":"Manga larga", "sl":"ML", "color":"Verde musgo", "cc":"VMU", "price":"30", "compare":"35"},
            {"img":"images/catalogo/5.webp", "sleeve":"Manga larga", "sl":"ML", "color":"Beige",       "cc":"BEI", "price":"30", "compare":"35"},

            # Manga corta $25 / $30
            {"img":"images/catalogo/6.webp",  "sleeve":"Manga corta", "sl":"MC", "color":"Negro",       "cc":"NGR", "price":"25", "compare":"30"},
            {"img":"images/catalogo/7.webp",  "sleeve":"Manga corta", "sl":"MC", "color":"Azul",        "cc":"AZL", "price":"25", "compare":"30"},
            {"img":"images/catalogo/8.webp",  "sleeve":"Manga corta", "sl":"MC", "color":"Blanco",      "cc":"BLN", "price":"25", "compare":"30"},
            {"img":"images/catalogo/9.webp",  "sleeve":"Manga corta", "sl":"MC", "color":"Verde musgo", "cc":"VMU", "price":"25", "compare":"30"},
            {"img":"images/catalogo/10.webp", "sleeve":"Manga corta", "sl":"MC", "color":"Beige",       "cc":"BEI", "price":"25", "compare":"30"},
        ]

        created = 0
        updated = 0

        for card in cards:
            for size in SIZES:
                s = sku(card["sl"], card["cc"], size)

                v, was_created = Variant.objects.get_or_create(
                    sku=s,
                    defaults={
                        "product": product,
                        "sleeve": card["sleeve"],
                        "color": card["color"],
                        "size": size,
                        "fabric": "Manta hindú",
                        "img": card["img"],
                        "price": card["price"],
                        "compare_at": card["compare"],
                        "inventory": 12,
                        "active": True,
                    }
                )

                if was_created:
                    created += 1
                else:
                    # opcional: actualizar datos si cambiaron (sin tocar inventory)
                    changed = False
                    if v.img != card["img"]: v.img = card["img"]; changed = True
                    if str(v.price) != str(card["price"]): v.price = card["price"]; changed = True
                    if str(v.compare_at) != str(card["compare"]): v.compare_at = card["compare"]; changed = True
                    if v.sleeve != card["sleeve"]: v.sleeve = card["sleeve"]; changed = True
                    if v.color != card["color"]: v.color = card["color"]; changed = True
                    if changed:
                        v.save()
                        updated += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Seed OK. Created: {created}, Updated: {updated}"))
