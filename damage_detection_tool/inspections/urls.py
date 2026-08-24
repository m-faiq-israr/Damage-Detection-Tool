from django.urls import include, path

from .test_ui import (
    test_ui_page,
    test_ui_upload,
    test_ui_submit,
    test_ui_media,
)

urlpatterns = [
    path(
        "api/v1/",
        include("inspections.api.urls"),
    ),
    path("test-ui/", test_ui_page, name="test_ui_page"),
    path("test-ui/upload/", test_ui_upload, name="test_ui_upload"),
    path("test-ui/submit/", test_ui_submit, name="test_ui_submit"),
    path(
        "test-ui/media/<str:filename>",
        test_ui_media,
        name="test_ui_media",
    ),
]
