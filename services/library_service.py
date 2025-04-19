from sqlalchemy import Column, Integer, String, ForeignKey, Text, UniqueConstraint, create_engine, MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.exc import IntegrityError

Base = declarative_base()
metadata = Base.metadata

class ValidationError(Exception):
    pass

# Make ValidationError importable from this module
__all__ = ["LibraryService", "ValidationError"]

class Category(Base):
    __tablename__ = 'categories'
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    snippets = relationship('Snippet', back_populates='category', cascade="all, delete-orphan")

class Snippet(Base):
    __tablename__ = 'snippets'
    snippet_id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('categories.category_id'), nullable=False)
    name = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    category = relationship('Category', back_populates='snippets')
    __table_args__ = (UniqueConstraint('category_id', 'name', name='uix_category_snippet_name'),)

class LibraryService:
    metadata = metadata
    def __init__(self, session):
        self.session = session

    # Category methods
    def add_category(self, name):
        if not name or len(name) > 50 or not name.isascii():
            raise ValidationError('Invalid category name')
        if self.session.query(Category).filter_by(name=name).first():
            raise ValidationError('Duplicate category name')
        cat = Category(name=name)
        self.session.add(cat)
        self.session.commit()
        return cat

    def get_categories(self):
        return self.session.query(Category).all()

    def edit_category(self, category_id, new_name):
        if not new_name or len(new_name) > 50 or not new_name.isascii():
            raise ValidationError('Invalid category name')
        cat = self.session.query(Category).filter_by(category_id=category_id).first()
        if not cat:
            raise ValidationError('Category not found')
        if self.session.query(Category).filter(Category.name==new_name, Category.category_id!=category_id).first():
            raise ValidationError('Duplicate category name')
        cat.name = new_name
        self.session.commit()
        return cat

    def delete_category(self, category_id):
        cat = self.session.query(Category).filter_by(category_id=category_id).first()
        if not cat:
            raise ValidationError('Category not found')
        self.session.delete(cat)
        self.session.commit()

    # Snippet methods
    def add_snippet(self, category_id, name, content):
        if not name or len(name) > 50 or not name.isascii():
            raise ValidationError('Invalid snippet name')
        if not content or not content.isascii():
            raise ValidationError('Invalid snippet content')
        if self.session.query(Snippet).filter_by(category_id=category_id, name=name).first():
            raise ValidationError('Duplicate snippet name')
        snip = Snippet(category_id=category_id, name=name, content=content)
        self.session.add(snip)
        self.session.commit()
        return snip

    def get_snippets(self, category_id):
        return self.session.query(Snippet).filter_by(category_id=category_id).all()

    def edit_snippet(self, snippet_id, new_name, new_content, new_category_id=None):
        if not new_name or len(new_name) > 50 or not new_name.isascii():
            raise ValidationError('Invalid snippet name')
        if not new_content or not new_content.isascii():
            raise ValidationError('Invalid snippet content')
        snip = self.session.query(Snippet).filter_by(snippet_id=snippet_id).first()
        if not snip:
            raise ValidationError('Snippet not found')
        category_id = new_category_id if new_category_id is not None else snip.category_id
        if self.session.query(Snippet).filter(Snippet.category_id==category_id, Snippet.name==new_name, Snippet.snippet_id!=snippet_id).first():
            raise ValidationError('Duplicate snippet name')
        snip.name = new_name
        snip.content = new_content
        snip.category_id = category_id
        self.session.commit()
        return snip

    def delete_snippet(self, snippet_id):
        snip = self.session.query(Snippet).filter_by(snippet_id=snippet_id).first()
        if not snip:
            raise ValidationError('Snippet not found')
        self.session.delete(snip)
        self.session.commit()
