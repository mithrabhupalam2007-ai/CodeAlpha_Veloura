"""
Seed the Veloura catalogue with demo data.

    python manage.py seed_catalog            # load if the store is empty
    python manage.py seed_catalog --reset    # wipe catalogue data first
    python manage.py seed_catalog --with-demo-users  # also create demo accounts

SEED DATA vs PRODUCTION DATA:
Everything created by this command is demo/seed content — product names,
images, reviews and coupons are generated placeholders. Replace them through
the Django admin before going live. The --reset flag deletes previously
seeded categories, products, coupons, reviews and generated media files.
"""
import random
import textwrap
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

# ---------------------------------------------------------------------------
# Catalogue definition: category -> list of products
# ---------------------------------------------------------------------------
CATEGORIES = [
    ('Dresses', 'Flowy day dresses, cocktail dresses and elegant gowns.'),
    ('Tops and T-shirts', 'Everyday tops, tees and crops in soft fabrics.'),
    ('Shirts and Blouses', 'Crisp shirts and feminine blouses for every setting.'),
    ('Jeans and Trousers', 'Denim and tailored trousers with the perfect fit.'),
    ('Skirts', 'Midi, maxi and mini skirts to style your way.'),
    ('Ethnic Wear', 'Sarees, lehengas and salwar sets for every celebration.'),
    ('Kurtis', 'Comfortable kurtis with contemporary prints and cuts.'),
    ('Co-ord Sets', 'Matching sets that make styling effortless.'),
    ('Party Wear', 'Sequins, satin and statement pieces for evenings out.'),
    ('Casual Wear', 'Relaxed essentials for weekends and everyday errands.'),
    ('Office Wear', 'Polished, professional looks that still feel like you.'),
    ('Winter Wear', 'Cozy knits, jackets and layers for colder days.'),
    ('Jumpsuits', 'One-and-done silhouettes for any occasion.'),
    ('Activewear', 'Performance pieces for workouts and athleisure.'),
]

PRODUCTS = {
    'Dresses': [
        ('Aurelia Floral Midi Dress', 2899, 20),
        ('Seraphine Slip Dress', 2499, 15),
        ('Elowen Wrap Maxi Dress', 3299, 25),
        ('Maren Lace Bodycon Dress', 2799, 10),
    ],
    'Tops and T-shirts': [
        ('Liora Ribbed Crop Top', 999, 20),
        ('Camille Relaxed Tee', 799, 10),
        ('Nadia Puff-Sleeve Blouse', 1299, 15),
        ('Isla Linen Blend Top', 1199, 0),
    ],
    'Shirts and Blouses': [
        ('Odette Satin Blouse', 1599, 25),
        ('Cora Oversized Shirt', 1499, 20),
        ('Wren Poplin Formal Shirt', 1399, 10),
        ('Piper Bow-Tie Blouse', 1699, 15),
    ],
    'Jeans and Trousers': [
        ('Nova High-Rise Skinny Jeans', 2199, 20),
        ('Eden Wide-Leg Trousers', 1899, 15),
        ('Riley Straight-Fit Denim', 2299, 10),
        ('Georgia Palazzo Pants', 1799, 0),
    ],
    'Skirts': [
        ('Vivienne Pleated Midi Skirt', 1699, 20),
        ('Sloane Denim Mini Skirt', 1299, 10),
        ('Amara Tiered Maxi Skirt', 1899, 25),
    ],
    'Ethnic Wear': [
        ('Zaira Anarkali Set', 3999, 30),
        ('Meher Banarasi Saree', 4999, 20),
        ('Ira Chikankari Kurta Set', 2899, 15),
        ('Riya Bandhani Dupatta Set', 3499, 25),
    ],
    'Kurtis': [
        ('Anaya Cotton Straight Kurti', 1299, 20),
        ('Tara Printed A-Line Kurti', 1199, 15),
        ('Kiara Rayon Kurti', 1099, 10),
        ('Myra Embroidered Kurti', 1599, 25),
    ],
    'Co-ord Sets': [
        ('Juniper Linen Co-ord Set', 2599, 20),
        ('Paloma Knit Co-ord Set', 2399, 15),
        ('Sage Utility Co-ord Set', 2799, 10),
    ],
    'Party Wear': [
        ('Celeste Sequin Cocktail Dress', 4499, 30),
        ('Nyx Velvet Jumpsuit', 3899, 25),
        ('Lumière Satin Gown', 5499, 20),
        ('Vega Feather Trim Top', 2699, 15),
    ],
    'Casual Wear': [
        ('Poppy Cotton Kurta Dress', 1499, 20),
        ('Meadow Graphic Tee', 699, 10),
        ('Harbor Comfy Joggers', 1399, 15),
        ('Daisy Tiered Peplum Top', 1199, 0),
    ],
    'Office Wear': [
        ('Regina Tailored Blazer', 3499, 20),
        ('Elle Pencil Skirt', 1899, 15),
        ('Aria Formal Trousers', 1999, 10),
        ('Vera Structured Sheath Dress', 2899, 25),
    ],
    'Winter Wear': [
        ('Fjord Cable-Knit Sweater', 2299, 20),
        ('Ember Wool-Blend Coat', 4999, 30),
        ('Hearth Fleece Zip Jacket', 2699, 15),
        ('Bliss Turtleneck Pullover', 1799, 10),
    ],
    'Jumpsuits': [
        ('Willow Belted Jumpsuit', 2799, 20),
        ('Astra Denim Jumpsuit', 2999, 15),
        ('Marigold Halter Jumpsuit', 2599, 25),
    ],
    'Activewear': [
        ('Pulse Performance Leggings', 1599, 20),
        ('Stride Sports Bra', 999, 15),
        ('Flexi Seamless Tank', 1199, 10),
        ('Dash Running Shorts', 899, 0),
    ],
}

