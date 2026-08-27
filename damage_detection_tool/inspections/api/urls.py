from django.urls import path

from .views import (
    single_inspection_api,
    comparison_api,
    quality_check_api,
)

urlpatterns = [
    path(
        "walkaround/single/",
        single_inspection_api,
        name="single_inspection_api",
    ),
    path(
        "walkaround/compare/",
        comparison_api,
        name="comparison_api",
    ),
    path(
        "walkaround/quality-check/",
        quality_check_api,
        name="quality_check_api",
    ),
]
