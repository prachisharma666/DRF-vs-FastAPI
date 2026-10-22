from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from books.views import BookDetailView, health, SearchView, ReadingListView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health),
    path("api/search", SearchView.as_view()),
    path("api/reading-list", ReadingListView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/books/<str:work_id>", BookDetailView.as_view())
]