# -*- coding: utf-8 -*-
"""
MyISAM → InnoDB 安全轉換工具（資料正確性優先版）

設計原則：
  1. 資料搬運完全交給 MariaDB 伺服器端（mysqldump 匯出 → 匯入 → ALTER TABLE），
     Python 不逐批搬資料，從根本上消除 LIMIT/OFFSET 順序不定造成的重複/遺漏風險。
  2. 匯入後、改引擎前，逐表核對 COUNT(*)，並以 mysqldump 分別匯出
     來源與目標的資料內容（依主鍵排序）比對 SHA-256 雜湊。
     這是「邏輯值」的逐位元組比對，不受實體列儲存格式影響。
     （不採用 CHECKSUM TABLE：舊版 MySQL/MariaDB 時代建立的表，
       其 temporal 欄位的實體儲存格式與新建表不同，
       即使資料完全相同，CHECKSUM TABLE 也會誤報不一致。）
  3. 可選：同時將字元集轉換為 utf8mb4。轉換前逐欄做
     「原字元集 → utf8mb4 → 原字元集」來回轉換測試，
     任何一筆資料無法無損轉換（如 big5 造字區罕用字）即停止並報告位置。
     檢查全數通過後，引擎與字元集合併在同一個 ALTER 執行，
     最終再以 utf8mb4 邏輯內容比對驗證轉換忠實無誤。
  4. ALTER 是伺服器端原子操作（內部為建新表→複製→改名），失敗時原表保持不變。
  4. 匯出檔以 binary 字元集 + --hex-blob 產生，位元組級零轉換。
     匯出檔置於系統暫存目錄，轉換成功後自動刪除、失敗時保留供排查；
     來源資料庫全程唯讀不被改動，本身即為完整的原始資料。
  5. 任何一關失敗即停止並明確報告，絕不默默繼續。
  6. 目標資料庫若已存在且含資料表，一律拒絕執行，避免覆蓋。

執行前注意：
  * 請在維護時段執行，停止所有會寫入來源資料庫的應用程式。
    （mysqldump 對 MyISAM 預設會鎖表，能保證匯出一致性，
      但應用程式若同時寫入會被擋住或造成核對誤差。）
  * 需要 mysqldump 與 mysql（或 mariadb-dump / mariadb）指令可用，
    通常隨 MariaDB/MySQL 安裝，程式會自動偵測。
"""

import sys
import os
import shutil
import subprocess
import configparser
import datetime
import time
import hashlib
import tempfile

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QHBoxLayout, QProgressBar, QTextEdit, QCheckBox
)

import mysql.connector


# 字元集轉換的目標排序規則。utf8mb4_unicode_ci 為通用且與各版本 MariaDB
# 相容的選擇；如有特殊排序需求可改為其他 utf8mb4 系列 collation。
TARGET_COLLATION = "utf8mb4_unicode_ci"


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------

def find_tool(*candidates):
    """在 PATH 中尋找可用的指令，回傳完整路徑或 None。"""
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def subprocess_flags():
    """Windows 下隱藏子程序的黑色主控台視窗。"""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


# ---------------------------------------------------------------------------
# 背景工作執行緒（避免 GUI 凍結）
# ---------------------------------------------------------------------------

