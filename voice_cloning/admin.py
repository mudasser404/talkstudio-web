from django.contrib import admin
from django.shortcuts import redirect


class CustomAdminSite(admin.AdminSite):
    site_header = 'VoiceClone Pro Administration'
    site_title = 'VoiceClone Pro Admin'
    index_title = 'Administration Dashboard'

    def index(self, request, extra_context=None):
        """Redirect admin index to custom dashboard"""
        return redirect('/admin-dashboard/')


# Create instance of custom admin site
admin_site = CustomAdminSite(name='myadmin')
