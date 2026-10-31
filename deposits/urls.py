from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("fdrs/", views.fdr_list, name="fdr_list"),
    path("fdrs/new/", views.fdr_create, name="fdr_create"),
    path("fdrs/<int:pk>/", views.fdr_detail, name="fdr_detail"),
    path("fdrs/<int:pk>/verify/", views.fdr_verify, name="fdr_verify"),
    path("fdrs/<int:pk>/renew/", views.fdr_renew, name="fdr_renew"),
    path("fdrs/<int:pk>/release/", views.release_request, name="release_request"),
    path("releases/", views.release_list, name="release_list"),
    path("releases/<int:pk>/decide/", views.release_decide, name="release_decide"),
    path("audit/", views.audit_list, name="audit_list"),
]