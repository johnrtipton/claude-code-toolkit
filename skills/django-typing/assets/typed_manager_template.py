"""
Comprehensive Django Manager and QuerySet Type Hints Template

This template demonstrates best practices for typing custom Django managers and querysets,
including generic types, proper return type annotations, and common patterns used in
Django applications.

Key Concepts:
- Generic QuerySets that maintain type information through chaining
- Manager.from_queryset() pattern with proper typing
- Type-safe custom filtering and aggregation methods
- Advanced patterns (soft delete, published, tenant-aware)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from django.db import models
from django.db.models import (
    Avg,
    Case,
    Count,
    F,
    Max,
    Min,
    Prefetch,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models.manager import Manager

# ==============================================================================
# GENERIC TYPE VARIABLES
# ==============================================================================

# TypeVar for the model class - used to maintain type information through chains
_T = TypeVar("_T", bound=models.Model)

# TypeVar specifically for models with soft delete functionality
_SoftDeleteModel = TypeVar("_SoftDeleteModel", bound="SoftDeleteMixin")

# TypeVar for publishable models
_PublishableModel = TypeVar("_PublishableModel", bound="PublishableMixin")

# TypeVar for tenant-aware models
_TenantModel = TypeVar("_TenantModel", bound="TenantAwareMixin")


# ==============================================================================
# BASE GENERIC QUERYSET
# ==============================================================================


class TypedQuerySet(QuerySet[_T], Generic[_T]):
    """
    Base generic QuerySet that maintains type information through method chaining.

    This class demonstrates:
    - Proper use of Generic[_T] to maintain model type
    - Return type annotations that preserve the QuerySet type
    - Common filtering patterns with type safety
    """

    def active(self) -> TypedQuerySet[_T]:
        """
        Filter to active records only.

        Returns:
            TypedQuerySet[_T]: Maintains the generic type through chaining
        """
        return self.filter(is_active=True)

    def inactive(self) -> TypedQuerySet[_T]:
        """Filter to inactive records."""
        return self.filter(is_active=False)

    def created_after(self, date: datetime) -> TypedQuerySet[_T]:
        """
        Filter records created after a specific date.

        Args:
            date: The datetime to filter from

        Returns:
            TypedQuerySet[_T]: Filtered queryset maintaining type
        """
        return self.filter(created_at__gte=date)

    def created_before(self, date: datetime) -> TypedQuerySet[_T]:
        """Filter records created before a specific date."""
        return self.filter(created_at__lte=date)

    def created_between(self, start: datetime, end: datetime) -> TypedQuerySet[_T]:
        """Filter records created between two dates."""
        return self.filter(created_at__gte=start, created_at__lte=end)

    def with_annotations(self) -> TypedQuerySet[_T]:
        """
        Add common annotations to the queryset.
        This is a placeholder that subclasses can override.
        """
        return self

    def search(self, query: str) -> TypedQuerySet[_T]:
        """
        Basic search implementation - override in subclasses.

        Args:
            query: Search term

        Returns:
            TypedQuerySet[_T]: Filtered queryset
        """
        return self

    def ordered(self) -> TypedQuerySet[_T]:
        """
        Apply default ordering - override in subclasses.

        Returns:
            TypedQuerySet[_T]: Ordered queryset
        """
        return self.order_by("-created_at")


# ==============================================================================
# SOFT DELETE QUERYSET AND MANAGER
# ==============================================================================


class SoftDeleteMixin(models.Model):
    """
    Mixin for models that support soft deletion.
    Models using this must have a deleted_at field.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(TypedQuerySet[_SoftDeleteModel]):
    """
    QuerySet for models with soft delete functionality.

    Demonstrates:
    - Filtering out deleted records by default
    - Methods to include/exclude deleted records
    - Soft delete operation
    """

    def delete(self) -> tuple[int, dict[str, int]]:
        """
        Soft delete - sets deleted_at instead of actually deleting.

        Returns:
            Tuple of (number of records marked as deleted, dict of model counts)
        """
        count = self.update(deleted_at=timezone.now())
        return count, {self.model._meta.label: count}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """
        Actually delete records from the database.
        Use with caution!
        """
        return super().delete()

    def alive(self) -> SoftDeleteQuerySet[_SoftDeleteModel]:
        """Filter to non-deleted records only."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> SoftDeleteQuerySet[_SoftDeleteModel]:
        """Filter to deleted records only."""
        return self.filter(deleted_at__isnull=False)

    def with_deleted(self) -> SoftDeleteQuerySet[_SoftDeleteModel]:
        """
        Include both deleted and non-deleted records.
        Useful when you need to see everything.
        """
        return self

    def restore(self) -> int:
        """
        Restore soft-deleted records.

        Returns:
            Number of records restored
        """
        return self.update(deleted_at=None)


class SoftDeleteManager(models.Manager[_SoftDeleteModel]):
    """
    Manager for soft delete models.

    By default, excludes deleted records. Use deleted() or with_deleted()
    to access them.
    """

    def get_queryset(self) -> SoftDeleteQuerySet[_SoftDeleteModel]:
        """
        Return queryset that excludes soft-deleted records by default.

        Returns:
            SoftDeleteQuerySet filtered to non-deleted records
        """
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def deleted(self) -> SoftDeleteQuerySet[_SoftDeleteModel]:
        """Get only deleted records."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()

    def with_deleted(self) -> SoftDeleteQuerySet[_SoftDeleteModel]:
        """Get all records including deleted."""
        return SoftDeleteQuerySet(self.model, using=self._db)


