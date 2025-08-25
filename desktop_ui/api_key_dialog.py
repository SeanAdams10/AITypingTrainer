"""API Key Configuration Dialog.

This module provides a dialog for configuring API keys for external services,
with secure storage and retrieval functionality.
"""

import base64
import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Dict, Optional

# Import winreg for Windows registry access
if sys.platform == "win32":
    import ctypes
    import winreg

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
    """Dialog for configuring API keys with secure storage.

    This dialog allows users to:
    - Enter their API keys
    - Save keys securely to disk
    - Retrieve previously saved keys

    The keys are stored in an encrypted file using Fernet symmetric encryption.
    A machine-specific salt is used to enhance security.
    """

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        """Initialize the API Key Configuration dialog.
        
        Args:
            parent: Optional parent dialog widget.
        """
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
        """Verify that the API key is valid by making a test API call to the models endpoint."""
        api_key = self.openai_key_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter an API key to verify.")
            return

        try:
            # Import here to avoid circular imports
            import requests
            from requests.exceptions import RequestException

            # Make a simple API call to list models (lightweight and doesn't consume tokens)
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=10,  # Set a reasonable timeout
            )

            # Check response status
            if response.status_code == 200:
                QMessageBox.information(
                    self, "API Key Verified", "Your OpenAI API key is valid and active!"
                )
            elif response.status_code == 401:
                # 401 typically means invalid or revoked key
                QMessageBox.critical(
                    self,
                    "Invalid API Key",
                    "This API key appears to be invalid or revoked. Please check your key.",
                )
            elif response.status_code == 429:
                # Rate limit reached but key might be valid
                QMessageBox.warning(
                    self,
                    "Rate Limit Reached",
                    "Your API key may be valid, but you've reached a rate limit. "
                    "Please try again later.",
                )
            else:
                # Other errors
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    if "error" in error_data and "message" in error_data["error"]:
                        error_msg = error_data["error"]["message"]
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass

                QMessageBox.critical(
                    self,
                    "Verification Failed",
                    f"Failed with status {response.status_code}: {error_msg}",
                )

        except RequestException as e:
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Could not connect to OpenAI API: {str(e)}. "
                "Please check your internet connection.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Verification Failed", f"Failed to verify API key: {str(e)}")

    def get_user_env_var(self, var_name: str) -> Optional[str]:
        """Reads the value of a user-level environment variable from the Windows Registry.

        Args:
            var_name: Name of the environment variable

        Returns:
            The value as a string, or None if not set
        """
        if not sys.platform == "win32":
            return os.environ.get(var_name)

        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ)

            value, _ = winreg.QueryValueEx(reg_key, var_name)
            winreg.CloseKey(reg_key)
            return str(value) if value is not None else None
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"⚠️ Error reading user env var '{var_name}': {e}")
            return None

    def _load_api_keys(self) -> None:
        """Load API keys from environment variable first, then secure storage.

        On Windows, this will check the Registry for user environment variables first,
        then fall back to process environment, and finally to the encrypted file.
        """
        try:
            # Use get_user_env_var which already handles Windows registry access
            # and falls back to os.environ on non-Windows platforms
            openai_key_from_env = self.get_user_env_var("OpenAPI_Key")

            if openai_key_from_env and openai_key_from_env.strip():
                logging.info("API key loaded from environment variable")
                self.api_keys["openai"] = openai_key_from_env
                self.openai_key_input.setText(openai_key_from_env)
                return
        except Exception as e:
            logging.warning(f"Error loading API key from environment variable: {str(e)}")
            # Continue to try encrypted file

        # If environment variable not found or empty, try the encrypted file
        if not CRYPTOGRAPHY_AVAILABLE:
            QMessageBox.warning(
                self,
                "Security Library Missing",
                "The cryptography library is not installed. API keys will not be securely stored."
                "\n\nPlease run: pip install cryptography",
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
            print(f"Error loading API keys from encrypted file: {str(e)}")
            # If there's an error, we'll start with empty keys
            self.api_keys = {}

    def _save_api_keys(self) -> None:
        """Save API keys to both environment variable (permanently) and secure storage."""
        # Get the API key
        openai_key = self.openai_key_input.text().strip()
        if not openai_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter an OpenAI API key.")
            return

        # Save to the user's environment variable permanently
        self._set_permanent_environment_variable("OpenAPI_Key", openai_key)

        # Also set for current session
        os.environ["OpenAPI_Key"] = openai_key
        os.environ["OPENAI_API_KEY"] = openai_key  # For compatibility with OpenAI SDK

        # Update the API keys dictionary
        self.api_keys["openai"] = openai_key

        # Check if cryptography is available for secure storage
        if not CRYPTOGRAPHY_AVAILABLE:
            # Even without cryptography, we've still set the env vars
            QMessageBox.warning(
                self,
                "Limited Security",
                "Your API key has been set as an environment variable, but secure file storage is not available."
                "\n\nThe cryptography library is needed for secure file storage."
                "\nPlease run: pip install cryptography",
            )
            self.accept()
            return

        try:
            # Get the encryption key
            key = self._get_encryption_key()

            # Encrypt and save
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(json.dumps(self.api_keys).encode())

            with open(self.config_dir / "api_keys.enc", "wb") as f:
                f.write(encrypted_data)

            QMessageBox.information(
                self,
                "Success",
                "API key saved successfully to environment variable and secure storage!",
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save API key to secure storage: {str(e)}\n\n"
                "However, the key has been saved as an environment variable.",
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save API key: {str(e)}")

    def _get_encryption_key(self) -> bytes:
        """Generate an encryption key based on machine-specific data.

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
            # Create machine-specific key for this installation
            machine_id = (
                platform.node()
                + platform.platform()
                + str(os.getuid() if hasattr(os, "getuid") else os.getpid())
            ).encode("utf-8")  # Ensure it's bytes for PBKDF2HMAC
        except Exception:
            # Fallback if platform specific info fails
            machine_id = "typing_trainer_default_key".encode("utf-8")  # Ensure it's bytes

        # Derive a key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id))  # Returns bytes
        return key

    def _set_permanent_environment_variable(self, var_name: str, var_value: str) -> None:
        """Set a permanent environment variable for the current user's profile.
        
        {{ ... }}.

        Args:
                    var_name: Name of the environment variable
                    var_value: Value to set
        """
        try:
            if sys.platform == "win32":
                # Use Windows Registry API
                # Open registry key for user environment variables
                reg_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE
                )

                # Set the value
                winreg.SetValueEx(reg_key, var_name, 0, winreg.REG_SZ, var_value)
                winreg.CloseKey(reg_key)

                # Tell Windows to broadcast that the environment has changed
                try:
                    # Constants for broadcasting the WM_SETTINGCHANGE message
                    HWND_BROADCAST = 0xFFFF
                    WM_SETTINGCHANGE = 0x001A
                    SMTO_ABORTIFHUNG = 0x0002
                    result = ctypes.c_long()

                    # Broadcast the environment change
                    ctypes.windll.user32.SendMessageTimeoutW(
                        HWND_BROADCAST,
                        WM_SETTINGCHANGE,
                        0,
                        "Environment",
                        SMTO_ABORTIFHUNG,
                        5000,  # 5 second timeout
                        ctypes.byref(result),
                    )
                    print(f"✅ Environment variable '{var_name}' set permanently.")
                except Exception as e:
                    # If broadcasting fails, the variable is still set, but may need a restart to take effect
                    print(f"⚠️ Variable set but may require restart: {e}")
            else:
                # On Unix/Linux/Mac, modify the appropriate profile file
                # This is a simplified approach - a more robust solution would
                # need to handle different shells and profile files
                home = os.path.expanduser("~")
                profile_file = os.path.join(home, ".bash_profile")

                # Check if .bash_profile exists, otherwise use .profile
                if not os.path.exists(profile_file):
                    profile_file = os.path.join(home, ".profile")

                # Read existing content
                try:
                    with open(profile_file, "r") as f:
                        content = f.read()
                except FileNotFoundError:
                    content = ""

                # Check if the variable is already set
                var_line = f'export {var_name}="{var_value}"'

                # If not found or different, add/update it
                if not any(
                    line.strip().startswith(f"export {var_name}=") for line in content.splitlines()
                ):
                    with open(profile_file, "a") as f:
                        f.write(f"\n# Added by AITypingTrainer\n{var_line}\n")
                else:
                    # Replace existing line (simplified - doesn't handle all edge cases)
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if line.strip().startswith(f"export {var_name}="):
                            lines[i] = var_line

                    with open(profile_file, "w") as f:
                        f.write("\n".join(lines))

                print(f"✅ Environment variable '{var_name}' set permanently in {profile_file}.")
        except Exception as e:
            print(f"❌ Failed to set environment variable: {e}")
            # If we can't set it permanently, at least set it for the current session
            os.environ[var_name] = var_value
            print("⚠️ Variable set for current session only.")

    @classmethod
    def get_api_key(
        cls, parent: Optional[QDialog] = None, key_type: str = "openai"
    ) -> Optional[str]:
        """Class method to get an API key, showing the dialog if needed.

        Args:
            parent: Parent widget
            key_type: The type of API key to retrieve (e.g., "openai")

        Returns:
            Optional[str]: The API key if available, None otherwise
        """
        # First check for the OpenAPI_Key environment variable
        if key_type == "openai":
            env_key = os.environ.get("OpenAPI_Key")
            if env_key and env_key.strip():
                return env_key

            # For backward compatibility, also check OPENAI_API_KEY
            env_key = os.environ.get("OPENAI_API_KEY")
            if env_key and env_key.strip():
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
