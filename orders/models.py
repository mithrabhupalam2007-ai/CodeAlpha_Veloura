from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from catalog.models import Product, ProductVariant


class Coupon(models.Model):
    """A discount code customers can apply in the cart."""

    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(
        max_length=10,
        choices=[('percent', 'Percentage'), ('flat', 'Flat amount')],
        default='percent',
    )
    value = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Percent (e.g. 10) or flat INR amount (e.g. 200)',
    )
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Minimum cart subtotal to use this coupon',
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    @property
    def is_currently_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True

    def is_valid_for(self, subtotal):
        """Return (ok, reason) — reason explains why the coupon was rejected."""
        if not self.is_active:
            return False, f'Coupon {self.code} is no longer active.'
        now = timezone.now()
        if now < self.valid_from:
            return False, f'Coupon {self.code} is not active yet.'
        if self.valid_to and now > self.valid_to:
            return False, f'Coupon {self.code} has expired.'
        if subtotal < self.min_order_amount:
            return False, f'Coupon {self.code} needs a minimum order of ₹{self.min_order_amount}.'
        return True, ''

    def discount_for(self, subtotal):
        """Server-calculated discount for a given subtotal."""
        if self.discount_type == 'percent':
            discount = subtotal * Decimal(str(self.value)) / Decimal(100)
        else:
            discount = Decimal(str(self.value))
        discount = discount.quantize(Decimal('0.01'))
        return min(discount, subtotal)


class Order(models.Model):
    """A confirmed customer order with a delivery address snapshot."""

    STATUS_PENDING = 'Pending'
    STATUS_CONFIRMED = 'Confirmed'
    STATUS_PROCESSING = 'Processing'
    STATUS_SHIPPED = 'Shipped'
    STATUS_DELIVERED = 'Delivered'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(
        max_length=20,
        choices=[('cod', 'Cash on Delivery'), ('demo', 'Demo Online Payment')],
        default='cod',
    )
    customer_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order {self.order_number}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_number():
        import secrets

        while True:
            number = 'VL' + timezone.now().strftime('%y%m%d') + secrets.token_hex(3).upper()
            if not Order.objects.filter(order_number=number).exists():
                return number

    @property
    def address_single_line(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.pincode]
        return ', '.join(p for p in parts if p)

    @property
    def can_cancel(self):
        """Customers may cancel while the order is still Pending or Confirmed."""
        return self.status in (self.STATUS_PENDING, self.STATUS_CONFIRMED)

    @property
    def status_step(self):
        """1-based progress used by the status timeline (0 when cancelled)."""
        order = [self.STATUS_PENDING, self.STATUS_CONFIRMED, self.STATUS_PROCESSING,
                 self.STATUS_SHIPPED, self.STATUS_DELIVERED]
        if self.status == self.STATUS_CANCELLED:
            return 0
        return order.index(self.status) + 1


class OrderItem(models.Model):
    """A product line inside an order, with price captured at purchase time."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=200)
    size = models.CharField(max_length=10, blank=True)
    color = models.CharField(max_length=50, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} × {self.product_name}'

    @property
    def line_total(self):
        from decimal import Decimal

        return (self.unit_price * Decimal(self.quantity)).quantize(Decimal('0.01'))


class Payment(models.Model):
    """Payment record for an order. Status only changes on provider/demo confirmation."""

    STATUS_PENDING = 'Pending'
    STATUS_PAID = 'Paid'
    STATUS_FAILED = 'Failed'
    STATUS_REFUNDED = 'Refunded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=[('cod', 'Cash on Delivery'), ('demo', 'Demo Online Payment')])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reference = models.CharField(max_length=100, blank=True)
    is_demo = models.BooleanField(default=False, help_text='True for demo/COD payments — no real money moved')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment {self.order.order_number} — {self.status}'