# ==============================================================================
# PUBLISHABLE QUERYSET AND MANAGER
# ==============================================================================


class PublishableMixin(models.Model):
    """
    Mixin for models with published/draft status.
    Models using this must have published and publish_date fields.
    """

    published = models.BooleanField(default=False, db_index=True)
    publish_date = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True


class PublishableQuerySet(TypedQuerySet[_PublishableModel]):
    """
    QuerySet for publishable models.

    Handles both a published flag and a publish_date for scheduled publishing.
    """

    def published(self) -> PublishableQuerySet[_PublishableModel]:
        """
        Filter to published records.
        Checks both the published flag and that publish_date is in the past.
        """
        now = timezone.now()
        return self.filter(
            Q(published=True)
            & (Q(publish_date__isnull=True) | Q(publish_date__lte=now))
        )

    def draft(self) -> PublishableQuerySet[_PublishableModel]:
        """Filter to draft (unpublished) records."""
        return self.filter(published=False)

    def scheduled(self) -> PublishableQuerySet[_PublishableModel]:
        """Filter to records scheduled for future publication."""
        now = timezone.now()
        return self.filter(published=True, publish_date__gt=now)

    def publish(self) -> int:
        """
        Publish all records in the queryset.

        Returns:
            Number of records published
        """
        return self.update(published=True, publish_date=timezone.now())

    def unpublish(self) -> int:
        """Unpublish all records in the queryset."""
        return self.update(published=False)


class PublishedManager(models.Manager[_PublishableModel]):
    """
    Manager that returns only published records by default.
    """

    def get_queryset(self) -> PublishableQuerySet[_PublishableModel]:
        """Return only published records."""
        return PublishableQuerySet(self.model, using=self._db).published()


# ==============================================================================
# TENANT-AWARE QUERYSET AND MANAGER
# ==============================================================================


class TenantAwareMixin(models.Model):
    """
    Mixin for multi-tenant models.
    Models using this must have a tenant field.
    """

    # In a real app, this would be a ForeignKey to a Tenant model
    tenant_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


class TenantAwareQuerySet(TypedQuerySet[_TenantModel]):
    """
    QuerySet that filters records by tenant.

    Demonstrates:
    - Tenant isolation patterns
    - Filtering by current tenant context
    """

    def for_tenant(self, tenant_id: int) -> TenantAwareQuerySet[_TenantModel]:
        """
        Filter records for a specific tenant.

        Args:
            tenant_id: The tenant ID to filter by

        Returns:
            Filtered queryset for the tenant
        """
        return self.filter(tenant_id=tenant_id)

    def shared(self) -> TenantAwareQuerySet[_TenantModel]:
        """
        Filter to records shared across all tenants.
        Assumes tenant_id=0 means shared.
        """
        return self.filter(tenant_id=0)


class TenantAwareManager(models.Manager[_TenantModel]):
    """
    Manager for tenant-aware models.

    In a real application, you'd typically set the tenant context
    at the request level and filter automatically.
    """

    def get_queryset(self) -> TenantAwareQuerySet[_TenantModel]:
        """Return base tenant-aware queryset."""
        return TenantAwareQuerySet(self.model, using=self._db)


