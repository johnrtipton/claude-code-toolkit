"""
Comprehensive Django Views with Type Annotations Template

This template provides fully-typed examples for all common Django view patterns:
- Function-based views (FBV)
- Class-based views (CBV)
- Generic views with model type parameters
- View mixins with proper typing
- Authentication and permission mixins
- JSON API views
- Form handling with type safety

Type annotation conventions used:
- HttpRequest: Always annotate the request parameter
- HttpResponse: Use specific response types (HttpResponse, JsonResponse, etc.)
- QuerySet[Model]: Use generic QuerySet types for queryset returns
- Dict[str, Any]: Standard type for context dictionaries
- Optional[Model]: For nullable model instances
- Type[Model]: For model class parameters
"""

from typing import Any, Dict, List, Optional, Type, Union, cast
from datetime import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.models import User
from django.core.paginator import Paginator, Page
from django.db.models import QuerySet, Model, Q
from django.forms import Form, ModelForm
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
    TemplateView,
)
from django.views.generic.detail import SingleObjectMixin


# Example models for demonstration (replace with your actual models)
class Article(Model):
    """Example model for demonstration purposes."""
    title: str
    content: str
    author: User
    created_at: datetime
    published: bool

    class Meta:
        app_label = "blog"


class Comment(Model):
    """Example model for demonstration purposes."""
    article: Article
    author: User
    text: str
    created_at: datetime

    class Meta:
        app_label = "blog"


class ArticleForm(ModelForm):
    """Example form for demonstration purposes."""
    class Meta:
        model = Article
        fields = ["title", "content", "published"]


# ============================================================================
# FUNCTION-BASED VIEWS (FBV)
# ============================================================================

def article_list_view(request: HttpRequest) -> HttpResponse:
    """
    Basic function-based view with type annotations.

    Type annotations:
    - request: HttpRequest - The incoming request object
    - return: HttpResponse - The response object
    """
    articles: QuerySet[Article] = Article.objects.all()
    context: Dict[str, Any] = {
        "articles": articles,
        "page_title": "All Articles",
    }
    return render(request, "blog/article_list.html", context)


@require_GET
def article_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    FBV with path parameter and decorator.

    Type annotations:
    - pk: int - Primary key from URL pattern
    - article: Article - Retrieved model instance (use get_object_or_404 for safety)
    """
    article: Article = get_object_or_404(Article, pk=pk)
    comments: QuerySet[Comment] = article.comment_set.all()

    context: Dict[str, Any] = {
        "article": article,
        "comments": comments,
    }
    return render(request, "blog/article_detail.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def article_create_view(request: HttpRequest) -> HttpResponse:
    """
    FBV with authentication decorator and form handling.

    Type annotations:
    - form: ArticleForm - The form instance
    - return: HttpResponse or HttpResponseRedirect
    """
    if request.method == "POST":
        form: ArticleForm = ArticleForm(request.POST)
        if form.is_valid():
            article: Article = form.save(commit=False)
            article.author = request.user
            article.save()
            return redirect("article-detail", pk=article.pk)
    else:
        form = ArticleForm()

    context: Dict[str, Any] = {"form": form}
    return render(request, "blog/article_form.html", context)


@permission_required("blog.change_article", raise_exception=True)
def article_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    FBV with permission decorator.

    Type annotations:
    - article: Article - The instance being updated
    - form: ArticleForm - Form bound to the instance
    """
    article: Article = get_object_or_404(Article, pk=pk)

    if request.method == "POST":
        form: ArticleForm = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            return redirect("article-detail", pk=article.pk)
    else:
        form = ArticleForm(instance=article)

    context: Dict[str, Any] = {
        "form": form,
        "article": article,
    }
    return render(request, "blog/article_form.html", context)


@require_POST
@login_required
def article_delete_view(request: HttpRequest, pk: int) -> HttpResponseRedirect:
    """
    FBV for deletion with specific return type.

    Type annotations:
    - return: HttpResponseRedirect - Always redirects after deletion
    """
    article: Article = get_object_or_404(Article, pk=pk)
    article.delete()
    return redirect("article-list")


# ============================================================================
# BASIC CLASS-BASED VIEWS
# ============================================================================

