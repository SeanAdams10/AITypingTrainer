"""
User dialog for adding/editing users.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from models.user import User


class UserDialog(QDialog):
    """
    Dialog for adding or editing a user.
    """

    def __init__(
        self,
        user: Optional[User] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize the user dialog.

        Args:
            user: Optional user to edit. If None, create a new user.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Edit User" if user else "Add User")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Form layout for user details
        form_layout = QFormLayout()

        # First name field
        self.first_name_edit = QLineEdit()
        self.first_name_edit.setPlaceholderText("Enter first name")
        form_layout.addRow("First Name:", self.first_name_edit)

        # Surname field
        self.surname_edit = QLineEdit()
        self.surname_edit.setPlaceholderText("Enter surname")
        form_layout.addRow("Surname:", self.surname_edit)

        # Email field
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Enter email address")
        form_layout.addRow("Email:", self.email_edit)

        # Populate fields if editing
        if self.user:
            self.first_name_edit.setText(self.user.first_name or "")
            self.surname_edit.setText(self.user.surname or "")
            self.email_edit.setText(self.user.email_address or "")

        layout.addLayout(form_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def validate_and_accept(self) -> None:
        """Validate input and accept the dialog if valid."""
        first_name = self.first_name_edit.text().strip()
        surname = self.surname_edit.text().strip()
        email = self.email_edit.text().strip()

        if not first_name:
            QMessageBox.warning(self, "Validation Error", "First name is required.")
            self.first_name_edit.setFocus()
            return

        if not email:
            QMessageBox.warning(self, "Validation Error", "Email is required.")
            self.email_edit.setFocus()
            return

        # Basic email validation
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            self.email_edit.setFocus()
            return

        # Create or update user object
        if self.user:
            self.user.first_name = first_name
            self.user.surname = surname
            self.user.email_address = email
        else:
            # Don't pass user_id - let the User model auto-generate it
            self.user = User(
                first_name=first_name,
                surname=surname,
                email_address=email,
            )

        self.accept()

    def get_user(self) -> User:
        """
        Get the user object with updated values.

        Returns:
            The updated or new user object.
        """
        return self.user
