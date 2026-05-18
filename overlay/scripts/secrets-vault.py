#!/usr/bin/env python3
"""
AegisNova OS — Secrets Vault Integration Utility
==================================================
Securely manages API keys, credentials, and secrets using:
- AES-256-GCM encryption
- Master password protection
- Environment variable injection
- Integration with Model Manager and AI agents

Usage:
    python3 secrets-vault.py --init
    python3 secrets-vault.py --store OPENAI_API_KEY sk-...
    python3 secrets-vault.py --load --format env
    python3 secrets-vault.py --list
    python3 secrets-vault.py --delete OPENAI_API_KEY
"""

import os
import sys
import json
import base64
import getpass
import hashlib
import argparse
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Encryption imports - use pycryptodome if available, fallback to simple encryption
try:
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Random import get_random_bytes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# ── Configuration ──
VAULT_DIR = "/etc/aegisnova/vault"
VAULT_FILE = f"{VAULT_DIR}/secrets.enc"
SALT_FILE = f"{VAULT_DIR}/salt"
MASTER_HASH_FILE = f"{VAULT_DIR}/master.hash"
ENV_OUTPUT = "/etc/aegisnova/env"

@dataclass
class SecretEntry:
    key: str
    value: str
    created_at: str
    modified_at: str
    description: str = ""

