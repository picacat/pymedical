# -*- coding: utf-8 -*-
import configparser
import os
import re
import time

import mysql.connector as mysql

from classes.database_interface import DatabaseInterface
from libs import db_utils, string_utils

BASE_DIR = os.path.abspath(os.getcwd())
DB_PATH = "mysql"


class MySQLDatabase(DatabaseInterface):
    """MySQL 資料庫操作類別，提供連線、查詢、插入、更新、刪除與資料表管理功能。"""

    CONFIG_FILE = os.path.join(BASE_DIR, "pymedical.conf")

    def __init__(self, config_file=None, **kwargs):
        """初始化 MySQLDatabase 類別。

        Args:
            config_file (str, optional): 設定檔路徑。
            **kwargs: 資料庫連線參數。
        """
        self.cnx = None
        self.host = "localhost"
        self.user = ""
        self.password = ""
        self.database = ""
        self.charset = "utf8mb4"
        self.port = 3306
        self.engine = "MyISAM"

        if config_file:
            self.CONFIG_FILE = config_file

        self.timeout = 0
        self._connect_to_db(**kwargs)

    # def __del__(self):
    #     """解構時關閉資料庫連線。"""
    #     self.close_database()

    def connected(self):
        """檢查是否與資料庫成功連線。

        Returns:
            bool: 如果資料庫連線成功，回傳 True，否則回傳 False。
        """
        try:
            return self.cnx is not None and self.cnx.is_connected()
        except:
            return False

    def close_database(self):
        """關閉目前的資料庫連線，並將連線設為 None。"""
        if self.cnx:
            self.cnx.close()
            self.cnx = None

    def _get_database_name(self):
        """取得目前使用的資料庫名稱。

        Returns:
            str: 資料庫名稱。
        """
        sql = "SELECT DATABASE()"
        rows = self.select_record(sql)

        return rows[0]["DATABASE()"] if rows else None

    def _connect_to_db(self, **kwargs):
        """建立資料庫連線，並初始化資料庫。

        Args:
            **kwargs: 包含 host、user、password、database 等參數。
        """
        try:
            if not kwargs:
                config = configparser.ConfigParser()
                config.read(self.CONFIG_FILE)
                if "db" in config:
                    self.host = config["db"].get("host", self.host)
                    self.user = config["db"]["user"]
                    self.password = config["db"]["password"]
                    self.database = config["db"]["database"]
                    self.charset = config["db"]["charset"]
                    self.port = config["db"].getint("port", 3306)
                    self.engine = config["db"].get("engine", "MyISAM")
                else:
                    print(f"⚠️ 找不到 [db] 區段，設定檔位置：{self.CONFIG_FILE}")
                    self.cnx = None
                    return
            else:
                self.host = kwargs.get("host", self.host)
                self.user = kwargs["user"]
                self.password = kwargs["password"]
                self.database = kwargs["database"]
                self.charset = kwargs["charset"]
                self.port = kwargs.get("port", 3306)
                self.engine = kwargs.get("engine", "MyISAM")

            self._create_connection(use_db=False)
            self._initialize_database()
        except mysql.Error as err:
            print(f"Error: {err}")
            self.cnx = None
        self.timeout = 0

    def _create_connection(self, use_db=True):
        """建立與資料庫的實際連線。

        Args:
            use_db (bool): 是否指定資料庫名稱連線。
        """
        try:
            self.cnx = mysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database if use_db else None,
                charset=self.charset,
                port=self.port,
                buffered=True,
                collation=f"{self.charset}_general_ci",
            )
        except mysql.Error as err:
            print(f"Error: {err}")
            self.cnx = None

    def _initialize_database(self):
        """如果資料庫不存在則建立，並重新連線使用該資料庫。"""
        if self.cnx is None:
            print("Database connection not established.")
            return
        try:
            cursor = self.cnx.cursor()
            cursor.execute(f"""
                CREATE DATABASE IF NOT EXISTS `{self.database}`
                DEFAULT CHARACTER SET {self.charset} COLLATE {self.charset}_general_ci
            """)
            cursor.close()
            self.cnx.close()
            self._create_connection(use_db=True)
        except mysql.Error as err:
            print(f"Error: {err}")

    def get_cursor(self, dictionary=False, buffered=True):
        """取得 cursor，若失敗則嘗試重新連線最多 10 次。

        Args:
            dictionary (bool): 是否回傳 dict 格式。
            buffered (bool): 是否啟用 buffer 模式。

        Returns:
            MySQLCursor: 資料庫 cursor。
        """
        for _ in range(10):
            try:
                return self.cnx.cursor(dictionary=dictionary, buffered=buffered)
            except Exception:
                self._reconnect()
                time.sleep(0.1)

        return None

    def _reconnect(self):
        """關閉並重新連線資料庫，強制指定使用資料庫。"""
        if self.cnx:
            try:
                self.cnx.close()
            except Exception:
                pass

        try:
            self._create_connection(use_db=True)
        except Exception as e:
            print(f"❌ 無法重新連線至資料庫：{e}")
            self.cnx = None

    def create_table(self, table_name):
        """
        根據指定資料表名稱，從對應的 .sql 檔案讀取建表語法並建立資料表。

        此方法會：
        - 讀取 BASE_DIR/mysql/{table_name}.sql 檔案內容
        - 清除 UTF-8 BOM（若存在）
        - 自動修正或補上 ENGINE 與 CHARSET 設定
        - 逐條執行 SQL 指令建立資料表

        Args:
            table_name (str): 要建立的資料表名稱，對應的 SQL 檔案應為 {table_name}.sql。

        Raises:
            顯示 QMessageBox 錯誤訊息，如果發生檔案不存在、編碼錯誤或 SQL 執行錯誤。
        """
        table_file = os.path.join(BASE_DIR, DB_PATH, f"{table_name}.sql")
        try:
            with open(table_file, "r", encoding="utf-8") as db_table:
                sql = db_table.read()

            # 移除 BOM
            sql = string_utils.remove_bom(sql)

            # 逐條處理 SQL 指令
            final_statements = []
            for statement in sql.split(";"):
                statement = statement.strip()
                if not statement:
                    continue

                # 強制設定 ENGINE 與 CHARSET
                upper_stmt = statement.upper()
                if upper_stmt.startswith("CREATE TABLE"):
                    # 使用正則式替換 ENGINE 設定
                    statement = re.sub(
                        r"ENGINE\s*=\s*\w+",
                        f"ENGINE={self.engine}",
                        statement,
                        flags=re.IGNORECASE,
                    )
                    # 若未指定 ENGINE，則補上 ENGINE 與 CHARSET 設定
                    if "ENGINE=" not in statement.upper():
                        statement += (
                            f" ENGINE={self.engine} DEFAULT CHARSET={self.charset}"
                        )

                final_statements.append(statement)

            # 執行所有 SQL 語句
            cursor = self.cnx.cursor()
            for stmt in final_statements:
                cursor.execute(stmt)
            self.cnx.commit()

        except FileNotFoundError:
            self._show_error_message(
                "資料表檔案不存在", f"找不到資料表定義檔：{table_file}"
            )
        except UnicodeDecodeError:
            self._show_error_message(
                "編碼錯誤", f"無法解析檔案：{table_file}，請確認是否為 UTF-8 編碼。"
            )
        except mysql.connector.Error as err:
            self._show_error_message(
                "建表錯誤", f"建立資料表 {table_name} 時出現錯誤：\n{str(err)}"
            )
        finally:
            try:
                cursor.close()
            except:
                pass

    # def select_record(self, sql, dictionary=True):
    #     if not sql:
    #         return []

    #     retry_count = 2
    #     for attempt in range(retry_count):
    #         cursor = None
    #         try:
    #             cursor = self.get_cursor(dictionary)
    #             if cursor is None:
    #                 # 如果拿不到游標，嘗試重連後繼續下一次迴圈
    #                 self._reconnect()
    #                 continue

    #             cursor.execute(sql)
    #             result = cursor.fetchall()
    #             return result  # 成功拿到資料就回傳

    #         except Exception as e:
    #             print(f"SQL: {sql}")
    #             print(f"⚠️ 執行 SQL 失敗（第 {attempt + 1} 次）：{e}")
    #             self._reconnect()
    #         finally:
    #             # 這裡是你修正的核心：確保關閉時不會崩潰
    #             if cursor:
    #                 try:
    #                     # 檢查 self.cnx 是否還存在且連線中
    #                     if self.cnx and self.cnx.is_connected():
    #                         cursor.close()
    #                 except (ReferenceError, Exception):
    #                     # 徹底無視關閉游標時的任何異常
    #                     pass

    #     return []

    def select_record(self, sql, dictionary=True):
        if not sql:
            return []

        retry_count = 2
        for attempt in range(retry_count):
            cursor = None
            try:
                # 這裡會用到你寫的 get_cursor，它內建重連與 buffered=True
                cursor = self.get_cursor(dictionary=dictionary)

                if cursor is None:
                    continue

                cursor.execute(sql)
                result = cursor.fetchall()
                return result

            except Exception as e:
                # 記錄一下，方便以後回頭看方醫師那邊的網路或資料庫穩不穩定
                print(f"⚠️ SQL 執行失敗 (第 {attempt + 1} 次): {e}\nSQL: {sql}")
                self._reconnect()

            finally:
                # 這是防止 ReferenceError 的最後一道防線
                if cursor is not None:
                    try:
                        # 只有在連線還在且有效時才手動關閉
                        if (
                            hasattr(self, "cnx")
                            and self.cnx
                            and self.cnx.is_connected()
                        ):
                            cursor.close()
                    except (ReferenceError, Exception):
                        # 32位元環境下，如果弱引用失效，直接放手讓 GC 處理，不讓程式崩潰
                        pass

        return []

    def delete_record(self, table_name, primary_key, key_value):
        """刪除資料表中指定主鍵的紀錄。

        Args:
            table_name (str): 資料表名稱。
            primary_key (str): 主鍵欄位名稱。
            key_value (any): 要刪除的主鍵值。
        """
        sql = f"DELETE FROM {table_name} WHERE {primary_key} = %s"
        cursor = self.get_cursor(dictionary=True)
        try:
            cursor.execute(sql, (key_value,))
            self.cnx.commit()
        finally:
            cursor.close()

    def insert_record(self, table_name, fields, data):
        """新增一筆紀錄至指定資料表。

        Args:
            table_name (str): 資料表名稱。
            fields (list[str]): 欄位名稱列表。
            data (list): 欲新增的值。

        Returns:
            int: 自動遞增的主鍵 ID。
        """
        fields_list = ", ".join(fields)
        value_list = ", ".join(["%s"] * len(fields))
        sql = f"INSERT INTO {table_name} ({fields_list}) VALUES ({value_list})"
        string_utils.str_to_none(data)
        cursor = self.get_cursor(dictionary=True)
        try:
            cursor.execute(sql, data)
            self.cnx.commit()
        except Exception:
            self.cnx.rollback()
            raise
        finally:
            try:
                if cursor and self.cnx and self.cnx.is_connected():
                    cursor.close()
            except:
                pass

        return self.get_last_insert_id()

    def update_record(self, table_name, fields, primary_key, key_value, data):
        """更新指定主鍵的紀錄。

        Args:
            table_name (str): 資料表名稱。
            fields (list[str]): 欲更新的欄位名稱。
            primary_key (str): 主鍵欄位名稱。
            key_value (any): 主鍵值。
            data (list): 欲更新的欄位值。
        """
        assignment_list = ", ".join([f"{field} = %s" for field in fields])
        sql = f"UPDATE {table_name} SET {assignment_list} WHERE {primary_key} = %s"
        string_utils.str_to_none(data)

        cursor = self.get_cursor(dictionary=True)
        try:
            cursor.execute(sql, data + [key_value])
            self.cnx.commit()
        except Exception:
            self.cnx.rollback()
            raise
        finally:
            # 加入同樣的保護機制
            try:
                if cursor and self.cnx and self.cnx.is_connected():
                    cursor.close()
            except:
                pass

    def exec_sql(self, sql, auto_commit=True):
        """執行任意 SQL 語句（非查詢類），例如 INSERT、UPDATE、DELETE。

        Args:
            sql (str): 要執行的 SQL 語句。
            auto_commit (bool): 是否自動提交變更。
        """
        cursor = self.get_cursor(dictionary=True)
        try:
            cursor.execute(sql)
            if auto_commit:
                self.cnx.commit()
        finally:
            cursor.close()

    def begin_transaction(self):
        """開始一個資料庫交易（transaction）。"""
        if self.cnx:
            self.cnx.start_transaction()

    def commit(self):
        """提交目前交易。"""
        if self.cnx:
            self.cnx.commit()

    def rollback(self):
        """回復目前交易。"""
        if self.cnx:
            self.cnx.rollback()

    def get_last_insert_id(self):
        """取得最近一次插入的自動編號 ID。

        Returns:
            int: 最後插入的 ID。
        """
        row = self.select_record("SELECT LAST_INSERT_ID()")
        return row[0]["LAST_INSERT_ID()"] if row else None

    def get_last_auto_increment_key(self, table_name):
        """取得指定資料表的下一個自動編號值。

        Args:
            table_name (str): 資料表名稱。

        Returns:
            int: 下一個自動編號值。
        """
        sql = f'''
            SELECT AUTO_INCREMENT FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "{table_name}"
        '''
        row = self.select_record(sql)
        return row[0]["AUTO_INCREMENT"] if row else None

    def host_name(self):
        """取得目前連線的主機名稱。"""
        return self.host

    def database_name(self):
        """取得目前使用的資料庫名稱。"""
        return self.database

    def cursor(self):
        """取得預設 dictionary 格式的 cursor。"""
        return self.get_cursor(dictionary=True)

    def get_table_names(self):
        """取得目前資料庫內所有資料表名稱。

        Returns:
            list[str]: 資料表名稱列表。
        """
        rows = self.select_record("SHOW TABLES")
        return [list(row.values())[0] for row in rows]

    def ping(self):
        """測試資料庫連線是否仍有效，若中斷則自動重連。

        Returns:
            bool: 測試是否成功。
        """
        try:
            self.cnx.ping(reconnect=True, attempts=3, delay=2)
            return True
        except mysql.Error:
            return False

    def check_table_exists(self, table_name):
        """檢查資料表是否存在，不存在時自動建立並寫入預設資料。"""
        if "InsReply" in table_name:
            return
        if not self._is_table_exists(table_name):
            try:
                self.create_table(table_name)
            except Exception:
                pass

            db_utils.set_default_data(self, table_name)

    def _is_table_exists(self, table_name):
        sql = "SHOW TABLES LIKE %s"
        cursor = self.get_cursor()
        cursor.execute(sql, (table_name,))
        exists = cursor.fetchone()
        cursor.close()
        return bool(exists)

    def check_field_exists(self, table_name, alter_type, column, data_type):
        """檢查欄位是否存在，必要時自動建立或修改欄位型態。"""
        if isinstance(column, list) and len(column) == 2:
            search_column, new_column = column
        else:
            search_column = new_column = column

        sql = f'SHOW COLUMNS FROM {table_name} LIKE "{search_column}"'
        rows = self.select_record(sql)
        column_exists = bool(rows)
        field_match = (
            column_exists and string_utils.xstr(rows[0]["Field"]) == new_column
        )
        type_match = (
            column_exists
            and string_utils.xstr(rows[0]["Type"]).lower() == data_type.lower()
        )
        if (alter_type == "add" and column_exists) or (
            alter_type in ["change", "modify"]
            and (not column_exists or (field_match and type_match))
        ):
            return

        try:
            self.kill_sleep_connections()
        except Exception:
            pass

        if alter_type == "add":
            sql = f"ALTER TABLE {table_name} ADD {column} {data_type}"
        elif alter_type == "change":
            sql = f"ALTER TABLE {table_name} CHANGE {search_column} {new_column} {data_type}"
        elif alter_type == "modify":
            sql = f"ALTER TABLE {table_name} MODIFY {new_column} {data_type}"
        self.exec_sql(sql)

    def kill_sleep_connections(self, threshold=60):
        """
        殺掉所有與本資料庫有關、且閒置時間超過 threshold 秒的 Sleep 連線。

        Args:
            threshold (int): 超過這個秒數的 Sleep 連線會被終止，預設為 60 秒。
        """
        cursor = self.get_cursor(dictionary=True, buffered=True)

        try:
            # 取得目前連線的 ID（避免自殺）
            cursor.execute("SELECT CONNECTION_ID()")
            my_id = cursor.fetchone()["CONNECTION_ID()"]

            # 取得所有連線狀態
            cursor.execute("SHOW PROCESSLIST")
            processlist = cursor.fetchall()

            for row in processlist:
                if (
                    row["Command"] == "Sleep"
                    and row["Time"] > threshold
                    and row["Id"] != my_id
                    and row.get("db")
                    in (self.database, None)  # 確保是連到同一個資料庫或未指定的資料庫
                ):
                    process_id = row["Id"]
                    print(
                        f"🔪 Killing sleep connection: ID {process_id}, User: {row['User']}, Host: {row['Host']}"
                    )
                    try:
                        kill_cursor = self.get_cursor(dictionary=True, buffered=True)
                        kill_cursor.execute(f"KILL {process_id}")
                        kill_cursor.close()
                    except Exception as e:
                        print(f"❌ 無法刪除 ID {process_id}: {e}")
        finally:
            cursor.close()

    def add_index_if_not_exists(self, table_name, index_name, fields):
        """
        動態檢查並建立索引
        :param table_name: 資料表名稱
        :param index_name: 索引名稱
        :param fields: 欄位串列, 例如 ['MedicineSet', 'CaseDate']
        """
        # 1. 檢查索引是否存在
        check_sql = f"""
            SELECT COUNT(*) as total FROM information_schema.STATISTICS 
            WHERE table_schema = DATABASE() 
            AND table_name = '{table_name}' 
            AND index_name = '{index_name}'
        """

        res = self.select_record(check_sql)

        # 2. 如果不存在則執行建立
        if res and res[0].get("total", 0) == 0:
            # 使用 join 處理欄位，避免 tuple 單一元素時出現的末尾逗號問題
            field_str = ", ".join([f"`{f}`" for f in fields])
            create_sql = (
                f"ALTER TABLE `{table_name}` ADD INDEX `{index_name}` ({field_str})"
            )

            print(f"正在建立索引：{index_name} -> {table_name}({field_str})")
            self.exec_sql(create_sql)
        else:
            # print(f"索引 {index_name} 已存在，跳過。")
            pass
