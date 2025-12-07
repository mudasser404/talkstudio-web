from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import (
    CarouselSlide, HeroSection, Statistic, Feature, HowItWorksStep,
    DemoVoice, Testimonial, UseCase, VideoSection,
    PricingPlan, FAQ, TrustBadge, QualityComparison,
    LiveStatistic, APIFeature, APISection, LanguageSupport,
    CTASection, HeroFeature, PricingFeature, VideoFeature, CTAFeature
)


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Carousel Slides
        context['carousel_slides'] = CarouselSlide.objects.filter(is_active=True).order_by('order')

        # Hero Section
        try:
            context['hero'] = HeroSection.objects.filter(is_active=True).first()
        except:
            context['hero'] = None

        # Statistics (top section)
        context['statistics'] = Statistic.objects.filter(is_active=True).order_by('order')

        # Features
        context['features'] = Feature.objects.filter(is_active=True).order_by('order')

        # How It Works Steps
        context['how_it_works'] = HowItWorksStep.objects.filter(is_active=True).order_by('order')

        # Demo Voices
        context['demo_voices'] = DemoVoice.objects.filter(is_active=True).order_by('order')

        # Testimonials
        context['testimonials'] = Testimonial.objects.filter(is_active=True).order_by('order')

        # Use Cases (separated by slide)
        use_cases = UseCase.objects.filter(is_active=True).order_by('slide_number', 'order')
        context['use_cases_slide_1'] = use_cases.filter(slide_number=1)
        context['use_cases_slide_2'] = use_cases.filter(slide_number=2)

        # Video Section
        try:
            context['video_section'] = VideoSection.objects.filter(is_active=True).first()
        except:
            context['video_section'] = None

        # Pricing Plans - Use SubscriptionPlan model
        from accounts.models import SubscriptionPlan
        context['pricing_plans'] = SubscriptionPlan.objects.filter(is_active=True).order_by('price')

        # FAQs
        context['faqs'] = FAQ.objects.filter(is_active=True).order_by('order')

        # Trust Badges
        context['trust_badges'] = TrustBadge.objects.filter(is_active=True).order_by('order')

        # Quality Comparison
        context['comparison_bad'] = QualityComparison.objects.filter(
            is_active=True, comparison_type='bad'
        ).order_by('order')
        context['comparison_good'] = QualityComparison.objects.filter(
            is_active=True, comparison_type='good'
        ).order_by('order')

        # Live Statistics
        context['live_statistics'] = LiveStatistic.objects.filter(is_active=True).order_by('order')

        # API Section
        try:
            context['api_section'] = APISection.objects.filter(is_active=True).first()
        except:
            context['api_section'] = None
        context['api_features'] = APIFeature.objects.filter(is_active=True).order_by('order')

        # Language Support
        context['languages'] = LanguageSupport.objects.filter(is_active=True).order_by('order')

        # CTA Section
        try:
            context['cta_section'] = CTASection.objects.filter(is_active=True).first()
        except:
            context['cta_section'] = None

        return context


def is_staff(user):
    return user.is_staff


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class LandingPageAdminView(TemplateView):
    template_name = 'landing_page_admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Count items in each section
        context['hero_count'] = HeroSection.objects.count()
        context['stats_count'] = Statistic.objects.count()
        context['features_count'] = Feature.objects.count()
        context['demo_voices_count'] = DemoVoice.objects.count()
        context['steps_count'] = HowItWorksStep.objects.count()
        context['testimonials_count'] = Testimonial.objects.count()
        context['pricing_count'] = PricingPlan.objects.count()
        context['faqs_count'] = FAQ.objects.count()
        context['usecases_count'] = UseCase.objects.count()
        context['video_count'] = VideoSection.objects.count()

        # Calculate totals
        context['total_sections'] = 17
        context['total_items'] = (
            context['hero_count'] + context['stats_count'] + context['features_count'] +
            context['demo_voices_count'] + context['steps_count'] + context['testimonials_count'] +
            context['pricing_count'] + context['faqs_count'] + context['usecases_count'] +
            context['video_count']
        )

        # Count active sections
        context['active_sections'] = sum([
            1 if HeroSection.objects.filter(is_active=True).exists() else 0,
            1 if Statistic.objects.filter(is_active=True).exists() else 0,
            1 if Feature.objects.filter(is_active=True).exists() else 0,
            1 if DemoVoice.objects.filter(is_active=True).exists() else 0,
            1 if HowItWorksStep.objects.filter(is_active=True).exists() else 0,
            1 if Testimonial.objects.filter(is_active=True).exists() else 0,
            1 if PricingPlan.objects.filter(is_active=True).exists() else 0,
            1 if FAQ.objects.filter(is_active=True).exists() else 0,
            1 if UseCase.objects.filter(is_active=True).exists() else 0,
            1 if VideoSection.objects.filter(is_active=True).exists() else 0,
        ])

        # Count media files
        context['media_files'] = (
            VideoSection.objects.exclude(video_file='').count() +
            DemoVoice.objects.exclude(audio_file='').count()
        )

        # Show setup if no data
        context['show_setup'] = context['total_items'] == 0

        return context


