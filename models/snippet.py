"""
Snippet business logic and data model.
Implements all CRUD, validation, and DB abstraction.
"""

from typing import Optional, List, Any, Union, Annotated
from pydantic import BaseModel, Field, field_validator, BeforeValidator

# Common validator helper functions
def validate_non_empty(value: str) -> str:
    """Validate that a string is not empty or just whitespace."""
    if not value or not value.strip():
        raise ValueError("Value cannot be empty or whitespace")
    return value

def validate_ascii_only(value: str) -> str:
    """Validate that a string contains only ASCII characters."""
    if not all(ord(c) < 128 for c in value):
        raise ValueError("Value must contain only ASCII characters")
    return value

def validate_no_sql_injection(value: str, is_content: bool = False) -> str:
    """Check for potential SQL injection patterns in the input.
    
    Args:
        value: The string to check
        is_content: Whether this is snippet content (code/text) that may legitimately contain
                    quotes and equals signs
    """
    # Core SQL injection patterns that should never be allowed
    core_patterns = [
        "DROP TABLE",   # SQL command
        "DELETE FROM",  # SQL command
        "INSERT INTO",  # SQL command
        "UPDATE SET",   # SQL command
        "SELECT FROM",  # SQL command
        "OR 1=1",      # Boolean injection
        "' OR '",      # String injection
    ]
    
    # Extended patterns that might be legitimate in code snippets
    extended_patterns = [
        "--",           # SQL comment
        ";",            # Statement terminator
        "'",            # Single quote (used in SQL injection)
        "=",            # Equals (used in WHERE clauses)
    ]
    
    # Always check core patterns
    for pattern in core_patterns:
        if pattern.lower() in value.lower():
            raise ValueError(f"Value contains potentially unsafe pattern: {pattern}")
    
    # Only check extended patterns if not validating content (code/text)
    if not is_content:
        for pattern in extended_patterns:
            if pattern.lower() in value.lower():
                raise ValueError(f"Value contains potentially unsafe pattern: {pattern}")
    
    return value

def validate_integer(value: Union[int, str]) -> int:
    """Validate that a value is an integer or can be converted to one."""
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise ValueError("Value must be an integer")
    elif not isinstance(value, int):
        raise ValueError("Value must be an integer")
    return value


class SnippetModel(BaseModel):
    snippet_id: Optional[int] = None
    category_id: int
    snippet_name: str = Field(
        ..., min_length=1, max_length=128, pattern=r"^[\x00-\x7F]+$"
    )
    content: str = Field(..., min_length=1)
    
    # Integer validators
    @field_validator("snippet_id")
    @classmethod
    def validate_snippet_id(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            return validate_integer(v)
        return v
    
    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, v: int) -> int:
        return validate_integer(v)
    
    # String validators
    @field_validator("snippet_name")
    @classmethod
    def validate_snippet_name(cls, v: str) -> str:
        v = validate_non_empty(v)
        v = validate_ascii_only(v)
        v = validate_no_sql_injection(v)
        return v
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = validate_non_empty(v)
        v = validate_ascii_only(v)
        v = validate_no_sql_injection(v, is_content=True)  # Pass is_content=True to allow quotes and equals
        return v


