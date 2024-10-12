#id_card_generator/api/urls.py
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import VendorViewSet, IDCardViewSet, TransactionViewSet, PrinterViewSet, PhotoEnhancementViewSet, dashboard, wallet, id_card_input, id_card_output, test_view

router = DefaultRouter()
router.register(r'vendors', VendorViewSet)
router.register(r'idcards', IDCardViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'printers', PrinterViewSet, basename='printer')
router.register(r'photoenhancements', PhotoEnhancementViewSet, basename='photoenhancement')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', dashboard, name='dashboard'),
     path('test/', test_view, name='test_view'),
    path('wallet/', wallet, name='wallet'),
    path('id_card_input/', id_card_input, name='id_card_input'),
    path('id_card_output/', id_card_output, name='id_card_output'),
    path('upload_pdf/', views.upload_pdf, name='upload_pdf'),
    path('upload_pan/', views.upload_pan, name='upload_pan'),
    path('upload_eshram/', views.upload_eshram, name='upload_eshram'),
    path('upload_election/', views.upload_election, name='upload_election'),
    path('upload_ayushman/', views.upload_ayushman, name='upload_ayushman'),
    path('upload_abha/', views.upload_abha, name='upload_abha'),
    path('upload_aadhaar/', views.upload_aadhaar, name='upload_aadhaar'),
    path('save_id_card/', views.save_id_card, name='save_id_card'),
    
    #path('review_data/', review_data, name='review_data'),
    path('edit_id_card/', views.edit_id_card, name='edit_id_card'),
    path('id_card_output1/', views.id_card_output, name='id_card_output1'),
]




