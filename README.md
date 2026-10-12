# CodeAlpha_Veloura

**Veloura** — a complete, database-backed women's fashion e-commerce website built with Django.

Elegant, feminine, modern and luxurious fashion for women of all ages, with a premium
lavender-and-white design and a functional end-to-end shopping experience.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript + Django templates |
| Backend | Python with Django 4.2 LTS |
| Database | SQLite (development) → PostgreSQL ready (production) |
| Auth | Django authentication (phone number + password) |
| Media | Django media storage (Pillow) |

No React, no Node.js, no frontend frameworks — every page is rendered by Django
from real database data.

## Features

- **Sign-in gate** — visitors register/sign in with phone number + password before browsing
- **Home page** — hero banner, category icon navigation, new arrivals, trending,
  best sellers, seasonal collections, promotional banners, newsletter signup
- **14 product categories** — Dresses, Tops, Shirts, Jeans, Skirts, Ethnic Wear,
  Kurtis, Co-ord Sets, Party Wear, Casual Wear, Office Wear, Winter Wear,
  Jumpsuits, Activewear
- **Catalog** — filters (category, price, colour, size, rating, availability),
  sorting (price, newest, popularity), and search across name/category/description
- **Product detail** — multi-image gallery with thumbnails, size/colour selection,
  size guide, quantity selector, reviews, related products
- **Cart** — variant-aware, server-validated stock and prices, coupon codes
- **Checkout** — address form, server-side totals, COD + demo online payment,
  unique order numbers, atomic stock decrement
- **Orders** — confirmation page, history, detail with status timeline,
  cancellation with stock restoration
- **Wishlist** — save, move to cart, remove (persisted per account)
- **Profile menu** — My Orders, Coupons, Payments, Manage Account, Wishlist,
  Settings, Logout
- **Django Admin** — full catalogue, image, inventory, order, coupon and review management
- **Security** — CSRF protection, hashed passwords, server-side validation,
  ownership checks on orders, session-based secrets

## Quick start

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Load seed data (demo catalogue, images, coupons, reviews)
python manage.py seed_catalog --with-demo-users

# 5. Create an administrator account
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** — you'll see the sign-in page.
Open **http://127.0.0.1:8000/admin/** for the admin dashboard.

### Demo accounts (after seeding with `--with-demo-users`)

| Phone | Password |
|---|---|
| 9000000001 | `Demo@12345` |
| 9000000002 | `Demo@12345` |
| 9000000003 | `Demo@12345` |

### Coupons (seeded)

| Code | Discount |
|---|---|
| `WELCOME10` | 10% off any order |
| `FLAT200` | ₹200 off orders above ₹1999 |
| `FESTIVE25` | 25% off orders above ₹2999 |

## Adding products and images

1. Sign in to `/admin/` with your superuser account.
2. **Catalog → Categories**: add a category (name, slug, description, image).
3. **Catalog → Products**: add a product with price, discount and stock.
4. On the product page, upload **multiple images** (inline) and define
   **variants** (size × colour × stock) inline.
5. Toggle *Is active*, *Is trending* or *Is seasonal* to feature it on the home page.

> **Seed vs production data:** everything created by `seed_catalog` is demo
> content — generated placeholder images, sample names and placeholder reviews.
> Use `python manage.py seed_catalog --reset` to wipe and reload it, and replace
> it with real products before going live.

## Running tests

```bash
python manage.py test
```

64 tests cover authentication, access control, search/filter/sorting, cart
operations, stock validation, coupon maths, order creation, cancellation and
cross-user ownership checks.

## Project structure

```
config/          settings, root URLs, WSGI
accounts/        custom User (unique phone), addresses, auth views
catalog/         categories, products, images, variants, reviews, home/shop
cart/            cart + cart items, server-side price validation
wishlist/        per-user wishlist
orders/          coupons, orders, order items, payments, checkout
templates/       all Django templates
static/          CSS, JavaScript, images
media/           uploaded & generated product images (gitignored)
requirements.txt
.gitignore
```

## Production notes

Sensitive settings come from environment variables — set these before deploying:

```bash
export DJANGO_SECRET_KEY='generate-a-real-secret'
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS='yourdomain.com'
```

With `DJANGO_DEBUG=False`, HTTPS redirect, secure cookies, HSTS and XSS
protection are enabled automatically. To move to PostgreSQL, replace the
`DATABASES` block in `config/settings.py` with a `django.db.backends.postgresql`
engine — the models and migrations work unchanged.

Online payments are clearly labelled as **demo**; only Cash on Delivery is
functional until a real payment provider is integrated. Never claim a payment
succeeded unless the provider confirms it.