# ============================================
# CRUD VIEWS FOR ALL SECTIONS
# ============================================

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class HeroSectionCRUDView(TemplateView):
    template_name = 'lp_hero_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Hero Sections'
        context['page_description'] = 'Manage main hero banner displayed at the top of landing page'
        context['icon'] = 'fas fa-star'
        context['items'] = HeroSection.objects.all().order_by('order')
        context['total_count'] = HeroSection.objects.count()
        context['active_count'] = HeroSection.objects.filter(is_active=True).count()
        context['inactive_count'] = HeroSection.objects.filter(is_active=False).count()
        context['table_headers'] = ['Badge', 'Title', 'Subtitle']
        context['save_url'] = '/api/lp-hero/save/'
        context['edit_url'] = '/api/lp-hero/'
        context['delete_url'] = '/api/lp-hero/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class StatisticsCRUDView(TemplateView):
    template_name = 'lp_statistics_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Statistics'
        context['page_description'] = 'Manage statistics numbers (10M+, 50K+, etc.)'
        context['icon'] = 'fas fa-chart-line'
        context['items'] = Statistic.objects.all().order_by('order')
        context['total_count'] = Statistic.objects.count()
        context['active_count'] = Statistic.objects.filter(is_active=True).count()
        context['inactive_count'] = Statistic.objects.filter(is_active=False).count()
        context['table_headers'] = ['Icon', 'Number', 'Label']
        context['save_url'] = '/api/lp-statistics/save/'
        context['edit_url'] = '/api/lp-statistics/'
        context['delete_url'] = '/api/lp-statistics/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class FeaturesCRUDView(TemplateView):
    template_name = 'lp_features_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Features'
        context['page_description'] = 'Manage feature cards displayed on landing page'
        context['icon'] = 'fas fa-magic'
        context['items'] = Feature.objects.all().order_by('order')
        context['total_count'] = Feature.objects.count()
        context['active_count'] = Feature.objects.filter(is_active=True).count()
        context['inactive_count'] = Feature.objects.filter(is_active=False).count()
        context['table_headers'] = ['Icon', 'Title', 'Description']
        context['save_url'] = '/api/lp-features/save/'
        context['edit_url'] = '/api/lp-features/'
        context['delete_url'] = '/api/lp-features/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class StepsCRUDView(TemplateView):
    template_name = 'lp_steps_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'How It Works Steps'
        context['page_description'] = 'Manage step-by-step process guide'
        context['icon'] = 'fas fa-tasks'
        context['items'] = HowItWorksStep.objects.all().order_by('order')
        context['total_count'] = HowItWorksStep.objects.count()
        context['active_count'] = HowItWorksStep.objects.filter(is_active=True).count()
        context['inactive_count'] = HowItWorksStep.objects.filter(is_active=False).count()
        context['table_headers'] = ['Icon', 'Title', 'Description']
        context['save_url'] = '/api/lp-steps/save/'
        context['edit_url'] = '/api/lp-steps/'
        context['delete_url'] = '/api/lp-steps/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class TestimonialsCRUDView(TemplateView):
    template_name = 'lp_testimonials_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Testimonials'
        context['page_description'] = 'Manage customer reviews and testimonials'
        context['icon'] = 'fas fa-quote-left'
        context['items'] = Testimonial.objects.all().order_by('order')
        context['total_count'] = Testimonial.objects.count()
        context['active_count'] = Testimonial.objects.filter(is_active=True).count()
        context['inactive_count'] = Testimonial.objects.filter(is_active=False).count()
        context['table_headers'] = ['Author', 'Title', 'Quote']
        context['save_url'] = '/api/lp-testimonials/save/'
        context['edit_url'] = '/api/lp-testimonials/'
        context['delete_url'] = '/api/lp-testimonials/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class PricingCRUDView(TemplateView):
    template_name = 'lp_pricing_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Pricing Plans'
        context['page_description'] = 'Manage pricing plans and features'
        context['icon'] = 'fas fa-dollar-sign'
        context['items'] = PricingPlan.objects.all().order_by('order')
        context['total_count'] = PricingPlan.objects.count()
        context['active_count'] = PricingPlan.objects.filter(is_active=True).count()
        context['inactive_count'] = PricingPlan.objects.filter(is_active=False).count()
        context['table_headers'] = ['Name', 'Price', 'Period']
        context['save_url'] = '/api/lp-pricing/save/'
        context['edit_url'] = '/api/lp-pricing/'
        context['delete_url'] = '/api/lp-pricing/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class DemoVoicesCRUDView(TemplateView):
    template_name = 'lp_demo_voices_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Demo Voices'
        context['page_description'] = 'Manage demo voices with audio samples'
        context['icon'] = 'fas fa-microphone'
        context['items'] = DemoVoice.objects.all().order_by('order')
        context['total_count'] = DemoVoice.objects.count()
        context['active_count'] = DemoVoice.objects.filter(is_active=True).count()
        context['inactive_count'] = DemoVoice.objects.filter(is_active=False).count()
        context['table_headers'] = ['Name', 'Description', 'Audio']
        context['save_url'] = '/api/lp-demo-voices/save/'
        context['edit_url'] = '/api/lp-demo-voices/'
        context['delete_url'] = '/api/lp-demo-voices/delete/'
        context['has_file_upload'] = True  # Special flag for file uploads
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class FAQsCRUDView(TemplateView):
    template_name = 'lp_faqs_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'FAQs'
        context['page_description'] = 'Manage frequently asked questions'
        context['icon'] = 'fas fa-question-circle'
        context['items'] = FAQ.objects.all().order_by('order')
        context['total_count'] = FAQ.objects.count()
        context['active_count'] = FAQ.objects.filter(is_active=True).count()
        context['inactive_count'] = FAQ.objects.filter(is_active=False).count()
        context['table_headers'] = ['Question', 'Answer']
        context['save_url'] = '/api/lp-faqs/save/'
        context['edit_url'] = '/api/lp-faqs/'
        context['delete_url'] = '/api/lp-faqs/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class UseCasesCRUDView(TemplateView):
    template_name = 'lp_usecases_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Use Cases'
        context['page_description'] = 'Manage use case cards in carousel'
        context['icon'] = 'fas fa-lightbulb'
        context['items'] = UseCase.objects.all().order_by('slide_number', 'order')
        context['total_count'] = UseCase.objects.count()
        context['active_count'] = UseCase.objects.filter(is_active=True).count()
        context['inactive_count'] = UseCase.objects.filter(is_active=False).count()
        context['table_headers'] = ['Icon', 'Title', 'Description', 'Slide']
        context['save_url'] = '/api/lp-usecases/save/'
        context['edit_url'] = '/api/lp-usecases/'
        context['delete_url'] = '/api/lp-usecases/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class VideoSectionCRUDView(TemplateView):
    template_name = 'lp_video_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Video Section'
        context['page_description'] = 'Manage video demo section'
        context['icon'] = 'fas fa-video'
        context['items'] = VideoSection.objects.all().order_by('order')
        context['total_count'] = VideoSection.objects.count()
        context['active_count'] = VideoSection.objects.filter(is_active=True).count()
        context['inactive_count'] = VideoSection.objects.filter(is_active=False).count()
        context['table_headers'] = ['Title', 'Subtitle', 'Has Video']
        context['save_url'] = '/api/lp-video/save/'
        context['edit_url'] = '/api/lp-video/'
        context['delete_url'] = '/api/lp-video/delete/'
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class CarouselCRUDView(TemplateView):
    template_name = 'lp_carousel_crud.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Hero Carousel'
        context['page_description'] = 'Manage hero carousel slides at the top of landing page'
        context['icon'] = 'fas fa-images'
        context['items'] = CarouselSlide.objects.all().order_by('order')
        context['total_count'] = CarouselSlide.objects.count()
        context['active_count'] = CarouselSlide.objects.filter(is_active=True).count()
        context['inactive_count'] = CarouselSlide.objects.filter(is_active=False).count()
        context['table_headers'] = ['Title', 'Subtitle', 'Button Text']
        context['save_url'] = '/api/lp-carousel/save/'
        context['edit_url'] = '/api/lp-carousel/'
        context['delete_url'] = '/api/lp-carousel/delete/'
        return context


