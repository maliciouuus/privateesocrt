from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentification
    path("register/", views.register_view, name="register"),
    path(
        "register/ambassador/",
        views.register_ambassador_view,
        name="register_ambassador",
    ),
    # Gestion de profil
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/change-password/", views.change_password, name="change_password"),
    path("profile/delete/", views.delete_account, name="delete_account"),
    path("activation-sent/", views.activation_sent, name="activation_sent"),
    path("activate/<str:uidb64>/<str:token>/", views.activate_account, name="activate"),
    path("signup-redirect/", views.signup_redirect, name="signup_redirect"),
    path("redirect-signup/", views.redirect_signup, name="redirect_signup"),
]
