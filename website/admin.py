from django.contrib import admin

from website.models import AboutInfo, PastEvent, Achievement


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 5 #number of default empty fields to show


class PastEventAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [AchievementInline]
    ordering = ['-id']


class AboutInfoAdmin(admin.ModelAdmin):
    list_display = ['get_id', 'heading', 'subheading', 'content']
    ordering = ['id']


admin.site.register(AboutInfo, AboutInfoAdmin)
admin.site.register(PastEvent, PastEventAdmin)
