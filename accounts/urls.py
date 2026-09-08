from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", views.MeView.as_view(), name="me"),
    path("pending-government/", views.PendingGovernmentListView.as_view(), name="pending-government"),
    path("verify-government/<int:user_id>/", views.VerifyGovernmentView.as_view(), name="verify-government"),
    path("maintainers/", views.MaintainerListView.as_view(), name="maintainers"),
]