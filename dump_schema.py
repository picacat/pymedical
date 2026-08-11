#!/usr/bin/env python3
"""
dump_schema.py - 只匯出資料表結構（不含資料），逐表一個 .sql 檔

用途：
    取得來源資料庫的完整結構定義，用來在新機器 / 新伺服器上
    建立一個結構相同但完全空白的資料庫。

輸出結構（與 dump_database.py 一致的時間戳記子目錄）：
    <輸出目錄>/<資料庫>_schema_YYYYMMDD_HHMMSS/
        00_manifest.txt      清單與選項記錄
        00_schema.sql        CREATE DATABASE（僅在勾選時產生）
        <資料表>.sql          每張表一個檔
        zz_views.sql         檢視表
        zz_triggers.sql      觸發程序
        zz_routines.sql      預存程序與函式
        99_import_all.sql    一次匯入全部的 source 清單

特點：
    - 不依賴 mysqldump，直接用 SHOW CREATE TABLE 取得 DDL
    - 可選擇強制 InnoDB ROW_FORMAT=DYNAMIC
    - 可選擇強制 utf8mb4 / utf8mb4_general_ci（含欄位層級，避免 uca1400）
    - 自動移除 AUTO_INCREMENT 起始值與 DEFINER
    - 遇到孤兒資料表（錯誤 1932）只記錄警告，不中斷
    - 產出的 SQL 完全不含 DROP 陳述式
    - 目標資料庫預設為「來源名稱_new」，不會指向來源資料庫本身
    - CREATE DATABASE / CREATE TABLE 都不加 IF NOT EXISTS，
      目標若已存在會直接停在錯誤 1007 / 1050，不會寫進既有的資料庫

搭配工具：dump_database.py（含資料備份）、restore_sql.py（還原）、
         convert_innodb.py（MyISAM → InnoDB 轉換）
"""

import os
import re
import sys
import traceback
from datetime import datetime

import mysql.connector
from PyQt5 import QtCore, QtGui, QtWidgets

APP_NAME = "資料表結構匯出工具"
APP_VERSION = "1.3"

TARGET_CHARSET = "utf8mb4"
TARGET_COLLATION = "utf8mb4_general_ci"

# InnoDB 索引前綴上限 3072 bytes，utf8mb4 每字元 4 bytes
MAX_INDEX_CHARS = 768


def monospace_font():
    font = QtGui.QFont("Consolas" if sys.platform == "win32" else "Monospace", 9)
    font.setStyleHint(QtGui.QFont.TypeWriter)
    return font


def safe_file_name(name):
    """資料表名稱轉成安全的檔名"""
    return re.sub(r"[^\w\-.]", "_", name)


# ----------------------------------------------------------------------
# DDL 改寫
# ----------------------------------------------------------------------
def strip_auto_increment(ddl):
    """移除 AUTO_INCREMENT=1234 起始值（新資料庫從 1 開始）"""
    return re.sub(r"\s+AUTO_INCREMENT=\d+", "", ddl)


def strip_definer(ddl):
    """移除 DEFINER=`user`@`host`，避免目標機器沒有該帳號"""
    return re.sub(r"\s*DEFINER=[^\s]+\s*", " ", ddl)


def force_innodb(ddl):
    """ENGINE 一律改為 InnoDB，ROW_FORMAT 一律改為 DYNAMIC"""
    ddl = re.sub(r"ENGINE=\w+", "ENGINE=InnoDB", ddl)

    if "ENGINE=InnoDB" not in ddl:  # 原本就沒有 ENGINE=
        ddl = re.sub(r"\)\s*(DEFAULT CHARSET)", r") ENGINE=InnoDB \1", ddl)

    if re.search(r"ROW_FORMAT=\w+", ddl):  # 原本是 COMPACT / FIXED 等
        ddl = re.sub(r"ROW_FORMAT=\w+", "ROW_FORMAT=DYNAMIC", ddl)
    else:
        ddl = ddl.replace("ENGINE=InnoDB", "ENGINE=InnoDB ROW_FORMAT=DYNAMIC")

    return ddl


