import sqlite3
import os
from classes.database_interface import DatabaseInterface


class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_file=":memory:"):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row

    def _execute(self, sql, params=None, fetch=True, commit=False, many=False):
        cursor = self.conn.cursor()
        try:
            if many and params:
                cursor.executemany(sql, params)
            else:
                cursor.execute(sql, params or [])
            if fetch:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            if commit:
                self.conn.commit()
        finally:
            cursor.close()

    def begin_transaction(self):
        self.conn.execute('BEGIN')

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def select_record(self, sql):
        return self._execute(sql, fetch=True)

    def insert_record(self, table_name, fields, data):
        fields_list = ', '.join(fields)
        value_list = ', '.join(['?'] * len(fields))
        sql = f'INSERT INTO {table_name} ({fields_list}) VALUES ({value_list})'
        self._execute(sql, params=data, fetch=False, commit=True)
        return self.get_last_insert_id()

    def update_record(self, table_name, fields, primary_key, key_value, data):
        assignment_list = ', '.join([f'{f} = ?' for f in fields])
        sql = f'UPDATE {table_name} SET {assignment_list} WHERE {primary_key} = ?'
        self._execute(sql, params=data + [key_value], fetch=False, commit=True)

    def delete_record(self, table_name, primary_key, key_value):
        sql = f'DELETE FROM {table_name} WHERE {primary_key} = ?'
        self._execute(sql, params=[key_value], fetch=False, commit=True)

    def exec_sql(self, sql, auto_commit=True):
        if ';' in sql.strip():
            cursor = self.conn.cursor()
            try:
                cursor.executescript(sql)
                if auto_commit:
                    self.conn.commit()
            finally:
                cursor.close()
        else:
            self._execute(sql, fetch=False, commit=auto_commit)

    def get_last_auto_increment_key(self, table_name):
        sql = 'SELECT seq FROM sqlite_sequence WHERE name = ?'
        rows = self._execute(sql, params=[table_name], fetch=True)
        return rows[0]['seq'] if rows else None

    def host_name(self):
        return "localhost"

    def database_name(self):
        return os.path.basename(self.db_file) if self.db_file != ":memory:" else "memory"

    def check_table_exists(self, table_name):
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        rows = self._execute(sql, params=[table_name])
        return bool(rows)

    def check_field_exists(self, table_name, alter_type, column, data_type):
        sql = f"PRAGMA table_info({table_name})"
        cursor = self.conn.cursor()
        cursor.execute(sql)
        columns = [row[1] for row in cursor.fetchall()]
        cursor.close()

        if alter_type == 'add' and column not in columns:
            alter_sql = f'ALTER TABLE {table_name} ADD COLUMN {column} {data_type}'
            self.exec_sql(alter_sql)
        elif alter_type in ['change', 'modify']:
            pass  # SQLite 不支援修改欄位型態，需重新建表

    def get_table_names(self):
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        rows = self.select_record(sql)
        return [row['name'] for row in rows]

    def ping(self):
        try:
            self.conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False