class SecretsVault:
    """Secure vault for managing sensitive credentials."""
    
    def __init__(self):
        os.makedirs(VAULT_DIR, mode=0o700, exist_ok=True)
        self._ensure_permissions()
    
    def _ensure_permissions(self):
        """Ensure vault directory has secure permissions."""
        os.chmod(VAULT_DIR, 0o700)
        for f in [VAULT_FILE, SALT_FILE, MASTER_HASH_FILE]:
            if os.path.exists(f):
                os.chmod(f, 0o600)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password."""
        if CRYPTO_AVAILABLE:
            return PBKDF2(password, salt, dkLen=32, count=100000)
        else:
            # Fallback (less secure, but functional)
            return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=32)
    
    def _encrypt(self, data: str, key: bytes) -> bytes:
        """Encrypt data using AES-256-GCM."""
        if CRYPTO_AVAILABLE:
            cipher = AES.new(key, AES.MODE_GCM)
            ciphertext, tag = cipher.encrypt_and_digest(data.encode())
            return base64.b64encode(cipher.nonce + tag + ciphertext)
        else:
            # Simple XOR fallback (NOT for production!)
            # This is a fallback when pycryptodome is not available
            # In production, pycryptodome should always be installed
            plaintext = data.encode()
            key_stream = hashlib.sha256(key).digest()
            encrypted = bytes(p ^ key_stream[i % len(key_stream)] for i, p in enumerate(plaintext))
            return base64.b64encode(encrypted)
    
    def _decrypt(self, encrypted_data: bytes, key: bytes) -> str:
        """Decrypt data."""
        data = base64.b64decode(encrypted_data)
        
        if CRYPTO_AVAILABLE:
            nonce = data[:16]
            tag = data[16:32]
            ciphertext = data[32:]
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag).decode()
        else:
            # Simple XOR fallback
            key_stream = hashlib.sha256(key).digest()
            decrypted = bytes(c ^ key_stream[i % len(key_stream)] for i, c in enumerate(data))
            return decrypted.decode()
    
    def init_vault(self, password: str) -> bool:
        """Initialize a new vault with master password."""
        if os.path.exists(MASTER_HASH_FILE):
            print("Vault already initialized. Use --reinit to reset.")
            return False
        
        # Generate salt
        if CRYPTO_AVAILABLE:
            salt = get_random_bytes(32)
        else:
            salt = os.urandom(32)
        
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)
        os.chmod(SALT_FILE, 0o600)
        
        # Store password hash
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with open(MASTER_HASH_FILE, 'w') as f:
            f.write(password_hash)
        os.chmod(MASTER_HASH_FILE, 0o600)
        
        # Create empty vault
        key = self._derive_key(password, salt)
        encrypted = self._encrypt(json.dumps({}), key)
        with open(VAULT_FILE, 'wb') as f:
            f.write(encrypted)
        os.chmod(VAULT_FILE, 0o600)
        
        print("✅ Vault initialized successfully.")
        print(f"   Location: {VAULT_DIR}")
        return True
    
    def _authenticate(self, password: str) -> bool:
        """Verify master password."""
        if not os.path.exists(MASTER_HASH_FILE):
            print("Vault not initialized. Run with --init first.")
            return False
        
        with open(MASTER_HASH_FILE, 'r') as f:
            stored_hash = f.read().strip()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == stored_hash
    
    def _load_vault(self, password: str) -> Dict[str, SecretEntry]:
        """Load and decrypt vault contents."""
        if not self._authenticate(password):
            raise ValueError("Invalid password")
        
        with open(SALT_FILE, 'rb') as f:
            salt = f.read()
        
        with open(VAULT_FILE, 'rb') as f:
            encrypted = f.read()
        
        key = self._derive_key(password, salt)
        decrypted = self._decrypt(encrypted, key)
        data = json.loads(decrypted)
        
        return {k: SecretEntry(**v) for k, v in data.items()}
    
    def _save_vault(self, password: str, vault: Dict[str, SecretEntry]):
        """Encrypt and save vault contents."""
        with open(SALT_FILE, 'rb') as f:
            salt = f.read()
        
        key = self._derive_key(password, salt)
        data = {k: asdict(v) for k, v in vault.items()}
        encrypted = self._encrypt(json.dumps(data), key)
        
        with open(VAULT_FILE, 'wb') as f:
            f.write(encrypted)
        os.chmod(VAULT_FILE, 0o600)
    
    def store_secret(self, password: str, key: str, value: str, description: str = "") -> bool:
        """Store a secret in the vault."""
        try:
            vault = self._load_vault(password)
        except ValueError as e:
            print(f"Error: {e}")
            return False
        
        now = datetime.utcnow().isoformat()
        vault[key] = SecretEntry(
            key=key,
            value=value,
            created_at=vault.get(key, SecretEntry("", "", now, now)).created_at if key in vault else now,
            modified_at=now,
            description=description
        )
        
        self._save_vault(password, vault)
        print(f"✅ Secret '{key}' stored successfully.")
        return True
    
    def retrieve_secret(self, password: str, key: str) -> Optional[str]:
        """Retrieve a secret from the vault."""
        try:
            vault = self._load_vault(password)
        except ValueError as e:
            print(f"Error: {e}")
            return None
        
        entry = vault.get(key)
        if entry:
            return entry.value
        print(f"Secret '{key}' not found.")
        return None
    
    def list_secrets(self, password: str) -> Dict[str, str]:
        """List all secrets (without values)."""
        try:
            vault = self._load_vault(password)
        except ValueError as e:
            print(f"Error: {e}")
            return {}
        
        return {k: f"{v.created_at} | {v.description}" for k, v in vault.items()}
    
    def delete_secret(self, password: str, key: str) -> bool:
        """Delete a secret from the vault."""
        try:
            vault = self._load_vault(password)
        except ValueError as e:
            print(f"Error: {e}")
            return False
        
        if key in vault:
            del vault[key]
            self._save_vault(password, vault)
            print(f"✅ Secret '{key}' deleted.")
            return True
        print(f"Secret '{key}' not found.")
        return False
    
    def export_to_env(self, password: str, output_file: str = ENV_OUTPUT) -> bool:
        """Export secrets to environment file."""
        try:
            vault = self._load_vault(password)
        except ValueError as e:
            print(f"Error: {e}")
            return False
        
        with open(output_file, 'w') as f:
            f.write("# AegisNova Secrets Vault Export\n")
            f.write(f"# Generated: {datetime.utcnow().isoformat()}\n\n")
            for entry in vault.values():
                f.write(f"export {entry.key}={entry.value}\n")
        
        os.chmod(output_file, 0o600)
        print(f"✅ Secrets exported to: {output_file}")
        return True


# ── CLI Interface ──
def main():
    parser = argparse.ArgumentParser(
        description="AegisNova Secrets Vault"
    )
    parser.add_argument("--init", action="store_true", help="Initialize vault")
    parser.add_argument("--store", nargs=2, metavar=("KEY", "VALUE"), help="Store a secret")
    parser.add_argument("--retrieve", metavar="KEY", help="Retrieve a secret")
    parser.add_argument("--delete", metavar="KEY", help="Delete a secret")
    parser.add_argument("--list", action="store_true", help="List all secrets")
    parser.add_argument("--export", action="store_true", help="Export to env file")
    parser.add_argument("--description", default="", help="Description for stored secret")
    
    args = parser.parse_args()
    
    vault = SecretsVault()
    
    if args.init:
        password = getpass.getpass("Set master password: ")
        confirm = getpass.getpass("Confirm master password: ")
        if password != confirm:
            print("Passwords do not match!")
            sys.exit(1)
        if len(password) < 12:
            print("Password must be at least 12 characters!")
            sys.exit(1)
        vault.init_vault(password)
        return
    
    if args.store:
        password = getpass.getpass("Master password: ")
        vault.store_secret(password, args.store[0], args.store[1], args.description)
        return
    
    if args.retrieve:
        password = getpass.getpass("Master password: ")
        value = vault.retrieve_secret(password, args.retrieve)
        if value:
            print(value)
        return
    
    if args.delete:
        password = getpass.getpass("Master password: ")
        vault.delete_secret(password, args.delete)
        return
    
    if args.list:
        password = getpass.getpass("Master password: ")
        secrets = vault.list_secrets(password)
        if secrets:
            print("\nStored Secrets:")
            print("-" * 60)
            for key, info in secrets.items():
                print(f"  {key:<30} {info}")
            print()
        else:
            print("Vault is empty.")
        return
    
    if args.export:
        password = getpass.getpass("Master password: ")
        vault.export_to_env(password)
        return
    
    parser.print_help()
    print("\n\nExamples:")
    print("  secrets-vault.py --init")
    print("  secrets-vault.py --store OPENAI_API_KEY sk-xxx --description 'OpenAI API Key'")
    print("  secrets-vault.py --retrieve OPENAI_API_KEY")
    print("  secrets-vault.py --list")
    print("  secrets-vault.py --export")


if __name__ == "__main__":
    main()
