import os
import json
import sqlite3
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ensure these imports match your project structure
from iLibrary import Library, User

from content.functions import get_or_generate_key, load_decrypted_credentials

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] SyncWorker: %(message)s"
)
logger = logging.getLogger("SyncWorker")


class SyncWorker:
    def __init__(self, page=None):
        """
        :param page: The Flet page object (optional), used for PubSub notifications.
        """
        self.page = page
        self.base_dir = Path(__file__).parent
        self.env_path = self.base_dir  / ".env"
        self.db_path = self.base_dir / ".auth" / "libraries_metadata.db"

        # Create storage directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _upsert_data(self, table_name, schema, upsert_sql, data_rows):
        """
        Performs a non-destructive update.
        It will NOT drop the table or delete existing data.
        """
        try:
            # timeout=30 prevents "database is locked" errors if the UI is reading
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                cursor = conn.cursor()

                # 1. Create table if it doesn't exist (ensures the table is always there)
                # Add this TEMPORARILY to your _upsert_data to fix the built app's DB
                #cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} {schema}")

                # 2. Insert new records or update existing ones (Upsert)
                # This requires a PRIMARY KEY defined in the schema
                cursor.executemany(upsert_sql, data_rows)

                conn.commit()
                logger.info(f"Successfully upserted {len(data_rows)} rows into {table_name}")

                # 3. Notify the UI to refresh without a full page reload
                if self.page:
                    self.page.pubsub.send_all(f"refresh_{table_name.lower()}")

        except sqlite3.Error as e:
            logger.error(f"Database error during upsert in {table_name}: {e}")

    async def run_sync_cycle(self):
        """A single pass of fetching data from the server and updating the local DB."""
        load_dotenv(self.env_path, override=True)
        encryption_key = get_or_generate_key(self.env_path)

        if not os.getenv("ENCRYPTED_DB_CREDENTIALS"):
            logger.warning("No credentials found in .env. Skipping sync cycle.")
            return

        creds = load_decrypted_credentials(encryption_key, self.env_path)
        if not creds:
            logger.error("Could not decrypt credentials.")
            return

        # --- Sync Libraries (Non-Destructive) ---
        try:
            with Library(creds["user"], creds["password"], creds["system"], creds["driver"]) as lib:
                raw_data = json.loads(lib.getAllLibraries())
                items = raw_data.get('data', [])

                values = [(i.get('OBJNAME'), i.get('OBJCREATED'), i.get('TEXT')) for i in items if isinstance(i, dict)]

                # Schema uses OBJNAME as PRIMARY KEY to enable upserting
                self._upsert_data(
                    table_name="LIBRARY_METADATA",
                    schema="(OBJNAME TEXT PRIMARY KEY, OBJCREATED TEXT, DESCRIPTION TEXT)",
                    upsert_sql="""
                             INSERT INTO LIBRARY_METADATA (OBJNAME, OBJCREATED, DESCRIPTION)
                                VALUES (?, ?, ?)
                                ON CONFLICT(OBJNAME) 
                                DO UPDATE SET 
                                    OBJCREATED = EXCLUDED.OBJCREATED,
                                    DESCRIPTION = EXCLUDED.DESCRIPTION;
                                 """,
                    data_rows=values
                )
        except Exception as e:
            logger.error(f"Library sync error: {e}")

        # --- Sync Users (Non-Destructive) ---
        try:
            with User(creds["user"], creds["password"], creds["system"], creds["driver"]) as user:
                raw_data = json.loads(user.getAllUsers())
                items = raw_data.get('data', [])

                values = [
                    (i.get('AUTHORIZATION_NAME'), i.get('CREATION_TIMESTAMP'), i.get('TEXT_DESCRIPTION'))
                    for i in items if isinstance(i, dict)
                ]

                # Schema uses AUTHORIZATION_NAME as PRIMARY KEY
                self._upsert_data(
                    table_name="USER_METADATA",
                    schema="(AUTHORIZATION_NAME TEXT PRIMARY KEY, CREATION_TIMESTAMP TEXT, TEXT_DESCRIPTION TEXT)",
                    upsert_sql=f"""INSERT INTO USER_METADATA (AUTHORIZATION_NAME, CREATION_TIMESTAMP, TEXT_DESCRIPTION)
                                   VALUES (?, ?, ?)
                           ON CONFLICT(AUTHORIZATION_NAME) 
                            DO UPDATE SET 
                            CREATION_TIMESTAMP = EXCLUDED.CREATION_TIMESTAMP,
                            TEXT_DESCRIPTION = EXCLUDED.TEXT_DESCRIPTION;""",
                    data_rows=values
                )

        except Exception as e:
            logger.error(f"User sync error: {e}")

    async def main_loop(self):
        """Infinite loop for the background worker."""
        logger.info("Background Worker heartbeat started.")
        while True:
            await self.run_sync_cycle()
            # Wait for 60 seconds before syncing again
            await asyncio.sleep(60.0)


# Entry point for stand-alone execution
if __name__ == "__main__":
    worker = SyncWorker()
    try:
        asyncio.run(worker.main_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped manually.")