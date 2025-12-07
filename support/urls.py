from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupportTicketViewSet, SupportFAQViewSet, get_support_status, set_support_status

router = DefaultRouter()
router.register(r'tickets', SupportTicketViewSet, basename='support-ticket')
router.register(r'faqs', SupportFAQViewSet, basename='support-faq')

urlpatterns = [
    path('', include(router.urls)),
    path('status/', get_support_status, name='support-status-get'),
    path('status/set/', set_support_status, name='support-status-set'),
]