class ArticleListView(ListView[Article]):
    """
    ListView with generic type parameter.

    Type annotations:
    - ListView[Article] - Generic type specifies the model
    - model: Type[Article] - The model class
    - queryset: QuerySet[Article] - The queryset to use
    - context_object_name: str - Name used in template context
    """
    model: Type[Article] = Article
    template_name: str = "blog/article_list.html"
    context_object_name: str = "articles"
    paginate_by: int = 10

    def get_queryset(self) -> QuerySet[Article]:
        """
        Override to customize the queryset.

        Return type: QuerySet[Article] - Must match the generic type parameter
        """
        queryset: QuerySet[Article] = super().get_queryset()

        # Example: Filter by search query
        search_query: Optional[str] = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(content__icontains=search_query)
            )

        # Example: Filter published articles
        return queryset.filter(published=True).order_by("-created_at")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Add additional context to the template.

        Type annotations:
        - **kwargs: Any - Accept any keyword arguments
        - return: Dict[str, Any] - Standard context dictionary type
        """
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context["page_title"] = "Published Articles"
        context["total_count"] = self.get_queryset().count()
        return context


class ArticleDetailView(DetailView[Article]):
    """
    DetailView with generic type parameter.

    Type annotations:
    - DetailView[Article] - Generic type for the model
    - object: Article - The retrieved object (available after get_object())
    """
    model: Type[Article] = Article
    template_name: str = "blog/article_detail.html"
    context_object_name: str = "article"

    def get_object(self, queryset: Optional[QuerySet[Article]] = None) -> Article:
        """
        Retrieve the object with custom logic.

        Type annotations:
        - queryset: Optional[QuerySet[Article]] - Optional custom queryset
        - return: Article - The retrieved model instance
        """
        obj: Article = super().get_object(queryset)

        # Example: Check if user has permission to view
        if not obj.published and obj.author != self.request.user:
            raise PermissionError("You cannot view unpublished articles.")

        return obj

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add related comments to context."""
        context: Dict[str, Any] = super().get_context_data(**kwargs)

        # self.object is available and properly typed as Article
        article: Article = self.object
        comments: QuerySet[Comment] = article.comment_set.all().select_related("author")

        context["comments"] = comments
        context["comment_count"] = comments.count()
        return context


# ============================================================================
# CREATE, UPDATE, DELETE VIEWS
# ============================================================================

class ArticleCreateView(LoginRequiredMixin, CreateView[Article, ArticleForm]):
    """
    CreateView with authentication and generic types.

    Type annotations:
    - CreateView[Article, ArticleForm] - Model and Form types
    - model: Type[Article] - Model class
    - form_class: Type[ArticleForm] - Form class
    - success_url: str - URL to redirect after successful creation
    """
    model: Type[Article] = Article
    form_class: Type[ArticleForm] = ArticleForm
    template_name: str = "blog/article_form.html"
    success_url: str = reverse_lazy("article-list")

    def form_valid(self, form: ArticleForm) -> HttpResponse:
        """
        Process valid form submission.

        Type annotations:
        - form: ArticleForm - The validated form instance
        - return: HttpResponse - The response (usually a redirect)
        """
        # Set the author before saving
        article: Article = form.save(commit=False)
        article.author = self.request.user
        article.save()

        # self.object is now available and typed as Article
        self.object: Article

        return super().form_valid(form)

    def form_invalid(self, form: ArticleForm) -> HttpResponse:
        """
        Handle invalid form submission.

        Type annotations:
        - form: ArticleForm - The invalid form instance with errors
        - return: HttpResponse - Response rendering the form with errors
        """
        # Add custom error handling or logging
        return super().form_invalid(form)

    def get_form_kwargs(self) -> Dict[str, Any]:
        """
        Customize form initialization kwargs.

        Return type: Dict[str, Any] - Form initialization arguments
        """
        kwargs: Dict[str, Any] = super().get_form_kwargs()
        # Example: Pass additional data to form
        kwargs["user"] = self.request.user
        return kwargs


class ArticleUpdateView(LoginRequiredMixin, UpdateView[Article, ArticleForm]):
    """
    UpdateView with authentication.

    Type annotations:
    - UpdateView[Article, ArticleForm] - Model and Form types
    - object: Article - The instance being updated (available after get_object())
    """
    model: Type[Article] = Article
    form_class: Type[ArticleForm] = ArticleForm
    template_name: str = "blog/article_form.html"
    context_object_name: str = "article"

    def get_success_url(self) -> str:
        """
        Dynamically determine success URL.

        Return type: str - The URL to redirect to after success
        """
        # self.object is typed as Article
        return reverse("article-detail", kwargs={"pk": self.object.pk})

    def get_queryset(self) -> QuerySet[Article]:
        """Restrict to articles owned by the current user."""
        queryset: QuerySet[Article] = super().get_queryset()
        return queryset.filter(author=self.request.user)


