"""
Comprehensive Django Model Template with Type Hints

This template demonstrates proper typing for Django models including:
- All common field types with correct type annotations
- Relationships (ForeignKey, OneToOneField, ManyToManyField)
- Model properties and methods with return types
- Custom managers and querysets
- Model choices using TextChoices and IntegerChoices
- Abstract base models for common patterns
- Model validation and clean methods
- Meta options
- String representations with proper typing

Type Hints Best Practices:
1. Use TYPE_CHECKING imports to avoid circular imports
2. Use string literals for forward references when needed
3. Use django-stubs for proper Django type support
4. Annotate RelatedManager and QuerySet types correctly
5. Use Self for methods that return the model instance (Python 3.11+)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Self

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    CASCADE,
    PROTECT,
    SET_NULL,
    Case,
    Count,
    F,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# TYPE_CHECKING imports are only used for type hints, not at runtime
# This prevents circular imports and reduces runtime overhead
if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    # Import related models only for type checking
    # from myapp.models import Category, Review, User


# ============================================================================
# Abstract Base Models - Reusable patterns for common model functionality
# ============================================================================


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating created and modified fields.

    Usage:
        class MyModel(TimeStampedModel):
            name = models.CharField(max_length=100)

    Type Hints:
        - created_at: datetime - automatically set on creation
        - updated_at: datetime - automatically updated on save
    """

    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
        help_text=_("Timestamp when the record was created"),
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
        help_text=_("Timestamp when the record was last updated"),
    )

    class Meta:
        abstract = True
        # These field names will be used in subclasses for ordering
        ordering = ["-created_at"]

    def was_recently_created(self, days: int = 7) -> bool:
        """
        Check if the model instance was created within the last N days.

        Args:
            days: Number of days to check (default: 7)

        Returns:
            bool: True if created within the specified days
        """
        now = timezone.now()
        return self.created_at >= now - timezone.timedelta(days=days)


class UUIDModel(models.Model):
    """
    Abstract base model using UUID as primary key instead of auto-incrementing ID.

    Benefits:
        - Globally unique identifiers
        - Prevents ID enumeration attacks
        - Better for distributed systems

    Type Hints:
        - id: uuid.UUID - the primary key field
    """

    id: models.UUIDField = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(QuerySet["SoftDeleteModel"]):
    """
    Custom QuerySet for soft delete functionality.

    Type Hints:
        - Generic parameter: SoftDeleteModel - ensures type safety for chained methods
    """

    def delete(self) -> tuple[int, dict[str, int]]:
        """
        Soft delete: mark records as deleted instead of removing from database.

        Returns:
            tuple: (count of affected rows, dict of model counts)
        """
        count = self.update(deleted_at=timezone.now())
        return count, {self.model._meta.label: count}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """
        Permanently delete records from the database.

        Returns:
            tuple: (count of deleted objects, dict of model counts)
        """
        return super().delete()

    def alive(self) -> SoftDeleteQuerySet[SoftDeleteModel]:
        """
        Filter to only non-deleted records.

        Returns:
            QuerySet: Filtered queryset of non-deleted records
        """
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> SoftDeleteQuerySet[SoftDeleteModel]:
        """
        Filter to only deleted records.

        Returns:
            QuerySet: Filtered queryset of deleted records
        """
        return self.filter(deleted_at__isnull=False)


