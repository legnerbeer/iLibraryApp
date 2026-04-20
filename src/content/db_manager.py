import sqlite3
import logging
from pathlib import Path

class DatabaseManager:
    def __init__(self):
        self.db_path = Path(__file__).parent / ".auth" / "libraries_metadata.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def refresh_table(self, table_name, schema, insert_sql, data):
        """
        Safely drops, recreates, and repopulates a table.
        """
        try:
            # timeout=10 helps prevent 'database is locked' errors
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()
                # Using f-strings for table names is okay here as they are internal,
                # but we use '?' placeholders for the actual data to prevent SQL injection.
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                cursor.execute(f"CREATE TABLE {table_name} {schema}")
                cursor.executemany(insert_sql, data)
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"DatabaseManager Error in refresh_table: {e}")
            raise  # Re-raise so the calling function knows the sync failed
db_mgr = DatabaseManager()