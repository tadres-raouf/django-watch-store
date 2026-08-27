from django.utils import timezone
from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Product, Category, Governorate, Order
from .serializers import ProductSerializer, CategorySerializer, GovernorateSerializer, OrderSerializer


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description', 'category__name']

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        category_slug = self.request.query_params.get('category', None)
        is_bestseller_param = self.request.query_params.get('bestseller', None)
        has_offer_param = self.request.query_params.get('has_offer', None)

        if category_slug is not None:
            queryset = queryset.filter(category__slug=category_slug)

        if is_bestseller_param is not None and is_bestseller_param.lower() == 'true':
            queryset = queryset.filter(is_bestseller=True)

        if has_offer_param is not None and has_offer_param.lower() == 'true':
            now = timezone.now()
            from django.db.models import Q
            queryset = queryset.filter(
                # خصم ثابت عادي
                Q(discount_percentage__gt=0) |
                # عرض محدود بوقت نشط حالياً
                Q(
                    offer_discount_percentage__gt=0,
                    offer_start_date__lte=now,
                    offer_end_date__gte=now
                )
            )

        return queryset.order_by('-created_at')


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer


class GovernorateViewSet(viewsets.ModelViewSet):
    queryset = Governorate.objects.all().order_by('id')
    serializer_class = GovernorateSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.action in ['create', 'check_status']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['post'], url_path='check-status')
    def check_status(self, request):
        self.pagination_class = None

        raw_order_ids = request.data.get('order_ids', [])
        if not isinstance(raw_order_ids, list):
            raw_order_ids = [raw_order_ids]

        clean_ids = []
        for oid in raw_order_ids:
            try:
                if oid is not None and str(oid).strip() != '' and str(oid).lower() != 'nan':
                    clean_ids.append(int(oid))
            except (ValueError, TypeError):
                continue

        if not clean_ids:
            return Response({"remove_order_ids": []}, status=status.HTTP_200_OK)

        try:
            completed_order_ids = Order.objects.filter(
                id__in=clean_ids,
                status__in=['Completed', 'completed', 'Cancelled', 'cancelled', 'تم التوصيل بنجاح', 'ملغي']
            ).values_list('id', flat=True)

            return Response({"remove_order_ids": list(completed_order_ids)}, status=status.HTTP_200_OK)

        except Exception as e:
            print("🚨 خطأ داخلي في دالة الفحص:", str(e))
            return Response({"remove_order_ids": []}, status=status.HTTP_200_OK)