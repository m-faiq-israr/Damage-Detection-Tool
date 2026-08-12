from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("single-inspection/", views.single_inspection, name="single_inspection"),
    path("download-report/", views.download_report, name="download_report"),
]
