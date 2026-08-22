from django.urls import path
from . import views

urlpatterns = [
    path('carga/', views.upload_view, name='upload_csv'),
    path('carga_comparativo/', views.carga_comparativo_view, name='carga_comparativo'),
]
