from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from .models import (
    CarouselSlide, HeroSection, HeroFeature, Statistic, Feature, HowItWorksStep,
    DemoVoice, Testimonial, UseCase, VideoSection, VideoFeature,
    PricingPlan, PricingFeature, FAQ, TrustBadge, QualityComparison,
    LiveStatistic, APIFeature, APISection, LanguageSupport,
    CTASection, CTAFeature
)


@admin.register(CarouselSlide)
class CarouselSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'subtitle', 'description')
    list_editable = ('order', 'is_active')
    ordering = ('order',)
    fieldsets = (
        (_('Content'), {
            'fields': ('title', 'subtitle', 'description')
        }),
        (_('Button'), {
            'fields': ('button_text', 'button_url')
        }),
        (_('Design'), {
            'fields': ('background_image', 'background_color', 'text_color')
        }),
        (_('Settings'), {
            'fields': ('order', 'is_active')
        }),
    )


class HeroFeatureInline(admin.TabularInline):
    model = HeroFeature
    extra = 1
    fields = ('text', 'order')


@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'subtitle', 'badge_text')
    inlines = [HeroFeatureInline]
    fieldsets = (
        (_('Content'), {
            'fields': ('badge_text', 'title', 'subtitle')
        }),
        (_('Settings'), {
            'fields': ('is_active',)
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.custom_changelist_view), name='homepage_herosection_changelist'),
        ]
        return custom_urls + urls

    def custom_changelist_view(self, request):
        """Redirect to custom Hero Section landing page"""
        return HttpResponseRedirect('/lp-hero/')


@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ('number', 'label', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('number', 'label')
    list_editable = ('order', 'is_active')
    ordering = ('order',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.custom_changelist_view), name='homepage_statistic_changelist'),
        ]
        return custom_urls + urls

    def custom_changelist_view(self, request):
        """Redirect to custom Statistics landing page"""
        return HttpResponseRedirect('/lp-statistics/')


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    list_editable = ('order', 'is_active')
    ordering = ('order',)
    fieldsets = (
        (_('Content'), {
            'fields': ('icon', 'title', 'description')
        }),
        (_('Settings'), {
            'fields': ('order', 'is_active')
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.custom_changelist_view), name='homepage_feature_changelist'),
        ]
        return custom_urls + urls

    def custom_changelist_view(self, request):
        """Redirect to custom Features landing page"""
        return HttpResponseRedirect('/lp-features/')


@admin.register(HowItWorksStep)
class HowItWorksStepAdmin(admin.ModelAdmin):
    list_display = ('step_number', 'title', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


@admin.register(DemoVoice)
class DemoVoiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    list_editable = ('order', 'is_active')
    ordering = ('order',)
    fieldsets = (
        (_('Content'), {
            'fields': ('name', 'description', 'audio_file')
        }),
        (_('Settings'), {
            'fields': ('order', 'is_active')
        }),
    )


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'author_title', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('author_name', 'author_title', 'quote')
    list_editable = ('order', 'is_active')
    ordering = ('order',)
    fieldsets = (
        (_('Content'), {
            'fields': ('quote',)
        }),
        (_('Author'), {
            'fields': ('author_name', 'author_title', 'author_initials')
        }),
        (_('Settings'), {
            'fields': ('order', 'is_active')
        }),
    )


@admin.register(UseCase)
class UseCaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'slide_number', 'order', 'is_active')
    list_filter = ('slide_number', 'is_active')
    search_fields = ('title', 'description')
    list_editable = ('order', 'is_active')
    ordering = ('slide_number', 'order')
    fieldsets = (
        (_('Content'), {
            'fields': ('icon', 'title', 'description')
        }),
        (_('Settings'), {
            'fields': ('slide_number', 'order', 'is_active')
        }),
    )


class VideoFeatureInline(admin.TabularInline):
    model = VideoFeature
    extra = 1
    fields = ('text', 'order')


@admin.register(VideoSection)
class VideoSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    inlines = [VideoFeatureInline]
    fieldsets = (
        (_('Content'), {
            'fields': ('title', 'subtitle')
        }),
        (_('Media'), {
            'fields': ('video_file', 'video_thumbnail')
        }),
        (_('Settings'), {
            'fields': ('is_active',)
        }),
    )


class PricingFeatureInline(admin.TabularInline):
    model = PricingFeature
    extra = 1
    fields = ('text', 'order')


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'period', 'is_featured', 'order', 'is_active')
    list_filter = ('is_featured', 'is_active')
    search_fields = ('name', 'price')
    list_editable = ('order', 'is_active', 'is_featured')
    ordering = ('order',)
    inlines = [PricingFeatureInline]
    fieldsets = (
        (_('Plan Details'), {
            'fields': ('name', 'price', 'period', 'badge_text')
        }),
        (_('Settings'), {
            'fields': ('is_featured', 'order', 'is_active')
        }),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('question', 'answer')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


@admin.register(TrustBadge)
class TrustBadgeAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'icon', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


@admin.register(QualityComparison)
class QualityComparisonAdmin(admin.ModelAdmin):
    list_display = ('comparison_type', 'text', 'order', 'is_active')
    list_filter = ('comparison_type', 'is_active')
    search_fields = ('text',)
    list_editable = ('order', 'is_active')
    ordering = ('comparison_type', 'order')


@admin.register(LiveStatistic)
class LiveStatisticAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'trend_percentage', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('label',)
    list_editable = ('order', 'is_active')
    ordering = ('order',)
    fieldsets = (
        (_('Content'), {
            'fields': ('icon', 'value', 'label', 'trend_percentage')
        }),
        (_('Settings'), {
            'fields': ('order', 'is_active')
        }),
    )


@admin.register(APIFeature)
class APIFeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


@admin.register(APISection)
class APISectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'code_language', 'is_active')
    fieldsets = (
        (_('Content'), {
            'fields': ('title', 'subtitle')
        }),
        (_('Code Example'), {
            'fields': ('code_language', 'code_example'),
            'description': 'Enter the code example that will be displayed in the API section'
        }),
        (_('Settings'), {
            'fields': ('is_active',)
        }),
    )


@admin.register(LanguageSupport)
class LanguageSupportAdmin(admin.ModelAdmin):
    list_display = ('language_name', 'flag_emoji', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('language_name', 'description')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


class CTAFeatureInline(admin.TabularInline):
    model = CTAFeature
    extra = 1
    fields = ('icon', 'text', 'order')


@admin.register(CTASection)
class CTASectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    inlines = [CTAFeatureInline]
    fieldsets = (
        (_('Content'), {
            'fields': ('title', 'subtitle', 'subtitle_extra')
        }),
        (_('Settings'), {
            'fields': ('is_active',)
        }),
    )
