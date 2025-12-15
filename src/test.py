from sqlalchemy import create_engine

# Format: ibmi://<user>:<password>@<host>/<rdbname>[?key=value]
try:
    engine = create_engine("ibmi://albeer:rv0751@pub400.com/ALBEER1")
except Exception as e:
    print(e)