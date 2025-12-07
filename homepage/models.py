from django.db import models
from django.utils.translation import gettext_lazy as _
from voice_cloning.compression_utils import compress_image, compress_video


class CarouselSlide(models.Model):
    """Hero carousel slides"""
    title = models.CharField(_('Title'), max_length=300)
    subtitle = models.TextField(_('Subtitle'))
    description = models.TextField(_('Description'), blank=True)
    button_text = models.CharField(_('Button Text'), max_length=100, default='Get Started')
    button_url = models.CharField(_('Button URL'), max_length=200, default='#')
    background_image = models.ImageField(_('Background Image'), upload_to='carousel/', blank=True, null=True)
    background_color = models.CharField(_('Background Color'), max_length=50, default='#000000', help_text='Hex color code')
    text_color = models.CharField(_('Text Color'), max_length=50, default='#ffffff', help_text='Hex color code')
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Carousel Slide')
        verbose_name_plural = _('Carousel Slides')
        ordering = ['order']

    def save(self, *args, **kwargs):
        # Compress background image if uploaded
        if self.background_image and hasattr(self.background_image, 'file'):
            self.background_image = compress_image(self.background_image, quality=90, max_width=1920, max_height=1080)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Slide {self.order}: {self.title[:50]}"


class HeroSection(models.Model):
    """Hero section content"""
    badge_text = models.CharField(_('Badge Text'), max_length=200, default='AI-Powered Voice Technology')
    title = models.CharField(_('Title'), max_length=300, default='Transform Text into Natural, Human-Like Speech')
    subtitle = models.TextField(_('Subtitle'), default='Clone any voice and generate professional-quality speech with our advanced AI technology. Perfect for content creators, businesses, and developers.')
    primary_button_text = models.CharField(_('Primary Button Text'), max_length=100, default='Get Started', blank=True)
    primary_button_url = models.CharField(_('Primary Button URL'), max_length=200, default='#', blank=True)
    secondary_button_text = models.CharField(_('Secondary Button Text'), max_length=100, default='', blank=True)
    secondary_button_url = models.CharField(_('Secondary Button URL'), max_length=200, default='', blank=True)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Hero Section')
        verbose_name_plural = _('Hero Sections')
        ordering = ['order', '-is_active', '-updated_at']

    def __str__(self):
        return f"Hero Section - {self.title[:50]}"


class HeroFeature(models.Model):
    """Features displayed in hero section"""
    hero = models.ForeignKey(HeroSection, on_delete=models.CASCADE, related_name='features')
    text = models.CharField(_('Feature Text'), max_length=200)
    order = models.IntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Hero Feature')
        verbose_name_plural = _('Hero Features')
        ordering = ['order']

    def __str__(self):
        return self.text


class Statistic(models.Model):
    """Platform statistics"""
    icon = models.CharField(_('Font Awesome Icon'), max_length=50, default='fa-users', help_text='e.g., fa-users, fa-microphone')
    number = models.CharField(_('Number'), max_length=50, help_text='e.g., 10M+, 50K+, 99.9%')
    label = models.CharField(_('Label'), max_length=100)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Statistic')
        verbose_name_plural = _('Statistics')
        ordering = ['order']

    def __str__(self):
        return f"{self.number} - {self.label}"


class Feature(models.Model):
    """Main features section"""
    icon = models.CharField(_('Font Awesome Icon'), max_length=50, help_text='e.g., fa-magic, fa-clone')
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Feature')
        verbose_name_plural = _('Features')
        ordering = ['order']

    def __str__(self):
        return self.title


class HowItWorksStep(models.Model):
    """How it works steps"""
    icon = models.CharField(_('Font Awesome Icon'), max_length=50, default='fa-upload', help_text='e.g., fa-upload, fa-magic, fa-download')
    step_number = models.IntegerField(_('Step Number'), default=1)
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('How It Works Step')
        verbose_name_plural = _('How It Works Steps')
        ordering = ['order']

    def __str__(self):
        return f"Step {self.step_number}: {self.title}"


