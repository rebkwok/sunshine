from django.shortcuts import render

from gallery.models import Category, Image


def gallery(request):
    categories = Category.objects.all().order_by('name')

    # import ipdb; ipdb.set_trace()
    category_choice = request.GET.getlist('category', ['All'])[0]
    if category_choice == 'All':
        images = Image.objects.all()
        cat_selection = 'All'
    else:
        images = Image.objects.filter(category__id=int(category_choice))
        cat_selection = int(category_choice)

    return render(
        request, 'website/gallery.html',
        {
            'section': 'gallery',
            'cat_selection': cat_selection,
            'categories': categories,
            'images': images,
            'total_image_count': Image.objects.all().count()
            }
    )