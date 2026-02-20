from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('index.html', views.index, name='index_html'),
    
    # User creation
    path('app/new/', views.new_user_form, name='new_user_form'),
    path('app/api/createUser/', views.create_user_api, name='create_user_api'),
    
    # Uploads
    path('app/uploads/', views.uploads, name='uploads'),
    path('app/api/upload/', views.upload_api, name='upload_api'),
    path('app/api/uploads-check/', views.uploads_api_check, name='uploads_api_check'),
    path('app/api/uploads-status/', views.uploads_status, name='uploads_status'),
    
    # Data dump endpoints
    path('app/api/dump-uploads/', views.dump_uploads_api, name='dump_uploads_api'),
    path('app/api/dump-data/', views.dump_data_api, name='dump_data_api'),
    
    # Knock knock joke endpoint
    path('app/api/knockknock/', views.knockknock_api, name='knockknock_api'),
]