class DemoVoice(models.Model):
    """Demo voices for trying"""
    name = models.CharField(_('Voice Name'), max_length=200, help_text='e.g., Sarah - Female (American)')
    description = models.CharField(_('Description'), max_length=300)
    audio_file = models.FileField(_('Audio File'), upload_to='demo_voices/', blank=True, null=True)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Demo Voice')
        verbose_name_plural = _('Demo Voices')
        ordering = ['order']

    def __str__(self):
        return self.name


class Testimonial(models.Model):
    """Customer testimonials"""
    quote = models.TextField(_('Quote'))
    author_name = models.CharField(_('Author Name'), max_length=200)
    author_title = models.CharField(_('Author Title'), max_length=200)
    author_initials = models.CharField(_('Author Initials'), max_length=3, help_text='e.g., JD')
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Testimonial')
        verbose_name_plural = _('Testimonials')
        ordering = ['order']

    def __str__(self):
        return f"{self.author_name} - {self.author_title}"


class UseCase(models.Model):
    """Use cases carousel"""
    icon = models.CharField(_('Font Awesome Icon'), max_length=50)
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    slide_number = models.IntegerField(_('Slide Number'), default=1, help_text='Which carousel slide (1 or 2)')
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Use Case')
        verbose_name_plural = _('Use Cases')
        ordering = ['slide_number', 'order']

    def __str__(self):
        return self.title


class VideoSection(models.Model):
    """Video demo section"""
    title = models.CharField(_('Title'), max_length=300, default='See It In Action')
    subtitle = models.TextField(_('Subtitle'), default='Watch how easy it is to clone a voice and generate professional audio in minutes')
    video_file = models.FileField(_('Video File'), upload_to='videos/', blank=True, null=True)
    video_thumbnail = models.ImageField(_('Video Thumbnail'), upload_to='video_thumbnails/', blank=True, null=True)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Video Section')
        verbose_name_plural = _('Video Sections')
        ordering = ['order']

    def save(self, *args, **kwargs):
        # Compress video file if uploaded
        if self.video_file and hasattr(self.video_file, 'file'):
            self.video_file = compress_video(self.video_file, target_size_mb=30)

        # Compress thumbnail if uploaded
        if self.video_thumbnail and hasattr(self.video_thumbnail, 'file'):
            self.video_thumbnail = compress_image(self.video_thumbnail, quality=85, max_width=1280, max_height=720)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class VideoFeature(models.Model):
    """Features listed in video section"""
    video_section = models.ForeignKey(VideoSection, on_delete=models.CASCADE, related_name='features')
    text = models.CharField(_('Feature Text'), max_length=300)
    order = models.IntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Video Feature')
        verbose_name_plural = _('Video Features')
        ordering = ['order']

    def __str__(self):
        return self.text


class PricingPlan(models.Model):
    """Pricing preview plans"""
    name = models.CharField(_('Plan Name'), max_length=100)
    price = models.CharField(_('Price'), max_length=50, help_text='e.g., $0, $29')
    period = models.CharField(_('Period'), max_length=50, default='per month')
    description = models.TextField(_('Description'), blank=True, default='')
    button_text = models.CharField(_('Button Text'), max_length=100, default='Get Started')
    button_url = models.CharField(_('Button URL'), max_length=200, default='#')
    is_popular = models.BooleanField(_('Popular/Recommended'), default=False)
    is_featured = models.BooleanField(_('Featured Plan'), default=False)
    badge_text = models.CharField(_('Badge Text'), max_length=50, blank=True, help_text='e.g., Most Popular')
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Pricing Plan')
        verbose_name_plural = _('Pricing Plans')
        ordering = ['order']

    def __str__(self):
        return f"{self.name} - {self.price}"


class PricingFeature(models.Model):
    """Features for each pricing plan"""
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE, related_name='features')
    text = models.CharField(_('Feature Text'), max_length=300)
    order = models.IntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Pricing Feature')
        verbose_name_plural = _('Pricing Features')
        ordering = ['order']

    def __str__(self):
        return f"{self.plan.name}: {self.text}"


