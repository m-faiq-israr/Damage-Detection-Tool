from django.urls import path

from .views import (
    single_inspection_api,
    comparison_api,
)

urlpatterns = [
    path(
        "single/",
        single_inspection_api,
        name="single_inspection_api",
    ),
    path(
        "compare/",
        comparison_api,
        name="comparison_api",
    ),
]
