from pathlib import Path
import json
import os
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet

def load_decrypted_credentials(key: str, env_file_path: Path) -> dict | None:
    """
    Loads the encrypted credential token from the .env file, decrypts it,
    and returns the credentials as a Python dictionary.

    Args:
        key: The encryption key (must match the key used for encryption).
        env_file_path: Path object pointing to the .env file.

    Returns:
        A dictionary of credentials or None if the token is missing or invalid.
    """
    # 1. Load the .env file contents into the OS environment
    # This ensures os.getenv() will see the encrypted token.
    load_dotenv(dotenv_path=env_file_path, override=True)

    # 2. Retrieve the encrypted token string
    encrypted_token_str = os.getenv("ENCRYPTED_DB_CREDENTIALS")

    if not encrypted_token_str:
        print("WARN: ENCRYPTED_DB_CREDENTIALS not found in .env file.")
        return None

    try:
        # 3. Initialize Fernet with the key
        f = Fernet(key.encode())

        # 4. Decrypt the token
        # The token must be encoded from its base64 string back into bytes for decryption
        decrypted_bytes = f.decrypt(encrypted_token_str.encode())

        # 5. Decode back to a string and parse the JSON
        decrypted_string = decrypted_bytes.decode("utf-8")

        # 6. Parse the JSON string back into a Python dictionary
        credentials = json.loads(decrypted_string)

        print("INFO: Database credentials successfully loaded and decrypted.")
        return credentials

    except Exception as e:
        print(f"ERROR: Decryption failed. Key mismatch or data corruption. Details: {e}")
        return None

def get_or_generate_key(env_file_path: Path) -> str:
    """
    Loads the environment file and retrieves the APP_ENCRYPTION_KEY.
    If the key is not found, a new one is generated and saved to the file.

    Args:
        env_file_path: The Path object pointing to the .env file.

    Returns:
        The encryption key as a UTF-8 string.
    """
    # 1. Ensure the .env file exists
    # Create the file if it doesn't exist.
    env_file_path.touch(mode=0o600, exist_ok=True)

    # 2. Load the existing .env contents into the OS environment
    # This ensures os.getenv() will see the key if it exists.
    load_dotenv(dotenv_path=env_file_path, override=True)

    # 3. Try to get the existing key
    key = os.getenv("APP_ENCRYPTION_KEY")

    if key is None:
        # 4. Key is missing: Generate a new one
        new_key_bytes = Fernet.generate_key()
        new_key_string = new_key_bytes.decode()

        # 5. Save the new key to the .env file
        set_key(
            dotenv_path=env_file_path,
            key_to_set="APP_ENCRYPTION_KEY",
            value_to_set=new_key_string
        )

        return new_key_string
    else:
        return key

