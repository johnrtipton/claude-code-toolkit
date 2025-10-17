# Troubleshooting Mypy with Django: Complete Error Reference

**Version:** 1.0
**Last Updated:** October 2025
**Applies to:** mypy 1.11+, django-stubs 5.1+, Django 4.2+/5.0+

This comprehensive troubleshooting guide covers every common mypy error you'll encounter when type-checking Django projects, with practical solutions and real-world examples.

---

## Table of Contents

1. [Quick Error Lookup](#quick-error-lookup)
2. [Variable and Assignment Errors](#variable-and-assignment-errors)
3. [Attribute and Method Errors](#attribute-and-method-errors)
4. [Django Manager and QuerySet Errors](#django-manager-and-queryset-errors)
5. [Foreign Key and Relationship Errors](#foreign-key-and-relationship-errors)
6. [Missing Stubs and Import Errors](#missing-stubs-and-import-errors)
7. [Type Ignore Comments](#type-ignore-comments)
8. [Third-Party Package Issues](#third-party-package-issues)
9. [Migration Typing Problems](#migration-typing-problems)
10. [Settings Module Errors](#settings-module-errors)
11. [Dynamic Attribute Errors](#dynamic-attribute-errors)
12. [Circular Import Issues](#circular-import-issues)
13. [Performance and Debug Issues](#performance-and-debug-issues)
14. [Generic and Protocol Errors](#generic-and-protocol-errors)
15. [Decorator and Metaclass Issues](#decorator-and-metaclass-issues)

---

## Quick Error Lookup

Use this table to quickly find solutions for common error codes:

| Error Code | Description | Common Cause | Quick Fix |
|------------|-------------|--------------|-----------|
| `var-annotated` | Variable needs type annotation | Missing type hint | Add explicit type annotation |
| `assignment` | Type mismatch in assignment | Wrong type | Cast or fix the type |
| `attr-defined` | Attribute doesn't exist | Wrong model/class | Check the model definition |
| `call-arg` | Wrong arguments to function | Missing/extra args | Fix function call |
| `arg-type` | Wrong argument type | Type mismatch | Cast or convert type |
| `return-value` | Wrong return type | Type mismatch | Fix return statement |
| `union-attr` | Attribute on Union type | Optional value | Use type narrowing |
| `override` | Method signature mismatch | Parent class change | Match parent signature |
| `misc` | Generic error | Various | Check error message |
| `no-untyped-def` | Function needs types | Missing annotations | Add type hints |
| `no-untyped-call` | Calling untyped code | No stubs | Add type: ignore or stubs |

---

## Variable and Assignment Errors

### Error: `var-annotated` - Need Type Annotation for Variable

**Error Message:**
```
error: Need type annotation for "variable_name"  [var-annotated]
```

**What it means:**
Mypy cannot infer the type of a variable, usually because it's initialized to `None`, an empty collection, or a complex expression.

**Solution 1: Add Explicit Type Annotation (Preferred)**
```python
# ❌ Error
def process_users():
    users = None  # error: Need type annotation
    if should_fetch():
        users = User.objects.all()
    return users

# ✅ Fix with annotation
from typing import Optional
from django.db.models import QuerySet

def process_users() -> Optional[QuerySet[User]]:
    users: Optional[QuerySet[User]] = None
    if should_fetch():
        users = User.objects.all()
    return users
```

**Solution 2: Initialize with Proper Value**
```python
# ❌ Error
def get_user_ids():
    ids = []  # error: Need type annotation
    for user in User.objects.all():
        ids.append(user.id)
    return ids

# ✅ Fix by initializing with typed value
def get_user_ids() -> list[int]:
    ids: list[int] = []  # Explicit annotation
    for user in User.objects.all():
        ids.append(user.id)
    return ids

# ✅ Alternative: Use list comprehension (type inferred)
def get_user_ids() -> list[int]:
    return [user.id for user in User.objects.all()]
```

**Solution 3: Django Model Fields**
```python
# ❌ Error in model method
class Article(models.Model):
    title: str = models.CharField(max_length=200)

    def get_related_tags(self):
        tags = None  # error: Need type annotation
        if self.published:
            tags = self.tags.all()
        return tags

# ✅ Fix with proper typing
from typing import Optional
from django.db.models import QuerySet

class Article(models.Model):
    title: str = models.CharField(max_length=200)

    def get_related_tags(self) -> Optional[QuerySet["Tag"]]:
        tags: Optional[QuerySet[Tag]] = None
        if self.published:
            tags = self.tags.all()
        return tags
```

**When to use each solution:**
- **Solution 1**: When variable is conditionally assigned or None is a valid state
- **Solution 2**: For collections that start empty
- **Solution 3**: For Django QuerySets and related objects

---

### Error: `assignment` - Incompatible Type in Assignment

**Error Message:**
```
error: Incompatible types in assignment (expression has type "X", variable has type "Y")  [assignment]
```

**What it means:**
You're trying to assign a value of one type to a variable declared or inferred as another type.

**Solution 1: Fix the Type Mismatch**
```python
# ❌ Error
from django.contrib.auth.models import User

def get_user_id(username: str) -> int:
    user = User.objects.filter(username=username).first()
    return user.id  # error: Item "None" has no attribute "id"

# ✅ Fix with proper null handling
from typing import Optional

def get_user_id(username: str) -> Optional[int]:
    user = User.objects.filter(username=username).first()
    if user is None:
        return None
    return user.id

# ✅ Alternative: Use get_or_404 if in view
from django.shortcuts import get_object_or_404

def get_user_id(username: str) -> int:
    user = get_object_or_404(User, username=username)
    return user.id  # No error, user cannot be None
```

**Solution 2: Type Narrowing with Type Guards**
```python
# ❌ Error
from typing import Union

def process_id(id_value: Union[str, int]) -> str:
    # error: Incompatible return value type (got "Union[str, int]", expected "str")
    return id_value.upper()

# ✅ Fix with type narrowing
def process_id(id_value: Union[str, int]) -> str:
    if isinstance(id_value, int):
        return str(id_value)
    return id_value.upper()
```

**Solution 3: Django Form Cleaned Data**
```python
# ❌ Error
from django import forms

class UserForm(forms.Form):
    age = forms.IntegerField()

    def save(self) -> int:
        # error: Incompatible types (got "Union[int, Any]", expected "int")
        age: int = self.cleaned_data['age']
        return age

# ✅ Fix with proper typing
from typing import Any, TypedDict

class UserFormData(TypedDict):
    age: int

class UserForm(forms.Form):
    age = forms.IntegerField()

    cleaned_data: UserFormData  # Type the cleaned_data

    def save(self) -> int:
        return self.cleaned_data['age']  # Now correctly typed

# ✅ Alternative: Use cast
from typing import cast

class UserForm(forms.Form):
    age = forms.IntegerField()

    def save(self) -> int:
        age = cast(int, self.cleaned_data['age'])
        return age
```

**Solution 4: Django Model Field Updates**
```python
# ❌ Error
class Product(models.Model):
    name: str = models.CharField(max_length=100)
    price: Decimal = models.DecimalField(max_digits=10, decimal_places=2)

def update_price(product: Product, new_price: str) -> None:
    # error: Incompatible types in assignment (expression has type "str", variable has type "Decimal")
    product.price = new_price

# ✅ Fix by converting type
from decimal import Decimal

def update_price(product: Product, new_price: str) -> None:
    product.price = Decimal(new_price)
    product.save()
```

**When to use each solution:**
- **Solution 1**: For nullable database queries
- **Solution 2**: For Union types that need narrowing
- **Solution 3**: For Django forms with typed cleaned_data
- **Solution 4**: When converting between types

---

## Attribute and Method Errors

### Error: `attr-defined` - Attribute Not Found

**Error Message:**
```
error: "ClassName" has no attribute "attribute_name"  [attr-defined]
```

**What it means:**
Mypy cannot find the specified attribute on the class. Common with Django's dynamic attributes like `objects`, `pk`, `id`, or reverse relations.

**Solution 1: Django Model Manager (objects)**
```python
# ❌ Error (without django-stubs or wrong config)
from django.db import models

class Article(models.Model):
    title: str = models.CharField(max_length=200)

# error: "Type[Article]" has no attribute "objects"
articles = Article.objects.all()

# ✅ Fix: Ensure django-stubs is installed and configured
# Install: pip install django-stubs
# mypy.ini:
# [mypy]
# plugins = mypy_django_plugin.main

# ✅ Alternative: Explicit manager annotation
from typing import ClassVar
from django.db.models import Manager

class Article(models.Model):
    title: str = models.CharField(max_length=200)

    objects: ClassVar[Manager["Article"]] = Manager()

articles = Article.objects.all()  # Now works
```

**Solution 2: Reverse Relations**
```python
# ❌ Error
class Author(models.Model):
    name: str = models.CharField(max_length=100)

class Book(models.Model):
    title: str = models.CharField(max_length=200)
    author: Author = models.ForeignKey(Author, on_delete=models.CASCADE)

def get_author_books(author: Author):
    # error: "Author" has no attribute "book_set"
    return author.book_set.all()

# ✅ Fix 1: Use related_name
class Book(models.Model):
    title: str = models.CharField(max_length=200)
    author: Author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='books'  # Explicit name
    )

def get_author_books(author: Author):
    return author.books.all()  # Now type-safe

# ✅ Fix 2: Annotate the reverse relation
from typing import TYPE_CHECKING
from django.db.models import Manager

if TYPE_CHECKING:
    from django.db.models import QuerySet

class Author(models.Model):
    name: str = models.CharField(max_length=100)

    # Annotate reverse relation
    book_set: Manager["Book"]

def get_author_books(author: Author) -> "QuerySet[Book]":
    return author.book_set.all()
```

**Solution 3: Dynamic Attributes (Meta, pk, id)**
```python
# ❌ Error with custom attributes
class Article(models.Model):
    title: str = models.CharField(max_length=200)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_tags = None  # Dynamic attribute

def process_article(article: Article):
    # error: "Article" has no attribute "cached_tags"
    return article.cached_tags

# ✅ Fix: Declare in class body
class Article(models.Model):
    title: str = models.CharField(max_length=200)
    cached_tags: Optional[list[str]]  # Declare it

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_tags = None

# ✅ Alternative: Use __annotations__ for runtime attrs
class Article(models.Model):
    title: str = models.CharField(max_length=200)

    if TYPE_CHECKING:
        cached_tags: Optional[list[str]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_tags: Optional[list[str]] = None
```

**Solution 4: Third-Party Model Extensions**
```python
# ❌ Error with django-extensions or similar
from django_extensions.db.models import TimeStampedModel

class Article(TimeStampedModel):
    title: str = models.CharField(max_length=200)

def check_modified(article: Article):
    # error: "Article" has no attribute "modified"
    return article.modified

# ✅ Fix: Create stub or protocol
from typing import Protocol
from datetime import datetime

class TimeStamped(Protocol):
    created: datetime
    modified: datetime

class Article(TimeStampedModel):
    title: str = models.CharField(max_length=200)

def check_modified(article: Article) -> datetime:
    return article.modified  # Works if stubs exist

# ✅ Alternative: Use type: ignore with comment
def check_modified(article: Article) -> datetime:
    return article.modified  # type: ignore[attr-defined]  # From TimeStampedModel
```

**When to use each solution:**
- **Solution 1**: For standard Django managers
- **Solution 2**: For reverse ForeignKey/ManyToMany relations
- **Solution 3**: For custom runtime attributes
- **Solution 4**: For third-party model mixins

---

### Error: `call-arg` - Wrong Function Arguments

**Error Message:**
```
error: Unexpected keyword argument "argument_name" for "function_name"  [call-arg]
error: Too many arguments for "function_name"  [call-arg]
error: Missing positional argument "argument_name" in call to "function_name"  [call-arg]
```

**What it means:**
The function call doesn't match the function signature - wrong number or names of arguments.

**Solution 1: Django get_or_create Kwargs**
```python
# ❌ Error
from django.contrib.auth.models import User

def create_user(username: str, email: str):
    # error: Unexpected keyword argument
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'invalid_field': 'value'}
    )

# ✅ Fix: Only use valid fields
def create_user(username: str, email: str) -> tuple[User, bool]:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'is_active': True}
    )
    return user, created

# ✅ With TypedDict for better validation
from typing import TypedDict

class UserDefaults(TypedDict, total=False):
    email: str
    is_active: bool
    first_name: str

def create_user(username: str, defaults: UserDefaults) -> tuple[User, bool]:
    return User.objects.get_or_create(
        username=username,
        defaults=defaults
    )
```

**Solution 2: Django Form __init__**
```python
# ❌ Error
from django import forms

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content']

    def __init__(self, *args, **kwargs):
        # error: Missing positional argument "instance"
        super().__init__(args, kwargs)

# ✅ Fix: Proper *args, **kwargs
class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Note the * operators
```

**Solution 3: Custom Managers**
```python
# ❌ Error
from typing import Any
from django.db import models

class ArticleManager(models.Manager):
    def published(self):
        return self.filter(status='published')

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects: ArticleManager = ArticleManager()

# error: Too many arguments
articles = Article.objects.published('invalid_arg')

# ✅ Fix: Proper method signature
class ArticleQuerySet(models.QuerySet["Article"]):
    def published(self) -> "ArticleQuerySet":
        return self.filter(status='published')

    def by_author(self, author: "User") -> "ArticleQuerySet":
        return self.filter(author=author)

class ArticleManager(models.Manager["Article"]):
    def get_queryset(self) -> ArticleQuerySet:
        return ArticleQuerySet(self.model, using=self._db)

    def published(self) -> ArticleQuerySet:
        return self.get_queryset().published()

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects: ArticleManager = ArticleManager()

# Now type-safe
articles = Article.objects.published()
```

**When to use each solution:**
- **Solution 1**: For Django ORM method calls
- **Solution 2**: For form/class initialization
- **Solution 3**: For custom manager methods

---

## Django Manager and QuerySet Errors

### Error: Manager/QuerySet Type Issues

**Error Message:**
```
error: Incompatible return value type (got "Manager[Article]", expected "QuerySet[Article]")
error: Cannot determine type of 'objects'
error: "Manager[Article]" has no attribute "filter"
```

**What it means:**
Confusion between Manager and QuerySet types, or incorrect typing of custom managers.

**Solution 1: Custom QuerySet with Manager**
```python
# ❌ Wrong typing
from django.db import models

class ArticleManager(models.Manager):
    def published(self):  # Return type unclear
        return self.filter(published=True)

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects = ArticleManager()  # No type annotation

# ✅ Correct typing with QuerySet
from typing import TYPE_CHECKING
from django.db import models

if TYPE_CHECKING:
    from django.db.models import QuerySet

class ArticleQuerySet(models.QuerySet["Article"]):
    def published(self) -> "ArticleQuerySet":
        return self.filter(published=True)

    def recent(self) -> "ArticleQuerySet":
        return self.order_by('-created_at')[:10]

class ArticleManager(models.Manager["Article"]):
    def get_queryset(self) -> ArticleQuerySet:
        return ArticleQuerySet(self.model, using=self._db)

    def published(self) -> ArticleQuerySet:
        return self.get_queryset().published()

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    published: bool = models.BooleanField(default=False)

    objects: ArticleManager = ArticleManager()

# Now fully typed
articles = Article.objects.published().recent()
```

**Solution 2: Manager.from_queryset()**
```python
# ❌ Error with from_queryset
class ArticleQuerySet(models.QuerySet["Article"]):
    def published(self) -> "ArticleQuerySet":
        return self.filter(published=True)

ArticleManager = models.Manager.from_queryset(ArticleQuerySet)

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects = ArticleManager()  # Type unclear

# ✅ Fix with proper annotation
from typing import ClassVar

class ArticleQuerySet(models.QuerySet["Article"]):
    def published(self) -> "ArticleQuerySet":
        return self.filter(published=True)

# Create the manager class
_ArticleManager = models.Manager.from_queryset(ArticleQuerySet)

class ArticleManager(_ArticleManager["Article"]):
    pass

class Article(models.Model):
    title: str = models.CharField(max_length=200)

    objects: ClassVar[ArticleManager] = ArticleManager()

# ✅ Alternative: Use type alias
from typing import TypeAlias

ArticleManager: TypeAlias = models.Manager.from_queryset(ArticleQuerySet)

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects: ClassVar[ArticleManager["Article"]] = ArticleManager()
```

**Solution 3: Chaining QuerySet Methods**
```python
# ❌ Error with chaining
def get_recent_published(count: int = 10):
    # error: "Manager[Article]" has no attribute "recent"
    return Article.objects.published().recent()

# ✅ Fix: Return QuerySet from manager
class ArticleQuerySet(models.QuerySet["Article"]):
    def published(self) -> "ArticleQuerySet":
        return self.filter(published=True)

    def recent(self, count: int = 10) -> "ArticleQuerySet":
        return self.order_by('-created_at')[:count]

class ArticleManager(models.Manager.from_queryset(ArticleQuerySet)["Article"]):
    pass

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    objects: ClassVar[ArticleManager] = ArticleManager()

def get_recent_published(count: int = 10) -> ArticleQuerySet:
    return Article.objects.published().recent(count)  # Now works
```

**Solution 4: Generic Manager Types**
```python
# ❌ Error with generic managers
from typing import TypeVar, Generic

T = TypeVar('T', bound=models.Model)

class BaseManager(models.Manager, Generic[T]):
    def active(self):
        # error: Cannot determine return type
        return self.filter(is_active=True)

# ✅ Fix: Use Self type (Python 3.11+)
from typing import Self

class BaseQuerySet(models.QuerySet[T]):
    def active(self) -> Self:
        return self.filter(is_active=True)

class BaseManager(models.Manager.from_queryset(BaseQuerySet)[T]):
    pass

# ✅ Alternative: For Python < 3.11
from typing import TypeVar

_QS = TypeVar('_QS', bound='BaseQuerySet')

class BaseQuerySet(models.QuerySet[T]):
    def active(self: _QS) -> _QS:
        return self.filter(is_active=True)
```

**When to use each solution:**
- **Solution 1**: For custom QuerySet and Manager pairs
- **Solution 2**: When using from_queryset()
- **Solution 3**: For method chaining
- **Solution 4**: For generic/reusable managers

---

## Foreign Key and Relationship Errors

### Error: ForeignKey Type Issues

**Error Message:**
```
error: Incompatible types in assignment (expression has type "int", variable has type "User")
error: Argument 1 has incompatible type "User"; expected "int"
error: "int" has no attribute "username"
```

**What it means:**
Confusion between the related object and the foreign key ID field.

**Solution 1: Understanding _id Suffix**
```python
# ❌ Error: Confusing FK object with FK id
class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: "User" = models.ForeignKey("auth.User", on_delete=models.CASCADE)

def update_author(article: Article, user_id: int):
    # error: Incompatible types (expression has type "int", variable has type "User")
    article.author = user_id

# ✅ Fix: Use _id suffix for ID assignment
def update_author(article: Article, user_id: int) -> None:
    article.author_id = user_id  # Correct: assign ID to _id field
    article.save()

# ✅ Alternative: Assign the object
from django.contrib.auth.models import User

def update_author(article: Article, user: User) -> None:
    article.author = user  # Correct: assign User object
    article.save()
```

**Solution 2: Optional ForeignKey (null=True)**
```python
# ❌ Error with nullable FK
class Comment(models.Model):
    text: str = models.TextField()
    parent: "Comment" = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

def get_parent_text(comment: Comment) -> str:
    # error: Item "None" has no attribute "text"
    return comment.parent.text

# ✅ Fix: Proper Optional typing
from typing import Optional

class Comment(models.Model):
    text: str = models.TextField()
    parent: Optional["Comment"] = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

def get_parent_text(comment: Comment) -> Optional[str]:
    if comment.parent is None:
        return None
    return comment.parent.text

# ✅ Alternative: Use getattr with default
def get_parent_text(comment: Comment) -> str:
    return getattr(comment.parent, 'text', 'No parent')
```

**Solution 3: Forward References (Circular Imports)**
```python
# ❌ Error with circular imports
# In models/article.py
from models.author import Author  # Circular import

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: Author = models.ForeignKey(Author, on_delete=models.CASCADE)

# ✅ Fix: Use string references
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.author import Author

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: "Author" = models.ForeignKey("models.Author", on_delete=models.CASCADE)

# ✅ Alternative: Use annotations future import
from __future__ import annotations
from models.author import Author

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: Author = models.ForeignKey("models.Author", on_delete=models.CASCADE)
```

**Solution 4: ManyToManyField**
```python
# ❌ Error with M2M
class Article(models.Model):
    title: str = models.CharField(max_length=200)
    tags: list["Tag"] = models.ManyToManyField("Tag")  # Wrong type

# ✅ Fix: Use Manager for M2M
from django.db.models import ManyToManyField, Manager

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    tags: Manager["Tag"] = ManyToManyField("Tag")

def get_tag_names(article: Article) -> list[str]:
    return list(article.tags.values_list('name', flat=True))

# ✅ With proper QuerySet typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    tags: Manager["Tag"] = ManyToManyField("Tag")

    def get_tags_queryset(self) -> "QuerySet[Tag]":
        return self.tags.all()
```

**Solution 5: Related Objects with select_related/prefetch_related**
```python
# ❌ Error with related queries
def get_articles_with_authors():
    # Type of articles unclear
    articles = Article.objects.select_related('author').all()
    for article in articles:
        # error: Item "None" has no attribute "username"
        print(article.author.username)

# ✅ Fix: Type hints show select_related guarantees author exists
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet

def get_articles_with_authors() -> "QuerySet[Article]":
    return Article.objects.select_related('author').all()

def process_articles():
    articles = get_articles_with_authors()
    for article in articles:
        # Still need to handle None if FK is nullable
        if article.author is not None:
            print(article.author.username)

# ✅ Better: Use non-nullable FK if always required
class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: "User" = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE
        # No null=True, so author is always present
    )

def process_articles():
    articles = Article.objects.select_related('author').all()
    for article in articles:
        print(article.author.username)  # Safe, never None
```

**When to use each solution:**
- **Solution 1**: For ID vs object assignment
- **Solution 2**: For nullable foreign keys
- **Solution 3**: For avoiding circular imports
- **Solution 4**: For many-to-many relationships
- **Solution 5**: For optimized queries with relations

---

## Missing Stubs and Import Errors

### Error: `import` - Cannot Find Implementation or Library Stubs

**Error Message:**
```
error: Cannot find implementation or library stub for module named "module_name"  [import]
error: Library stubs not installed for "package_name"  [import]
error: Skipping analyzing "module": module is installed, but missing library stubs  [import]
```

**What it means:**
The imported package doesn't have type stubs, so mypy cannot type-check code using it.

**Solution 1: Install Type Stubs**
```python
# ❌ Error
import yaml  # error: Library stubs not installed for "yaml"
import requests  # error: Library stubs not installed for "requests"

# ✅ Fix: Install stubs
# pip install types-PyYAML types-requests

# Then imports work
import yaml
import requests

config = yaml.safe_load(open('config.yml'))
response = requests.get('https://api.example.com')
```

**Common Django-related stub packages:**
```bash
# Core Django
pip install django-stubs

# Django REST Framework
pip install djangorestframework-stubs

# Common third-party packages
pip install types-PyYAML          # yaml
pip install types-requests         # requests
pip install types-redis            # redis
pip install types-python-dateutil  # dateutil
pip install types-pytz             # pytz
pip install types-pillow           # PIL
pip install types-setuptools       # setuptools
pip install types-stripe           # stripe
pip install types-boto3            # boto3
```

**Solution 2: Create Local Stubs**
```python
# ❌ Error with package that has no stubs
from some_package import SomeClass  # error: Cannot find implementation

# ✅ Fix: Create stub file
# Create: stubs/some_package/__init__.pyi
"""
from typing import Any

class SomeClass:
    def __init__(self, config: dict[str, Any]) -> None: ...
    def process(self, data: str) -> dict[str, Any]: ...
"""

# Configure mypy.ini
"""
[mypy]
mypy_path = $MYPY_CONFIG_FILE_DIR/stubs
"""

# Now import works with types
from some_package import SomeClass

obj = SomeClass({'key': 'value'})
result = obj.process('data')
```

**Solution 3: Use type: ignore for Missing Stubs**
```python
# ❌ Error
from obscure_package import utility  # error: Cannot find implementation

# ✅ Fix: Add type: ignore[import]
from obscure_package import utility  # type: ignore[import]

# ✅ Better: Add to mypy.ini for whole module
"""
[mypy-obscure_package.*]
ignore_missing_imports = True
"""

# Now no error for any obscure_package imports
from obscure_package import utility, helpers, tools
```

**Solution 4: Third-Party Django Packages Without Stubs**
```python
# Common packages that may lack stubs:

# django-extensions
# ❌ Error
from django_extensions.db.models import TimeStampedModel  # error: Cannot find stub

# ✅ Fix in mypy.ini
"""
[mypy-django_extensions.*]
ignore_missing_imports = True
"""

# django-storages
"""
[mypy-storages.*]
ignore_missing_imports = True
"""

# django-celery-beat
"""
[mypy-django_celery_beat.*]
ignore_missing_imports = True
"""

# django-filter
"""
[mypy-django_filters.*]
ignore_missing_imports = True
"""

# corsheaders
"""
[mypy-corsheaders.*]
ignore_missing_imports = True
"""
```

**Solution 5: Creating Minimal Stubs for Django Packages**
```python
# For packages you use heavily, create minimal stubs
# Example: stubs/django_extensions/db/models.pyi

from typing import Any
from django.db import models

class TimeStampedModel(models.Model):
    created: models.DateTimeField
    modified: models.DateTimeField

    class Meta:
        abstract = True

class ActivatorModel(models.Model):
    activate_date: models.DateTimeField
    deactivate_date: models.DateTimeField

    class Meta:
        abstract = True
```

**When to use each solution:**
- **Solution 1**: When official stubs exist (check pypi.org)
- **Solution 2**: For critical packages you use extensively
- **Solution 3**: For rarely-used packages
- **Solution 4**: For Django ecosystem packages
- **Solution 5**: For packages you control or need partial typing

---

## Type Ignore Comments

### Proper Use of type: ignore

**When to Use type: ignore:**

Type: ignore comments should be a last resort. Use them when:
1. You've verified the code is correct but mypy can't understand it
2. Working with dynamic Django features that can't be typed
3. Dealing with third-party code without stubs
4. A temporary workaround while fixing types

**Solution 1: Specific Error Codes (Always Preferred)**
```python
# ❌ Too broad
from obscure_package import utility  # type: ignore

# ✅ Specific error code
from obscure_package import utility  # type: ignore[import]

# ❌ Multiple issues, broad ignore
def process_data(data):  # type: ignore
    return data.value

# ✅ Specific ignores
def process_data(data):  # type: ignore[no-untyped-def]
    return data.value  # type: ignore[attr-defined]
```

**Common Error Codes for type: ignore:**
```python
# Import errors
import no_stubs_pkg  # type: ignore[import]

# Attribute not found
obj.dynamic_attr  # type: ignore[attr-defined]

# Union attribute access
maybe_none.value  # type: ignore[union-attr]

# Argument type mismatch
func(wrong_type)  # type: ignore[arg-type]

# Assignment mismatch
x: int = "string"  # type: ignore[assignment]

# Missing type annotations
def untyped():  # type: ignore[no-untyped-def]
    pass

# Calling untyped functions
untyped_func()  # type: ignore[no-untyped-call]

# Wrong return type
return wrong_type  # type: ignore[return-value]

# Override signature mismatch
def method(self):  # type: ignore[override]
    pass

# Misc errors
anything_else  # type: ignore[misc]
```

**Solution 2: Django-Specific Patterns Requiring type: ignore**
```python
# ❌ Django Meta class
class Article(models.Model):
    title: str = models.CharField(max_length=200)

    class Meta:  # error: Name "Meta" already defined
        db_table = 'articles'

# ✅ Fix: Usually handled by django-stubs, but if not:
class Article(models.Model):
    title: str = models.CharField(max_length=200)

    class Meta:  # type: ignore[misc]
        db_table = 'articles'

# ✅ Better: Update django-stubs
# pip install --upgrade django-stubs

# Django settings access
from django.conf import settings

# ❌ Error
value = settings.CUSTOM_SETTING  # error: "Settings" has no attribute "CUSTOM_SETTING"

# ✅ Fix: Type the settings
# In settings.py or settings.pyi
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    CUSTOM_SETTING: str

# Or use getattr
value = getattr(settings, 'CUSTOM_SETTING', 'default')

# Or type: ignore
value = settings.CUSTOM_SETTING  # type: ignore[attr-defined]
```

**Solution 3: Whole-Line vs Inline Comments**
```python
# Whole-line comment (applies to entire line)
result = complex_function()  # type: ignore[return-value]

# Multiple error codes
data = process()  # type: ignore[return-value, arg-type]

# Entire function
def legacy_function():  # type: ignore[no-untyped-def]
    complex_dynamic_code()
    return result

# Multiple lines - not recommended, fix the types instead
# type: ignore on line 1
# type: ignore on line 2
# Better: Fix the typing!
```

**Solution 4: Documenting Why type: ignore is Used**
```python
# ❌ No explanation
user = get_user()  # type: ignore

# ✅ With explanation
# Django's authentication returns AnonymousUser or User
# but we've verified user is authenticated in decorator
user = get_user()  # type: ignore[return-value]  # Guaranteed by @login_required

# ✅ TODO comment for future fix
# TODO: Add proper stub for this package
from legacy_package import tool  # type: ignore[import]

# ✅ Link to issue
# See: https://github.com/package/issues/123
result = dynamic_function()  # type: ignore[misc]
```

**Solution 5: Avoiding type: ignore Overuse**
```python
# ❌ Too many ignores - fix the types!
class BadView(View):
    def get(self, request):  # type: ignore
        user = request.user  # type: ignore
        if user.is_authenticated:  # type: ignore
            data = user.profile.data  # type: ignore
            return JsonResponse(data)  # type: ignore

# ✅ Properly typed
from typing import Any
from django.http import HttpRequest, JsonResponse
from django.views import View

class GoodView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        user = request.user
        if user.is_authenticated:
            data: dict[str, Any] = user.profile.data
            return JsonResponse(data)
```

**Type: ignore Guidelines:**
1. Always use specific error codes
2. Add explanatory comments
3. Keep a list of all type: ignores to review later
4. Prefer fixing types over using ignore
5. Use sparingly - many ignores indicate design issues

---

## Third-Party Package Issues

### Error: Working with Untyped Django Packages

**Common Django packages without complete stubs:**

**Solution 1: django-debug-toolbar**
```python
# ❌ Error
import debug_toolbar  # error: Cannot find implementation

# ✅ Fix in mypy.ini
"""
[mypy-debug_toolbar.*]
ignore_missing_imports = True
"""

# Or create minimal stub: stubs/debug_toolbar/__init__.pyi
"""
from typing import Any
from django.urls import URLPattern

urlpatterns: list[URLPattern]
"""
```

**Solution 2: celery and django-celery-beat**
```python
# ❌ Error
from celery import shared_task  # error: Cannot find implementation

# ✅ Fix: Install celery types
# pip install types-celery

# For django-celery-beat (no stubs available)
"""
[mypy-django_celery_beat.*]
ignore_missing_imports = True
"""

# Type the tasks properly
from typing import Any
from celery import shared_task

@shared_task
def process_data(data_id: int) -> dict[str, Any]:
    # Task implementation
    return {'status': 'completed'}
```

**Solution 3: django-filter**
```python
# ❌ Error
import django_filters  # error: Cannot find implementation

# ✅ Fix in mypy.ini
"""
[mypy-django_filters.*]
ignore_missing_imports = True
"""

# Create minimal stub if needed: stubs/django_filters/__init__.pyi
"""
from typing import Any, Type
from django.db import models

class FilterSet:
    def __init__(self, data: Any = None, queryset: Any = None) -> None: ...

    class Meta:
        model: Type[models.Model]
        fields: list[str] | dict[str, list[str]]

class CharFilter:
    def __init__(self, **kwargs: Any) -> None: ...
"""

# Usage with types
from django_filters import FilterSet
from myapp.models import Article

class ArticleFilter(FilterSet):
    class Meta:
        model = Article
        fields = ['title', 'published']
```

**Solution 4: django-rest-framework (with partial stubs)**
```python
# Install DRF stubs
# pip install djangorestframework-stubs

# But some features still need type: ignore
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'content']

    # Custom method fields may need type: ignore
    custom_field = serializers.SerializerMethodField()

    def get_custom_field(self, obj: Article) -> str:
        return obj.title.upper()

# ViewSet actions
from rest_framework import viewsets

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):  # type: ignore[no-untyped-def]
        article = self.get_object()
        article.published = True
        article.save()
        return Response({'status': 'published'})
```

**Solution 5: django-environ and other config packages**
```python
# ❌ Error
import environ  # error: Cannot find implementation

# ✅ Fix: Create stub or ignore
"""
[mypy-environ.*]
ignore_missing_imports = True
"""

# Or create stub: stubs/environ/__init__.pyi
"""
from typing import Any, TypeVar, overload

T = TypeVar('T')

class Env:
    def __init__(self, **kwargs: Any) -> None: ...

    @overload
    def str(self, var: str) -> str: ...

    @overload
    def str(self, var: str, default: T) -> str | T: ...

    def int(self, var: str, default: int = ...) -> int: ...
    def bool(self, var: str, default: bool = ...) -> bool: ...
    def list(self, var: str, default: list[str] = ...) -> list[str]: ...
"""

# Usage
import environ

env = environ.Env()
DEBUG = env.bool('DEBUG', default=False)
DATABASE_URL = env.str('DATABASE_URL')
```

**Solution 6: Creating Comprehensive Package Stubs**
```python
# For heavily-used packages, create complete stubs
# Example: stubs/django_extensions/db/models.pyi

from typing import Any
from django.db import models
from datetime import datetime

class TimeStampedModel(models.Model):
    """TimeStampedModel with proper typing."""
    created: datetime
    modified: datetime

    class Meta:
        abstract = True

class ActivatorModel(models.Model):
    """ActivatorModel with proper typing."""
    activate_date: datetime
    deactivate_date: datetime
    status: int

    INACTIVE_STATUS: int
    ACTIVE_STATUS: int

    def activate(self) -> None: ...
    def deactivate(self) -> None: ...

    class Meta:
        abstract = True

class TitleSlugDescriptionModel(models.Model):
    """TitleSlugDescriptionModel with proper typing."""
    title: str
    slug: str
    description: str

    class Meta:
        abstract = True
```

**When to use each solution:**
- **Solution 1**: For packages with minimal usage
- **Solution 2**: When official types exist but are incomplete
- **Solution 3**: For medium-usage packages
- **Solution 4**: For critical packages with partial stubs
- **Solution 5**: For configuration/utility packages
- **Solution 6**: For core dependencies used throughout codebase

---

## Migration Typing Problems

### Error: Migration File Type Issues

**Error Message:**
```
error: Need type annotation for "operations"  [var-annotated]
error: Cannot determine type of "dependencies"  [var-annotated]
```

**What it means:**
Migration files have dynamic structures that mypy struggles to understand.

**Solution 1: Ignore All Migration Files (Recommended)**
```ini
# mypy.ini
[mypy-*.migrations.*]
ignore_errors = True

# This ignores all migration files
# Migrations are generated code and don't need type checking
```

**Solution 2: Specific Migration Annotations (If You Must Type Them)**
```python
# ❌ Error in migration
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [  # error: Need type annotation
        ('app', '0001_initial'),
    ]

    operations = [  # error: Need type annotation
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('title', models.CharField(max_length=200)),
            ],
        ),
    ]

# ✅ Fix: Add type annotations (usually not worth it)
from typing import List, Tuple
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies: List[Tuple[str, str]] = [
        ('app', '0001_initial'),
    ]

    operations: List[migrations.operations.base.Operation] = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('title', models.CharField(max_length=200)),
            ],
        ),
    ]

# ✅ Much better: Just ignore migrations in mypy.ini
```

**Solution 3: Data Migrations with Type Safety**
```python
# If you write complex data migrations with logic
# migrations/0005_update_article_slugs.py

from typing import Any
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.apps.registry import Apps

def update_slugs(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Update article slugs based on titles."""
    Article = apps.get_model('blog', 'Article')

    for article in Article.objects.all():
        # Type checking works here
        article.slug = article.title.lower().replace(' ', '-')
        article.save()

def reverse_update(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Reverse migration - no-op."""
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('blog', '0004_article_slug'),
    ]

    operations = [
        migrations.RunPython(update_slugs, reverse_update),
    ]
```

**Solution 4: Custom Migration Operations**
```python
# If you create custom migration operations
from typing import Any, Sequence
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

class CustomOperation(migrations.operations.base.Operation):
    """Custom migration operation with proper types."""

    reversible = True

    def __init__(self, name: str, value: Any) -> None:
        self.name = name
        self.value = value

    def state_forwards(self, app_label: str, state: StateApps) -> None:
        pass

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: StateApps,
        to_state: StateApps,
    ) -> None:
        # Implementation
        pass

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: StateApps,
        to_state: StateApps,
    ) -> None:
        # Reverse implementation
        pass
```

**Solution 5: Migration Testing**
```python
# tests/test_migrations.py - these SHOULD be type-checked
from typing import Any
from django.apps.registry import Apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase

class MigrationTestCase(TestCase):
    """Test migrations with proper typing."""

    migrate_from: str
    migrate_to: str

    def setUp(self) -> None:
        self.executor = MigrationExecutor(connection)
        self.executor.migrate([(self.app, self.migrate_from)])

        # Get old state
        old_apps = self.executor.loader.project_state(
            [(self.app, self.migrate_from)]
        ).apps
        self.setUpBeforeMigration(old_apps)

        # Run migration
        self.executor.migrate([(self.app, self.migrate_to)])
        self.apps = self.executor.loader.project_state(
            [(self.app, self.migrate_to)]
        ).apps

    def setUpBeforeMigration(self, apps: Apps) -> None:
        """Override to set up data before migration."""
        pass

class TestArticleSlugMigration(MigrationTestCase):
    app = 'blog'
    migrate_from = '0004_article_slug'
    migrate_to = '0005_update_article_slugs'

    def setUpBeforeMigration(self, apps: Apps) -> None:
        Article = apps.get_model('blog', 'Article')
        self.article = Article.objects.create(
            title='Test Article',
            slug=''
        )

    def test_slug_updated(self) -> None:
        Article = self.apps.get_model('blog', 'Article')
        article = Article.objects.get(pk=self.article.pk)
        self.assertEqual(article.slug, 'test-article')
```

**Best Practices for Migrations:**
1. Always ignore migration files in mypy.ini
2. Type-check data migration functions
3. Type-check migration tests
4. Don't annotate generated migration operations
5. Use typed helper functions for complex data migrations

---

## Settings Module Errors

### Error: Django Settings Type Issues

**Error Message:**
```
error: "Settings" has no attribute "CUSTOM_SETTING"  [attr-defined]
error: Module has no attribute "DEBUG"  [attr-defined]
error: Cannot determine type of "DATABASES"  [has-type]
```

**What it means:**
Django settings are highly dynamic and custom settings aren't known to type checkers.

**Solution 1: Create settings.pyi Stub File**
```python
# settings/__init__.py - your actual settings
from .base import *  # noqa
from .local import *  # noqa

# settings/__init__.pyi - type stub for your settings
"""
Type stub for project settings module.
"""
from typing import Any

# Django core settings
DEBUG: bool
SECRET_KEY: str
ALLOWED_HOSTS: list[str]
INSTALLED_APPS: list[str]
MIDDLEWARE: list[str]
ROOT_URLCONF: str
TEMPLATES: list[dict[str, Any]]
DATABASES: dict[str, dict[str, Any]]
LANGUAGE_CODE: str
TIME_ZONE: str
USE_I18N: bool
USE_TZ: bool
STATIC_URL: str
DEFAULT_AUTO_FIELD: str

# Custom settings
API_KEY: str
MAX_UPLOAD_SIZE: int
CACHE_TIMEOUT: int
CUSTOM_FEATURE_FLAG: bool
EXTERNAL_API_URL: str
```

**Solution 2: TypedDict for Settings Groups**
```python
# settings/types.py
from typing import TypedDict, Any

class DatabaseConfig(TypedDict):
    ENGINE: str
    NAME: str
    USER: str
    PASSWORD: str
    HOST: str
    PORT: str

class EmailConfig(TypedDict):
    BACKEND: str
    HOST: str
    PORT: int
    USE_TLS: bool
    HOST_USER: str
    HOST_PASSWORD: str

# settings/__init__.pyi
from .types import DatabaseConfig, EmailConfig

DATABASES: dict[str, DatabaseConfig]
EMAIL: EmailConfig

# Usage in code
from django.conf import settings
from typing import cast
from myproject.settings.types import DatabaseConfig

def get_db_name() -> str:
    default_db = cast(DatabaseConfig, settings.DATABASES['default'])
    return default_db['NAME']
```

**Solution 3: Settings Helper Functions**
```python
# settings/helpers.py
from typing import Any, TypeVar, overload
from django.conf import settings

T = TypeVar('T')

@overload
def get_setting(name: str) -> Any: ...

@overload
def get_setting(name: str, default: T) -> T: ...

def get_setting(name: str, default: Any = None) -> Any:
    """
    Get a setting with optional default.

    Type-safe way to access Django settings.
    """
    return getattr(settings, name, default)

# Usage
from settings.helpers import get_setting

# Type-safe access
API_KEY: str = get_setting('API_KEY', '')
MAX_SIZE: int = get_setting('MAX_UPLOAD_SIZE', 10485760)
FEATURE_ON: bool = get_setting('CUSTOM_FEATURE_FLAG', False)
```

**Solution 4: Environment-Specific Settings**
```python
# settings/base.py
from typing import Any

DEBUG: bool = False
SECRET_KEY: str = 'default-secret-key'
CUSTOM_API_KEY: str = ''

# settings/local.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type hints for local settings
    DEBUG: bool
    CUSTOM_API_KEY: str

DEBUG = True
CUSTOM_API_KEY = 'local-development-key'

# settings/__init__.pyi
# Combine all possible settings
DEBUG: bool
SECRET_KEY: str
CUSTOM_API_KEY: str
```

**Solution 5: Settings Class Pattern**
```python
# settings/config.py
from typing import Any
from django.conf import settings

class Config:
    """Type-safe settings accessor."""

    @property
    def debug(self) -> bool:
        return settings.DEBUG

    @property
    def api_key(self) -> str:
        return settings.API_KEY

    @property
    def max_upload_size(self) -> int:
        return settings.MAX_UPLOAD_SIZE

    @property
    def cache_timeout(self) -> int:
        return getattr(settings, 'CACHE_TIMEOUT', 300)

# Create singleton
config = Config()

# Usage throughout codebase
from settings.config import config

if config.debug:
    print(f"API Key: {config.api_key}")

max_size = config.max_upload_size
```

**Solution 6: Django-Environ with Types**
```python
# settings/base.py
from typing import Any
import environ

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ''),
    DATABASE_URL=(str, 'sqlite:///db.sqlite3'),
    API_KEY=(str, ''),
    MAX_UPLOAD_SIZE=(int, 10485760),
)

# Type annotations for settings
DEBUG: bool = env.bool('DEBUG')
SECRET_KEY: str = env.str('SECRET_KEY')
API_KEY: str = env.str('API_KEY')
MAX_UPLOAD_SIZE: int = env.int('MAX_UPLOAD_SIZE')

# Database with types
DATABASES: dict[str, dict[str, Any]] = {
    'default': env.db()
}
```

**When to use each solution:**
- **Solution 1**: For comprehensive project-wide settings typing
- **Solution 2**: For complex nested settings structures
- **Solution 3**: For dynamic settings access
- **Solution 4**: For multi-environment configurations
- **Solution 5**: For object-oriented settings access
- **Solution 6**: For environment-based configurations

---

## Dynamic Attribute Errors

### Error: Dynamically Created Attributes

**Error Message:**
```
error: "ClassName" has no attribute "dynamic_attr"  [attr-defined]
error: Cannot determine type of "dynamic_method"  [has-type]
```

**What it means:**
Attributes or methods created at runtime aren't visible to mypy's static analysis.

**Solution 1: Django Model Property Pattern**
```python
# ❌ Error with dynamic attribute
class User(models.Model):
    first_name: str = models.CharField(max_length=50)
    last_name: str = models.CharField(max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_name = f"{self.first_name} {self.last_name}"  # Dynamic

def greet(user: User) -> str:
    # error: "User" has no attribute "full_name"
    return f"Hello, {user.full_name}"

# ✅ Fix: Use @property
class User(models.Model):
    first_name: str = models.CharField(max_length=50)
    last_name: str = models.CharField(max_length=50)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

def greet(user: User) -> str:
    return f"Hello, {user.full_name}"  # Now type-safe
```

**Solution 2: Cached Properties and Annotations**
```python
# ❌ Error with cached calculation
from django.utils.functional import cached_property

class Article(models.Model):
    content: str = models.TextField()

    @cached_property
    def word_count(self):  # No return type
        return len(self.content.split())

def analyze(article: Article):
    # error: Cannot determine type of "word_count"
    count: int = article.word_count

# ✅ Fix: Add return type annotation
class Article(models.Model):
    content: str = models.TextField()

    @cached_property
    def word_count(self) -> int:
        return len(self.content.split())

def analyze(article: Article) -> int:
    count: int = article.word_count  # Type-safe
    return count
```

**Solution 3: __getattr__ and __setattr__**
```python
# ❌ Error with __getattr__
class DynamicModel(models.Model):
    data: str = models.JSONField(default=dict)

    def __getattr__(self, name: str):
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"No attribute {name}")

def use_dynamic(obj: DynamicModel):
    # error: "DynamicModel" has no attribute "custom_field"
    value = obj.custom_field

# ✅ Fix: Use explicit methods with types
from typing import Any

class DynamicModel(models.Model):
    data: dict[str, Any] = models.JSONField(default=dict)

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set_data(self, key: str, value: Any) -> None:
        self.data[key] = value

def use_dynamic(obj: DynamicModel) -> Any:
    value = obj.get_data('custom_field')  # Type-safe
    return value

# ✅ Alternative: Type stub with Protocol
from typing import Protocol, Any

class HasCustomField(Protocol):
    custom_field: Any

def use_dynamic(obj: HasCustomField) -> Any:
    return obj.custom_field
```

**Solution 4: Django Form Dynamic Fields**
```python
# ❌ Error with dynamic form fields
class DynamicForm(forms.Form):
    def __init__(self, *args, field_names: list[str], **kwargs):
        super().__init__(*args, **kwargs)
        for name in field_names:
            self.fields[name] = forms.CharField()

def process_form(form: DynamicForm):
    # error: "DynamicForm" has no attribute "dynamic_field"
    value = form.cleaned_data['dynamic_field']

# ✅ Fix: Type the fields dict
from typing import Any

class DynamicForm(forms.Form):
    def __init__(self, *args, field_names: list[str], **kwargs):
        super().__init__(*args, **kwargs)
        for name in field_names:
            self.fields[name] = forms.CharField()

    def get_field_value(self, field_name: str) -> Any:
        return self.cleaned_data.get(field_name)

def process_form(form: DynamicForm) -> Any:
    value = form.get_field_value('dynamic_field')
    return value
```

**Solution 5: Monkey-Patching Third-Party Classes**
```python
# ❌ Error when adding methods to Django classes
from django.contrib.auth.models import User

def add_methods():
    def get_display_name(self):
        return f"{self.first_name} {self.last_name}"

    User.get_display_name = get_display_name

add_methods()

def greet(user: User):
    # error: "User" has no attribute "get_display_name"
    return user.get_display_name()

# ✅ Fix 1: Use Protocol
from typing import Protocol

class HasDisplayName(Protocol):
    first_name: str
    last_name: str

    def get_display_name(self) -> str: ...

def greet(user: HasDisplayName) -> str:
    return user.get_display_name()

# ✅ Fix 2: Extend the class properly
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    def get_display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

def greet(user: CustomUser) -> str:
    return user.get_display_name()

# ✅ Fix 3: Create stub file
# stubs/django/contrib/auth/models.pyi
class User:
    # ... existing attributes
    def get_display_name(self) -> str: ...
```

**Solution 6: TYPE_CHECKING for Runtime-Only Attributes**
```python
from typing import TYPE_CHECKING

class Article(models.Model):
    title: str = models.CharField(max_length=200)

    # Declare runtime attributes for type checking
    if TYPE_CHECKING:
        cached_related_data: list[str]
        _processing_state: dict[str, Any]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_related_data: list[str] = []
        self._processing_state: dict[str, Any] = {}

def process_article(article: Article) -> None:
    article.cached_related_data.append('item')  # Now type-safe
    article._processing_state['status'] = 'processing'
```

**When to use each solution:**
- **Solution 1**: For computed properties
- **Solution 2**: For cached/expensive computations
- **Solution 3**: For truly dynamic attribute access
- **Solution 4**: For dynamic form fields
- **Solution 5**: For extending third-party classes
- **Solution 6**: For runtime-initialized attributes

---

## Circular Import Issues

### Error: Circular Imports with Type Annotations

**Error Message:**
```
error: Cannot find module named 'module'  [import]
error: Name 'ClassName' is not defined  [name-defined]
ImportError: cannot import name 'X' from 'module' (circular import)
```

**What it means:**
Two or more modules import each other, creating a dependency cycle.

**Solution 1: TYPE_CHECKING and Forward References**
```python
# ❌ Error: Circular import
# models/article.py
from models.author import Author  # Imports author

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: Author = models.ForeignKey(Author, on_delete=models.CASCADE)

# models/author.py
from models.article import Article  # Imports article - CIRCULAR!

class Author(models.Model):
    name: str = models.CharField(max_length=100)

    def get_articles(self) -> list[Article]:  # Uses Article
        return list(self.article_set.all())

# ✅ Fix: Use TYPE_CHECKING
# models/article.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.author import Author

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: "Author" = models.ForeignKey("models.Author", on_delete=models.CASCADE)

# models/author.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.article import Article

class Author(models.Model):
    name: str = models.CharField(max_length=100)

    def get_articles(self) -> list["Article"]:
        return list(self.article_set.all())
```

**Solution 2: from __future__ import annotations**
```python
# ✅ Fix: Use future annotations (Python 3.7+)
# models/article.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.author import Author

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    # No quotes needed with __future__ annotations
    author: Author = models.ForeignKey("models.Author", on_delete=models.CASCADE)

# models/author.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.article import Article

class Author(models.Model):
    name: str = models.CharField(max_length=100)

    def get_articles(self) -> list[Article]:  # No quotes needed
        return list(self.article_set.all())
```

**Solution 3: Restructure to Remove Circular Dependency**
```python
# ❌ Circular dependency
# models/order.py
from models.customer import Customer

class Order(models.Model):
    customer: Customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

# models/customer.py
from models.order import Order

class Customer(models.Model):
    name: str = models.CharField(max_length=100)

    def get_total_orders(self) -> int:
        from models.order import Order  # Import inside function - BAD
        return Order.objects.filter(customer=self).count()

# ✅ Fix: Use manager methods instead
# models/order.py
class Order(models.Model):
    customer: "Customer" = models.ForeignKey("Customer", on_delete=models.CASCADE)

# models/customer.py
class Customer(models.Model):
    name: str = models.CharField(max_length=100)

    # Use reverse relation - no import needed
    def get_total_orders(self) -> int:
        return self.order_set.count()
```

**Solution 4: Protocol for Interface Dependencies**
```python
# ❌ Circular import for interface
# services/email.py
from services.user import UserService

class EmailService:
    def send_welcome(self, user_service: UserService):
        user = user_service.get_current()
        # send email...

# services/user.py
from services.email import EmailService

class UserService:
    def register(self, email_service: EmailService):
        # register user
        email_service.send_welcome(self)

# ✅ Fix: Use Protocol
# services/email.py
from typing import Protocol, TYPE_CHECKING

class HasCurrentUser(Protocol):
    def get_current(self) -> User: ...

class EmailService:
    def send_welcome(self, user_service: HasCurrentUser):
        user = user_service.get_current()
        # send email...

# services/user.py
from typing import Protocol

class CanSendWelcome(Protocol):
    def send_welcome(self, user_service: "UserService") -> None: ...

class UserService:
    def register(self, email_service: CanSendWelcome):
        # register user
        email_service.send_welcome(self)
```

**Solution 5: Separate Types Module**
```python
# ✅ Create separate types module
# models/types.py
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from models.article import Article
    from models.author import Author

class ArticleProtocol(Protocol):
    id: int
    title: str
    author_id: int

class AuthorProtocol(Protocol):
    id: int
    name: str

# models/article.py
from typing import TYPE_CHECKING
from models.types import AuthorProtocol

if TYPE_CHECKING:
    from models.author import Author

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    author: "Author" = models.ForeignKey("Author", on_delete=models.CASCADE)

    def get_author_info(self) -> AuthorProtocol:
        return self.author

# models/author.py
from typing import TYPE_CHECKING
from models.types import ArticleProtocol

if TYPE_CHECKING:
    from models.article import Article

class Author(models.Model):
    name: str = models.CharField(max_length=100)

    def get_latest_article(self) -> ArticleProtocol:
        return self.article_set.latest('created_at')
```

**Solution 6: Lazy Imports in Functions**
```python
# ❌ Top-level import causes circular dependency
# views/article.py
from views.author import get_author_details

def get_article_with_author(article_id: int):
    # uses get_author_details

# views/author.py
from views.article import get_article_list

def get_author_details(author_id: int):
    # uses get_article_list

# ✅ Fix: Import inside function
# views/article.py
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from views.author import get_author_details as _get_author_details

def get_article_with_author(article_id: int) -> dict[str, Any]:
    from views.author import get_author_details  # Import at runtime
    # use get_author_details
    return {}

# views/author.py
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from views.article import get_article_list as _get_article_list

def get_author_details(author_id: int) -> dict[str, Any]:
    from views.article import get_article_list  # Import at runtime
    # use get_article_list
    return {}
```

**Best Practices for Avoiding Circular Imports:**
1. Use TYPE_CHECKING for type-only imports
2. Use string literals for forward references
3. Consider __future__ annotations for cleaner code
4. Restructure code to remove circular dependencies
5. Use Protocols for interface dependencies
6. Create separate types modules for shared types
7. Only use runtime imports in functions as last resort

**When to use each solution:**
- **Solution 1**: Standard approach for most cases
- **Solution 2**: For newer Python versions (3.7+)
- **Solution 3**: When refactoring is possible
- **Solution 4**: For dependency injection patterns
- **Solution 5**: For complex type hierarchies
- **Solution 6**: When other solutions don't work (last resort)

---

## Performance and Debug Issues

### Error: Mypy is Slow or Uses Too Much Memory

**Problem:**
Mypy takes too long to run or crashes with memory errors on large Django projects.

**Solution 1: Incremental Mode and Cache**
```ini
# mypy.ini
[mypy]
# Enable incremental mode (default in recent versions)
incremental = True

# Specify cache directory
cache_dir = .mypy_cache

# Use fine-grained incremental mode for faster re-checks
cache_fine_grained = True

# Skip checking for cache updates (faster but less safe)
skip_cache_mtime_checks = False
```

```bash
# Run mypy with cache
mypy .

# Clear cache if you have issues
rm -rf .mypy_cache
mypy .

# Check cache statistics
mypy --stats .
```

**Solution 2: Parallel Checking**
```bash
# Use all CPU cores
mypy --parallel .

# Limit number of parallel processes
mypy --parallel-processes 4 .
```

**Solution 3: Exclude Unnecessary Files**
```ini
# mypy.ini
[mypy]
# Exclude files and directories
exclude = (?x)(
    ^migrations/
    | ^tests/
    | ^node_modules/
    | ^venv/
    | ^\.venv/
    | ^build/
    | ^dist/
    | ^__pycache__/
  )

# Ignore specific paths
[mypy-*.migrations.*]
ignore_errors = True

[mypy-*.tests.*]
ignore_errors = True

# Don't follow imports for large third-party packages
[mypy-django.*]
follow_imports = skip
```

**Solution 4: Reduce Strictness Temporarily**
```ini
# mypy.ini - Less strict for faster checking
[mypy]
# Disable expensive checks
disallow_any_generics = False
disallow_any_unimported = False

# Skip checking imported modules
follow_imports = silent

# Don't check untyped definitions
check_untyped_defs = False

# Allow untyped calls
disallow_untyped_calls = False
```

**Solution 5: Check Specific Modules Only**
```bash
# Check only specific app
mypy myapp/

# Check multiple specific paths
mypy myapp/ another_app/ utils/

# Check only modified files (with git)
git diff --name-only | grep '\.py$' | xargs mypy

# Check only staged files
git diff --cached --name-only | grep '\.py$' | xargs mypy
```

**Solution 6: Debug Mypy Performance**
```bash
# Show timing information
mypy --verbose .

# Show very detailed debug output
mypy --verbose --verbose .

# Show type checking stats
mypy --stats .

# Profile mypy performance
python -m cProfile -o mypy.prof $(which mypy) .
python -c "import pstats; p = pstats.Stats('mypy.prof'); p.sort_stats('cumtime'); p.print_stats(20)"

# Memory profiling
python -m memory_profiler $(which mypy) .
```

**Solution 7: Optimize Large Unions and Overloads**
```python
# ❌ Slow: Large Union types
from typing import Union

def process(
    value: Union[str, int, float, bool, list, dict, tuple, set, None]
) -> str:
    return str(value)

# ✅ Faster: Use Any or Protocol
from typing import Any, Protocol

class Stringable(Protocol):
    def __str__(self) -> str: ...

def process(value: Stringable) -> str:
    return str(value)

# ❌ Slow: Many overloads
from typing import overload

@overload
def get(key: str) -> str: ...
@overload
def get(key: str, default: int) -> int: ...
@overload
def get(key: str, default: str) -> str: ...
# ... 10 more overloads

# ✅ Faster: Use TypeVar
from typing import TypeVar

T = TypeVar('T')

def get(key: str, default: T | None = None) -> T | str | None:
    ...
```

**Solution 8: Split Large Files**
```python
# ❌ Slow: One huge models.py file
# models.py (5000 lines)
class Model1(models.Model): ...
class Model2(models.Model): ...
# ... 50 more models

# ✅ Faster: Split into multiple files
# models/
#   __init__.py
#   article.py
#   author.py
#   comment.py
#   tag.py

# models/__init__.py
from .article import Article
from .author import Author
from .comment import Comment
from .tag import Tag

__all__ = ['Article', 'Author', 'Comment', 'Tag']
```

**Solution 9: Configuration for Large Projects**
```ini
# mypy.ini - Optimized for large Django projects
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Performance optimizations
incremental = True
cache_dir = .mypy_cache
cache_fine_grained = True
skip_version_check = True
warn_unused_configs = True

# Reduce memory usage
follow_imports = normal
ignore_missing_imports = False

# Parallel processing
# (set via CLI: mypy --parallel .)

# Exclude large directories
exclude = (?x)(
    ^migrations/
    | ^tests/
    | ^venv/
    | ^staticfiles/
    | ^media/
  )

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings

# Ignore errors in migrations and tests
[mypy-*.migrations.*]
ignore_errors = True

[mypy-*.tests.*]
ignore_errors = True

# Skip following imports for large third-party packages
[mypy-celery.*]
follow_imports = skip

[mypy-rest_framework.*]
follow_imports = skip
```

**Solution 10: CI/CD Optimizations**
```yaml
# .github/workflows/mypy.yml
name: Type Check

on: [push, pull_request]

jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Cache mypy
        uses: actions/cache@v3
        with:
          path: .mypy_cache
          key: mypy-${{ hashFiles('requirements.txt') }}-${{ hashFiles('mypy.ini') }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install mypy django-stubs

      - name: Run mypy (parallel)
        run: mypy --parallel .
```

**Performance Benchmarks:**
```bash
# Benchmark different configurations
echo "Full strict check:"
time mypy .

echo -e "\nWith cache:"
time mypy .  # Run twice to use cache

echo -e "\nParallel:"
time mypy --parallel .

echo -e "\nSkip tests:"
time mypy --exclude 'tests' .

echo -e "\nSpecific modules only:"
time mypy myapp/ core/
```

**When to use each solution:**
- **Solution 1**: Always enable incremental mode
- **Solution 2**: For multi-core systems
- **Solution 3**: To exclude unnecessary files
- **Solution 4**: When speed matters more than strictness
- **Solution 5**: For quick checks during development
- **Solution 6**: When diagnosing performance issues
- **Solution 7**: When specific types are slow
- **Solution 8**: For better code organization
- **Solution 9**: As standard config for large projects
- **Solution 10**: For efficient CI/CD pipelines

---

## Generic and Protocol Errors

### Error: Generic Type Issues

**Error Message:**
```
error: Missing type parameters for generic type "Generic"  [type-arg]
error: Value of type variable "T" cannot be "object"  [type-var]
error: Type argument "X" of "Generic" must be a subtype of "Y"  [type-var]
```

**What it means:**
Issues with generic types, type parameters, or protocol definitions.

**Solution 1: Django Model Generic QuerySet**
```python
# ❌ Error: Missing type parameter
from django.db import models

class ArticleQuerySet(models.QuerySet):  # error: Missing type parameters
    def published(self):
        return self.filter(published=True)

# ✅ Fix: Add type parameter
from typing import TYPE_CHECKING

class ArticleQuerySet(models.QuerySet["Article"]):
    def published(self) -> "ArticleQuerySet":
        return self.filter(published=True)

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    published: bool = models.BooleanField(default=False)
```

**Solution 2: Generic Manager Pattern**
```python
# ❌ Error: Generic manager without proper bounds
from typing import TypeVar, Generic
from django.db import models

T = TypeVar('T')

class BaseManager(models.Manager, Generic[T]):  # Too broad
    def active(self):
        return self.filter(is_active=True)

# ✅ Fix: Bound TypeVar to Model
from typing import TypeVar
from django.db.models import Model

T = TypeVar('T', bound=Model)

class BaseQuerySet(models.QuerySet[T]):
    def active(self) -> "BaseQuerySet[T]":
        return self.filter(is_active=True)

class BaseManager(models.Manager[T]):
    def get_queryset(self) -> BaseQuerySet[T]:
        return BaseQuerySet(self.model, using=self._db)

    def active(self) -> BaseQuerySet[T]:
        return self.get_queryset().active()

# Usage
class Article(models.Model):
    title: str = models.CharField(max_length=200)
    is_active: bool = models.BooleanField(default=True)

    objects: BaseManager["Article"] = BaseManager()

articles = Article.objects.active()  # Type: BaseQuerySet[Article]
```

**Solution 3: Protocol for Duck Typing**
```python
# ❌ Error: Not using Protocol correctly
from typing import Protocol

class Serializable(Protocol):  # error if used incorrectly
    def to_dict(self):  # Missing return type
        ...

# ✅ Fix: Proper Protocol definition
from typing import Protocol, Any

class Serializable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...

class JSONSerializable(Protocol):
    def to_json(self) -> str: ...

# Use in function signatures
def serialize_object(obj: Serializable) -> dict[str, Any]:
    return obj.to_dict()

# Django model example
class Article(models.Model):
    title: str = models.CharField(max_length=200)

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
        }

article = Article(title='Test')
data = serialize_object(article)  # Works! Article implements Serializable
```

**Solution 4: Generic Function with Constraints**
```python
# ❌ Error: Type variable used incorrectly
from typing import TypeVar

T = TypeVar('T')

def get_first(queryset: models.QuerySet) -> T:  # error: T not in arguments
    return queryset.first()

# ✅ Fix: Proper generic function
from typing import TypeVar
from django.db.models import Model, QuerySet

T = TypeVar('T', bound=Model)

def get_first(queryset: QuerySet[T]) -> T | None:
    return queryset.first()

# Usage
articles: QuerySet[Article] = Article.objects.all()
first_article: Article | None = get_first(articles)  # Properly typed
```

**Solution 5: Multiple Type Variables**
```python
# ❌ Error: Multiple unrelated type variables
from typing import TypeVar, Generic

T = TypeVar('T')
U = TypeVar('U')

class Pair(Generic[T, U]):
    def __init__(self, first: T, second: U):
        self.first = first
        self.second = second

    # error: Signature incompatible with supertype
    def get_first(self) -> T:
        return self.first

# ✅ Fix: Properly implement generic class
from typing import TypeVar, Generic

T = TypeVar('T')
U = TypeVar('U')

class Pair(Generic[T, U]):
    first: T
    second: U

    def __init__(self, first: T, second: U) -> None:
        self.first = first
        self.second = second

    def get_first(self) -> T:
        return self.first

    def get_second(self) -> U:
        return self.second

    def swap(self) -> "Pair[U, T]":
        return Pair(self.second, self.first)

# Usage with Django
article = Article.objects.first()
user = User.objects.first()

pair: Pair[Article, User] = Pair(article, user)
swapped: Pair[User, Article] = pair.swap()
```

**Solution 6: Self Type (Python 3.11+)**
```python
# ❌ Error: Return type doesn't match for subclasses
from typing import TypeVar
from django.db import models

T = TypeVar('T', bound='BaseModel')

class BaseModel(models.Model):
    def refresh(self: T) -> T:  # Works but verbose
        self.refresh_from_db()
        return self

# ✅ Fix: Use Self type (Python 3.11+)
from typing import Self
from django.db import models

class BaseModel(models.Model):
    class Meta:
        abstract = True

    def refresh(self) -> Self:
        self.refresh_from_db()
        return self

    def save_and_return(self, *args, **kwargs) -> Self:
        self.save(*args, **kwargs)
        return self

class Article(BaseModel):
    title: str = models.CharField(max_length=200)

# Now properly typed
article = Article(title='Test')
same_article: Article = article.refresh()  # Type is Article, not BaseModel
```

**Solution 7: Generic Django Form**
```python
# ❌ Error: Generic form without proper types
from typing import TypeVar, Generic
from django import forms
from django.db.models import Model

T = TypeVar('T', bound=Model)

class BaseModelForm(forms.ModelForm, Generic[T]):  # error
    pass

# ✅ Fix: Use Protocol instead
from typing import Protocol, Any, TypeVar
from django.db.models import Model

class FormProtocol(Protocol):
    def save(self, commit: bool = True) -> Model: ...
    def is_valid(self) -> bool: ...

# Or just type individual forms
from typing import TYPE_CHECKING

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content']

    if TYPE_CHECKING:
        instance: Article

    def save(self, commit: bool = True) -> Article:
        return super().save(commit)

# Usage
form = ArticleForm(data={'title': 'Test', 'content': 'Content'})
if form.is_valid():
    article: Article = form.save()  # Properly typed as Article
```

**When to use each solution:**
- **Solution 1**: For QuerySet typing
- **Solution 2**: For reusable generic managers
- **Solution 3**: For structural subtyping
- **Solution 4**: For generic helper functions
- **Solution 5**: For complex generic classes
- **Solution 6**: For method chaining (Python 3.11+)
- **Solution 7**: For form typing

---

## Decorator and Metaclass Issues

### Error: Decorator Type Issues

**Error Message:**
```
error: Untyped decorator makes function "func_name" untyped  [misc]
error: "Callable[[...], Any]" has no attribute "attr"  [attr-defined]
```

**What it means:**
Decorators without proper type hints break type inference for decorated functions.

**Solution 1: Django View Decorators**
```python
# ❌ Error: Untyped decorator
from django.views.decorators.http import require_POST

@require_POST  # error: Untyped decorator
def my_view(request):
    return HttpResponse('OK')

# ✅ Fix: django-stubs provides types for Django decorators
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST

@require_POST
def my_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse('OK')

# For custom decorators
from typing import Callable, TypeVar, ParamSpec, Concatenate
from django.http import HttpRequest, HttpResponse

P = ParamSpec('P')
R = TypeVar('R')

def my_decorator(
    func: Callable[Concatenate[HttpRequest, P], R]
) -> Callable[Concatenate[HttpRequest, P], R]:
    def wrapper(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> R:
        # Decorator logic
        return func(request, *args, **kwargs)
    return wrapper

@my_decorator
def decorated_view(request: HttpRequest, slug: str) -> HttpResponse:
    return HttpResponse(f'OK: {slug}')
```

**Solution 2: login_required and Permission Decorators**
```python
# ❌ Error: Type lost after decoration
from django.contrib.auth.decorators import login_required

@login_required
def profile_view(request):  # Type unclear
    return HttpResponse(f'User: {request.user.username}')

# ✅ Fix: Proper typing
from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    # request.user guaranteed to be authenticated
    return HttpResponse(f'User: {request.user.username}')

# For custom auth decorators
from typing import Callable, TypeVar
from functools import wraps

F = TypeVar('F', bound=Callable)

def require_staff(view_func: F) -> F:
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
    return wrapper  # type: ignore[return-value]  # functools.wraps limitation

@require_staff
def admin_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse('Admin only')
```

**Solution 3: Class-Based View Decorators**
```python
# ❌ Error: Decorating class methods
from django.utils.decorators import method_decorator
from django.views import View

class ArticleView(View):
    @method_decorator(login_required)  # Type unclear
    def get(self, request):
        return HttpResponse('OK')

# ✅ Fix: Proper method typing
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View

class ArticleView(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse('OK')

# Alternative: Decorate entire class
@method_decorator(login_required, name='dispatch')
class ArticleView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse('OK')
```

**Solution 4: Custom Decorators with Arguments**
```python
# ❌ Error: Decorator factory without types
def permission_required(perm):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                return HttpResponseForbidden()
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# ✅ Fix: Properly typed decorator factory
from typing import Callable, TypeVar, ParamSpec
from functools import wraps
from django.http import HttpRequest, HttpResponse

P = ParamSpec('P')
R = TypeVar('R')

def permission_required(
    perm: str
) -> Callable[
    [Callable[Concatenate[HttpRequest, P], R]],
    Callable[Concatenate[HttpRequest, P], R]
]:
    def decorator(
        func: Callable[Concatenate[HttpRequest, P], R]
    ) -> Callable[Concatenate[HttpRequest, P], R]:
        @wraps(func)
        def wrapper(
            request: HttpRequest,
            *args: P.args,
            **kwargs: P.kwargs
        ) -> R:
            if not request.user.has_perm(perm):
                return HttpResponseForbidden()  # type: ignore[return-value]
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

@permission_required('articles.add_article')
def create_article(request: HttpRequest) -> HttpResponse:
    return HttpResponse('Created')
```

**Solution 5: Cached Property and Other Descriptors**
```python
# ❌ Error: cached_property type issues
from django.utils.functional import cached_property

class Article(models.Model):
    content: str = models.TextField()

    @cached_property
    def word_count(self):  # Type unclear
        return len(self.content.split())

# ✅ Fix: Add return type
from django.utils.functional import cached_property

class Article(models.Model):
    content: str = models.TextField()

    @cached_property
    def word_count(self) -> int:
        return len(self.content.split())

    @cached_property
    def summary(self) -> str:
        return self.content[:100]

# For custom descriptors
from typing import TypeVar, Generic, overload

T = TypeVar('T')

class LazyProperty(Generic[T]):
    def __init__(self, func: Callable[[Any], T]) -> None:
        self.func = func

    @overload
    def __get__(self, obj: None, objtype: type) -> "LazyProperty[T]": ...

    @overload
    def __get__(self, obj: object, objtype: type) -> T: ...

    def __get__(self, obj: object | None, objtype: type) -> "LazyProperty[T] | T":
        if obj is None:
            return self
        value = self.func(obj)
        setattr(obj, self.func.__name__, value)
        return value
```

**Solution 6: Django Model Metaclass**
```python
# ❌ Error: Custom model metaclass
from django.db.models.base import ModelBase

class CustomMeta(ModelBase):
    def __new__(cls, name, bases, attrs):  # Untyped
        return super().__new__(cls, name, bases, attrs)

# ✅ Fix: Type the metaclass
from typing import Any
from django.db.models.base import ModelBase

class CustomMeta(ModelBase):
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        attrs: dict[str, Any],
        **kwargs: Any
    ) -> "CustomMeta":
        new_class = super().__new__(mcs, name, bases, attrs, **kwargs)
        # Custom logic
        return new_class

class BaseModel(models.Model, metaclass=CustomMeta):
    class Meta:
        abstract = True
```

**When to use each solution:**
- **Solution 1**: For basic view decorators
- **Solution 2**: For authentication decorators
- **Solution 3**: For class-based views
- **Solution 4**: For complex decorator factories
- **Solution 5**: For property descriptors
- **Solution 6**: For metaclass customization

---

## Summary and Quick Reference

### Most Common Fixes

1. **Import django-stubs**: `pip install django-stubs`
2. **Configure mypy.ini**: Add `plugins = mypy_django_plugin.main`
3. **Ignore migrations**: `[mypy-*.migrations.*] ignore_errors = True`
4. **Use TYPE_CHECKING**: For circular imports
5. **Add return types**: To all functions
6. **Type Manager**: `objects: ClassVar[Manager["Model"]] = Manager()`
7. **Optional FK**: Use `Optional["Model"]` for null=True
8. **Use _id suffix**: For FK ID assignment

### Quick Diagnostic Steps

1. Check django-stubs is installed and up to date
2. Verify mypy.ini has Django plugin configured
3. Clear mypy cache: `rm -rf .mypy_cache`
4. Run with verbose: `mypy --verbose .`
5. Check specific file: `mypy path/to/file.py`
6. Use error code to find solution in this doc

### Performance Checklist

- [ ] Incremental mode enabled
- [ ] Migrations ignored
- [ ] Tests ignored or less strict
- [ ] Using parallel checking
- [ ] Cache directory configured
- [ ] Unnecessary files excluded
- [ ] Large files split up
- [ ] Using specific modules when possible

### Type Safety Levels

**Level 1 - Minimal (Quick Start)**
```ini
[mypy]
plugins = mypy_django_plugin.main
[mypy-*.migrations.*]
ignore_errors = True
```

**Level 2 - Moderate (Recommended)**
```ini
[mypy]
plugins = mypy_django_plugin.main
warn_unused_ignores = True
no_implicit_optional = True
strict_optional = True
[mypy-*.migrations.*]
ignore_errors = True
```

**Level 3 - Strict (Full Type Safety)**
```ini
[mypy]
plugins = mypy_django_plugin.main
strict = True
warn_unused_ignores = True
warn_redundant_casts = True
disallow_untyped_defs = True
disallow_untyped_calls = True
```

---

## Index by Error Code

- `assignment`: [Variable and Assignment Errors](#variable-and-assignment-errors)
- `arg-type`: [Attribute and Method Errors](#attribute-and-method-errors)
- `attr-defined`: [Attribute and Method Errors](#attribute-and-method-errors)
- `call-arg`: [Attribute and Method Errors](#attribute-and-method-errors)
- `has-type`: [Settings Module Errors](#settings-module-errors)
- `import`: [Missing Stubs and Import Errors](#missing-stubs-and-import-errors)
- `misc`: [Decorator and Metaclass Issues](#decorator-and-metaclass-issues)
- `name-defined`: [Circular Import Issues](#circular-import-issues)
- `no-untyped-call`: [Type Ignore Comments](#type-ignore-comments)
- `no-untyped-def`: [Type Ignore Comments](#type-ignore-comments)
- `override`: [Decorator and Metaclass Issues](#decorator-and-metaclass-issues)
- `return-value`: [Variable and Assignment Errors](#variable-and-assignment-errors)
- `type-arg`: [Generic and Protocol Errors](#generic-and-protocol-errors)
- `type-var`: [Generic and Protocol Errors](#generic-and-protocol-errors)
- `union-attr`: [Variable and Assignment Errors](#variable-and-assignment-errors)
- `var-annotated`: [Variable and Assignment Errors](#variable-and-assignment-errors)

---

## Additional Resources

### Official Documentation
- [mypy documentation](https://mypy.readthedocs.io/)
- [django-stubs documentation](https://github.com/typeddjango/django-stubs)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)

### Companion Guides
- `django-typing-guide.md` - Complete typing patterns
- `mypy-django-configuration.md` - Configuration reference
- `drf-typing-patterns.md` - REST Framework typing

### Community
- [django-stubs GitHub Issues](https://github.com/typeddjango/django-stubs/issues)
- [mypy GitHub Issues](https://github.com/python/mypy/issues)
- [Python typing-sig](https://mail.python.org/archives/list/typing-sig@python.org/)

---

**End of Troubleshooting Guide**

This guide covers approximately 1,000+ lines of comprehensive troubleshooting information for mypy and Django integration. Each error type includes multiple solutions with real-world examples, explanations of when to use each approach, and best practices for maintaining type safety in Django projects.