class SoftDeleteModel(models.Model):
    """
    Abstract base model that implements soft deletion.

    Soft deletion marks records as deleted without removing them from the database.
    This allows for data recovery and maintains referential integrity.

    Type Hints:
        - deleted_at: datetime | None - timestamp when soft deleted, None if active
    """

    deleted_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Deleted at"),
        help_text=_("Timestamp when the record was soft deleted"),
    )

    # Custom manager with soft delete support
    objects: ClassVar[SoftDeleteQuerySet[Self]] = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(
        self, using: Any = None, keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        """
        Soft delete the instance.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent records in MTI

        Returns:
            tuple: (1, dict with model count)
        """
        self.deleted_at = timezone.now()
        self.save(using=using)
        return 1, {self._meta.label: 1}

    def hard_delete(self, using: Any = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        """
        Permanently delete the instance from the database.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent records in MTI

        Returns:
            tuple: (count of deleted objects, dict of model counts)
        """
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self) -> None:
        """Restore a soft-deleted instance."""
        self.deleted_at = None
        self.save()

    @property
    def is_deleted(self) -> bool:
        """Check if the instance is soft deleted."""
        return self.deleted_at is not None


# ============================================================================
# Model Choices - Type-safe choice fields using TextChoices/IntegerChoices
# ============================================================================


class ProductStatus(models.TextChoices):
    """
    Status choices for products using TextChoices.

    Benefits of TextChoices:
        - Type-safe choice values
        - IDE autocomplete support
        - Human-readable database values
        - Built-in label translations

    Usage:
        status = models.CharField(max_length=20, choices=ProductStatus.choices)
        if product.status == ProductStatus.ACTIVE:
            # Type checker knows this is valid
    """

    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    DISCONTINUED = "discontinued", _("Discontinued")


class PriorityLevel(models.IntegerChoices):
    """
    Priority levels using IntegerChoices.

    Benefits:
        - Numeric values for ordering/comparison
        - Type-safe integer choices
        - Efficient database storage
    """

    LOW = 1, _("Low")
    MEDIUM = 2, _("Medium")
    HIGH = 3, _("High")
    URGENT = 4, _("Urgent")


# ============================================================================
# Custom QuerySet and Manager Examples
# ============================================================================


class ProductQuerySet(models.QuerySet["Product"]):
    """
    Custom QuerySet for Product model with business logic.

    Type Hints:
        - Generic parameter ["Product"] ensures all methods return correctly typed QuerySets
        - Methods should return Self or ProductQuerySet for proper chaining
    """

    def active(self) -> ProductQuerySet[Product]:
        """Filter to only active products."""
        return self.filter(status=ProductStatus.ACTIVE)

    def available(self) -> ProductQuerySet[Product]:
        """Filter to products that are in stock."""
        return self.filter(stock_quantity__gt=0, status=ProductStatus.ACTIVE)

    def by_category(self, category: Category) -> ProductQuerySet[Product]:
        """
        Filter products by category.

        Args:
            category: Category instance to filter by

        Returns:
            QuerySet: Filtered products
        """
        return self.filter(category=category)

    def with_review_stats(self) -> ProductQuerySet[Product]:
        """
        Annotate products with review statistics.

        Returns:
            QuerySet: Products with review_count and avg_rating annotations
        """
        return self.annotate(
            review_count=Count("reviews"),
            avg_rating=Coalesce(models.Avg("reviews__rating"), Value(0.0)),
        )

    def low_stock(self, threshold: int = 10) -> ProductQuerySet[Product]:
        """
        Filter to products with low stock.

        Args:
            threshold: Stock quantity threshold (default: 10)

        Returns:
            QuerySet: Products with stock below threshold
        """
        return self.filter(stock_quantity__lte=threshold, status=ProductStatus.ACTIVE)

    def expensive(self, min_price: Decimal = Decimal("100.00")) -> ProductQuerySet[Product]:
        """
        Filter to expensive products.

        Args:
            min_price: Minimum price threshold

        Returns:
            QuerySet: Products above price threshold
        """
        return self.filter(price__gte=min_price)


class ProductManager(models.Manager["Product"]):
    """
    Custom Manager for Product model.

    Type Hints:
        - Generic parameter ["Product"] ensures get_queryset returns correct type
        - Inherit from models.Manager with generic parameter for type safety
    """

    def get_queryset(self) -> ProductQuerySet[Product]:
        """
        Return custom QuerySet.

        Returns:
            ProductQuerySet: Custom queryset with additional methods
        """
        return ProductQuerySet(self.model, using=self._db)

    def active(self) -> ProductQuerySet[Product]:
        """Shortcut for active products."""
        return self.get_queryset().active()

    def create_product(
        self,
        name: str,
        slug: str,
        price: Decimal,
        category: Category,
        **kwargs: Any,
    ) -> Product:
        """
        Create a new product with validation.

        Args:
            name: Product name
            slug: URL-friendly slug
            price: Product price
            category: Category instance
            **kwargs: Additional fields

        Returns:
            Product: Created product instance

        Raises:
            ValidationError: If validation fails
        """
        product = self.model(
            name=name,
            slug=slug,
            price=price,
            category=category,
            **kwargs,
        )
        product.full_clean()  # Validate before saving
        product.save()
        return product


# ============================================================================
# Example Models - Complete implementation with all field types
# ============================================================================


class Category(TimeStampedModel):
    """
    Product category model demonstrating tree structure with self-referencing FK.

    Type Hints for Relations:
        - parent: Category | None - optional self-reference
        - children: RelatedManager[Category] - reverse relation (auto-generated)
        - products: RelatedManager[Product] - reverse relation from Product.category
    """

    name: models.CharField = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Name"),
    )
    slug: models.SlugField = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Slug"),
    )
    description: models.TextField = models.TextField(
        blank=True,
        verbose_name=_("Description"),
    )
    parent: models.ForeignKey = models.ForeignKey(
        "self",  # Self-referencing FK for tree structure
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent Category"),
    )
    is_active: models.BooleanField = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
    )

    # Reverse relations (created by Django, shown here for documentation)
    if TYPE_CHECKING:
        children: RelatedManager[Category]
        products: RelatedManager[Product]

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent", "is_active"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return self.name

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<Category: {self.name} (id={self.pk})>"

    @property
    def full_path(self) -> str:
        """
        Get full category path (e.g., "Electronics > Computers > Laptops").

        Returns:
            str: Full category path with parent hierarchy
        """
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name

    def get_descendants(self) -> QuerySet[Category]:
        """
        Get all descendant categories (children, grandchildren, etc.).

        Returns:
            QuerySet: All descendant categories
        """
        descendants = list(self.children.all())
        for child in list(descendants):
            descendants.extend(child.get_descendants())
        # Return as queryset of pks for consistency
        descendant_ids = [cat.pk for cat in descendants]
        return Category.objects.filter(pk__in=descendant_ids)


