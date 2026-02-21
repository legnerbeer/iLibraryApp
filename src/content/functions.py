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
        #print(f"ERROR: Decryption failed. Key mismatch or data corruption. Details: {e}")
        return None


# --- Background Task: Sync and Banner Management ---
async def run_query_after_settings(page, page_content):
    env_file_path = Path(__file__).parent / ".env"



    ENCRYPTION_KEY_STR = get_or_generate_key(env_file_path)
    load_dotenv(env_file_path, override=True)
    credentials_str = os.getenv("ENCRYPTED_DB_CREDENTIALS")


    if credentials_str:
        db_credentials = load_decrypted_credentials(ENCRYPTION_KEY_STR, env_file_path)

        if db_credentials:
            await ft.SharedPreferences().set('server', str(db_credentials["system"]))
            page.pop_dialog()
            try:
                with Library(db_credentials["user"], db_credentials["password"],
                             db_credentials["system"], db_credentials["driver"]) as lib:
                    # making a new table and insert data into it
                    path_to_DB = Path(__file__).parent.parent / ".auth"
                    path_to_DB_file = path_to_DB / "libraries_metadata.db"
                    if not path_to_DB.exists():
                        path_to_DB.mkdir(parents=True, exist_ok=True)

                    DBConnect = sqlite3.connect(path_to_DB_file)
                    cursor = DBConnect.cursor()
                    cursor.execute("DROP TABLE IF EXISTS LIBRARY_METADATA")
                    cursor.execute("""CREATE TABLE LIBRARY_METADATA
                                      (

                                          OBJNAME    VARCHAR(128),
                                          OBJCREATED TIMESTAMP
                                      )
                                   """)
                    # 1. Ensure result is a valid string
                    raw_result = lib.getAllLibraries()

                    result_str = str(raw_result) if raw_result is not None else "[]"

                    data_list = json.loads(result_str)

                    if data_list:
                        # Wir nehmen nur OBJNAME und OBJCREATED aus jedem Dictionary
                        values = [(item.get('OBJNAME'), item.get('OBJCREATED')) for item in data_list]

                        sql_insert = "INSERT INTO LIBRARY_METADATA (OBJNAME, OBJCREATED) VALUES (?, ?)"

                        # 3. Daten für executemany vorbereiten (Liste von Tupeln)
                        # .get(col) stellt sicher, dass es nicht abstürzt, falls ein Key mal fehlt
                        # values = [tuple(item.get(col) for col in columns) for item in data_list]

                        try:
                            # 4. Massen-Insert ausführen
                            cursor.executemany(sql_insert, values)
                            DBConnect.commit()
                            print(f"Erfolg: {len(values)} Datensätze wurden importiert.")
                        except sqlite3.Error as e:
                            print(f"Fehler beim Einfügen: {e}")

            except Exception as e:
                #config.SERVER_STATUS = False
                print(f"Library Sync Error: {e}")

                # --- Sync Users ---
            try:
                with User(db_credentials["user"], db_credentials["password"],
                          db_credentials["system"], db_credentials["driver"]) as user:

                    # 1. Fetch result

                    path_to_DB = Path(__file__).parent.parent / ".auth"
                    path_to_DB_file = path_to_DB / "libraries_metadata.db"
                    if not path_to_DB.exists():
                        path_to_DB.mkdir(parents=True, exist_ok=True)

                    DBConnect = sqlite3.connect(path_to_DB_file)
                    cursor = DBConnect.cursor()

                    cursor.execute("DROP TABLE IF EXISTS USER_METADATA")
                    cursor.execute("""CREATE TABLE USER_METADATA
                                      (
                                          AUTHORIZATION_NAME VARCHAR(10),
                                          CREATION_TIMESTAMP TIMESTAMP,
                                          TEXT_DESCRIPTION   VARCHAR(50)
                                      )
                                   """)

                    # 1. Ensure result is a valid string
                    raw_user_result = user.getAllUsers(wantJson=True)
                    user_result_str = str(raw_user_result) if raw_user_result is not None else "[]"

                    data_list = json.loads(user_result_str)

                    if data_list:
                        # Wir nehmen nur OBJNAME und OBJCREATED aus jedem Dictionary
                        values = [(item.get('AUTHORIZATION_NAME'), item.get('CREATION_TIMESTAMP'),
                                   item.get('TEXT_DESCRIPTION')) for item in data_list]

                        sql_insert = "INSERT INTO USER_METADATA (AUTHORIZATION_NAME, CREATION_TIMESTAMP, TEXT_DESCRIPTION) VALUES (?, ?, ?)"

                        try:
                            # 4. Massen-Insert ausführen
                            cursor.executemany(sql_insert, values)
                            DBConnect.commit()

                        except sqlite3.Error as e:
                            page.show_dialog(ft.AlertDialog(title="Error", content=ft.Text(f"Error: {e}")))
                            page.update()

            except Exception as e:
                print(f"User Sync Error: {e}")
    else:
        # Show banner if credentials missing
        if not error_banner.open:
            page.show_dialog(error_banner)

    page.update()


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
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return  data
    except Exception as e:
        print(e)

