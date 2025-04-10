from django.urls import path
from .views import home_view, enrollments_view, csv_view, manage_view

urlpatterns = [
    path('', home_view, name='home_view'),
    path('enrollments/', enrollments_view, name='enrollments_view'),
    path('csv/', csv_view, name='csv_view'),
    path('manage/', manage_view, name='manage_view'),
]