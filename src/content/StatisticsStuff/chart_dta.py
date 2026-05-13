import sqlite3
from pathlib import Path


class ChartManager:
    """A helper class to keep the chart logic organized."""

    def __init__(self):
        self.lib_months = []
        self.user_months = []
        self.lib_counts = []
        self.user_counts = []
        self.path_to_DB = Path(__file__).parent.parent / ".auth"
        self.path_to_DB_file = self.path_to_DB / "libraries_metadata.db"

    def get_library_data(self):
        query = """
                SELECT strftime('%Y-%m', OBJCREATED) AS month, COUNT(OBJNAME)
                FROM LIBRARY_METADATA
                WHERE OBJCREATED >= date('now', '-1 year')
                GROUP BY month
                ORDER BY month ASC; 
                """
        try:
            with sqlite3.connect(self.path_to_DB_file) as con:
                cur = con.cursor()
                data = cur.execute(query).fetchall()
                self.lib_months = [row[0] for row in data]
                self.lib_counts = [row[1] for row in data]
        except sqlite3.Error:
            self.lib_months, self.lib_counts = [], []



    def get_user_data(self):
        query = """
                SELECT strftime('%Y-%m', CREATION_TIMESTAMP) AS month, COUNT(AUTHORIZATION_NAME)
                FROM USER_METADATA
                WHERE CREATION_TIMESTAMP >= date('now', '-1 year')
                GROUP BY month
                ORDER BY month ASC; 
                """
        try:
            with sqlite3.connect(self.path_to_DB_file) as con:
                cur = con.cursor()
                data = cur.execute(query).fetchall()
                self.user_months = [row[0] for row in data]
                self.user_counts = [row[1] for row in data]
        except sqlite3.Error:
            self.user_months, self.user_counts = [], []

