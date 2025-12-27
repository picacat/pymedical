from PyQt5.QtWidgets import QMessageBox, QPushButton
import configparser
import os

from libs import string_utils
from libs import db_utils
from libs import system_utils

try:
    import pyodbc
except Exception:
    system_utils.pip3_install('pyodbc')

from classes.database_interface import DatabaseInterface

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))
DB_PATH = "mssql"

class MSSQLDatabase(DatabaseInterface):
    CONFIG_FILE = os.path.join(BASE_DIR, "pymedical.conf")

    def __init__(self, config_file=None, **kwargs):
        self.cnx = None
        self.server = 'localhost'
        self.user = ''
        self.password = ''
        self.database = ''
        self.driver = 'ODBC Driver 17 for SQL Server'
        if config_file:
            self.CONFIG_FILE = config_file
        self.timeout = 0
        self._connect_to_db(**kwargs)

    def __del__(self):
        self.close_database()

    def connected(self):
        return self.cnx is not None

    def close_database(self):
        if self.cnx:
            self.cnx.close()

    def _connect_to_db(self, **kwargs):
        try:
            if not kwargs:
                config = configparser.ConfigParser()
                config.read(self.CONFIG_FILE)
                self.server = config['db'].get('host', self.server)
                self.user = config['db']['user']
                self.password = config['db']['password']
                self.database = config['db']['database']
                self.driver = config['db'].get('driver', self.driver)
            else:
                self.server = kwargs.get('host', self.server)
                self.user = kwargs['user']
                self.password = kwargs['password']
                self.database = kwargs['database']
                self.driver = kwargs.get('driver', self.driver)

            self._create_connection()
        except Exception as err:
            print(f"Error: {err}")
            self.cnx = None
        self.timeout = 0

    def _create_connection(self):
        try:
            conn_str = (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.user};"
                f"PWD={self.password};"
                f"TrustServerCertificate=yes"
            )
            self.cnx = pyodbc.connect(conn_str, timeout=5, autocommit=False)
        except pyodbc.Error as err:
            print(f"Connection error: {err}")
            self.cnx = None

    def begin_transaction(self):
        self.cnx.autocommit = False

    def commit(self):
        self.cnx.commit()

    def rollback(self):
        self.cnx.rollback()

    def get_cursor(self):
        for _ in range(10):
            try:
                return self.cnx.cursor()
            except Exception:
                self._reconnect()
        return None

    def _reconnect(self):
        if self.cnx:
            self.cnx.close()
        self._connect_to_db()

    def select_record(self, sql):
        if not sql:
            return None
        try:
            cursor = self.get_cursor()
            cursor.execute(sql)
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
        return rows

    def delete_record(self, table_name, primary_key, key_value):
        cursor = self.get_cursor()
        sql = f'DELETE FROM {table_name} WHERE {primary_key} = ?'
        cursor.execute(sql, (key_value,))
        self.cnx.commit()
        cursor.close()

    def insert_record(self, table_name, fields, data):
        cursor = self.get_cursor()
        fields_list = ', '.join(fields)
        placeholders = ', '.join(['?'] * len(fields))
        sql = f'INSERT INTO {table_name} ({fields_list}) VALUES ({placeholders})'
        string_utils.str_to_none(data)
        cursor.execute(sql, data)
        self.cnx.commit()
        cursor.execute("SELECT @@IDENTITY AS id")
        last_row_id = cursor.fetchone()[0]
        cursor.close()
        return last_row_id

    def update_record(self, table_name, fields, primary_key, key_value, data):
        cursor = self.get_cursor()
        assignment_list = ', '.join([f'{field} = ?' for field in fields])
        sql = f'UPDATE {table_name} SET {assignment_list} WHERE {primary_key} = ?'
        string_utils.str_to_none(data)
        cursor.execute(sql, data + [key_value])
        self.cnx.commit()
        cursor.close()

    def exec_sql(self, sql, auto_commit=True):
        cursor = self.get_cursor()
        cursor.execute(sql)
        if auto_commit:
            self.cnx.commit()
        cursor.close()

    def _is_table_exists(self, table_name):
        sql = f"""
            SELECT * FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{table_name}'
        """
        rows = self.select_record(sql)
        return bool(rows)

    def create_table(self, table_name):
        table_file = os.path.join(BASE_DIR, DB_PATH, f'{table_name}.sql')
        try:
            with open(table_file, 'r', encoding='utf-8') as db_table:
                sql = db_table.read()

            sql = string_utils.remove_bom(sql)
            cursor = self.cnx.cursor()
            for statement in sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)
            self.cnx.commit()
        except FileNotFoundError:
            self._show_error_message('資料庫檔案不存在', f'找不到 {table_file}，請確認路徑正確。')
        except UnicodeDecodeError:
            print('檔案編碼錯誤')
        finally:
            cursor.close()

    def _show_error_message(self, title, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def check_table_exists(self, table_name):
        if 'InsReply' in table_name:
            return

        if not self._is_table_exists(table_name):
            self.create_table(table_name)
            db_utils.set_default_data(self, table_name)

    def get_last_auto_increment_key(self, table_name):
        sql = f'''
            SELECT IDENT_CURRENT('{table_name}') AS AUTO_INCREMENT
        '''
        row = self.select_record(sql)
        return row[0]['AUTO_INCREMENT'] if row else None

    def host_name(self):
        return self.server

    def database_name(self):
        return self.database

    def check_field_exists(self, table_name, alter_type, column, data_type):
        sql = f'''
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{column}'
        '''
        rows = self.select_record(sql)

        column_exists = bool(rows)
        type_match = column_exists and rows[0]['DATA_TYPE'].lower() == data_type.lower()

        if (alter_type == 'add' and column_exists) or \
           (alter_type in ['change', 'modify'] and (not column_exists or type_match)):
            return

        if alter_type == 'add':
            alter_sql = f'ALTER TABLE {table_name} ADD {column} {data_type}'
        elif alter_type == 'change':
            alter_sql = f'ALTER TABLE {table_name} ALTER COLUMN {column} {data_type}'
        elif alter_type == 'modify':
            alter_sql = f'ALTER TABLE {table_name} ALTER COLUMN {column} {data_type}'

        self.exec_sql(alter_sql)

    def get_table_names(self):
        sql = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        rows = self.select_record(sql)
        return [row['TABLE_NAME'] for row in rows]

    def ping(self):
        try:
            self.cnx.cursor().execute("SELECT 1")
            return True
        except pyodbc.Error:
            return False
