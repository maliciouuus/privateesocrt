from django.urls import path
from . import views

app_name = "whitelabel"

urlpatterns = [
    path("sites/", views.site_list, name="sites"),
    path("sites/create/", views.create_site, name="create_site"),
    path("sites/<int:pk>/", views.site_detail, name="site_detail"),
    path("sites/<int:pk>/edit/", views.edit_site, name="edit_site"),
    path("sites/<int:pk>/delete/", views.delete_site, name="delete_site"),
]