# ==============================================================================
# EXAMPLE: ARTICLE MODEL WITH CUSTOM QUERYSET
# ==============================================================================


class ArticleQuerySet(TypedQuerySet["Article"]):
    """
    Custom QuerySet for Article model.

    Demonstrates:
    - Domain-specific filtering methods
    - Aggregations with proper typing
    - Complex annotations
    - Search functionality
    """

    def published(self) -> ArticleQuerySet:
        """Filter to published articles."""
        return self.filter(status="published", publish_date__lte=timezone.now())

    def draft(self) -> ArticleQuerySet:
        """Filter to draft articles."""
        return self.filter(status="draft")

    def by_author(self, author_id: int) -> ArticleQuerySet:
        """Filter articles by author ID."""
        return self.filter(author_id=author_id)

    def featured(self) -> ArticleQuerySet:
        """Filter to featured articles."""
        return self.filter(is_featured=True)

    def in_category(self, category_id: int) -> ArticleQuerySet:
        """Filter articles in a specific category."""
        return self.filter(category_id=category_id)

    def with_view_count(self) -> ArticleQuerySet:
        """Annotate queryset with view count from related views."""
        return self.annotate(view_count=Count("views"))

    def with_comment_count(self) -> ArticleQuerySet:
        """Annotate with comment count."""
        return self.annotate(comment_count=Count("comments"))

    def with_stats(self) -> ArticleQuerySet:
        """Annotate with comprehensive stats."""
        return self.annotate(
            view_count=Count("views"),
            comment_count=Count("comments"),
            like_count=Count("likes"),
            avg_rating=Avg("ratings__score"),
        )

    def popular(self, threshold: int = 100) -> ArticleQuerySet:
        """
        Filter to popular articles based on view count.

        Args:
            threshold: Minimum number of views to be considered popular
        """
        return self.with_view_count().filter(view_count__gte=threshold)

    def recent(self, days: int = 7) -> ArticleQuerySet:
        """
        Filter to recently published articles.

        Args:
            days: Number of days to look back
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(publish_date__gte=cutoff)

    def search(self, query: str) -> ArticleQuerySet:
        """
        Search articles by title and content.

        Args:
            query: Search term
        """
        return self.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )

    def ordered(self) -> ArticleQuerySet:
        """Return articles in default order (newest first)."""
        return self.order_by("-publish_date", "-created_at")


class Article(models.Model):
    """
    Example Article model using custom manager.

    Demonstrates:
    - Using Manager.from_queryset() for type-safe manager
    - Multiple managers for different default querysets
    """

    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[("draft", "Draft"), ("published", "Published")],
    )
    publish_date = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    author_id = models.IntegerField()
    category_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Default manager with all articles
    objects: ClassVar[models.Manager[Article]] = models.Manager.from_queryset(
        ArticleQuerySet
    )()

    # Published manager - only returns published articles
    published_objects: ClassVar[
        models.Manager[Article]
    ] = models.Manager.from_queryset(ArticleQuerySet)()

    class Meta:
        ordering = ["-publish_date"]

    def __str__(self) -> str:
        return self.title


# ==============================================================================
# EXAMPLE: PRODUCT MODEL WITH INVENTORY QUERYSET
# ==============================================================================


class ProductQuerySet(TypedQuerySet["Product"]):
    """
    QuerySet for Product model with inventory and pricing methods.
    """

    def in_stock(self) -> ProductQuerySet:
        """Filter to products that are in stock."""
        return self.filter(stock_quantity__gt=0)

    def out_of_stock(self) -> ProductQuerySet:
        """Filter to products that are out of stock."""
        return self.filter(stock_quantity=0)

    def low_stock(self, threshold: int = 10) -> ProductQuerySet:
        """
        Filter to products with low stock levels.

        Args:
            threshold: Stock quantity considered low
        """
        return self.filter(stock_quantity__lte=threshold, stock_quantity__gt=0)

    def active(self) -> ProductQuerySet:
        """Filter to active products."""
        return self.filter(is_active=True)

    def in_price_range(
        self, min_price: Decimal, max_price: Decimal
    ) -> ProductQuerySet:
        """
        Filter products within a price range.

        Args:
            min_price: Minimum price
            max_price: Maximum price
        """
        return self.filter(price__gte=min_price, price__lte=max_price)

    def with_discount(self) -> ProductQuerySet:
        """Filter to products that have a discount applied."""
        return self.filter(discount_percentage__gt=0)

    def with_final_price(self) -> ProductQuerySet:
        """Annotate with calculated final price after discount."""
        return self.annotate(
            final_price=Case(
                When(
                    discount_percentage__gt=0,
                    then=F("price") * (100 - F("discount_percentage")) / 100,
                ),
                default=F("price"),
            )
        )

    def by_category(self, category_id: int) -> ProductQuerySet:
        """Filter products by category."""
        return self.filter(category_id=category_id)

    def bestsellers(self, limit: int = 10) -> ProductQuerySet:
        """
        Get bestselling products based on sales count.

        Args:
            limit: Number of products to return
        """
        return (
            self.annotate(sales_count=Count("orders"))
            .order_by("-sales_count")[:limit]
        )

    def with_inventory_value(self) -> ProductQuerySet:
        """Annotate with total inventory value (price * quantity)."""
        return self.annotate(inventory_value=F("price") * F("stock_quantity"))

    def search(self, query: str) -> ProductQuerySet:
        """Search products by name and description."""
        return self.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )


class Product(models.Model):
    """Example Product model with inventory management."""

    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    stock_quantity = models.IntegerField(default=0)
    category_id = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: ClassVar[models.Manager[Product]] = models.Manager.from_queryset(
        ProductQuerySet
    )()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# ==============================================================================
# EXAMPLE: USER MODEL WITH CUSTOM MANAGER
# ==============================================================================


class UserQuerySet(TypedQuerySet["User"]):
    """
    QuerySet for User model.

    Demonstrates user-specific filtering patterns.
    """

    def active(self) -> UserQuerySet:
        """Filter to active users."""
        return self.filter(is_active=True, email_verified=True)

    def inactive(self) -> UserQuerySet:
        """Filter to inactive users."""
        return self.filter(is_active=False)

    def verified(self) -> UserQuerySet:
        """Filter to users with verified email."""
        return self.filter(email_verified=True)

    def unverified(self) -> UserQuerySet:
        """Filter to users with unverified email."""
        return self.filter(email_verified=False)

    def premium(self) -> UserQuerySet:
        """Filter to premium/paid users."""
        return self.filter(is_premium=True)

    def registered_after(self, date: datetime) -> UserQuerySet:
        """Filter users registered after a date."""
        return self.filter(date_joined__gte=date)

    def with_login_stats(self) -> UserQuerySet:
        """Annotate with login statistics."""
        return self.annotate(
            login_count=Count("logins"),
            last_login_date=Max("logins__login_date"),
        )

    def search(self, query: str) -> UserQuerySet:
        """Search users by username, email, or name."""
        return self.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )


class User(models.Model):
    """Example User model with custom manager."""

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects: ClassVar[models.Manager[User]] = models.Manager.from_queryset(
        UserQuerySet
    )()

    def __str__(self) -> str:
        return self.username


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================

"""
Example usage patterns demonstrating type-safe manager and queryset operations:

