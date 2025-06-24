#!/usr/bin/env python3
"""
Generate a secure encryption key for MakerMatrix supplier credentials
"""
import base64
import secrets

# Generate a cryptographically secure 32-byte key
key_bytes = secrets.token_bytes(32)
key_base64 = base64.b64encode(key_bytes).decode('utf-8')

print("🔐 MakerMatrix Encryption Key Generator")
print("=" * 50)
print(f"Generated encryption key: {key_base64}")
print("\n📝 To use this key:")
print(f"   export MAKERMATRIX_ENCRYPTION_KEY=\"{key_base64}\"")
print("\n⚠️  IMPORTANT:")
print("   - Save this key securely!")
print("   - If you lose it, encrypted credentials become unreadable")
print("   - Add it to your .env file or startup script")
print("   - Keep it consistent across restarts")
print("\n💡 Add to .bashrc or .zshrc:")
print(f"   echo 'export MAKERMATRIX_ENCRYPTION_KEY=\"{key_base64}\"' >> ~/.bashrc")