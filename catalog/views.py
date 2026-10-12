from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ContactForm, NewsletterForm, ProductFilterForm, ReviewForm
from .models import Category, ContactMessage, NewsletterSubscriber, Product, ProductReview

# --------------------------------------------------------------------------
# Static content pages (footer links)
# --------------------------------------------------------------------------
STATIC_PAGES = {
    'about': {
        'title': 'About Veloura',
        'body': [
            'Veloura is a modern women\'s fashion house built on a simple belief — elegance should be accessible.',
            'From flowing dresses and refined workwear to vibrant ethnic pieces, every collection is designed to celebrate women of all ages and styles.',
            'We focus on quality fabrics, thoughtful tailoring and a shopping experience that feels as luxurious as the clothes themselves.',
        ],
    },
    'help': {
        'title': 'Help Center',
        'body': [
            'Ordering: add items to your cart, choose size and colour, then proceed to secure checkout.',
            'Account: sign in with your phone number and password to track orders, manage addresses and view your wishlist.',
            'Payments: Veloura currently supports Cash on Delivery and a demo online payment option. No real charge is made in demo mode.',
            'Still stuck? Reach us at support@veloura.example or +91 98765 43210, Monday to Saturday, 10am–7pm.',
        ],
    },
    'shipping': {
        'title': 'Shipping & Delivery',
        'body': [
            'Orders are dispatched within 1–2 business days and delivered in 3–7 days depending on your location.',
            'Shipping is FREE on all orders above ₹1499. Orders below that carry a flat ₹99 delivery fee.',
            'You will receive order status updates — Pending, Confirmed, Processing, Shipped, Delivered — from your account page.',
        ],
    },
    'returns': {
        'title': 'Returns & Exchanges',
        'body': [
            'Not the right fit? Request a return within 7 days of delivery from your order details page.',
            'Items must be unworn, unwashed and tagged. Once received, refunds are processed to the original payment method within 5–7 business days.',
            'For Cash on Delivery orders, refunds are issued to your bank account via UPI or NEFT.',
        ],
    },
    'privacy': {
        'title': 'Privacy Policy',
        'body': [
            'We collect only the information needed to fulfil your orders: name, phone number, delivery address and order history.',
            'Passwords are stored using Django\'s secure one-way hashing — they are never saved in plain text.',
            'We do not sell your personal data. Payment details are never stored on our servers.',
            'You can request deletion of your account at any time by contacting support@veloura.example.',
        ],
    },
    'terms': {
        'title': 'Terms of Service',
        'body': [
            'By using Veloura you agree to provide accurate account and delivery information.',
            'Product colours may vary slightly due to screen settings; fabric and finish details on each product page are authoritative.',
            'Veloura reserves the right to cancel orders with incorrect pricing or unavailable stock, with a full refund.',
            'These terms are governed by the laws of India.',
        ],
    },
}


def _base_context(request):
    return {
        'categories': Category.objects.filter(is_active=True),
        'newsletter_form': NewsletterForm(),
    }


@login_required
def home(request):
    products = Product.objects.filter(is_active=True)
    context = _base_context(request)
    context.update({
        'new_arrivals': products.order_by('-created_at')[:8],
        'trending': products.filter(is_trending=True)[:8],
        'bestsellers': products.order_by('-sales_count', '-created_at')[:8],
        'seasonal': products.filter(is_seasonal=True)[:8],
        'hero_products': products.order_by('-sales_count')[:4],
    })
    return render(request, 'catalog/home.html', context)


