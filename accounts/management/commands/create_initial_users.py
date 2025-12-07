"""
Django Management Command to Create Initial Users
Creates:
- 2 Superadmins (one visible, one hidden)
- 1 Test user with credits
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import SubscriptionPlan

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates initial users: 2 superadmins and 1 test user'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Creating Initial Users'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Get Free Plan for test user
        try:
            free_plan = SubscriptionPlan.objects.get(plan_type='free')
        except SubscriptionPlan.DoesNotExist:
            self.stdout.write(self.style.ERROR('Free plan not found! Run create_plans.py first.'))
            return

        # 1. Regular Superadmin (Visible)
        self.create_superadmin(
            username='admin',
            email='admin@voiceclone.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            is_hidden=False
        )

        # 2. Hidden Superadmin (Not shown in user lists)
        self.create_superadmin(
            username='superadmin',
            email='superadmin@voiceclone.com',
            password='super123',
            first_name='Super',
            last_name='Admin',
            is_hidden=True
        )

        # 3. Test User
        self.create_test_user(
            username='testuser',
            email='test@voiceclone.com',
            password='test123',
            first_name='Test',
            last_name='User',
            credits=5000,
            subscription_plan=free_plan
        )

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('User Creation Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

    def create_superadmin(self, username, email, password, first_name, last_name, is_hidden=False):
        """Create a superadmin user"""
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'    Superadmin "{username}" already exists'))
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Add hidden attribute if needed
        if is_hidden:
            user.is_hidden = is_hidden
            user.save()

        hidden_text = ' (HIDDEN)' if is_hidden else ''
        self.stdout.write(self.style.SUCCESS(f'[+] Created Superadmin{hidden_text}:'))
        self.stdout.write(f'    Username: {username}')
        self.stdout.write(f'    Email:    {email}')
        self.stdout.write(f'    Password: {password}')
        self.stdout.write(f'    Hidden:   {is_hidden}\n')

    def create_test_user(self, username, email, password, first_name, last_name, credits, subscription_plan):
        """Create a test user with credits"""
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'    Test user "{username}" already exists'))
            return

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        user.credits = credits
        user.subscription_plan = subscription_plan
        user.subscription_type = subscription_plan.plan_type  # Update the CharField that UI displays
        user.save()

        self.stdout.write(self.style.SUCCESS('[+] Created Test User:'))
        self.stdout.write(f'    Username: {username}')
        self.stdout.write(f'    Email:    {email}')
        self.stdout.write(f'    Password: {password}')
        self.stdout.write(f'    Credits:  {credits}')
        self.stdout.write(f'    Plan:     {subscription_plan.name}\n')
