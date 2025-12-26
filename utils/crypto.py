"""
MediaMTX VMS Client v2.0 - Cryptography Utilities
Secure encryption/decryption for sensitive data like passwords.
"""

import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from utils.logger import logger


class CryptoManager:
    """
    Manages encryption/decryption of sensitive data.
    Uses Fernet symmetric encryption with a machine-derived key.
    """
    
    # Prefix to identify encrypted strings
    ENCRYPTED_PREFIX = "ENC:"
    
    def __init__(self):
        """Initialize crypto manager with machine-derived key."""
        self._fernet: Optional[Fernet] = None
        self._initialize_key()
    
    def _initialize_key(self) -> None:
        """
        Initialize encryption key derived from machine-specific data.
        This ensures passwords are tied to the machine.
        """
        try:
            # Derive key from machine-specific identifiers
            # Combine username + hostname for a unique but reproducible key
            machine_id = f"{os.environ.get('COMPUTERNAME', 'default')}-{os.environ.get('USERNAME', 'user')}"
            
            # Add a salt for additional security
            salt = b"MediaMTX-VMS-Client-Salt-2025"
            
            # Create a 32-byte key using SHA-256
            key_material = hashlib.pbkdf2_hmac(
                'sha256',
                machine_id.encode('utf-8'),
                salt,
                100000  # iterations
            )
            
            # Fernet requires a base64-encoded 32-byte key
            fernet_key = base64.urlsafe_b64encode(key_material)
            self._fernet = Fernet(fernet_key)
            
            logger.debug("CryptoManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CryptoManager: {e}")
            self._fernet = None
    
    def encrypt(self, plain_text: str) -> str:
        """
        Encrypt a plain text string.
        
        Args:
            plain_text: Plain text to encrypt
            
        Returns:
            Encrypted string with prefix, or original if encryption fails
        """
        if not plain_text:
            return plain_text
            
        # Don't double-encrypt
        if plain_text.startswith(self.ENCRYPTED_PREFIX):
            return plain_text
        
        if not self._fernet:
            logger.warning("Encryption not available, storing plain text")
            return plain_text
        
        try:
            encrypted_bytes = self._fernet.encrypt(plain_text.encode('utf-8'))
            encrypted_str = base64.urlsafe_b64encode(encrypted_bytes).decode('ascii')
            return f"{self.ENCRYPTED_PREFIX}{encrypted_str}"
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return plain_text
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_text: Encrypted string (with prefix)
            
        Returns:
            Decrypted plain text, or original if decryption fails
        """
        if not encrypted_text:
            return encrypted_text
        
        # If not encrypted (legacy plain text), return as-is
        if not encrypted_text.startswith(self.ENCRYPTED_PREFIX):
            return encrypted_text
        
        if not self._fernet:
            logger.warning("Decryption not available")
            return ""
        
        try:
            # Remove prefix and decode
            encrypted_data = encrypted_text[len(self.ENCRYPTED_PREFIX):]
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('ascii'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
            
        except InvalidToken:
            logger.error("Decryption failed: Invalid token (wrong machine or corrupted data)")
            return ""
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ""
    
    def is_encrypted(self, text: str) -> bool:
        """Check if a string is encrypted."""
        return text.startswith(self.ENCRYPTED_PREFIX) if text else False


# Global crypto manager instance
crypto = CryptoManager()


def encrypt_password(password: str) -> str:
    """Convenience function to encrypt a password."""
    return crypto.encrypt(password)


def decrypt_password(encrypted: str) -> str:
    """Convenience function to decrypt a password."""
    return crypto.decrypt(encrypted)
