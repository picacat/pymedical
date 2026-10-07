"""
整庫單檔備份還原工具（GUI 版）— restore_database.py

對應的備份格式（pymedical_backup.bat / backup_pymedical.sh 產生）：
    <db>_<yyyymmdd>.7z（內含單一 .sql）或直接是 .sql
    mariadb-dump --databases <db> --default-character-set=binary --hex-blob
                 --routines --events --triggers --extended-insert

逐表目錄格式（backup.py / dump_database.py）請用 restore_sql.py。

安全原則（與 restore_sql.py、restore_pymedical.bat/.sh 一致）：
  1. 還原絕不假裝成功：匯入後比對 dump 內的 CREATE TABLE 與實際資料表，
     少一張就判定失敗。
  2. 密碼透過 MYSQL_PWD 傳遞，不出現在命令列與程序列表。
  3. 目標庫已有資料表時，必須手動輸入庫名確認；並預設先做 prerestore
     快照，快照失敗就中止，不做任何破壞性動作。
  4. dump 自帶的 CREATE DATABASE / USE 一律濾掉，資料只會進到畫面上
     指定的目標庫。（restore_pymedical.sh 曾因此把 muxin 寫進 pymedical：
     USE 會在連線建立後把 session 切走，命令列指定的預設庫完全無效。）
  5. 預設先 DROP 目標庫再匯入：dump 裡只有 DROP TABLE IF EXISTS，
     目標庫裡多出來的表會殘留（孤兒表、錯誤 1932、errno 184）。
  6. 原樣還原：位元組以 dump 宣告的編碼（通常是 binary）灌回，
     引擎、字元集、collation 一律照備份檔，不做任何轉換。
     要轉 InnoDB / utf8mb4，還原後另用 convert_innodb.py。
"""

import configparser
import glob
import locale
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import mysql.connector
from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 與 pymedical_backup.bat 的 BACKUP_DIR 相同
DEFAULT_BACKUP_DIR = r"D:\auto_backup"

# 還原前快照放在備份目錄的子目錄裡。.bat 的保留天數清理只掃第一層
# （Get-ChildItem 不帶 -Recurse），快照不會被 7 天輪替刪掉，要自己清。
SNAPSHOT_SUBDIR = "prerestore"

# 與 classes/mysql_database.py、restore_sql.py 統一
TARGET_COLLATION = "utf8mb4_general_ci"

# 伺服器端 max_allowed_packet 小於此值時，extended-insert 的大型 INSERT
# 可能在匯入中途噴 "server has gone away"。會嘗試暫時拉高，結束後還原。
MIN_SERVER_PACKET = 256 * 1024 * 1024
RAISE_SERVER_PACKET = 1024 * 1024 * 1024

FORBIDDEN_TARGETS = {"mysql", "information_schema", "performance_schema", "sys"}

IMPORT_PROLOGUE = (
    b"SET SESSION unique_checks=0;\n"
    b"SET SESSION foreign_key_checks=0;\n"
    b"SET SESSION autocommit=0;\n"
)
IMPORT_EPILOGUE = b"\nCOMMIT;\n"

# 被濾掉的行改成註解而不是刪掉，mysql 回報的「at line N」才對得上原始檔
FILTER_PREFIX = b"-- [restore_database] "

RE_CREATE_TABLE = re.compile(rb"^CREATE TABLE `([^`]+)`")
RE_CREATE_DB = re.compile(rb"^CREATE\s+DATABASE\b.*?`([^`]+)`", re.IGNORECASE)
RE_USE = re.compile(rb"^USE\s+`([^`]+)`", re.IGNORECASE)
RE_DB_CHARSET = re.compile(
    rb"DEFAULT\s+CHARACTER\s+SET\s+(\w+)(?:\s+COLLATE\s+(\w+))?", re.IGNORECASE
)
RE_ENGINE = re.compile(rb"^\)\s*ENGINE\s*=\s*(\w+)", re.IGNORECASE)
RE_SET_NAMES = re.compile(rb"SET\s+NAMES\s+(\w+)", re.IGNORECASE)

# MariaDB 2024 年中之後的 dump 工具（11.x、12.x）會在第一行寫入
#     /*M!999999\- enable the sandbox mode */
# 舊版 client（例如 pymedical 目錄裡的 10.6 mysql.exe）不認得 \- 這個指令，
# 會在第 1 行直接報錯。這一行只是禁止 dump 執行 shell 指令；備份是自己產生的，
# 拿掉不影響安全性，也讓新舊 client 都能匯入。
SANDBOX_PREFIX = b"/*M!999999\\- enable the sandbox mode"


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------


def subprocess_flags():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def run_cmd(cmd, env=None):
    """執行外部程式，回傳 (returncode, stdout, stderr)。"""
    enc = locale.getpreferredencoding(False) or "utf-8"
    r = subprocess.run(
        cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **subprocess_flags()
    )
    return (
        r.returncode,
        r.stdout.decode(enc, errors="replace"),
        r.stderr.decode(enc, errors="replace"),
    )


def fmt_bytes(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def fmt_secs(seconds):
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m} 分 {s} 秒"
    h, m = divmod(m, 60)
    return f"{h} 小時 {m} 分 {s} 秒"


