from django.shortcuts import render

def index(request):
    return render(request, 'website/index.html', {})

def about(request):
    return render(request, 'website/about.html', { 'section': 'about'})

def classes_polefit(request):
    return render(request, 'website/classes_polefit.html', { 'section': 'classes_polefit', 'dd_section': 'class_dd'})

def classes_hoop(request):
    return render(request, 'website/classes_hoop.html', { 'section': 'classes_hoop', 'dd_section': 'class_dd'})

def classes_balletfit(request):
    return render(request, 'website/classes_balletfit.html', { 'section': 'classes_balletfit', 'dd_section': 'class_dd'})

def classes_bouncefit(request):
    return render(request, 'website/classes_bouncefit.html', { 'section': 'classes_bouncefit', 'dd_section': 'class_dd'})

def classes_stretch(request):
    return render(request, 'website/classes_stretch.html', { 'section': 'classes_stretch', 'dd_section': 'class_dd'})

def booking(request):
    return render(request, 'website/booking.html', { 'section': 'booking'})

def instructors(request):
    return render(request, 'website/instructors.html', { 'section': 'instructors'})

def venues(request):
    return render(request, 'website/venues.html', { 'section': 'venues'})

def gallery(request):
    return render(request, 'website/gallery.html', { 'section': 'gallery'})