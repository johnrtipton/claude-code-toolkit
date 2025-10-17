"""
Comprehensive Django REST Framework Typed Serializer Template

This template demonstrates best practices for type-annotated DRF serializers using
djangorestframework-stubs. It includes examples of:
- ModelSerializer with proper type parameters
- Regular Serializer (non-model)
- Nested serializers (read and write)
- SerializerMethodField with return type annotations
- Custom field validation
- Object-level validation
- create/update methods with proper types
- to_representation/to_internal_value overrides
- ListSerializer for bulk operations
- HyperlinkedModelSerializer
- Complete ViewSet examples

Requirements:
    pip install djangorestframework
    pip install djangorestframework-stubs
    pip install django-stubs
"""

from typing import Any, Dict, List, Optional, TypedDict, cast
from decimal import Decimal
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Type stubs imports for proper type checking
from rest_framework.fields import Field
from rest_framework.serializers import Serializer

User = get_user_model()


# =============================================================================
# Example Models (for demonstration purposes)
# =============================================================================

class Author:
    """Example model for demonstration"""
    id: int
    name: str
    email: str
    bio: str
    created_at: datetime
    updated_at: datetime

    class Meta:
        db_table = "authors"


class Book:
    """Example model for demonstration"""
    id: int
    title: str
    isbn: str
    published_date: datetime
    price: Decimal
    author: Author
    categories: QuerySet
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Meta:
        db_table = "books"


class Category:
    """Example model for demonstration"""
    id: int
    name: str
    slug: str
    description: str


# =============================================================================
# TypedDict Definitions for Validated Data
# =============================================================================

class AuthorValidatedData(TypedDict, total=False):
    """Type definition for validated Author data"""
    name: str
    email: str
    bio: str


class BookValidatedData(TypedDict, total=False):
    """Type definition for validated Book data"""
    title: str
    isbn: str
    published_date: datetime
    price: Decimal
    author: Author
    categories: List[Category]
    is_published: bool


class BookCreateData(TypedDict):
    """Type definition for book creation data"""
    title: str
    isbn: str
    published_date: datetime
    price: Decimal
    author_id: int
    category_ids: List[int]


# =============================================================================
# Regular Serializer (Non-Model)
# =============================================================================