def find_exe(names, preferred=None):
    """
    依序尋找：設定檔指定的路徑 → pymedical 目錄 → PATH → 常見安裝目錄。

    pymedical 目錄優先，與 system_utils.get_mariadb_dump() 的選擇一致
    （目錄裡隨程式附帶 mariadb-dump.exe 與舊版 mysqldump.exe）。
    """
    if preferred and os.path.isfile(preferred):
        return preferred

    suffix = ".exe" if os.name == "nt" else ""
    for name in names:
        path = os.path.join(SCRIPT_DIR, name + suffix)
        if os.path.isfile(path):
            return path

    for name in names:
        path = shutil.which(name)
        if path:
            return path

    if os.name == "nt":
        dirs = []
        for pattern in (
            r"C:\MariaDB*\bin",
            r"C:\Program Files\MariaDB*\bin",
            r"C:\Program Files\MySQL\*\bin",
        ):
            # 反向排序讓新版目錄排前面（MariaDB 11.7 先於 11.0）
            dirs.extend(sorted(glob.glob(pattern), reverse=True))
        for d in dirs:
            for name in names:
                path = os.path.join(d, name + suffix)
                if os.path.isfile(path):
                    return path
    return None


def find_7z():
    for path in (
        os.path.join(SCRIPT_DIR, "7z.exe"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ):
        if os.path.isfile(path):
            return path
    return shutil.which("7z") or shutil.which("7za")


def dump_completed(path):
    """dump 工具的回傳碼不可信，結尾標記才是完整的證據。"""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 4096))
            return b"-- Dump completed" in f.read()
    except OSError:
        return False


def list_7z_entries(sevenzip, archive):
    """回傳壓縮檔內的 [(路徑, 大小, 是否目錄)]。"""
    rc, out, err = run_cmd([sevenzip, "l", "-slt", archive])
    if rc != 0:
        raise RuntimeError(f"無法讀取壓縮檔內容（7z 回傳 {rc}）：{err or out}")

    text = out.replace("\r\n", "\n")
    marker = "\n----------\n"
    pos = text.find(marker)
    if pos < 0:
        return []

    entries = []
    for block in text[pos + len(marker):].split("\n\n"):
        fields = {}
        for line in block.split("\n"):
            if " = " in line:
                key, value = line.split(" = ", 1)
                fields[key.strip()] = value.strip()
        if "Path" not in fields:
            continue
        is_dir = fields.get("Folder") == "+" or "D" in fields.get("Attributes", "")
        try:
            size = int(fields.get("Size") or 0)
        except ValueError:
            size = 0
        entries.append((fields["Path"], size, is_dir))
    return entries


def filter_reason(line):
    """這一行是否需要在匯入時濾掉，回傳原因或 None。"""
    first = line[:1]
    if first == b"C" and RE_CREATE_DB.match(line):
        return "CREATE DATABASE"
    if first == b"U" and RE_USE.match(line):
        return "USE"
    if first == b"/" and line.startswith(SANDBOX_PREFIX):
        return "sandbox mode"
    return None


def connect(p):
    return mysql.connector.connect(
        host=p["host"],
        port=p["port"],
        user=p["user"],
        password=p["password"],
        charset="utf8mb4",
        # 一定要明確指定 collation，否則 mysql-connector-python 會送出
        # MySQL 8 的 utf8mb4_0900_ai_ci，MariaDB 直接拋 1273。
        collation=TARGET_COLLATION,
        connection_timeout=10,
        autocommit=True,
    )


def cleanup_temp(info):
    if info and info.get("temp_dir"):
        shutil.rmtree(info["temp_dir"], ignore_errors=True)
        info["temp_dir"] = None


# ---------------------------------------------------------------------------
# 分析階段：測試、解壓、掃描（不動任何資料）
# ---------------------------------------------------------------------------


