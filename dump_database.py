"""
逐表 SQL 備份工具（GUI 版）

與 restore_sql.py 成對使用：本工具產生的目錄可以直接餵給 restore_sql.py
還原。介面風格與安全原則相同——每個檔案的匯出結果逐一檢查，任何失敗立即
記錄並在結束時明確列出，備份工具絕不假裝成功。

為什麼不能再直接複製資料夾
--------------------------
MyISAM 的 .frm / .MYD / .MYI 三個檔是自給自足的，複製到別台機器就能用。
InnoDB 不是：即使開了 innodb_file_per_table，每張表的 .ibd 裡有一個
tablespace ID，必須與共用表空間 ibdata1 裡的資料字典對得起來，而 ibdata1、
ib_logfile* 都在 datadir 根目錄、不在資料庫的資料夾裡。只複製資料庫資料夾
過去，MariaDB 會回報 Tablespace is missing 或 Table doesn't exist in
engine——表看得到、查不了。

更麻煩的是這種備份【看起來是成功的】：檔案都在、大小也對，直到真的要還原
才發現是空的。所以轉成 InnoDB 之後，備份一律要走 mysqldump。

本工具做的事
------------
  1. 前置檢查（唯讀）：資料表清單、引擎、大小、磁碟空間、其他連線，
     以及「中繼資料裡有但引擎裡沒有實體」的殘骸表（錯誤 1932）。
  2. 逐表匯出成獨立的 .sql 檔，另外匯出 view 與預存程序。
  3. 逐檔驗證：確認每個檔案都以 mysqldump 的完成標記結尾。磁碟寫滿或
     程序被中斷時，檔案會停在半途而沒有任何錯誤碼——這一步就是為了
     抓那種情況。
  4. 寫出 00_manifest.txt：資料庫名稱、字元集、各表筆數與檔案大小。
     還原之後可以拿它逐項核對。

一致性的限制（重要）
--------------------
逐表匯出是分次進行的，因此【不保證跨資料表的一致性】：如果匯出期間有人
在看診，A 表可能是 10:00 的狀態、B 表是 10:05 的狀態，還原後兩者對不起來。
單一資料表內部則是一致的。

要拿到真正一致的備份，執行前請關閉所有診所端程式（含候診看板、Kiosk、
預約掛號伺服器）。前置檢查會列出還連著的連線。
"""

import configparser
import datetime
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

# 重用 restore_sql 的工具函式，不複製貼上——複製會讓兩邊日後慢慢分岔。
from restore_sql import find_tool, fmt_secs, subprocess_flags

# 「資料表存在於中繼資料，但引擎裡沒有實體」的錯誤碼。這種表無法 dump，
# 而且會讓 mysqldump 的 LOCK TABLES 整批失敗，必須先找出來排除。
BROKEN_TABLE_ERRORS = {1017, 1030, 1146, 1877, 1932}

# mysqldump 正常結束時寫在檔尾的標記。用來確認檔案沒有被截斷。
DUMP_COMPLETE_MARKER = b"-- Dump completed"

MANIFEST_FILE = "00_manifest.txt"
TABLE_PREFIX = "10_"
VIEWS_FILE = "90_views.sql"
ROUTINES_FILE = "91_routines.sql"


def fmt_bytes(n):
    if n is None:
        return "未知"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{int(n)} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def safe_filename(name):
    """把資料表名稱轉成安全的檔名片段。"""
    return re.sub(r"[^0-9A-Za-z_.-]", "_", name)