class ArticleDeleteView(LoginRequiredMixin, DeleteView[Article]):
    """
    DeleteView with authentication.

    Type annotations:
    - DeleteView[Article] - Model type
    - success_url: str - URL after successful deletion
    """
    model: Type[Article] = Article
    template_name: str = "blog/article_confirm_delete.html"
    success_url: str = reverse_lazy("article-list")
    context_object_name: str = "article"

    def get_queryset(self) -> QuerySet[Article]:
        """Only allow users to delete their own articles."""
        queryset: QuerySet[Article] = super().get_queryset()
        return queryset.filter(author=self.request.user)

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """
        Override delete to add custom logic.

        Type annotations:
        - request: HttpRequest - The request object
        - *args, **kwargs: Any - Additional arguments
        - return: HttpResponse - The response after deletion
        """
        # Add logging or cleanup before deletion
        self.object: Article = self.get_object()

        # Perform deletion
        return super().delete(request, *args, **kwargs)


# ============================================================================
# FORM VIEW
# ============================================================================

class ContactFormView(FormView[Form]):
    """
    FormView for non-model forms.

    Type annotations:
    - FormView[Form] - Generic form type
    - template_name: str - Template to render
    - success_url: str - Redirect URL after success
    """
    template_name: str = "contact_form.html"
    form_class: Type[Form] = Form  # Replace with actual form class
    success_url: str = reverse_lazy("contact-success")

    def form_valid(self, form: Form) -> HttpResponse:
        """
        Process valid form submission.

        Type annotations:
        - form: Form - The validated form
        """
        # Example: Send email or process data
        # cleaned_data: Dict[str, Any] = form.cleaned_data
        return super().form_valid(form)


# ============================================================================
# VIEW MIXINS WITH PROPER TYPING
# ============================================================================

class MultiplePermissionsRequiredMixin(PermissionRequiredMixin):
    """
    Custom mixin requiring multiple permissions.

    Type annotations for overridden methods:
    - permission_required: List[str] or str - Required permissions
    """
    permission_required: List[str] = []

    def has_permission(self) -> bool:
        """
        Check if user has all required permissions.

        Return type: bool - True if user has all permissions
        """
        perms: Union[List[str], str] = self.get_permission_required()
        if isinstance(perms, str):
            perms = [perms]
        return self.request.user.has_perms(perms)


class AuthorRequiredMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to object authors.

    Type annotations:
    - Uses test_func to verify user is the author
    """

    def test_func(self) -> bool:
        """
        Test if current user is the object author.

        Return type: bool - True if user is the author
        """
        obj: Article = self.get_object()  # type: ignore[assignment]
        return obj.author == self.request.user


class PaginationMixin:
    """
    Reusable pagination mixin with type annotations.
    """
    paginate_by: int = 20

    def paginate_queryset(
        self, queryset: QuerySet[Any], page_size: int
    ) -> tuple[Paginator, Page[Any], QuerySet[Any], bool]:
        """
        Paginate the queryset with proper types.

        Type annotations:
        - queryset: QuerySet[Any] - The queryset to paginate
        - page_size: int - Number of items per page
        - return: tuple with Paginator, Page, queryset, and boolean
        """
        paginator: Paginator = Paginator(queryset, page_size)
        page_kwarg: str = self.page_kwarg  # type: ignore[attr-defined]
        page_number: str = self.request.GET.get(page_kwarg) or "1"  # type: ignore[attr-defined]

        page: Page[Any] = paginator.get_page(page_number)

        return (
            paginator,
            page,
            page.object_list,
            page.has_other_pages(),
        )


# ============================================================================
# ADVANCED CBV EXAMPLES
# ============================================================================

class ArticleListWithFilterView(LoginRequiredMixin, ListView[Article]):
    """
    ListView combining multiple mixins with complex filtering.
    """
    model: Type[Article] = Article
    template_name: str = "blog/article_list.html"
    context_object_name: str = "articles"
    paginate_by: int = 10

    def get_queryset(self) -> QuerySet[Article]:
        """Complex queryset with multiple filters."""
        queryset: QuerySet[Article] = Article.objects.select_related("author")

        # Filter by author
        author_id: Optional[str] = self.request.GET.get("author")
        if author_id:
            queryset = queryset.filter(author_id=int(author_id))

        # Filter by published status
        published: Optional[str] = self.request.GET.get("published")
        if published:
            queryset = queryset.filter(published=published.lower() == "true")

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add filter options to context."""
        context: Dict[str, Any] = super().get_context_data(**kwargs)

        # Add all authors for filter dropdown
        authors: QuerySet[User] = User.objects.filter(
            article__isnull=False
        ).distinct()
        context["authors"] = authors

        return context


