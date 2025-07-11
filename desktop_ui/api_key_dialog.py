"""
API Key Configuration Dialog.

This module provides a dialog for configuring API keys for external services,
with secure storage and retrieval functionality.
"""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

# Attempt to import cryptography - will be required for encryption features
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


class APIKeyDialog(QDialog):
    """
    Dialog for configuring API keys with secure storage.
    
    This dialog allows users to:
    - Enter their API keys
    - Save keys securely to disk
    - Retrieve previously saved keys
    
    The keys are stored in an encrypted file using Fernet symmetric encryption.
    A machine-specific salt is used to enhance security.
    """
    
    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("API Key Configuration")
        self.setMinimumWidth(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.api_keys: Dict[str, str] = {}
        self.config_dir = self._get_config_dir()
        
        self._setup_ui()
        self._load_api_keys()
    
    def _get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        # Get project root directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        
        # Create and return config directory path
        config_dir = project_root / "config"
        config_dir.mkdir(exist_ok=True)
        return config_dir
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # OpenAI API Key section
        layout.addWidget(QLabel("<b>OpenAI API Key</b>"))
        layout.addWidget(QLabel("Your API key is stored securely on this device."))
        
        openai_layout = QHBoxLayout()
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setPlaceholderText("Enter your OpenAI API key")
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        openai_layout.addWidget(self.openai_key_input)
        
        show_key_btn = QPushButton("Show")
        show_key_btn.setCheckable(True)
        show_key_btn.toggled.connect(self._toggle_key_visibility)
        openai_layout.addWidget(show_key_btn)
        
        layout.addLayout(openai_layout)
        
        # API key verification and information
        api_info_label = QLabel(
            "Your API key is required for word generation features.\n"
            "The key is stored securely and never transmitted except to OpenAI services."
        )
        api_info_label.setWordWrap(True)
        layout.addWidget(api_info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        verify_button = QPushButton("Verify API Key")
        verify_button.clicked.connect(self._verify_api_key)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_api_keys)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(verify_button)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addStretch()
        layout.addLayout(button_layout)
    
    def _toggle_key_visibility(self, checked: bool) -> None:
        """Toggle the visibility of the API key."""
        self.openai_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
    
    def _verify_api_key(self) -> None:
        """Verify that the API key is valid by making a test API call."""
        api_key = self.openai_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(
                self, "Missing API Key", "Please enter an API key to verify."
            )
            return
            
        try:
            # Import here to avoid circular imports
            from models.llm_ngram_service import LLMNgramService
            
            # Create a temporary service to test the key
            service = LLMNgramService(api_key)
            
            # Simple test query
            result = service.get_words_with_ngrams(
                ngrams=["the"], max_length=10, model="gpt-3.5-turbo"
            )
            
            if result:
                QMessageBox.information(
                    self, "API Key Verified", "Your OpenAI API key is valid!"
                )
            else:
                QMessageBox.warning(
                    self, "Verification Issue", 
                    "API responded, but no content was returned. The key may be valid, "
                    "but there might be other issues."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self, "Verification Failed", f"Failed to verify API key: {str(e)}"
            )
    
    def _load_api_keys(self) -> None:
        """Load API keys from secure storage."""
        if not CRYPTOGRAPHY_AVAILABLE:
            QMessageBox.warning(
                self, 
                "Security Library Missing", 
                "The cryptography library is not installed. API keys will not be securely stored."
                "\n\nPlease run: pip install cryptography"
            )
            return
            
        try:
            encrypted_path = self.config_dir / "api_keys.enc"
            if not encrypted_path.exists():
                return
                
            # Get the encryption key
            key = self._get_encryption_key()
            
            # Read and decrypt the file
            with open(encrypted_path, "rb") as f:
                encrypted_data = f.read()
                
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)
            self.api_keys = json.loads(decrypted_data.decode())
            
            # Set the OpenAI API key in the input field
            if "openai" in self.api_keys:
                self.openai_key_input.setText(self.api_keys["openai"])
                
        except Exception as e:
            print(f"Error loading API keys: {str(e)}")
            # If there's an error, we'll start with empty keys
            self.api_keys = {}
    
    def _save_api_keys(self) -> None:
        """Save API keys to secure storage."""
        # Check if cryptography is available for secure storage
        if not CRYPTOGRAPHY_AVAILABLE:
            # Even without cryptography, we can still set the env var for current session
            openai_key = self.openai_key_input.text().strip()
            if not openai_key:
                QMessageBox.warning(
                    self, "Missing API Key", "Please enter an OpenAI API key."
                )
                return
                
            os.environ["OPENAI_API_KEY"] = openai_key
            self.api_keys["openai"] = openai_key
            
            QMessageBox.warning(
                self,
                "Limited Security",
                "Your API key has been set for this session, but secure storage is not available."
                "\n\nThe cryptography library is needed for secure storage."
                "\nPlease run: pip install cryptography"
            )
            self.accept()
            return
            
        try:
            # Update the API keys dictionary
            openai_key = self.openai_key_input.text().strip()
            if not openai_key:
                QMessageBox.warning(
                    self, "Missing API Key", "Please enter an OpenAI API key."
                )
                return
            
            self.api_keys["openai"] = openai_key
            
            # Get the encryption key
            key = self._get_encryption_key()
            
            # Encrypt and save
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(json.dumps(self.api_keys).encode())
            
            with open(self.config_dir / "api_keys.enc", "wb") as f:
                f.write(encrypted_data)
            
            # Set environment variable for current session
            os.environ["OPENAI_API_KEY"] = openai_key
            
            QMessageBox.information(
                self, "Success", "API key saved successfully!"
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save API key: {str(e)}"
            )
    
    def _get_encryption_key(self) -> bytes:
        """
        Generate an encryption key based on machine-specific data.
        
        This creates a deterministic but secure key based on:
        - A salt file stored in the config directory
        - Machine-specific information
        
        Returns:
            bytes: A 32-byte key for Fernet encryption
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("Cryptography package is not available")
            
        # Get or create a salt
        salt_path = self.config_dir / "salt.bin"
        if salt_path.exists():
            with open(salt_path, "rb") as f:
                salt = f.read()
        else:
            # Create a random salt and save it
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
        
        # Get machine-specific data
        # This creates a unique identifier for the current machine
        # While not foolproof, it helps ensure keys can only be decrypted on this machine
        try:
            import platform
            machine_id = (
                platform.node() + 
                platform.platform() + 
                str(os.getuid() if hasattr(os, 'getuid') else os.getpid())
            )
        except Exception:
            # Fallback if platform specific info fails
            machine_id = "typing_trainer_default_key"
            
        machine_id = machine_id.encode()
            
        # Derive a key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(machine_id))
        return key

    @classmethod
    def get_api_key(cls, parent: Optional[QDialog] = None, key_type: str = "openai") -> Optional[str]:
        """
        Class method to get an API key, showing the dialog if needed.
        
        Args:
            parent: Parent widget
            key_type: The type of API key to retrieve (e.g., "openai")
            
        Returns:
            Optional[str]: The API key if available, None otherwise
        """
        # First check environment variable
        if key_type == "openai":
            env_key = os.environ.get("OPENAI_API_KEY")
            if env_key:
                return env_key
                
        # Then try to load from our encrypted storage
        try:
            dialog_instance = cls(parent=parent)
            dialog_instance._load_api_keys()
            
            if key_type in dialog_instance.api_keys and dialog_instance.api_keys[key_type]:
                return dialog_instance.api_keys[key_type]
                
        except Exception:
            pass
            
        # If we couldn't get the key, show the dialog
        dialog = cls(parent=parent)
        if dialog.exec():
            # Dialog was accepted, keys should be saved
            # Return the requested key
            return dialog.api_keys.get(key_type)
            
        return None


if __name__ == "__main__":
    # Test the dialog
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = APIKeyDialog()
    dialog.exec()