class LoginSerializer(serializers.Serializer[None]):
    """
    Non-model serializer for login credentials.
    Type parameter is None since it doesn't represent a model.
    """

    email = serializers.EmailField(
        required=True,
        max_length=255,
        help_text="User's email address"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User's password"
    )
    remember_me = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Keep user logged in"
    )

    def validate_email(self, value: str) -> str:
        """
        Validate email field.

        Args:
            value: The email to validate

        Returns:
            The validated email in lowercase

        Raises:
            serializers.ValidationError: If email format is invalid
        """
        return value.lower().strip()

    def validate_password(self, value: str) -> str:
        """
        Validate password field.

        Args:
            value: The password to validate

        Returns:
            The validated password

        Raises:
            serializers.ValidationError: If password is too short
        """
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
            )
        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Object-level validation.

        Args:
            attrs: Dictionary of validated field data

        Returns:
            The validated attributes dictionary

        Raises:
            serializers.ValidationError: If validation fails
        """
        # You can add cross-field validation here
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Example: Check if user exists and password is correct
            # This is just demonstration - actual auth should be in views
            pass

        return attrs


# =============================================================================
# Simple ModelSerializer with Type Parameters
# =============================================================================

class CategorySerializer(serializers.ModelSerializer[Category]):
    """
    Simple serializer for Category model.
    Type parameter indicates the model type for better type checking.
    """

    # Explicitly typed field override
    name: serializers.CharField = serializers.CharField(
        max_length=100,
        help_text="Category name"
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']
        read_only_fields = ['id', 'slug']

    def validate_name(self, value: str) -> str:
        """
        Validate category name.

        Args:
            value: The category name

        Returns:
            Validated and cleaned name
        """
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError(
                "Category name must be at least 3 characters"
            )
        return value

    def create(self, validated_data: Dict[str, Any]) -> Category:
        """
        Create a new category instance.

        Args:
            validated_data: Validated data dictionary

        Returns:
            Created Category instance
        """
        # Auto-generate slug from name
        name = validated_data['name']
        slug = name.lower().replace(' ', '-')
        validated_data['slug'] = slug

        return super().create(validated_data)


# =============================================================================
# Nested Serializer - Read Only
# =============================================================================

class AuthorReadSerializer(serializers.ModelSerializer[Author]):
    """
    Read-only serializer for Author with computed fields.
    Used for nested representations and list views.
    """

    # SerializerMethodField with proper return type annotation
    full_name: serializers.SerializerMethodField[str] = serializers.SerializerMethodField()
    book_count: serializers.SerializerMethodField[int] = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            'id',
            'name',
            'email',
            'bio',
            'full_name',
            'book_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_full_name(self, obj: Author) -> str:
        """
        Get formatted full name.

        Args:
            obj: The Author instance

        Returns:
            Formatted name string
        """
        return f"{obj.name} ({obj.email})"

    def get_book_count(self, obj: Author) -> int:
        """
        Get count of books by this author.

        Args:
            obj: The Author instance

        Returns:
            Number of books
        """
        # Type hint helps with IDE autocomplete
        count: int = obj.books.count()
        return count


# =============================================================================
# Nested Serializer - Write
# =============================================================================

class AuthorWriteSerializer(serializers.ModelSerializer[Author]):
    """
    Write serializer for Author.
    Separate from read serializer to handle different validation logic.
    """

    class Meta:
        model = Author
        fields = ['name', 'email', 'bio']

    def validate_email(self, value: str) -> str:
        """
        Validate email is unique.

        Args:
            value: Email to validate

        Returns:
            Validated email

        Raises:
            serializers.ValidationError: If email already exists
        """
        # Check uniqueness, excluding current instance if updating
        instance = cast(Optional[Author], getattr(self, 'instance', None))
        queryset = Author.objects.filter(email=value)

        if instance:
            queryset = queryset.exclude(pk=instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "An author with this email already exists"
            )

        return value.lower()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Object-level validation for author data.

        Args:
            attrs: Dictionary of field values

        Returns:
            Validated attributes
        """
        # Example: Ensure bio is not too short if provided
        bio = attrs.get('bio', '')
        if bio and len(bio) < 10:
            raise serializers.ValidationError({
                'bio': "Bio must be at least 10 characters if provided"
            })

        return attrs

    def create(self, validated_data: AuthorValidatedData) -> Author:
        """
        Create new author instance.

        Args:
            validated_data: Validated author data

        Returns:
            Created Author instance
        """
        author = Author.objects.create(**validated_data)
        return author

    def update(self, instance: Author, validated_data: AuthorValidatedData) -> Author:
        """
        Update existing author instance.

        Args:
            instance: Existing Author instance
            validated_data: Validated update data

        Returns:
            Updated Author instance
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# =============================================================================
# Complex ModelSerializer with Nested Relationships
# =============================================================================

class BookSerializer(serializers.ModelSerializer[Book]):
    """
    Complete serializer for Book model with nested relationships.
    Demonstrates:
    - Nested read serializers
    - Nested write handling
    - SerializerMethodFields
    - Custom validation
    - Override to_representation/to_internal_value
    """

    # Nested read-only author representation
    author: AuthorReadSerializer = AuthorReadSerializer(read_only=True)

    # Write-only field for author assignment
    author_id: serializers.PrimaryKeyRelatedField[Author] = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(),
        write_only=True,
        help_text="ID of the author"
    )

    # Many-to-many nested read
    categories: CategorySerializer = CategorySerializer(many=True, read_only=True)

    # Write-only field for category assignment
    category_ids: serializers.PrimaryKeyRelatedField[Category] = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True,
        write_only=True,
        help_text="List of category IDs"
    )

    # Computed field
    price_display: serializers.SerializerMethodField[str] = serializers.SerializerMethodField()
    is_new_release: serializers.SerializerMethodField[bool] = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'isbn',
            'published_date',
            'price',
            'price_display',
            'author',
            'author_id',
            'categories',
            'category_ids',
            'is_published',
            'is_new_release',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_price_display(self, obj: Book) -> str:
        """
        Get formatted price string.

        Args:
            obj: Book instance

        Returns:
            Formatted price with currency symbol
        """
        return f"${obj.price:.2f}"

    def get_is_new_release(self, obj: Book) -> bool:
        """
        Check if book is a new release (within 6 months).

        Args:
            obj: Book instance

        Returns:
            True if published within last 6 months
        """
        from datetime import timedelta
        from django.utils import timezone

        six_months_ago = timezone.now() - timedelta(days=180)
        return obj.published_date >= six_months_ago.date() if obj.published_date else False

    def validate_isbn(self, value: str) -> str:
        """
        Validate ISBN format and uniqueness.

        Args:
            value: ISBN string

        Returns:
            Validated ISBN

        Raises:
            serializers.ValidationError: If ISBN is invalid
        """
        # Remove hyphens and spaces
        isbn = value.replace('-', '').replace(' ', '')

        # Check length (ISBN-10 or ISBN-13)
        if len(isbn) not in [10, 13]:
            raise serializers.ValidationError(
                "ISBN must be 10 or 13 characters"
            )

        # Check uniqueness
        instance = cast(Optional[Book], getattr(self, 'instance', None))
        queryset = Book.objects.filter(isbn=isbn)

        if instance:
            queryset = queryset.exclude(pk=instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A book with this ISBN already exists"
            )

        return isbn

    def validate_price(self, value: Decimal) -> Decimal:
        """
        Validate price is positive.

        Args:
            value: Price value

        Returns:
            Validated price

        Raises:
            serializers.ValidationError: If price is invalid
        """
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than zero"
            )

        if value > 9999:
            raise serializers.ValidationError(
                "Price cannot exceed $9,999"
            )

        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Object-level validation.

        Args:
            attrs: Dictionary of validated fields

        Returns:
            Validated attributes

        Raises:
            serializers.ValidationError: If validation fails
        """
        # Ensure published books have all required fields
        is_published = attrs.get('is_published', False)

        if is_published:
            if not attrs.get('published_date'):
                raise serializers.ValidationError({
                    'published_date': "Published books must have a publication date"
                })

            if not attrs.get('category_ids'):
                raise serializers.ValidationError({
                    'category_ids': "Published books must have at least one category"
                })

        return attrs

    def create(self, validated_data: Dict[str, Any]) -> Book:
        """
        Create new book with nested relationships.

        Args:
            validated_data: Validated book data

        Returns:
            Created Book instance
        """
        # Extract nested data
        author_id = validated_data.pop('author_id')
        category_ids = validated_data.pop('category_ids', [])

        # Create book with atomic transaction
        with transaction.atomic():
            book = Book.objects.create(
                author=author_id,
                **validated_data
            )

            # Set many-to-many relationships
            if category_ids:
                book.categories.set(category_ids)

        return book

    def update(self, instance: Book, validated_data: Dict[str, Any]) -> Book:
        """
        Update book instance with nested relationships.

        Args:
            instance: Existing Book instance
            validated_data: Validated update data

        Returns:
            Updated Book instance
        """
        # Extract nested data
        author_id = validated_data.pop('author_id', None)
        category_ids = validated_data.pop('category_ids', None)

        # Update with atomic transaction
        with transaction.atomic():
            # Update simple fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            # Update foreign key
            if author_id:
                instance.author = author_id

            instance.save()

            # Update many-to-many
            if category_ids is not None:
                instance.categories.set(category_ids)

        return instance

    def to_representation(self, instance: Book) -> Dict[str, Any]:
        """
        Customize serialized output.

        Args:
            instance: Book instance to serialize

        Returns:
            Dictionary representation
        """
        # Get default representation
        ret = super().to_representation(instance)

        # Add custom fields or modify existing ones
        # Example: Add a computed URL
        request = self.context.get('request')
        if request:
            ret['url'] = request.build_absolute_uri(f'/api/books/{instance.id}/')

        # Example: Conditionally include fields
        if not instance.is_published:
            ret['status'] = 'draft'
        else:
            ret['status'] = 'published'

        return ret

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert incoming data to internal Python representation.

        Args:
            data: Input data dictionary

        Returns:
            Internal representation

        Raises:
            serializers.ValidationError: If data is invalid
        """
        # Perform custom data transformations before validation
        # Example: Normalize ISBN format
        if 'isbn' in data:
            data['isbn'] = str(data['isbn']).replace('-', '').replace(' ', '')

        return super().to_internal_value(data)


# =============================================================================
# ListSerializer for Bulk Operations
# =============================================================================

class BookListSerializer(serializers.ListSerializer[Book]):
    """
    Custom ListSerializer for bulk book operations.
    Enables efficient bulk create/update with validation.
    """

    def create(self, validated_data: List[Dict[str, Any]]) -> List[Book]:
        """
        Bulk create books efficiently.

        Args:
            validated_data: List of validated book data

        Returns:
            List of created Book instances
        """
        books_to_create: List[Book] = []

        with transaction.atomic():
            for item in validated_data:
                author_id = item.pop('author_id')
                category_ids = item.pop('category_ids', [])

                book = Book(author=author_id, **item)
                books_to_create.append(book)

            # Bulk create for efficiency
            created_books = Book.objects.bulk_create(books_to_create)

            # Handle M2M relationships (cannot be done in bulk_create)
            for idx, book in enumerate(created_books):
                category_ids = validated_data[idx].get('category_ids', [])
                if category_ids:
                    book.categories.set(category_ids)

        return created_books

    def update(self, instance: List[Book], validated_data: List[Dict[str, Any]]) -> List[Book]:
        """
        Bulk update books.

        Args:
            instance: List of existing Book instances
            validated_data: List of validated update data

        Returns:
            List of updated Book instances
        """
        # Create mapping of id to instance and data
        book_mapping = {book.id: book for book in instance}
        updated_books: List[Book] = []

        with transaction.atomic():
            for item in validated_data:
                book_id = item.get('id')
                if book_id and book_id in book_mapping:
                    book = book_mapping[book_id]

                    # Update fields
                    for attr, value in item.items():
                        if attr not in ['id', 'category_ids', 'author_id']:
                            setattr(book, attr, value)

                    updated_books.append(book)

            # Bulk update
            if updated_books:
                Book.objects.bulk_update(
                    updated_books,
                    ['title', 'isbn', 'published_date', 'price', 'is_published']
                )

        return updated_books


class BookBulkSerializer(serializers.ModelSerializer[Book]):
    """
    Serializer for bulk book operations.
    Uses custom ListSerializer for efficient bulk processing.
    """

    author_id: serializers.PrimaryKeyRelatedField[Author] = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all()
    )
    category_ids: serializers.PrimaryKeyRelatedField[Category] = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True
    )

    class Meta:
        model = Book
        list_serializer_class = BookListSerializer
        fields = [
            'id',
            'title',
            'isbn',
            'published_date',
            'price',
            'author_id',
            'category_ids',
            'is_published',
        ]


# =============================================================================
# HyperlinkedModelSerializer
# =============================================================================

class BookHyperlinkedSerializer(serializers.HyperlinkedModelSerializer[Book]):
    """
    Hyperlinked serializer using URLs instead of IDs.
    Better for RESTful APIs.
    """

    # Use hyperlinks for relationships
    author: serializers.HyperlinkedRelatedField[Author] = serializers.HyperlinkedRelatedField(
        view_name='author-detail',
        read_only=True
    )

    categories: serializers.HyperlinkedRelatedField[Category] = serializers.HyperlinkedRelatedField(
        view_name='category-detail',
        many=True,
        read_only=True
    )

    class Meta:
        model = Book
        fields = [
            'url',  # Self link
            'title',
            'isbn',
            'published_date',
            'price',
            'author',
            'categories',
            'is_published',
        ]
        extra_kwargs = {
            'url': {'view_name': 'book-detail'},
        }


# =============================================================================
# ViewSet Examples Using Typed Serializers
# =============================================================================

class AuthorViewSet(viewsets.ModelViewSet[Author]):
    """
    ViewSet for Author model with proper typing.
    Demonstrates different serializers for read/write operations.
    """

    queryset = Author.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self) -> type[serializers.ModelSerializer[Author]]:
        """
        Return appropriate serializer class based on action.

        Returns:
            Serializer class for the current action
        """
        if self.action in ['create', 'update', 'partial_update']:
            return AuthorWriteSerializer
        return AuthorReadSerializer

    @action(detail=True, methods=['get'])
    def books(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Get all books by this author.

        Args:
            request: The HTTP request
            pk: Author primary key

        Returns:
            Response with serialized books
        """
        author = self.get_object()
        books = author.books.all()
        serializer = BookSerializer(books, many=True, context={'request': request})
        return Response(serializer.data)