# ============================================
# AJAX API ENDPOINTS FOR CRUD OPERATIONS
# ============================================

@login_required
@user_passes_test(is_staff)
@require_POST
def save_hero_section(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            hero = get_object_or_404(HeroSection, id=item_id)
        else:
            hero = HeroSection()

        hero.badge_text = request.POST.get('badge_text', '')
        hero.title = request.POST.get('title', '')
        hero.subtitle = request.POST.get('subtitle', '')
        hero.primary_button_text = request.POST.get('primary_button_text', '')
        hero.primary_button_url = request.POST.get('primary_button_url', '')
        hero.secondary_button_text = request.POST.get('secondary_button_text', '')
        hero.secondary_button_url = request.POST.get('secondary_button_url', '')
        hero.order = int(request.POST.get('order', 0))
        hero.is_active = request.POST.get('is_active') == 'on'
        hero.save()

        return JsonResponse({'success': True, 'message': 'Hero section saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_hero_section(request, item_id):
    try:
        hero = get_object_or_404(HeroSection, id=item_id)
        data = {
            'id': hero.id,
            'badge_text': hero.badge_text,
            'title': hero.title,
            'subtitle': hero.subtitle,
            'primary_button_text': hero.primary_button_text,
            'primary_button_url': hero.primary_button_url,
            'secondary_button_text': hero.secondary_button_text,
            'secondary_button_url': hero.secondary_button_url,
            'order': hero.order,
            'is_active': hero.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_hero_section(request, item_id):
    try:
        hero = get_object_or_404(HeroSection, id=item_id)
        hero.delete()
        return JsonResponse({'success': True, 'message': 'Hero section deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_statistic(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            stat = get_object_or_404(Statistic, id=item_id)
        else:
            stat = Statistic()

        stat.icon = request.POST.get('icon', '')
        stat.number = request.POST.get('number', '')
        stat.label = request.POST.get('label', '')
        stat.order = int(request.POST.get('order', 0))
        stat.is_active = request.POST.get('is_active') == 'on'
        stat.save()

        return JsonResponse({'success': True, 'message': 'Statistic saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_statistic(request, item_id):
    try:
        stat = get_object_or_404(Statistic, id=item_id)
        data = {
            'id': stat.id,
            'icon': stat.icon,
            'number': stat.number,
            'label': stat.label,
            'order': stat.order,
            'is_active': stat.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_statistic(request, item_id):
    try:
        stat = get_object_or_404(Statistic, id=item_id)
        stat.delete()
        return JsonResponse({'success': True, 'message': 'Statistic deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_feature(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            feature = get_object_or_404(Feature, id=item_id)
        else:
            feature = Feature()

        feature.icon = request.POST.get('icon', '')
        feature.title = request.POST.get('title', '')
        feature.description = request.POST.get('description', '')
        feature.order = int(request.POST.get('order', 0))
        feature.is_active = request.POST.get('is_active') == 'on'
        feature.save()

        return JsonResponse({'success': True, 'message': 'Feature saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_feature(request, item_id):
    try:
        feature = get_object_or_404(Feature, id=item_id)
        data = {
            'id': feature.id,
            'icon': feature.icon,
            'title': feature.title,
            'description': feature.description,
            'order': feature.order,
            'is_active': feature.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_feature(request, item_id):
    try:
        feature = get_object_or_404(Feature, id=item_id)
        feature.delete()
        return JsonResponse({'success': True, 'message': 'Feature deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_step(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            step = get_object_or_404(HowItWorksStep, id=item_id)
        else:
            step = HowItWorksStep()

        step.icon = request.POST.get('icon', '')
        step.title = request.POST.get('title', '')
        step.description = request.POST.get('description', '')
        step.order = int(request.POST.get('order', 0))
        step.is_active = request.POST.get('is_active') == 'on'
        step.save()

        return JsonResponse({'success': True, 'message': 'Step saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_step(request, item_id):
    try:
        step = get_object_or_404(HowItWorksStep, id=item_id)
        data = {
            'id': step.id,
            'icon': step.icon,
            'title': step.title,
            'description': step.description,
            'order': step.order,
            'is_active': step.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_step(request, item_id):
    try:
        step = get_object_or_404(HowItWorksStep, id=item_id)
        step.delete()
        return JsonResponse({'success': True, 'message': 'Step deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_testimonial(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            testimonial = get_object_or_404(Testimonial, id=item_id)
        else:
            testimonial = Testimonial()

        testimonial.quote = request.POST.get('quote', '')
        testimonial.author_name = request.POST.get('author_name', '')
        testimonial.author_title = request.POST.get('author_title', '')
        testimonial.author_initials = request.POST.get('author_initials', '')
        testimonial.order = int(request.POST.get('order', 0))
        testimonial.is_active = request.POST.get('is_active') == 'on'
        testimonial.save()

        return JsonResponse({'success': True, 'message': 'Testimonial saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_testimonial(request, item_id):
    try:
        testimonial = get_object_or_404(Testimonial, id=item_id)
        data = {
            'id': testimonial.id,
            'quote': testimonial.quote,
            'author_name': testimonial.author_name,
            'author_title': testimonial.author_title,
            'author_initials': testimonial.author_initials,
            'order': testimonial.order,
            'is_active': testimonial.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_testimonial(request, item_id):
    try:
        testimonial = get_object_or_404(Testimonial, id=item_id)
        testimonial.delete()
        return JsonResponse({'success': True, 'message': 'Testimonial deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_pricing_plan(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            plan = get_object_or_404(PricingPlan, id=item_id)
        else:
            plan = PricingPlan()

        plan.name = request.POST.get('name', '')
        plan.price = request.POST.get('price', '')
        plan.period = request.POST.get('period', '')
        plan.description = request.POST.get('description', '')
        plan.button_text = request.POST.get('button_text', '')
        plan.button_url = request.POST.get('button_url', '')
        plan.is_popular = request.POST.get('is_popular') == 'on'
        plan.order = int(request.POST.get('order', 0))
        plan.is_active = request.POST.get('is_active') == 'on'
        plan.save()

        return JsonResponse({'success': True, 'message': 'Pricing plan saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_pricing_plan(request, item_id):
    try:
        plan = get_object_or_404(PricingPlan, id=item_id)
        data = {
            'id': plan.id,
            'name': plan.name,
            'price': plan.price,
            'period': plan.period,
            'description': plan.description,
            'button_text': plan.button_text,
            'button_url': plan.button_url,
            'is_popular': plan.is_popular,
            'order': plan.order,
            'is_active': plan.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_pricing_plan(request, item_id):
    try:
        plan = get_object_or_404(PricingPlan, id=item_id)
        plan.delete()
        return JsonResponse({'success': True, 'message': 'Pricing plan deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_faq(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            faq = get_object_or_404(FAQ, id=item_id)
        else:
            faq = FAQ()

        faq.question = request.POST.get('question', '')
        faq.answer = request.POST.get('answer', '')
        faq.order = int(request.POST.get('order', 0))
        faq.is_active = request.POST.get('is_active') == 'on'
        faq.save()

        return JsonResponse({'success': True, 'message': 'FAQ saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_faq(request, item_id):
    try:
        faq = get_object_or_404(FAQ, id=item_id)
        data = {
            'id': faq.id,
            'question': faq.question,
            'answer': faq.answer,
            'order': faq.order,
            'is_active': faq.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_faq(request, item_id):
    try:
        faq = get_object_or_404(FAQ, id=item_id)
        faq.delete()
        return JsonResponse({'success': True, 'message': 'FAQ deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_demo_voice(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            voice = get_object_or_404(DemoVoice, id=item_id)
        else:
            voice = DemoVoice()

        voice.name = request.POST.get('name', '')
        voice.description = request.POST.get('description', '')
        voice.order = int(request.POST.get('order', 0))
        voice.is_active = request.POST.get('is_active') == 'on'

        # Handle audio file upload
        if 'audio_file' in request.FILES:
            voice.audio_file = request.FILES['audio_file']

        voice.save()

        return JsonResponse({'success': True, 'message': 'Demo voice saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_demo_voice(request, item_id):
    try:
        voice = get_object_or_404(DemoVoice, id=item_id)
        data = {
            'id': voice.id,
            'name': voice.name,
            'description': voice.description,
            'order': voice.order,
            'is_active': voice.is_active,
            'audio_file': voice.audio_file.url if voice.audio_file else '',
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_demo_voice(request, item_id):
    try:
        voice = get_object_or_404(DemoVoice, id=item_id)
        # Delete audio file if exists
        if voice.audio_file:
            voice.audio_file.delete()
        voice.delete()
        return JsonResponse({'success': True, 'message': 'Demo voice deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_usecase(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            usecase = get_object_or_404(UseCase, id=item_id)
        else:
            usecase = UseCase()

        usecase.icon = request.POST.get('icon', '')
        usecase.title = request.POST.get('title', '')
        usecase.description = request.POST.get('description', '')
        usecase.slide_number = int(request.POST.get('slide_number', 1))
        usecase.order = int(request.POST.get('order', 0))
        usecase.is_active = request.POST.get('is_active') == 'on'
        usecase.save()

        return JsonResponse({'success': True, 'message': 'Use case saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_usecase(request, item_id):
    try:
        usecase = get_object_or_404(UseCase, id=item_id)
        data = {
            'id': usecase.id,
            'icon': usecase.icon,
            'title': usecase.title,
            'description': usecase.description,
            'slide_number': usecase.slide_number,
            'order': usecase.order,
            'is_active': usecase.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_usecase(request, item_id):
    try:
        usecase = get_object_or_404(UseCase, id=item_id)
        usecase.delete()
        return JsonResponse({'success': True, 'message': 'Use case deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_video_section(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            video = get_object_or_404(VideoSection, id=item_id)
        else:
            video = VideoSection()

        video.title = request.POST.get('title', '')
        video.subtitle = request.POST.get('subtitle', '')

        if 'video_file' in request.FILES:
            video.video_file = request.FILES['video_file']
        if 'video_thumbnail' in request.FILES:
            video.video_thumbnail = request.FILES['video_thumbnail']

        video.order = int(request.POST.get('order', 0))
        video.is_active = request.POST.get('is_active') == 'on'
        video.save()

        return JsonResponse({'success': True, 'message': 'Video section saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_video_section(request, item_id):
    try:
        video = get_object_or_404(VideoSection, id=item_id)
        data = {
            'id': video.id,
            'title': video.title,
            'subtitle': video.subtitle,
            'has_video': bool(video.video_file),
            'has_thumbnail': bool(video.video_thumbnail),
            'order': video.order,
            'is_active': video.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_video_section(request, item_id):
    try:
        video = get_object_or_404(VideoSection, id=item_id)
        video.delete()
        return JsonResponse({'success': True, 'message': 'Video section deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
@require_POST
def save_carousel_slide(request):
    try:
        item_id = request.POST.get('item_id')
        if item_id:
            slide = get_object_or_404(CarouselSlide, id=item_id)
        else:
            slide = CarouselSlide()

        slide.title = request.POST.get('title', '')
        slide.subtitle = request.POST.get('subtitle', '')
        slide.description = request.POST.get('description', '')
        slide.button_text = request.POST.get('button_text', '')
        slide.button_url = request.POST.get('button_url', '')
        slide.background_color = request.POST.get('background_color', '#000000')
        slide.text_color = request.POST.get('text_color', '#ffffff')

        if 'background_image' in request.FILES:
            slide.background_image = request.FILES['background_image']

        slide.order = int(request.POST.get('order', 0))
        slide.is_active = request.POST.get('is_active') == 'on'
        slide.save()

        return JsonResponse({'success': True, 'message': 'Carousel slide saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff)
def get_carousel_slide(request, item_id):
    try:
        slide = get_object_or_404(CarouselSlide, id=item_id)
        data = {
            'id': slide.id,
            'title': slide.title,
            'subtitle': slide.subtitle,
            'description': slide.description,
            'button_text': slide.button_text,
            'button_url': slide.button_url,
            'background_color': slide.background_color,
            'text_color': slide.text_color,
            'has_background_image': bool(slide.background_image),
            'order': slide.order,
            'is_active': slide.is_active,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def delete_carousel_slide(request, item_id):
    try:
        slide = get_object_or_404(CarouselSlide, id=item_id)
        slide.delete()
        return JsonResponse({'success': True, 'message': 'Carousel slide deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
