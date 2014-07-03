from django.contrib import admin

from polefit.website.models import AboutInfo, PastEvent, Achievement


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 5 #number of default empty fields to show

class PastEventAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [AchievementInline]

class AboutInfoAdmin(admin.ModelAdmin):
    list_display = ['heading', 'subheading']


admin.site.register(AboutInfo, AboutInfoAdmin)
admin.site.register(PastEvent, PastEventAdmin)