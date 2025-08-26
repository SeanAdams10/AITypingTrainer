"""Simple library service built on SQLAlchemy models.

Provides CRUD operations for categories and snippets with basic validation.
"""

from __future__ import annotations

from typing import List, Optional, Protocol, TypeVar

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Typed SQLAlchemy declarative base."""


metadata = Base.metadata


class ValidationError(Exception):
    """Raised for invalid input or business-rule violations."""

    pass


# Make ValidationError importable from this module
__all__ = ["LibraryService", "ValidationError", "Category", "Snippet"]


class Category(Base):
    """Category entity."""

    __tablename__ = "categories"
    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    snippets: Mapped[list["Snippet"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Snippet(Base):
    """Snippet entity."""

    __tablename__ = "snippets"
    snippet_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped["Category"] = relationship(back_populates="snippets")
    __table_args__ = (UniqueConstraint("category_id", "name", name="uix_category_snippet_name"),)


class LibraryService:
    """Service to manage Categories and Snippets."""

    metadata = metadata

    def __init__(self, session: "SessionLike") -> None:
        """Initialize with a SQLAlchemy session or compatible facade."""
        self.session = session

    # Category methods
    def add_category(self, name: str) -> Category:
        """Create and persist a category if valid and unique."""
        if not name or len(name) > 50 or not name.isascii():
            raise ValidationError("Invalid category name")
        if self.session.query(Category).filter_by(name=name).first():
            raise ValidationError("Duplicate category name")
        cat = Category(name=name)
        self.session.add(cat)
        return cat

    def get_categories(self) -> List[Category]:
        """Return all categories."""
        return self.session.query(Category).all()

    def edit_category(self, category_id: int, new_name: str) -> Category:
        """Rename a category if found and the new name is valid/unique."""
        if not new_name or len(new_name) > 50 or not new_name.isascii():
            raise ValidationError("Invalid category name")
        cat = self.session.query(Category).filter_by(category_id=category_id).first()
        if not cat:
            raise ValidationError("Category not found")
        if (
            self.session.query(Category)
            .filter(Category.name == new_name, Category.category_id != category_id)
            .first()
        ):
            raise ValidationError("Duplicate category name")
        cat.name = new_name
        return cat

    def delete_category(self, category_id: int) -> None:
        """Delete a category by id if it exists."""
        cat = self.session.query(Category).filter_by(category_id=category_id).first()
        if not cat:
            raise ValidationError("Category not found")
        self.session.delete(cat)

    # Snippet methods
    def add_snippet(self, category_id: int, name: str, content: str) -> Snippet:
        """Create and persist a snippet if valid and unique for the category."""
        if not name or len(name) > 50 or not name.isascii():
            raise ValidationError("Invalid snippet name")
        if not content or not content.isascii():
            raise ValidationError("Invalid snippet content")
        if self.session.query(Snippet).filter_by(category_id=category_id, name=name).first():
            raise ValidationError("Duplicate snippet name")
        snip = Snippet(category_id=category_id, name=name, content=content)
        self.session.add(snip)
        return snip

    def get_snippets(self, category_id: int) -> List[Snippet]:
        """List snippets for a category."""
        return self.session.query(Snippet).filter_by(category_id=category_id).all()

    def edit_snippet(
        self,
        snippet_id: int,
        new_name: str,
        new_content: str,
        new_category_id: Optional[int] = None,
    ) -> Snippet:
        """Edit snippet properties ensuring uniqueness and validity."""
        if not new_name or len(new_name) > 50 or not new_name.isascii():
            raise ValidationError("Invalid snippet name")
        if not new_content or not new_content.isascii():
            raise ValidationError("Invalid snippet content")
        snip = self.session.query(Snippet).filter_by(snippet_id=snippet_id).first()
        if not snip:
            raise ValidationError("Snippet not found")
        category_id = new_category_id if new_category_id is not None else snip.category_id
        if (
            self.session.query(Snippet)
            .filter(
                Snippet.category_id == category_id,
                Snippet.name == new_name,
                Snippet.snippet_id != snippet_id,
            )
            .first()
        ):
            raise ValidationError("Duplicate snippet name")
        snip.name = new_name
        snip.content = new_content
        snip.category_id = category_id
        return snip

    def delete_snippet(self, snippet_id: int) -> None:
        """Delete a snippet by id if it exists."""
        snip = self.session.query(Snippet).filter_by(snippet_id=snippet_id).first()
        if not snip:
            raise ValidationError("Snippet not found")
        self.session.delete(snip)


# --- Lightweight typing for the session/query surface used above ---
T = TypeVar("T")


class QueryLike(Protocol[T]):
    def filter_by(self, **kwargs: object) -> "QueryLike[T]": ...

    def filter(self, *args: object, **kwargs: object) -> "QueryLike[T]": ...

    def first(self) -> Optional[T]: ...

    def all(self) -> List[T]: ...


class SessionLike(Protocol):
    def query(self, model: type[T]) -> QueryLike[T]: ...

    def add(self, instance: object) -> None: ...

    def delete(self, instance: object) -> None: ...
