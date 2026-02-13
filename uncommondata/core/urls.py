from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('index.html', views.index, name='index_html'),
    
    # User creation pages/endpoints
    path('app/new/', views.new_user_form, name='new_user_form'),
    path('app/api/createUser/', views.create_user_api, name='create_user_api'),
]
