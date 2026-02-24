from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from orders.views import catalogo

def index(request):
    return render(request, "index.html")



from orders import views

urlpatterns = [
  path("", views.home, name="home"),
  path("", include("orders.urls")),
  path("admin/", admin.site.urls),
]
