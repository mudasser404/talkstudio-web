"""
URL configuration for voice_cloning project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.i18n import set_language
from django.shortcuts import redirect
from homepage.views import (
    HomePageView, LandingPageAdminView,
    CarouselCRUDView, HeroSectionCRUDView, StatisticsCRUDView, FeaturesCRUDView, StepsCRUDView,
    TestimonialsCRUDView, DemoVoicesCRUDView, PricingCRUDView, FAQsCRUDView, UseCasesCRUDView, VideoSectionCRUDView,
    save_carousel_slide, get_carousel_slide, delete_carousel_slide,
    save_hero_section, get_hero_section, delete_hero_section,
    save_statistic, get_statistic, delete_statistic,
    save_feature, get_feature, delete_feature,
    save_step, get_step, delete_step,
    save_testimonial, get_testimonial, delete_testimonial,
    save_demo_voice, get_demo_voice, delete_demo_voice,
    save_pricing_plan, get_pricing_plan, delete_pricing_plan,
    save_faq, get_faq, delete_faq,
    save_usecase, get_usecase, delete_usecase,
    save_video_section, get_video_section, delete_video_section
)
from accounts.views import pricing_page, dashboard_pricing_page
from payments.views import manual_payment_page, manual_payments_admin, my_payment_requests


# Create login-required template views
class ProtectedTemplateView(TemplateView):
    @method_decorator(login_required(login_url='/accounts/login/'))
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


# Clone page view with language context
class ClonePageView(ProtectedTemplateView):
    template_name = 'clone.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.language_models import SupportedLanguage
        # Get only enabled and trained languages
        context['supported_languages'] = SupportedLanguage.objects.filter(
            is_enabled=True,
            is_trained=True
        ).order_by('language_name')
        return context


# API Docs page view with API keys context
class APIDocsPageView(ProtectedTemplateView):
    template_name = 'api_docs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get user's active API keys
        from accounts.models import APIKey
        context['api_keys'] = APIKey.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-created_at')
        return context


# Override admin index to redirect to custom dashboard
def admin_index_redirect(request):
    return redirect('/admin-dashboard/')

# Monkey patch admin site index
original_admin_index = admin.site.index
admin.site.index = admin_index_redirect


urlpatterns = [
    # Language switching endpoints
    path('i18n/', include('django.conf.urls.i18n')),

    # Django Admin
    path('admin/', admin.site.urls),

    # API endpoints (internal - session auth)
    path('api/accounts/', include('accounts.urls')),
    path('api/voices/', include('voices.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/support/', include('support.urls')),
    path('api/tts/', include('tts_engine.urls')),

    # API Key Management (session auth required)
    path('api/keys/', include('accounts.api_urls')),

    # External API endpoints (API key auth)
    path('api/tts/', include('accounts.external_api_urls')),

    # Authentication
    path('api/auth/', include('rest_framework.urls')),
    path('accounts/', include('allauth.urls')),

    # Frontend pages (public)
    path('', HomePageView.as_view(), name='home'),
    path('pricing/', pricing_page, name='pricing'),
    path('test-api/', TemplateView.as_view(template_name='test_api.html'), name='test-api'),

    # Policy Pages (public)
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
    path('refund/', TemplateView.as_view(template_name='refund.html'), name='refund'),
    path('shipping/', TemplateView.as_view(template_name='shipping.html'), name='shipping'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),

    # Protected pages (require login)
    path('dashboard/', ProtectedTemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('dashboard/pricing/', login_required(dashboard_pricing_page), name='dashboard-pricing'),
    path('clone/', ClonePageView.as_view(), name='clone'),
    path('my-voices/', ProtectedTemplateView.as_view(template_name='my_voices.html'), name='my-voices'),
    path('voice-library/', ProtectedTemplateView.as_view(template_name='voice_library.html'), name='voice-library'),
    path('default-voices/', ProtectedTemplateView.as_view(template_name='default_voices.html'), name='default-voices'),
    path('my-audios/', ProtectedTemplateView.as_view(template_name='my_audios.html'), name='my-audios'),
    path('profile/', ProtectedTemplateView.as_view(template_name='profile.html'), name='profile'),
    path('api-docs/', APIDocsPageView.as_view(), name='api-docs'),
    path('admin-dashboard/', ProtectedTemplateView.as_view(template_name='admin_dashboard.html'), name='admin-dashboard'),
    path('model-training/', ProtectedTemplateView.as_view(template_name='model_training.html'), name='model-training'),
    path('language-management/', ProtectedTemplateView.as_view(template_name='language_management.html'), name='language-management'),
    path('landing-page-admin/', LandingPageAdminView.as_view(), name='landing-page-admin'),
    path('activity-logs/', ProtectedTemplateView.as_view(template_name='activity_logs.html'), name='activity-logs'),
    path('platform-settings/', ProtectedTemplateView.as_view(template_name='platform_settings.html'), name='platform-settings'),
    path('support/', ProtectedTemplateView.as_view(template_name='support.html'), name='support'),

    # Payment pages
    path('payments/manual-payment/', login_required(manual_payment_page), name='manual-payment'),
    path('payments/manual-payments-admin/', login_required(manual_payments_admin), name='manual-payments-admin'),
    path('payments/my-payment-requests/', login_required(my_payment_requests), name='my-payment-requests'),

    # Landing Page CRUD Pages
    path('lp-carousel/', CarouselCRUDView.as_view(), name='lp-carousel'),
    path('lp-hero/', HeroSectionCRUDView.as_view(), name='lp-hero'),
    path('lp-statistics/', StatisticsCRUDView.as_view(), name='lp-statistics'),
    path('lp-features/', FeaturesCRUDView.as_view(), name='lp-features'),
    path('lp-steps/', StepsCRUDView.as_view(), name='lp-steps'),
    path('lp-testimonials/', TestimonialsCRUDView.as_view(), name='lp-testimonials'),
    path('lp-demo-voices/', DemoVoicesCRUDView.as_view(), name='lp-demo-voices'),
    path('lp-pricing/', PricingCRUDView.as_view(), name='lp-pricing'),
    path('lp-faqs/', FAQsCRUDView.as_view(), name='lp-faqs'),
    path('lp-usecases/', UseCasesCRUDView.as_view(), name='lp-usecases'),
    path('lp-video/', VideoSectionCRUDView.as_view(), name='lp-video'),

    # Landing Page AJAX Endpoints - Carousel
    path('api/lp-carousel/save/', save_carousel_slide, name='api-save-carousel'),
    path('api/lp-carousel/<int:item_id>/', get_carousel_slide, name='api-get-carousel'),
    path('api/lp-carousel/delete/<int:item_id>/', delete_carousel_slide, name='api-delete-carousel'),

    # Landing Page AJAX Endpoints - Hero Section
    path('api/lp-hero/save/', save_hero_section, name='api-save-hero'),
    path('api/lp-hero/<int:item_id>/', get_hero_section, name='api-get-hero'),
    path('api/lp-hero/delete/<int:item_id>/', delete_hero_section, name='api-delete-hero'),

    # Landing Page AJAX Endpoints - Statistics
    path('api/lp-statistics/save/', save_statistic, name='api-save-statistic'),
    path('api/lp-statistics/<int:item_id>/', get_statistic, name='api-get-statistic'),
    path('api/lp-statistics/delete/<int:item_id>/', delete_statistic, name='api-delete-statistic'),

    # Landing Page AJAX Endpoints - Features
    path('api/lp-features/save/', save_feature, name='api-save-feature'),
    path('api/lp-features/<int:item_id>/', get_feature, name='api-get-feature'),
    path('api/lp-features/delete/<int:item_id>/', delete_feature, name='api-delete-feature'),

    # Landing Page AJAX Endpoints - Steps
    path('api/lp-steps/save/', save_step, name='api-save-step'),
    path('api/lp-steps/<int:item_id>/', get_step, name='api-get-step'),
    path('api/lp-steps/delete/<int:item_id>/', delete_step, name='api-delete-step'),

    # Landing Page AJAX Endpoints - Testimonials
    path('api/lp-testimonials/save/', save_testimonial, name='api-save-testimonial'),
    path('api/lp-testimonials/<int:item_id>/', get_testimonial, name='api-get-testimonial'),
    path('api/lp-testimonials/delete/<int:item_id>/', delete_testimonial, name='api-delete-testimonial'),

    # Landing Page AJAX Endpoints - Demo Voices
    path('api/lp-demo-voices/save/', save_demo_voice, name='api-save-demo-voice'),
    path('api/lp-demo-voices/<int:item_id>/', get_demo_voice, name='api-get-demo-voice'),
    path('api/lp-demo-voices/delete/<int:item_id>/', delete_demo_voice, name='api-delete-demo-voice'),

    # Landing Page AJAX Endpoints - Pricing Plans
    path('api/lp-pricing/save/', save_pricing_plan, name='api-save-pricing'),
    path('api/lp-pricing/<int:item_id>/', get_pricing_plan, name='api-get-pricing'),
    path('api/lp-pricing/delete/<int:item_id>/', delete_pricing_plan, name='api-delete-pricing'),

    # Landing Page AJAX Endpoints - FAQs
    path('api/lp-faqs/save/', save_faq, name='api-save-faq'),
    path('api/lp-faqs/<int:item_id>/', get_faq, name='api-get-faq'),
    path('api/lp-faqs/delete/<int:item_id>/', delete_faq, name='api-delete-faq'),

    # Landing Page AJAX Endpoints - Use Cases
    path('api/lp-usecases/save/', save_usecase, name='api-save-usecase'),
    path('api/lp-usecases/<int:item_id>/', get_usecase, name='api-get-usecase'),
    path('api/lp-usecases/delete/<int:item_id>/', delete_usecase, name='api-delete-usecase'),

    # Landing Page AJAX Endpoints - Video Section
    path('api/lp-video/save/', save_video_section, name='api-save-video'),
    path('api/lp-video/<int:item_id>/', get_video_section, name='api-get-video'),
    path('api/lp-video/delete/<int:item_id>/', delete_video_section, name='api-delete-video'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
