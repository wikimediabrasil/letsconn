from django.urls import path
from .views import (
    home_view,
    enrollments_view,
    manage_view,
    receive_enrollment_data,
    proxy_api_request,
    profile_view,
    exist_view,
    badges_view,
    user_badges_api,
    badge_verification_view,
)

urlpatterns = [
    path('', home_view, name='home_view'),
    path('enrollments/', enrollments_view, name='enrollments_view'),
    path('manage/', manage_view, name='manage_view'),
    path('badges/', badges_view, name='badges_view'),
    path('badge/<str:verification_code>/', badge_verification_view, name='badge_verification'),
    path('endpoint/', receive_enrollment_data, name='receive_enrollment_data'),
    path('proxy/', proxy_api_request, name='proxy_api_request'),
    path('profile/', profile_view, name='profile_view'),
    path('exists/', exist_view, name='exist_view'),
    path('user-badges/', user_badges_api, name='user_badges_api'),
]