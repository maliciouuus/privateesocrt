from django.urls import path
from . import views

app_name = "whitelabel"

urlpatterns = [
    path("sites/", views.SiteListView.as_view(), name="sites"),
    path("sites/create/", views.SiteCreateView.as_view(), name="create_site"),
    path("sites/<int:site_id>/edit/", views.SiteEditView.as_view(), name="edit_site"),
    path(
        "sites/<int:site_id>/edit/save/",
        views.SiteEditView.as_view(),
        name="edit_site_save",
    ),
    path(
        "sites/<int:site_id>/delete/",
        views.SiteDeleteView.as_view(),
        name="delete_site",
    ),
    path("sites/<int:site_id>/view/", views.SiteView.as_view(), name="site_view"),
]
