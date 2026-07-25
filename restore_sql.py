# -*- coding: utf-8 -*-
"""
逐表 SQL 備份還原工具（GUI 版）

與 convert_gui.py 相同的介面風格與安全原則：
  1. 每個 .sql 檔的匯入結果逐一檢查，任何失敗立即記錄並在
     結束時明確列出——還原工具絕不假裝成功。
  2. 密碼透過 MYSQL_PWD 環境變數傳遞，不出現在命令列與程序列表。
  3. 目標資料庫已存在且含資料表時，開始前顯示現況並要求明確確認
     （備份檔中的 DROP TABLE 會覆蓋同名資料表）。
  4. 「備份檔編碼」須與備份檔當初匯出的編碼一致（告訴伺服器檔案內
     位元組的編碼），與最終想要的字元集是兩回事。
  5. 可選「還原後轉換為 utf8mb4」：照備份檔原編碼忠實匯入後，
     先逐欄做無損轉換檢查（同義異碼視為正規化放行、真正有損則停止），
     通過後由伺服器端 ALTER 轉換——與 convert_gui 相同的檢查邏輯。
  6. 資料引擎可選（預設 MyISAM）。先照備份檔原樣匯入，全部成功後，
     凡引擎與選擇不符的表逐張由伺服器端 ALTER 轉換。
  7. 還原後核對資料表數量、引擎分佈與字元集。
"""

import configparser
import os
import re
import shutil
import subprocess
import sys
import time

import mysql.connector
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

CHARSET_CHOICES = ["自動偵測", "utf8mb4", "utf8mb3", "utf8", "big5", "latin1"]
ENGINE_CHOICES = ["MyISAM", "InnoDB"]
TARGET_COLLATION = "utf8mb4_unicode_ci"


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------


def find_tool(*candidates):
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def subprocess_flags():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def detect_sql_charset(folder, sql_files, max_files=3, sample_bytes=4 * 1024 * 1024):
    """
    偵測 .sql 備份檔的內容編碼。回傳 (charset, 說明) 或 (None, 原因)。
    判斷順序：
      1. 檔頭的 SET NAMES 聲明（mysqldump 標準檔頭，最權威）。
      2. UTF-8 BOM。
      3. 位元組結構：整份樣本能以嚴格 UTF-8 解碼 → utf8mb4；
         否則能以 cp950（Big5 的 Windows 超集）解碼 → big5。
    純 ASCII 內容會被判為 utf8mb4，選任何編碼匯入結果皆相同，無影響。
    """
    samples = []
    for name in sql_files[:max_files]:
        try:
            with open(os.path.join(folder, name), "rb") as f:
                data = f.read(sample_bytes)
        except OSError:
            continue
        m = re.search(rb"SET NAMES (\w+)", data)
        if m:
            cs = m.group(1).decode("ascii", errors="replace")
            return cs, f"{name} 檔頭聲明 SET NAMES {cs}"
        samples.append((name, data))

    if not samples:
        return None, "讀不到任何檔案內容"

    joined = b"".join(d for _, d in samples)
    if joined.startswith(b"\xef\xbb\xbf"):
        return "utf8mb4", "檔案帶有 UTF-8 BOM"
    try:
        # 去掉樣本尾端可能被截斷的多位元組字元再驗證
        joined[:-4].decode("utf-8")
        return "utf8mb4", "內容為有效的 UTF-8 位元組序列"
    except UnicodeDecodeError:
        pass
    try:
        joined[:-2].decode("cp950")
        return "big5", "內容符合 Big5 位元組結構"
    except UnicodeDecodeError:
        pass
    return None, "位元組結構不符合 UTF-8 也不符合 Big5"


# ---------------------------------------------------------------------------
# 背景工作執行緒
# ---------------------------------------------------------------------------


