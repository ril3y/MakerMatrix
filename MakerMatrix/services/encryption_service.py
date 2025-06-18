"""
Encryption Service for Supplier Credentials

Provides AES-256-GCM encryption for sensitive supplier credentials with
proper key management, salt generation, and secure storage practices.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import logging
import json

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting supplier credentials
    
    Uses AES-256-GCM encryption with PBKDF2 key derivation for secure
    credential storage. Each credential is encrypted with its own salt.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            master_key: Master encryption key (if None, uses environment variable)
        """
        self.logger = logging.getLogger(f"{__name__}.EncryptionService")
        self.master_key = master_key or self._get_master_key()
        self.algorithm = "AES-256-GCM"
        self.key_length = 32  # 256 bits
        self.salt_length = 16  # 128 bits
        self.nonce_length = 12  # 96 bits for GCM
        self.tag_length = 16  # 128 bits for GCM authentication tag
        self.iterations = 100000  # PBKDF2 iterations
        
        # Validate master key
        if not self.master_key:
            raise ValueError("Master encryption key not provided")
        
        self.logger.info("Encryption service initialized with AES-256-GCM")
    
    def _get_master_key(self) -> str:
        """Get master key from environment or generate a new one"""
        # Try to get from environment first
        master_key = os.getenv("MAKERMATRIX_ENCRYPTION_KEY")
        
        if not master_key:
            # Generate a new master key and warn user
            master_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            self.logger.warning(
                "No master encryption key found in environment. Generated new key. "
                "Set MAKERMATRIX_ENCRYPTION_KEY environment variable to persist encryption keys."
            )
            self.logger.warning(f"Generated key: {master_key}")
        
        return master_key
    
    def generate_salt(self) -> bytes:
        """Generate a cryptographically secure random salt"""
        return secrets.token_bytes(self.salt_length)
    
    def derive_key(self, salt: bytes) -> bytes:
        """
        Derive encryption key from master key and salt using PBKDF2
        
        Args:
            salt: Random salt for key derivation
            
        Returns:
            Derived encryption key
        """
        master_key_bytes = base64.b64decode(self.master_key.encode('utf-8'))
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.key_length,
            salt=salt,
            iterations=self.iterations,
            backend=default_backend()
        )
        
        return kdf.derive(master_key_bytes)
    
    def encrypt(self, plaintext: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        Encrypt plaintext using AES-256-GCM
        
        Args:
            plaintext: Text to encrypt
            salt: Optional salt (generates new one if not provided)
            
        Returns:
            Tuple of (encrypted_data_base64, salt_base64)
        """
        if not plaintext:
            return "", ""
        
        try:
            # Generate salt if not provided
            if salt is None:
                salt = self.generate_salt()
            
            # Derive encryption key
            key = self.derive_key(salt)
            
            # Generate nonce for GCM
            nonce = secrets.token_bytes(self.nonce_length)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            
            # Encrypt data
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
            
            # Combine nonce + ciphertext + tag
            encrypted_data = nonce + ciphertext + encryptor.tag
            
            # Encode as base64 for storage
            encrypted_base64 = base64.b64encode(encrypted_data).decode('utf-8')
            salt_base64 = base64.b64encode(salt).decode('utf-8')
            
            self.logger.debug(f"Successfully encrypted data of length {len(plaintext)}")
            return encrypted_base64, salt_base64
            
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, encrypted_data_base64: str, salt_base64: str) -> str:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data_base64: Base64 encoded encrypted data
            salt_base64: Base64 encoded salt
            
        Returns:
            Decrypted plaintext
        """
        if not encrypted_data_base64 or not salt_base64:
            return ""
        
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_data_base64.encode('utf-8'))
            salt = base64.b64decode(salt_base64.encode('utf-8'))
            
            # Extract components
            nonce = encrypted_data[:self.nonce_length]
            tag = encrypted_data[-self.tag_length:]
            ciphertext = encrypted_data[self.nonce_length:-self.tag_length]
            
            # Derive decryption key
            key = self.derive_key(salt)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            
            # Decrypt data
            decryptor = cipher.decryptor()
            plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()
            
            plaintext = plaintext_bytes.decode('utf-8')
            self.logger.debug(f"Successfully decrypted data to length {len(plaintext)}")
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_credentials(self, credentials: Dict[str, str]) -> Tuple[Dict[str, str], str]:
        """
        Encrypt multiple credential fields
        
        Args:
            credentials: Dictionary of credential field names to values
            
        Returns:
            Tuple of (encrypted_credentials_dict, salt_base64)
        """
        if not credentials:
            return {}, ""
        
        # Generate single salt for all fields
        salt = self.generate_salt()
        salt_base64 = base64.b64encode(salt).decode('utf-8')
        
        encrypted_creds = {}
        
        for field_name, value in credentials.items():
            if value:  # Only encrypt non-empty values
                encrypted_value, _ = self.encrypt(value, salt)
                encrypted_creds[f"{field_name}_encrypted"] = encrypted_value
        
        self.logger.info(f"Encrypted {len(encrypted_creds)} credential fields")
        return encrypted_creds, salt_base64
    
    def decrypt_credentials(self, encrypted_credentials: Dict[str, str], salt_base64: str) -> Dict[str, str]:
        """
        Decrypt multiple credential fields
        
        Args:
            encrypted_credentials: Dictionary of encrypted credential fields
            salt_base64: Base64 encoded salt
            
        Returns:
            Dictionary of decrypted credential values
        """
        if not encrypted_credentials or not salt_base64:
            return {}
        
        decrypted_creds = {}
        
        for field_name, encrypted_value in encrypted_credentials.items():
            if field_name.endswith('_encrypted') and encrypted_value:
                # Remove _encrypted suffix to get original field name
                original_field = field_name[:-10]
                decrypted_value = self.decrypt(encrypted_value, salt_base64)
                decrypted_creds[original_field] = decrypted_value
        
        self.logger.debug(f"Decrypted {len(decrypted_creds)} credential fields")
        return decrypted_creds
    
    def rotate_encryption(self, encrypted_data_base64: str, old_salt_base64: str) -> Tuple[str, str]:
        """
        Rotate encryption by decrypting with old salt and re-encrypting with new salt
        
        Args:
            encrypted_data_base64: Currently encrypted data
            old_salt_base64: Current salt
            
        Returns:
            Tuple of (new_encrypted_data_base64, new_salt_base64)
        """
        try:
            # Decrypt with old salt
            plaintext = self.decrypt(encrypted_data_base64, old_salt_base64)
            
            # Re-encrypt with new salt
            new_encrypted, new_salt = self.encrypt(plaintext)
            
            self.logger.info("Successfully rotated encryption")
            return new_encrypted, new_salt
            
        except Exception as e:
            self.logger.error(f"Encryption rotation failed: {e}")
            raise EncryptionError(f"Failed to rotate encryption: {str(e)}")
    
    def generate_key_id(self, salt_base64: str) -> str:
        """
        Generate a unique key ID for tracking encryption keys
        
        Args:
            salt_base64: Base64 encoded salt
            
        Returns:
            Unique key identifier
        """
        # Create hash of salt + master key info for key identification
        hash_input = f"{salt_base64}:{self.algorithm}:{self.iterations}"
        key_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        return f"key_{key_hash[:16]}"
    
    def validate_encryption_integrity(self, encrypted_data_base64: str, salt_base64: str) -> bool:
        """
        Validate that encrypted data can be properly decrypted
        
        Args:
            encrypted_data_base64: Encrypted data to validate
            salt_base64: Salt used for encryption
            
        Returns:
            True if data can be decrypted successfully
        """
        try:
            # Attempt decryption
            self.decrypt(encrypted_data_base64, salt_base64)
            return True
        except Exception:
            return False
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """Get information about the encryption configuration"""
        return {
            "algorithm": self.algorithm,
            "key_length": self.key_length,
            "salt_length": self.salt_length,
            "nonce_length": self.nonce_length,
            "tag_length": self.tag_length,
            "iterations": self.iterations,
            "master_key_configured": bool(self.master_key)
        }