class ConvertWorker(QObject):
    sig_log = pyqtSignal(str)
    sig_progress = pyqtSignal(int, int)      # (目前, 總數)；總數 0 = 不確定模式
    sig_finished = pyqtSignal(bool, str)     # (是否成功, 摘要訊息)

    def __init__(self, params):
        super().__init__()
        self.p = params

    # -- 便利方法 --------------------------------------------------------
    def log(self, msg):
        self.sig_log.emit(msg)

    def busy(self):
        """進度條切到不確定（跑馬燈）模式。"""
        self.sig_progress.emit(0, 0)

    def _table_data_hash(self, env, db, table, charset):
        """
        以 mysqldump 匯出單一表格的「資料內容」並回傳 SHA-256。
        - --skip-extended-insert：一列一句 INSERT。mysqldump 會把字串中的
          換行逸出為 \\n，故輸出每一實體行恰為一列資料，可安全逐行處理。
        - 所有列「排序後」才計算雜湊：比對結果與實體列順序、索引、
          排序規則（collation）完全無關。
        - charset='binary'：位元組級比對（來源/目標字元集相同時使用）。
          charset='utf8mb4'：由伺服器統一轉為 utf8mb4 後比對「邏輯字元
          內容」，用於驗證字元集轉換後資料仍一致。
        - --compact --no-create-info：只留 INSERT，排除註解與時間戳記。
        - --hex-blob：二進位欄位以十六進位輸出，不受字元集影響。
        """
        cmd = [
            self.p["mysqldump"],
            f"--host={self.p['host']}", f"--port={self.p['port']}",
            f"--user={self.p['user']}",
            f"--default-character-set={charset}",
            "--hex-blob",
            "--compact", "--no-create-info",
            "--skip-extended-insert",
            "--max-allowed-packet=256M",
            db, table,
        ]
        r = subprocess.run(cmd, env=env, capture_output=True,
                           **subprocess_flags())
        if r.returncode != 0:
            raise RuntimeError(
                f"匯出 {db}.{table} 供比對時失敗：\n"
                f"{r.stderr.decode('utf-8', errors='replace').strip()}")
        h = hashlib.sha256()
        for line in sorted(r.stdout.split(b"\n")):
            h.update(line)
            h.update(b"\n")
        return h.hexdigest()

    # -- 主流程 ----------------------------------------------------------
    def run(self):
        conn = None
        dump_file = None
        try:
            p = self.p
            self._check_tools()

            self.log("連線到資料庫伺服器…")
            conn = mysql.connector.connect(
                host=p["host"], port=p["port"],
                user=p["user"], password=p["password"],
                connection_timeout=10,
            )
            cur = conn.cursor()

            # ---------- 0. 事前檢查 ----------
            source_db = p["source_db"]
            target_db = p["target_db"]

            cur.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (source_db,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"找不到來源資料庫：{source_db}")
            charset, collation = row
            self.log(f"來源資料庫字元集：{charset} / {collation}")

            # 列出來源所有「實體資料表」（排除 VIEW）與引擎
            cur.execute(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY TABLE_NAME",
                (source_db,))
            source_tables = cur.fetchall()
            if not source_tables:
                raise RuntimeError(f"來源資料庫 {source_db} 中沒有任何資料表。")

            myisam_tables = [t for t, e in source_tables if (e or "").upper() == "MYISAM"]
            self.log(f"來源共 {len(source_tables)} 張資料表，"
                     f"其中 MyISAM {len(myisam_tables)} 張。")
            if not myisam_tables:
                self.log("（沒有 MyISAM 表，仍會完整複製一份到目標資料庫。）")

            # 目標資料庫：不存在→稍後建立；存在但空→沿用；存在且有表→拒絕
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = %s", (target_db,))
            target_exists = cur.fetchone()[0] > 0
            if target_exists:
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = %s", (target_db,))
                if cur.fetchone()[0] > 0:
                    raise RuntimeError(
                        f"目標資料庫 {target_db} 已存在且內含資料表。\n"
                        f"為避免覆蓋任何資料，本工具不會使用非空的目標資料庫。\n"
                        f"請確認內容後手動 DROP，或改用其他目標名稱。")
                self.log(f"目標資料庫 {target_db} 已存在但為空，將直接使用。")

            # 提醒：沒有主鍵的表（不影響本次轉換，但建議日後補上）
            cur.execute("""
                SELECT t.TABLE_NAME
                FROM information_schema.TABLES t
                LEFT JOIN information_schema.TABLE_CONSTRAINTS c
                  ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
                 AND c.TABLE_NAME  = t.TABLE_NAME
                 AND c.CONSTRAINT_TYPE = 'PRIMARY KEY'
                WHERE t.TABLE_SCHEMA = %s AND t.TABLE_TYPE = 'BASE TABLE'
                  AND c.CONSTRAINT_NAME IS NULL
                ORDER BY t.TABLE_NAME""", (source_db,))
            no_pk = [r[0] for r in cur.fetchall()]
            if no_pk:
                self.log(f"提醒：以下 {len(no_pk)} 張表沒有主鍵，"
                         f"轉成 InnoDB 仍可運作，但建議日後補上主鍵以利效能：")
                self.log("  " + ", ".join(no_pk))

            # ---------- 1. mysqldump 匯出（同時是完整備份） ----------
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_file = os.path.join(
                tempfile.gettempdir(), f"{source_db}_dump_{ts}.sql")

            self.log(f"\n[步驟 1/6] 匯出來源資料庫 → {dump_file}")
            self.log("（使用 binary 字元集 + hex-blob，位元組級零轉換。"
                     "此為暫存檔，轉換成功後自動刪除；"
                     "來源資料庫全程不被改動，即為最完整的原始資料。）")
            self.busy()

            env = os.environ.copy()
            env["MYSQL_PWD"] = p["password"]   # 不放命令列，避免出現在程序列表

            dump_cmd = [
                p["mysqldump"],
                f"--host={p['host']}", f"--port={p['port']}",
                f"--user={p['user']}",
                "--default-character-set=binary",
                "--hex-blob",
                "--routines", "--triggers", "--events",
                "--max-allowed-packet=256M",
                "--result-file=" + dump_file,   # 由工具直接寫檔，避免 shell 重導向的編碼問題
                source_db,
            ]
            t0 = time.time()
            r = subprocess.run(dump_cmd, env=env,
                               capture_output=True, text=True,
                               **subprocess_flags())
            if r.returncode != 0:
                raise RuntimeError(f"mysqldump 失敗：\n{r.stderr.strip()}")
            size_mb = os.path.getsize(dump_file) / 1024 / 1024
            self.log(f"匯出完成（{size_mb:.1f} MB，{time.time()-t0:.0f} 秒）。")

            # ---------- 2. 建立目標資料庫並匯入 ----------
            self.log(f"\n[步驟 2/6] 匯入到目標資料庫 {target_db} …")
            self.busy()

            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{target_db}` "
                f"DEFAULT CHARACTER SET {charset} COLLATE {collation}")

            import_cmd = [
                p["mysql"],
                f"--host={p['host']}", f"--port={p['port']}",
                f"--user={p['user']}",
                "--default-character-set=binary",
                "--max-allowed-packet=256M",
                target_db,
            ]
            t0 = time.time()
            with open(dump_file, "rb") as f:
                r = subprocess.run(import_cmd, env=env, stdin=f,
                                   capture_output=True, text=True,
                                   **subprocess_flags())
            if r.returncode != 0:
                raise RuntimeError(f"匯入失敗：\n{r.stderr.strip()}")
            self.log(f"匯入完成（{time.time()-t0:.0f} 秒）。目前目標資料庫與來源引擎相同。")

            # ---------- 3. 核對筆數 + 資料內容逐位元組邏輯比對 ----------
            # 不使用 CHECKSUM TABLE：它雜湊的是「實體列儲存格式」，
            # 舊版本時代建立的表（temporal 欄位為舊格式）與新建表即使資料
            # 完全相同也會不一致。改為 mysqldump 匯出邏輯資料值比對雜湊，
            # 不受儲存格式、引擎、版本歷史影響。
            self.log(f"\n[步驟 3/6] 逐表核對筆數與資料內容"
                     f"（mysqldump 邏輯值 SHA-256 比對）…")
            total = len(source_tables)
            mismatches = []

            for i, (table, _eng) in enumerate(source_tables, start=1):
                self.sig_progress.emit(i, total)

                cur.execute(f"SELECT COUNT(*) FROM `{source_db}`.`{table}`")
                src_cnt = cur.fetchone()[0]
                cur.execute(f"SELECT COUNT(*) FROM `{target_db}`.`{table}`")
                tgt_cnt = cur.fetchone()[0]

                src_hash = self._table_data_hash(env, source_db, table,
                                                 "binary")
                tgt_hash = self._table_data_hash(env, target_db, table,
                                                 "binary")

                if src_cnt != tgt_cnt or src_hash != tgt_hash:
                    mismatches.append(
                        f"{table}（筆數 {src_cnt}/{tgt_cnt}，"
                        f"內容雜湊 {'相符' if src_hash == tgt_hash else '不符'}）")
                    self.log(f"  ✗ [{i}/{total}] {table} 核對不符！")
                else:
                    self.log(f"  ✓ [{i}/{total}] {table}"
                             f"（{src_cnt} 筆，內容一致）")

            if mismatches:
                raise RuntimeError(
                    "以下表格複製後資料內容核對不符，已停止（尚未改動引擎）：\n  "
                    + "\n  ".join(mismatches)
                    + "\n請勿使用目標資料庫。最常見的原因是來源資料庫"
                    "在轉換期間被應用程式寫入，請停止應用程式後重新執行。")

            self.log("全部表格核對通過：目標資料庫與來源資料內容完全一致。")

            # ---------- 4. 字元集無損轉換預檢 ----------
            convert_charset = p["convert_charset"]
            normalized = []
            if convert_charset:
                self.log(f"\n[步驟 4/6] 檢查所有文字資料能否無損轉換為 utf8mb4 …")
                self.log("（逐欄做「原字元集 → utf8mb4 → 原字元集」來回轉換測試，"
                         "big5 造字區罕用字等無法對應的資料會在此被攔下。）")
                # 找出目標庫中所有非 utf8mb4 的文字欄位
                cur.execute("""
                    SELECT TABLE_NAME, COLUMN_NAME, CHARACTER_SET_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND CHARACTER_SET_NAME IS NOT NULL
                      AND CHARACTER_SET_NAME <> 'utf8mb4'
                    ORDER BY TABLE_NAME, ORDINAL_POSITION""", (target_db,))
                text_cols = cur.fetchall()
                lossy = []
                normalized = []
                n_cols = len(text_cols)
                for i, (table, col, cs) in enumerate(text_cols, start=1):
                    self.sig_progress.emit(i, n_cols or 1)
                    # 第一級：嚴格位元組來回比對。
                    # NOT (a <=> b)：NULL 視為相等，只抓轉換後位元組不同的值
                    strict_ne = (
                        f"NOT (CAST(CONVERT(CONVERT(`{col}` USING utf8mb4)"
                        f" USING {cs}) AS BINARY) <=> CAST(`{col}` AS BINARY))")
                    cur.execute(
                        f"SELECT COUNT(*) FROM `{target_db}`.`{table}` "
                        f"WHERE {strict_ne}")
                    bad = cur.fetchone()[0]
                    if not bad:
                        continue
                    # 第二級：位元組不同的列，進一步判定是否「真正有損」。
                    # 真正有損 = 轉為 utf8mb4 後字元內容不穩定（來回後 Unicode
                    # 值改變），或轉換產生了新的 '?'（無法對應的字被取代）。
                    # 若兩者皆否，代表只是「同義異碼」（同一字在原字元集有
                    # 多種位元組編碼，如 Big5 符號區），轉換後字義完全不變，
                    # 僅位元組正規化為標準編碼，可安全放行。
                    u1 = f"CONVERT(`{col}` USING utf8mb4)"
                    cur.execute(
                        f"SELECT COUNT(*) FROM `{target_db}`.`{table}` "
                        f"WHERE ({strict_ne}) AND ("
                        f"  NOT (CAST(CONVERT(CONVERT({u1} USING {cs})"
                        f"       USING utf8mb4) AS BINARY)"
                        f"       <=> CAST({u1} AS BINARY))"
                        f"  OR (LENGTH({u1}) - LENGTH(REPLACE({u1}, '?', '')))"
                        f"     > (LENGTH(`{col}`)"
                        f"        - LENGTH(REPLACE(`{col}`, '?', ''))))")
                    truly_lossy = cur.fetchone()[0]
                    if truly_lossy:
                        lossy.append(
                            f"{table}.{col}（{truly_lossy} 筆，原字元集 {cs}）")
                        self.log(f"  ✗ {table}.{col}：{truly_lossy} 筆"
                                 f"無法無損轉換")
                    if bad - truly_lossy > 0:
                        normalized.append(
                            f"{table}.{col}（{bad - truly_lossy} 筆）")
                        self.log(f"  ⚠ {table}.{col}：{bad - truly_lossy} 筆"
                                 f"含同義異碼符號，轉換後將正規化為標準"
                                 f" Unicode 編碼（字義不變），放行。")
                if lossy:
                    raise RuntimeError(
                        "以下欄位含有無法無損轉換為 utf8mb4 的資料"
                        "（轉換後字元會遺失或變成 '?'，常見原因："
                        "big5 造字區的罕用字），已停止，"
                        "尚未進行任何引擎或字元集變更：\n  "
                        + "\n  ".join(lossy)
                        + "\n來源與目標資料庫的資料皆完整。"
                        "請先確認並處理上述資料，或取消勾選字元集轉換後重新執行。")
                self.log(f"檢查通過：{n_cols} 個文字欄位皆可無損轉換為 utf8mb4"
                         + (f"（其中 {len(normalized)} 個欄位含同義異碼，"
                            f"將正規化）" if normalized else "") + "。")
            else:
                self.log(f"\n[步驟 4/6] 未勾選字元集轉換，略過無損檢查。")

            # ---------- 5. 逐表轉換引擎（與字元集）----------
            # 引擎與字元集合併在同一個 ALTER，每張表只需重建一次。
            # ALTER 為伺服器端操作（建新表→複製→改名），失敗時原表保持不變。
            cur.execute(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY TABLE_NAME", (target_db,))
            target_tables = cur.fetchall()

            action_desc = "轉為 InnoDB"
            if convert_charset:
                action_desc += f" 並轉換字元集為 utf8mb4（{TARGET_COLLATION}）"
            self.log(f"\n[步驟 5/6] 將目標資料庫 {len(target_tables)} 張表"
                     f"{action_desc} …")

            alter_failed = []
            for i, (table, engine) in enumerate(target_tables, start=1):
                self.sig_progress.emit(i, len(target_tables))
                opts = []
                if (engine or "").upper() != "INNODB":
                    opts.append("ENGINE=InnoDB")
                if convert_charset:
                    opts.append(f"CONVERT TO CHARACTER SET utf8mb4 "
                                f"COLLATE {TARGET_COLLATION}")
                if not opts:
                    self.log(f"  - [{i}/{len(target_tables)}] {table}"
                             f"（已是 InnoDB，無須變更）")
                    continue
                t0 = time.time()
                try:
                    cur.execute(f"ALTER TABLE `{target_db}`.`{table}` "
                                + ", ".join(opts))
                    self.log(f"  ✓ [{i}/{len(target_tables)}] {table}"
                             f"（{time.time()-t0:.1f} 秒）")
                except Exception as e:
                    # ALTER 失敗時該表維持原狀，資料不受影響
                    alter_failed.append((table, str(e)))
                    self.log(f"  ✗ [{i}/{len(target_tables)}] {table} 失敗："
                             f"{e}（該表維持原狀，資料未受影響）")

            if convert_charset:
                # 資料庫層級的預設字元集也一併更新（影響日後新建的表）
                cur.execute(
                    f"ALTER DATABASE `{target_db}` CHARACTER SET utf8mb4 "
                    f"COLLATE {TARGET_COLLATION}")

            # ---------- 6. 最終核對（筆數 + 邏輯內容） ----------
            # 若已轉字元集，改以 utf8mb4 連線字元集比對「邏輯字元內容」：
            # 來源（big5 等）由伺服器轉為 utf8mb4 匯出、目標直接匯出，
            # 兩者一致即證明字元集轉換忠實無誤。
            verify_charset = "utf8mb4" if convert_charset else "binary"
            self.log(f"\n[步驟 6/6] 最終核對筆數與資料內容"
                     f"（以 {verify_charset} 比對）…")
            final_bad = []
            for i, (table, _eng) in enumerate(source_tables, start=1):
                self.sig_progress.emit(i, total)
                if any(t == table for t, _ in alter_failed):
                    self.log(f"  - [{i}/{total}] {table}（ALTER 失敗，略過核對）")
                    continue
                cur.execute(f"SELECT COUNT(*) FROM `{source_db}`.`{table}`")
                src_cnt = cur.fetchone()[0]
                cur.execute(f"SELECT COUNT(*) FROM `{target_db}`.`{table}`")
                tgt_cnt = cur.fetchone()[0]
                src_hash = self._table_data_hash(env, source_db, table,
                                                 verify_charset)
                tgt_hash = self._table_data_hash(env, target_db, table,
                                                 verify_charset)
                if src_cnt != tgt_cnt or src_hash != tgt_hash:
                    final_bad.append(
                        f"{table}（筆數 {src_cnt}/{tgt_cnt}，內容雜湊 "
                        f"{'相符' if src_hash == tgt_hash else '不符'}）")
                    self.log(f"  ✗ [{i}/{total}] {table} 核對不符！")
                else:
                    self.log(f"  ✓ [{i}/{total}] {table}"
                             f"（{src_cnt} 筆，內容一致）")

            if final_bad:
                raise RuntimeError(
                    "最終核對不符（來源可能在轉換期間被寫入，"
                    "或字元集轉換有異常）：\n  " + "\n  ".join(final_bad)
                    + "\n請勿使用目標資料庫，來源資料庫未被改動。")

            cur.execute(
                "SELECT ENGINE, COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "GROUP BY ENGINE", (target_db,))
            engine_summary = ", ".join(f"{e}: {c} 張" for e, c in cur.fetchall())

            cur.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (target_db,))
            tgt_cs, tgt_coll = cur.fetchone()

            cur.close()

            # ---------- 摘要 ----------
            lines = [
                f"目標資料庫 {target_db} 建立完成。",
                f"引擎分佈：{engine_summary}；字元集：{tgt_cs} / {tgt_coll}。",
            ]
            if alter_failed:
                lines.append(
                    f"注意：{len(alter_failed)} 張表 ALTER 失敗（維持原狀，"
                    f"資料完整）：" +
                    "、".join(t for t, _ in alter_failed))
                lines.append("修正問題後可對這些表單獨執行 ALTER TABLE。")
                ok = False
            else:
                if convert_charset:
                    lines.append("全部表格已成功轉為 InnoDB + utf8mb4，"
                                 "內容核對一致。")
                    if normalized:
                        lines.append(
                            f"其中 {len(normalized)} 個欄位的同義異碼符號"
                            f"已正規化為標準 Unicode 編碼（字義不變）："
                            + "、".join(normalized))
                else:
                    lines.append("全部表格已成功轉為 InnoDB，內容核對一致。")
                ok = True

            # 全部成功才刪除暫存檔；部分失敗時保留以便排查
            if ok:
                try:
                    os.remove(dump_file)
                    self.log(f"（已刪除暫存檔 {dump_file}）")
                except OSError:
                    lines.append(f"提醒：暫存檔未能自動刪除，"
                                 f"可手動移除：{dump_file}")
            else:
                lines.append(f"暫存檔保留於 {dump_file}，"
                             f"排查完畢後可手動刪除。")

            summary = "\n".join(lines)
            self.log("\n=== 轉換結束 ===\n" + summary)
            self.sig_finished.emit(ok, summary)

        except Exception as e:
            self.log(f"\n⚠ 已停止：{e}")
            if dump_file and os.path.exists(dump_file):
                self.log(f"（暫存檔保留於 {dump_file}，"
                         f"排查完畢後可手動刪除。）")
            self.sig_finished.emit(False, str(e))
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def _check_tools(self):
        if not self.p["mysqldump"]:
            raise RuntimeError(
                "找不到 mysqldump（或 mariadb-dump）指令。\n"
                "請確認 MariaDB/MySQL 的 bin 目錄已加入 PATH，"
                "或在 pymedical.conf 的 [tools] 區段指定 mysqldump 路徑。")
        if not self.p["mysql"]:
            raise RuntimeError(
                "找不到 mysql（或 mariadb）指令。\n"
                "請確認 MariaDB/MySQL 的 bin 目錄已加入 PATH，"
                "或在 pymedical.conf 的 [tools] 區段指定 mysql 路徑。")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class MyISAMToInnoDBConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyISAM 轉換為 InnoDB 工具（安全版）")
        self.resize(560, 520)
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
        self.source_input = self._add_row(layout, "來源資料庫:")
        self.target_input = self._add_row(layout, "目標資料庫:")

        self.charset_checkbox = QCheckBox(
            "同時將字元集轉換為 utf8mb4（含轉換前無損檢查，任何一筆資料"
            "無法無損轉換即停止）")
        self.charset_checkbox.setChecked(True)
        layout.addWidget(self.charset_checkbox)

        self.tool_label = QLabel("")
        self.tool_label.setWordWrap(True)
        layout.addWidget(self.tool_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.start_button = QPushButton("開始轉換")
        self.start_button.clicked.connect(self.start_convert)
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

    def _load_config(self):
        self.mysqldump_path = find_tool("mysqldump", "mariadb-dump")
        self.mysql_path = find_tool("mysql", "mariadb")

        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "pymedical.conf")
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file, encoding="utf-8")
            db = config["db"] if "db" in config else {}
            self.host_input.setText(db.get("host", "localhost"))
            self.port_input.setText(db.get("port", "3306"))
            self.user_input.setText(db.get("user", "root"))
            self.password_input.setText(db.get("password", ""))
            self.source_input.setText(db.get("database", "pymedical"))
            self.target_input.setText(db.get("inno_database", "pymedical_innodb"))
            # 允許在設定檔手動指定工具路徑（選填）
            if "tools" in config:
                self.mysqldump_path = config["tools"].get(
                    "mysqldump", self.mysqldump_path)
                self.mysql_path = config["tools"].get(
                    "mysql", self.mysql_path)
        else:
            QMessageBox.warning(self, "提示",
                                f"找不到設定檔 {config_file}，請手動填寫連線資訊。")
            self.host_input.setText("localhost")
            self.port_input.setText("3306")

        self.tool_label.setText(
            f"mysqldump: {self.mysqldump_path or '（未找到）'}\n"
            f"mysql: {self.mysql_path or '（未找到）'}")

    # -- 事件處理 ---------------------------------------------------------
    def start_convert(self):
        source_db = self.source_input.text().strip()
        target_db = self.target_input.text().strip()

        if not source_db or not target_db:
            QMessageBox.warning(self, "提示", "請填寫來源與目標資料庫名稱。")
            return
        if source_db == target_db:
            QMessageBox.warning(self, "提示",
                                "來源與目標資料庫不可相同，避免覆蓋原始資料。")
            return

        answer = QMessageBox.question(
            self, "轉換前確認",
            "開始前請確認：\n\n"
            "1. 已停止所有會寫入來源資料庫的應用程式（維護時段執行）。\n"
            "2. 系統暫存目錄所在磁碟（通常是 C:）需有約來源資料庫\n"
            "    大小 1.5 倍的空間放匯出暫存檔（成功後自動刪除）；\n"
            "    資料庫所在磁碟需有約 2 倍空間（目標庫 + ALTER 暫存）。\n\n"
            f"將由「{source_db}」複製並轉換到「{target_db}」"
            + ("（含字元集轉換為 utf8mb4）" if self.charset_checkbox.isChecked() else "")
            + "，\n來源資料庫完全不會被修改。要開始嗎？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return

        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "提示", "埠號必須是數字。")
            return

        params = {
            "host": self.host_input.text().strip(),
            "port": port,
            "user": self.user_input.text().strip(),
            "password": self.password_input.text(),
            "source_db": source_db,
            "target_db": target_db,
            "mysqldump": self.mysqldump_path,
            "mysql": self.mysql_path,
            "work_dir": os.path.dirname(os.path.abspath(__file__)),
            "convert_charset": self.charset_checkbox.isChecked(),
        }

        self.log_box.clear()
        self.start_button.setEnabled(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

        self._thread = QThread()
        self._worker = ConvertWorker(params)
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
        if total == 0:           # 不確定模式（匯出/匯入中）
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
            QMessageBox.information(self, "轉換完成", summary)
        else:
            QMessageBox.critical(self, "轉換未完成", summary)

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.warning(self, "提示",
                                "轉換仍在進行中，請等待完成後再關閉視窗。")
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyISAMToInnoDBConverter()
    window.show()
    sys.exit(app.exec_())
