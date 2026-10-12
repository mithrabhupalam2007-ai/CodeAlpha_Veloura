from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

SIZE_CHOICES = [
    ('XS', 'XS'),
    ('S', 'S'),
    ('M', 'M'),
    ('L', 'L'),
    ('XL', 'XL'),
    ('XXL', 'XXL'),
    ('FREE', 'Free Size'),
]

RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]


class Category(models.Model):
    """A women's clothing category shown with an image icon on the home page."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text='Display order on the home page')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('catalog:category', args=[self.slug])


class Product(models.Model):
    """A single product (e.g. a dress) sold by Veloura."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Original price in INR',
    )
    discount_percent = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Discount percentage (0-100)',
    )
    stock = models.PositiveIntegerField(default=0, help_text='Total stock across all variants')
    is_active = models.BooleanField(default=True)
    is_trending = models.BooleanField(default=False)
    is_seasonal = models.BooleanField(default=False)
    sales_count = models.PositiveIntegerField(default=0, help_text='Units sold — used for popularity sorting')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200] or 'product'
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('catalog:product_detail', args=[self.slug])

    @property
    def discounted_price(self):
        """Price after the discount — what the customer actually pays."""
        price = Decimal(str(self.price))
        if self.discount_percent:
            return (price * (Decimal(100) - self.discount_percent) / Decimal(100)).quantize(Decimal('0.01'))
        return price.quantize(Decimal('0.01'))

    @property
    def discount_amount(self):
        """Absolute rupee saving compared to the original price."""
        return (Decimal(str(self.price)) - self.discounted_price).quantize(Decimal('0.01'))

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def available_sizes(self):
        seen = {v.size for v in self.variants.all() if v.stock > 0}
        order = [c[0] for c in SIZE_CHOICES]
        return sorted(seen, key=lambda s: order.index(s) if s in order else 99)

    @property
    def available_colors(self):
        return sorted({v.color for v in self.variants.all() if v.stock > 0})


class ProductImage(models.Model):
    """One photograph of a product (front, back, side, close-up...)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/%Y/%m/')
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f'Image {self.display_order} of {self.product.name}'

    @property
    def label(self):
        return self.alt_text or f'{self.product.name} view'


class ProductVariant(models.Model):
    """A size + colour combination of a product with its own stock count."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    color = models.CharField(max_length=50)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['product', 'color', 'size']
        constraints = [
            models.UniqueConstraint(fields=['product', 'size', 'color'], name='unique_variant_per_product'),
        ]

    def __str__(self):
        return f'{self.product.name} / {self.size} / {self.color}'

    @property
    def is_in_stock(self):
        return self.stock > 0


class ProductReview(models.Model):
    """A rating + comment left by a verified customer."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['product', 'user'], name='one_review_per_customer'),
        ]

    def __str__(self):
        return f'{self.product.name} — {self.rating}★ by {self.user}'


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    """Messages submitted through the contact form in the footer."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.subject} — {self.email}'
