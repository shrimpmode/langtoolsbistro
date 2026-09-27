from django.contrib import admin

from .models import LoginCode, MockEmail

admin.site.register(LoginCode)
admin.site.register(MockEmail)
