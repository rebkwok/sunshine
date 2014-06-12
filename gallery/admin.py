from django.contrib import admin

from gallery.models import Category, Image


class ImageInline(admin.TabularInline):
    model = Image
    extra = 5 #number of default empty fields to show

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

    inlines = [ImageInline]

admin.site.register(Category, CategoryAdmin)