# --------------------------------------------------------------------------
# Shared listing logic: filters, sorting, search
# --------------------------------------------------------------------------
def _build_listing(request, base_queryset, heading, subtitle=''):
    form = ProductFilterForm(request.GET)
    products = base_queryset
    valid = form.is_valid()
    data = form.cleaned_data if valid else {}

    q = data.get('q') or request.GET.get('q', '')
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )

    category_slug = data.get('category') or request.GET.get('category', '')
    category = None
    if category_slug:
        category = Category.objects.filter(slug=category_slug).first()
        if category:
            products = products.filter(category=category)
            if heading == 'Shop':
                heading = category.name

    if data.get('min_price') is not None:
        products = products.filter(price__gte=data['min_price'])
    if data.get('max_price') is not None:
        products = products.filter(price__lte=data['max_price'])
    if data.get('color'):
        products = products.filter(variants__color__iexact=data['color']).distinct()
    if data.get('size'):
        products = products.filter(variants__size=data['size'], variants__stock__gt=0).distinct()
    availability = data.get('availability')
    if availability == 'in':
        products = products.filter(stock__gt=0)
    elif availability == 'out':
        products = products.filter(stock=0)

    # Annotate first so both filtering and sorting can use the same aliases.
    products = products.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True),
        effective_price=ExpressionWrapper(
            F('price') * (100 - F('discount_percent')) / 100,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )

    min_rating = data.get('min_rating')
    if min_rating:
        products = products.filter(avg_rating__gte=min_rating)

    sort = data.get('sort') or request.GET.get('sort', 'newest')
    sorters = {
        'price_asc': 'effective_price',
        'price_desc': '-effective_price',
        'popular': ('-sales_count', '-created_at'),
        'rating': ('-avg_rating', '-review_count'),
        'newest': '-created_at',
    }
    order = sorters.get(sort, '-created_at')
    products = products.order_by(*order) if isinstance(order, tuple) else products.order_by(order)

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)

    # Facet values for filter chips (colours present in this listing)
    colors = (
        base_queryset.filter(is_active=True)
        .values_list('variants__color', flat=True)
        .distinct()
    )
    colors = sorted({c for c in colors if c})

    context = _base_context(request)
    context.update({
        'form': form,
        'filter_errors': form.non_field_errors(),
        'heading': heading,
        'subtitle': subtitle,
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'result_count': paginator.count,
        'active_category': category,
        'filter_colors': colors,
        'q': q,
        'active_sort': sort,
        'filter_query': request.GET.urlencode(),
    })
    return context


@login_required
def shop(request):
    products = Product.objects.filter(is_active=True)
    context = _build_listing(request, products, heading='Shop All')
    return render(request, 'catalog/shop.html', context)


@login_required
def category_listing(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = Product.objects.filter(is_active=True, category=category)
    context = _build_listing(request, products, heading=category.name,
                             subtitle=category.description)
    return render(request, 'catalog/shop.html', context)


@login_required
def search(request):
    return shop(request)


@login_required
def new_arrivals(request):
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    context = _build_listing(request, products, heading='New Arrivals',
                             subtitle='Fresh drops straight from the studio.')
    return render(request, 'catalog/shop.html', context)


@login_required
def trending(request):
    products = Product.objects.filter(is_active=True, is_trending=True)
    context = _build_listing(request, products, heading='Trending Now',
                             subtitle='What everyone is loving this week.')
    return render(request, 'catalog/shop.html', context)


# --------------------------------------------------------------------------
# Product detail
# --------------------------------------------------------------------------
@login_required
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related('images', 'variants', 'reviews__user'),
        slug=slug,
        is_active=True,
    )
    images = list(product.images.all())
    if not images:
        images = []

    reviews = product.reviews.all()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    review_count = reviews.count()
    user_review = None
    if request.user.is_authenticated:
        user_review = ProductReview.objects.filter(product=product, user=request.user).first()

    related = Product.objects.filter(
        is_active=True, category=product.category
    ).exclude(pk=product.pk)[:4]

    context = _base_context(request)
    context.update({
        'product': product,
        'images': images,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'user_review': user_review,
        'review_form': ReviewForm(),
        'related_products': related,
        'sizes': product.available_sizes,
        'colors': product.available_colors,
    })
    return render(request, 'catalog/product_detail.html', context)


@login_required
@require_http_methods(['POST'])
def submit_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    existing = ProductReview.objects.filter(product=product, user=request.user).first()
    form = ReviewForm(request.POST, instance=existing)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        messages.success(request, 'Thank you — your review has been saved.')
    else:
        messages.error(request, 'Please choose a rating and keep your comment within limits.')
    return redirect(product.get_absolute_url() + '#reviews')


# --------------------------------------------------------------------------
# Footer forms: newsletter + contact
# --------------------------------------------------------------------------
@require_http_methods(['POST'])
def newsletter_subscribe(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data['email']
        obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
        if created:
            messages.success(request, 'You are subscribed! Welcome to the Veloura list.')
        else:
            messages.info(request, 'This email is already on the Veloura list.')
    else:
        messages.error(request, 'Please enter a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', '/') or '/')


@login_required
@require_http_methods(['GET', 'POST'])
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Message sent! Our team will reply within 24 hours.')
            return redirect('catalog:contact')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm(initial={'name': request.user.full_name, 'email': request.user.email})
    context = _base_context(request)
    context['form'] = form
    return render(request, 'catalog/contact.html', context)


@login_required
def static_page(request, slug):
    page = STATIC_PAGES.get(slug)
    if page is None:
        raise Http404
    context = _base_context(request)
    context.update({'page': page, 'page_slug': slug})
    return render(request, 'catalog/page.html', context)