def prescan(job, sql_path):
    """
    掃描整份 dump 的行首，取得：來源資料庫名稱與字元集、資料表清單、
    引擎分佈、SET NAMES 編碼、是否含 sandbox 行。

    只看行首第一個位元組就能排除絕大多數的行，GB 級的檔案也只要幾秒。
    """
    size = os.path.getsize(sql_path) or 1
    create_dbs, use_dbs, tables = [], [], []
    engines = {}
    db_charset = db_collation = None
    sandbox = False

    with open(sql_path, "rb") as f:
        head = f.read(64 * 1024)
        m = RE_SET_NAMES.search(head)
        set_names = m.group(1).decode("ascii", "replace").lower() if m else None
        f.seek(0)

        done = 0
        step = max(size // 200, 1)
        mark = step
        for line in f:
            done += len(line)
            if done >= mark:
                job.progress(int(done * 1000 / size), 1000)
                mark = done + step

            first = line[:1]
            if first == b"C":
                m = RE_CREATE_TABLE.match(line)
                if m:
                    tables.append(m.group(1).decode("utf-8", "replace"))
                    continue
                m = RE_CREATE_DB.match(line)
                if m:
                    name = m.group(1).decode("utf-8", "replace")
                    if name not in create_dbs:
                        create_dbs.append(name)
                    mc = RE_DB_CHARSET.search(line)
                    if mc and db_charset is None:
                        db_charset = mc.group(1).decode("ascii", "replace")
                        if mc.group(2):
                            db_collation = mc.group(2).decode("ascii", "replace")
            elif first == b")":
                m = RE_ENGINE.match(line)
                if m:
                    eng = m.group(1).decode("ascii", "replace").upper()
                    engines[eng] = engines.get(eng, 0) + 1
            elif first == b"U":
                m = RE_USE.match(line)
                if m:
                    name = m.group(1).decode("utf-8", "replace")
                    if name not in use_dbs:
                        use_dbs.append(name)
            elif first == b"/" and line.startswith(SANDBOX_PREFIX):
                sandbox = True

    job.progress(1000, 1000)
    return {
        "set_names": set_names,
        "create_dbs": create_dbs,
        "use_dbs": use_dbs,
        "tables": tables,
        "engines": engines,
        "db_charset": db_charset,
        "db_collation": db_collation,
        "sandbox": sandbox,
    }


def analyze(job, p):
    info = {"source": p["backup_file"], "temp_dir": None}
    try:
        _analyze(job, p, info)
    except Exception:
        cleanup_temp(info)
        raise
    return info


def _analyze(job, p, info):
    target = p["database"]
    src = p["backup_file"]

    # ---------- 1. 連線與目標庫現況 ----------
    job.log("[分析 1/4] 連線並檢查目標資料庫 …")
    job.busy()
    conn = connect(p)
    try:
        cur = conn.cursor()
        cur.execute("SELECT VERSION(), @@lower_case_table_names")
        version, lctn = cur.fetchone()
        info["server_version"] = version
        info["lctn"] = int(lctn)

        cur.execute(
            "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
            (target,),
        )
        info["target_exists"] = cur.fetchone()[0] > 0

        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(ENGINE <> 'InnoDB'), 0) "
            "FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
            (target,),
        )
        n, nontrx = cur.fetchone()
        info["target_tables"] = int(n)
        info["target_nontrx"] = int(nontrx)
        cur.close()
    finally:
        conn.close()

    job.log(
        f"  伺服器 {version}（lower_case_table_names={info['lctn']}）；"
        + (
            f"目標庫 `{target}` 已存在，{info['target_tables']} 張資料表。"
            if info["target_exists"]
            else f"目標庫 `{target}` 不存在，將新建。"
        )
    )

    # ---------- 2. 取得 .sql（必要時解壓） ----------
    if not os.path.isfile(src):
        raise RuntimeError(f"找不到備份檔：{src}")

    lower = src.lower()
    if lower.endswith(".7z"):
        sevenzip = p["sevenzip"]
        if not sevenzip:
            raise RuntimeError(
                "找不到 7z.exe，無法解壓縮。請把 7z.exe 放在 pymedical 目錄，"
                "或安裝 7-Zip。"
            )

        job.log("\n[分析 2/4] 測試並解壓縮 …")
        job.busy()
        rc, out, err = run_cmd([sevenzip, "t", src])
        if rc != 0:
            raise RuntimeError(
                f"壓縮檔測試失敗（7z 回傳 {rc}），檔案可能已損壞：\n{(err or out).strip()}"
            )
        job.log("  ✓ 壓縮檔測試通過")

        files = [e for e in list_7z_entries(sevenzip, src) if not e[2]]
        sqls = [e for e in files if e[0].lower().endswith(".sql")]
        if len(sqls) != 1:
            raise RuntimeError(
                "壓縮檔內應該只有一個 .sql，實際內容："
                + ("、".join(e[0] for e in files) or "（空）")
            )
        size = sqls[0][1]

        # 優先解壓到備份檔旁邊（通常是 D 槽，空間較足），不行再退回系統暫存目錄
        need = int(size * 1.05) + 256 * 1024 * 1024
        temp_dir = None
        tried = []
        for base in (os.path.dirname(os.path.abspath(src)), tempfile.gettempdir()):
            try:
                free = shutil.disk_usage(base).free
            except OSError:
                continue
            tried.append(f"{base}（剩 {fmt_bytes(free)}）")
            if free < need:
                continue
            try:
                temp_dir = tempfile.mkdtemp(prefix="_restore_tmp_", dir=base)
                break
            except OSError:
                continue
        if not temp_dir:
            raise RuntimeError(
                f"空間不足，無法解壓（需要約 {fmt_bytes(need)}）：" + "；".join(tried)
            )
        info["temp_dir"] = temp_dir

        job.log(f"  解壓縮到 {temp_dir}（{fmt_bytes(size)}）…")
        rc, out, err = run_cmd([sevenzip, "e", f"-o{temp_dir}", "-y", src])
        if rc != 0:
            raise RuntimeError(f"解壓縮失敗（7z 回傳 {rc}）：{(err or out).strip()}")

        extracted = [f for f in os.listdir(temp_dir) if f.lower().endswith(".sql")]
        if len(extracted) != 1:
            raise RuntimeError("解壓後找不到唯一的 .sql 檔。")
        sql_path = os.path.join(temp_dir, extracted[0])
        job.log("  ✓ 解壓完成")
    elif lower.endswith(".sql"):
        job.log("\n[分析 2/4] 備份檔為 .sql，不需解壓。")
        sql_path = src
    else:
        raise RuntimeError("只支援 .7z 與 .sql 備份檔。")

    info["sql_path"] = sql_path
    info["sql_size"] = os.path.getsize(sql_path)

    # ---------- 3. 完整性 ----------
    job.log("\n[分析 3/4] 檢查 dump 是否完整 …")
    if not dump_completed(sql_path):
        raise RuntimeError(
            "找不到結尾的 '-- Dump completed' 標記，這份備份被截斷，不可用來還原。"
        )
    job.log("  ✓ 結尾標記存在")

    # ---------- 4. 內容掃描 ----------
    job.log("\n[分析 4/4] 掃描備份檔內容 …")
    scan = prescan(job, sql_path)
    info.update(scan)

    dbs = list(dict.fromkeys(scan["create_dbs"] + scan["use_dbs"]))
    if len(dbs) > 1:
        raise RuntimeError(
            f"這份 dump 含有多個資料庫（{'、'.join(dbs)}），本工具只還原單一資料庫。"
        )
    info["src_db"] = dbs[0] if dbs else None

    if not scan["tables"]:
        raise RuntimeError("備份檔裡沒有任何 CREATE TABLE，不是有效的資料庫備份。")

    if not scan["set_names"]:
        info["set_names"] = "binary"
        job.log("  ⚠ 檔頭沒有 SET NAMES 宣告，以 binary 匯入（不轉碼）。")

    # 表名大小寫：Windows（lower_case_table_names=1）會折成小寫，
    # Debian（=0）大小寫敏感——shenmin 的 ReturnGoods 就是這樣來的。
    groups = {}
    for t in scan["tables"]:
        groups.setdefault(t.lower(), []).append(t)
    info["case_dups"] = [v for v in groups.values() if len(v) > 1]
    info["upper_tables"] = [t for t in scan["tables"] if t != t.lower()]

    engines = "、".join(f"{e} {c} 張" for e, c in sorted(scan["engines"].items()))
    job.log(
        f"  來源資料庫：{info['src_db'] or '（dump 未指定）'}；"
        f"{len(scan['tables'])} 張資料表（{engines or '引擎不明'}）；"
        f"編碼 {info['set_names']}。"
    )


