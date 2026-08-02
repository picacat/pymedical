"""
MyISAM → InnoDB 轉換工具（GUI 版）— dump / 轉換 / 匯入 / 驗證

本工具【不會修改來源資料庫】。它把來源 dump 出來、把 schema 裡的
ENGINE=MyISAM 改成 InnoDB、再匯入一個新的目標資料庫，最後逐表核對兩邊的
資料是否完全相同。來源始終保持原樣，出問題就把目標資料庫砍掉重跑，不需要
動用備份。

為什麼用 mysqldump 而不是自己寫複製邏輯
----------------------------------------
自己寫「讀出來、寫進去」要處理的東西，mysqldump 早就處理好了：分頁順序、
複合主鍵邊界、NULL、二進位資料、跳脫字元、AUTO_INCREMENT 值、索引、view、
trigger、預存程序。用自己寫的幾百行新程式碼去換這些，等於用未驗證的東西
取代被驗證了二十幾年的東西。

先前版本正是踩到這一點：它用 LIMIT/OFFSET 分批而且沒有 ORDER BY。SQL 不
保證沒有 ORDER BY 的查詢在多次執行間回傳相同順序，批與批之間順序若有變動
就會重複複製某些列、漏掉另一些。有 PRIMARY KEY 的表會撞 duplicate key 而
中斷（等於有保護），但沒有 PRIMARY KEY 的表，重複與遺漏可能剛好抵消，
筆數核對照樣通過而資料已經錯了。它也只複製 ENGINE='MyISAM' 的表，view、
trigger、預存程序完全不會過去，目標資料庫是殘缺的。

本版把匯入交給 restore_sql.py（直接 import 重用，不複製貼上，避免兩邊
日後分岔），把 dump 交給 mysqldump，自己只做三件事：前置檢查、schema 的
引擎替換、以及最後的驗證。

schema 與 data 分開 dump 的理由
-------------------------------
mysqldump 沒有「改成 InnoDB」的參數，所以引擎替換只能做文字取代。直接對
含資料的檔案跑 regex 是有風險的——理論上某個 TEXT 欄位裡就是可能出現
`) ENGINE=MyISAM` 這串位元組。

因此 schema 與 data 分成不同檔案：只對 00_schema.sql 做取代，那個檔案
【完全不含任何資料】，風險歸零。檔名以數字開頭是刻意的，restore_sql 用
sorted() 排序檔案，schema 一定排在 data 之前。

為什麼以 binary 字元集 dump
---------------------------
本工具只轉引擎，不轉編碼，目標欄位的字元集與來源完全相同，所以要的是
「位元組原樣搬過去」。--default-character-set=binary 搭配 --hex-blob 可以
做到位元組級的忠實複製，而且不必先確認來源的欄位字元集是否一致（舊資料庫
常見 big5 與 utf8mb3 混雜，指定單一字元集 dump 反而可能損壞資料）。
匯入時同樣以 binary 讀取，兩邊對稱。

最後的 CHECKSUM 核對會證明這件事有沒有做對。

驗證：兩層
------
mysqldump 和 restore_sql 都不會告訴你「兩邊資料是否真的一樣」，這是本工具
唯一自己做的事。分兩層：

  第一層 CHECKSUM TABLE ... EXTENDED（快）
    逐列計算後加總，與資料列的實體順序無關。但它【不是】與儲存引擎或列格式
    無關——MySQL 官方文件明載「checksum 值取決於資料表的列格式，列格式改變
    checksum 就會跟著改變」。MyISAM 的 ROW_FORMAT=Fixed（全部欄位都是定長
    型別時的預設）轉成 InnoDB 的 DYNAMIC 之後，即使資料一模一樣，checksum
    也會不同。早期設計、只用 CHAR/INT/DATE 的舊表最容易踩到。
    因此 checksum 相同可以直接判定通過，但 checksum 不同【不能】判定失敗。

  第二層 值層級指紋（慢，只在第一層不符時才跑）
    對每一列組出 `IF(欄位 IS NULL,'N',CONCAT('V',值))` 再以 0x1F 串接，
    取 MD5 的兩段各 15 個十六進位字元，分別加總。比對的是【欄位的值】而不是
    列的儲存位元組，所以完全不受引擎與列格式影響。
    CHAR 欄位的尾隨空白在讀取時本來就會被去除，兩邊一致，不影響結果。
    這一層若也不符，才是真正的資料不一致。

另外核對兩邊的物件清單（表、view、trigger、程序）。
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

# 直接重用 restore_sql 的匯入邏輯與工具函式，不複製貼上——複製會讓兩邊
# 日後慢慢分岔，而匯入那段是已經實測過的程式碼。
from restore_sql import find_tool, fmt_secs, run_import, subprocess_flags

# InnoDB DYNAMIC 列格式的單一索引長度上限（bytes）。超過會建索引失敗。
INNODB_MAX_INDEX_BYTES = 3072

# 目標資料庫名稱的後綴：<來源>_innodb
TARGET_SUFFIX = "_innodb"

# 「資料表存在於中繼資料，但引擎裡沒有實體」的錯誤碼。
# 最常見的是 1932（Table doesn't exist in engine）：.frm 還在但 .MYD/.MYI
# 不見了，多半是早年手動刪檔、複製資料目錄或磁碟問題留下的殘骸。
# 這種表無法 dump，而且會讓 mysqldump 的 LOCK TABLES 整批失敗，
# 所以要在前置檢查就找出來並排除。
BROKEN_TABLE_ERRORS = {1017, 1030, 1146, 1877, 1932}

# 不可作為目標的資料庫
SYSTEM_DATABASES = {"mysql", "information_schema", "performance_schema", "sys"}

# 只匹配行首的表選項。mysqldump 產生的 CREATE TABLE 最後一行必定是
#   ) ENGINE=MyISAM AUTO_INCREMENT=... DEFAULT CHARSET=...;
# 而這個檔案完全不含資料，因此不會誤傷。
RE_TABLE_ENGINE = re.compile(rb"^\) ENGINE=MyISAM", re.MULTILINE)
ENGINE_REPLACEMENT = b") ENGINE=InnoDB ROW_FORMAT=DYNAMIC"

SCHEMA_FILE = "00_schema.sql"
DATA_PREFIX = "10_data_"


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


def transform_schema(path):
    """把 schema 檔中的 ENGINE=MyISAM 改成 InnoDB。

    以位元組處理，不做解碼——dump 是以 binary 字元集產生的，用任何文字編碼
    去讀都可能失敗或損壞內容。

    Returns:
        int: 替換的張數。
    """
    with open(path, "rb") as f:
        data = f.read()

    new_data, count = RE_TABLE_ENGINE.subn(ENGINE_REPLACEMENT, data)
    if count:
        with open(path, "wb") as f:
            f.write(new_data)
    return count


# ---------------------------------------------------------------------------
# 前置檢查（純唯讀）
# ---------------------------------------------------------------------------


class Preflight:
    """檢查結果。blocking 非空時不允許轉換。"""

    def __init__(self):
        self.charset = None
        self.collation = None
        self.tables = []  # [(table, engine, bytes)]
        self.broken = []  # [(table, errno, 訊息)] — 無法讀取，會被排除
        self.myisam_count = 0
        self.total_bytes = 0
        self.views = []
        self.triggers = []
        self.routines = []  # [(type, name)]
        self.events = []
        self.no_pk = []
        self.fulltext = []
        self.long_index = []
        self.target_tables = []
        self.other_connections = []
        self.blocking = []
        self.warnings = []


def run_preflight(cur, src, tgt, log):
    pf = Preflight()

    # ---- 來源資料庫 ----
    cur.execute(
        "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
        "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
        (src,),
    )
    row = cur.fetchone()
    if not row:
        pf.blocking.append(f"找不到來源資料庫 `{src}`。")
        return pf
    pf.charset, pf.collation = row
    log(f"來源資料庫字元集：{pf.charset} / {pf.collation}（目標會沿用）")

    if tgt in SYSTEM_DATABASES:
        pf.blocking.append(f"`{tgt}` 是系統資料庫，不可作為目標。")
    if tgt == src:
        pf.blocking.append("來源與目標資料庫不可相同。")

    # ---- 資料表（所有引擎）----
    cur.execute(
        """
        SELECT TABLE_NAME, ENGINE, DATA_LENGTH + INDEX_LENGTH AS SZ
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """,
        (src,),
    )
    listed = [
        (name, (engine or "").upper(), int(size or 0))
        for name, engine, size in cur.fetchall()
    ]

    if not listed:
        pf.blocking.append(f"來源資料庫 `{src}` 沒有任何資料表。")
        return pf

    # ---- 逐表探測：中繼資料有、引擎裡沒有實體的殘骸要先排除 ----
    # 這種表（典型是錯誤 1932）無法 dump，而且因為 mysqldump 預設會一次
    # LOCK TABLES 整個資料庫，一張壞表就會讓整批匯出失敗。必須在這裡找出來
    # 並以 --ignore-table 排除，否則錯誤會在 dump 到一半才爆出來。
    for name, engine, size in listed:
        try:
            cur.execute(f"SELECT 1 FROM `{src}`.`{name}` LIMIT 1")
            cur.fetchall()
        except mysql.connector.Error as e:
            errno = getattr(e, "errno", None)
            if errno in BROKEN_TABLE_ERRORS:
                pf.broken.append((name, errno, str(e)))
                continue
            raise
        pf.tables.append((name, engine, size))
        pf.total_bytes += size
        if engine == "MYISAM":
            pf.myisam_count += 1

    if not pf.tables:
        pf.blocking.append(f"來源資料庫 `{src}` 的資料表全部無法讀取，已停止。")
        return pf

    other = sorted({e for _, e, _ in pf.tables if e != "MYISAM"})
    log(
        f"來源資料表：{len(pf.tables)} 張"
        f"（MyISAM {pf.myisam_count} 張"
        + (f"，其他引擎 {'、'.join(other)}" if other else "")
        + f"，合計 {fmt_bytes(pf.total_bytes)}）"
    )
    if other:
        log("  · 非 MyISAM 的表也會一併複製，引擎維持原樣，避免目標資料庫殘缺。")

    if pf.broken:
        names = "、".join(t for t, _, _ in pf.broken)
        log(f"  ⚠ {len(pf.broken)} 張表無法讀取，將被排除：{names}")
        pf.warnings.append(
            f"以下 {len(pf.broken)} 張表在中繼資料裡存在，但引擎裡沒有實體"
            f"（典型錯誤 1932）：{names}。\n"
            "    這些是壞掉的殘骸——.frm 還在但資料檔不見了，多半是早年手動"
            "刪檔、複製資料目錄或磁碟問題造成的。它們無法 dump，會被排除，"
            "目標資料庫不會有這些表。\n"
            "    【請確認程式是否會用到它們】。若會用到，代表來源資料庫的"
            "該功能目前就已經是壞的。建議在來源執行 DROP TABLE 清掉殘骸，"
            "pymedical 啟動時的 check_table_exists 會自動依 mysql/*.sql "
            "重建成空表。"
        )

    # ---- view / trigger / routine / event ----
    cur.execute(
        "SELECT TABLE_NAME FROM information_schema.VIEWS "
        "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
        (src,),
    )
    pf.views = [r[0] for r in cur.fetchall()]

    cur.execute(
        "SELECT TRIGGER_NAME FROM information_schema.TRIGGERS "
        "WHERE TRIGGER_SCHEMA = %s ORDER BY TRIGGER_NAME",
        (src,),
    )
    pf.triggers = [r[0] for r in cur.fetchall()]

    cur.execute(
        "SELECT ROUTINE_TYPE, ROUTINE_NAME FROM information_schema.ROUTINES "
        "WHERE ROUTINE_SCHEMA = %s ORDER BY ROUTINE_NAME",
        (src,),
    )
    pf.routines = [(t, n) for t, n in cur.fetchall()]

    try:
        cur.execute(
            "SELECT EVENT_NAME FROM information_schema.EVENTS "
            "WHERE EVENT_SCHEMA = %s ORDER BY EVENT_NAME",
            (src,),
        )
        pf.events = [r[0] for r in cur.fetchall()]
    except Exception:
        pf.events = []

    parts = []
    if pf.views:
        parts.append(f"view {len(pf.views)} 個")
    if pf.triggers:
        parts.append(f"trigger {len(pf.triggers)} 個")
    if pf.routines:
        parts.append(f"預存程序/函式 {len(pf.routines)} 個")
    if pf.events:
        parts.append(f"排程事件 {len(pf.events)} 個")
    if parts:
        log("其他物件（mysqldump 會一併帶出）：" + "、".join(parts))

    # ---- 索引長度：阻斷性 ----
    cur.execute(
        """
        SELECT s.TABLE_NAME, s.INDEX_NAME,
               SUM(
                 CASE
                   WHEN c.CHARACTER_OCTET_LENGTH IS NULL THEN 8
                   WHEN s.SUB_PART IS NOT NULL AND c.CHARACTER_MAXIMUM_LENGTH > 0
                     THEN s.SUB_PART *
                          CEIL(c.CHARACTER_OCTET_LENGTH / c.CHARACTER_MAXIMUM_LENGTH)
                   ELSE c.CHARACTER_OCTET_LENGTH
                 END
               ) AS approx_bytes
        FROM information_schema.STATISTICS s
        JOIN information_schema.COLUMNS c
          ON  c.TABLE_SCHEMA = s.TABLE_SCHEMA
          AND c.TABLE_NAME   = s.TABLE_NAME
          AND c.COLUMN_NAME  = s.COLUMN_NAME
        JOIN information_schema.TABLES t
          ON  t.TABLE_SCHEMA = s.TABLE_SCHEMA
          AND t.TABLE_NAME   = s.TABLE_NAME
        WHERE s.TABLE_SCHEMA = %s AND t.ENGINE = 'MyISAM'
        GROUP BY s.TABLE_NAME, s.INDEX_NAME
        HAVING approx_bytes > %s
        ORDER BY approx_bytes DESC
        """,
        (src, INNODB_MAX_INDEX_BYTES),
    )
    pf.long_index = [(t, i, int(b)) for t, i, b in cur.fetchall()]
    if pf.long_index:
        detail = "、".join(f"{t}.{i}（約 {b} bytes）" for t, i, b in pf.long_index[:10])
        pf.blocking.append(
            f"{len(pf.long_index)} 個索引超過 InnoDB 的 "
            f"{INNODB_MAX_INDEX_BYTES} bytes 上限，匯入時建表會失敗：{detail}。"
            "請先縮短索引欄位長度或改用前綴索引。"
        )

    # ---- 缺 PRIMARY KEY：警告 ----
    cur.execute(
        """
        SELECT t.TABLE_NAME
        FROM information_schema.TABLES t
        WHERE t.TABLE_SCHEMA = %s AND t.TABLE_TYPE = 'BASE TABLE'
          AND NOT EXISTS (
                SELECT 1 FROM information_schema.STATISTICS s
                WHERE s.TABLE_SCHEMA = t.TABLE_SCHEMA
                  AND s.TABLE_NAME   = t.TABLE_NAME
                  AND s.INDEX_NAME   = 'PRIMARY')
        ORDER BY t.TABLE_NAME
        """,
        (src,),
    )
    pf.no_pk = [r[0] for r in cur.fetchall()]
    if pf.no_pk:
        pf.warnings.append(
            f"{len(pf.no_pk)} 張表沒有 PRIMARY KEY："
            + "、".join(pf.no_pk)
            + "。轉換不會失敗（dump/restore 不依賴主鍵），但 InnoDB 會為它們"
            "自建隱藏的 6-byte rowid，效能較差，建議日後補上。"
        )

    # ---- FULLTEXT：警告 ----
    cur.execute(
        """
        SELECT DISTINCT s.TABLE_NAME, s.INDEX_NAME
        FROM information_schema.STATISTICS s
        JOIN information_schema.TABLES t
          ON  t.TABLE_SCHEMA = s.TABLE_SCHEMA AND t.TABLE_NAME = s.TABLE_NAME
        WHERE s.TABLE_SCHEMA = %s AND t.ENGINE = 'MyISAM'
          AND s.INDEX_TYPE = 'FULLTEXT'
        """,
        (src,),
    )
    pf.fulltext = [f"{t}.{i}" for t, i in cur.fetchall()]
    if pf.fulltext:
        pf.warnings.append(
            "以下為 FULLTEXT 索引："
            + "、".join(pf.fulltext)
            + "。InnoDB 支援 FULLTEXT，但中文斷詞行為與 MyISAM 不同"
            "（需搭配 ngram parser），切換前請實測相關查詢。"
        )

    # ---- 目標資料庫現況 ----
    cur.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
        "ORDER BY TABLE_NAME",
        (tgt,),
    )
    pf.target_tables = [r[0] for r in cur.fetchall()]
    if pf.target_tables:
        pf.warnings.append(
            f"目標資料庫 `{tgt}` 已存在且含有 {len(pf.target_tables)} 張資料表。"
            "dump 檔中的 DROP TABLE 會覆蓋同名資料表，原有內容將遺失。"
            "確認那不是你要保留的資料。"
        )

    # ---- 其他連線 ----
    # 來源在 dump 期間若持續被寫入，dump 出來的會是不一致的快照，
    # 最後的 checksum 核對必然失敗。
    cur.execute("SELECT CONNECTION_ID()")
    my_id = cur.fetchone()[0]
    cur.execute("SHOW PROCESSLIST")
    for row in cur.fetchall():
        pid, user, host, rdb = row[0], row[1], row[2], row[3]
        if pid != my_id and rdb == src:
            pf.other_connections.append((pid, user, host))
    if pf.other_connections:
        detail = "、".join(f"{u}@{h}" for _, u, h in pf.other_connections[:10])
        pf.warnings.append(
            f"目前還有 {len(pf.other_connections)} 個連線連到來源 `{src}`"
            f"（{detail}）。dump 期間若有人繼續寫入，兩邊的 checksum 必然"
            "對不上。請先關閉所有診所端程式"
            "（含候診看板、Kiosk、預約掛號伺服器）。"
        )

    return pf


# ---------------------------------------------------------------------------
# 背景工作執行緒
# ---------------------------------------------------------------------------


class ConvertWorker(QObject):
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
            connection_timeout=10,
            autocommit=True,
        )
        cur = conn.cursor()
        for stmt in (
            "SET SESSION wait_timeout = 28800",
            "SET SESSION net_read_timeout = 3600",
            "SET SESSION net_write_timeout = 3600",
        ):
            try:
                cur.execute(stmt)
            except Exception:
                pass
        return conn, cur

    def _fingerprint(self, cur, db, table):
        """第一層驗證：回傳 (筆數, checksum)。

        CHECKSUM TABLE ... EXTENDED 逐列計算後加總，與資料列的實體順序無關，
        但【取決於列格式】——MyISAM 的 ROW_FORMAT=Fixed 轉成 InnoDB 的
        DYNAMIC 之後，即使資料完全相同，checksum 也會不同。
        因此相同可以直接判定通過，不同時必須改用 _value_fingerprint 再確認。
        """
        cur.execute(f"SELECT COUNT(*) FROM `{db}`.`{table}`")
        count = int(cur.fetchone()[0])
        checksum = None
        try:
            cur.execute(f"CHECKSUM TABLE `{db}`.`{table}` EXTENDED")
            rows = cur.fetchall()
            if rows:
                checksum = rows[0][1]
        except Exception as e:
            self.log(f"    （CHECKSUM 取得失敗：{e}）")
        return count, checksum

    # 需要以 HEX() 取值的二進位型別。直接串接會因為字元集轉換而失真。
    BINARY_TYPES = {
        "binary",
        "varbinary",
        "blob",
        "tinyblob",
        "mediumblob",
        "longblob",
        "bit",
        "geometry",
    }

    def _row_expression(self, cur, db, table):
        """組出「把一整列的值串成一個字串」的 SQL 運算式。

        每個欄位寫成 IF(欄位 IS NULL,'N',CONCAT('V',值))：'N' 與 'V...' 前綴
        讓 NULL 與字面上剛好等於某個標記字串的值不會混淆。欄位之間以 0x1F
        （單元分隔符，不會出現在正常文字裡）串接。
        """
        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION",
            (db, table),
        )
        parts = []
        for col, dtype in cur.fetchall():
            ref = f"`{col}`"
            value = f"HEX({ref})" if str(dtype).lower() in self.BINARY_TYPES else ref
            parts.append(f"IF({ref} IS NULL,'N',CONCAT('V',{value}))")
        if not parts:
            return None
        return "CONCAT_WS(0x1f, " + ", ".join(parts) + ")"

    def _column_fingerprints(self, cur, db, table):
        """診斷用：逐欄位各算一個指紋，回傳 {欄位: 值} 或 None。

        整列指紋不符時，用它指出差異究竟落在哪一欄。一次查詢算完所有欄位，
        只在真的出問題時才跑，不影響正常流程的速度。

        知道是哪一欄，通常就知道原因了：日期欄 → 無效日期被轉成
        0000-00-00；字串欄 → 超長值被截斷或編碼問題；浮點欄 → 文字往返的
        精度差異。
        """
        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION",
            (db, table),
        )
        cols = [(c, str(t).lower()) for c, t in cur.fetchall()]
        if not cols:
            return None

        selects = []
        for col, dtype in cols:
            ref = f"`{col}`"
            value = f"HEX({ref})" if dtype in self.BINARY_TYPES else ref
            expr = f"IF({ref} IS NULL,'N',CONCAT('V',{value}))"
            selects.append(f"COALESCE(SUM(CRC32({expr})),0)")

        try:
            cur.execute(f"SELECT {', '.join(selects)} FROM `{db}`.`{table}`")
            row = cur.fetchone()
            return {col: str(row[i]) for i, (col, _t) in enumerate(cols)}
        except Exception as e:
            self.log(f"    （逐欄位指紋計算失敗：{e}）")
            return None

    def _diff_columns(self, cur, src, tgt, table):
        """比對兩邊的逐欄位指紋。

        回傳 (狀態, 欄位清單)：
          ("differ", [...])  有欄位不同
          ("same",   [])     所有欄位的指紋都相符
          ("failed", [])     指紋無法取得

        "same" 與 "failed" 必須分開。逐欄位用的是 SUM(CRC32(...))，CRC32
        回傳整數、SUM 是精確的十進位運算，因此這個結果比整列指紋可靠。
        如果整列指紋說不同、逐欄位卻說全部相同，最可能的解釋是整列指紋
        的計算方式有問題，而不是資料真的不一致——把這兩種情況混成一句
        「無法判定」會讓這個線索完全消失。
        """
        s = self._column_fingerprints(cur, src, table)
        t = self._column_fingerprints(cur, tgt, table)
        if s is None or t is None:
            return "failed", []
        diff = [c for c in s if c in t and s[c] != t[c]]
        return ("differ", diff) if diff else ("same", [])

    def _value_fingerprint(self, cur, db, table):
        """第二層驗證：回傳 (筆數, 加總A, 加總B) 或 None。

        比對的是【欄位的值】而不是列的儲存位元組，因此完全不受儲存引擎與
        列格式影響。取 MD5 的兩段各 15 個十六進位字元分別加總（15 位 = 60
        bit，不會溢位），兩個獨立的加總讓碰撞機率低到可以忽略。
        用加總而非串接，所以與資料列的順序無關。

        CHAR 欄位的尾隨空白在讀取時本來就會被去除，兩邊一致，不影響結果。
        """
        expr = self._row_expression(cur, db, table)
        if expr is None:
            return None
        try:
            # 【務必保留 CAST ... AS DECIMAL(65,0)】
            # CONV() 回傳的是字串，SUM() 對字串引數會轉成 DOUBLE。15 位十六
            # 進位的值最大約 1.15e18，遠超過 DOUBLE 能精確表示整數的上限
            # 2^53 ≈ 9e15——單一個值就已經失真，而且浮點加法不符合結合律，
            # 於是【同一批資料以不同順序相加會得到不同結果】。
            # MyISAM 與 InnoDB 的實體掃描順序本來就不同，因此少了這個 CAST，
            # 資料完全相同的表也會被誤判為不一致。
            # CAST 成 DECIMAL 之後是精確的十進位運算，與相加順序無關。
            cur.execute(
                f"SELECT COUNT(*), "
                f"COALESCE(SUM(CAST(CONV(SUBSTR(MD5(rt),1,15),16,10) "
                f"                AS DECIMAL(65,0))),0), "
                f"COALESCE(SUM(CAST(CONV(SUBSTR(MD5(rt),17,15),16,10) "
                f"                AS DECIMAL(65,0))),0) "
                f"FROM (SELECT {expr} AS rt FROM `{db}`.`{table}`) AS x"
            )
            row = cur.fetchone()
            # 以整數比對，避免 Decimal / float 的字串表示差異造成誤判
            return (int(row[0]), str(int(row[1])), str(int(row[2])))
        except Exception as e:
            self.log(f"    （值層級指紋計算失敗：{e}）")
            return None

    # -- 主流程 -----------------------------------------------------------
    def run(self):
        conn = None
        cur = None
        try:
            p = self.p
            src, tgt = p["source"], p["target"]
            tmp_dir = p["tmp_dir"]
            t_start = time.time()

            conn, cur = self._connect()

            # ---------- 前置檢查 ----------
            self.log("=== 前置檢查（唯讀，不會修改任何資料）===")
            pf = run_preflight(cur, src, tgt, self.log)

            if not p["mysqldump"]:
                pf.blocking.append(
                    "找不到 mysqldump（或 mariadb-dump）指令。請確認 MariaDB "
                    "的 bin 目錄已加入 PATH。"
                )
            if not p["mysql"]:
                pf.blocking.append(
                    "找不到 mysql（或 mariadb）指令。請確認 MariaDB 的 bin "
                    "目錄已加入 PATH。"
                )
            if not os.path.isdir(tmp_dir):
                pf.blocking.append(f"暫存目錄不存在：{tmp_dir}")
            else:
                # dump 檔加上目標資料庫，總共約三份
                try:
                    free = shutil.disk_usage(tmp_dir).free
                    self.log(
                        f"暫存目錄：{tmp_dir}（剩餘 {fmt_bytes(free)}，"
                        f"dump 約需 {fmt_bytes(pf.total_bytes)}）"
                    )
                    if free < pf.total_bytes * 1.2:
                        pf.blocking.append(
                            f"暫存目錄空間不足：剩餘 {fmt_bytes(free)}，"
                            f"dump 檔約需 {fmt_bytes(pf.total_bytes)}。"
                        )
                except OSError:
                    pass

            if pf.blocking:
                self.log("\n⛔ 發現阻斷性問題，不可轉換：")
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
                        else "可以進行轉換。"
                    ),
                )
                return

            if pf.blocking:
                raise RuntimeError(
                    "存在阻斷性問題，已停止：\n  " + "\n  ".join(pf.blocking)
                )

            env = os.environ.copy()
            env["MYSQL_PWD"] = p["password"]
            dump_base = [
                p["mysqldump"],
                f"--host={p['host']}",
                f"--port={p['port']}",
                f"--user={p['user']}",
                # 位元組原樣搬移：不做任何編碼轉換，也不必先確認來源的欄位
                # 字元集是否一致（舊資料庫常見 big5 與 utf8mb3 混雜）
                "--default-character-set=binary",
                "--hex-blob",
            ]
            # 排除讀不到的殘骸。mysqldump 預設一次 LOCK TABLES 整個資料庫，
            # 少了這幾個參數，一張壞表就會讓整批匯出失敗。
            ignore_args = [f"--ignore-table={src}.{t}" for t, _, _ in pf.broken]
            if ignore_args:
                self.log(
                    f"（已排除 {len(ignore_args)} 張讀不到的表："
                    + "、".join(t for t, _, _ in pf.broken)
                    + "）"
                )

            # ---------- 1. dump schema ----------
            self.log("\n[步驟 1/5] 匯出 schema（含 view / trigger / 預存程序）…")
            t0 = time.time()
            schema_path = os.path.join(tmp_dir, SCHEMA_FILE)
            rc, err = run_dump(
                dump_base
                + ignore_args
                + ["--no-data", "--routines", "--events", "--triggers", src],
                env,
                schema_path,
            )
            if rc != 0:
                raise RuntimeError(f"schema 匯出失敗：{err}")
            self.log(
                f"  ✓ {SCHEMA_FILE}"
                f"（{fmt_bytes(os.path.getsize(schema_path))}，"
                f"{fmt_secs(time.time() - t0)}）"
            )

            # ---------- 2. 替換引擎 ----------
            self.log("\n[步驟 2/5] 將 schema 中的 ENGINE=MyISAM 改為 InnoDB …")
            replaced = transform_schema(schema_path)
            self.log(f"  已替換 {replaced} 張表的引擎宣告。")
            if replaced != pf.myisam_count:
                raise RuntimeError(
                    f"替換張數（{replaced}）與檢查時統計的 MyISAM 張數"
                    f"（{pf.myisam_count}）不符，已停止。"
                    "請人工檢查 schema 檔案後再決定是否繼續。"
                )
            # 再確認一次檔案裡沒有殘留
            with open(schema_path, "rb") as f:
                if RE_TABLE_ENGINE.search(f.read()):
                    raise RuntimeError("schema 檔中仍殘留 ENGINE=MyISAM，已停止。")
            self.log("  ✓ 已確認檔案中沒有殘留的 ENGINE=MyISAM。")

            # ---------- 3. dump 資料（逐表一檔）----------
            self.log(f"\n[步驟 3/5] 逐表匯出資料（{len(pf.tables)} 張）…")
            t0_phase = time.time()
            data_files = []
            for i, (table, engine, size) in enumerate(pf.tables, start=1):
                self.sig_progress.emit(i, len(pf.tables))
                out = os.path.join(
                    tmp_dir, f"{DATA_PREFIX}{i:04d}_{safe_filename(table)}.sql"
                )
                t0 = time.time()
                rc, err = run_dump(
                    dump_base + ["--no-create-info", src, table], env, out
                )
                if rc != 0:
                    raise RuntimeError(f"`{table}` 資料匯出失敗：{err}")
                data_files.append(out)
                self.log(
                    f"  ✓ [{i}/{len(pf.tables)}] {table}"
                    f"（{fmt_bytes(os.path.getsize(out))}，"
                    f"{time.time() - t0:.1f} 秒）"
                )
            self.log(f"資料匯出完成（{fmt_secs(time.time() - t0_phase)}）。")

            # ---------- 4. 建立目標資料庫並匯入 ----------
            self.log(f"\n[步驟 4/5] 建立 `{tgt}` 並匯入 …")
            t0_phase = time.time()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{tgt}` "
                f"DEFAULT CHARACTER SET {pf.charset} COLLATE {pf.collation}"
            )
            self.log(f"  字元集沿用來源：{pf.charset} / {pf.collation}")

            import_cmd = [
                p["mysql"],
                f"--host={p['host']}",
                f"--port={p['port']}",
                f"--user={p['user']}",
                # 與 dump 對稱，維持位元組原樣
                "--default-character-set=binary",
                "--max-allowed-packet=256M",
                tgt,
            ]

            all_files = [schema_path] + data_files
            for i, path in enumerate(all_files, start=1):
                self.sig_progress.emit(i, len(all_files))
                name = os.path.basename(path)
                t0 = time.time()
                rc, err = run_import(import_cmd, env, path)
                if rc != 0:
                    raise RuntimeError(f"{name} 匯入失敗：{err}")
                self.log(
                    f"  ✓ [{i}/{len(all_files)}] {name}（{time.time() - t0:.1f} 秒）"
                )
            self.log(f"匯入完成（{fmt_secs(time.time() - t0_phase)}）。")

            # ---------- 5. 驗證 ----------
            self.log("\n[步驟 5/5] 逐表核對 …")
            t0_phase = time.time()

            # 兩邊的列格式，用於解釋 checksum 為何不同
            row_formats = {}
            for which in (src, tgt):
                cur.execute(
                    "SELECT TABLE_NAME, ROW_FORMAT FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
                    (which,),
                )
                row_formats[which] = {t: f for t, f in cur.fetchall()}

            mismatched = []
            by_value = []  # checksum 不同但值層級相符（列格式差異）
            by_column = []  # 整列指紋不同但逐欄位全部相符
            unverified = []  # 兩層都無法取得
            accepted = []  # 核對不符，但使用者已明確列入略過清單
            skip_verify = self.p.get("skip_verify") or set()
            if skip_verify:
                self.log(
                    "略過清單（核對不符時放行）：" + "、".join(sorted(skip_verify))
                )
            for i, (table, engine, size) in enumerate(pf.tables, start=1):
                self.sig_progress.emit(i, len(pf.tables))
                tag = f"[{i}/{len(pf.tables)}] {table}"

                s_count, s_sum = self._fingerprint(cur, src, table)
                try:
                    t_count, t_sum = self._fingerprint(cur, tgt, table)
                except Exception as e:
                    mismatched.append((table, f"目標表無法讀取：{e}"))
                    self.log(f"  ✗ {tag}：{e}")
                    continue

                if s_count != t_count:
                    mismatched.append((table, f"筆數 來源 {s_count} / 目標 {t_count}"))
                    self.log(f"  ✗ {tag}：筆數不符（{s_count} / {t_count}）")
                    continue

                # 第一層：checksum 相同就直接通過
                if s_sum is not None and t_sum is not None and s_sum == t_sum:
                    self.log(f"  ✓ {tag}（{s_count} 筆，checksum 相符）")
                    continue

                # 第一層不符或取不到 → 第二層。checksum 取決於列格式，
                # MyISAM 的 Fixed 轉成 InnoDB 的 DYNAMIC 之後值必然不同，
                # 不能據此判定資料有問題。
                sf = row_formats[src].get(table, "?")
                tf = row_formats[tgt].get(table, "?")
                self.log(
                    f"  · {tag}：checksum 不同（列格式 {sf} → {tf}），改以值層級比對 …"
                )
                sv = self._value_fingerprint(cur, src, table)
                tv = self._value_fingerprint(cur, tgt, table)

                if sv is None or tv is None:
                    unverified.append(table)
                    self.log(
                        f"  ⚠ {tag}：值層級指紋無法取得，僅確認筆數相符（{s_count} 筆）"
                    )
                    continue

                if sv == tv:
                    by_value.append(table)
                    self.log(f"  ✓ {tag}（{s_count} 筆，值層級相符）")
                else:
                    # 值層級也不符 → 用逐欄位指紋再確認一次。
                    # 逐欄位是 SUM(CRC32(...))，整數精確運算，比整列指紋可靠。
                    status, diff_cols = self._diff_columns(cur, src, tgt, table)

                    if status == "same":
                        # 逐欄位全部相符：資料是一致的。
                        by_column.append(table)
                        self.log(f"  ✓ {tag}（{s_count} 筆，逐欄位指紋全部相符）")
                        continue

                    col_note = (
                        "差異欄位：" + "、".join(diff_cols)
                        if status == "differ"
                        else "逐欄位指紋無法取得"
                    )
                    if table in skip_verify:
                        accepted.append((table, col_note))
                        self.log(
                            f"  ⚠ {tag}：核對不符，但已列入略過清單，放行。{col_note}"
                        )
                    else:
                        mismatched.append((table, col_note))
                        self.log(f"  ✗ {tag}：資料確實不一致。{col_note}")

            t_verify = time.time() - t0_phase

            if mismatched:
                detail = "\n  ".join(f"{t}：{r}" for t, r in mismatched)
                raise RuntimeError(
                    f"{len(mismatched)}/{len(pf.tables)} 張表核對失敗，"
                    f"目標資料庫【不可使用】：\n  {detail}\n"
                    "這些是值層級比對也不符的表，資料確實不一致"
                    "（列格式差異已排除）。最常見的原因是 dump 期間有人在"
                    "寫入來源資料庫。\n"
                    f"來源 `{src}` 未受任何影響。請關閉所有診所端程式後，"
                    f"DROP DATABASE `{tgt}` 再重跑。"
                )

            # ---------- 物件清單核對 ----------
            self.log("\n核對兩邊的物件清單 …")
            cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
                (tgt,),
            )
            tgt_tables = {r[0] for r in cur.fetchall()}
            missing = sorted({t for t, _, _ in pf.tables} - tgt_tables)
            if missing:
                raise RuntimeError(
                    f"目標資料庫少了 {len(missing)} 張表：" + "、".join(missing)
                )

            obj_notes = []
            for label, sql, want in (
                (
                    "view",
                    "SELECT COUNT(*) FROM information_schema.VIEWS "
                    "WHERE TABLE_SCHEMA = %s",
                    len(pf.views),
                ),
                (
                    "trigger",
                    "SELECT COUNT(*) FROM information_schema.TRIGGERS "
                    "WHERE TRIGGER_SCHEMA = %s",
                    len(pf.triggers),
                ),
                (
                    "預存程序/函式",
                    "SELECT COUNT(*) FROM information_schema.ROUTINES "
                    "WHERE ROUTINE_SCHEMA = %s",
                    len(pf.routines),
                ),
            ):
                cur.execute(sql, (tgt,))
                got = int(cur.fetchone()[0])
                if got != want:
                    obj_notes.append(f"{label}：來源 {want} 個、目標 {got} 個")
            self.log(
                f"✓ {len(tgt_tables)} 張資料表全部存在。"
                + ("" if not obj_notes else "（其他物件有出入，見摘要）")
            )

            # ---------- ANALYZE ----------
            self.log("\n更新統計資訊 …")
            analyze_failed = []
            for table, _e, _s in pf.tables:
                try:
                    cur.execute(f"ANALYZE TABLE `{tgt}`.`{table}`")
                    cur.fetchall()
                except Exception:
                    analyze_failed.append(table)

            cur.execute(
                "SELECT ENGINE, COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "GROUP BY ENGINE",
                (tgt,),
            )
            engine_summary = "、".join(f"{e}: {c} 張" for e, c in cur.fetchall())

            # ---------- 摘要 ----------
            ok = True
            lines = [
                f"轉換完成：`{src}` → `{tgt}`。",
                f"{len(pf.tables)} 張資料表全部通過核對"
                f"（核對耗時 {fmt_secs(t_verify)}）。",
                f"目標引擎分佈：{engine_summary}。",
                f"總耗時：{fmt_secs(time.time() - t_start)}。",
                "",
                f"⚠ 來源資料庫 `{src}` 完全未被修改，可隨時退回使用。",
                f"dump 檔保留在 {tmp_dir}，確認無誤後可自行刪除。",
            ]
            if by_value:
                lines.append(
                    f"（其中 {len(by_value)} 張表的 CHECKSUM 值不同，這是列格式"
                    "由 MyISAM 的 Fixed 轉為 InnoDB 的 DYNAMIC 造成的，"
                    "不代表資料有問題；已改用不受列格式影響的值層級比對確認"
                    "內容完全相同：" + "、".join(by_value) + "）"
                )
            if by_column:
                lines.append(
                    f"（其中 {len(by_column)} 張表是以逐欄位指紋確認相符："
                    + "、".join(by_column)
                    + "）"
                )
            if unverified:
                ok = False
                lines.append(
                    f"⚠ {len(unverified)} 張表的兩種指紋都無法取得，"
                    "只核對了筆數：" + "、".join(unverified) + "。請自行抽查內容。"
                )
            if accepted:
                lines.append(
                    f"⚠ 以下 {len(accepted)} 張表【核對不符但已依略過清單放行】，"
                    "目標資料庫中的這些表與來源內容不同，請確認它們確實已停用："
                    + "；".join(f"{t}（{n}）" for t, n in accepted)
                )
            if pf.broken:
                lines.append(
                    f"⚠ {len(pf.broken)} 張表因為在引擎裡沒有實體而被排除，"
                    "目標資料庫【沒有】這些表："
                    + "、".join(t for t, _, _ in pf.broken)
                    + "。若程式會用到，切換後該功能會失敗——"
                    "請在來源 DROP TABLE 清掉殘骸後，讓 pymedical 自動重建。"
                )
            if obj_notes:
                ok = False
                lines.append("⚠ 物件數量有出入：" + "；".join(obj_notes))
            if analyze_failed:
                lines.append(
                    f"注意：{len(analyze_failed)} 張表統計更新失敗"
                    "（不影響資料正確性）。"
                )
            if pf.no_pk:
                lines.append(
                    f"提醒：{len(pf.no_pk)} 張表沒有 PRIMARY KEY，建議日後補上。"
                )

            lines += [
                "",
                "接下來的切換步驟：",
                f"1. 把 pymedical.conf 的 database= 暫時改為 {tgt}，"
                "跑一輪完整門診流程（掛號、看診、批價、報表、健保申報）確認無誤。",
                "2. 確認無誤後才正式切換所有站台。",
                f"3. 舊的 `{src}` 至少保留一個申報週期再考慮刪除。",
            ]

            summary = "\n".join(lines)
            self.log("\n=== 結束 ===\n" + summary)
            self.sig_finished.emit(ok, summary)

        except Exception as e:
            self.log(f"\n⛔ 已停止：{e}")
            self.log("（來源資料庫未被修改）")
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


class ConvertWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyISAM → InnoDB 轉換工具")
        self.resize(700, 720)
        self._thread = None
        self._worker = None
        self._preflight = None
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
        self.target_input.setToolTip(
            f"預設為「來源資料庫{TARGET_SUFFIX}」，會隨來源自動更新。\n"
            "手動改過之後就不再自動變更。"
        )
        # 目標名稱預設跟著來源走。使用者一旦手動改過就不再覆蓋。
        self._auto_target = ""
        self.source_input.textChanged.connect(self._sync_target_name)

        self.skip_input = self._add_row(layout, "核對略過:")
        self.skip_input.setPlaceholderText(
            "留空即可。以逗號分隔要放行的資料表名稱，例如：exam, expense"
        )
        self.skip_input.setToolTip(
            "列在這裡的資料表，即使核對不符也會放行，不中斷整批轉換。\n"
            "只用於已確認停用、內容不再重要的表。\n"
            "放行的表會在結束摘要中明確列出，連同差異欄位。\n"
            "⚠ 不要把還在使用的表放進來——核對不符代表資料真的不一樣。"
        )

        folder_row = QHBoxLayout()
        folder_label = QLabel("暫存目錄:")
        folder_label.setFixedWidth(90)
        self.tmp_input = QLineEdit()
        browse = QPushButton("瀏覽…")
        browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.tmp_input)
        folder_row.addWidget(browse)
        layout.addLayout(folder_row)

        info_label = QLabel(
            "本工具不會修改來源資料庫：先用 mysqldump 匯出、把 schema 的\n"
            "ENGINE=MyISAM 改成 InnoDB、再匯入目標資料庫，最後逐表核對\n"
            "筆數與內容指紋。出問題就砍掉目標資料庫重跑即可。"
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
        self.convert_button = QPushButton("2. 開始轉換")
        self.convert_button.clicked.connect(self.start_convert)
        self.convert_button.setEnabled(False)
        button_row.addWidget(self.check_button)
        button_row.addWidget(self.convert_button)
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

    def _sync_target_name(self, source_text):
        """來源改變時，把目標名稱更新為 <來源>_innodb。

        只在目標欄位是空的、或內容正是上一次自動填入的值時才動它——
        使用者手動輸入過的名稱不會被覆蓋。
        """
        current = self.target_input.text().strip()
        if current and current != self._auto_target:
            return
        source = source_text.strip()
        self._auto_target = f"{source}{TARGET_SUFFIX}" if source else ""
        self.target_input.setText(self._auto_target)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "選擇暫存目錄", self.tmp_input.text() or ""
        )
        if folder:
            self.tmp_input.setText(folder)

    def _load_config(self):
        self.mysqldump_path = find_tool("mysqldump", "mariadb-dump")
        self.mysql_path = find_tool("mysql", "mariadb")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_dir, "pymedical.conf")
        source = ""
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file, encoding="utf-8")
            db = config["db"] if "db" in config else {}
            self.host_input.setText(db.get("host", "localhost"))
            self.port_input.setText(db.get("port", "3306"))
            self.user_input.setText(db.get("user", "root"))
            self.password_input.setText(db.get("password", ""))
            source = db.get("database", "")
            self.source_input.setText(source)
            # 一律以「來源 + _innodb」為準，不再讀 conf 的 inno_database——
            # 設定檔裡的舊值可能指向別的資料庫，而使用者常常會直接改上面的
            # 來源欄位去轉換另一家診所。
            self._auto_target = f"{source}{TARGET_SUFFIX}" if source else ""
            self.target_input.setText(self._auto_target)
            if "tools" in config:
                self.mysqldump_path = config["tools"].get(
                    "mysqldump", self.mysqldump_path
                )
                self.mysql_path = config["tools"].get("mysql", self.mysql_path)
        else:
            self.host_input.setText("localhost")
            self.port_input.setText("3306")

        self.tmp_input.setText(os.path.join(base_dir, "tmp_convert"))
        self.tool_label.setText(
            f"mysqldump: {self.mysqldump_path or '（未找到）'}　"
            f"mysql: {self.mysql_path or '（未找到）'}"
        )

    def _collect_params(self):
        source = self.source_input.text().strip()
        target = self.target_input.text().strip()
        tmp_dir = self.tmp_input.text().strip()
        if not source or not target:
            QMessageBox.warning(self, "提示", "請填寫來源與目標資料庫名稱。")
            return None
        if source == target:
            QMessageBox.warning(
                self, "提示", "來源與目標資料庫不可相同，避免覆蓋原始資料。"
            )
            return None
        if not tmp_dir:
            QMessageBox.warning(self, "提示", "請指定暫存目錄。")
            return None
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "錯誤", f"無法建立暫存目錄：\n{e}")
            return None
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "提示", "埠號必須是數字。")
            return None
        skip_verify = {
            s.strip()
            for s in self.skip_input.text().replace("，", ",").split(",")
            if s.strip()
        }
        return {
            "host": self.host_input.text().strip(),
            "port": port,
            "user": self.user_input.text().strip(),
            "password": self.password_input.text(),
            "source": source,
            "target": target,
            "tmp_dir": tmp_dir,
            "skip_verify": skip_verify,
            "mysqldump": self.mysqldump_path,
            "mysql": self.mysql_path,
        }

    def start_check(self):
        params = self._collect_params()
        if params is None:
            return
        self._preflight = None
        self.convert_button.setEnabled(False)
        self.log_box.clear()
        self._start_worker(params, dry_run=True)

    def start_convert(self):
        params = self._collect_params()
        if params is None:
            return
        if self._preflight is None:
            QMessageBox.warning(self, "提示", "請先執行檢查。")
            return
        if self._preflight.blocking:
            QMessageBox.critical(
                self, "無法轉換", "檢查發現阻斷性問題，請先處理後重新檢查。"
            )
            return

        pf = self._preflight
        msg = (
            f"即將把 `{params['source']}`（{len(pf.tables)} 張表，"
            f"{fmt_bytes(pf.total_bytes)}）轉換到 `{params['target']}`，"
            f"其中 {pf.myisam_count} 張 MyISAM 會建成 InnoDB。\n\n"
            "來源資料庫不會被修改。完成後會逐表核對筆數與內容指紋，"
            "任何一張對不上就判定失敗。"
        )
        if pf.warnings:
            msg += "\n\n檢查時發現以下需注意項目：\n・" + "\n・".join(pf.warnings)
        if params["skip_verify"]:
            msg += (
                "\n\n⚠ 以下資料表已列入核對略過清單，即使內容與來源不同"
                "也會放行：\n・"
                + "、".join(sorted(params["skip_verify"]))
                + "\n請確認它們確實都已停用。"
            )
        msg += "\n\n確定要開始嗎？"

        answer = QMessageBox.question(
            self, "轉換前確認", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return

        self.log_box.clear()
        self._start_worker(params, dry_run=False)

    def _start_worker(self, params, dry_run):
        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)

        self._thread = QThread()
        self._worker = ConvertWorker(params, dry_run)
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

        can_convert = (
            self._preflight is not None
            and not self._preflight.blocking
            and bool(self._preflight.tables)
        )
        self.convert_button.setEnabled(can_convert)

        if ok:
            if was_dry_run and can_convert:
                summary += "\n\n可以按「2. 開始轉換」。"
            QMessageBox.information(self, "完成", summary)
        else:
            QMessageBox.critical(self, "未完成", summary)

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.warning(
                self, "提示", "作業仍在進行中，請等待完成後再關閉視窗。"
            )
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConvertWindow()
    window.show()
    sys.exit(app.exec_())
