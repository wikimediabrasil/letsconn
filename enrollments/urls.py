from django.urls import path
from .views import home_view, enrollments_view, manage_view, receive_enrollment_data, proxy_api_request

urlpatterns = [
    path('', home_view, name='home_view'),
    path('enrollments/', enrollments_view, name='enrollments_view'),
    path('manage/', manage_view, name='manage_view'),
    path('endpoint/', receive_enrollment_data, name='receive_enrollment_data'),
    path('proxy/', proxy_api_request, name='proxy_api_request')
]