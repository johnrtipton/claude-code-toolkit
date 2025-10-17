# Complete Guide to Django Typing

A comprehensive reference for type safety in Django applications using mypy and django-stubs.

## Table of Contents

1. [Introduction](#introduction)
2. [Django Models](#django-models)
3. [Views and URL Patterns](#views-and-url-patterns)
4. [Forms and Form Handling](#forms-and-form-handling)
5. [Django Admin](#django-admin)
6. [Middleware](#middleware)
7. [Signals](#signals)
8. [Template Context](#template-context)
9. [Django REST Framework](#django-rest-framework)
10. [Advanced Patterns](#advanced-patterns)
11. [Common Pitfalls](#common-pitfalls)
12. [Best Practices](#best-practices)

---

## Introduction

### Why Type Django Code?

Type hints provide:
- **Early error detection**: Catch bugs before runtime
- **Better IDE support**: Autocomplete, go-to-definition, refactoring
- **Documentation**: Types serve as inline documentation
- **Refactoring confidence**: Change code with confidence
- **Team collaboration**: Clear interfaces between components

### Setup Requirements

```bash
pip install mypy django-stubs django-stubs-ext djangorestframework-stubs
```

**mypy.ini configuration:**

```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main, mypy_drf_plugin.main
strict = True
warn_unused_ignores = True
warn_redundant_casts = True
warn_unused_configs = True
disallow_subclassing_any = True
disallow_any_generics = True
disallow_untyped_calls = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_return_any = True
strict_equality = True

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings

[mypy-*.migrations.*]
ignore_errors = True

[mypy-*.tests.*]
disallow_untyped_defs = False
```

---

## Django Models

### Basic Model Typing

```python
from django.db import models
from typing import ClassVar
from datetime import datetime

class Article(models.Model):
    """
    Article model with complete type annotations.

    Type annotations for fields follow the pattern:
    field_name: python_type = models.FieldType(...)
    """

    # CharField becomes str in Python
    title: str = models.CharField(max_length=200)

    # TextField also becomes str
    content: str = models.TextField()

    # BooleanField becomes bool
    published: bool = models.BooleanField(default=False)

    # IntegerField becomes int
    view_count: int = models.IntegerField(default=0)

    # DateTimeField becomes datetime
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)

    # Nullable fields use Optional or | None (Python 3.10+)
    published_at: datetime | None = models.DateTimeField(null=True, blank=True)

    # Manager typing - use ClassVar to indicate class-level attribute
    objects: ClassVar[models.Manager["Article"]] = models.Manager()

    class Meta:
        db_table = "articles"
        ordering = ["-created_at"]
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __str__(self) -> str:
        return self.title

    def get_excerpt(self, length: int = 100) -> str:
        """Get excerpt of content with type-safe parameters."""
        if len(self.content) <= length:
            return self.content
        return self.content[:length] + "..."

    def increment_views(self) -> None:
        """Increment view count - void return type."""
        self.view_count += 1
        self.save(update_fields=["view_count"])

    def publish(self) -> bool:
        """Publish article and return success status."""
        if self.published:
            return False

        self.published = True
        self.published_at = datetime.now()
        self.save(update_fields=["published", "published_at"])
        return True
```

### Foreign Key Relationships

```python
from django.db import models
from django.contrib.auth.models import User
from typing import ClassVar

class Author(models.Model):
    """Author with proper ForeignKey typing."""

    # ForeignKey annotation includes the related model in quotes
    user: User = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="author_profile"
    )

    bio: str = models.TextField(blank=True)
    website: str = models.URLField(blank=True)

    objects: ClassVar[models.Manager["Author"]] = models.Manager()

    def __str__(self) -> str:
        return self.user.get_full_name() or self.user.username


class Article(models.Model):
    """Article with ForeignKey to Author."""

    title: str = models.CharField(max_length=200)

    # ForeignKey creates both the field and the _id field
    # author: Author - the related object
    # author_id: int - the foreign key value
    author: Author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="articles"
    )

    # Self-referential ForeignKey
    parent: "Article | None" = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    objects: ClassVar[models.Manager["Article"]] = models.Manager()

    def get_author_name(self) -> str:
        """Access related object with full type safety."""
        return self.author.user.get_full_name() or self.author.user.username

    def get_parent_title(self) -> str | None:
        """Handle nullable foreign keys properly."""
        if self.parent is not None:
            return self.parent.title
        return None
```

### Many-to-Many Relationships

```python
from django.db import models
from typing import ClassVar

class Tag(models.Model):
    """Tag model for many-to-many relationships."""

    name: str = models.CharField(max_length=50, unique=True)
    slug: str = models.SlugField(unique=True)

    objects: ClassVar[models.Manager["Tag"]] = models.Manager()

    def __str__(self) -> str:
        return self.name


class Article(models.Model):
    title: str = models.CharField(max_length=200)

    # ManyToManyField creates a manager
    # tags: models.Manager[Tag] - runtime type
    # But we annotate with the field type for model definition
    tags: models.ManyToManyField[Tag, "Article"] = models.ManyToManyField(
        Tag,
        related_name="articles",
        blank=True
    )

    objects: ClassVar[models.Manager["Article"]] = models.Manager()

    def add_tags(self, *tag_names: str) -> None:
        """Type-safe method to add tags by name."""
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(
                name=name,
                defaults={"slug": name.lower().replace(" ", "-")}
            )
            self.tags.add(tag)

    def get_tag_names(self) -> list[str]:
        """Get list of tag names with proper return type."""
        return list(self.tags.values_list("name", flat=True))


class ArticleTag(models.Model):
    """Explicit through model for M2M with extra fields."""

    article: Article = models.ForeignKey(Article, on_delete=models.CASCADE)
    tag: Tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_at: datetime = models.DateTimeField(auto_now_add=True)
    added_by: User = models.ForeignKey(User, on_delete=models.CASCADE)

    objects: ClassVar[models.Manager["ArticleTag"]] = models.Manager()

    class Meta:
        unique_together = [["article", "tag"]]
        ordering = ["-added_at"]


class ArticleWithThrough(models.Model):
    """Article using explicit through model."""

    title: str = models.CharField(max_length=200)

    tags: models.ManyToManyField[Tag, "ArticleWithThrough"] = models.ManyToManyField(
        Tag,
        through=ArticleTag,
        related_name="articles_with_metadata"
    )

    objects: ClassVar[models.Manager["ArticleWithThrough"]] = models.Manager()
```

### Custom Managers and QuerySets

```python
from django.db import models
from django.db.models import QuerySet, Manager
from typing import TypeVar, Generic, ClassVar, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from django.db.models.manager import Manager as DjangoManager

# Generic type variable bound to Model
_T = TypeVar("_T", bound=models.Model)


class ArticleQuerySet(QuerySet["Article"]):
    """Custom QuerySet with type-safe methods."""

    def published(self) -> "ArticleQuerySet":
        """Return only published articles."""
        return self.filter(published=True)

    def recent(self, days: int = 7) -> "ArticleQuerySet":
        """Return articles from last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff)

    def by_author(self, author: "Author") -> "ArticleQuerySet":
        """Filter by author with type checking."""
        return self.filter(author=author)

    def with_tag(self, tag_name: str) -> "ArticleQuerySet":
        """Filter articles with specific tag."""
        return self.filter(tags__name=tag_name)

    def popular(self, min_views: int = 100) -> "ArticleQuerySet":
        """Return popular articles."""
        return self.filter(view_count__gte=min_views)


class ArticleManager(Manager["Article"]):
    """Custom Manager with QuerySet methods."""

    def get_queryset(self) -> ArticleQuerySet:
        """Override to return custom QuerySet."""
        return ArticleQuerySet(self.model, using=self._db)

    def published(self) -> ArticleQuerySet:
        """Proxy method to QuerySet."""
        return self.get_queryset().published()

    def recent(self, days: int = 7) -> ArticleQuerySet:
        """Proxy method with parameters."""
        return self.get_queryset().recent(days)

    def by_author(self, author: "Author") -> ArticleQuerySet:
        """Type-safe filtering by author."""
        return self.get_queryset().by_author(author)

    def create_article(
        self,
        title: str,
        content: str,
        author: "Author",
        published: bool = False
    ) -> "Article":
        """Type-safe creation method."""
        article = self.create(
            title=title,
            content=content,
            author=author,
            published=published
        )
        return article


class Article(models.Model):
    """Article with custom manager and queryset."""

    title: str = models.CharField(max_length=200)
    content: str = models.TextField()
    published: bool = models.BooleanField(default=False)
    view_count: int = models.IntegerField(default=0)
    created_at: datetime = models.DateTimeField(auto_now_add=True)

    author: Author = models.ForeignKey(
        "Author",
        on_delete=models.CASCADE,
        related_name="articles"
    )

    # Multiple managers with different purposes
    objects: ClassVar[ArticleManager] = ArticleManager()
    published_objects: ClassVar[ArticleManager] = ArticleManager()

    class Meta:
        ordering = ["-created_at"]


# Generic QuerySet for reuse across models
class PublishableQuerySet(QuerySet[_T], Generic[_T]):
    """Generic queryset for any publishable model."""

    def published(self) -> "PublishableQuerySet[_T]":
        return self.filter(published=True)  # type: ignore[arg-type]

    def unpublished(self) -> "PublishableQuerySet[_T]":
        return self.filter(published=False)  # type: ignore[arg-type]


class PublishableManager(Manager[_T]):
    """Generic manager for publishable models."""

    def get_queryset(self) -> PublishableQuerySet[_T]:
        return PublishableQuerySet(self.model, using=self._db)

    def published(self) -> PublishableQuerySet[_T]:
        return self.get_queryset().published()


class BlogPost(models.Model):
    """Blog post using generic publishable manager."""

    title: str = models.CharField(max_length=200)
    published: bool = models.BooleanField(default=False)

    objects: ClassVar[PublishableManager["BlogPost"]] = PublishableManager()
```

### Model Properties and Methods

```python
from django.db import models
from typing import ClassVar
from decimal import Decimal

class Product(models.Model):
    """Product with computed properties and type-safe methods."""

    name: str = models.CharField(max_length=200)
    price: Decimal = models.DecimalField(max_digits=10, decimal_places=2)
    cost: Decimal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate: Decimal = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0825")
    )

    objects: ClassVar[models.Manager["Product"]] = models.Manager()

    @property
    def profit(self) -> Decimal:
        """Calculate profit with proper return type."""
        return self.price - self.cost

    @property
    def profit_margin(self) -> float:
        """Calculate profit margin as percentage."""
        if self.price == 0:
            return 0.0
        return float((self.profit / self.price) * 100)

    @property
    def price_with_tax(self) -> Decimal:
        """Calculate price including tax."""
        return self.price * (1 + self.tax_rate)

    def apply_discount(self, percentage: float) -> Decimal:
        """
        Apply discount and return new price.

        Args:
            percentage: Discount percentage (0-100)

        Returns:
            New discounted price

        Raises:
            ValueError: If percentage is invalid
        """
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")

        discount_multiplier = Decimal(str(1 - (percentage / 100)))
        return self.price * discount_multiplier

    def update_price(self, new_price: Decimal, save: bool = True) -> None:
        """Update price with optional save."""
        self.price = new_price
        if save:
            self.save(update_fields=["price"])

    def __str__(self) -> str:
        return f"{self.name} - ${self.price}"


class Order(models.Model):
    """Order with computed totals."""

    customer: User = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at: datetime = models.DateTimeField(auto_now_add=True)

    objects: ClassVar[models.Manager["Order"]] = models.Manager()

    @property
    def total(self) -> Decimal:
        """Calculate order total from line items."""
        return sum(
            (item.quantity * item.price for item in self.items.all()),
            start=Decimal("0.00")
        )

    @property
    def item_count(self) -> int:
        """Get total number of items."""
        return sum(item.quantity for item in self.items.all())

    def add_item(self, product: Product, quantity: int = 1) -> "OrderItem":
        """Add item to order with type safety."""
        item, created = self.items.get_or_create(
            product=product,
            defaults={"quantity": quantity, "price": product.price}
        )

        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity"])

        return item


class OrderItem(models.Model):
    """Order line item."""

    order: Order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product: Product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity: int = models.IntegerField(default=1)
    price: Decimal = models.DecimalField(max_digits=10, decimal_places=2)

    objects: ClassVar[models.Manager["OrderItem"]] = models.Manager()

    @property
    def subtotal(self) -> Decimal:
        """Calculate line item subtotal."""
        return self.quantity * self.price

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product.name}"
```

### Model Choices and Enums

```python
from django.db import models
from typing import ClassVar
from enum import Enum

class ArticleStatus(models.TextChoices):
    """Article status choices with type safety."""
    DRAFT = "draft", "Draft"
    REVIEW = "review", "Under Review"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class Priority(models.IntegerChoices):
    """Priority levels as integer choices."""
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    URGENT = 4, "Urgent"


class Article(models.Model):
    """Article with typed choices."""

    title: str = models.CharField(max_length=200)

    # Type is str (the value from TextChoices)
    status: str = models.CharField(
        max_length=20,
        choices=ArticleStatus.choices,
        default=ArticleStatus.DRAFT
    )

    # Type is int (from IntegerChoices)
    priority: int = models.IntegerField(
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    objects: ClassVar[models.Manager["Article"]] = models.Manager()

    def is_published(self) -> bool:
        """Type-safe status check."""
        return self.status == ArticleStatus.PUBLISHED

    def can_edit(self) -> bool:
        """Check if article can be edited."""
        return self.status in [ArticleStatus.DRAFT, ArticleStatus.REVIEW]

    def publish(self) -> bool:
        """Publish article if in valid state."""
        if self.status != ArticleStatus.REVIEW:
            return False

        self.status = ArticleStatus.PUBLISHED
        self.save(update_fields=["status"])
        return True

    def get_status_display_custom(self) -> str:
        """Custom status display with type safety."""
        return ArticleStatus(self.status).label


# Using standard Enum for more complex choices
class PaymentMethod(str, Enum):
    """Payment method enum."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"

    @property
    def requires_verification(self) -> bool:
        """Check if payment method requires verification."""
        return self in [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.BANK_TRANSFER
        ]

    @property
    def is_instant(self) -> bool:
        """Check if payment is instant."""
        return self in [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.CASH
        ]


class Payment(models.Model):
    """Payment with enum-based choices."""

    amount: Decimal = models.DecimalField(max_digits=10, decimal_places=2)

    method: str = models.CharField(
        max_length=20,
        choices=[(m.value, m.name.replace("_", " ").title())
                 for m in PaymentMethod]
    )

    objects: ClassVar[models.Manager["Payment"]] = models.Manager()

    def get_payment_method(self) -> PaymentMethod:
        """Get typed payment method enum."""
        return PaymentMethod(self.method)

    def requires_verification(self) -> bool:
        """Check if payment requires verification."""
        return self.get_payment_method().requires_verification
```

### Abstract Base Models

```python
from django.db import models
from typing import ClassVar
from uuid import uuid4

class UUIDModel(models.Model):
    """Abstract base with UUID primary key."""

    id: uuid4 = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Abstract base with created/updated timestamps."""

    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def age_in_days(self) -> int:
        """Calculate age in days."""
        delta = datetime.now() - self.created_at
        return delta.days


class SoftDeleteModel(models.Model):
    """Abstract base with soft delete functionality."""

    deleted_at: datetime | None = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        """Soft delete by setting deleted_at."""
        self.deleted_at = datetime.now()
        self.save(update_fields=["deleted_at"])
        return (0, {})

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """Permanently delete the object."""
        return super().delete()

    def restore(self) -> None:
        """Restore soft-deleted object."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        """Check if object is soft-deleted."""
        return self.deleted_at is not None


class Article(UUIDModel, TimestampedModel, SoftDeleteModel):
    """Article using multiple abstract bases."""

    title: str = models.CharField(max_length=200)
    content: str = models.TextField()

    objects: ClassVar[models.Manager["Article"]] = models.Manager()

    def __str__(self) -> str:
        return self.title
```

---

## Views and URL Patterns

### Function-Based Views

```python
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    HttpResponseRedirect,
    HttpResponseNotFound,
    HttpResponseBadRequest,
    HttpResponseForbidden
)
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from typing import Any

# Basic view with proper typing
def article_list(request: HttpRequest) -> HttpResponse:
    """List all published articles."""
    articles = Article.objects.published()
    context: dict[str, Any] = {
        "articles": articles,
        "title": "Articles"
    }
    return render(request, "articles/list.html", context)


# View with path parameters
def article_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Display single article by primary key."""
    article = get_object_or_404(Article, pk=pk)
    context: dict[str, Any] = {
        "article": article
    }
    return render(request, "articles/detail.html", context)


# View with multiple parameters
def article_by_slug(
    request: HttpRequest,
    year: int,
    month: int,
    slug: str
) -> HttpResponse:
    """Get article by year, month, and slug."""
    article = get_object_or_404(
        Article,
        created_at__year=year,
        created_at__month=month,
        slug=slug
    )
    return render(request, "articles/detail.html", {"article": article})


# View with query parameters
def search_articles(request: HttpRequest) -> HttpResponse:
    """Search articles with query parameters."""
    query = request.GET.get("q", "")
    tag = request.GET.get("tag")

    articles = Article.objects.published()

    if query:
        articles = articles.filter(title__icontains=query)

    if tag:
        articles = articles.filter(tags__slug=tag)

    context: dict[str, Any] = {
        "articles": articles,
        "query": query,
        "tag": tag
    }
    return render(request, "articles/search.html", context)


# POST handler with form data
@require_POST
def create_article(request: HttpRequest) -> HttpResponse:
    """Create new article from POST data."""
    title = request.POST.get("title", "")
    content = request.POST.get("content", "")

    if not title or not content:
        return HttpResponseBadRequest("Title and content required")

    article = Article.objects.create(
        title=title,
        content=content,
        author=request.user
    )

    return redirect("article-detail", pk=article.pk)


# JSON API view
def api_article_list(request: HttpRequest) -> JsonResponse:
    """Return articles as JSON."""
    articles = Article.objects.published().values(
        "id", "title", "created_at"
    )

    data: dict[str, Any] = {
        "articles": list(articles),
        "count": articles.count()
    }

    return JsonResponse(data)


# Protected view requiring login
@login_required
def my_articles(request: HttpRequest) -> HttpResponse:
    """Display current user's articles."""
    articles = Article.objects.filter(author__user=request.user)
    return render(request, "articles/my_articles.html", {"articles": articles})


# Method-restricted view
@require_http_methods(["GET", "POST"])
def article_form(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    """Handle both GET (display form) and POST (submit form)."""
    article: Article | None = None

    if pk is not None:
        article = get_object_or_404(Article, pk=pk)

    if request.method == "POST":
        # Handle form submission
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            article = form.save()
            return redirect("article-detail", pk=article.pk)
    else:
        # Display form
        form = ArticleForm(instance=article)

    context: dict[str, Any] = {
        "form": form,
        "article": article
    }
    return render(request, "articles/form.html", context)


# Union return types for different response types
def conditional_response(
    request: HttpRequest
) -> HttpResponse | JsonResponse:
    """Return different response types based on Accept header."""
    accepts_json = request.headers.get("Accept") == "application/json"

    articles = Article.objects.published()

    if accepts_json:
        data = {
            "articles": list(articles.values("id", "title"))
        }
        return JsonResponse(data)

    return render(request, "articles/list.html", {"articles": articles})
```

### Class-Based Views

```python
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    FormView
)
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse_lazy
from typing import Any

# Basic View subclass
class ArticleListView(ListView[Article]):
    """
    Type-safe ListView for Article model.

    ListView is generic and takes the model type as a parameter.
    """
    model = Article
    template_name = "articles/list.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self) -> models.QuerySet[Article]:
        """Override queryset with proper return type."""
        queryset = super().get_queryset()
        return queryset.published().order_by("-created_at")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add extra context with type hints."""
        context = super().get_context_data(**kwargs)
        context["popular_tags"] = Tag.objects.all()[:10]
        context["recent_count"] = Article.objects.recent().count()
        return context


class ArticleDetailView(DetailView[Article]):
    """Display single article with type safety."""
    model = Article
    template_name = "articles/detail.html"
    context_object_name = "article"

    def get_object(self, queryset: models.QuerySet[Article] | None = None) -> Article:
        """Override get_object with proper typing."""
        obj = super().get_object(queryset)
        # Increment view count
        obj.increment_views()
        return obj

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add related articles to context."""
        context = super().get_context_data(**kwargs)
        article = self.object

        context["related_articles"] = (
            Article.objects
            .published()
            .filter(tags__in=article.tags.all())
            .exclude(pk=article.pk)
            .distinct()[:5]
        )

        return context


class ArticleCreateView(CreateView[Article, ArticleForm]):
    """Create new article with form."""
    model = Article
    form_class = ArticleForm
    template_name = "articles/form.html"
    success_url = reverse_lazy("article-list")

    def form_valid(self, form: ArticleForm) -> HttpResponse:
        """Set author before saving."""
        form.instance.author = self.request.user.author
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect to created article."""
        return reverse("article-detail", kwargs={"pk": self.object.pk})


class ArticleUpdateView(UpdateView[Article, ArticleForm]):
    """Update existing article."""
    model = Article
    form_class = ArticleForm
    template_name = "articles/form.html"

    def get_queryset(self) -> models.QuerySet[Article]:
        """Only allow editing own articles."""
        return Article.objects.filter(author__user=self.request.user)

    def get_success_url(self) -> str:
        """Return to article detail after update."""
        return reverse("article-detail", kwargs={"pk": self.object.pk})


class ArticleDeleteView(DeleteView[Article]):
    """Delete article with confirmation."""
    model = Article
    template_name = "articles/confirm_delete.html"
    success_url = reverse_lazy("article-list")

    def get_queryset(self) -> models.QuerySet[Article]:
        """Only allow deleting own articles."""
        return Article.objects.filter(author__user=self.request.user)


class ArticleSearchView(TemplateView):
    """Search view with custom logic."""
    template_name = "articles/search.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Perform search and add results to context."""
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get("q", "")

        if query:
            results = Article.objects.published().filter(
                title__icontains=query
            )
        else:
            results = Article.objects.none()

        context["query"] = query
        context["results"] = results

        return context


# Generic View for custom logic
class ArticleAPIView(View):
    """API view with typed HTTP method handlers."""

    def get(self, request: HttpRequest, pk: int) -> JsonResponse:
        """GET handler returns JSON."""
        article = get_object_or_404(Article, pk=pk)
        data: dict[str, Any] = {
            "id": article.pk,
            "title": article.title,
            "content": article.content,
            "published": article.published
        }
        return JsonResponse(data)

    def post(self, request: HttpRequest) -> JsonResponse:
        """POST handler creates article."""
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            return JsonResponse(
                {"error": "Title and content required"},
                status=400
            )

        article = Article.objects.create(
            title=title,
            content=content,
            author=request.user.author
        )

        return JsonResponse(
            {"id": article.pk, "title": article.title},
            status=201
        )

    def put(self, request: HttpRequest, pk: int) -> JsonResponse:
        """PUT handler updates article."""
        article = get_object_or_404(Article, pk=pk)

        # Parse JSON body
        import json
        data = json.loads(request.body)

        article.title = data.get("title", article.title)
        article.content = data.get("content", article.content)
        article.save()

        return JsonResponse({"id": article.pk, "title": article.title})

    def delete(self, request: HttpRequest, pk: int) -> JsonResponse:
        """DELETE handler removes article."""
        article = get_object_or_404(Article, pk=pk)
        article.delete()
        return JsonResponse({"deleted": True}, status=204)


# FormView with proper typing
class ContactFormView(FormView[ContactForm]):
    """Contact form with email sending."""
    template_name = "contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact-success")

    def form_valid(self, form: ContactForm) -> HttpResponse:
        """Send email on valid form."""
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        message = form.cleaned_data["message"]

        # Send email
        from django.core.mail import send_mail
        send_mail(
            subject=f"Contact form from {name}",
            message=message,
            from_email=email,
            recipient_list=["admin@example.com"]
        )

        return super().form_valid(form)
```

### URL Patterns

```python
from django.urls import path, re_path, include
from django.urls.resolvers import URLPattern, URLResolver
from typing import List
from . import views

# Type annotation for URL patterns
urlpatterns: list[URLPattern | URLResolver] = [
    # Function-based views
    path("", views.article_list, name="article-list"),
    path("<int:pk>/", views.article_detail, name="article-detail"),
    path("search/", views.search_articles, name="article-search"),
    path("create/", views.create_article, name="article-create"),

    # Class-based views
    path("cbv/", views.ArticleListView.as_view(), name="article-list-cbv"),
    path("cbv/<int:pk>/", views.ArticleDetailView.as_view(), name="article-detail-cbv"),
    path("cbv/create/", views.ArticleCreateView.as_view(), name="article-create-cbv"),
    path("cbv/<int:pk>/edit/", views.ArticleUpdateView.as_view(), name="article-update"),
    path("cbv/<int:pk>/delete/", views.ArticleDeleteView.as_view(), name="article-delete"),

    # API endpoints
    path("api/", views.api_article_list, name="api-article-list"),
    path("api/<int:pk>/", views.ArticleAPIView.as_view(), name="api-article-detail"),

    # Regex patterns with type hints
    re_path(
        r"^(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<slug>[\w-]+)/$",
        views.article_by_slug,
        name="article-by-slug"
    ),

    # Include other URL configs
    path("comments/", include("comments.urls")),
]

app_name = "articles"
```

---

## Forms and Form Handling

### ModelForm Typing

```python
from django import forms
from django.core.exceptions import ValidationError
from typing import Any

class ArticleForm(forms.ModelForm[Article]):
    """Type-safe ModelForm for Article."""

    # Override field with custom widget
    content = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "cols": 80}),
        help_text="Enter article content"
    )

    # Add fields not in model
    send_notification = forms.BooleanField(
        required=False,
        help_text="Notify subscribers of new article"
    )

    class Meta:
        model = Article
        fields = ["title", "content", "tags", "published"]
        widgets = {
            "tags": forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            "title": "Enter a descriptive title"
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize form with custom logic."""
        super().__init__(*args, **kwargs)

        # Customize field attributes
        self.fields["title"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Enter title"
        })

    def clean_title(self) -> str:
        """Validate and clean title field."""
        title = self.cleaned_data["title"]

        if len(title) < 5:
            raise ValidationError("Title must be at least 5 characters")

        # Check for duplicate titles
        if Article.objects.filter(title=title).exists():
            if not self.instance.pk or self.instance.title != title:
                raise ValidationError("Article with this title already exists")

        return title.strip()

    def clean(self) -> dict[str, Any]:
        """Cross-field validation."""
        cleaned_data = super().clean()

        published = cleaned_data.get("published")
        content = cleaned_data.get("content")

        if published and content and len(content) < 100:
            raise ValidationError(
                "Published articles must have at least 100 characters of content"
            )

        return cleaned_data

    def save(self, commit: bool = True) -> Article:
        """Override save with custom logic."""
        article = super().save(commit=False)

        # Set author if not set
        if not article.author_id:
            # Would need to pass author through form init or view
            pass

        if commit:
            article.save()
            self.save_m2m()  # Save many-to-many relationships

            # Handle extra field
            if self.cleaned_data.get("send_notification"):
                # Send notification logic here
                pass

        return article


class ArticleFilterForm(forms.Form):
    """Non-model form for filtering articles."""

    query = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Search..."})
    )

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    status = forms.ChoiceField(
        choices=[("", "All")] + list(ArticleStatus.choices),
        required=False
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    def clean(self) -> dict[str, Any]:
        """Validate date range."""
        cleaned_data = super().clean()

        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise ValidationError("Start date must be before end date")

        return cleaned_data

    def get_queryset(self) -> models.QuerySet[Article]:
        """Return filtered queryset based on form data."""
        queryset = Article.objects.all()

        if not self.is_valid():
            return queryset

        query = self.cleaned_data.get("query")
        if query:
            queryset = queryset.filter(title__icontains=query)

        tags = self.cleaned_data.get("tags")
        if tags:
            queryset = queryset.filter(tags__in=tags).distinct()

        status = self.cleaned_data.get("status")
        if status:
            queryset = queryset.filter(status=status)

        date_from = self.cleaned_data.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = self.cleaned_data.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset
```

### Formsets

```python
from django.forms import formset_factory, modelformset_factory, inlineformset_factory
from typing import Any

# Model formset for editing multiple objects
ArticleFormSet = modelformset_factory(
    Article,
    fields=["title", "published"],
    extra=0,  # No extra blank forms
    can_delete=True
)

def manage_articles(request: HttpRequest) -> HttpResponse:
    """View using model formset."""
    if request.method == "POST":
        formset = ArticleFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            return redirect("article-list")
    else:
        formset = ArticleFormSet(queryset=Article.objects.filter(
            author__user=request.user
        ))

    context: dict[str, Any] = {"formset": formset}
    return render(request, "articles/manage.html", context)


# Inline formset for related objects
OrderItemFormSet = inlineformset_factory(
    Order,  # Parent model
    OrderItem,  # Child model
    fields=["product", "quantity", "price"],
    extra=1,
    can_delete=True
)

def edit_order(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit order with inline formset for items."""
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST":
        formset = OrderItemFormSet(request.POST, instance=order)
        if formset.is_valid():
            formset.save()
            return redirect("order-detail", pk=order.pk)
    else:
        formset = OrderItemFormSet(instance=order)

    context: dict[str, Any] = {
        "order": order,
        "formset": formset
    }
    return render(request, "orders/edit.html", context)


# Regular formset (not model-based)
class ContactForm(forms.Form):
    """Simple contact form."""
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)


ContactFormSet = formset_factory(ContactForm, extra=3)

def bulk_contact(request: HttpRequest) -> HttpResponse:
    """Handle multiple contact forms."""
    if request.method == "POST":
        formset = ContactFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                name = form.cleaned_data["name"]
                email = form.cleaned_data["email"]
                message = form.cleaned_data["message"]
                # Process each form
            return redirect("success")
    else:
        formset = ContactFormSet()

    return render(request, "contact_bulk.html", {"formset": formset})
```

---

## Django Admin

### Basic Admin Configuration

```python
from django.contrib import admin
from django.http import HttpRequest
from django.db.models import QuerySet
from typing import Any, Sequence

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin[Article]):
    """Type-safe admin configuration for Article."""

    # Display configuration
    list_display: Sequence[str] = [
        "title",
        "author",
        "status",
        "published",
        "view_count",
        "created_at"
    ]

    list_filter: Sequence[str] = [
        "status",
        "published",
        "created_at",
        "tags"
    ]

    search_fields: Sequence[str] = [
        "title",
        "content",
        "author__user__username"
    ]

    date_hierarchy: str = "created_at"

    ordering: Sequence[str] = ["-created_at"]

    # Edit configuration
    fields: Sequence[str] = [
        "title",
        "content",
        "author",
        "status",
        "published",
        "tags"
    ]

    filter_horizontal: Sequence[str] = ["tags"]

    readonly_fields: Sequence[str] = ["view_count", "created_at", "updated_at"]

    # Method overrides with proper typing
    def get_queryset(self, request: HttpRequest) -> QuerySet[Article]:
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related("author__user").prefetch_related("tags")

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Article | None = None
    ) -> bool:
        """Custom permission logic."""
        if obj is not None and obj.author.user != request.user:
            return False
        return super().has_change_permission(request, obj)

    def save_model(
        self,
        request: HttpRequest,
        obj: Article,
        form: Any,
        change: bool
    ) -> None:
        """Custom save logic."""
        if not change:  # New object
            obj.author = request.user.author
        super().save_model(request, obj, form, change)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin[Author]):
    """Admin for Author model."""

    list_display: Sequence[str] = ["get_full_name", "email", "article_count"]
    search_fields: Sequence[str] = ["user__username", "user__email", "bio"]

    def get_full_name(self, obj: Author) -> str:
        """Display method with proper return type."""
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = "Name"
    get_full_name.admin_order_field = "user__first_name"

    def email(self, obj: Author) -> str:
        """Get author email."""
        return obj.user.email
    email.short_description = "Email"
    email.admin_order_field = "user__email"

    def article_count(self, obj: Author) -> int:
        """Count articles for author."""
        return obj.articles.count()
    article_count.short_description = "Articles"


# Inline admin for related models
class OrderItemInline(admin.TabularInline[OrderItem, Order]):
    """Inline admin for order items."""
    model = OrderItem
    extra = 1
    fields: Sequence[str] = ["product", "quantity", "price", "subtotal"]
    readonly_fields: Sequence[str] = ["subtotal"]

    def subtotal(self, obj: OrderItem) -> Decimal:
        """Display calculated subtotal."""
        return obj.subtotal
    subtotal.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin[Order]):
    """Admin for Order with inline items."""

    list_display: Sequence[str] = ["id", "customer", "created_at", "total", "item_count"]
    list_filter: Sequence[str] = ["created_at"]
    search_fields: Sequence[str] = ["customer__username", "customer__email"]
    date_hierarchy: str = "created_at"
    inlines: Sequence[type[admin.TabularInline[OrderItem, Order]]] = [OrderItemInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Order]:
        """Optimize with prefetch_related."""
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("items__product")

    def total(self, obj: Order) -> Decimal:
        """Display order total."""
        return obj.total
    total.short_description = "Total"

    def item_count(self, obj: Order) -> int:
        """Display item count."""
        return obj.item_count
    item_count.short_description = "Items"
```

### Advanced Admin Features

```python
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from typing import Any, Callable

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin[Article]):
    """Advanced admin with custom actions and URLs."""

    list_display: Sequence[str] = [
        "title",
        "status_badge",
        "published",
        "view_count",
        "action_buttons"
    ]

    actions: list[str] = ["make_published", "make_draft", "reset_view_count"]

    def status_badge(self, obj: Article) -> str:
        """Display status as colored badge."""
        colors = {
            ArticleStatus.DRAFT: "gray",
            ArticleStatus.REVIEW: "orange",
            ArticleStatus.PUBLISHED: "green",
            ArticleStatus.ARCHIVED: "red"
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; '
            'border-radius: 3px; color: white;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def action_buttons(self, obj: Article) -> str:
        """Display custom action buttons."""
        buttons = []

        if obj.status == ArticleStatus.DRAFT:
            url = reverse("admin:articles_article_submit_review", args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="button">Submit for Review</a>'
            )

        if obj.status == ArticleStatus.REVIEW:
            url = reverse("admin:articles_article_publish", args=[obj.pk])
            buttons.append(
                f'<a href="{url}" class="button">Publish</a>'
            )

        return format_html(" ".join(buttons))
    action_buttons.short_description = "Actions"

    # Custom admin actions
    @admin.action(description="Publish selected articles")
    def make_published(
        self,
        request: HttpRequest,
        queryset: QuerySet[Article]
    ) -> None:
        """Bulk publish articles."""
        updated = queryset.update(
            status=ArticleStatus.PUBLISHED,
            published=True
        )
        self.message_user(
            request,
            f"{updated} articles published successfully.",
            messages.SUCCESS
        )

    @admin.action(description="Move to draft")
    def make_draft(
        self,
        request: HttpRequest,
        queryset: QuerySet[Article]
    ) -> None:
        """Move articles to draft status."""
        updated = queryset.update(
            status=ArticleStatus.DRAFT,
            published=False
        )
        self.message_user(
            request,
            f"{updated} articles moved to draft.",
            messages.SUCCESS
        )

    @admin.action(description="Reset view count")
    def reset_view_count(
        self,
        request: HttpRequest,
        queryset: QuerySet[Article]
    ) -> None:
        """Reset view count to zero."""
        updated = queryset.update(view_count=0)
        self.message_user(
            request,
            f"View count reset for {updated} articles.",
            messages.SUCCESS
        )

    # Custom URLs
    def get_urls(self) -> list[Any]:
        """Add custom admin URLs."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/submit-review/",
                self.admin_site.admin_view(self.submit_review_view),
                name="articles_article_submit_review"
            ),
            path(
                "<int:pk>/publish/",
                self.admin_site.admin_view(self.publish_view),
                name="articles_article_publish"
            ),
        ]
        return custom_urls + urls

    def submit_review_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Custom view to submit article for review."""
        article = get_object_or_404(Article, pk=pk)
        article.status = ArticleStatus.REVIEW
        article.save(update_fields=["status"])

        self.message_user(
            request,
            f"Article '{article.title}' submitted for review.",
            messages.SUCCESS
        )

        return redirect("admin:articles_article_change", pk)

    def publish_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Custom view to publish article."""
        article = get_object_or_404(Article, pk=pk)

        if article.publish():
            self.message_user(
                request,
                f"Article '{article.title}' published successfully.",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "Article must be in review to publish.",
                messages.ERROR
            )

        return redirect("admin:articles_article_change", pk)
```

---

## Middleware

### Type-Safe Middleware

```python
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from typing import Callable
import time

# Modern middleware (Django 1.10+)
class TimingMiddleware:
    """Middleware to measure request processing time."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request and add timing header."""
        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time
        response["X-Request-Duration"] = str(duration)

        return response

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable[..., HttpResponse],
        view_args: tuple[Any, ...],
        view_kwargs: dict[str, Any]
    ) -> HttpResponse | None:
        """Optional: process view before it's called."""
        request.view_start_time = time.time()  # type: ignore[attr-defined]
        return None


class AuthenticationMiddleware:
    """Custom authentication middleware."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Add custom auth attribute to request."""
        # Add custom auth logic
        request.custom_auth = True  # type: ignore[attr-defined]

        response = self.get_response(request)
        return response


# Legacy middleware (using MiddlewareMixin)
class LegacyMiddleware(MiddlewareMixin):
    """Legacy-style middleware for compatibility."""

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Process request before view."""
        # Return None to continue processing
        # Return HttpResponse to short-circuit
        return None

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse
    ) -> HttpResponse:
        """Process response after view."""
        response["X-Custom-Header"] = "Custom Value"
        return response

    def process_exception(
        self,
        request: HttpRequest,
        exception: Exception
    ) -> HttpResponse | None:
        """Handle exceptions from views."""
        # Return None to let Django handle it
        # Return HttpResponse to handle it custom
        return None
```

---

## Signals

### Signal Typing

```python
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver, Signal
from django.http import HttpRequest
from typing import Any, Type

# Define custom signal
article_viewed: Signal = Signal()


@receiver(post_save, sender=Article)
def article_post_save(
    sender: Type[Article],
    instance: Article,
    created: bool,
    **kwargs: Any
) -> None:
    """Handle article save with proper typing."""
    if created:
        # New article created
        print(f"New article created: {instance.title}")
    else:
        # Existing article updated
        print(f"Article updated: {instance.title}")


@receiver(pre_delete, sender=Article)
def article_pre_delete(
    sender: Type[Article],
    instance: Article,
    **kwargs: Any
) -> None:
    """Handle article deletion."""
    print(f"Deleting article: {instance.title}")

    # Archive related data before deletion
    # ...


@receiver(article_viewed)
def handle_article_viewed(
    sender: Type[Article],
    instance: Article,
    request: HttpRequest,
    **kwargs: Any
) -> None:
    """Handle custom article_viewed signal."""
    # Log view
    print(f"Article viewed: {instance.title} by {request.user}")

    # Update analytics
    # ...


# Sending custom signals
def article_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    """View that sends custom signal."""
    article = get_object_or_404(Article, pk=pk)

    # Send signal
    article_viewed.send(
        sender=Article,
        instance=article,
        request=request
    )

    return render(request, "articles/detail.html", {"article": article})
```

---

## Template Context

### Typed Context Processors

```python
from django.http import HttpRequest
from typing import TypedDict

class BaseContext(TypedDict):
    """Type definition for base context."""
    site_name: str
    year: int
    debug: bool


def base_context(request: HttpRequest) -> BaseContext:
    """Context processor with typed return."""
    return {
        "site_name": "My Site",
        "year": 2024,
        "debug": settings.DEBUG
    }


class UserContext(TypedDict, total=False):
    """Context with optional fields."""
    user_name: str
    is_authenticated: bool
    profile_url: str


def user_context(request: HttpRequest) -> UserContext:
    """Add user info to context."""
    context: UserContext = {}

    if request.user.is_authenticated:
        context["user_name"] = request.user.get_full_name()
        context["is_authenticated"] = True
        context["profile_url"] = f"/profile/{request.user.pk}/"
    else:
        context["is_authenticated"] = False

    return context
```

### View Context Typing

```python
from typing import TypedDict, NotRequired

class ArticleListContext(TypedDict):
    """Type for article list view context."""
    articles: models.QuerySet[Article]
    title: str
    page_obj: Any  # Django paginator object
    is_paginated: bool
    popular_tags: NotRequired[models.QuerySet[Tag]]


def article_list_view(request: HttpRequest) -> HttpResponse:
    """View with fully typed context."""
    articles = Article.objects.published()

    context: ArticleListContext = {
        "articles": articles,
        "title": "Articles",
        "page_obj": None,  # Would be set by paginator
        "is_paginated": False
    }

    return render(request, "articles/list.html", context)
```

---

## Django REST Framework

### Serializer Typing

```python
from rest_framework import serializers
from typing import Any, OrderedDict

class ArticleSerializer(serializers.ModelSerializer[Article]):
    """Type-safe serializer for Article."""

    # Computed fields
    author_name = serializers.SerializerMethodField()
    tag_names = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "content",
            "published",
            "author",
            "author_name",
            "tags",
            "tag_names",
            "created_at"
        ]
        read_only_fields = ["id", "created_at", "author_name", "tag_names"]

    def get_author_name(self, obj: Article) -> str:
        """Get author name with proper typing."""
        return obj.author.user.get_full_name()

    def get_tag_names(self, obj: Article) -> list[str]:
        """Get list of tag names."""
        return obj.get_tag_names()

    def validate_title(self, value: str) -> str:
        """Validate title field."""
        if len(value) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters"
            )
        return value.strip()

    def validate(self, attrs: OrderedDict[str, Any]) -> OrderedDict[str, Any]:
        """Cross-field validation."""
        if attrs.get("published") and len(attrs.get("content", "")) < 100:
            raise serializers.ValidationError(
                "Published articles must have substantial content"
            )
        return attrs

    def create(self, validated_data: OrderedDict[str, Any]) -> Article:
        """Create article with proper typing."""
        tags = validated_data.pop("tags", [])
        article = Article.objects.create(**validated_data)
        article.tags.set(tags)
        return article

    def update(
        self,
        instance: Article,
        validated_data: OrderedDict[str, Any]
    ) -> Article:
        """Update article with proper typing."""
        tags = validated_data.pop("tags", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        return instance


class TagSerializer(serializers.ModelSerializer[Tag]):
    """Serializer for Tag."""

    article_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "article_count"]
        read_only_fields = ["id", "article_count"]

    def get_article_count(self, obj: Tag) -> int:
        """Get count of articles with this tag."""
        return obj.articles.count()
```

### ViewSet Typing

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from typing import Any

class ArticleViewSet(viewsets.ModelViewSet[Article]):
    """Type-safe ViewSet for Article."""

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_queryset(self) -> models.QuerySet[Article]:
        """Filter queryset with proper typing."""
        queryset = super().get_queryset()

        # Filter by query params
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__slug=tag)

        return queryset.select_related("author__user").prefetch_related("tags")

    def perform_create(self, serializer: ArticleSerializer) -> None:
        """Set author on create."""
        serializer.save(author=self.request.user.author)

    @action(detail=True, methods=["post"])
    def publish(self, request: Request, pk: int | None = None) -> Response:
        """Custom action to publish article."""
        article = self.get_object()

        if article.publish():
            return Response(
                {"status": "published"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"error": "Cannot publish article in current state"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=["get"])
    def recent(self, request: Request) -> Response:
        """Get recent articles."""
        articles = self.get_queryset().recent()
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)


class ReadOnlyArticleViewSet(viewsets.ReadOnlyModelViewSet[Article]):
    """Read-only viewset for public article access."""

    queryset = Article.objects.published()
    serializer_class = ArticleSerializer

    def get_queryset(self) -> models.QuerySet[Article]:
        """Only published articles."""
        return super().get_queryset().select_related(
            "author__user"
        ).prefetch_related("tags")
```

---

## Advanced Patterns

### Generic Views with Type Parameters

```python
from typing import TypeVar, Generic
from django.views.generic import ListView
from django.db.models import Model

_ModelT = TypeVar("_ModelT", bound=Model)

class FilteredListView(ListView[_ModelT], Generic[_ModelT]):
    """Generic filtered list view."""

    def get_queryset(self) -> models.QuerySet[_ModelT]:
        """Apply filters from query params."""
        queryset = super().get_queryset()

        # Apply generic filters
        for key, value in self.request.GET.items():
            if hasattr(self.model, key):
                queryset = queryset.filter(**{key: value})

        return queryset


class ArticleFilteredListView(FilteredListView[Article]):
    """Article list with filtering."""
    model = Article
    template_name = "articles/list.html"
```

### Protocol for Duck Typing

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Publishable(Protocol):
    """Protocol for publishable models."""
    published: bool

    def publish(self) -> bool:
        ...

    def can_edit(self) -> bool:
        ...


def publish_item(item: Publishable) -> bool:
    """Publish any publishable item."""
    if not item.can_edit():
        return False

    return item.publish()


# Works with any model implementing the protocol
article = Article.objects.first()
if article and isinstance(article, Publishable):
    publish_item(article)
```

---

## Common Pitfalls

### Pitfall 1: Optional Foreign Keys

```python
# WRONG - mypy error: Article | None not compatible with Article
def get_article_title(pk: int) -> str:
    article = Article.objects.filter(pk=pk).first()
    return article.title  # Error: article might be None


# RIGHT - Handle None case
def get_article_title(pk: int) -> str | None:
    article = Article.objects.filter(pk=pk).first()
    if article is None:
        return None
    return article.title


# OR use get_object_or_404
def get_article_title_safe(pk: int) -> str:
    article = get_object_or_404(Article, pk=pk)
    return article.title  # No error, get_object_or_404 returns Article
```

### Pitfall 2: QuerySet vs Manager

```python
# WRONG - Manager is not QuerySet
def filter_articles(articles: models.QuerySet[Article]) -> models.QuerySet[Article]:
    return articles.filter(published=True)

# This fails:
filter_articles(Article.objects)  # Type error


# RIGHT - Accept Manager or QuerySet
from django.db.models import Manager, QuerySet
from typing import Union

def filter_articles(
    articles: Union[Manager[Article], QuerySet[Article]]
) -> QuerySet[Article]:
    if isinstance(articles, Manager):
        articles = articles.all()
    return articles.filter(published=True)
```

### Pitfall 3: ClassVar for Class Attributes

```python
# WRONG - mypy thinks objects is instance attribute
class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects = models.Manager()  # Type error


# RIGHT - Use ClassVar for class-level attributes
from typing import ClassVar

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects: ClassVar[models.Manager["Article"]] = models.Manager()
```

### Pitfall 4: Cleaned Data Dictionary

```python
# WRONG - cleaned_data keys might not exist
def process_form(form: ArticleForm) -> None:
    title = form.cleaned_data["title"]  # KeyError if validation failed


# RIGHT - Check is_valid first and use .get()
def process_form(form: ArticleForm) -> None:
    if form.is_valid():
        title = form.cleaned_data["title"]  # Safe
        # OR
        title = form.cleaned_data.get("title", "")  # Even safer
```

---

## Best Practices

### 1. Use Strict Mode Gradually

Start with basic type checking and enable stricter rules over time:

```ini
[mypy]
# Start here
check_untyped_defs = True
warn_return_any = True
warn_unused_configs = True

# Add later
disallow_untyped_defs = True
disallow_any_generics = True
strict = True
```

### 2. Type All Public APIs

Always type:
- View functions and methods
- Model methods
- Form clean methods
- Serializer methods
- Custom managers

### 3. Use TypedDict for Complex Dictionaries

```python
from typing import TypedDict

class ArticleData(TypedDict):
    title: str
    content: str
    author_id: int
    tag_ids: list[int]


def create_article_from_data(data: ArticleData) -> Article:
    """Create article with typed dictionary."""
    tags = Tag.objects.filter(id__in=data["tag_ids"])
    article = Article.objects.create(
        title=data["title"],
        content=data["content"],
        author_id=data["author_id"]
    )
    article.tags.set(tags)
    return article
```

### 4. Document Complex Types

```python
from typing import TypeAlias

# Type alias for complex types
ArticleQuerySet: TypeAlias = models.QuerySet[Article]
ArticleList: TypeAlias = list[Article]
ArticleDict: TypeAlias = dict[str, Any]

def process_articles(articles: ArticleQuerySet) -> ArticleDict:
    """Process articles with clear type aliases."""
    return {
        "count": articles.count(),
        "published": articles.filter(published=True).count()
    }
```

### 5. Use reveal_type for Debugging

```python
from typing import reveal_type

articles = Article.objects.published()
reveal_type(articles)  # mypy will show the inferred type

# Output: Revealed type is 'QuerySet[Article]'
```

### 6. Leverage TYPE_CHECKING

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Imports only for type checking, not runtime
    from django.contrib.auth.models import User
    from .models import Article

def get_user_articles(user: "User") -> "models.QuerySet[Article]":
    """Use string annotations to avoid circular imports."""
    return Article.objects.filter(author__user=user)
```

---

## Conclusion

This guide covers comprehensive type annotations for Django applications. Key takeaways:

1. **Always annotate models** - Fields, managers, and methods
2. **Type views properly** - Both FBV and CBV patterns
3. **Use Generic types** - Especially for QuerySets and Managers
4. **Handle None cases** - Django often returns Optional types
5. **Leverage django-stubs** - It does most of the work
6. **Enable mypy gradually** - Don't try to fix everything at once
7. **Document with types** - Types serve as documentation

With proper typing, you'll catch bugs earlier, improve IDE support, and make your Django codebase more maintainable.

---

**Additional Resources:**

- [django-stubs documentation](https://github.com/typeddjango/django-stubs)
- [mypy documentation](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [Django typing best practices](https://docs.djangoproject.com/en/stable/ref/contrib/gis/tutorial/)
