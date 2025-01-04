from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.utils.safestring import mark_safe

from .models import GalleryCategory, GalleryImage, TeamMember


@admin.register(GalleryCategory)
class GalleryCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

    fieldsets = [
        (None, {
            'fields': ('name',),
            'description': (
                'Gallery category, used to filter images')
        }),
    ]


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('category', 'caption_title', 'caption_subtitle', 'image_img', 'display_on_homepage')

    @mark_safe
    def image_img(self,obj):
        if obj.photo:
            return '<img src="%s"  height="60px"/>' % obj.photo.url
        else:
            return '-'
    image_img.short_description = "photo"



@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'image_img')

    @mark_safe
    def image_img(self,obj):
        if obj.photo:
            return '<img src="%s"  height="60px"/>' % obj.photo.url
        else:
            return '-'
    image_img.short_description = "photo"