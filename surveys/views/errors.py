from django.shortcuts import render


def custom_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    return render(request, 'errors/500.html', status=500)


def custom_502(request):
    return render(request, 'errors/502.html', status=502)


def custom_404_preview(request):
    return render(request, 'errors/404.html', status=404)