class FAQ(models.Model):
    """Frequently asked questions"""
    question = models.CharField(_('Question'), max_length=500)
    answer = models.TextField(_('Answer'))
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQs')
        ordering = ['order']

    def __str__(self):
        return self.question


class TrustBadge(models.Model):
    """Trust indicators/badges"""
    icon = models.CharField(_('Font Awesome Icon'), max_length=50)
    title = models.CharField(_('Title'), max_length=100)
    subtitle = models.CharField(_('Subtitle'), max_length=100)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Trust Badge')
        verbose_name_plural = _('Trust Badges')
        ordering = ['order']

    def __str__(self):
        return f"{self.title} - {self.subtitle}"


class QualityComparison(models.Model):
    """Voice quality comparison points"""
    COMPARISON_TYPE_CHOICES = [
        ('bad', 'Traditional TTS (Bad)'),
        ('good', 'Index-TTS2 AI (Good)'),
    ]

    comparison_type = models.CharField(_('Comparison Type'), max_length=10, choices=COMPARISON_TYPE_CHOICES)
    text = models.CharField(_('Text'), max_length=300)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Quality Comparison Point')
        verbose_name_plural = _('Quality Comparison Points')
        ordering = ['comparison_type', 'order']

    def __str__(self):
        return f"{self.get_comparison_type_display()}: {self.text}"


class LiveStatistic(models.Model):
    """Live statistics with counters"""
    icon = models.CharField(_('Font Awesome Icon'), max_length=50)
    value = models.IntegerField(_('Value'), help_text='The number to count up to')
    label = models.CharField(_('Label'), max_length=200)
    trend_percentage = models.IntegerField(_('Trend Percentage'), default=0)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Live Statistic')
        verbose_name_plural = _('Live Statistics')
        ordering = ['order']

    def __str__(self):
        return f"{self.value:,} - {self.label}"


class APIFeature(models.Model):
    """API section features"""
    icon = models.CharField(_('Font Awesome Icon'), max_length=50)
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('API Feature')
        verbose_name_plural = _('API Features')
        ordering = ['order']

    def __str__(self):
        return self.title


class APISection(models.Model):
    """API section content"""
    title = models.CharField(_('Title'), max_length=300, default='Powerful API for Developers')
    subtitle = models.TextField(_('Subtitle'), default='Integrate voice generation into your applications with our simple REST API')
    code_example = models.TextField(_('Code Example'), help_text='Python or other code example')
    code_language = models.CharField(_('Code Language'), max_length=50, default='Python')
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('API Section')
        verbose_name_plural = _('API Sections')

    def __str__(self):
        return self.title


class LanguageSupport(models.Model):
    """Supported languages showcase"""
    flag_emoji = models.CharField(_('Flag Emoji'), max_length=10, help_text='e.g., 🇺🇸')
    language_name = models.CharField(_('Language Name'), max_length=100)
    description = models.CharField(_('Description'), max_length=300)
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Language Support')
        verbose_name_plural = _('Language Supports')
        ordering = ['order']

    def __str__(self):
        return f"{self.flag_emoji} {self.language_name}"


class CTASection(models.Model):
    """Call to action section"""
    title = models.CharField(_('Title'), max_length=300, default='Ready to Get Started?')
    subtitle = models.TextField(_('Subtitle'), default='Sign up now and get 1,000 free credits plus 1 free voice clone!')
    subtitle_extra = models.CharField(_('Extra Subtitle'), max_length=200, default='No credit card required.', blank=True)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('CTA Section')
        verbose_name_plural = _('CTA Sections')

    def __str__(self):
        return self.title


class CTAFeature(models.Model):
    """Features in CTA section"""
    cta_section = models.ForeignKey(CTASection, on_delete=models.CASCADE, related_name='features')
    icon = models.CharField(_('Font Awesome Icon'), max_length=50)
    text = models.CharField(_('Feature Text'), max_length=300)
    order = models.IntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('CTA Feature')
        verbose_name_plural = _('CTA Features')
        ordering = ['order']

    def __str__(self):
        return self.text