class ArticleAuthorUpdateView(
    LoginRequiredMixin, AuthorRequiredMixin, UpdateView[Article, ArticleForm]
):
    """
    UpdateView combining multiple mixins with proper typing.

    Mixins applied (order matters):
    1. LoginRequiredMixin - Requires authentication
    2. AuthorRequiredMixin - Requires user to be the author
    3. UpdateView - Provides update functionality
    """
    model: Type[Article] = Article
    form_class: Type[ArticleForm] = ArticleForm
    template_name: str = "blog/article_form.html"

    def get_success_url(self) -> str:
        """Return to article detail after update."""
        return reverse("article-detail", kwargs={"pk": self.object.pk})


# ============================================================================
# JSON API VIEWS
# ============================================================================

class ArticleJSONListView(View):
    """
    JSON API view for article list.

    Type annotations:
    - Returns JsonResponse for API endpoints
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """
        Return articles as JSON.

        Type annotations:
        - request: HttpRequest - The incoming request
        - return: JsonResponse - JSON formatted response
        """
        articles: QuerySet[Article] = Article.objects.filter(published=True)

        data: List[Dict[str, Any]] = [
            {
                "id": article.pk,
                "title": article.title,
                "author": article.author.username,
                "created_at": article.created_at.isoformat(),
            }
            for article in articles
        ]

        return JsonResponse({"articles": data}, safe=False)


class ArticleJSONDetailView(View):
    """
    JSON API view for article detail.
    """

    def get(self, request: HttpRequest, pk: int) -> Union[JsonResponse, HttpResponseNotFound]:
        """
        Return single article as JSON.

        Type annotations:
        - pk: int - Article primary key
        - return: JsonResponse or HttpResponseNotFound
        """
        try:
            article: Article = Article.objects.get(pk=pk, published=True)
        except Article.DoesNotExist:
            return HttpResponseNotFound(
                JsonResponse({"error": "Article not found"}, status=404)
            )

        data: Dict[str, Any] = {
            "id": article.pk,
            "title": article.title,
            "content": article.content,
            "author": {
                "id": article.author.pk,
                "username": article.author.username,
            },
            "created_at": article.created_at.isoformat(),
        }

        return JsonResponse(data)


@method_decorator(csrf_exempt, name="dispatch")
class ArticleAPIView(View):
    """
    RESTful API view with multiple HTTP methods.

    Type annotations for each HTTP method handler.
    """

    def get(self, request: HttpRequest, pk: Optional[int] = None) -> JsonResponse:
        """GET - Retrieve article(s)."""
        if pk:
            article: Article = get_object_or_404(Article, pk=pk)
            data: Dict[str, Any] = {
                "id": article.pk,
                "title": article.title,
            }
        else:
            articles: QuerySet[Article] = Article.objects.all()[:10]
            data = {
                "articles": [{"id": a.pk, "title": a.title} for a in articles]
            }

        return JsonResponse(data)

    def post(self, request: HttpRequest) -> Union[JsonResponse, HttpResponseBadRequest]:
        """
        POST - Create new article.

        Type annotations:
        - return: JsonResponse on success, HttpResponseBadRequest on error
        """
        # In production, use proper form/serializer validation
        title: Optional[str] = request.POST.get("title")
        content: Optional[str] = request.POST.get("content")

        if not title or not content:
            return HttpResponseBadRequest(
                JsonResponse({"error": "Title and content required"})
            )

        article: Article = Article.objects.create(
            title=title,
            content=content,
            author=request.user,
            published=False,
        )

        return JsonResponse({"id": article.pk, "title": article.title}, status=201)

    def put(self, request: HttpRequest, pk: int) -> JsonResponse:
        """PUT - Update article."""
        article: Article = get_object_or_404(Article, pk=pk)

        # Parse request body for PUT data
        # In production, use proper form/serializer validation

        return JsonResponse({"id": article.pk, "title": article.title})

    def delete(self, request: HttpRequest, pk: int) -> JsonResponse:
        """DELETE - Delete article."""
        article: Article = get_object_or_404(Article, pk=pk)
        article.delete()

        return JsonResponse({"success": True}, status=204)


# ============================================================================
# TEMPLATE VIEW EXAMPLE
# ============================================================================

class AboutTemplateView(TemplateView):
    """
    Simple template view with type annotations.

    Type annotations:
    - template_name: str - Path to template
    """
    template_name: str = "about.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add context for template rendering."""
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context["page_title"] = "About Us"
        context["team_size"] = 10
        return context
