import sqlite3
from pathlib import Path
import json
import os
import socket
import pyodbc
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet
import tomllib
import flet as ft
from iLibrary import Library, User

from content.db_manager import db_mgr
import logging

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

        #print("INFO: Database credentials successfully loaded and decrypted.")
        return credentials

    except Exception as e:
        #print(f"ERROR: Decryption failed. Key mismatch or data corruption. Details: {e}")
        return None


# --- Background Task: Sync and Banner Management ---

logger = logging.getLogger("QueryAfterSettings")


async def run_query_after_settings(page: ft.Page, page_content: ft.Container):
    """
    Executed after settings are saved.
    Loads credentials and performs an immediate sync of Library and User metadata.
    """
    env_file_path = Path(__file__).parent / ".env"

    # 1. Load and Decrypt Credentials
    load_dotenv(env_file_path, override=True)
    encryption_key = get_or_generate_key(env_file_path)
    credentials_str = os.getenv("ENCRYPTED_DB_CREDENTIALS")

    if not credentials_str:
        logger.warning("Sync aborted: No credentials found.")
        return

    db_creds = load_decrypted_credentials(encryption_key, env_file_path)
    if not db_creds:
        logger.error("Sync aborted: Could not decrypt credentials.")
        return

    # Update Global State
    await ft.SharedPreferences().set('server', str(db_creds["system"]))

    # Close any open dialogs (like the settings modal)
    page.pop_dialog()

    # 2. Synchronize Library Data
    try:
        with Library(db_creds["user"], db_creds["password"],
                     db_creds["system"], db_creds["driver"]) as lib:

            raw_data = json.loads(lib.getAllLibraries())
            items = raw_data.get('data', [])

            values = [
                (item.get('OBJNAME'), item.get('OBJCREATED'), item.get("TEXT"))
                for item in items if isinstance(item, dict)
            ]

            # Use the manager to refresh the table
            db_mgr.refresh_table(
                table_name="LIBRARY_METADATA",
                schema="(OBJNAME TEXT, OBJCREATED TEXT, DESCRIPTION TEXT)",
                insert_sql="INSERT INTO LIBRARY_METADATA VALUES (?, ?, ?)",
                data=values
            )
            logger.info(f"Library Sync: {len(values)} items processed.")

    except Exception as e:
        logger.exception(f"Library Sync failed: {e}")

    # 3. Synchronize User Data
    try:
        with User(db_creds["user"], db_creds["password"],
                  db_creds["system"], db_creds["driver"]) as user:

            raw_data = json.loads(user.getAllUsers())
            items = raw_data.get('data', [])

            values = [
                (item.get('AUTHORIZATION_NAME'), item.get('CREATION_TIMESTAMP'), item.get('TEXT_DESCRIPTION'))
                for item in items if isinstance(item, dict)
            ]

            # Use the manager to refresh the table
            db_mgr.refresh_table(
                table_name="USER_METADATA",
                schema="(AUTHORIZATION_NAME TEXT, CREATION_TIMESTAMP TEXT, TEXT_DESCRIPTION TEXT)",
                insert_sql="INSERT INTO USER_METADATA VALUES (?, ?, ?)",
                data=values
            )
            logger.info(f"User Sync: {len(values)} items processed.")

    except Exception as e:
        logger.exception(f"User Sync failed: {e}")

    # Final UI Refresh
    page.update()


async def _sync_library_data(page, creds, db_path):
    try:
        with Library(creds["user"], creds["password"], creds["system"], creds["driver"]) as lib:
            raw_data = json.loads(lib.getAllLibraries())
            items = raw_data.get('data', [])

            values = [
                (item.get('OBJNAME'), item.get('OBJCREATED'), item.get('TEXT'))
                for item in items if isinstance(item, dict)
            ]

            _execute_db_transaction(
                db_path,
                "DROP TABLE IF EXISTS LIBRARY_METADATA",
                "CREATE TABLE LIBRARY_METADATA (OBJNAME VARCHAR(128), OBJCREATED TIMESTAMP, DESCRIPTION TEXT)",
                "INSERT INTO LIBRARY_METADATA (OBJNAME, OBJCREATED, DESCRIPTION) VALUES (?, ?, ?)",
                values
            )
            logger.info("Library metadata synced successfully.")
    except Exception as e:
        logger.error(f"Library Sync Error: {e}")


async def _sync_user_data(page, creds, db_path):
    try:
        with User(creds["user"], creds["password"], creds["system"], creds["driver"]) as user:
            raw_data = json.loads(user.getAllUsers())
            items = raw_data.get('data', [])

            values = [
                (item.get('AUTHORIZATION_NAME'), item.get('CREATION_TIMESTAMP'), item.get('TEXT_DESCRIPTION'))
                for item in items if isinstance(item, dict)
            ]

            _execute_db_transaction(
                db_path,
                "DROP TABLE IF EXISTS USER_METADATA",
                "CREATE TABLE USER_METADATA (AUTHORIZATION_NAME VARCHAR(10), CREATION_TIMESTAMP TIMESTAMP, TEXT_DESCRIPTION VARCHAR(50))",
                "INSERT INTO USER_METADATA (AUTHORIZATION_NAME, CREATION_TIMESTAMP, TEXT_DESCRIPTION) VALUES (?, ?, ?)",
                values
            )
            logger.info("User metadata synced successfully.")
    except Exception as e:
        logger.error(f"User Sync Error: {e}")


def _execute_db_transaction(db_path, drop_sql, create_sql, insert_sql, values):
    """Internal helper to minimize boilerplate for SQLite operations."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(drop_sql)
            cursor.execute(create_sql)
            cursor.executemany(insert_sql, values)
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database Transaction Error: {e}")
        raise  # Pass it up to the caller to handle UI notifications

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

def try_to_build_connection(db_driver:str, db_host:str, port:int, db_user:str, db_password:str) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((db_host, port))
        if result == 0:
            conn_str = (
                f"DRIVER={db_driver};"
                f"SYSTEM={db_host};"
                f"UID={db_user};"
                f"PWD={db_password};"
            )
            pyodbc.connect(conn_str, autocommit=True)

            return True
        else:
            return False

    except pyodbc.Error as ex:
        return False

def load_app_info():
    try:
        with open("assets/app.json", "rb") as f:
            data = json.load(f)
            print(data)
            return  data
    except Exception as e:
        print(e)