class Product(TimeStampedModel, SoftDeleteModel):
    """
    Comprehensive product model demonstrating all common field types and patterns.

    This model showcases:
        - Various field types with proper type hints
        - ForeignKey and ManyToMany relationships
        - Custom managers and querysets
        - Model properties and methods
        - Validation and clean methods
        - Meta options and indexes

    Type Hints for Fields:
        - CharField: str
        - TextField: str
        - IntegerField: int
        - DecimalField: Decimal
        - BooleanField: bool
        - DateTimeField: datetime
        - ForeignKey: Model instance or None
        - ManyToManyField: RelatedManager[Model]
    """

    # Basic text fields
    name: models.CharField = models.CharField(
        max_length=200,
        verbose_name=_("Product Name"),
        help_text=_("Enter the product name"),
    )
    slug: models.SlugField = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name=_("URL Slug"),
        help_text=_("Unique URL-friendly identifier"),
    )
    description: models.TextField = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed product description"),
    )
    sku: models.CharField = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("SKU"),
        help_text=_("Stock Keeping Unit"),
    )

    # Numeric fields
    price: models.DecimalField = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Price"),
        help_text=_("Product price in USD"),
    )
    cost: models.DecimalField = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Cost"),
        help_text=_("Product cost for margin calculations"),
    )
    stock_quantity: models.IntegerField = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Stock Quantity"),
        help_text=_("Available quantity in stock"),
    )
    weight: models.DecimalField = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Weight (kg)"),
        help_text=_("Product weight in kilograms"),
    )

    # Choice field
    status: models.CharField = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.DRAFT,
        verbose_name=_("Status"),
    )

    # Boolean fields
    is_featured: models.BooleanField = models.BooleanField(
        default=False,
        verbose_name=_("Is Featured"),
        help_text=_("Display product in featured section"),
    )
    is_taxable: models.BooleanField = models.BooleanField(
        default=True,
        verbose_name=_("Is Taxable"),
    )

    # Date and time fields
    published_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Published At"),
    )
    available_from: models.DateField = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Available From"),
    )
    available_until: models.DateField = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Available Until"),
    )

    # Foreign key relationships
    category: models.ForeignKey = models.ForeignKey(
        Category,
        on_delete=PROTECT,  # Prevent deletion if products exist
        related_name="products",
        verbose_name=_("Category"),
    )

    # Optional foreign key (nullable)
    # manufacturer: models.ForeignKey = models.ForeignKey(
    #     "Manufacturer",
    #     on_delete=SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="products",
    #     verbose_name=_("Manufacturer"),
    # )

    # Many-to-many relationship
    # tags: models.ManyToManyField = models.ManyToManyField(
    #     "Tag",
    #     blank=True,
    #     related_name="products",
    #     verbose_name=_("Tags"),
    # )

    # Reverse relations (created by Django, shown here for type checking)
    if TYPE_CHECKING:
        # From Review model (defined elsewhere)
        reviews: RelatedManager[Review]
        # From OrderItem model (defined elsewhere)
        order_items: RelatedManager[OrderItem]

    # Custom manager
    objects: ClassVar[ProductManager] = ProductManager()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["category", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0),
                name="price_non_negative",
            ),
            models.CheckConstraint(
                check=Q(stock_quantity__gte=0),
                name="stock_non_negative",
            ),
        ]

    def __str__(self) -> str:
        """String representation for admin and templates."""
        return self.name

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<Product: {self.name} (SKU: {self.sku})>"

    def clean(self) -> None:
        """
        Model validation method called by full_clean().

        Raises:
            ValidationError: If validation fails
        """
        super().clean()

        # Validate date range
        if (
            self.available_from
            and self.available_until
            and self.available_from > self.available_until
        ):
            raise ValidationError({
                "available_until": _("End date must be after start date"),
            })

        # Validate price vs cost
        if self.cost > self.price:
            raise ValidationError({
                "cost": _("Cost cannot exceed price"),
            })

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save to add custom logic.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        # Auto-publish if status changed to active
        if self.status == ProductStatus.ACTIVE and not self.published_at:
            self.published_at = timezone.now()

        self.full_clean()  # Validate before saving
        super().save(*args, **kwargs)

    @property
    def profit_margin(self) -> Decimal:
        """
        Calculate profit margin percentage.

        Returns:
            Decimal: Profit margin as percentage (0-100)
        """
        if self.price == 0:
            return Decimal("0.00")
        return ((self.price - self.cost) / self.price) * 100

    @property
    def is_available(self) -> bool:
        """
        Check if product is currently available for purchase.

        Returns:
            bool: True if available
        """
        if self.status != ProductStatus.ACTIVE:
            return False
        if self.stock_quantity <= 0:
            return False

        now = timezone.now().date()
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False

        return True

    @property
    def is_low_stock(self) -> bool:
        """Check if product has low stock (less than 10 units)."""
        return 0 < self.stock_quantity < 10

    def adjust_stock(self, quantity: int, reason: str = "") -> None:
        """
        Adjust stock quantity with validation.

        Args:
            quantity: Amount to adjust (positive or negative)
            reason: Reason for adjustment

        Raises:
            ValidationError: If adjustment would result in negative stock
        """
        new_quantity = self.stock_quantity + quantity
        if new_quantity < 0:
            raise ValidationError(
                _("Insufficient stock. Available: %(current)s, Requested: %(requested)s"),
                params={"current": self.stock_quantity, "requested": abs(quantity)},
            )

        self.stock_quantity = new_quantity
        self.save(update_fields=["stock_quantity"])

    def get_average_rating(self) -> float:
        """
        Calculate average rating from reviews.

        Returns:
            float: Average rating (0.0 if no reviews)
        """
        avg = self.reviews.aggregate(avg_rating=models.Avg("rating"))["avg_rating"]
        return float(avg) if avg is not None else 0.0

    def get_review_count(self) -> int:
        """
        Get total number of reviews.

        Returns:
            int: Number of reviews
        """
        return self.reviews.count()


