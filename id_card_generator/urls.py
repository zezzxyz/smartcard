# id_card_generator/urls.py
from django.contrib import admin
from django.urls import path, include
from api.views import index, upload_pdf, upload_pan  # Import the index view
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Include the API URL patterns
    path('accounts/', include('allauth.urls')),
    #path('upload-pdf/', upload_pdf, name='upload_pdf'),
    #path('upload-pan/', upload_pan, name='upload_pan'),
    path('', RedirectView.as_view(url='/accounts/login/')),  # Redirect to login page
    path('dashboard/', RedirectView.as_view(url='/api/dashboard/')),  # Redirect dashboard to api dashboard
    path('', index, name='index'),  # Handle the root URL
]



