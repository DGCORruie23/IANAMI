from django.urls import path
from . import views

urlpatterns = [
    path('inteligencia/', views.inteligencia_view, name='inteligencia'),
    path('indicadores/', views.indicadores_view, name='indicadores'),
    path('comparativo/', views.comparativo_view, name='comparativo'),
    path('comparativo/data/', views.comparativo_data_view, name='comparativo_data'),
    path('indicadores/data/', views.indicadores_data_view, name='indicadores_data'),
    path('indicadores/tramites/data/', views.tramites_data_view, name='tramites_data'),
    path('indicadores/control/data/', views.control_data_view, name='control_data'),
    path('indicadores/proteccion/data/', views.proteccion_data_view, name='proteccion_data'),
]
