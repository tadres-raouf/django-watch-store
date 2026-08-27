from rest_framework import serializers
from django.utils import timezone
from .models import Category, Color, Product, ProductVariant, VariantImage, Governorate, Order, OrderItem


class VariantImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantImage
        fields = ['id', 'image', 'is_main']


class ProductVariantSerializer(serializers.ModelSerializer):
    color_name = serializers.CharField(source='color.name', read_only=True)
    hex_code = serializers.CharField(source='color.hex_code', read_only=True)
    images = VariantImageSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'color_name', 'hex_code', 'is_default', 'is_active', 'images']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.ReadOnlyField(source='category.slug')
    variants = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    is_offer_active = serializers.SerializerMethodField()
    offer_discount_percentage = serializers.IntegerField(read_only=True)
    offer_end_date = serializers.DateTimeField(read_only=True)
    offer_label_days = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'category_name', 'category_slug', 'title', 'slug', 'description',
            'price', 'discount_percentage', 'final_price',
            'is_bestseller', 'is_active', 'created_at', 'variants',
            'is_offer_active', 'offer_discount_percentage', 'offer_end_date', 'offer_label_days',
        ]

    def get_variants(self, obj):
        active_variants = obj.variants.filter(is_active=True)
        return ProductVariantSerializer(active_variants, many=True).data

    def get_final_price(self, obj):
        if obj.is_offer_active:
            discount_amount = (obj.price * obj.offer_discount_percentage) / 100
            return float(round(obj.price - discount_amount, 2))
        if obj.discount_percentage > 0:
            discount_amount = (obj.price * obj.discount_percentage) / 100
            return float(round(obj.price - discount_amount, 2))
        return float(obj.price)

    def get_is_offer_active(self, obj):
        return obj.is_offer_active

    def get_offer_label_days(self, obj):
        if not obj.is_offer_active:
            return None
        delta = obj.offer_end_date - obj.offer_start_date
        total_days = round(delta.total_seconds() / 86400)
        return total_days

    def validate(self, data):
        offer_discount = data.get('offer_discount_percentage', getattr(self.instance, 'offer_discount_percentage', 0))
        offer_start = data.get('offer_start_date', getattr(self.instance, 'offer_start_date', None))
        offer_end = data.get('offer_end_date', getattr(self.instance, 'offer_end_date', None))

        if (offer_start or offer_end) and not offer_discount:
            raise serializers.ValidationError({
                "offer_discount_percentage": "⚠️ يجب تحديد نسبة خصم العرض إذا قمت بتحديد تاريخ بداية أو نهاية العرض."
            })

        if offer_discount and not (offer_start and offer_end):
            raise serializers.ValidationError({
                "offer_start_date": "⚠️ يجب تحديد تاريخ بداية ونهاية العرض إذا قمت بتحديد نسبة خصم العرض."
            })

        if offer_start and offer_end and offer_end <= offer_start:
            raise serializers.ValidationError({
                "offer_end_date": "⚠️ تاريخ انتهاء العرض يجب أن يكون بعد تاريخ البداية."
            })

        if offer_end and offer_end <= timezone.now():
            raise serializers.ValidationError({
                "offer_end_date": "⚠️ تاريخ انتهاء العرض يجب أن يكون في المستقبل."
            })

        return data


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class GovernorateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Governorate
        fields = ['id', 'name', 'shipping_cost']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_title', 'color_name', 'quantity', 'price_per_unit']
        read_only_fields = ['product_title', 'price_per_unit']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)
    order_items = OrderItemSerializer(many=True, read_only=True, source='items')
    governorate_name = serializers.CharField(source='governorate.name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'phone_number', 'alternate_phone_number',
            'governorate', 'governorate_name', 'address_details', 'shipping_price_at_order',
            'total_products_price', 'final_total_price', 'status', 'created_at', 'items', 'order_items'
        ]
        read_only_fields = ['shipping_price_at_order', 'total_products_price', 'final_total_price', 'status', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        governorate = validated_data.get('governorate')

        shipping_cost = governorate.shipping_cost if governorate else 0

        validated_data['shipping_price_at_order'] = shipping_cost
        validated_data['total_products_price'] = 0
        validated_data['final_total_price'] = 0

        order = Order.objects.create(**validated_data)
        total_products_price = 0

        for item in items_data:
            product_obj = item['product']
            quantity = item['quantity']
            color_name = item['color_name']

            # ✅ نفس أولوية get_final_price بالظبط: العرض النشط أولاً ثم الخصم الدائم
            if product_obj.is_offer_active:
                discount_amount = (product_obj.price * product_obj.offer_discount_percentage) / 100
                final_unit_price = round(product_obj.price - discount_amount, 2)
            elif product_obj.discount_percentage > 0:
                discount_amount = (product_obj.price * product_obj.discount_percentage) / 100
                final_unit_price = round(product_obj.price - discount_amount, 2)
            else:
                final_unit_price = product_obj.price

            item_total_price = final_unit_price * quantity
            total_products_price += item_total_price

            OrderItem.objects.create(
                order=order,
                product=product_obj,
                product_title=product_obj.title,
                color_name=color_name,
                quantity=quantity,
                price_per_unit=final_unit_price
            )

        order.total_products_price = total_products_price
        order.final_total_price = total_products_price + shipping_cost
        order.save()

        return order