def run_dump(cmd, env, out_path):
    """執行 mysqldump，輸出寫入 out_path。回傳 (returncode, stderr)。

    刻意使用 mysqldump 的 --result-file 而非 shell 重導向：Windows 上重導向
    會做 CRLF 轉換，可能弄壞 dump 內容。--result-file 以二進位模式寫入。
    """
    proc = subprocess.Popen(
        cmd + [f"--result-file={out_path}"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **subprocess_flags(),
    )
    _, err = proc.communicate()
    return proc.returncode, err.decode("utf-8", errors="replace").strip()


def verify_dump_file(path, tail_bytes=4096):
    """確認 dump 檔以 mysqldump 的完成標記結尾。

    回傳 (是否完整, 說明)。

    這一步是為了抓「磁碟寫滿」「程序被中斷」這類情況：檔案會停在半途，
    而 mysqldump 不一定回報非零的結束碼，看起來像成功。備份工具最不能
    接受的就是這種假成功。
    """
    try:
        size = os.path.getsize(path)
    except OSError as e:
        return False, f"讀不到檔案：{e}"

    if size == 0:
        return False, "檔案是空的"

    try:
        with open(path, "rb") as f:
            f.seek(max(0, size - tail_bytes))
            tail = f.read()
    except OSError as e:
        return False, f"讀取失敗：{e}"

    if DUMP_COMPLETE_MARKER not in tail:
        return False, "檔尾沒有 mysqldump 的完成標記，檔案可能被截斷"
    return True, ""


# ---------------------------------------------------------------------------
# 前置檢查（純唯讀）
# ---------------------------------------------------------------------------


class Preflight:
    def __init__(self):
        self.charset = None
        self.collation = None
        self.server_version = None
        self.tables = []  # [(table, engine, bytes)]
        self.broken = []  # [(table, errno, 訊息)]
        self.engines = {}
        self.total_bytes = 0
        self.views = []
        self.routines = []
        self.events = []
        self.mixed_charsets = []
        self.other_connections = []
        self.existing_sql = []
        self.blocking = []
        self.warnings = []


def run_preflight(cur, db, out_dir, log):
    pf = Preflight()

    cur.execute("SELECT VERSION()")
    pf.server_version = cur.fetchone()[0]

    cur.execute(
        "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
        "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
        (db,),
    )
    row = cur.fetchone()
    if not row:
        pf.blocking.append(f"找不到資料庫 `{db}`。")
        return pf
    pf.charset, pf.collation = row
    log(f"資料庫 `{db}`：{pf.charset} / {pf.collation}（MariaDB {pf.server_version}）")

    # ---- 資料表 ----
    cur.execute(
        """
        SELECT TABLE_NAME, ENGINE, DATA_LENGTH + INDEX_LENGTH AS SZ
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """,
        (db,),
    )
    listed = [
        (name, (engine or "").upper(), int(size or 0))
        for name, engine, size in cur.fetchall()
    ]
    if not listed:
        pf.blocking.append(f"資料庫 `{db}` 沒有任何資料表。")
        return pf

    # 逐表探測：中繼資料有、引擎裡沒有實體的殘骸要先排除，否則 mysqldump
    # 的 LOCK TABLES 會讓整批匯出失敗。
    for name, engine, size in listed:
        try:
            cur.execute(f"SELECT 1 FROM `{db}`.`{name}` LIMIT 1")
            cur.fetchall()
        except mysql.connector.Error as e:
            errno = getattr(e, "errno", None)
            if errno in BROKEN_TABLE_ERRORS:
                pf.broken.append((name, errno, str(e)))
                continue
            raise
        pf.tables.append((name, engine, size))
        pf.total_bytes += size
        pf.engines[engine] = pf.engines.get(engine, 0) + 1

    if not pf.tables:
        pf.blocking.append(f"資料庫 `{db}` 的資料表全部無法讀取。")
        return pf

    engine_detail = "、".join(f"{k} {v} 張" for k, v in sorted(pf.engines.items()))
    log(
        f"資料表：{len(pf.tables)} 張（{engine_detail}，"
        f"合計 {fmt_bytes(pf.total_bytes)}）"
    )

    if pf.broken:
        names = "、".join(t for t, _, _ in pf.broken)
        log(f"  ⚠ {len(pf.broken)} 張表無法讀取，將被排除：{names}")
        pf.warnings.append(
            f"以下 {len(pf.broken)} 張表在中繼資料裡存在，但引擎裡沒有實體"
            f"（典型錯誤 1932）：{names}。\n"
            "    這些是壞掉的殘骸——.frm 還在但資料檔不見了。它們無法備份，"
            "備份中不會有這些表。若程式會用到，代表該功能目前就已經是壞的，"
            "建議 DROP TABLE 清掉殘骸後讓程式自動重建。"
        )

    # ---- view / routine / event ----
    cur.execute(
        "SELECT TABLE_NAME FROM information_schema.VIEWS "
        "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
        (db,),
    )
    pf.views = [r[0] for r in cur.fetchall()]
    cur.execute(
        "SELECT ROUTINE_NAME FROM information_schema.ROUTINES "
        "WHERE ROUTINE_SCHEMA = %s",
        (db,),
    )
    pf.routines = [r[0] for r in cur.fetchall()]
    try:
        cur.execute(
            "SELECT EVENT_NAME FROM information_schema.EVENTS WHERE EVENT_SCHEMA = %s",
            (db,),
        )
        pf.events = [r[0] for r in cur.fetchall()]
    except Exception:
        pf.events = []

    parts = []
    if pf.views:
        parts.append(f"view {len(pf.views)} 個")
    if pf.routines:
        parts.append(f"預存程序/函式 {len(pf.routines)} 個")
    if pf.events:
        parts.append(f"排程事件 {len(pf.events)} 個")
    if parts:
        log("其他物件（會一併備份）：" + "、".join(parts))

    # ---- 欄位字元集是否一致 ----
    cur.execute(
        "SELECT DISTINCT CHARACTER_SET_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND CHARACTER_SET_NAME IS NOT NULL",
        (db,),
    )
    pf.mixed_charsets = sorted(r[0] for r in cur.fetchall())
    if len(pf.mixed_charsets) > 1:
        pf.warnings.append(
            "資料庫中混用了多種欄位字元集（"
            + "、".join(pf.mixed_charsets)
            + "）。備份會以 binary 模式匯出，位元組原樣保留，"
            "不做任何編碼轉換——這正是混合字元集下唯一安全的做法。"
        )
    elif pf.mixed_charsets:
        log(f"欄位字元集：{pf.mixed_charsets[0]}（單一）")

    # ---- 其他連線 ----
    cur.execute("SELECT CONNECTION_ID()")
    my_id = cur.fetchone()[0]
    cur.execute("SHOW PROCESSLIST")
    for row in cur.fetchall():
        pid, user, host, rdb = row[0], row[1], row[2], row[3]
        if pid != my_id and rdb == db:
            pf.other_connections.append((pid, user, host))
    if pf.other_connections:
        detail = "、".join(f"{u}@{h}" for _, u, h in pf.other_connections[:10])
        pf.warnings.append(
            f"目前還有 {len(pf.other_connections)} 個連線連到 `{db}`（{detail}）。\n"
            "    逐表備份是分次進行的，備份期間若有人在看診，"
            "不同資料表會停在不同時間點，還原後可能對不起來"
            "（例如病歷有了、處方還沒有）。\n"
            "    請先關閉所有診所端程式再備份。"
        )

    # ---- 輸出目錄 ----
    if not os.path.isdir(out_dir):
        pf.blocking.append(f"輸出目錄不存在：{out_dir}")
    else:
        pf.existing_sql = sorted(f for f in os.listdir(out_dir) if f.endswith(".sql"))
        if pf.existing_sql:
            pf.warnings.append(
                f"輸出目錄已有 {len(pf.existing_sql)} 個 .sql 檔案。"
                "restore_sql.py 還原時會把目錄裡【所有】.sql 都匯入，"
                "新舊混在一起會產生一個不存在於任何時間點的資料庫。"
                "強烈建議勾選「建立時間戳記子目錄」。"
            )
        try:
            free = shutil.disk_usage(out_dir).free
            # 文字形式的 dump 通常小於資料檔本身，但索引不會被匯出、
            # 而數值會變成文字，抓 1.2 倍當保守估計
            needed = int(pf.total_bytes * 1.2)
            log(f"輸出目錄剩餘空間 {fmt_bytes(free)}，估計需要 {fmt_bytes(needed)}")
            if free < needed:
                pf.blocking.append(
                    f"磁碟空間可能不足：剩餘 {fmt_bytes(free)}，"
                    f"估計需要 {fmt_bytes(needed)}。"
                )
        except OSError:
            pass

    return pf


# ---------------------------------------------------------------------------
# 背景工作執行緒
# ---------------------------------------------------------------------------


class DumpWorker(QObject):
    sig_log = pyqtSignal(str)
    sig_progress = pyqtSignal(int, int)
    sig_preflight = pyqtSignal(object)
    sig_finished = pyqtSignal(bool, str)

    def __init__(self, params, dry_run):
        super().__init__()
        self.p = params
        self.dry_run = dry_run

    def log(self, msg):
        self.sig_log.emit(msg)

    def _connect(self):
        conn = mysql.connector.connect(
            host=self.p["host"],
            port=self.p["port"],
            user=self.p["user"],
            password=self.p["password"],
            charset="utf8mb4",
            # 一定要明確指定 collation。mysql-connector-python 內建一張
            # charset → collation 對照表，utf8mb4 會對到 MySQL 8 的預設值
            # utf8mb4_0900_ai_ci；MariaDB 沒有這個 collation，連線當下就會
            # 拋 1273 Unknown collation，連第一次查詢都到不了。
            collation="utf8mb4_general_ci",
            connection_timeout=10,
            autocommit=True,
        )
        return conn, conn.cursor()

    def _write_manifest(self, path, db, pf, files, counts, elapsed):
        """寫出清單檔，供還原後逐項核對。

        副檔名刻意不是 .sql——restore_sql.py 只會匯入 .sql，清單檔不能被
        當成 SQL 執行。
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "資料庫備份清單",
            "=" * 60,
            f"資料庫      : {db}",
            f"字元集      : {pf.charset} / {pf.collation}",
            f"伺服器      : MariaDB {pf.server_version}",
            f"備份時間    : {now}",
            f"耗時        : {fmt_secs(elapsed)}",
            f"資料表數    : {len(pf.tables)}",
            "引擎分佈    : "
            + "、".join(f"{k} {v} 張" for k, v in sorted(pf.engines.items())),
            "",
        ]
        if counts:
            lines += ["各資料表筆數與檔案大小", "-" * 60]
            for table, _e, _s in pf.tables:
                n = counts.get(table)
                fn = files.get(table, "")
                size = (
                    os.path.getsize(os.path.join(os.path.dirname(path), fn))
                    if fn
                    else 0
                )
                lines.append(
                    f"{table:<32} {('' if n is None else n):>10} 筆   "
                    f"{fmt_bytes(size):>10}   {fn}"
                )
            lines.append("")
        if pf.broken:
            lines += [
                "【未備份】以下資料表在引擎裡沒有實體，無法匯出：",
                "  " + "、".join(t for t, _, _ in pf.broken),
                "",
            ]
        lines += [
            "還原方式",
            "-" * 60,
            "以 restore_sql.py 選擇本目錄還原。",
            "還原後請對照上表逐項核對筆數。",
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def run(self):
        conn = None
        cur = None
        try:
            p = self.p
            db = p["database"]
            out_dir = p["out_dir"]
            t_start = time.time()

            conn, cur = self._connect()

            # ---------- 前置檢查 ----------
            self.log("=== 前置檢查（唯讀，不會修改任何資料）===")
            pf = run_preflight(cur, db, out_dir, self.log)

            if not p["mysqldump"]:
                pf.blocking.append(
                    "找不到 mysqldump（或 mariadb-dump）指令。請確認 MariaDB "
                    "的 bin 目錄已加入 PATH，或在 pymedical.conf 的 [tools] "
                    "區段指定路徑。"
                )

            if pf.blocking:
                self.log("\n⛔ 發現阻斷性問題，不可備份：")
                for b in pf.blocking:
                    self.log(f"  ⛔ {b}")
            if pf.warnings:
                self.log("\n⚠ 需要注意的項目：")
                for w in pf.warnings:
                    self.log(f"  ⚠ {w}")
            if not pf.blocking and not pf.warnings:
                self.log("\n✓ 檢查全部通過，沒有發現問題。")

            self.sig_preflight.emit(pf)

            if self.dry_run:
                self.sig_finished.emit(
                    not pf.blocking,
                    "檢查完成。"
                    + (
                        f"發現 {len(pf.blocking)} 項阻斷性問題，請先處理。"
                        if pf.blocking
                        else "可以開始備份。"
                    ),
                )
                return

            if pf.blocking:
                raise RuntimeError(
                    "存在阻斷性問題，已停止：\n  " + "\n  ".join(pf.blocking)
                )

            self.log(f"\n輸出目錄：{out_dir}")

            env = os.environ.copy()
            env["MYSQL_PWD"] = p["password"]
            dump_base = [
                p["mysqldump"],
                f"--host={p['host']}",
                f"--port={p['port']}",
                f"--user={p['user']}",
                # 位元組原樣匯出：不做任何編碼轉換，混合字元集的舊資料庫
                # （big5 與 utf8mb3 並存）也不會失真。restore_sql.py 會從
                # 檔頭的 SET NAMES 自動偵測並以相同模式匯入。
                "--default-character-set=binary",
                "--hex-blob",
                # 一句 INSERT 帶多列。少了它，還原時間會是好幾十倍。
                "--extended-insert",
                "--quick",
                f"--max-allowed-packet={p['max_packet']}",
            ]
            if pf.broken:
                dump_base += [f"--ignore-table={db}.{t}" for t, _, _ in pf.broken]

            # 全部都是 InnoDB 時可用 --single-transaction 取得一致快照而不鎖表；
            # 只要有一張 MyISAM 就沒有用（MyISAM 不支援交易），改用鎖表。
            all_innodb = set(pf.engines) <= {"INNODB"}
            if all_innodb:
                dump_base.append("--single-transaction")
                self.log("全部為 InnoDB，使用 --single-transaction（不鎖表）。")
            else:
                dump_base.append("--lock-tables")
                self.log(
                    "含有非 InnoDB 資料表，使用 --lock-tables"
                    "（匯出期間該資料庫會被鎖住，無法寫入）。"
                )

            # ---------- 逐表匯出 ----------
            total_steps = (
                len(pf.tables)
                + (1 if pf.views else 0)
                + (1 if (pf.routines or pf.events) else 0)
            )
            self.log(f"\n=== 逐表匯出（{len(pf.tables)} 張）===")
            failed = []
            files = {}
            step = 0

            for i, (table, engine, size) in enumerate(pf.tables, start=1):
                step += 1
                self.sig_progress.emit(step, total_steps)
                fn = f"{TABLE_PREFIX}{i:04d}_{safe_filename(table)}.sql"
                out = os.path.join(out_dir, fn)
                t0 = time.time()
                rc, err = run_dump(dump_base + [db, table], env, out)
                if rc != 0:
                    failed.append((table, err))
                    self.log(f"  ✗ [{i}/{len(pf.tables)}] {table}：{err}")
                    continue
                ok, why = verify_dump_file(out)
                if not ok:
                    failed.append((table, why))
                    self.log(f"  ✗ [{i}/{len(pf.tables)}] {table}：{why}")
                    continue
                files[table] = fn
                self.log(
                    f"  ✓ [{i}/{len(pf.tables)}] {table}"
                    f"（{fmt_bytes(os.path.getsize(out))}，"
                    f"{time.time() - t0:.1f} 秒）"
                )

            # ---------- view ----------
            if pf.views:
                step += 1
                self.sig_progress.emit(step, total_steps)
                out = os.path.join(out_dir, VIEWS_FILE)
                rc, err = run_dump(dump_base + ["--no-data", db] + pf.views, env, out)
                ok, why = verify_dump_file(out) if rc == 0 else (False, err)
                if ok:
                    self.log(f"  ✓ {VIEWS_FILE}（{len(pf.views)} 個 view）")
                else:
                    failed.append(("(views)", why))
                    self.log(f"  ✗ {VIEWS_FILE}：{why}")

            # ---------- 預存程序 / 事件 ----------
            if pf.routines or pf.events:
                step += 1
                self.sig_progress.emit(step, total_steps)
                out = os.path.join(out_dir, ROUTINES_FILE)
                rc, err = run_dump(
                    dump_base
                    + [
                        "--no-create-info",
                        "--no-data",
                        "--no-create-db",
                        "--routines",
                        "--events",
                        "--skip-triggers",
                        db,
                    ],
                    env,
                    out,
                )
                ok, why = verify_dump_file(out) if rc == 0 else (False, err)
                if ok:
                    self.log(
                        f"  ✓ {ROUTINES_FILE}"
                        f"（預存程序 {len(pf.routines)}、事件 {len(pf.events)}）"
                    )
                else:
                    failed.append(("(routines)", why))
                    self.log(f"  ✗ {ROUTINES_FILE}：{why}")

            if failed:
                detail = "\n  ".join(f"{n}：{e}" for n, e in failed)
                raise RuntimeError(
                    f"{len(failed)} 項匯出失敗，這份備份【不完整、不可用於"
                    f"還原】：\n  {detail}\n"
                    "請排除問題後重新備份。"
                )

            # ---------- 記錄筆數 ----------
            counts = {}
            if p["record_counts"]:
                self.log("\n=== 記錄各表筆數（供還原後核對）===")
                for i, (table, _e, _s) in enumerate(pf.tables, start=1):
                    self.sig_progress.emit(i, len(pf.tables))
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM `{db}`.`{table}`")
                        counts[table] = int(cur.fetchone()[0])
                    except Exception as e:
                        self.log(f"  ⚠ {table} 筆數取得失敗：{e}")
                self.log(f"已記錄 {len(counts)} 張表的筆數。")

            # ---------- 清單 ----------
            elapsed = time.time() - t_start
            manifest = os.path.join(out_dir, MANIFEST_FILE)
            self._write_manifest(manifest, db, pf, files, counts, elapsed)
            self.log(f"\n已寫出清單：{MANIFEST_FILE}")

            total_size = sum(
                os.path.getsize(os.path.join(out_dir, f))
                for f in os.listdir(out_dir)
                if f.endswith(".sql")
            )

            ok = True
            lines = [
                f"資料庫 `{db}` 備份完成。",
                f"{len(pf.tables)} 張資料表全部匯出成功，每個檔案都通過完整性檢查。",
                f"輸出目錄：{out_dir}",
                f"檔案總大小：{fmt_bytes(total_size)}；耗時 {fmt_secs(elapsed)}。",
            ]
            if pf.broken:
                lines.append(
                    f"⚠ {len(pf.broken)} 張表因為在引擎裡沒有實體而未被備份："
                    + "、".join(t for t, _, _ in pf.broken)
                    + "。"
                )
            if pf.other_connections:
                ok = False
                lines.append(
                    f"⚠ 備份期間有 {len(pf.other_connections)} 個其他連線連著"
                    "資料庫。逐表備份不保證跨資料表的一致性——若當時有人在"
                    "看診，不同資料表可能停在不同時間點。"
                    "請在無人使用時重做一次。"
                )
            lines += [
                "",
                "驗證與還原：",
                f"1. {MANIFEST_FILE} 記錄了各表筆數，還原後可逐項核對。",
                "2. 以 restore_sql.py 選擇本目錄還原。備份檔編碼留在"
                "「自動偵測」即可（會偵測為 binary）。",
                "3. 若只是要原樣搬到別台機器，請【取消勾選】restore_sql.py 的"
                "「還原後轉換為 utf8mb4」——那是編碼升級用的，不是還原用的。",
                "4. 備份能不能用，只有真的還原過一次才知道——"
                "建議定期還原到測試資料庫驗證。",
            ]

            summary = "\n".join(lines)
            self.log("\n=== 備份結束 ===\n" + summary)
            self.sig_finished.emit(ok, summary)

        except Exception as e:
            self.log(f"\n⛔ 已停止：{e}")
            self.sig_finished.emit(False, str(e))
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------


class DumpWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SQL 資料庫備份工具")
        self.resize(700, 700)
        self._thread = None
        self._worker = None
        self._preflight = None
        self._resolved_dir = None
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout()

        self.host_input = self._add_row(layout, "主機:")
        self.port_input = self._add_row(layout, "埠號:")
        self.user_input = self._add_row(layout, "使用者:")
        self.password_input = self._add_row(layout, "密碼:", is_password=True)
        self.database_input = self._add_row(layout, "資料庫:")

        folder_row = QHBoxLayout()
        folder_label = QLabel("備份目錄:")
        folder_label.setFixedWidth(90)
        self.folder_input = QLineEdit()
        browse = QPushButton("瀏覽…")
        browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(browse)
        layout.addLayout(folder_row)

        self.subdir_checkbox = QCheckBox("在備份目錄下建立時間戳記子目錄（建議）")
        self.subdir_checkbox.setChecked(True)
        self.subdir_checkbox.setToolTip(
            "例如 pymedical_20260802_143000。\n"
            "restore_sql.py 還原時會匯入目錄裡的【所有】.sql 檔案，\n"
            "新舊備份混在同一個目錄會產生一個不存在於任何時間點的資料庫。\n"
            "每次備份各自獨立的子目錄可以徹底避免這件事。"
        )
        layout.addWidget(self.subdir_checkbox)

        self.counts_checkbox = QCheckBox("記錄各資料表筆數到清單檔（便於還原後核對）")
        self.counts_checkbox.setChecked(True)
        self.counts_checkbox.setToolTip(
            "以 COUNT(*) 逐表計數，大型資料庫會多花一些時間。\n"
            "還原之後可以拿清單檔逐項核對，確認沒有漏掉資料。"
        )
        layout.addWidget(self.counts_checkbox)

        info_label = QLabel(
            "轉成 InnoDB 之後，備份【不能】再用複製資料夾的方式——\n"
            "InnoDB 的 .ibd 需要 datadir 根目錄的 ibdata1 才能解讀，\n"
            "複製過去會得到「看得到、查不了」的資料表。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #060;")
        layout.addWidget(info_label)

        self.tool_label = QLabel("")
        self.tool_label.setWordWrap(True)
        layout.addWidget(self.tool_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        button_row = QHBoxLayout()
        self.check_button = QPushButton("1. 執行檢查（唯讀）")
        self.check_button.clicked.connect(self.start_check)
        self.dump_button = QPushButton("2. 開始備份")
        self.dump_button.clicked.connect(self.start_dump)
        self.dump_button.setEnabled(False)
        button_row.addWidget(self.check_button)
        button_row.addWidget(self.dump_button)
        layout.addLayout(button_row)

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
            self, "選擇備份目錄", self.folder_input.text() or ""
        )
        if folder:
            self.folder_input.setText(folder)

    def _load_config(self):
        self.mysqldump_path = find_tool("mysqldump", "mariadb-dump")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_dir, "pymedical.conf")
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
                self.mysqldump_path = config["tools"].get(
                    "mysqldump", self.mysqldump_path
                )
        else:
            self.host_input.setText("localhost")
            self.port_input.setText("3306")

        self.folder_input.setText(os.path.join(base_dir, "backup"))
        self.tool_label.setText(f"mysqldump: {self.mysqldump_path or '（未找到）'}")

    def _collect_params(self, create_subdir):
        database = self.database_input.text().strip()
        folder = self.folder_input.text().strip()
        if not database:
            QMessageBox.warning(self, "提示", "請填寫資料庫名稱。")
            return None
        if not folder:
            QMessageBox.warning(self, "提示", "請選擇備份目錄。")
            return None
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "提示", "埠號必須是數字。")
            return None

        out_dir = folder
        if create_subdir and self.subdir_checkbox.isChecked():
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = os.path.join(folder, f"{database}_{stamp}")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "錯誤", f"無法建立目錄：\n{e}")
            return None

        return {
            "host": self.host_input.text().strip(),
            "port": port,
            "user": self.user_input.text().strip(),
            "password": self.password_input.text(),
            "database": database,
            "out_dir": out_dir,
            "record_counts": self.counts_checkbox.isChecked(),
            "max_packet": "256M",
            "mysqldump": self.mysqldump_path,
        }

    def start_check(self):
        # 檢查階段不建立時間戳記子目錄——那會在還沒決定要備份時就留下空目錄
        params = self._collect_params(create_subdir=False)
        if params is None:
            return
        self._preflight = None
        self.dump_button.setEnabled(False)
        self.log_box.clear()
        self._start_worker(params, dry_run=True)

    def start_dump(self):
        params = self._collect_params(create_subdir=True)
        if params is None:
            return
        if self._preflight is None:
            QMessageBox.warning(self, "提示", "請先執行檢查。")
            return
        if self._preflight.blocking:
            QMessageBox.critical(
                self, "無法備份", "檢查發現阻斷性問題，請先處理後重新檢查。"
            )
            return

        pf = self._preflight
        msg = (
            f"即將備份資料庫「{params['database']}」的 {len(pf.tables)} 張"
            f"資料表（合計 {fmt_bytes(pf.total_bytes)}）。\n\n"
            f"輸出目錄：\n{params['out_dir']}"
        )
        if pf.warnings:
            msg += "\n\n檢查時發現以下需注意項目：\n・" + "\n・".join(pf.warnings)
        msg += "\n\n要開始嗎？"

        answer = QMessageBox.question(
            self, "備份前確認", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return

        self.log_box.clear()
        self._start_worker(params, dry_run=False)

    def _start_worker(self, params, dry_run):
        self.check_button.setEnabled(False)
        self.dump_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)

        self._thread = QThread()
        self._worker = DumpWorker(params, dry_run)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.sig_log.connect(self._on_log)
        self._worker.sig_progress.connect(self._on_progress)
        self._worker.sig_preflight.connect(self._on_preflight)
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

    def _on_preflight(self, pf):
        self._preflight = pf

    def _on_finished(self, ok, summary):
        self._thread.quit()
        self._thread.wait()
        was_dry_run = self._worker.dry_run
        self._thread = None
        self._worker = None

        self.check_button.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1 if ok else 0)

        can_dump = (
            self._preflight is not None
            and not self._preflight.blocking
            and bool(self._preflight.tables)
        )
        self.dump_button.setEnabled(can_dump)

        if ok:
            if was_dry_run and can_dump:
                summary += "\n\n可以按「2. 開始備份」。"
            QMessageBox.information(self, "完成", summary)
        else:
            QMessageBox.critical(self, "未完成", summary)

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.warning(
                self, "提示", "備份仍在進行中，請等待完成後再關閉視窗。"
            )
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DumpWindow()
    window.show()
    sys.exit(app.exec_())
