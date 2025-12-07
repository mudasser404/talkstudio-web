from django.core.management.base import BaseCommand
from homepage.models import (
    HeroSection, HeroFeature, Statistic, Feature, HowItWorksStep,
    DemoVoice, Testimonial, UseCase, VideoSection, VideoFeature,
    PricingPlan, PricingFeature, FAQ, TrustBadge, QualityComparison,
    LiveStatistic, APIFeature, APISection, LanguageSupport,
    CTASection, CTAFeature
)


class Command(BaseCommand):
    help = 'Populates the homepage with initial data'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting to populate homepage data...'))

        # Clear existing data
        self.stdout.write('Clearing existing data...')
        HeroSection.objects.all().delete()
        Statistic.objects.all().delete()
        Feature.objects.all().delete()
        HowItWorksStep.objects.all().delete()
        DemoVoice.objects.all().delete()
        Testimonial.objects.all().delete()
        UseCase.objects.all().delete()
        VideoSection.objects.all().delete()
        PricingPlan.objects.all().delete()
        FAQ.objects.all().delete()
        TrustBadge.objects.all().delete()
        QualityComparison.objects.all().delete()
        LiveStatistic.objects.all().delete()
        APIFeature.objects.all().delete()
        APISection.objects.all().delete()
        LanguageSupport.objects.all().delete()
        CTASection.objects.all().delete()

        # 1. Hero Section
        self.stdout.write('Creating Hero Section...')
        hero = HeroSection.objects.create(
            badge_text='AI-Powered Voice Technology',
            title='Transform Text into Natural, Human-Like Speech',
            subtitle='Clone any voice and generate professional-quality speech with our advanced AI technology. Perfect for content creators, businesses, and developers.',
            is_active=True
        )

        # Hero Features
        HeroFeature.objects.create(hero=hero, text='1,000 free credits', order=1)
        HeroFeature.objects.create(hero=hero, text='1 free voice clone', order=2)
        HeroFeature.objects.create(hero=hero, text='No credit card required', order=3)

        # 2. Statistics
        self.stdout.write('Creating Statistics...')
        Statistic.objects.create(number='10M+', label='Words Generated', order=1, is_active=True)
        Statistic.objects.create(number='50K+', label='Happy Users', order=2, is_active=True)
        Statistic.objects.create(number='100+', label='Voice Options', order=3, is_active=True)
        Statistic.objects.create(number='99.9%', label='Uptime', order=4, is_active=True)

        # 3. Features
        self.stdout.write('Creating Features...')
        features_data = [
            ('fa-magic', 'Text-to-Speech', 'Convert up to 50k characters at once into natural-sounding speech with adjustable parameters.', 1),
            ('fa-clone', 'Talk Studio', 'Upload or record a voice sample and clone it for unlimited text-to-speech generation.', 2),
            ('fa-sliders-h', 'Voice Control', 'Fine-tune speed, pitch, and tone to get the perfect voice output for your needs.', 3),
            ('fa-book', 'Voice Library', 'Access default voices with various male, female accents and languages.', 4),
            ('fa-download', 'Easy Downloads', 'Download generated audio files instantly and manage your voice library.', 5),
            ('fa-shield-alt', 'Secure & Private', 'Your voice data is encrypted and stored securely. Delete anytime.', 6),
        ]
        for icon, title, desc, order in features_data:
            Feature.objects.create(icon=icon, title=title, description=desc, order=order, is_active=True)

        # 4. How It Works
        self.stdout.write('Creating How It Works Steps...')
        steps_data = [
            (1, 'Sign Up Free', 'Create your account and get 1,000 free credits plus 1 free voice clone to start.', 1),
            (2, 'Choose or Clone', 'Select from our voice library or clone your own voice in seconds.', 2),
            (3, 'Generate & Download', 'Enter your text, customize settings, and download high-quality audio instantly.', 3),
        ]
        for num, title, desc, order in steps_data:
            HowItWorksStep.objects.create(step_number=num, title=title, description=desc, order=order, is_active=True)

        # 5. Demo Voices
        self.stdout.write('Creating Demo Voices...')
        voices_data = [
            ('Sarah - Female (American)', 'Professional and friendly voice', 1),
            ('John - Male (British)', 'Clear and authoritative voice', 2),
            ('Emma - Female (Australian)', 'Warm and engaging voice', 3),
        ]
        for name, desc, order in voices_data:
            DemoVoice.objects.create(name=name, description=desc, order=order, is_active=True)

        # 6. Testimonials
        self.stdout.write('Creating Testimonials...')
        testimonials_data = [
            ("This is the best Talk Studio platform I've used. The quality is amazing and the interface is so easy to use!", 'John Doe', 'Content Creator', 'JD', 1),
            ('I use this for my podcast and audiobooks. The Talk Studio feature saved me countless hours of recording.', 'Sarah Miller', 'Podcast Host', 'SM', 2),
            ('Outstanding API and customer support. Perfect for integrating voice generation into our applications.', 'Robert Chen', 'Software Developer', 'RC', 3),
        ]
        for quote, name, title, initials, order in testimonials_data:
            Testimonial.objects.create(quote=quote, author_name=name, author_title=title, author_initials=initials, order=order, is_active=True)

        # 7. Use Cases
        self.stdout.write('Creating Use Cases...')
        use_cases_data = [
            # Slide 1
            ('fa-podcast', 'Podcast Production', 'Create consistent voiceovers for your podcast episodes without recording every time. Perfect for intro/outro segments.', 1, 1),
            ('fa-video', 'Video Content', 'Generate narration for YouTube videos, tutorials, and promotional content with natural-sounding voices.', 1, 2),
            ('fa-book-reader', 'Audiobooks', 'Transform your written content into professional audiobooks with customizable voice characteristics.', 1, 3),
            # Slide 2
            ('fa-bullhorn', 'Advertisements', 'Create engaging voice ads for radio, social media, and digital marketing campaigns quickly and affordably.', 2, 1),
            ('fa-graduation-cap', 'E-Learning', 'Develop educational content with clear, professional narration for online courses and training materials.', 2, 2),
            ('fa-gamepad', 'Gaming', 'Add character voices and narration to your games without expensive voice actor sessions.', 2, 3),
        ]
        for icon, title, desc, slide, order in use_cases_data:
            UseCase.objects.create(icon=icon, title=title, description=desc, slide_number=slide, order=order, is_active=True)

        # 8. Video Section
        self.stdout.write('Creating Video Section...')
        video = VideoSection.objects.create(
            title='See It In Action',
            subtitle='Watch how easy it is to clone a voice and generate professional audio in minutes',
            is_active=True
        )
        video_features = [
            'Upload your voice sample in seconds',
            'AI analyzes and clones your unique voice',
            'Generate unlimited audio with your cloned voice',
            'Download in high-quality WAV format',
        ]
        for idx, text in enumerate(video_features, 1):
            VideoFeature.objects.create(video_section=video, text=text, order=idx)

        # 9. Pricing Plans
        self.stdout.write('Creating Pricing Plans...')

        # Free Plan
        free_plan = PricingPlan.objects.create(
            name='Free',
            price='$0',
            period='Forever',
            is_featured=False,
            order=1,
            is_active=True
        )
        free_features = [
            '1,000 free credits',
            '1 voice clone',
            'Basic audio quality',
            'Community support',
        ]
        for idx, text in enumerate(free_features, 1):
            PricingFeature.objects.create(plan=free_plan, text=text, order=idx)

        # Pro Plan
        pro_plan = PricingPlan.objects.create(
            name='Pro',
            price='$29',
            period='per month',
            is_featured=True,
            badge_text='Most Popular',
            order=2,
            is_active=True
        )
        pro_features = [
            '50,000 credits/month',
            '10 voice clones',
            'HD audio quality',
            'Priority support',
            'Commercial use',
        ]
        for idx, text in enumerate(pro_features, 1):
            PricingFeature.objects.create(plan=pro_plan, text=text, order=idx)

        # Enterprise Plan
        enterprise_plan = PricingPlan.objects.create(
            name='Enterprise',
            price='$99',
            period='per month',
            is_featured=False,
            order=3,
            is_active=True
        )
        enterprise_features = [
            '200,000 credits/month',
            'Unlimited voice clones',
            'Studio audio quality',
            'Dedicated support',
            'API access',
        ]
        for idx, text in enumerate(enterprise_features, 1):
            PricingFeature.objects.create(plan=enterprise_plan, text=text, order=idx)

        # 10. FAQs
        self.stdout.write('Creating FAQs...')
        faqs_data = [
            ('What is talk studio?', 'Talk Studio uses AI to create a digital replica of a voice from audio samples. Once cloned, you can generate speech in that voice by simply typing text.', 1),
            ('How long does it take to clone a voice?', 'Talk Studio typically takes 30-60 seconds. Simply upload a 5-15 second audio sample and our AI will process and clone the voice instantly.', 2),
            ('How many characters can I convert at once?', 'You can convert up to 50,000 characters in a single generation, which is approximately 25-30 pages of text.', 3),
            ('What audio format do I get?', 'All generated audio is provided in high-quality WAV format, which can be easily converted to MP3 or other formats using free tools.', 4),
            ('Can I use the generated audio commercially?', 'Yes! Pro and Enterprise plans include commercial usage rights. Free plan users can upgrade anytime to unlock commercial use.', 5),
            ('Is my data secure?', 'Absolutely. All voice data and generated audio are encrypted and stored securely. You can delete your voice clones and data at any time.', 6),
        ]
        for question, answer, order in faqs_data:
            FAQ.objects.create(question=question, answer=answer, order=order, is_active=True)

        # 11. Trust Badges
        self.stdout.write('Creating Trust Badges...')
        trust_data = [
            ('fa-shield-alt', '99.9%', 'Uptime', 1),
            ('fa-lock', '256-bit', 'Encryption', 2),
            ('fa-check-circle', 'SOC 2', 'Compliant', 3),
            ('fa-certificate', 'GDPR', 'Ready', 4),
            ('fa-headset', '24/7', 'Support', 5),
            ('fa-award', 'ISO', 'Certified', 6),
        ]
        for icon, title, subtitle, order in trust_data:
            TrustBadge.objects.create(icon=icon, title=title, subtitle=subtitle, order=order, is_active=True)

        # 12. Quality Comparison
        self.stdout.write('Creating Quality Comparison...')
        comparison_bad = [
            'Robotic and unnatural tone',
            'Monotone delivery',
            'Poor pronunciation',
            'Limited emotion control',
            'Generic voice options',
        ]
        for idx, text in enumerate(comparison_bad, 1):
            QualityComparison.objects.create(comparison_type='bad', text=text, order=idx, is_active=True)

        comparison_good = [
            'Natural human-like speech',
            'Dynamic emotion control',
            'Perfect pronunciation',
            '8-vector emotion system',
            'Custom Talk Studio',
        ]
        for idx, text in enumerate(comparison_good, 1):
            QualityComparison.objects.create(comparison_type='good', text=text, order=idx, is_active=True)

        # 13. Live Statistics
        self.stdout.write('Creating Live Statistics...')
        live_stats = [
            ('fa-users', 50000, 'Active Users', 12, 1),
            ('fa-microphone-alt', 125000, 'Voices Cloned', 24, 2),
            ('fa-volume-up', 2500000, 'Audio Generated (hrs)', 35, 3),
            ('fa-globe', 150, 'Countries', 8, 4),
        ]
        for icon, value, label, trend, order in live_stats:
            LiveStatistic.objects.create(icon=icon, value=value, label=label, trend_percentage=trend, order=order, is_active=True)

        # 14. API Section
        self.stdout.write('Creating API Section...')
        api_code = '''import requests

# Generate voice
response = requests.post(
    'https://api.example.com/generate',
    headers={'Authorization': 'Bearer YOUR_API_KEY'},
    json={
        'text': 'Hello world!',
        'voice_id': 'your_cloned_voice',
        'emotion': 'happy',
        'speed': 1.0
    }
)

audio_url = response.json()['audio_url']
print(f"Audio ready: {audio_url}")'''

        APISection.objects.create(
            title='Powerful API for Developers',
            subtitle='Integrate voice generation into your applications with our simple REST API',
            code_example=api_code,
            code_language='Python',
            is_active=True
        )

        api_features = [
            ('fa-code', 'RESTful API', 'Simple HTTP endpoints with JSON responses', 1),
            ('fa-book', 'Complete Documentation', 'Detailed guides and code examples', 2),
            ('fa-bolt', 'Fast Response Times', 'Average API response under 200ms', 3),
            ('fa-shield-alt', 'Secure Authentication', 'API keys with rate limiting and HTTPS', 4),
        ]
        for icon, title, desc, order in api_features:
            APIFeature.objects.create(icon=icon, title=title, description=desc, order=order, is_active=True)

        # 15. Language Support
        self.stdout.write('Creating Language Support...')
        languages = [
            ('🇺🇸', 'English', 'Full platform support', 1),
            ('🇸🇦', 'Arabic', 'RTL interface support', 2),
            ('🇵🇰', 'Urdu', 'Complete translation', 3),
            ('🇮🇳', 'Hindi', 'Native language support', 4),
            ('🇧🇩', 'Bengali', 'Fully localized', 5),
            ('🇨🇳', 'Chinese', 'Simplified Chinese', 6),
            ('🇪🇸', 'Spanish', 'Global Spanish', 7),
            ('🇫🇷', 'French', 'Full interface', 8),
            ('🌐', 'More Coming', 'Request your language', 9),
        ]
        for flag, name, desc, order in languages:
            LanguageSupport.objects.create(flag_emoji=flag, language_name=name, description=desc, order=order, is_active=True)

        # 16. CTA Section
        self.stdout.write('Creating CTA Section...')
        cta = CTASection.objects.create(
            title='Ready to Get Started?',
            subtitle='Sign up now and get 1,000 free credits plus 1 free voice clone!',
            subtitle_extra='No credit card required.',
            is_active=True
        )

        cta_features = [
            ('fa-shield-alt', 'Secure payment processing', 1),
            ('fa-lock', 'Your data is encrypted', 2),
            ('fa-headset', '24/7 support', 3),
        ]
        for icon, text, order in cta_features:
            CTAFeature.objects.create(cta_section=cta, icon=icon, text=text, order=order)

        self.stdout.write(self.style.SUCCESS('\n✅ Successfully populated homepage with initial data!'))
        self.stdout.write(self.style.SUCCESS('\nYou can now:'))
        self.stdout.write('  1. Visit http://localhost:8000/admin/ to manage content')
        self.stdout.write('  2. Edit any section through the admin panel')
        self.stdout.write('  3. Upload images and videos')
        self.stdout.write('  4. Reorder items by changing the "Order" field')
        self.stdout.write('  5. Show/hide items using the "Is Active" checkbox\n')
