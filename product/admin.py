from django.contrib import admin
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
import nested_admin
from .models import Category, Color, Product, ProductVariant, VariantImage, Governorate, Order, OrderItem


class VariantImageInline(nested_admin.NestedStackedInline):
    model = VariantImage
    extra = 1
    fk_name = 'variant'


class ProductVariantInline(nested_admin.NestedTabularInline):
    model = ProductVariant
    extra = 1
    fk_name = 'product'
    fields = ['color', 'is_default', 'is_active']
    inlines = [VariantImageInline]


class ProductAdminForm(forms.ModelForm):
    """
    فورم مخصص للمنتج بالـ Validation الخاص بحقول العرض
    بيمنع السيف لو في تناقض في بيانات العرض
    """
    class Meta:
        model = Product
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        offer_discount = cleaned_data.get('offer_discount_percentage', 0)
        offer_start = cleaned_data.get('offer_start_date')
        offer_end = cleaned_data.get('offer_end_date')

        # لو حط تواريخ من غير نسبة خصم
        if (offer_start or offer_end) and not offer_discount:
            raise ValidationError(
                "⚠️ لا يمكن حفظ العرض: يجب تحديد نسبة خصم العرض إذا قمت بتحديد تاريخ بداية أو نهاية."
            )

        # لو حط نسبة من غير تواريخ
        if offer_discount and not (offer_start and offer_end):
            raise ValidationError(
                "⚠️ لا يمكن حفظ العرض: يجب تحديد تاريخ بداية ونهاية العرض إذا قمت بتحديد نسبة الخصم."
            )

        # لو تاريخ النهاية قبل أو مساوي للبداية
        if offer_start and offer_end and offer_end <= offer_start:
            raise ValidationError(
                "⚠️ تاريخ انتهاء العرض يجب أن يكون بعد تاريخ البداية."
            )

        # لو تاريخ النهاية في الماضي
        if offer_end and offer_end <= timezone.now():
            raise ValidationError(
                "⚠️ تاريخ انتهاء العرض يجب أن يكون في المستقبل."
            )

        return cleaned_data


@admin.register(Product)
class ProductAdmin(nested_admin.NestedModelAdmin):
    form = ProductAdminForm
    list_display = [
        'id', 'title', 'category', 'price',
        'discount_percentage',
        'offer_discount_percentage',
        'offer_start_date', 'offer_end_date',
        'is_bestseller', 'is_active', 'created_at'
    ]
    list_filter = ['category', 'is_bestseller', 'is_active']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_bestseller', 'is_active', 'discount_percentage']
    inlines = [ProductVariantInline]

    fieldsets = (
        ("معلومات المنتج الأساسية", {
            'fields': (
                'category', 'title', 'slug', 'description',
                'price', 'discount_percentage', 'is_bestseller', 'is_active'
            )
        }),
        ("🔥 إعدادات العرض المحدود بوقت (اختياري)", {
            'fields': ('offer_discount_percentage', 'offer_start_date', 'offer_end_date'),
            'description': (
                "⚠️ الثلاثة حقول مرتبطة ببعض: إما تملأهم كلهم أو تسيبهم فاضيين. "
                "نسبة الخصم تُطبَّق على السعر الأصلي مباشرةً. "
                "العرض ينتهي تلقائياً عند تجاوز تاريخ الانتهاء."
            ),
            'classes': ('collapse',),
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_title', 'color_name', 'quantity', 'price_per_unit']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'phone_number', 'governorate', 'final_total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'governorate']
    search_fields = ['customer_name', 'phone_number']
    list_editable = ['status']
    inlines = [OrderItemInline]


@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'shipping_cost']
    list_editable = ['shipping_cost']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'hex_code']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug']
    prepopulated_fields = {'slug': ('name',)}