# Basic filtering with type preservation
articles = Article.objects.published().featured()
# Type: QuerySet[Article]

# Chaining custom methods
recent_popular = Article.objects.recent(days=30).popular(threshold=1000)
# Type: ArticleQuerySet -> maintains custom methods

# Using multiple managers
all_articles = Article.objects.all()  # All articles
published = Article.published_objects.all()  # Only published

# Aggregations with annotations
top_articles = (
    Article.objects
    .published()
    .with_stats()
    .order_by("-view_count")[:10]
)

# Complex queries with Q objects
searched = Article.objects.search("django").published().recent()

# Product inventory operations
low_stock_products = Product.objects.active().low_stock(threshold=5)

# Products with calculated fields
discounted = (
    Product.objects
    .with_discount()
    .with_final_price()
    .order_by("final_price")
)

# User filtering
active_premium_users = User.objects.active().premium()

# Soft delete operations
from typing import cast
# Assuming Article used SoftDeleteQuerySet
deleted = cast(SoftDeleteQuerySet[Article], Article.objects.deleted())
deleted.restore()  # Restore all deleted articles

# Tenant-aware queries
# Assuming Product was tenant-aware
tenant_products = cast(
    TenantAwareQuerySet[Product],
    Product.objects.for_tenant(tenant_id=123)
)
"""
