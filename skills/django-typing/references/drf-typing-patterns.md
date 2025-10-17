# Django REST Framework Typing Patterns

Comprehensive guide to type safety in Django REST Framework using mypy and djangorestframework-stubs.

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Serializer Typing](#serializer-typing)
3. [ViewSets and Views](#viewsets-and-views)
4. [Permissions and Authentication](#permissions-and-authentication)
5. [Pagination](#pagination)
6. [Filtering and Search](#filtering-and-search)
7. [Custom Actions and Decorators](#custom-actions-and-decorators)
8. [Request and Response Typing](#request-and-response-typing)
9. [API Versioning](#api-versioning)
10. [OpenAPI/Swagger Integration](#openapiswagger-integration)
11. [Testing](#testing)

---

## Installation and Setup

### Required Packages

```bash
pip install djangorestframework-stubs[compatible-mypy]
```

This installs:
- `djangorestframework-stubs` - Type stubs for DRF
- `types-requests` - Type stubs for requests library
- Compatible version of mypy

### mypy Configuration

Add to `mypy.ini`:

```ini
[mypy]
plugins =
    mypy_django_plugin.main,
    mypy_drf_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings

[mypy-rest_framework.*]
ignore_missing_imports = False

[mypy-*.migrations.*]
ignore_errors = True

# Strict settings (enable gradually)
check_untyped_defs = True
disallow_untyped_defs = True
disallow_any_generics = True
warn_return_any = True
warn_unused_ignores = True
```

### Type Checking Command

```bash
# Check entire project
mypy .

# Check specific app
mypy apps/api/

# Generate HTML report
mypy --html-report ./mypy-report .
```

---

## Serializer Typing

### Basic ModelSerializer

```python
from django.db import models
from rest_framework import serializers
from typing import Any, ClassVar, OrderedDict


class Article(models.Model):
    title: str = models.CharField(max_length=200)
    content: str = models.TextField()
    published: bool = models.BooleanField(default=False)
    author: models.ForeignKey["User"] = models.ForeignKey(
        "User", on_delete=models.CASCADE
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)


class ArticleSerializer(serializers.ModelSerializer[Article]):
    """Type-safe article serializer."""

    # Explicit field type annotations
    author_name: serializers.ReadOnlyField = serializers.ReadOnlyField(
        source="author.username"
    )
    word_count: serializers.SerializerMethodField = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "title", "content", "published", "author",
                  "author_name", "word_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_word_count(self, obj: Article) -> int:
        """Calculate word count from content."""
        return len(obj.content.split())

    def validate_title(self, value: str) -> str:
        """Validate title field."""
        if len(value) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters")
        return value.strip()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation."""
        if attrs.get("published") and not attrs.get("content"):
            raise serializers.ValidationError(
                "Cannot publish article without content"
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Article:
        """Create article with validated data."""
        return Article.objects.create(**validated_data)

    def update(self, instance: Article, validated_data: dict[str, Any]) -> Article:
        """Update article instance."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
```

### Regular Serializer

```python
from rest_framework import serializers
from typing import Any


class LoginSerializer(serializers.Serializer[Any]):
    """Serializer for login data (not tied to a model)."""

    username: serializers.CharField = serializers.CharField(max_length=150)
    password: serializers.CharField = serializers.CharField(
        max_length=128,
        write_only=True,
        style={"input_type": "password"}
    )
    remember_me: serializers.BooleanField = serializers.BooleanField(
        default=False,
        required=False
    )

    def validate_username(self, value: str) -> str:
        """Validate username format."""
        return value.lower().strip()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate credentials."""
        username = attrs.get("username")
        password = attrs.get("password")

        if not username or not password:
            raise serializers.ValidationError("Must include username and password")

        return attrs

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Custom output representation."""
        ret = super().to_representation(instance)
        # Don't include password in response
        ret.pop("password", None)
        return ret
```

### Nested Serializers

```python
from rest_framework import serializers
from typing import Any, OrderedDict


class UserSerializer(serializers.ModelSerializer["User"]):
    """Serializer for user objects."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["id"]


class CommentSerializer(serializers.ModelSerializer["Comment"]):
    """Serializer for comment objects."""

    author: UserSerializer = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "content", "author", "created_at"]
        read_only_fields = ["id", "created_at"]


class ArticleDetailSerializer(serializers.ModelSerializer[Article]):
    """Detailed article serializer with nested relations."""

    author: UserSerializer = UserSerializer(read_only=True)
    comments: CommentSerializer = CommentSerializer(many=True, read_only=True)
    comment_count: serializers.SerializerMethodField = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "title", "content", "published", "author",
                  "comments", "comment_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_comment_count(self, obj: Article) -> int:
        """Get number of comments."""
        return obj.comments.count()
```

### Writable Nested Serializers

```python
from rest_framework import serializers
from typing import Any


class TagSerializer(serializers.ModelSerializer["Tag"]):
    """Serializer for tag objects."""

    class Meta:
        model = Tag
        fields = ["id", "name"]


class ArticleWithTagsSerializer(serializers.ModelSerializer[Article]):
    """Article serializer with writable nested tags."""

    tags: TagSerializer = TagSerializer(many=True)

    class Meta:
        model = Article
        fields = ["id", "title", "content", "tags"]

    def create(self, validated_data: dict[str, Any]) -> Article:
        """Create article with nested tags."""
        tags_data = validated_data.pop("tags", [])
        article = Article.objects.create(**validated_data)

        for tag_data in tags_data:
            tag, _ = Tag.objects.get_or_create(**tag_data)
            article.tags.add(tag)

        return article

    def update(self, instance: Article, validated_data: dict[str, Any]) -> Article:
        """Update article with nested tags."""
        tags_data = validated_data.pop("tags", None)

        # Update article fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tags_data is not None:
            instance.tags.clear()
            for tag_data in tags_data:
                tag, _ = Tag.objects.get_or_create(**tag_data)
                instance.tags.add(tag)

        return instance
```

### ListSerializer Typing

```python
from rest_framework import serializers
from typing import Any, Sequence


class BulkArticleSerializer(serializers.ListSerializer[Article]):
    """Custom list serializer for bulk operations."""

    def create(self, validated_data: list[dict[str, Any]]) -> list[Article]:
        """Bulk create articles."""
        articles = [Article(**item) for item in validated_data]
        return Article.objects.bulk_create(articles)

    def update(self, instance: Sequence[Article], validated_data: list[dict[str, Any]]) -> list[Article]:
        """Bulk update articles."""
        article_mapping = {article.id: article for article in instance}
        data_mapping = {item["id"]: item for item in validated_data}

        updated_articles = []
        for article_id, data in data_mapping.items():
            article = article_mapping.get(article_id)
            if article is not None:
                for attr, value in data.items():
                    setattr(article, attr, value)
                updated_articles.append(article)

        Article.objects.bulk_update(updated_articles, ["title", "content", "published"])
        return updated_articles


class ArticleSerializer(serializers.ModelSerializer[Article]):
    """Article serializer with custom list serializer."""

    class Meta:
        model = Article
        fields = ["id", "title", "content", "published"]
        list_serializer_class = BulkArticleSerializer
```

### Custom Field Types

```python
from rest_framework import serializers
from typing import Any
import json


class JSONField(serializers.Field[dict[str, Any], str]):
    """Custom JSON field with proper typing."""

    def to_representation(self, value: dict[str, Any]) -> str:
        """Convert dict to JSON string."""
        return json.dumps(value)

    def to_internal_value(self, data: str) -> dict[str, Any]:
        """Parse JSON string to dict."""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise serializers.ValidationError(f"Invalid JSON: {e}")


class ColorField(serializers.Field[str, str]):
    """Custom color field that validates hex colors."""

    def to_representation(self, value: str) -> str:
        """Return hex color."""
        return value

    def to_internal_value(self, data: str) -> str:
        """Validate and normalize hex color."""
        if not isinstance(data, str):
            raise serializers.ValidationError("Color must be a string")

        color = data.strip().upper()
        if not color.startswith("#"):
            color = f"#{color}"

        if len(color) not in (4, 7) or not all(c in "0123456789ABCDEF" for c in color[1:]):
            raise serializers.ValidationError("Invalid hex color")

        return color


class ConfigSerializer(serializers.Serializer[Any]):
    """Serializer using custom fields."""

    settings: JSONField = JSONField()
    theme_color: ColorField = ColorField()
```

### SerializerMethodField Typing

```python
from rest_framework import serializers
from typing import Any


class ArticleListSerializer(serializers.ModelSerializer[Article]):
    """Article list serializer with computed fields."""

    preview: serializers.SerializerMethodField = serializers.SerializerMethodField()
    is_recent: serializers.SerializerMethodField = serializers.SerializerMethodField()
    author_info: serializers.SerializerMethodField = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "title", "preview", "is_recent", "author_info", "created_at"]

    def get_preview(self, obj: Article) -> str:
        """Get content preview."""
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    def get_is_recent(self, obj: Article) -> bool:
        """Check if article is recent (within 7 days)."""
        from django.utils import timezone
        from datetime import timedelta
        return obj.created_at >= timezone.now() - timedelta(days=7)

    def get_author_info(self, obj: Article) -> dict[str, Any]:
        """Get author information."""
        return {
            "id": obj.author.id,
            "username": obj.author.username,
            "email": obj.author.email,
        }
```

---

## ViewSets and Views

### ModelViewSet Typing

```python
from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import QuerySet
from typing import Any


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet for article CRUD operations."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_queryset(self) -> QuerySet[Article]:
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()

        if self.request.user.is_authenticated:
            # Show all articles to authenticated users
            return queryset
        else:
            # Only show published articles to anonymous users
            return queryset.filter(published=True)

    def get_serializer_class(self) -> type[serializers.Serializer[Article]]:
        """Return appropriate serializer based on action."""
        if self.action == "retrieve":
            return ArticleDetailSerializer
        elif self.action == "list":
            return ArticleListSerializer
        return self.serializer_class

    def perform_create(self, serializer: ArticleSerializer) -> None:
        """Save article with current user as author."""
        serializer.save(author=self.request.user)

    def perform_update(self, serializer: ArticleSerializer) -> None:
        """Update article with timestamp."""
        from django.utils import timezone
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance: Article) -> None:
        """Soft delete by marking as unpublished."""
        instance.published = False
        instance.save()
```

### ReadOnlyModelViewSet

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import QuerySet
from typing import Any


class PublicArticleViewSet(viewsets.ReadOnlyModelViewSet[Article]):
    """Read-only ViewSet for public articles."""

    queryset: QuerySet[Article] = Article.objects.filter(published=True)
    serializer_class = ArticleListSerializer

    def get_queryset(self) -> QuerySet[Article]:
        """Get published articles ordered by date."""
        return super().get_queryset().order_by("-created_at")

    @action(detail=False, methods=["get"])
    def featured(self, request: Request) -> Response:
        """Get featured articles."""
        articles = self.get_queryset().filter(featured=True)[:5]
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)
```

### GenericViewSet with Mixins

```python
from rest_framework import viewsets, mixins, status
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import QuerySet
from typing import Any


class CommentViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet[Comment]
):
    """ViewSet for comments without delete functionality."""

    queryset: QuerySet[Comment] = Comment.objects.all()
    serializer_class = CommentSerializer

    def get_queryset(self) -> QuerySet[Comment]:
        """Filter comments by article if provided."""
        queryset = super().get_queryset()
        article_id = self.request.query_params.get("article")

        if article_id is not None:
            queryset = queryset.filter(article_id=article_id)

        return queryset.select_related("author", "article")

    def perform_create(self, serializer: CommentSerializer) -> None:
        """Save comment with current user."""
        serializer.save(author=self.request.user)
```

### Generic API Views

```python
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import QuerySet
from typing import Any


class ArticleListCreateView(generics.ListCreateAPIView[Article]):
    """List and create articles."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_queryset(self) -> QuerySet[Article]:
        """Get articles for current user."""
        return super().get_queryset().filter(author=self.request.user)

    def perform_create(self, serializer: ArticleSerializer) -> None:
        """Create article for current user."""
        serializer.save(author=self.request.user)


class ArticleRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView[Article]):
    """Retrieve, update, or delete a single article."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleDetailSerializer

    def get_queryset(self) -> QuerySet[Article]:
        """Ensure user can only access their own articles."""
        return super().get_queryset().filter(author=self.request.user)


class ArticleListView(generics.ListAPIView[Article]):
    """List articles only."""

    queryset: QuerySet[Article] = Article.objects.filter(published=True)
    serializer_class = ArticleListSerializer


class ArticleCreateView(generics.CreateAPIView[Article]):
    """Create article only."""

    serializer_class = ArticleSerializer

    def perform_create(self, serializer: ArticleSerializer) -> None:
        """Create with current user as author."""
        serializer.save(author=self.request.user)
```

### APIView

```python
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from typing import Any


class ArticleStatsView(APIView):
    """Custom view for article statistics."""

    def get(self, request: Request, format: str | None = None) -> Response:
        """Get article statistics."""
        stats = {
            "total": Article.objects.count(),
            "published": Article.objects.filter(published=True).count(),
            "draft": Article.objects.filter(published=False).count(),
            "by_author": self._get_author_stats(),
        }
        return Response(stats)

    def _get_author_stats(self) -> list[dict[str, Any]]:
        """Get article count by author."""
        from django.db.models import Count

        return list(
            Article.objects
            .values("author__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )


class ArticlePublishView(APIView):
    """Custom view for publishing articles."""

    def post(self, request: Request, pk: int, format: str | None = None) -> Response:
        """Publish an article."""
        try:
            article = Article.objects.get(pk=pk, author=request.user)
        except Article.DoesNotExist:
            return Response(
                {"error": "Article not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if article.published:
            return Response(
                {"error": "Article is already published"},
                status=status.HTTP_400_BAD_REQUEST
            )

        article.published = True
        article.save()

        serializer = ArticleSerializer(article)
        return Response(serializer.data)
```

---

## Permissions and Authentication

### Custom Permission Classes

```python
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from typing import Any


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission that allows owners to edit their objects.
    Read-only for everyone else.
    """

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any
    ) -> bool:
        """Check object-level permission."""
        # Read permissions allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        return obj.author == request.user


class IsAuthorOrAdmin(permissions.BasePermission):
    """Permission for authors and admin users."""

    message = "You must be the author or an admin to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check view-level permission."""
        return request.user.is_authenticated

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any
    ) -> bool:
        """Check object-level permission."""
        return (
            request.user.is_staff or
            obj.author == request.user
        )


class IsPublishedOrOwner(permissions.BasePermission):
    """Allow access to published articles or owner."""

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Article
    ) -> bool:
        """Check if article is published or user is owner."""
        if obj.published:
            return True

        return (
            request.user.is_authenticated and
            obj.author == request.user
        )


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with custom permissions."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
```

### Permission Composition

```python
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from typing import Any


class IsOwner(permissions.BasePermission):
    """Check if user is the owner."""

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any
    ) -> bool:
        """Check ownership."""
        return obj.author == request.user


class HasSubscription(permissions.BasePermission):
    """Check if user has an active subscription."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check subscription status."""
        return (
            request.user.is_authenticated and
            hasattr(request.user, "subscription") and
            request.user.subscription.is_active
        )


class PremiumArticleViewSet(viewsets.ReadOnlyModelViewSet[Article]):
    """ViewSet requiring subscription."""

    queryset: QuerySet[Article] = Article.objects.filter(is_premium=True)
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated, HasSubscription]
```

### Custom Authentication

```python
from rest_framework import authentication, exceptions
from rest_framework.request import Request
from typing import Tuple, Any
from django.contrib.auth.models import User


class TokenAuthentication(authentication.BaseAuthentication):
    """Custom token authentication."""

    def authenticate(self, request: Request) -> Tuple[User, None] | None:
        """Authenticate user via token."""
        token = request.META.get("HTTP_X_API_TOKEN")

        if not token:
            return None

        try:
            user = User.objects.get(auth_token=token)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid token")

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive")

        return (user, None)

    def authenticate_header(self, request: Request) -> str:
        """Return authentication header."""
        return "Token"


class APIKeyAuthentication(authentication.BaseAuthentication):
    """API key authentication."""

    def authenticate(self, request: Request) -> Tuple[User, str] | None:
        """Authenticate via API key."""
        api_key = request.META.get("HTTP_X_API_KEY")

        if not api_key:
            return None

        try:
            from .models import APIKey
            key_obj = APIKey.objects.select_related("user").get(
                key=api_key,
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key")

        # Update last used timestamp
        key_obj.update_last_used()

        return (key_obj.user, api_key)
```

---

## Pagination

### Custom Pagination Classes

```python
from rest_framework.pagination import (
    PageNumberPagination,
    LimitOffsetPagination,
    CursorPagination,
)
from rest_framework.request import Request
from rest_framework.response import Response
from typing import Any, OrderedDict
from collections import OrderedDict as OrderedDictType


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination with configurable page size."""

    page_size: int = 10
    page_size_query_param: str = "page_size"
    max_page_size: int = 100

    def get_paginated_response(self, data: list[Any]) -> Response:
        """Return paginated response with metadata."""
        return Response(OrderedDict([
            ("count", self.page.paginator.count),
            ("next", self.get_next_link()),
            ("previous", self.get_previous_link()),
            ("total_pages", self.page.paginator.num_pages),
            ("current_page", self.page.number),
            ("results", data),
        ]))


class LargeResultsSetPagination(PageNumberPagination):
    """Pagination for large result sets."""

    page_size: int = 50
    page_size_query_param: str = "page_size"
    max_page_size: int = 1000


class CustomLimitOffsetPagination(LimitOffsetPagination):
    """Custom limit/offset pagination."""

    default_limit: int = 20
    max_limit: int = 200

    def get_paginated_response(self, data: list[Any]) -> Response:
        """Return response with custom metadata."""
        return Response(OrderedDict([
            ("count", self.count),
            ("next", self.get_next_link()),
            ("previous", self.get_previous_link()),
            ("limit", self.limit),
            ("offset", self.offset),
            ("results", data),
        ]))


class TimestampCursorPagination(CursorPagination):
    """Cursor pagination based on timestamp."""

    page_size: int = 25
    ordering: str = "-created_at"
    cursor_query_param: str = "cursor"

    def get_paginated_response(self, data: list[Any]) -> Response:
        """Return cursor paginated response."""
        return Response(OrderedDict([
            ("next", self.get_next_link()),
            ("previous", self.get_previous_link()),
            ("results", data),
        ]))


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with pagination."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer
    pagination_class = StandardResultsSetPagination
```

### Dynamic Pagination

```python
from rest_framework import viewsets
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from django.db.models import QuerySet
from typing import Any


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with dynamic pagination."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_pagination_class(self) -> type[BasePagination] | None:
        """Select pagination based on query parameters."""
        if self.request.query_params.get("cursor"):
            return TimestampCursorPagination
        elif self.request.query_params.get("offset"):
            return CustomLimitOffsetPagination
        return StandardResultsSetPagination

    @property
    def pagination_class(self) -> type[BasePagination] | None:
        """Return pagination class."""
        return self.get_pagination_class()
```

---

## Filtering and Search

### FilterSet with django-filter

```python
from django_filters import rest_framework as filters
from rest_framework import viewsets
from django.db.models import QuerySet
from typing import Any


class ArticleFilter(filters.FilterSet):
    """Filter for article queries."""

    title: filters.CharFilter = filters.CharFilter(
        lookup_expr="icontains",
        label="Title contains"
    )
    published: filters.BooleanFilter = filters.BooleanFilter()
    created_after: filters.DateTimeFilter = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte"
    )
    created_before: filters.DateTimeFilter = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte"
    )
    author: filters.NumberFilter = filters.NumberFilter(
        field_name="author__id"
    )
    author_username: filters.CharFilter = filters.CharFilter(
        field_name="author__username",
        lookup_expr="iexact"
    )
    tags: filters.ModelMultipleChoiceFilter = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name="tags__slug",
        to_field_name="slug",
    )
    min_word_count: filters.NumberFilter = filters.NumberFilter(
        method="filter_word_count"
    )

    class Meta:
        model = Article
        fields = ["title", "published", "author", "created_at"]

    def filter_word_count(
        self,
        queryset: QuerySet[Article],
        name: str,
        value: int
    ) -> QuerySet[Article]:
        """Filter by minimum word count."""
        from django.db.models import F, Func, Value

        return queryset.annotate(
            word_count=Func(
                Func(F("content"), Value(" "), function="SPLIT_PART"),
                function="ARRAY_LENGTH"
            )
        ).filter(word_count__gte=value)


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with filtering."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer
    filterset_class = ArticleFilter
    filter_backends = [filters.DjangoFilterBackend]
```

### SearchFilter and OrderingFilter

```python
from rest_framework import viewsets, filters
from django.db.models import QuerySet
from typing import Any


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with search and ordering."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        filters.DjangoFilterBackend,
    ]

    # Search configuration
    search_fields = ["title", "content", "author__username"]

    # Ordering configuration
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-created_at"]

    # Filtering configuration
    filterset_class = ArticleFilter
```

### Custom Filter Backend

```python
from rest_framework import filters
from rest_framework.request import Request
from django.db.models import QuerySet
from typing import Any


class TenantFilterBackend(filters.BaseFilterBackend):
    """Filter results by tenant."""

    def filter_queryset(
        self,
        request: Request,
        queryset: QuerySet[Any],
        view: Any
    ) -> QuerySet[Any]:
        """Filter by tenant from request."""
        if not hasattr(request, "tenant"):
            return queryset.none()

        return queryset.filter(tenant=request.tenant)


class IsOwnerFilterBackend(filters.BaseFilterBackend):
    """Filter results to only show user's own objects."""

    def filter_queryset(
        self,
        request: Request,
        queryset: QuerySet[Any],
        view: Any
    ) -> QuerySet[Any]:
        """Filter to user's objects."""
        if not request.user.is_authenticated:
            return queryset.none()

        if request.user.is_staff:
            return queryset

        return queryset.filter(author=request.user)


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with custom filter backends."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [TenantFilterBackend, IsOwnerFilterBackend]
```

---

## Custom Actions and Decorators

### Custom Actions

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import QuerySet
from typing import Any


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with custom actions."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=True, methods=["post"])
    def publish(self, request: Request, pk: int | None = None) -> Response:
        """Publish an article."""
        article = self.get_object()

        if article.published:
            return Response(
                {"error": "Article is already published"},
                status=status.HTTP_400_BAD_REQUEST
            )

        article.published = True
        article.save()

        serializer = self.get_serializer(article)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request: Request, pk: int | None = None) -> Response:
        """Unpublish an article."""
        article = self.get_object()

        if not article.published:
            return Response(
                {"error": "Article is not published"},
                status=status.HTTP_400_BAD_REQUEST
            )

        article.published = False
        article.save()

        serializer = self.get_serializer(article)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request: Request) -> Response:
        """Get featured articles."""
        articles = self.get_queryset().filter(featured=True)[:10]
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request: Request) -> Response:
        """Get article statistics."""
        queryset = self.get_queryset()

        stats = {
            "total": queryset.count(),
            "published": queryset.filter(published=True).count(),
            "draft": queryset.filter(published=False).count(),
            "featured": queryset.filter(featured=True).count(),
        }

        return Response(stats)

    @action(detail=True, methods=["post"], url_path="add-tag")
    def add_tag(self, request: Request, pk: int | None = None) -> Response:
        """Add a tag to an article."""
        article = self.get_object()
        tag_id = request.data.get("tag_id")

        if not tag_id:
            return Response(
                {"error": "tag_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tag = Tag.objects.get(id=tag_id)
        except Tag.DoesNotExist:
            return Response(
                {"error": "Tag not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        article.tags.add(tag)
        serializer = self.get_serializer(article)
        return Response(serializer.data)
```

### Custom Decorators

```python
from functools import wraps
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from typing import Callable, Any, TypeVar, ParamSpec


P = ParamSpec("P")
R = TypeVar("R")


def require_subscription(view_func: Callable[P, R]) -> Callable[P, R]:
    """Decorator to require active subscription."""

    @wraps(view_func)
    def wrapper(self: Any, request: Request, *args: P.args, **kwargs: P.kwargs) -> R | Response:
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not hasattr(request.user, "subscription") or not request.user.subscription.is_active:
            return Response(
                {"error": "Active subscription required"},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper


def rate_limit(max_requests: int, window_seconds: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for rate limiting."""

    def decorator(view_func: Callable[P, R]) -> Callable[P, R]:
        @wraps(view_func)
        def wrapper(self: Any, request: Request, *args: P.args, **kwargs: P.kwargs) -> R | Response:
            from django.core.cache import cache

            user_id = request.user.id if request.user.is_authenticated else request.META.get("REMOTE_ADDR")
            cache_key = f"rate_limit:{view_func.__name__}:{user_id}"

            current = cache.get(cache_key, 0)

            if current >= max_requests:
                return Response(
                    {"error": "Rate limit exceeded"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            cache.set(cache_key, current + 1, window_seconds)
            return view_func(self, request, *args, **kwargs)

        return wrapper

    return decorator


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet using custom decorators."""

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=True, methods=["post"])
    @require_subscription
    def mark_favorite(self, request: Request, pk: int | None = None) -> Response:
        """Mark article as favorite (requires subscription)."""
        article = self.get_object()
        request.user.favorite_articles.add(article)
        return Response({"status": "marked as favorite"})

    @action(detail=False, methods=["post"])
    @rate_limit(max_requests=10, window_seconds=3600)
    def bulk_create(self, request: Request) -> Response:
        """Bulk create articles with rate limiting."""
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

---

## Request and Response Typing

### Request Object

```python
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from typing import Any


class ExampleView(APIView):
    """View demonstrating request typing."""

    def get(self, request: Request, format: str | None = None) -> Response:
        """Handle GET request."""
        # Query parameters
        page: str | None = request.query_params.get("page")
        page_size: str | None = request.query_params.get("page_size", "10")

        # Headers
        auth_token: str | None = request.META.get("HTTP_AUTHORIZATION")

        # User
        if request.user.is_authenticated:
            username: str = request.user.username

        # Content negotiation
        accepted_types: list[str] = request.accepted_renderer.media_type

        return Response({"message": "OK"})

    def post(self, request: Request, format: str | None = None) -> Response:
        """Handle POST request."""
        # Request data
        data: dict[str, Any] = request.data
        title: str = data.get("title", "")
        content: str = data.get("content", "")

        # Files
        if "file" in request.FILES:
            uploaded_file = request.FILES["file"]
            filename: str = uploaded_file.name
            size: int = uploaded_file.size

        # Create object
        article = Article.objects.create(
            title=title,
            content=content,
            author=request.user
        )

        serializer = ArticleSerializer(article)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

### Response Types

```python
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import status
from typing import Any


class ResponseExamplesView(APIView):
    """View demonstrating different response types."""

    def get(self, request: Request, format: str | None = None) -> Response:
        """Return different response types."""
        action = request.query_params.get("action", "default")

        if action == "json":
            # JSON response
            data: dict[str, Any] = {
                "message": "Hello",
                "count": 42,
                "items": ["a", "b", "c"]
            }
            return Response(data)

        elif action == "list":
            # List response
            items: list[dict[str, Any]] = [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
            ]
            return Response(items)

        elif action == "created":
            # Created response
            new_item: dict[str, Any] = {"id": 3, "name": "New Item"}
            return Response(new_item, status=status.HTTP_201_CREATED)

        elif action == "error":
            # Error response
            error_data: dict[str, Any] = {
                "error": "Something went wrong",
                "details": "More information here"
            }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        elif action == "no_content":
            # No content response
            return Response(status=status.HTTP_204_NO_CONTENT)

        else:
            # Default response
            return Response({"status": "ok"})
```

### Custom Response Classes

```python
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.request import Request
from typing import Any, OrderedDict
from collections import OrderedDict as OrderedDictType


class StandardResponse(Response):
    """Standard response format with metadata."""

    def __init__(
        self,
        data: Any = None,
        message: str = "",
        status: int | None = None,
        **kwargs: Any
    ) -> None:
        """Initialize response with standard format."""
        response_data: OrderedDictType[str, Any] = OrderedDict([
            ("success", 200 <= (status or 200) < 300),
            ("message", message),
            ("data", data),
        ])
        super().__init__(response_data, status=status, **kwargs)


class PaginatedResponse(Response):
    """Paginated response format."""

    def __init__(
        self,
        data: list[Any],
        count: int,
        page: int,
        page_size: int,
        status: int | None = None,
        **kwargs: Any
    ) -> None:
        """Initialize paginated response."""
        response_data: OrderedDictType[str, Any] = OrderedDict([
            ("count", count),
            ("page", page),
            ("page_size", page_size),
            ("total_pages", (count + page_size - 1) // page_size),
            ("results", data),
        ])
        super().__init__(response_data, status=status, **kwargs)


class ErrorResponse(Response):
    """Standardized error response."""

    def __init__(
        self,
        error: str,
        details: dict[str, Any] | None = None,
        status: int = 400,
        **kwargs: Any
    ) -> None:
        """Initialize error response."""
        response_data: OrderedDictType[str, Any] = OrderedDict([
            ("success", False),
            ("error", error),
        ])
        if details:
            response_data["details"] = details

        super().__init__(response_data, status=status, **kwargs)


class ArticleView(APIView):
    """View using custom responses."""

    def get(self, request: Request, pk: int) -> StandardResponse | ErrorResponse:
        """Get article by ID."""
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return ErrorResponse("Article not found", status=404)

        serializer = ArticleSerializer(article)
        return StandardResponse(
            data=serializer.data,
            message="Article retrieved successfully"
        )
```

---

## API Versioning

### URL Path Versioning

```python
from rest_framework import versioning, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import QuerySet
from typing import Any


class ArticleV1Serializer(serializers.ModelSerializer[Article]):
    """Version 1 serializer."""

    class Meta:
        model = Article
        fields = ["id", "title", "content"]


class ArticleV2Serializer(serializers.ModelSerializer[Article]):
    """Version 2 serializer with additional fields."""

    author_name: serializers.ReadOnlyField = serializers.ReadOnlyField(
        source="author.username"
    )

    class Meta:
        model = Article
        fields = ["id", "title", "content", "author", "author_name", "created_at"]


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """Versioned article viewset."""

    queryset: QuerySet[Article] = Article.objects.all()
    versioning_class = versioning.URLPathVersioning

    def get_serializer_class(self) -> type[serializers.Serializer[Article]]:
        """Return serializer based on API version."""
        if self.request.version == "v1":
            return ArticleV1Serializer
        return ArticleV2Serializer


# URL configuration
# path('api/v1/articles/', ArticleViewSet.as_view({'get': 'list'}))
# path('api/v2/articles/', ArticleViewSet.as_view({'get': 'list'}))
```

### Accept Header Versioning

```python
from rest_framework import versioning, viewsets
from rest_framework.request import Request
from django.db.models import QuerySet
from typing import Any


class AcceptHeaderVersioning(versioning.AcceptHeaderVersioning):
    """Custom accept header versioning."""

    allowed_versions = ["1.0", "2.0"]
    version_param = "version"


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with accept header versioning."""

    queryset: QuerySet[Article] = Article.objects.all()
    versioning_class = AcceptHeaderVersioning

    def get_serializer_class(self) -> type[serializers.Serializer[Article]]:
        """Return serializer based on version."""
        version = self.request.version

        if version == "1.0":
            return ArticleV1Serializer
        elif version == "2.0":
            return ArticleV2Serializer

        return ArticleV2Serializer  # Default to latest

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """List with version-specific behavior."""
        queryset = self.get_queryset()

        # Version 1: Only published articles
        if request.version == "1.0":
            queryset = queryset.filter(published=True)

        # Version 2: All articles with filtering

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Usage:
# GET /api/articles/
# Accept: application/json; version=1.0
```

### Namespace Versioning

```python
from rest_framework import versioning, viewsets
from django.db.models import QuerySet


class NamespaceVersioning(versioning.NamespaceVersioning):
    """Versioning based on URL namespace."""

    allowed_versions = ["v1", "v2"]
    default_version = "v2"


class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """ViewSet with namespace versioning."""

    queryset: QuerySet[Article] = Article.objects.all()
    versioning_class = NamespaceVersioning

    def get_serializer_class(self) -> type[serializers.Serializer[Article]]:
        """Return version-specific serializer."""
        if self.request.version == "v1":
            return ArticleV1Serializer
        return ArticleV2Serializer


# URL configuration
# app_name = 'v1'
# path('api/v1/', include((router.urls, 'v1')))
# path('api/v2/', include((router.urls, 'v2')))
```

---

## OpenAPI/Swagger Integration

### Schema Customization

```python
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from drf_spectacular.types import OpenApiTypes
from django.db.models import QuerySet
from typing import Any


@extend_schema_view(
    list=extend_schema(
        summary="List all articles",
        description="Get a paginated list of all articles.",
        parameters=[
            OpenApiParameter(
                name="published",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by published status",
            ),
            OpenApiParameter(
                name="author",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by author ID",
            ),
        ],
        responses={
            200: ArticleSerializer(many=True),
        },
    ),
    create=extend_schema(
        summary="Create a new article",
        description="Create a new article with the provided data.",
        request=ArticleSerializer,
        responses={
            201: ArticleSerializer,
            400: OpenApiResponse(description="Bad request"),
        },
        examples=[
            OpenApiExample(
                "Create Article Example",
                value={
                    "title": "Sample Article",
                    "content": "This is the article content.",
                    "published": False,
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get article details",
        description="Retrieve a single article by ID.",
        responses={
            200: ArticleDetailSerializer,
            404: OpenApiResponse(description="Article not found"),
        },
    ),
    update=extend_schema(
        summary="Update article",
        description="Update an existing article.",
        request=ArticleSerializer,
        responses={
            200: ArticleSerializer,
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Article not found"),
        },
    ),
    partial_update=extend_schema(
        summary="Partially update article",
        description="Update specific fields of an article.",
    ),
    destroy=extend_schema(
        summary="Delete article",
        description="Delete an article by ID.",
        responses={
            204: OpenApiResponse(description="Article deleted successfully"),
            404: OpenApiResponse(description="Article not found"),
        },
    ),
)
class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """
    ViewSet for managing articles.

    Provides CRUD operations for articles with filtering and search capabilities.
    """

    queryset: QuerySet[Article] = Article.objects.all()
    serializer_class = ArticleSerializer

    @extend_schema(
        summary="Publish an article",
        description="Mark an article as published.",
        request=None,
        responses={
            200: ArticleSerializer,
            400: OpenApiResponse(description="Article is already published"),
            404: OpenApiResponse(description="Article not found"),
        },
    )
    @action(detail=True, methods=["post"])
    def publish(self, request: Request, pk: int | None = None) -> Response:
        """Publish an article."""
        article = self.get_object()

        if article.published:
            return Response(
                {"error": "Article is already published"},
                status=400
            )

        article.published = True
        article.save()

        serializer = self.get_serializer(article)
        return Response(serializer.data)

    @extend_schema(
        summary="Get article statistics",
        description="Get statistics about articles.",
        request=None,
        responses={
            200: OpenApiResponse(
                description="Statistics",
                response={
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "published": {"type": "integer"},
                        "draft": {"type": "integer"},
                    },
                },
            ),
        },
    )
    @action(detail=False, methods=["get"])
    def stats(self, request: Request) -> Response:
        """Get article statistics."""
        queryset = self.get_queryset()

        stats = {
            "total": queryset.count(),
            "published": queryset.filter(published=True).count(),
            "draft": queryset.filter(published=False).count(),
        }

        return Response(stats)
```

### Custom Schema Fields

```python
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from typing import Any


class ArticleSerializer(serializers.ModelSerializer[Article]):
    """Article serializer with documented fields."""

    @extend_schema_field(OpenApiTypes.STR)
    def get_preview(self, obj: Article) -> str:
        """Get article preview."""
        return obj.content[:100]

    preview: serializers.SerializerMethodField = serializers.SerializerMethodField(
        help_text="First 100 characters of content"
    )

    @extend_schema_field(OpenApiTypes.INT)
    def get_word_count(self, obj: Article) -> int:
        """Get word count."""
        return len(obj.content.split())

    word_count: serializers.SerializerMethodField = serializers.SerializerMethodField(
        help_text="Total number of words in content"
    )

    class Meta:
        model = Article
        fields = ["id", "title", "content", "preview", "word_count"]
```

### Schema Settings

```python
# settings.py

INSTALLED_APPS = [
    # ...
    "drf_spectacular",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "My API",
    "DESCRIPTION": "API documentation for My Project",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,

    # Schema generation
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "DEFAULT_GENERATOR_CLASS": "drf_spectacular.generators.SchemaGenerator",

    # Swagger UI settings
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },

    # Component settings
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,

    # Enum settings
    "ENUM_NAME_OVERRIDES": {
        "ValidationErrorEnum": "drf_spectacular.validation.ValidationErrorEnum.choices",
    },
}
```

---

## Testing

### ViewSet Testing

```python
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from typing import Any


class ArticleViewSetTest(APITestCase):
    """Tests for ArticleViewSet."""

    client: APIClient
    user: User
    article: Article

    def setUp(self) -> None:
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        self.article = Article.objects.create(
            title="Test Article",
            content="Test content",
            author=self.user,
            published=False
        )

        self.client = APIClient()

    def test_list_articles(self) -> None:
        """Test listing articles."""
        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_retrieve_article(self) -> None:
        """Test retrieving a single article."""
        response = self.client.get(f"/api/articles/{self.article.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.article.id)
        self.assertEqual(response.data["title"], self.article.title)

    def test_create_article_authenticated(self) -> None:
        """Test creating article when authenticated."""
        self.client.force_authenticate(user=self.user)

        data: dict[str, Any] = {
            "title": "New Article",
            "content": "New content",
            "published": False,
        }

        response = self.client.post("/api/articles/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], data["title"])
        self.assertEqual(Article.objects.count(), 2)

    def test_create_article_unauthenticated(self) -> None:
        """Test creating article without authentication."""
        data: dict[str, Any] = {
            "title": "New Article",
            "content": "New content",
        }

        response = self.client.post("/api/articles/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_article(self) -> None:
        """Test updating an article."""
        self.client.force_authenticate(user=self.user)

        data: dict[str, Any] = {
            "title": "Updated Title",
            "content": "Updated content",
        }

        response = self.client.patch(
            f"/api/articles/{self.article.id}/",
            data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], data["title"])

        self.article.refresh_from_db()
        self.assertEqual(self.article.title, data["title"])

    def test_delete_article(self) -> None:
        """Test deleting an article."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f"/api/articles/{self.article.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Article.objects.count(), 0)

    def test_publish_action(self) -> None:
        """Test publish custom action."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f"/api/articles/{self.article.id}/publish/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.article.refresh_from_db()
        self.assertTrue(self.article.published)

    def test_stats_action(self) -> None:
        """Test stats custom action."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/articles/stats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)
        self.assertIn("published", response.data)
        self.assertIn("draft", response.data)
```

### Serializer Testing

```python
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from typing import Any


class ArticleSerializerTest(APITestCase):
    """Tests for ArticleSerializer."""

    user: User

    def setUp(self) -> None:
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com"
        )

    def test_serializer_with_valid_data(self) -> None:
        """Test serializer with valid data."""
        data: dict[str, Any] = {
            "title": "Test Article",
            "content": "Test content",
            "published": False,
        }

        serializer = ArticleSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        article = serializer.save(author=self.user)

        self.assertEqual(article.title, data["title"])
        self.assertEqual(article.content, data["content"])
        self.assertEqual(article.author, self.user)

    def test_serializer_with_invalid_data(self) -> None:
        """Test serializer with invalid data."""
        data: dict[str, Any] = {
            "title": "Bad",  # Too short
            "content": "",
        }

        serializer = ArticleSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_serializer_read_only_fields(self) -> None:
        """Test that read-only fields are not writable."""
        article = Article.objects.create(
            title="Original",
            content="Content",
            author=self.user
        )

        data: dict[str, Any] = {
            "id": 999,  # Should be ignored
            "title": "Updated",
            "created_at": "2020-01-01",  # Should be ignored
        }

        serializer = ArticleSerializer(article, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_article = serializer.save()

        self.assertNotEqual(updated_article.id, 999)
        self.assertEqual(updated_article.title, "Updated")

    def test_nested_serializer(self) -> None:
        """Test serializer with nested relations."""
        article = Article.objects.create(
            title="Test",
            content="Content",
            author=self.user
        )

        serializer = ArticleDetailSerializer(article)

        self.assertIn("author", serializer.data)
        self.assertEqual(serializer.data["author"]["username"], self.user.username)
```

### Permission Testing

```python
from rest_framework.test import APITestCase, force_authenticate
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User


class PermissionTest(APITestCase):
    """Tests for custom permissions."""

    factory: APIRequestFactory
    user: User
    other_user: User
    article: Article

    def setUp(self) -> None:
        """Set up test data."""
        self.factory = APIRequestFactory()

        self.user = User.objects.create_user(
            username="owner",
            email="owner@example.com"
        )

        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com"
        )

        self.article = Article.objects.create(
            title="Test",
            content="Content",
            author=self.user
        )

    def test_is_owner_permission(self) -> None:
        """Test IsOwnerOrReadOnly permission."""
        from .permissions import IsOwnerOrReadOnly

        permission = IsOwnerOrReadOnly()

        # Test read permission for non-owner
        request = self.factory.get("/")
        force_authenticate(request, user=self.other_user)

        self.assertTrue(
            permission.has_object_permission(request, None, self.article)
        )

        # Test write permission for owner
        request = self.factory.put("/")
        force_authenticate(request, user=self.user)

        self.assertTrue(
            permission.has_object_permission(request, None, self.article)
        )

        # Test write permission for non-owner
        request = self.factory.put("/")
        force_authenticate(request, user=self.other_user)

        self.assertFalse(
            permission.has_object_permission(request, None, self.article)
        )
```

### Pagination Testing

```python
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


class PaginationTest(APITestCase):
    """Tests for pagination."""

    user: User

    def setUp(self) -> None:
        """Create test articles."""
        self.user = User.objects.create_user(username="test")

        # Create 25 articles
        for i in range(25):
            Article.objects.create(
                title=f"Article {i}",
                content=f"Content {i}",
                author=self.user
            )

    def test_default_pagination(self) -> None:
        """Test default pagination."""
        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 10)  # Default page size

    def test_custom_page_size(self) -> None:
        """Test custom page size parameter."""
        response = self.client.get("/api/articles/?page_size=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 5)

    def test_pagination_links(self) -> None:
        """Test pagination navigation links."""
        response = self.client.get("/api/articles/")

        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

        # Get second page
        response = self.client.get("/api/articles/?page=2")

        self.assertIsNotNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])
```

### Filter Testing

```python
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


class FilterTest(APITestCase):
    """Tests for filtering."""

    user: User
    published_article: Article
    draft_article: Article

    def setUp(self) -> None:
        """Create test data."""
        self.user = User.objects.create_user(username="test")

        self.published_article = Article.objects.create(
            title="Published",
            content="Content",
            author=self.user,
            published=True
        )

        self.draft_article = Article.objects.create(
            title="Draft",
            content="Content",
            author=self.user,
            published=False
        )

    def test_filter_by_published(self) -> None:
        """Test filtering by published status."""
        response = self.client.get("/api/articles/?published=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.published_article.id)

    def test_search_by_title(self) -> None:
        """Test searching by title."""
        response = self.client.get("/api/articles/?search=Published")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Published")

    def test_ordering(self) -> None:
        """Test ordering results."""
        response = self.client.get("/api/articles/?ordering=-created_at")

        self.assertEqual(response.status_code, 200)
        # Most recent first
        self.assertEqual(response.data[0]["id"], self.draft_article.id)
```

---

## Best Practices

### 1. Always Use Generic Type Parameters

```python
# Good
class ArticleSerializer(serializers.ModelSerializer[Article]):
    pass

# Bad
class ArticleSerializer(serializers.ModelSerializer):
    pass
```

### 2. Type Request and Response

```python
# Good
def my_view(request: Request) -> Response:
    return Response({"status": "ok"})

# Bad
def my_view(request):
    return Response({"status": "ok"})
```

### 3. Use Type Hints for Serializer Methods

```python
# Good
def get_preview(self, obj: Article) -> str:
    return obj.content[:100]

# Bad
def get_preview(self, obj):
    return obj.content[:100]
```

### 4. Annotate QuerySets

```python
# Good
queryset: QuerySet[Article] = Article.objects.all()

# Bad
queryset = Article.objects.all()
```

### 5. Type Custom Permissions

```python
# Good
def has_object_permission(
    self,
    request: Request,
    view: APIView,
    obj: Article
) -> bool:
    return obj.author == request.user

# Bad
def has_object_permission(self, request, view, obj):
    return obj.author == request.user
```

---

## Common Type Errors and Solutions

### Error: Need type annotation for 'queryset'

```python
# Error
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()

# Fix
class ArticleViewSet(viewsets.ModelViewSet[Article]):
    queryset: QuerySet[Article] = Article.objects.all()
```

### Error: Incompatible type for serializer_class

```python
# Error
def get_serializer_class(self):
    return ArticleSerializer

# Fix
def get_serializer_class(self) -> type[serializers.Serializer[Article]]:
    return ArticleSerializer
```

### Error: Cannot determine type of SerializerMethodField

```python
# Error
preview = serializers.SerializerMethodField()
def get_preview(self, obj):
    return obj.content[:100]

# Fix
preview: serializers.SerializerMethodField = serializers.SerializerMethodField()
def get_preview(self, obj: Article) -> str:
    return obj.content[:100]
```

---

## Resources

- [djangorestframework-stubs GitHub](https://github.com/typeddjango/djangorestframework-stubs)
- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
