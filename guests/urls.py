from django.urls import path

from .views import LoginRequestView, LoginVerifyView, LogoutView, MockInboxView

urlpatterns = [
    path(
        "conversations/<uuid:conversation_id>/login/",
        LoginRequestView.as_view(),
        name="guest-login-request",
    ),
    path(
        "conversations/<uuid:conversation_id>/login/verify/",
        LoginVerifyView.as_view(),
        name="guest-login-verify",
    ),
    path(
        "conversations/<uuid:conversation_id>/logout/",
        LogoutView.as_view(),
        name="guest-logout",
    ),
    path("mock-inbox/", MockInboxView.as_view(), name="mock-inbox"),
]