# ---------------------------------------------------------------------------
# 還原階段
# ---------------------------------------------------------------------------


def make_snapshot(job, p, info):
    """還原前先把目標庫完整備份一份。任何一步失敗都中止整個還原。"""
    dump = p["dump"]
    if not dump:
        raise RuntimeError(
            "找不到 mariadb-dump / mysqldump，無法建立還原前快照。"
            "若確定不需要快照，請取消勾選「還原前先快照」。"
        )

    base = p["backup_dir"] if os.path.isdir(p["backup_dir"]) else SCRIPT_DIR
    snap_dir = os.path.join(base, SNAPSHOT_SUBDIR)
    os.makedirs(snap_dir, exist_ok=True)

    target = p["database"]
    name = f"{target}_prerestore_{time.strftime('%Y%m%d_%H%M%S')}"
    sql = os.path.join(snap_dir, name + ".sql")

    lock = (
        ["--single-transaction"] if info["target_nontrx"] == 0 else ["--lock-all-tables"]
    )
    head = [
        dump,
        f"--host={p['host']}",
        f"--port={p['port']}",
        f"--user={p['user']}",
        *lock,
        "--quick",
        "--default-character-set=binary",
        "--hex-blob",
        "--routines",
        "--triggers",
        "--extended-insert",
    ]
    tail = ["--databases", target, f"--result-file={sql}"]
    env = os.environ.copy()
    env["MYSQL_PWD"] = p["password"]

    job.busy()
    rc, _, err = run_cmd(head + ["--events"] + tail, env=env)
    if rc != 0:
        # MySQL 5.0 與部分舊版不支援 --events
        job.log(f"  ⚠ 快照失敗（{err.strip()[:200]}），改用不含 --events 重試 …")
        if os.path.exists(sql):
            os.remove(sql)
        rc, _, err = run_cmd(head + tail, env=env)

    if rc != 0 or not dump_completed(sql):
        if os.path.exists(sql):
            os.remove(sql)
        raise RuntimeError(f"還原前快照失敗：{err.strip() or '結尾標記不存在'}")

    final = sql
    sevenzip = p["sevenzip"]
    if sevenzip:
        archive = os.path.join(snap_dir, name + ".7z")
        rc, _, _ = run_cmd([sevenzip, "a", "-mx=5", "-mmt=on", archive, sql])
        if rc == 0 and run_cmd([sevenzip, "t", archive])[0] == 0:
            os.remove(sql)
            final = archive
        else:
            job.log("  ⚠ 快照壓縮失敗，保留未壓縮的 .sql。")
            if os.path.exists(archive):
                os.remove(archive)

    job.log(f"  ✓ 快照：{final}（{fmt_bytes(os.path.getsize(final))}）")
    return final


def adjust_server(job, cur, p, saved):
    """暫時調整全域設定，原值記在 saved，結束時由 restore_server 還原。"""
    try:
        cur.execute("SELECT @@GLOBAL.max_allowed_packet")
        old = int(cur.fetchone()[0])
        if old < MIN_SERVER_PACKET:
            cur.execute(f"SET GLOBAL max_allowed_packet = {RAISE_SERVER_PACKET}")
            saved["max_allowed_packet"] = old
            job.log(
                f"  已暫時把伺服器 max_allowed_packet 從 {fmt_bytes(old)} "
                f"拉高到 {fmt_bytes(RAISE_SERVER_PACKET)}。"
            )
    except Exception as e:
        job.log(
            f"  ⚠ 伺服器 max_allowed_packet 偏小且無法調整（{e}），"
            f"大型 INSERT 可能在中途噴 server has gone away。"
        )

    if p["relax"]:
        try:
            cur.execute(
                "SELECT @@GLOBAL.innodb_flush_log_at_trx_commit, @@GLOBAL.sync_binlog"
            )
            flush, sync = cur.fetchone()
            cur.execute("SET GLOBAL innodb_flush_log_at_trx_commit = 2")
            saved["innodb_flush_log_at_trx_commit"] = int(flush)
            cur.execute("SET GLOBAL sync_binlog = 0")
            saved["sync_binlog"] = int(sync)
            job.log(
                f"  已暫時放寬持久性設定（innodb_flush_log_at_trx_commit {flush}→2、"
                f"sync_binlog {sync}→0），結束後還原。"
            )
        except Exception as e:
            job.log(f"  （無法調整持久性設定，略過此優化：{e}）")


def restore_server(job, conn, saved):
    if not saved:
        return
    try:
        conn.ping(reconnect=True, attempts=3, delay=2)
        cur = conn.cursor()
    except Exception as e:
        job.log(f"⚠ 無法重新連線以還原伺服器設定（{e}），請手動執行：")
        for var, val in saved.items():
            job.log(f"    SET GLOBAL {var} = {val};")
        return
    for var, val in saved.items():
        try:
            cur.execute(f"SET GLOBAL {var} = {int(val)}")
            job.log(f"  已還原 {var} = {val}")
        except Exception as e:
            job.log(f"⚠ {var} 還原失敗（{e}），請手動執行：SET GLOBAL {var} = {val};")
    cur.close()