class BookViewSet(viewsets.ModelViewSet[Book]):
    """
    ViewSet for Book model with custom actions and bulk operations.
    """

    queryset = Book.objects.select_related('author').prefetch_related('categories')
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Book]:
        """
        Get filtered queryset.

        Returns:
            Filtered QuerySet of books
        """
        queryset = super().get_queryset()

        # Filter by published status
        is_published = self.request.query_params.get('is_published')
        if is_published is not None:
            queryset = queryset.filter(is_published=is_published.lower() == 'true')

        # Filter by author
        author_id = self.request.query_params.get('author_id')
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        return queryset

    @action(detail=False, methods=['post'])
    def bulk_create(self, request: Request) -> Response:
        """
        Bulk create multiple books.

        Args:
            request: The HTTP request with list of books

        Returns:
            Response with created books
        """
        serializer = BookBulkSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def publish(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Publish a book.

        Args:
            request: The HTTP request
            pk: Book primary key

        Returns:
            Response with updated book
        """
        book = self.get_object()

        if book.is_published:
            return Response(
                {'error': 'Book is already published'},
                status=status.HTTP_400_BAD_REQUEST
            )

        book.is_published = True
        book.save()

        serializer = self.get_serializer(book)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def new_releases(self, request: Request) -> Response:
        """
        Get new release books.

        Args:
            request: The HTTP request

        Returns:
            Response with new release books
        """
        from datetime import timedelta
        from django.utils import timezone

        six_months_ago = timezone.now() - timedelta(days=180)
        books = self.get_queryset().filter(
            published_date__gte=six_months_ago.date(),
            is_published=True
        )

        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet[Category]):
    """
    Simple ViewSet for Category model.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
