# db/interfaces/database_interface.py

from abc import ABC, abstractmethod

class DatabaseInterface(ABC):
    @abstractmethod
    def select_record(self, sql): pass

    @abstractmethod
    def insert_record(self, table_name, fields, data): pass

    @abstractmethod
    def update_record(self, table_name, fields, primary_key, key_value, data): pass

    @abstractmethod
    def delete_record(self, table_name, primary_key, key_value): pass

    @abstractmethod
    def exec_sql(self, sql): pass

    @abstractmethod
    def get_last_auto_increment_key(self, table_name): pass

    @abstractmethod
    def host_name(self): pass

    @abstractmethod
    def database_name(self): pass

    @abstractmethod
    def get_cursor(self): pass

    @abstractmethod
    def check_table_exists(self, table_name): pass

    @abstractmethod
    def check_field_exists(self, table_name, alter_type, column, data_type): pass

    @abstractmethod
    def begin_transaction(self): pass

    @abstractmethod
    def commit(self): pass

    @abstractmethod
    def rollback(self): pass

    @abstractmethod
    def close_database(self): pass

    @abstractmethod
    def connected(self): pass

    # ✅ Optional but useful
    @abstractmethod
    def get_table_names(self): pass

    @abstractmethod
    def ping(self): pass