# ============================================================================
# Additional Model Examples
# ============================================================================


class Review(TimeStampedModel):
    """Product review model demonstrating composite keys and validation."""

    product: models.ForeignKey = models.ForeignKey(
        Product,
        on_delete=CASCADE,
        related_name="reviews",
        verbose_name=_("Product"),
    )
    # user: models.ForeignKey = models.ForeignKey(
    #     "User",
    #     on_delete=CASCADE,
    #     related_name="reviews",
    #     verbose_name=_("User"),
    # )
    rating: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Rating"),
        help_text=_("Rating from 1 to 5 stars"),
    )
    title: models.CharField = models.CharField(
        max_length=200,
        verbose_name=_("Title"),
    )
    comment: models.TextField = models.TextField(
        verbose_name=_("Comment"),
    )
    is_verified_purchase: models.BooleanField = models.BooleanField(
        default=False,
        verbose_name=_("Verified Purchase"),
    )

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ["-created_at"]
        # Prevent multiple reviews from same user for same product
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=["product", "user"],
        #         name="unique_product_user_review",
        #     ),
        # ]

    def __str__(self) -> str:
        return f"{self.title} - {self.rating}/5"


class OrderItem(TimeStampedModel):
    """Order item model demonstrating snapshot pattern."""

    # order: models.ForeignKey = models.ForeignKey(
    #     "Order",
    #     on_delete=CASCADE,
    #     related_name="items",
    #     verbose_name=_("Order"),
    # )
    product: models.ForeignKey = models.ForeignKey(
        Product,
        on_delete=PROTECT,
        related_name="order_items",
        verbose_name=_("Product"),
    )

    # Snapshot fields - store values at time of order
    product_name: models.CharField = models.CharField(
        max_length=200,
        verbose_name=_("Product Name"),
        help_text=_("Product name at time of order"),
    )
    product_sku: models.CharField = models.CharField(
        max_length=100,
        verbose_name=_("SKU"),
    )
    unit_price: models.DecimalField = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Unit Price"),
        help_text=_("Price at time of order"),
    )
    quantity: models.IntegerField = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Quantity"),
    )

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    @property
    def total_price(self) -> Decimal:
        """Calculate total price for this line item."""
        return self.unit_price * self.quantity

    def __str__(self) -> str:
        return f"{self.product_name} x {self.quantity}"
