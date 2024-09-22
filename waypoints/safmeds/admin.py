from django.contrib import admin

# Register your models here.
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.utils.crypto import get_random_string
from authtools.admin import NamedUserAdmin
from safmeds.forms import *
from safmeds.models import *

User = get_user_model()

class UserAdmin(NamedUserAdmin):
    add_form = AdminUserCreationForm
    add_fieldsets = (
        (None, {
            'description': (
                "Enter the new user's name and email address and click save."
            ),
            'fields': ('email', 'name',),
        }),
        ('Password', {
            'description': "Optionally, you may set the user's password here.",
            'fields': ('password1', 'password2'),
            'classes': ('collapse', 'collapse-closed'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and (not form.cleaned_data['password1'] or not obj.has_usable_password()):
            # Django's PasswordResetForm won't let us reset an unusable
            # password. We set it above super() so we don't have to save twice.
            obj.set_unusable_password()

        super(UserAdmin, self).save_model(request, obj, form, change)

class CardAdmin(admin.ModelAdmin):
    search_fields = ['term', 'definition']

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Deck)
admin.site.register(Card, CardAdmin)