class EncryptionError(Exception):
    """Exception raised for encryption/decryption errors"""
    pass


class CredentialEncryptionMixin:
    """
    Mixin class for models that need credential encryption
    
    Provides helper methods for encrypting/decrypting credential fields
    in database models.
    """
    
    _encryption_service: Optional[EncryptionService] = None
    
    @classmethod
    def get_encryption_service(cls) -> EncryptionService:
        """Get or create encryption service instance"""
        if cls._encryption_service is None:
            cls._encryption_service = EncryptionService()
        return cls._encryption_service
    
    def encrypt_field(self, field_value: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Encrypt a single field value
        
        Args:
            field_value: Value to encrypt
            salt: Optional salt (generates new one if not provided)
            
        Returns:
            Tuple of (encrypted_value, salt_base64)
        """
        encryption_service = self.get_encryption_service()
        
        salt_bytes = base64.b64decode(salt) if salt else None
        return encryption_service.encrypt(field_value, salt_bytes)
    
    def decrypt_field(self, encrypted_value: str, salt: str) -> str:
        """
        Decrypt a single field value
        
        Args:
            encrypted_value: Encrypted value
            salt: Salt used for encryption
            
        Returns:
            Decrypted value
        """
        encryption_service = self.get_encryption_service()
        return encryption_service.decrypt(encrypted_value, salt)
    
    def encrypt_credentials_dict(self, credentials: Dict[str, str]) -> Tuple[Dict[str, str], str]:
        """
        Encrypt multiple credentials
        
        Args:
            credentials: Dictionary of credential fields
            
        Returns:
            Tuple of (encrypted_credentials, salt_base64)
        """
        encryption_service = self.get_encryption_service()
        return encryption_service.encrypt_credentials(credentials)
    
    def decrypt_credentials_dict(self, encrypted_credentials: Dict[str, str], salt: str) -> Dict[str, str]:
        """
        Decrypt multiple credentials
        
        Args:
            encrypted_credentials: Dictionary of encrypted credentials
            salt: Salt used for encryption
            
        Returns:
            Dictionary of decrypted credentials
        """
        encryption_service = self.get_encryption_service()
        return encryption_service.decrypt_credentials(encrypted_credentials, salt)