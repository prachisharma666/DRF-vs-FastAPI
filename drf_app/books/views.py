import requests
import re
from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException,NotFound
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .serializers import BookSerializer, ReadingListItemSerializer

CONTACT_EMAIL = settings.OPENLIBRARY_CONTACT_EMAIL
HEADERS = {
    "User-Agent": f"BookExplorer/0.1 ({CONTACT_EMAIL})"
    if CONTACT_EMAIL
    else "BookExplorer/0.1"
}
READING_LIST = []
session = requests.Session()

class UpstreamError(APIException):
    status_code = 502
    default_detail = "Upstream error"

def health(request):
    return JsonResponse({"status": "ok"})

class SearchView(APIView):
    @extend_schema(parameters=[OpenApiParameter("q", str, required=True),
                               OpenApiParameter("limit", int)],
                   responses=BookSerializer(many=True))
    def get(self, request):
        q = request.query_params.get("q", "")
        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            return Response({"detail": "limit must be an integer"}, status=422)
        if not q or not 1 <= limit <= 50:
            return Response({"detail": "invalid q or limit"}, status=422)
        try:
            r = session.get(f"{settings.UPSTREAM_URL}/search.json", headers=HEADERS,
                            timeout=5, params={"q": q, "limit": limit,
                            "fields": "key,title,author_name,first_publish_year,cover_i"})
            r.raise_for_status()
        except requests.RequestException:
            raise UpstreamError()
        books = [{"work_id": d["key"].split("/")[-1], "title": d["title"],
                  "authors": d.get("author_name", []),
                  "first_publish_year": d.get("first_publish_year"),
                  "cover_url": f"https://covers.openlibrary.org/b/id/{d['cover_i']}-M.jpg"
                               if d.get("cover_i") else None}
                 for d in r.json()["docs"]]
        return Response(BookSerializer(books, many=True).data)

class ReadingListView(APIView):
    @extend_schema(request=ReadingListItemSerializer, responses=ReadingListItemSerializer)
    def post(self, request):
        s = ReadingListItemSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        READING_LIST.append(s.validated_data)
        return Response(s.data, status=201)

    @extend_schema(responses=ReadingListItemSerializer(many=True))
    def get(self, request):
        return Response(READING_LIST)

class BookDetailView(APIView):
    @extend_schema(responses=BookSerializer)
    def get(self, request, work_id):
        if not re.fullmatch(r"OL\d+W", work_id):
            return Response({"detail": "invalid work_id"}, status=422)
        try:
            r = session.get(f"{settings.UPSTREAM_URL}/works/{work_id}.json",
                            headers=HEADERS, timeout=5)
        except requests.RequestException:        # network failure only
            raise UpstreamError()
        if r.status_code == 404:                 # check 404 first
            raise NotFound("Work not found")
        if r.status_code >= 400:                 # any other upstream error
            raise UpstreamError()
        d = r.json()
        covers = d.get("covers") or []
        book = {"work_id": work_id, "title": d["title"], "authors": [],
                "first_publish_year": None,
                "cover_url": f"https://covers.openlibrary.org/b/id/{covers[0]}-M.jpg" if covers else None}
        return Response(BookSerializer(book).data)
