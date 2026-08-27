from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# 1. Category Table
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم التصنيف")
    slug = models.SlugField(unique=True, allow_unicode=True, blank=True, null=True)

    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"

    def __str__(self):
        return self.name


# 2. Color Table
class Color(models.Model):
    name = models.CharField(max_length=50, verbose_name="اسم اللون")
    hex_code = models.CharField(max_length=7, verbose_name="كود اللون (Hex)")

    class Meta:
        verbose_name = "لون عام"
        verbose_name_plural = "الألوان العامة"

    def __str__(self):
        return self.name


# 3. Product Table
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="التصنيف")
    title = models.CharField(max_length=200, verbose_name="اسم الساعة")
    slug = models.SlugField(unique=True, allow_unicode=True, blank=True, null=True)
    description = models.TextField(verbose_name="الوصف")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر الأصلي")
    discount_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="نسبة الخصم الدائم (%)"
    )
    is_bestseller = models.BooleanField(default=False, verbose_name="الأكثر مبيعاً")
    is_active = models.BooleanField(default=True, verbose_name="نشط / متاح")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    # ========== حقول العروض المحدودة بوقت ==========
    offer_discount_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="نسبة خصم العرض المحدود (%)",
        help_text="نسبة الخصم الخاصة بالعرض، تُطبَّق على السعر الأصلي مباشرةً وليس على سعر الخصم الدائم"
    )
    offer_start_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name="تاريخ ووقت بدء العرض"
    )
    offer_end_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name="تاريخ ووقت انتهاء العرض"
    )

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"

    def __str__(self):
        return self.title

    @property
    def is_offer_active(self):
        """
        حساب ديناميكي 100% — لا يُخزَّن في قاعدة البيانات.
        العرض يكون نشطاً فقط إذا:
        1. offer_discount_percentage > 0
        2. offer_start_date <= now <= offer_end_date
        """
        if not self.offer_discount_percentage:
            return False
        if not self.offer_start_date or not self.offer_end_date:
            return False
        now = timezone.now()
        return self.offer_start_date <= now <= self.offer_end_date


# 4. ProductVariant Table (الربط بين المنتج واللون)
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', verbose_name="المنتج")
    color = models.ForeignKey(Color, on_delete=models.CASCADE, related_name='variants', verbose_name="اللون")
    is_default = models.BooleanField(default=False, verbose_name="اللون الافتراضي للساعة")
    is_active = models.BooleanField(default=True, verbose_name="هذا اللون نشط / متاح في المخزن")

    class Meta:
        verbose_name = "موديل المنتج (Variant)"
        verbose_name_plural = "موديلات المنتجات (Variants)"

    def __str__(self):
        return f"{self.product.title} - {self.color.name}"


# 5. VariantImage Table (الصور الخاصة بكل موديل)
class VariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images', verbose_name="الموديل")
    image = models.ImageField(upload_to='watches/', verbose_name="الصورة")
    is_main = models.BooleanField(default=False, verbose_name="الصورة الرئيسية للموديل")

    class Meta:
        verbose_name = "صورة الموديل"
        verbose_name_plural = "صور الموديلات"


# ==================== الإضافات الجديدة الخاصة بالسيستم التجاري والطلبات ====================

# 6. جدول المحافظات وأسعار الشحن
class Governorate(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="اسم المحافظة")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر الشحن للمحافظة")

    class Meta:
        verbose_name = "محافظة وشحن"
        verbose_name_plural = "إدارة المحافظات والشحن"

    def __str__(self):
        return f"{self.name} ({self.shipping_cost} ج.م)"


# 7. جدول الطلبات الرئيسي
class Order(models.Model):
    ORDER_STATUS = [
        ('Pending', 'قيد المراجعة'),
        ('Completed', 'تم التوصيل بنجاح'),
        ('Cancelled', 'ملغي'),
    ]

    customer_name = models.CharField(max_length=255, verbose_name="اسم العميل (ضروري)")
    phone_number = models.CharField(max_length=20, verbose_name="رقم الهاتف (عليه واتساب)")
    alternate_phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم هاتف إضافي (اختياري)")
    governorate = models.ForeignKey(Governorate, on_delete=models.SET_NULL, null=True, verbose_name="المحافظة")
    shipping_price_at_order = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="تمن الشحن وقت الطلب")
    address_details = models.TextField(verbose_name="العنوان بالتفصيل")

    total_products_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="إجمالي سعر الساعات")
    final_total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر الإجمالي (بالشحن)")

    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='Pending', verbose_name="حالة الطلب")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ ووقت الطلب")

    class Meta:
        verbose_name = "طلب عميل"
        verbose_name_plural = "الطلبات والاوردرات"
        ordering = ['-created_at']

    def __str__(self):
        return f"اوردر #{self.id} - {self.customer_name}"


# 8. جدول تفاصيل الساعات داخل كل طلب
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="الطلب التابع له")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="الساعة")
    product_title = models.CharField(max_length=255, verbose_name="اسم الساعة وقت الشراء")
    color_name = models.CharField(max_length=50, verbose_name="اللون المحدد")
    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية المطلوبة")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر القطعة وقت الشراء")

    class Meta:
        verbose_name = "قطعة داخل الطلب"
        verbose_name_plural = "تفاصيل القطع المطلوبة"

    def __str__(self):
        return f"{self.quantity} x {self.product_title} ({self.color_name})"