class RestoreWorker(QObject):
    sig_log = pyqtSignal(str)
    sig_progress = pyqtSignal(int, int)
    sig_finished = pyqtSignal(bool, str)

    def __init__(self, params):
        super().__init__()
        self.p = params

    def log(self, msg):
        self.sig_log.emit(msg)

    def run(self):
        conn = None
        try:
            p = self.p
            db = p["database"]
            file_charset = p["file_charset"]
            engine = p["engine"]
            to_utf8mb4 = p["to_utf8mb4"]

            sql_files = sorted(
                f for f in os.listdir(p["sql_folder"]) if f.endswith(".sql")
            )
            total = len(sql_files)
            if total == 0:
                raise RuntimeError("指定目錄中沒有任何 .sql 檔案。")

            self.log(f"找到 {total} 個 .sql 檔案。")

            if file_charset == "自動偵測":
                detected, reason = detect_sql_charset(p["sql_folder"], sql_files)
                if not detected:
                    raise RuntimeError(
                        f"無法自動判斷備份檔編碼（{reason}）。\n"
                        f"請在「備份檔編碼」手動選擇正確的編碼後重新執行。"
                    )
                file_charset = detected
                self.log(f"自動偵測備份檔編碼：{file_charset}（{reason}）")

            self.log(
                f"目標資料庫：{db}；備份檔編碼：{file_charset}；"
                f"引擎：{engine}；"
                f"轉換為 utf8mb4：{'是' if to_utf8mb4 else '否'}"
            )

            conn = mysql.connector.connect(
                host=p["host"],
                port=p["port"],
                user=p["user"],
                password=p["password"],
                charset="utf8mb4",
                connection_timeout=10,
            )
            cur = conn.cursor()

            # ---------- 1. 建立（或確認）目標資料庫 ----------
            self.log("\n[步驟 1/4] 確認目標資料庫 …")
            db_charset = "utf8mb4" if to_utf8mb4 else file_charset
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = %s",
                (db,),
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    f"CREATE DATABASE `{db}` DEFAULT CHARACTER SET {db_charset}"
                )
                self.log(f"已建立資料庫 `{db}`（預設字元集 {db_charset}）。")
            else:
                self.log(f"資料庫 `{db}` 已存在，直接使用。")
                # （已含資料表的覆蓋確認在按下開始前的主視窗完成）

            # ---------- 2. 逐檔匯入 ----------
            self.log(f"\n[步驟 2/4] 逐檔匯入（以 {file_charset} 編碼讀取）…")
            env = os.environ.copy()
            env["MYSQL_PWD"] = p["password"]
            cmd = [
                p["mysql"],
                f"--host={p['host']}",
                f"--port={p['port']}",
                f"--user={p['user']}",
                f"--default-character-set={file_charset}",
                "--max-allowed-packet=256M",
                db,
            ]

            failed = []
            for i, sql_file in enumerate(sql_files, start=1):
                self.sig_progress.emit(i, total)
                full_path = os.path.join(p["sql_folder"], sql_file)
                t0 = time.time()
                with open(full_path, "rb") as f:
                    r = subprocess.run(
                        cmd, env=env, stdin=f, capture_output=True, **subprocess_flags()
                    )
                if r.returncode != 0:
                    err = r.stderr.decode("utf-8", errors="replace").strip()
                    failed.append((sql_file, err))
                    self.log(f"  ✗ [{i}/{total}] {sql_file} 失敗：{err}")
                else:
                    self.log(
                        f"  ✓ [{i}/{total}] {sql_file}（{time.time() - t0:.1f} 秒）"
                    )

            if failed:
                detail = "\n  ".join(f"{n}：{e}" for n, e in failed)
                raise RuntimeError(
                    f"{len(failed)}/{total} 個檔案匯入失敗，"
                    f"資料庫【不完整】，請勿直接使用：\n  {detail}\n"
                    f"修正問題後可重新執行（同名資料表會被覆蓋，可安全重跑）。"
                )

            self.log(f"全部 {total} 個檔案匯入成功。")

            # ---------- 3. 字元集無損檢查與轉換（可選） ----------
            normalized = []
            cs_failed = []
            if to_utf8mb4:
                self.log("\n[步驟 3/4] 檢查所有文字資料能否無損轉換為 utf8mb4 …")
                cur.execute(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME, CHARACTER_SET_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND CHARACTER_SET_NAME IS NOT NULL
                      AND CHARACTER_SET_NAME <> 'utf8mb4'
                    ORDER BY TABLE_NAME, ORDINAL_POSITION""",
                    (db,),
                )
                text_cols = cur.fetchall()
                lossy = []
                n_cols = len(text_cols)
                for i, (table, col, cs) in enumerate(text_cols, start=1):
                    self.sig_progress.emit(i, n_cols or 1)
                    # 第一級：嚴格位元組來回比對（NULL 視為相等）
                    strict_ne = (
                        f"NOT (CAST(CONVERT(CONVERT(`{col}` USING utf8mb4)"
                        f" USING {cs}) AS BINARY) <=> CAST(`{col}` AS BINARY))"
                    )
                    cur.execute(
                        f"SELECT COUNT(*) FROM `{db}`.`{table}` WHERE {strict_ne}"
                    )
                    bad = cur.fetchone()[0]
                    if not bad:
                        continue
                    # 第二級：判定是否「真正有損」。
                    # 真正有損 = 轉為 utf8mb4 後字元內容不穩定，
                    # 或轉換產生新的 '?'（無法對應的字被取代）。
                    # 否則為同義異碼，轉換後字義不變，僅位元組正規化，放行。
                    u1 = f"CONVERT(`{col}` USING utf8mb4)"
                    cur.execute(
                        f"SELECT COUNT(*) FROM `{db}`.`{table}` "
                        f"WHERE ({strict_ne}) AND ("
                        f"  NOT (CAST(CONVERT(CONVERT({u1} USING {cs})"
                        f"       USING utf8mb4) AS BINARY)"
                        f"       <=> CAST({u1} AS BINARY))"
                        f"  OR (LENGTH({u1}) - LENGTH(REPLACE({u1}, '?', '')))"
                        f"     > (LENGTH(`{col}`)"
                        f"        - LENGTH(REPLACE(`{col}`, '?', ''))))"
                    )
                    truly_lossy = cur.fetchone()[0]
                    if truly_lossy:
                        lossy.append(
                            f"{table}.{col}（{truly_lossy} 筆，原字元集 {cs}）"
                        )
                        self.log(f"  ✗ {table}.{col}：{truly_lossy} 筆無法無損轉換")
                    if bad - truly_lossy > 0:
                        normalized.append(f"{table}.{col}（{bad - truly_lossy} 筆）")
                        self.log(
                            f"  ⚠ {table}.{col}：{bad - truly_lossy} 筆"
                            f"含同義異碼符號，轉換後將正規化為標準"
                            f" Unicode 編碼（字義不變），放行。"
                        )
                if lossy:
                    raise RuntimeError(
                        "以下欄位含有無法無損轉換為 utf8mb4 的資料"
                        "（轉換後字元會遺失或變成 '?'，常見原因："
                        "big5 造字區的罕用字），已停止字元集轉換：\n  "
                        + "\n  ".join(lossy)
                        + f"\n資料已完整還原為原編碼（{file_charset}），"
                        "可直接使用。請先確認並處理上述資料，"
                        "或取消勾選轉換選項後重新執行。"
                    )
                if n_cols:
                    self.log(
                        f"檢查通過：{n_cols} 個文字欄位皆可無損轉換"
                        + (
                            f"（其中 {len(normalized)} 個欄位含同義異碼，將正規化）"
                            if normalized
                            else ""
                        )
                        + "。"
                    )
                    # 逐表轉換
                    cur.execute(
                        "SELECT TABLE_NAME FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = %s "
                        "AND TABLE_TYPE = 'BASE TABLE' "
                        "ORDER BY TABLE_NAME",
                        (db,),
                    )
                    all_tables = [r[0] for r in cur.fetchall()]
                    self.log(
                        f"將 {len(all_tables)} 張表轉換為 utf8mb4"
                        f"（{TARGET_COLLATION}）…"
                    )
                    for i, table in enumerate(all_tables, start=1):
                        self.sig_progress.emit(i, len(all_tables))
                        t0 = time.time()
                        try:
                            cur.execute(
                                f"ALTER TABLE `{db}`.`{table}` "
                                f"CONVERT TO CHARACTER SET utf8mb4 "
                                f"COLLATE {TARGET_COLLATION}"
                            )
                            self.log(
                                f"  ✓ [{i}/{len(all_tables)}] {table}"
                                f"（{time.time() - t0:.1f} 秒）"
                            )
                        except Exception as e:
                            cs_failed.append((table, str(e)))
                            self.log(
                                f"  ✗ [{i}/{len(all_tables)}] {table}"
                                f" 失敗：{e}"
                                f"（該表維持原字元集，資料未受影響）"
                            )
                    cur.execute(
                        f"ALTER DATABASE `{db}` CHARACTER SET utf8mb4 "
                        f"COLLATE {TARGET_COLLATION}"
                    )
                else:
                    self.log("所有文字欄位已是 utf8mb4，無須轉換。")
            else:
                self.log("\n[步驟 3/4] 未勾選字元集轉換，略過。")

            # ---------- 4. 統一資料引擎 + 核對 ----------
            self.log(f"\n[步驟 4/4] 檢查並統一資料引擎為 {engine} …")
            cur.execute(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY TABLE_NAME",
                (db,),
            )
            tables = cur.fetchall()
            to_alter = [t for t, e in tables if (e or "").upper() != engine.upper()]

            alter_failed = []
            if not to_alter:
                self.log(f"所有資料表引擎已是 {engine}，無須調整。")
            else:
                self.log(f"{len(to_alter)} 張表引擎與選擇不符，逐張轉換 …")
                for i, table in enumerate(to_alter, start=1):
                    self.sig_progress.emit(i, len(to_alter))
                    t0 = time.time()
                    try:
                        cur.execute(f"ALTER TABLE `{db}`.`{table}` ENGINE={engine}")
                        self.log(
                            f"  ✓ [{i}/{len(to_alter)}] {table}"
                            f"（{time.time() - t0:.1f} 秒）"
                        )
                    except Exception as e:
                        alter_failed.append((table, str(e)))
                        self.log(
                            f"  ✗ [{i}/{len(to_alter)}] {table} 失敗："
                            f"{e}（該表維持原引擎，資料未受影響）"
                        )

            cur.execute(
                "SELECT ENGINE, COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "GROUP BY ENGINE",
                (db,),
            )
            engine_summary = ", ".join(f"{e}: {c} 張" for e, c in cur.fetchall())
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
                (db,),
            )
            n_tables = cur.fetchone()[0]
            cur.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (db,),
            )
            db_cs, db_coll = cur.fetchone()
            cur.close()

            # ---------- 摘要 ----------
            lines = [
                f"資料庫 `{db}` 還原完成：{total} 個檔案全部匯入成功，"
                f"共 {n_tables} 張資料表。",
                f"引擎分佈：{engine_summary}；字元集：{db_cs} / {db_coll}。",
            ]
            if normalized:
                lines.append(
                    f"{len(normalized)} 個欄位的同義異碼符號已正規化"
                    f"（字義不變）：" + "、".join(normalized)
                )
            problems = [f"{t}（引擎）" for t, _ in alter_failed] + [
                f"{t}（字元集）" for t, _ in cs_failed
            ]
            if problems:
                lines.append(
                    f"注意：{len(problems)} 項轉換失敗（該表維持原狀，"
                    f"資料完整）：" + "、".join(problems)
                )
                ok = False
            else:
                ok = True
            lines.append("建議抽查主要資料表的筆數（如 cases、patient）確認內容。")

            summary = "\n".join(lines)
            self.log("\n=== 還原結束 ===\n" + summary)
            self.sig_finished.emit(ok, summary)

        except Exception as e:
            self.log(f"\n⚠ 已停止：{e}")
            self.sig_finished.emit(False, str(e))
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------


class SqlRestoreWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SQL 備份還原工具")
        self.resize(580, 580)
        self._thread = None
        self._worker = None
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout()

        self.host_input = self._add_row(layout, "主機:")
        self.port_input = self._add_row(layout, "埠號:")
        self.user_input = self._add_row(layout, "使用者:")
        self.password_input = self._add_row(layout, "密碼:", is_password=True)
        self.database_input = self._add_row(layout, "目標資料庫:")

        # SQL 目錄選擇
        folder_row = QHBoxLayout()
        folder_label = QLabel("SQL 目錄:")
        folder_label.setFixedWidth(90)
        self.folder_input = QLineEdit()
        browse_button = QPushButton("瀏覽…")
        browse_button.clicked.connect(self._browse_folder)
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(browse_button)
        layout.addLayout(folder_row)

        # 備份檔編碼與引擎
        combo_row = QHBoxLayout()
        cs_label = QLabel("備份檔編碼:")
        cs_label.setFixedWidth(90)
        self.charset_combo = QComboBox()
        self.charset_combo.addItems(CHARSET_CHOICES)
        self.charset_combo.setCurrentText("自動偵測")
        eng_label = QLabel("資料引擎:")
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(ENGINE_CHOICES)
        self.engine_combo.setCurrentText("MyISAM")
        combo_row.addWidget(cs_label)
        combo_row.addWidget(self.charset_combo)
        combo_row.addWidget(eng_label)
        combo_row.addWidget(self.engine_combo)
        layout.addLayout(combo_row)

        self.utf8mb4_checkbox = QCheckBox(
            "還原後將資料庫轉換為 utf8mb4（含無損檢查；"
            "備份檔為 big5 等舊編碼時可一次到位）"
        )
        self.utf8mb4_checkbox.setChecked(True)
        layout.addWidget(self.utf8mb4_checkbox)

        self.tool_label = QLabel("")
        self.tool_label.setWordWrap(True)
        layout.addWidget(self.tool_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.start_button = QPushButton("開始還原")
        self.start_button.clicked.connect(self.start_restore)
        layout.addWidget(self.start_button)

        layout.addWidget(QLabel("處理紀錄:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

    def _add_row(self, parent_layout, label_text, is_password=False):
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(90)
        field = QLineEdit()
        if is_password:
            field.setEchoMode(QLineEdit.Password)
        row.addWidget(label)
        row.addWidget(field)
        parent_layout.addLayout(row)
        return field

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "選擇 SQL 備份目錄", self.folder_input.text() or ""
        )
        if folder:
            self.folder_input.setText(folder)

    def _load_config(self):
        self.mysql_path = find_tool("mysql", "mariadb")

        config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "pymedical.conf"
        )
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file, encoding="utf-8")
            db = config["db"] if "db" in config else {}
            self.host_input.setText(db.get("host", "localhost"))
            self.port_input.setText(db.get("port", "3306"))
            self.user_input.setText(db.get("user", "root"))
            self.password_input.setText(db.get("password", ""))
            self.database_input.setText(db.get("database", ""))
            if "tools" in config:
                self.mysql_path = config["tools"].get("mysql", self.mysql_path)
        else:
            self.host_input.setText("localhost")
            self.port_input.setText("3306")

        self.tool_label.setText(f"mysql: {self.mysql_path or '（未找到）'}")

    # -- 事件處理 ---------------------------------------------------------
    def start_restore(self):
        database = self.database_input.text().strip()
        folder = self.folder_input.text().strip()

        if not database:
            QMessageBox.warning(self, "提示", "請填寫目標資料庫名稱。")
            return
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "提示", "請選擇有效的 SQL 備份目錄。")
            return
        if not self.mysql_path:
            QMessageBox.critical(
                self,
                "錯誤",
                "找不到 mysql（或 mariadb）指令。\n"
                "請確認 MariaDB 的 bin 目錄已加入 PATH，"
                "或在 pymedical.conf 的 [tools] 區段指定 mysql 路徑。",
            )
            return
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "提示", "埠號必須是數字。")
            return

        n_sql = len([f for f in os.listdir(folder) if f.endswith(".sql")])
        if n_sql == 0:
            QMessageBox.warning(self, "提示", "指定目錄中沒有任何 .sql 檔案。")
            return

        # 目標資料庫若已含資料表，開始前明確警告覆蓋風險
        try:
            probe = mysql.connector.connect(
                host=self.host_input.text().strip(),
                port=port,
                user=self.user_input.text().strip(),
                password=self.password_input.text(),
                charset="utf8mb4",
                connection_timeout=10,
            )
            pcur = probe.cursor()
            pcur.execute(
                "SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s",
                (database,),
            )
            n_existing = pcur.fetchone()[0]
            pcur.close()
            probe.close()
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "錯誤", f"無法連線資料庫伺服器：\n{err}")
            return

        warn = ""
        if n_existing > 0:
            warn = (
                f"\n\n⚠ 注意：資料庫「{database}」已存在且內含 "
                f"{n_existing} 張資料表！\n"
                f"還原會以備份檔內容【覆蓋同名資料表】，原有資料將遺失。"
            )

        to_utf8mb4 = self.utf8mb4_checkbox.isChecked()
        answer = QMessageBox.question(
            self,
            "還原前確認",
            f"將從目錄匯入 {n_sql} 個 .sql 檔案到資料庫「{database}」。\n"
            f"備份檔編碼：{self.charset_combo.currentText()}"
            f"（須與備份檔匯出時的編碼一致）\n"
            f"資料引擎：{self.engine_combo.currentText()}\n"
            f"轉換為 utf8mb4：{'是（含無損檢查）' if to_utf8mb4 else '否'}"
            + warn
            + "\n\n要開始嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        params = {
            "host": self.host_input.text().strip(),
            "port": port,
            "user": self.user_input.text().strip(),
            "password": self.password_input.text(),
            "database": database,
            "sql_folder": folder,
            "file_charset": self.charset_combo.currentText(),
            "engine": self.engine_combo.currentText(),
            "to_utf8mb4": to_utf8mb4,
            "mysql": self.mysql_path,
        }

        self.log_box.clear()
        self.start_button.setEnabled(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

        self._thread = QThread()
        self._worker = RestoreWorker(params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.sig_log.connect(self._on_log)
        self._worker.sig_progress.connect(self._on_progress)
        self._worker.sig_finished.connect(self._on_finished)
        self._thread.start()

    def _on_log(self, msg):
        self.log_box.append(msg)
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_progress(self, current, total):
        if total == 0:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)

    def _on_finished(self, ok, summary):
        self._thread.quit()
        self._thread.wait()
        self._thread = None
        self._worker = None
        self.start_button.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1 if ok else 0)
        if ok:
            QMessageBox.information(self, "還原完成", summary)
        else:
            QMessageBox.critical(self, "還原未完成", summary)

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.warning(
                self, "提示", "還原仍在進行中，請等待完成後再關閉視窗。"
            )
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SqlRestoreWindow()
    window.show()
    sys.exit(app.exec_())