COLORS = ['Black', 'Ivory', 'Lavender', 'Rose', 'Sage', 'Navy', 'Blush', 'Wine', 'Sky', 'Ochre']
SIZES = ['S', 'M', 'L', 'XL', 'XXL']

REVIEWS = [
    (5, 'Absolutely love this! The fabric feels premium and the fit is flattering.'),
    (5, 'Exactly as pictured. Shipped fast and packed beautifully.'),
    (4, 'Very pretty and comfortable — just a tad long for my height.'),
    (4, 'Great quality for the price. Sizing runs slightly large.'),
    (3, 'Nice design but the colour is a little lighter than the photos.'),
    (5, 'Second one I have bought — compliments every time!'),
    (4, 'Soft fabric, true to size. Would recommend.'),
]

COUPONS = [
    ('WELCOME10', 'percent', 10, 0, '10% off your first Veloura order'),
    ('FLAT200', 'flat', 200, 1999, 'Flat ₹200 off orders above ₹1999'),
    ('FESTIVE25', 'percent', 25, 2999, '25% off festive orders above ₹2999'),
]

DEMO_USERS = [
    ('Aisha Verma', '9000000001'),
    ('Priya Sharma', '9000000002'),
    ('Neha Iyer', '9000000003'),
]


# ---------------------------------------------------------------------------
# Image generation (Pillow)
# ---------------------------------------------------------------------------
def _gradient_image(width, height, top, bottom, text, subtitle, variant=0):
    """Create an elegant gradient card so every product has a unique image."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new('RGB', (width, height))
    px = img.load()
    for y in range(height):
        t = y / height
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(width):
            px[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img, 'RGBA')

    # Decorative shapes differ per variant so images are not identical.
    rng = random.Random(variant * 7 + 91)
    for _ in range(5):
        cx, cy = rng.randint(0, width), rng.randint(0, height)
        rad = rng.randint(60, 220)
        alpha = rng.randint(14, 34)
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(255, 255, 255, alpha))

    # "Dress silhouette" — abstract figure made of arcs and shapes.
    cx, cy = width // 2, int(height * 0.42)
    draw.ellipse([cx - 42, cy - 118, cx + 42, cy - 34], fill=(255, 255, 255, 90))
    draw.polygon(
        [(cx - 24, cy - 30), (cx + 24, cy - 30), (cx + 96, cy + 190), (cx - 96, cy + 190)],
        fill=(255, 255, 255, 70),
    )
    draw.arc([cx - 130, cy - 60, cx + 130, cy + 170], 200, 340, fill=(255, 255, 255, 110), width=4)

    def _font(size):
        for candidate in (
            '/System/Library/Fonts/Supplemental/Georgia.ttf',
            '/System/Library/Fonts/Supplemental/Times New Roman.ttf',
            '/Library/Fonts/Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        ):
            try:
                return ImageFont.truetype(candidate, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()

    title_font = _font(54)
    sub_font = _font(30)

    # Wrap the product name so long titles do not overflow.
    words, lines, current = text.split(), [], ''
    for word in words:
        trial = (current + ' ' + word).strip()
        if len(trial) > 18:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    lines = lines[:3]

    y = height - 90 - (len(lines) - 1) * 62
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        draw.text(((width - w) / 2 + 2, y + 2), line, font=title_font, fill=(40, 30, 70, 90))
        draw.text(((width - w) / 2, y), line, font=title_font, fill=(255, 255, 255, 245))
        y += 62

    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    w = bbox[2] - bbox[0]
    draw.text(((width - w) / 2, y + 6), subtitle, font=sub_font, fill=(255, 255, 255, 200))

    return img


def _palettes():
    """10 tasteful lavender-family palettes."""
    return [
        ((184, 164, 227), (91, 63, 168)),
        ((232, 214, 240), (146, 110, 190)),
        ((206, 190, 232), (74, 52, 140)),
        ((238, 226, 246), (120, 88, 178)),
        ((199, 182, 230), (66, 46, 125)),
        ((221, 205, 238), (105, 75, 172)),
        ((245, 236, 250), (160, 128, 205)),
        ((176, 156, 222), (58, 40, 112)),
        ((228, 214, 243), (128, 96, 184)),
        ((212, 196, 236), (88, 62, 155)),
    ]


def _save_image(img, name, path):
    from io import BytesIO

    buf = BytesIO()
    img.save(buf, format='JPEG', quality=86)
    return ContentFile(buf.getvalue(), name=name)


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------
class Command(BaseCommand):
    help = 'Load demo categories, products, images, reviews and coupons into the store.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing catalogue data before seeding.')
        parser.add_argument('--with-demo-users', action='store_true',
                            help='Also create demo customer accounts (password: Demo@12345).')

    def handle(self, *args, **options):
        from django.db import transaction

        if options['reset']:
            self._reset()
        elif ProductExists():
            self.stdout.write(self.style.WARNING(
                'Store already has products — nothing to do. '
                'Use --reset to wipe and reseed.'
            ))
            return

        with transaction.atomic():
            reviews = self._seed_categories_and_products()
            self._seed_coupons()
        self._seed_demo_users(options['with_demo_users'])

        self.stdout.write(self.style.SUCCESS(
            'Seeded %d categories and %d products (%d reviews).'
            % (CategoryCount(), ProductCount(), reviews)
        ))
        self.stdout.write('SEED DATA ONLY — replace demo products/images via the Django admin.')

    # -- reset ------------------------------------------------------------
    def _reset(self):
        from catalog.models import Category, ContactMessage, NewsletterSubscriber, Product, ProductReview
        from orders.models import Coupon

        self.stdout.write('Resetting catalogue data…')
        # Generated media files first.
        for folder in ('products', 'categories'):
            root = Path(settings.MEDIA_ROOT) / folder
            if root.exists():
                for f in root.rglob('*'):
                    if f.is_file():
                        f.unlink()
        ProductReview.objects.all().delete()
        Coupon.objects.all().delete()
        ContactMessage.objects.all().delete()
        NewsletterSubscriber.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        self.stdout.write(self.style.WARNING('Deleted products, categories, reviews and coupons.'))

    # -- catalogue --------------------------------------------------------
    def _seed_categories_and_products(self):
        from catalog.models import Category, Product, ProductImage, ProductReview, ProductVariant

        palettes = _palettes()
        review_total = 0
        rng = random.Random(20261012)

        demo_users = []
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for name, phone in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=phone,
                defaults={
                    'first_name': name.split()[0],
                    'last_name': ' '.join(name.split()[1:]),
                    'phone': phone,
                    'email': f'{slugify(name)}@example.com',
                },
            )
            demo_users.append(user)

        for ci, (cat_name, cat_desc) in enumerate(CATEGORIES):
            category, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={
                    'description': cat_desc,
                    'order': ci,
                    'is_active': True,
                },
            )
            if not category.image:
                top, bottom = palettes[ci % len(palettes)]
                img = _gradient_image(600, 600, top, bottom, cat_name, 'VELOURA', variant=ci)
                category.image.save(
                    f'{slugify(cat_name)}.jpg',
                    _save_image(img, f'{slugify(cat_name)}.jpg', 'categories'),
                    save=True,
                )

            for pi, (prod_name, price, discount) in enumerate(PRODUCTS[cat_name]):
                stock_base = rng.randint(4, 14)
                product = Product.objects.create(
                    name=prod_name,
                    category=category,
                    description=textwrap.dedent(f"""\
                        {prod_name} from the Veloura {cat_name} collection.

                        • Premium fabric with a soft, flattering drape
                        • Designed for all-day comfort and effortless style
                        • Pair it with heels for evenings or sneakers for brunch
                        • Machine wash cold, line dry

                        {cat_desc}"""),
                    price=price,
                    discount_percent=discount,
                    stock=0,  # updated after variants are created
                    is_trending=(pi + ci) % 3 == 0,
                    is_seasonal=(ci + pi) % 4 == 0,
                    sales_count=rng.randint(2, 60),
                )

                # Variants: a realistic subset of size × colour combinations.
                colors = rng.sample(COLORS, k=rng.randint(2, 3))
                sizes = SIZES[:rng.randint(3, 5)]
                total_stock = 0
                for color in colors:
                    for size in sizes:
                        if rng.random() < 0.8:
                            vstock = rng.randint(0, 9)
                            ProductVariant.objects.create(
                                product=product, size=size, color=color, stock=vstock,
                            )
                            total_stock += vstock
                Product.objects.filter(pk=product.pk).update(stock=total_stock)
                product.stock = total_stock

                # 3 unique images per product (front / back / detail views).
                views = [('Front view', 'FRONT'), ('Back view', 'BACK'), ('Detail view', 'DETAIL')]
                for order, (label, tag) in enumerate(views):
                    top, bottom = palettes[(ci + pi + order) % len(palettes)]
                    img = _gradient_image(720, 960, top, bottom, prod_name, tag, variant=ci * 10 + pi * 3 + order)
                    ProductImage.objects.create(
                        product=product,
                        display_order=order,
                        alt_text=f'{prod_name} — {label}',
                        image=_save_image(
                            img,
                            f'{slugify(prod_name)}-{order + 1}.jpg',
                            'products',
                        ),
                    )

                # Reviews from demo customers (only where data actually exists).
                if demo_users and (pi + ci) % 2 == 0:
                    for user in rng.sample(demo_users, k=min(len(demo_users), rng.randint(1, 3))):
                        rating, comment = rng.choice(REVIEWS)
                        _, created = ProductReview.objects.get_or_create(
                            product=product, user=user,
                            defaults={'rating': rating, 'comment': comment},
                        )
                        if created:
                            review_total += 1

        return review_total

    # -- coupons ----------------------------------------------------------
    def _seed_coupons(self):
        from orders.models import Coupon

        for code, dtype, value, minimum, desc in COUPONS:
            Coupon.objects.get_or_create(
                code=code,
                defaults={
                    'discount_type': dtype,
                    'value': value,
                    'min_order_amount': minimum,
                    'description': desc,
                    'is_active': True,
                },
            )

    # -- demo users -------------------------------------------------------
    def _seed_demo_users(self, enabled):
        if not enabled:
            self.stdout.write('Tip: run with --with-demo-users to create demo logins.')
            return
        from django.contrib.auth import get_user_model

        User = get_user_model()
        for name, phone in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=phone,
                defaults={
                    'first_name': name.split()[0],
                    'last_name': ' '.join(name.split()[1:]),
                    'phone': phone,
                    'email': f'{slugify(name)}@example.com',
                },
            )
            # Users may already exist from review seeding with an unusable
            # password — always (re)set it so the demo logins really work.
            user.set_password('Demo@12345')
            user.save(update_fields=['password'])
            if created:
                self.stdout.write(f'  demo login: {phone} / Demo@12345  ({name})')


def ProductExists():
    from catalog.models import Product

    return Product.objects.exists()


def CategoryCount():
    from catalog.models import Category

    return Category.objects.count()


def ProductCount():
    from catalog.models import Product

    return Product.objects.count()
