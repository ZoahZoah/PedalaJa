from django.urls import path, include
from .views import home, redirect_to_home, suporte, route_to_station_view, login_view, logout_view, vincular_bicicletario, avaliar_bicicletario

urlpatterns = [
    path('', redirect_to_home),
    path('home/', home, name='home'),
    path('suporte/', suporte, name='suporte'),
    path('rota-estacao/',route_to_station_view, name='rota_para_estacao'),
    path('accounts/login/', login_view, name='login'),
    path('accounts/logout/', logout_view, name='logout'),
    path('vincular/<str:external_id>/', vincular_bicicletario, name='vincular_bicicletario'),
    path('avaliar/<int:bicicletario_id>/', avaliar_bicicletario, name='avaliar_bicicletario'),
]