def force_utf8mb4(ddl):
    """
    字元集與 collation 全面正規化。
    欄位層級與資料表層級都要處理，且 DEFAULT CHARSET 一定要帶 COLLATE，
    否則在 MariaDB 11.4+ 會拿到 uca1400 預設值。
    """
    # 欄位層級
    ddl = re.sub(r"CHARACTER SET \w+", "CHARACTER SET %s" % TARGET_CHARSET, ddl)
    ddl = re.sub(r"COLLATE (\w+)", "COLLATE %s" % TARGET_COLLATION, ddl)

    # 資料表層級
    ddl = re.sub(r"DEFAULT CHARSET=\w+", "DEFAULT CHARSET=%s" % TARGET_CHARSET, ddl)
    ddl = re.sub(r"COLLATE=\w+", "COLLATE=%s" % TARGET_COLLATION, ddl)

    # DEFAULT CHARSET 後面沒接 COLLATE= 的，補上
    if "COLLATE=" not in ddl:
        ddl = ddl.replace(
            "DEFAULT CHARSET=%s" % TARGET_CHARSET,
            "DEFAULT CHARSET=%s COLLATE=%s" % (TARGET_CHARSET, TARGET_COLLATION),
        )

    return ddl


# ----------------------------------------------------------------------
# 工作執行緒
# ----------------------------------------------------------------------
class DumpWorker(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    progress_signal = QtCore.pyqtSignal(int, int)
    finished_signal = QtCore.pyqtSignal(bool, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.database = None
        self.cursor = None
        self.out_path = ""

    # ------------------------------------------------------------------
    def log(self, message):
        self.log_signal.emit(message)

    def connect_database(self):
        self.database = mysql.connector.connect(
            host=self.config["host"],
            port=self.config["port"],
            user=self.config["user"],
            password=self.config["password"],
            database=self.config["database"],
            charset=TARGET_CHARSET,
            collation=TARGET_COLLATION,  # 不指定會被送出 utf8mb4_0900_ai_ci
        )
        self.cursor = self.database.cursor()

    def close_database(self):
        try:
            if self.cursor is not None:
                self.cursor.close()
            if self.database is not None and self.database.is_connected():
                self.database.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 查詢
    # ------------------------------------------------------------------
    def get_objects(self):
        """回傳 (base_tables, views)"""
        self.cursor.execute(
            """
            SELECT TABLE_NAME, TABLE_TYPE
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_TYPE, TABLE_NAME
        """,
            (self.config["database"],),
        )

        tables, views = [], []
        for name, table_type in self.cursor.fetchall():
            if table_type == "BASE TABLE":
                tables.append(name)
            elif table_type == "VIEW":
                views.append(name)

        return tables, views

    def get_database_charset(self):
        self.cursor.execute(
            """
            SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME = %s
        """,
            (self.config["database"],),
        )
        row = self.cursor.fetchone()
        return (row[0], row[1]) if row else (TARGET_CHARSET, TARGET_COLLATION)

    def get_column_count(self, table):
        self.cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """,
            (self.config["database"], table),
        )
        return self.cursor.fetchone()[0]

    def find_long_index_columns(self, table):
        """
        找出被索引、且長度足以在 utf8mb4 下超過 InnoDB 索引上限的字串欄位。
        只回報，不修改——由使用者決定怎麼處理。
        """
        self.cursor.execute(
            """
            SELECT DISTINCT s.COLUMN_NAME, c.CHARACTER_MAXIMUM_LENGTH
            FROM information_schema.STATISTICS s
            JOIN information_schema.COLUMNS c
              ON  c.TABLE_SCHEMA = s.TABLE_SCHEMA
              AND c.TABLE_NAME   = s.TABLE_NAME
              AND c.COLUMN_NAME  = s.COLUMN_NAME
            WHERE s.TABLE_SCHEMA = %s
              AND s.TABLE_NAME = %s
              AND s.SUB_PART IS NULL
              AND c.CHARACTER_MAXIMUM_LENGTH > %s
        """,
            (self.config["database"], table, MAX_INDEX_CHARS),
        )
        return self.cursor.fetchall()

    def get_table_ddl(self, table):
        self.cursor.execute("SHOW CREATE TABLE `%s`" % table)
        return self.cursor.fetchone()[1]

    def get_view_ddl(self, view):
        self.cursor.execute("SHOW CREATE VIEW `%s`" % view)
        return self.cursor.fetchone()[1]

    def get_triggers(self):
        self.cursor.execute(
            """
            SELECT TRIGGER_NAME
            FROM information_schema.TRIGGERS
            WHERE TRIGGER_SCHEMA = %s
            ORDER BY TRIGGER_NAME
        """,
            (self.config["database"],),
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_trigger_ddl(self, trigger):
        self.cursor.execute("SHOW CREATE TRIGGER `%s`" % trigger)
        return self.cursor.fetchone()[2]

    def get_routines(self):
        self.cursor.execute(
            """
            SELECT ROUTINE_NAME, ROUTINE_TYPE
            FROM information_schema.ROUTINES
            WHERE ROUTINE_SCHEMA = %s
            ORDER BY ROUTINE_TYPE, ROUTINE_NAME
        """,
            (self.config["database"],),
        )
        return self.cursor.fetchall()

    def get_routine_ddl(self, name, routine_type):
        self.cursor.execute("SHOW CREATE %s `%s`" % (routine_type, name))
        return self.cursor.fetchone()[2]

    # ------------------------------------------------------------------
    # 輸出
    # ------------------------------------------------------------------
    def transform(self, ddl):
        ddl = strip_auto_increment(ddl)

        if self.config["force_innodb"]:
            ddl = force_innodb(ddl)

        if self.config["force_utf8mb4"]:
            ddl = force_utf8mb4(ddl)

        return ddl

    def file_header(self, title):
        return (
            "-- ------------------------------------------------------------\n"
            "-- %s\n"
            "-- 來源: %s:%s / %s\n"
            "-- 產生: %s v%s  %s\n"
            "-- ------------------------------------------------------------\n\n"
            "-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，\n"
            "-- 匯入會停在錯誤 1050 (Table already exists)。\n\n"
            "SET NAMES %s;\n"
            "SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;\n\n"
            % (
                title,
                self.config["host"],
                self.config["port"],
                self.config["database"],
                APP_NAME,
                APP_VERSION,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                TARGET_CHARSET,
            )
        )

    def file_footer(self):
        return "\nSET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;\n"

    def write_file(self, file_name, title, body):
        full_path = os.path.join(self.out_path, file_name)
        with open(full_path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(self.file_header(title))
            fp.write(body)
            fp.write(self.file_footer())
        return full_path

    def write_create_database(self, db_charset, db_collation):
        target_db = self.config["target_database"]

        if self.config["force_utf8mb4"]:
            charset, collation = TARGET_CHARSET, TARGET_COLLATION
        else:
            charset, collation = db_charset, db_collation

        body = (
            "-- 目標資料庫若已存在，此處會停在錯誤 1007，這是刻意的保護。\n"
            "-- 確定要重建時，請自行在 client 端處理既有的資料庫。\n\n"
            "CREATE DATABASE `%s`\n"
            "    DEFAULT CHARACTER SET %s\n"
            "    DEFAULT COLLATE %s;\n\n"
            "USE `%s`;\n" % (target_db, charset, collation, target_db)
        )

        self.write_file("00_schema.sql", "建立資料庫 %s" % target_db, body)

    def write_import_all(self, file_names):
        full_path = os.path.join(self.out_path, "99_import_all.sql")

        with open(full_path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(
                "-- ------------------------------------------------------------\n"
            )
            fp.write("-- 一次匯入全部結構\n")
            fp.write("--\n")
            fp.write("-- 用法（需先切換到本目錄）：\n")
            if self.config["create_database"]:
                fp.write("--     mysql -u root -p < 99_import_all.sql\n")
            else:
                fp.write("--     mysql -u root -p 目標資料庫 < 99_import_all.sql\n")
            fp.write(
                "-- ------------------------------------------------------------\n\n"
            )
            fp.write("SET NAMES %s;\n" % TARGET_CHARSET)
            fp.write(
                "SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n"
            )
            fp.write(
                "SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;\n"
            )
            fp.write("SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;\n\n")

            fp.writelines("source %s\n" % file_name for file_name in file_names)

            fp.write("\nSET SQL_MODE=@OLD_SQL_MODE;\n")
            fp.write("SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;\n")
            fp.write("SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;\n")

    def write_manifest(self, entries, skipped, warnings, db_charset, db_collation):
        full_path = os.path.join(self.out_path, "00_manifest.txt")

        with open(full_path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write("%s v%s\n" % (APP_NAME, APP_VERSION))
            fp.write("只含結構，不含任何資料\n\n")
            fp.write("產生時間  : %s\n" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            fp.write("來源主機  : %s:%s\n" % (self.config["host"], self.config["port"]))
            fp.write(
                "來源資料庫: %s (%s / %s)\n"
                % (self.config["database"], db_charset, db_collation)
            )
            fp.write("目標資料庫: %s\n" % self.config["target_database"])
            fp.write(
                "引擎      : %s\n"
                % (
                    "強制 InnoDB ROW_FORMAT=DYNAMIC"
                    if self.config["force_innodb"]
                    else "沿用來源"
                )
            )
            fp.write(
                "字元集    : %s\n"
                % (
                    "強制 %s / %s" % (TARGET_CHARSET, TARGET_COLLATION)
                    if self.config["force_utf8mb4"]
                    else "沿用來源"
                )
            )
            fp.write("資料表數  : %s\n" % len(entries))
            fp.write("DROP 陳述: 無（全部檔案皆不含 DROP）\n\n")

            fp.write("%-40s %-40s %s\n" % ("資料表", "檔案", "欄位數"))
            fp.write("%s\n" % ("-" * 90))
            fp.writelines(
                "%-40s %-40s %s\n" % (table, file_name, columns)
                for table, file_name, columns in entries
            )

            if skipped:
                fp.write("\n略過的資料表（錯誤 1932 多為孤兒資料表）:\n")
                fp.writelines("    %s\n" % item for item in skipped)

            if warnings:
                fp.write("\n索引長度警告（utf8mb4 下可能超過 3072 bytes 上限）:\n")
                fp.writelines("    %s\n" % item for item in warnings)

    # ------------------------------------------------------------------
    def run(self):
        try:
            self.log(
                "連線 %s:%s / %s ..."
                % (self.config["host"], self.config["port"], self.config["database"])
            )
            self.connect_database()

            db_charset, db_collation = self.get_database_charset()
            self.log("來源資料庫字元集: %s / %s" % (db_charset, db_collation))

            tables, views = self.get_objects()
            self.log("共 %s 張資料表、%s 個檢視表" % (len(tables), len(views)))

            dir_name = "%s_schema_%s" % (
                self.config["database"],
                datetime.now().strftime("%Y%m%d_%H%M%S"),
            )
            self.out_path = os.path.join(self.config["output_path"], dir_name)
            os.makedirs(self.out_path)
            self.log("輸出目錄: %s" % self.out_path)
            self.log("")

            import_list = []
            entries = []
            skipped = []
            warnings = []
            done = 0
            total = len(tables) + len(views)

            # ---------- 00_schema.sql ----------
            if self.config["create_database"]:
                self.write_create_database(db_charset, db_collation)
                import_list.append("00_schema.sql")
                self.log("  00_schema.sql")

            # ---------- 逐表一檔 ----------
            used_names = set()

            for table in tables:
                try:
                    ddl = self.get_table_ddl(table)
                except mysql.connector.Error as e:
                    # 1932: .frm 存在但引擎裡沒有實體（孤兒資料表）
                    skipped.append("%s (錯誤 %s)" % (table, e.errno))
                    self.log("  [略過] %s → 錯誤 %s" % (table, e.errno))
                    done += 1
                    self.progress_signal.emit(done, total)
                    continue

                ddl = self.transform(ddl)

                if self.config["force_utf8mb4"]:
                    for column, length in self.find_long_index_columns(table):
                        warnings.append("%s.%s 長度 %s" % (table, column, length))

                # 檔名衝突處理（大小寫不同的表名在 Windows 上會撞檔）
                file_name = "%s.sql" % safe_file_name(table)
                if file_name.lower() in used_names:
                    file_name = "%s__%s.sql" % (safe_file_name(table), len(used_names))
                used_names.add(file_name.lower())

                body = "%s;\n" % ddl

                self.write_file(file_name, "資料表 %s" % table, body)

                import_list.append(file_name)
                entries.append((table, file_name, self.get_column_count(table)))

                done += 1
                self.log("  %s" % file_name)
                self.progress_signal.emit(done, total)

            # ---------- 檢視表 ----------
            if views and self.config["include_views"]:
                body = ""
                for view in views:
                    try:
                        ddl = strip_definer(self.get_view_ddl(view))
                    except mysql.connector.Error as e:
                        skipped.append("%s (檢視表, 錯誤 %s)" % (view, e.errno))
                        self.log("  [略過] 檢視表 %s → 錯誤 %s" % (view, e.errno))
                        done += 1
                        self.progress_signal.emit(done, total)
                        continue

                    body += "%s;\n\n" % ddl
                    done += 1
                    self.progress_signal.emit(done, total)

                if body:
                    self.write_file("zz_views.sql", "檢視表 (VIEW)", body)
                    import_list.append("zz_views.sql")
                    self.log("  zz_views.sql (%s 個)" % len(views))

            # ---------- 觸發程序 ----------
            if self.config["include_triggers"]:
                triggers = self.get_triggers()
                if triggers:
                    body = "DELIMITER ;;\n\n"
                    for trigger in triggers:
                        ddl = strip_definer(self.get_trigger_ddl(trigger))
                        body += "%s;;\n\n" % ddl
                    body += "DELIMITER ;\n"

                    self.write_file("zz_triggers.sql", "觸發程序 (TRIGGER)", body)
                    import_list.append("zz_triggers.sql")
                    self.log("  zz_triggers.sql (%s 個)" % len(triggers))

            # ---------- 預存程序 / 函式 ----------
            if self.config["include_routines"]:
                routines = self.get_routines()
                if routines:
                    body = "DELIMITER ;;\n\n"
                    for name, routine_type in routines:
                        ddl = strip_definer(self.get_routine_ddl(name, routine_type))
                        body += "%s;;\n\n" % ddl
                    body += "DELIMITER ;\n"

                    self.write_file("zz_routines.sql", "預存程序與函式", body)
                    import_list.append("zz_routines.sql")
                    self.log("  zz_routines.sql (%s 個)" % len(routines))

            # ---------- 清單檔 ----------
            if self.config["import_all"]:
                self.write_import_all(import_list)
                self.log("  99_import_all.sql")

            self.write_manifest(entries, skipped, warnings, db_charset, db_collation)
            self.log("  00_manifest.txt")

            # ---------- 摘要 ----------
            self.log("")
            self.log("匯出完成: %s 張資料表" % len(entries))
            self.log("輸出目錄: %s" % self.out_path)

            if skipped:
                self.log("")
                self.log("略過 %s 項（多半是孤兒資料表，錯誤 1932）:" % len(skipped))
                for item in skipped:
                    self.log("    %s" % item)

            if warnings:
                self.log("")
                self.log("注意：以下欄位轉 utf8mb4 後索引可能超過 3072 bytes 上限，")
                self.log("      建議改用前綴索引或縮短欄位長度：")
                for item in warnings:
                    self.log("    %s" % item)

            self.finished_signal.emit(True, self.out_path)

        except Exception as e:
            self.log("")
            self.log("發生錯誤: %s" % e)
            self.log(traceback.format_exc())
            self.finished_signal.emit(False, str(e))

        finally:
            self.close_database()


# ----------------------------------------------------------------------
# 主視窗
# ----------------------------------------------------------------------
class DumpSchema(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.last_out_path = ""
        self.settings = QtCore.QSettings("pymedical", "dump_schema")
        self._init_ui()
        self._load_settings()

    # ------------------------------------------------------------------
    def _init_ui(self):
        self.setWindowTitle("%s v%s" % (APP_NAME, APP_VERSION))
        self.resize(780, 680)

        layout = QtWidgets.QVBoxLayout(self)

        # ---------- 連線設定 ----------
        conn_group = QtWidgets.QGroupBox("來源資料庫")
        conn_layout = QtWidgets.QGridLayout(conn_group)

        self.host_edit = QtWidgets.QLineEdit("localhost")
        self.port_edit = QtWidgets.QLineEdit("3306")
        self.user_edit = QtWidgets.QLineEdit("root")
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.database_combo = QtWidgets.QComboBox()
        self.database_combo.setEditable(True)

        self.list_button = QtWidgets.QPushButton("讀取資料庫清單")
        self.list_button.clicked.connect(self.list_databases)

        conn_layout.addWidget(QtWidgets.QLabel("主機"), 0, 0)
        conn_layout.addWidget(self.host_edit, 0, 1)
        conn_layout.addWidget(QtWidgets.QLabel("連接埠"), 0, 2)
        conn_layout.addWidget(self.port_edit, 0, 3)
        conn_layout.addWidget(QtWidgets.QLabel("帳號"), 1, 0)
        conn_layout.addWidget(self.user_edit, 1, 1)
        conn_layout.addWidget(QtWidgets.QLabel("密碼"), 1, 2)
        conn_layout.addWidget(self.password_edit, 1, 3)
        conn_layout.addWidget(QtWidgets.QLabel("資料庫"), 2, 0)
        conn_layout.addWidget(self.database_combo, 2, 1)
        conn_layout.addWidget(self.list_button, 2, 3)

        layout.addWidget(conn_group)

        # ---------- 輸出設定 ----------
        out_group = QtWidgets.QGroupBox("輸出設定")
        out_layout = QtWidgets.QGridLayout(out_group)

        self.output_edit = QtWidgets.QLineEdit(os.path.expanduser("~"))
        browse_button = QtWidgets.QPushButton("瀏覽...")
        browse_button.clicked.connect(self.browse_output_path)

        self.target_edit = QtWidgets.QLineEdit()
        self.target_edit.setPlaceholderText("留白則使用「來源名稱_new」")
        self.database_combo.currentTextChanged.connect(self._suggest_target_name)

        out_layout.addWidget(QtWidgets.QLabel("輸出目錄"), 0, 0)
        out_layout.addWidget(self.output_edit, 0, 1)
        out_layout.addWidget(browse_button, 0, 2)
        out_layout.addWidget(QtWidgets.QLabel("新資料庫名稱"), 1, 0)
        out_layout.addWidget(self.target_edit, 1, 1)

        layout.addWidget(out_group)

        # ---------- 選項 ----------
        opt_group = QtWidgets.QGroupBox("選項")
        opt_layout = QtWidgets.QGridLayout(opt_group)

        self.create_database_check = QtWidgets.QCheckBox(
            "產生 00_schema.sql（CREATE DATABASE）"
        )
        self.create_database_check.setChecked(True)
        self.import_all_check = QtWidgets.QCheckBox("產生 99_import_all.sql")
        self.import_all_check.setChecked(True)
        self.innodb_check = QtWidgets.QCheckBox("強制 ENGINE=InnoDB ROW_FORMAT=DYNAMIC")
        self.innodb_check.setChecked(True)
        self.utf8mb4_check = QtWidgets.QCheckBox(
            "強制 %s / %s" % (TARGET_CHARSET, TARGET_COLLATION)
        )
        self.utf8mb4_check.setChecked(True)
        self.views_check = QtWidgets.QCheckBox("包含檢視表 (VIEW)")
        self.views_check.setChecked(True)
        self.triggers_check = QtWidgets.QCheckBox("包含觸發程序 (TRIGGER)")
        self.routines_check = QtWidgets.QCheckBox("包含預存程序與函式")

        opt_layout.addWidget(self.create_database_check, 0, 0)
        opt_layout.addWidget(self.innodb_check, 0, 1)
        opt_layout.addWidget(self.import_all_check, 1, 0)
        opt_layout.addWidget(self.utf8mb4_check, 1, 1)
        opt_layout.addWidget(self.views_check, 2, 1)
        opt_layout.addWidget(self.triggers_check, 3, 1)
        opt_layout.addWidget(self.routines_check, 4, 1)

        layout.addWidget(opt_group)

        # ---------- 執行 ----------
        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("開始匯出")
        self.start_button.setMinimumHeight(34)
        self.start_button.clicked.connect(self.start_dump)
        self.open_button = QtWidgets.QPushButton("開啟輸出目錄")
        self.open_button.clicked.connect(self.open_output_path)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.open_button)
        layout.addLayout(button_layout)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(monospace_font())
        layout.addWidget(self.log_text)

    # ------------------------------------------------------------------
    def _load_settings(self):
        self.host_edit.setText(self.settings.value("host", "localhost"))
        self.port_edit.setText(self.settings.value("port", "3306"))
        self.user_edit.setText(self.settings.value("user", "root"))
        self.output_edit.setText(
            self.settings.value("output_path", os.path.expanduser("~"))
        )
        database = self.settings.value("database", "")
        if database:
            self.database_combo.addItem(database)

    def _save_settings(self):
        self.settings.setValue("host", self.host_edit.text())
        self.settings.setValue("port", self.port_edit.text())
        self.settings.setValue("user", self.user_edit.text())
        self.settings.setValue("database", self.database_combo.currentText())
        self.settings.setValue("output_path", self.output_edit.text())

    # ------------------------------------------------------------------
    def append_log(self, message):
        self.log_text.appendPlainText(message)

    def _suggest_target_name(self, database_name):
        """來源資料庫換了就重新建議目標名稱，避免沿用上一個庫的名字"""
        current = self.target_edit.text().strip()
        if not current or current.endswith("_new"):
            self.target_edit.setText("%s_new" % database_name if database_name else "")

    def browse_output_path(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "選擇輸出目錄", self.output_edit.text()
        )
        if path:
            self.output_edit.setText(path)

    def open_output_path(self):
        path = self.last_out_path or self.output_edit.text()
        if os.path.isdir(path):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

    def list_databases(self):
        try:
            database = mysql.connector.connect(
                host=self.host_edit.text(),
                port=int(self.port_edit.text()),
                user=self.user_edit.text(),
                password=self.password_edit.text(),
                charset=TARGET_CHARSET,
                collation=TARGET_COLLATION,
            )
            cursor = database.cursor()
            cursor.execute("""
                SELECT SCHEMA_NAME FROM information_schema.SCHEMATA
                WHERE SCHEMA_NAME NOT IN
                    ('information_schema', 'mysql', 'performance_schema', 'sys')
                ORDER BY SCHEMA_NAME
            """)

            current = self.database_combo.currentText()
            self.database_combo.clear()
            self.database_combo.addItems([row[0] for row in cursor.fetchall()])
            if current:
                self.database_combo.setCurrentText(current)

            cursor.close()
            database.close()
            self.append_log("已讀取 %s 個資料庫" % self.database_combo.count())

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "連線失敗", str(e))

    # ------------------------------------------------------------------
    def start_dump(self):
        database_name = self.database_combo.currentText().strip()

        if not database_name:
            QtWidgets.QMessageBox.warning(self, "提醒", "請選擇來源資料庫")
            return

        if not os.path.isdir(self.output_edit.text()):
            QtWidgets.QMessageBox.warning(self, "提醒", "輸出目錄不存在")
            return

        target_database = self.target_edit.text().strip() or "%s_new" % database_name

        if target_database == database_name:
            reply = QtWidgets.QMessageBox.warning(
                self,
                "目標與來源同名",
                "目標資料庫名稱與來源相同（%s）。\n\n"
                "00_schema.sql 裡的 USE 會指向來源資料庫本身，\n"
                "建議改成別的名稱。仍要繼續嗎？" % database_name,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        config = {
            "host": self.host_edit.text().strip(),
            "port": int(self.port_edit.text().strip() or 3306),
            "user": self.user_edit.text().strip(),
            "password": self.password_edit.text(),
            "database": database_name,
            "target_database": target_database,
            "output_path": self.output_edit.text().strip(),
            "create_database": self.create_database_check.isChecked(),
            "import_all": self.import_all_check.isChecked(),
            "force_innodb": self.innodb_check.isChecked(),
            "force_utf8mb4": self.utf8mb4_check.isChecked(),
            "include_views": self.views_check.isChecked(),
            "include_triggers": self.triggers_check.isChecked(),
            "include_routines": self.routines_check.isChecked(),
        }

        self._save_settings()

        self.log_text.clear()
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = DumpWorker(config)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.dump_finished)
        self.worker.start()

    def update_progress(self, done, total):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(done)

    def dump_finished(self, success, message):
        self.start_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        if success:
            self.last_out_path = message
            QtWidgets.QMessageBox.information(
                self, "完成", "結構已匯出至:\n%s" % message
            )
        else:
            QtWidgets.QMessageBox.critical(self, "失敗", message)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            reply = QtWidgets.QMessageBox.question(
                self,
                "確認",
                "匯出尚未結束，確定要關閉？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                event.ignore()
                return

        self._save_settings()
        event.accept()


# ----------------------------------------------------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    window = DumpSchema()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