def prepare_target(job, cur, p, info, state):
    target = p["database"]
    exists = info["target_exists"]

    if exists and p["drop_first"]:
        job.log(f"  刪除目標資料庫 `{target}` …")
        state["touched"] = True
        try:
            cur.execute(f"DROP DATABASE `{target}`")
        except mysql.connector.Error as e:
            raise RuntimeError(
                f"DROP DATABASE 失敗：{e}\n"
                f"（errno 1010 多半是資料目錄裡有不屬於資料庫的殘留檔案，"
                f"請手動清理 datadir 下的 {target} 目錄）"
            ) from e
        exists = False

    if exists:
        job.log(f"  `{target}` 保留現狀（未勾選先刪除），備份中沒有的資料表會殘留。")
        return

    # 照 dump 原本的字元集／collation 建庫。collation 在此伺服器不存在時
    # （例如 uca1400 的備份還原到 10.x）退一步只帶字元集。
    clauses = []
    cs, coll = info.get("db_charset"), info.get("db_collation")
    if cs:
        if coll:
            clauses.append(f"DEFAULT CHARACTER SET {cs} COLLATE {coll}")
        clauses.append(f"DEFAULT CHARACTER SET {cs}")
    clauses.append(f"DEFAULT CHARACTER SET utf8mb4 COLLATE {TARGET_COLLATION}")

    last_error = None
    for clause in clauses:
        try:
            cur.execute(f"CREATE DATABASE `{target}` {clause}")
            job.log(f"  已建立 `{target}`（{clause}）。")
            state["touched"] = True
            return
        except mysql.connector.Error as e:
            last_error = e
            job.log(f"  （{clause} 失敗：{e}，改用下一個）")
    raise RuntimeError(f"無法建立目標資料庫：{last_error}")


