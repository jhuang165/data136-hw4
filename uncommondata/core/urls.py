from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('index.html', views.index, name='index_html'),
    path('app/new/', views.new_user_form, name='new_user_form'),
    path('app/api/createUser/', views.create_user_api, name='create_user_api'),
    path('app/uploads/', views.uploads, name='uploads'),
    path('app/show-uploads/', views.show_uploads, name='show_uploads'),
    path('app/api/upload/', views.upload_api, name='upload_api'),

    path('app/api/uploads-check/', views.uploads_api_check, name='uploads_api_check'),
    path('app/api/uploads-status/', views.uploads_status, name='uploads_status'),
    path('app/api/dump-uploads/', views.dump_uploads_api, name='dump_uploads_api'),
    path('app/api/dump-data/', views.dump_data_api, name='dump_data_api'),
    path('app/api/knockknock/', views.knockknock_api, name='knockknock_api'),
]
