# classes/db.py

from classes.mysql_db import MySQLDatabase
# from classes.mssql_db import MSSQLDatabase
from classes.sqlite_db import SQLiteDatabase


def get_database(backend="mysql", **kwargs):
    if backend == "mysql":
        return MySQLDatabase(**kwargs)
    # elif backend == "mssql":
    #     return MSSQLDatabase(**kwargs)
    elif backend == "sqlite":
        return SQLiteDatabase(**kwargs)
    else:
        raise ValueError(f"Unsupported backend: {backend}")