def import_dump(job, p, info):
    env = os.environ.copy()
    env["MYSQL_PWD"] = p["password"]
    cmd = [
        p["client"],
        f"--host={p['host']}",
        f"--port={p['port']}",
        f"--user={p['user']}",
        f"--default-character-set={info['set_names']}",
        "--max-allowed-packet=1G",
        p["database"],  # 預設庫；dump 裡的 USE 已濾掉，所以這裡說了算
    ]

    sql_path = info["sql_path"]
    size = info["sql_size"] or 1
    removed = {}
    write_error = ""

    # stderr 寫到暫存檔而不是 PIPE：一邊寫 stdin 一邊不讀 stderr，
    # 錯誤訊息一多就會把管線塞滿造成死結。
    with tempfile.TemporaryFile() as errf:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=errf,
            bufsize=1024 * 1024,
            **subprocess_flags(),
        )
        try:
            out = proc.stdin
            out.write(IMPORT_PROLOGUE)
            done = 0
            step = max(size // 500, 1)
            mark = step
            with open(sql_path, "rb") as f:
                for line in f:
                    done += len(line)
                    reason = filter_reason(line)
                    if reason:
                        removed[reason] = removed.get(reason, 0) + 1
                        if reason == "sandbox mode":
                            # 整行換掉，不留反斜線給舊版 client 解析
                            line = FILTER_PREFIX + b"removed sandbox-mode line\n"
                        else:
                            line = FILTER_PREFIX + line
                    out.write(line)
                    if done >= mark:
                        job.progress(int(done * 1000 / size), 1000)
                        mark = done + step
            out.write(IMPORT_EPILOGUE)
        except (BrokenPipeError, OSError, ValueError) as e:
            # 多半代表 mysql 已因 SQL 錯誤提早結束，真正原因在 stderr
            write_error = f"（送入資料中斷：{type(e).__name__}: {e}）"
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass

        rc = proc.wait()
        errf.seek(0)
        err = errf.read().decode("utf-8", errors="replace").strip()

    for reason, count in removed.items():
        job.log(f"  · 已濾掉 {count} 行 {reason}")

    if rc != 0 or write_error:
        raise RuntimeError(f"匯入失敗（client 回傳 {rc}）：{err} {write_error}".strip())
    if err:
        job.log(f"  client 訊息：{err}")
    job.progress(1000, 1000)


def restore(job, p, info):
    target = p["database"]
    t_start = time.time()
    timings = []
    state = {"touched": False}
    snapshot_path = ""
    saved = {}

    conn = connect(p)
    try:
        try:
            cur = conn.cursor()

            # ---------- 1. 快照 ----------
            if info["target_tables"] and p["snapshot"]:
                job.log(f"[步驟 1/5] 建立 `{target}` 的還原前快照 …")
                t0 = time.time()
                snapshot_path = make_snapshot(job, p, info)
                timings.append(("快照", time.time() - t0))
            else:
                job.log("[步驟 1/5] 略過快照（目標庫不存在、為空，或未勾選）。")

            # ---------- 2. 伺服器設定與目標庫 ----------
            job.log("\n[步驟 2/5] 準備伺服器設定與目標資料庫 …")
            adjust_server(job, cur, p, saved)
            prepare_target(job, cur, p, info, state)

            # ---------- 3. 匯入 ----------
            job.log(
                f"\n[步驟 3/5] 匯入 {fmt_bytes(info['sql_size'])}"
                f"（以 {info['set_names']} 編碼原樣灌回）…"
            )
            state["touched"] = True
            t0 = time.time()
            import_dump(job, p, info)
            timings.append(("匯入", time.time() - t0))
            job.log(f"  ✓ 匯入完成（{fmt_secs(timings[-1][1])}）")

            # 長時間匯入後連線可能已逾時
            conn.ping(reconnect=True, attempts=3, delay=2)
            cur = conn.cursor()

            # ---------- 4. 核對 ----------
            job.log("\n[步驟 4/5] 核對資料表 …")
            job.busy()
            cur.execute(
                "SELECT TABLE_NAME, ENGINE, TABLE_TYPE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s",
                (target,),
            )
            rows = cur.fetchall()
            base_tables = [r[0] for r in rows if r[2] == "BASE TABLE"]
            n_views = sum(1 for r in rows if r[2] == "VIEW")
            engine_count = {}
            for _name, eng, ttype in rows:
                if ttype == "BASE TABLE":
                    key = (eng or "?").upper()
                    engine_count[key] = engine_count.get(key, 0) + 1

            fold = info["lctn"] != 0
            norm = (lambda s: s.lower()) if fold else (lambda s: s)
            expected = {norm(t) for t in info["tables"]}
            actual = {norm(t) for t in base_tables}
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)

            if missing:
                raise RuntimeError(
                    f"還原後缺少 {len(missing)} 張資料表："
                    + "、".join(missing[:20])
                    + ("…" if len(missing) > 20 else "")
                )
            job.log(
                f"  ✓ 備份檔 {len(info['tables'])} 張資料表全部到位"
                + (f"、{n_views} 個檢視表" if n_views else "")
                + "。"
            )

            # ---------- 5. 統計資訊 ----------
            job.log("\n[步驟 5/5] 更新統計資訊 …")
            t0 = time.time()
            analyze_failed = []
            for i, table in enumerate(base_tables, start=1):
                job.progress(i, len(base_tables))
                try:
                    cur.execute(f"ANALYZE TABLE `{target}`.`{table}`")
                    cur.fetchall()
                except Exception as e:
                    analyze_failed.append(table)
                    job.log(f"  ⚠ {table}：{e}")
            timings.append(("統計更新", time.time() - t0))

            cur.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (target,),
            )
            db_cs, db_coll = cur.fetchone()
            cur.close()

        except Exception as e:
            msg = str(e)
            if not state["touched"]:
                msg += "\n\n目標資料庫未被更動。"
            else:
                msg += f"\n\n⚠ 目標資料庫 `{target}` 目前【不完整】，請勿直接使用。"
                if snapshot_path:
                    msg += (
                        f"\n還原前的快照：{snapshot_path}"
                        f"\n可在本工具選取該檔還原回原狀。"
                    )
            raise RuntimeError(msg) from e
    finally:
        restore_server(job, conn, saved)
        try:
            conn.close()
        except Exception:
            pass

    # ---------- 摘要 ----------
    total = time.time() - t_start
    engines = "、".join(f"{e} {c} 張" for e, c in sorted(engine_count.items()))
    lines = [
        f"資料庫 `{target}` 還原完成：{len(base_tables)} 張資料表"
        + (f"、{n_views} 個檢視表" if n_views else "")
        + "，與備份檔一致。",
        f"來源：{os.path.basename(info['source'])}"
        + (f"（dump 內的資料庫：{info['src_db']}）" if info["src_db"] else ""),
        f"引擎：{engines}；字元集：{db_cs} / {db_coll}。",
        "耗時：總計 "
        + fmt_secs(total)
        + "（"
        + "、".join(f"{k} {fmt_secs(v)}" for k, v in timings)
        + "）。",
    ]
    if snapshot_path:
        lines.append(f"還原前快照：{snapshot_path}（確認無誤後可自行刪除）")
    if engine_count.get("MYISAM"):
        lines.append(
            f"⚠ 有 {engine_count['MYISAM']} 張 MyISAM 資料表（照備份原樣）。"
            f"需要的話請另用 convert_innodb.py 轉換。"
        )
    if extra:
        lines.append(
            f"注意：目標庫另有 {len(extra)} 張備份裡沒有的資料表（未勾選先刪除）："
            + "、".join(extra[:20])
        )
    if analyze_failed:
        lines.append(
            f"注意：{len(analyze_failed)} 張表統計更新失敗（不影響資料正確性）："
            + "、".join(analyze_failed)
        )
    lines.append("建議抽查主要資料表的筆數（如 cases、patient）確認內容。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 背景工作
# ---------------------------------------------------------------------------


class Job(QObject):
    sig_log = pyqtSignal(str)
    sig_progress = pyqtSignal(int, int)
    sig_done = pyqtSignal(bool, object)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn = fn
        self.args = args

    def log(self, msg):
        self.sig_log.emit(msg)

    def progress(self, current, total):
        self.sig_progress.emit(current, total)

    def busy(self):
        self.sig_progress.emit(0, 0)

    def run(self):
        try:
            result = self.fn(self, *self.args)
            self.sig_done.emit(True, result)
        except Exception as e:
            self.sig_done.emit(False, e)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------


class RestoreWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("整庫備份還原工具（.7z / .sql）")
        self.resize(680, 760)
        self._thread = None
        self._job = None
        self._pending = None
        self._info = None
        self._setup_ui()
        self._load_config()
        self._refresh_list()

    # -- 介面 -------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout()

        self.host_input = self._add_row(layout, "主機:")
        self.port_input = self._add_row(layout, "埠號:")
        self.user_input = self._add_row(layout, "使用者:")
        self.password_input = self._add_row(layout, "密碼:", is_password=True)
        self.database_input = self._add_row(layout, "目標資料庫:")

        folder_row = QHBoxLayout()
        folder_label = QLabel("備份目錄:")
        folder_label.setFixedWidth(90)
        self.folder_input = QLineEdit()
        self.folder_input.editingFinished.connect(self._refresh_list)
        browse_button = QPushButton("瀏覽…")
        browse_button.clicked.connect(self._browse_folder)
        refresh_button = QPushButton("重新整理")
        refresh_button.clicked.connect(self._refresh_list)
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(browse_button)
        folder_row.addWidget(refresh_button)
        layout.addLayout(folder_row)

        layout.addWidget(QLabel("選擇要還原的備份檔（新到舊）:"))
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(160)
        layout.addWidget(self.file_list)

        other_button = QPushButton("選擇其他位置的備份檔…")
        other_button.clicked.connect(self._browse_file)
        layout.addWidget(other_button)

        self.drop_checkbox = QCheckBox(
            "還原前先刪除目標資料庫（建議；避免殘留備份裡沒有的資料表）"
        )
        self.drop_checkbox.setChecked(True)
        layout.addWidget(self.drop_checkbox)

        self.snapshot_checkbox = QCheckBox(
            f"還原前先快照目前的目標資料庫（存到備份目錄的 {SNAPSHOT_SUBDIR} 子目錄）"
        )
        self.snapshot_checkbox.setChecked(True)
        layout.addWidget(self.snapshot_checkbox)

        self.relax_checkbox = QCheckBox(
            "還原期間暫時放寬 InnoDB 持久性設定以加速（需 SUPER 權限，結束後自動還原）"
        )
        self.relax_checkbox.setChecked(True)
        self.relax_checkbox.setToolTip(
            "暫時設定 innodb_flush_log_at_trx_commit=2、sync_binlog=0。\n"
            "這是全域設定，會影響同一台伺服器上的其他資料庫，\n"
            "請勿在營業時段對線上主機使用。"
        )
        layout.addWidget(self.relax_checkbox)

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

    def _load_config(self):
        conf_mysql = None
        config_file = os.path.join(SCRIPT_DIR, "pymedical.conf")
        if os.path.exists(config_file):
            config = configparser.ConfigParser(interpolation=None)
            # utf-8-sig：設定檔可能帶 BOM
            config.read(config_file, encoding="utf-8-sig")
            db = config["db"] if "db" in config else {}
            self.host_input.setText(db.get("host", "localhost"))
            self.port_input.setText(db.get("port", "3306"))
            self.user_input.setText(db.get("user", "root"))
            self.password_input.setText(db.get("password", ""))
            self.database_input.setText(db.get("database", ""))
            if "tools" in config:
                conf_mysql = config["tools"].get("mysql")
        else:
            self.host_input.setText("localhost")
            self.port_input.setText("3306")
            self.user_input.setText("root")

        self.client = find_exe(["mariadb", "mysql"], preferred=conf_mysql)
        self.dump = find_exe(["mariadb-dump", "mysqldump"])
        self.sevenzip = find_7z()

        self.folder_input.setText(
            DEFAULT_BACKUP_DIR if os.path.isdir(DEFAULT_BACKUP_DIR) else SCRIPT_DIR
        )
        self.tool_label.setText(
            f"client: {self.client or '（未找到）'}\n"
            f"dump:   {self.dump or '（未找到，無法做還原前快照）'}\n"
            f"7-Zip:  {self.sevenzip or '（未找到，只能還原 .sql）'}"
        )

    def _refresh_list(self):
        self.file_list.clear()
        folder = self.folder_input.text().strip()
        if not os.path.isdir(folder):
            return

        found = []
        for sub, tag in (("", ""), (SNAPSHOT_SUBDIR, "[還原前快照] ")):
            d = os.path.join(folder, sub) if sub else folder
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                if not name.lower().endswith((".7z", ".sql")):
                    continue
                path = os.path.join(d, name)
                if os.path.isfile(path):
                    found.append((os.path.getmtime(path), tag, name, path))

        for mtime, tag, name, path in sorted(found, reverse=True):
            text = (
                f"{tag}{name}    {fmt_bytes(os.path.getsize(path))}    "
                f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, path)
            self.file_list.addItem(item)

        if self.file_list.count():
            self.file_list.setCurrentRow(0)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "選擇備份目錄", self.folder_input.text() or ""
        )
        if folder:
            self.folder_input.setText(folder)
            self._refresh_list()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇備份檔",
            self.folder_input.text() or "",
            "備份檔 (*.7z *.sql);;所有檔案 (*)",
        )
        if path:
            item = QListWidgetItem(f"[另選] {path}")
            item.setData(Qt.UserRole, path)
            self.file_list.insertItem(0, item)
            self.file_list.setCurrentRow(0)

    # -- 流程 -------------------------------------------------------------
    def start_restore(self):
        item = self.file_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "提示", "請先選擇要還原的備份檔。")
            return
        database = self.database_input.text().strip()
        if not database or "`" in database:
            QMessageBox.warning(self, "提示", "請填寫有效的目標資料庫名稱。")
            return
        if database.lower() in FORBIDDEN_TARGETS:
            QMessageBox.critical(self, "錯誤", f"不可還原到系統資料庫 `{database}`。")
            return
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "提示", "埠號必須是數字。")
            return
        if not self.client:
            QMessageBox.critical(
                self,
                "錯誤",
                "找不到 mariadb.exe / mysql.exe。\n"
                "請把它放在 pymedical 目錄、加入 PATH，"
                "或在 pymedical.conf 的 [tools] 區段指定 mysql 路徑。",
            )
            return

        params = {
            "host": self.host_input.text().strip(),
            "port": port,
            "user": self.user_input.text().strip(),
            "password": self.password_input.text(),
            "database": database,
            "backup_file": item.data(Qt.UserRole),
            "backup_dir": self.folder_input.text().strip(),
            "drop_first": self.drop_checkbox.isChecked(),
            "snapshot": self.snapshot_checkbox.isChecked(),
            "relax": self.relax_checkbox.isChecked(),
            "client": self.client,
            "dump": self.dump,
            "sevenzip": self.sevenzip,
        }

        self.log_box.clear()
        self._set_running(True)
        self._run(analyze, (params,), lambda ok, r: self._on_analyzed(params, ok, r))

    def _on_analyzed(self, params, ok, result):
        if not ok:
            self._on_log(f"\n⚠ 已停止：{result}")
            self._set_running(False)
            QMessageBox.critical(self, "無法還原", str(result))
            return

        info = result
        self._info = info
        if not self._confirm(params, info):
            cleanup_temp(info)
            self._info = None
            self._on_log("\n已取消，未做任何變更。")
            self._set_running(False)
            return

        self._on_log("\n=== 開始還原 ===")
        self._run(restore, (params, info), self._on_restored)

    def _on_restored(self, ok, result):
        cleanup_temp(self._info)
        self._info = None
        self._set_running(False)
        if ok:
            self._on_log("\n=== 還原結束 ===\n" + result)
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
            QMessageBox.information(self, "還原完成", result)
        else:
            self._on_log(f"\n⚠ 已停止：{result}")
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            QMessageBox.critical(self, "還原未完成", str(result))
        self._refresh_list()

    def _confirm(self, p, info):
        target = p["database"]
        src_db = info["src_db"]
        engines = "、".join(f"{e} {c} 張" for e, c in sorted(info["engines"].items()))
        is_archive = info["source"].lower().endswith(".7z")

        lines = [
            f"備份檔：{os.path.basename(info['source'])}"
            + (
                f"（解壓後 {fmt_bytes(info['sql_size'])}）"
                if is_archive
                else f"（{fmt_bytes(info['sql_size'])}）"
            ),
            f"dump 內的資料庫：{src_db or '（未指定）'}　→　還原到：{target}",
            f"資料表：{len(info['tables'])} 張（{engines or '引擎不明'}）",
            f"備份檔編碼：{info['set_names']}（原樣灌回，不轉碼）",
            f"伺服器：{info['server_version']}",
            (
                f"目標資料庫：已存在，內含 {info['target_tables']} 張資料表"
                if info["target_exists"]
                else "目標資料庫：不存在，將新建"
            ),
        ]
        if info["target_tables"] and p["snapshot"]:
            lines.append(f"還原前快照：會先完整備份 `{target}`，失敗就中止")

        warns = []
        if src_db and src_db != target:
            warns.append(
                f"備份來源是 `{src_db}`，將寫進 `{target}`。"
                f"dump 內的 CREATE DATABASE / USE 會被濾掉，`{src_db}` 不受影響。"
            )
        if info["target_tables"]:
            if p["drop_first"]:
                warns.append(
                    f"⚠ 會先 DROP DATABASE `{target}`："
                    f"現有 {info['target_tables']} 張資料表全部刪除後再匯入。"
                )
            else:
                warns.append(
                    "⚠ 未勾選先刪除：同名資料表會被覆蓋，"
                    "備份裡沒有的資料表會殘留在目標庫。"
                )
            if not p["snapshot"]:
                warns.append("⚠ 未勾選還原前快照：一旦開始，目前的資料將無法復原。")
        myisam = info["engines"].get("MYISAM", 0)
        if myisam:
            warns.append(
                f"⚠ 備份中有 {myisam} 張 MyISAM 資料表，會照原樣還原成 MyISAM"
                f"（多半是轉換 InnoDB 之前的舊備份）。"
            )
        if info["case_dups"] and info["lctn"] != 0:
            dups = "、".join("/".join(g) for g in info["case_dups"])
            warns.append(
                f"⚠ 備份裡有只差大小寫的同名資料表（{dups}）。此伺服器"
                f"（lower_case_table_names={info['lctn']}）不分大小寫，"
                f"它們會互相覆蓋，只留下最後一張。"
            )
        if info["upper_tables"] and info["lctn"] == 0:
            preview = "、".join(info["upper_tables"][:5])
            warns.append(
                f"注意：{len(info['upper_tables'])} 張資料表名稱含大寫（{preview}）。"
                f"此伺服器大小寫敏感，程式若以小寫存取會找不到表。"
            )
        if p["relax"]:
            warns.append("· 會暫時放寬伺服器全域持久性設定，結束後自動還原。")

        text = "\n".join(lines)
        if warns:
            text += "\n\n" + "\n\n".join(warns)
        text += "\n\n要開始嗎？"

        answer = QMessageBox.question(
            self, "還原前確認", text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return False

        if info["target_tables"]:
            typed, ok = QInputDialog.getText(
                self,
                "再次確認",
                f"目標資料庫 `{target}` 內有 {info['target_tables']} 張資料表，"
                f"將被覆蓋。\n請輸入資料庫名稱以確認：",
            )
            if not ok or typed.strip() != target:
                if ok:
                    QMessageBox.warning(self, "提示", "名稱不符，已取消。")
                return False
        return True

    # -- 背景執行 -----------------------------------------------------------
    def _run(self, fn, args, on_done):
        self._pending = on_done
        self._thread = QThread()
        self._job = Job(fn, *args)
        self._job.moveToThread(self._thread)
        self._thread.started.connect(self._job.run)
        self._job.sig_log.connect(self._on_log)
        self._job.sig_progress.connect(self._on_progress)
        self._job.sig_done.connect(self._on_job_done)
        self._thread.start()

    def _on_job_done(self, ok, result):
        self._thread.quit()
        self._thread.wait()
        self._thread = None
        self._job = None
        callback, self._pending = self._pending, None
        if callback:
            callback(ok, result)

    def _set_running(self, running):
        self.start_button.setEnabled(not running)
        self.file_list.setEnabled(not running)
        for w in (
            self.host_input,
            self.port_input,
            self.user_input,
            self.password_input,
            self.database_input,
            self.folder_input,
            self.drop_checkbox,
            self.snapshot_checkbox,
            self.relax_checkbox,
        ):
            w.setEnabled(not running)

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

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.warning(self, "提示", "還原仍在進行中，請等待完成後再關閉視窗。")
            event.ignore()
            return
        cleanup_temp(self._info)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RestoreWindow()
    window.show()
    sys.exit(app.exec_())

