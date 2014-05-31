from django.shortcuts import render


def booking(request):
    return render(request, 'website/booking.html', { 'section': 'booking'})


def about(request):
    return render(request, 'website/about.html', { 'section': 'about'})