class SnippetManager:
    def __init__(self, db_manager: Any) -> None:
        self.db = db_manager
        self.MAX_PART_LENGTH = 500  # Maximum length of each snippet part
        
    def _split_content_into_parts(self, content: str) -> List[str]:
        """Split content into parts of maximum 500 characters each."""
        parts = []
        remaining = content
        
        while remaining:
            # Take up to MAX_PART_LENGTH characters
            part = remaining[:self.MAX_PART_LENGTH]
            parts.append(part)
            remaining = remaining[self.MAX_PART_LENGTH:]
            
        return parts

    def create_snippet(self, category_id: int, snippet_name: str, content: str) -> int:
        # Validate inputs using the Pydantic model
        try:
            # Create model instance to trigger validation
            SnippetModel(
                category_id=category_id,
                snippet_name=snippet_name,
                content=content
            )
        except ValueError as e:
            # Re-raise any validation errors from the Pydantic model
            raise ValueError(f"Validation error: {str(e)}") from e
            
        # Validate uniqueness
        if self.snippet_exists(category_id, snippet_name):
            raise ValueError("Snippet name must be unique within category")
            
        # Split content into parts of maximum 500 characters
        content_parts = self._split_content_into_parts(content)
        
        # Start transaction - first insert into snippets table
        self.db.execute("BEGIN TRANSACTION", commit=False)
        try:
            cursor = self.db.execute(
                "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
                (category_id, snippet_name),
                commit=False,
            )
            
            lastrowid = getattr(cursor, "lastrowid", None)
            if lastrowid is None:
                raise RuntimeError("Failed to retrieve lastrowid after insert.")
                
            # Next, insert each part into snippet_parts
            for i, part_content in enumerate(content_parts):
                self.db.execute(
                    "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
                    (lastrowid, i, part_content),
                    commit=False
                )
            
            # Commit the transaction
            self.db.execute("COMMIT", commit=True)
            return int(lastrowid)
        except Exception as e:
            # Rollback on any error
            self.db.execute("ROLLBACK", commit=True)
            raise e

    def get_snippet(self, snippet_id: int) -> SnippetModel:
        # First retrieve the snippet metadata from snippets table
        cursor = self.db.execute(
            "SELECT snippet_id, category_id, snippet_name "
            "FROM snippets WHERE snippet_id = ?",
            (snippet_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Snippet not found")
            
        # Convert row to dict for later use
        snippet_dict = (
            {k: row[k] for k in row.keys()}
            if hasattr(row, "keys")
            else dict(
                zip(["snippet_id", "category_id", "snippet_name"], row)
            )
        )
        
        # Now retrieve the content from snippet_parts
        parts_cursor = self.db.execute(
            "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
            (snippet_id,),
        )
        content_parts = parts_cursor.fetchall()
        
        # Combine all parts into a single content string
        if hasattr(content_parts[0], "keys") if content_parts else False:
            full_content = "".join(part["content"] for part in content_parts)
        else:
            full_content = "".join(part[0] for part in content_parts)
            
        # Add content to the dict and create the model
        snippet_dict["content"] = full_content
        return SnippetModel(**snippet_dict)

    def list_snippets(self, category_id: int) -> List[SnippetModel]:
        # First get all snippets in the category
        cursor = self.db.execute(
            "SELECT snippet_id, category_id, snippet_name "
            "FROM snippets WHERE category_id = ?",
            (category_id,),
        )
        rows = cursor.fetchall()
        
        # Create a list to hold the snippet models
        result = []
        
        # For each snippet, get its content from snippet_parts and create a model
        for row in rows:
            # Extract snippet metadata
            snippet_dict = (
                {k: row[k] for k in row.keys()}
                if hasattr(row, "keys")
                else dict(
                    zip(
                        ["snippet_id", "category_id", "snippet_name"],
                        row,
                    )
                )
            )
            
            # Get content parts for this snippet
            snippet_id = snippet_dict["snippet_id"]
            parts_cursor = self.db.execute(
                "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
                (snippet_id,),
            )
            content_parts = parts_cursor.fetchall()
            
            # Combine parts into a single content string
            if content_parts:
                if hasattr(content_parts[0], "keys"):
                    full_content = "".join(part["content"] for part in content_parts)
                else:
                    full_content = "".join(part[0] for part in content_parts)
                    
                # Add content to the dict and create the model
                snippet_dict["content"] = full_content
                result.append(SnippetModel(**snippet_dict))
            
        return result

    def edit_snippet(
        self,
        snippet_id: int,
        snippet_name: Optional[str] = None,
        content: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> None:
        """
        Edit a snippet's name, content, and/or category.
        """
        # Get current snippet to validate and update fields
        snippet = self.get_snippet(snippet_id)

        # Check if name change is valid
        if snippet_name and snippet_name != snippet.snippet_name:
            # Check uniqueness within the new or current category
            check_cat_id = category_id if category_id is not None else snippet.category_id
            if self.snippet_exists(check_cat_id, snippet_name):
                raise ValueError("Snippet name must be unique within category")
            snippet.snippet_name = snippet_name

        # Start transaction for database updates
        self.db.execute("BEGIN TRANSACTION", commit=False)
        try:
            # Update category if changed
            if category_id is not None and category_id != snippet.category_id:
                # Check if the category exists
                category_exists = self.db.execute(
                    "SELECT COUNT(*) FROM categories WHERE category_id = ?",
                    (category_id,)
                ).fetchone()
                if not category_exists or category_exists[0] == 0:
                    raise ValueError(f"Category with ID {category_id} does not exist")
                self.db.execute(
                    "UPDATE snippets SET category_id = ? WHERE snippet_id = ?",
                    (category_id, snippet_id),
                    commit=False
                )
                snippet.category_id = category_id

            # Update snippet name if changed
            if snippet_name:
                self.db.execute(
                    "UPDATE snippets SET snippet_name = ? WHERE snippet_id = ?",
                    (snippet.snippet_name, snippet_id),
                    commit=False,
                )

            # Update content if provided
            if content:
                # Delete existing parts
                self.db.execute(
                    "DELETE FROM snippet_parts WHERE snippet_id = ?",
                    (snippet_id,),
                    commit=False,
                )
                # Split content into parts and insert
                content_parts = self._split_content_into_parts(content)
                for i, part_content in enumerate(content_parts):
                    self.db.execute(
                        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
                        (snippet_id, i, part_content),
                        commit=False
                    )
            # Commit all changes
            self.db.execute("COMMIT", commit=True)
        except Exception as e:
            # Rollback on any error
            self.db.execute("ROLLBACK", commit=True)
            raise e

    def delete_snippet(self, snippet_id: int) -> None:
        # Check if snippet exists
        exists = self.db.execute(
            "SELECT COUNT(*) FROM snippets WHERE snippet_id = ?", 
            (snippet_id,)
        ).fetchone()
        
        if not exists or exists[0] == 0:
            raise ValueError(f"Snippet with ID {snippet_id} does not exist")
        
        # Start transaction for deletion
        self.db.execute("BEGIN TRANSACTION", commit=False)
        try:
            # First delete all related parts
            self.db.execute(
                "DELETE FROM snippet_parts WHERE snippet_id = ?", 
                (snippet_id,), 
                commit=False
            )
            
            # Then delete the snippet itself
            self.db.execute(
                "DELETE FROM snippets WHERE snippet_id = ?", 
                (snippet_id,), 
                commit=False
            )
            
            # Commit all changes
            self.db.execute("COMMIT", commit=True)
        except Exception as e:
            # Rollback on any error
            self.db.execute("ROLLBACK", commit=True)
            raise e

    def snippet_exists(self, category_id: int, snippet_name: str) -> bool:
        cursor = self.db.execute(
            "SELECT 1 FROM snippets WHERE category_id = ? AND snippet_name = ?",
            (category_id, snippet_name),
        )
        row = cursor.fetchone()
        return bool(row)
