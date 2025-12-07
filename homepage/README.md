# Homepage Dynamic Content Management

## Overview
This app provides a complete Content Management System (CMS) for the landing page. Admin users can manage all sections, text, images, and videos through the Django admin panel without touching any code.

## Features
- **Fully Dynamic**: All landing page content is stored in the database
- **Easy to Use**: Manage everything through Django admin panel
- **Multilingual Ready**: All text fields support Django's i18n translation
- **Media Support**: Upload images and videos
- **Order Management**: Drag and drop ordering for all sections
- **Active/Inactive Toggle**: Show or hide sections without deleting them

## Installation & Setup

### 1. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Superuser (if you haven't already)
```bash
python manage.py createsuperuser
```

### 3. Populate Initial Data
```bash
python manage.py populate_homepage
```

This command will create all the default content for your landing page with sample data.

### 4. Access Django Admin
1. Start your development server: `python manage.py runserver`
2. Go to: `http://localhost:8000/admin/`
3. Login with your superuser credentials
4. Navigate to "Homepage Content Management" section

## Admin Panel Sections

### Hero Section
**Location**: Hero Section
- Manage the main hero section at the top of the page
- Fields:
  - Badge Text (e.g., "AI-Powered Voice Technology")
  - Title (Main headline)
  - Subtitle (Description text)
  - Hero Features (inline - add multiple features like "1,000 free credits")

### Statistics
**Location**: Statistics
- The 4 stats shown below the hero (10M+ Words, 50K+ Users, etc.)
- Fields: Number, Label, Order

### Features
**Location**: Features
- Main features section (6 feature cards)
- Fields: Icon (Font Awesome class), Title, Description, Order

### How It Works
**Location**: How It Works Steps
- 3-step process explanation
- Fields: Step Number, Title, Description, Order

### Demo Voices
**Location**: Demo Voices
- Voice samples users can play
- Fields: Name, Description, Audio File (optional), Order

### Testimonials
**Location**: Testimonials
- Customer testimonials
- Fields: Quote, Author Name, Author Title, Author Initials, Order

### Use Cases
**Location**: Use Cases
- Carousel with use case cards
- Fields: Icon, Title, Description, Slide Number (1 or 2), Order
- Note: Slide Number determines which carousel slide the card appears on

### Video Section
**Location**: Video Section
- Video demo section
- Fields:
  - Title, Subtitle
  - Video File (upload MP4)
  - Video Thumbnail (optional)
  - Video Features (inline - list of features)

### Pricing Plans
**Location**: Pricing Plans
- Pricing preview cards
- Fields:
  - Name, Price, Period
  - Is Featured (highlights the plan)
  - Badge Text (e.g., "Most Popular")
  - Features (inline - add pricing features)

### FAQs
**Location**: FAQs
- Frequently asked questions
- Fields: Question, Answer, Order

### Trust Badges
**Location**: Trust Badges
- Security/trust indicators (99.9% Uptime, SOC 2, etc.)
- Fields: Icon, Title, Subtitle, Order

### Quality Comparison
**Location**: Quality Comparison Points
- Side-by-side comparison (Traditional TTS vs Index-TTS2)
- Fields: Comparison Type (Bad/Good), Text, Order

### Live Statistics
**Location**: Live Statistics
- Animated counter statistics
- Fields: Icon, Value (number), Label, Trend Percentage, Order

### API Section
**Location**: API Section
- Developer API showcase
- Fields:
  - Title, Subtitle
  - Code Example (paste code)
  - Code Language
- Also manage API Features separately (4 feature points)

### Language Support
**Location**: Language Support
- Languages supported by platform
- Fields: Flag Emoji, Language Name, Description, Order

### CTA Section
**Location**: CTA Section
- Final call-to-action section
- Fields:
  - Title, Subtitle, Extra Subtitle
  - CTA Features (inline - 3 features with icons)

## Usage Tips

### Reordering Items
1. Items are displayed based on their "Order" field
2. Lower numbers appear first
3. You can bulk edit order values from the list view

### Showing/Hiding Content
- Use the "Is Active" checkbox to show/hide items
- Inactive items are not displayed on the website
- This is useful for temporarily hiding content without deleting it

### Uploading Media
1. Click on the file upload field
2. Select your image/video
3. Files are stored in `media/` directory
4. Supported formats:
   - Images: JPG, PNG, GIF, WebP
   - Videos: MP4, WebM
   - Audio: MP3, WAV, OGG

### Font Awesome Icons
- Use Font Awesome class names (e.g., `fa-magic`, `fa-clone`, `fa-users`)
- View all icons at: https://fontawesome.com/icons
- Format: `fa-icon-name` or `fas fa-icon-name`

### Featured Items
- Pricing plans can be marked as "Featured"
- Featured items get special styling (highlighted, larger, etc.)
- Only one item should typically be featured per section

## Best Practices

### Content Guidelines
1. **Keep titles concise**: 50-70 characters max
2. **Descriptions should be clear**: 150-200 characters optimal
3. **Use active voice**: "Generate voice" not "Voice can be generated"
4. **Be consistent**: Use same terminology throughout

### Image/Video Guidelines
1. **Hero images**: 1920x1080px minimum
2. **Thumbnails**: 800x600px minimum
3. **Videos**: MP4 format, H.264 codec, max 50MB
4. **Optimize images**: Use tools like TinyPNG before uploading
5. **Alt text**: Always provide descriptive alt text

### Performance
1. **Limit active items**: Too many items can slow page load
2. **Optimize media**: Compress images and videos
3. **Use CDN**: Consider using a CDN for media files in production

## Customization

### Adding New Fields
1. Edit `homepage/models.py`
2. Add your new field
3. Run migrations: `python manage.py makemigrations && python manage.py migrate`
4. Update `homepage/admin.py` if needed
5. Update template to use new field

### Adding New Sections
1. Create new model in `homepage/models.py`
2. Register in `homepage/admin.py`
3. Add to view context in `homepage/views.py`
4. Update template in `templates/home.html`

## Troubleshooting

### Admin panel not showing homepage sections
- Check that 'homepage' is in INSTALLED_APPS in settings.py
- Run migrations: `python manage.py migrate`

### Changes not appearing on website
- Clear browser cache (Ctrl+Shift+R)
- Check "Is Active" checkbox is enabled
- Verify item has correct order value

### Media files not displaying
- Check MEDIA_URL and MEDIA_ROOT in settings.py
- Ensure media files are being served in development
- Check file permissions

### Translations not working
- Run `python manage.py makemessages -l LANG_CODE`
- Translate strings in .po files
- Run `python manage.py compilemessages`

## Support
For issues or questions, please contact the development team or refer to Django documentation.
