"""
逐表 SQL 備份還原工具（GUI 版）— 效能改良版

與 convert_sql.py 相同的介面風格與安全原則：
  1. 每個 .sql 檔的匯入結果逐一檢查，任何失敗立即記錄並在
     結束時明確列出——還原工具絕不假裝成功。
  2. 密碼透過 MYSQL_PWD 環境變數傳遞，不出現在命令列與程序列表。
  3. 目標資料庫已存在且含資料表時，開始前顯示現況並要求明確確認
     （備份檔中的 DROP TABLE 會覆蓋同名資料表）。
  4. 「備份檔編碼」須與備份檔當初匯出的編碼一致（告訴伺服器檔案內
     位元組的編碼），與最終想要的字元集是兩回事。
  5. 可選「還原後轉換為 utf8mb4」：照備份檔原編碼忠實匯入後，
     先逐欄做無損轉換檢查（同義異碼視為正規化放行、真正有損則停止），
     通過後由伺服器端 ALTER 轉換。

本版相對前版的修正：
  A. 資料引擎預設「依備份檔」。備份檔的 CREATE TABLE 已帶
     ENGINE=xxx，不應由使用者覆寫；只有明確選擇 MyISAM/InnoDB
     時才做轉換。（前版預設 MyISAM，會把 InnoDB 備份倒退轉回去，
     方向錯誤而且多一次全表重建。）
  B. 無損檢查改為「每張表一次掃描」：把該表所有文字欄位的判斷
     併成單一 SELECT 的多個 SUM()，掃描次數從 2N 降到 1（欄位多
     時分批，每批 20 欄）。空表直接跳過。
  C. 字元集轉換只針對「真的含非 utf8mb4 文字欄位」的表做重建；
     僅預設字元集不符者用 DEFAULT CHARACTER SET（純中繼資料，
     不重建）。字元集與引擎若同時要改，合併成一句 ALTER，
     資料只重建一次。
  D. 匯入改用管線包一層交易：SET unique_checks/foreign_key_checks=0、
     autocommit=0，檔案結束後補 COMMIT。避免 InnoDB 每句 INSERT
     一次 fsync。
  E. 可選在還原期間暫時放寬 InnoDB 持久性設定（需 SUPER 權限，
     結束後自動還原原值）。
  F. 結束摘要列出各階段耗時，方便定位瓶頸。

本版（InnoDB 全面轉換後）再新增：
  G. 開始前先掃描備份檔的 ENGINE= 宣告。轉換前產生的舊備份仍寫著
     ENGINE=MyISAM，「依備份檔」會靜默把資料表退回 MyISAM——現在
     會在確認對話框明確警告並建議改選 InnoDB，結束摘要也會再檢查
     一次實際結果。
  H. 連線明確設定 autocommit=True。mysql.connector 預設為 False，
     步驟 3 的檢查查詢會開啟一個交易並持續到步驟 4 第一句 DDL 為止，
     期間 InnoDB 持有 read view、擋住 purge，undo log 持續累積。
  I. 新增步驟 5：ALTER 完成後執行 ANALYZE TABLE 更新統計資訊。
     大量匯入後 InnoDB 的取樣統計可能失準，會導致優化器選錯索引
     （症狀為「還原完的資料庫查詢特別慢」）。
  J. 步驟 5 一併列出沒有 PRIMARY KEY 的資料表。InnoDB 缺 PK 會自建
     隱藏 rowid，效能較差；僅提醒，不自動修改。
  K. TARGET_COLLATION 由 utf8mb4_unicode_ci 改為 utf8mb4_general_ci，
     與 classes/mysql_database.py 及 convert_sql.py 統一。先前不一致會
     讓「經本工具還原的資料庫」與「程式後續新建的資料表」collation 不同，
     JOIN/UNION 時可能拋 Illegal mix of collations（1267）。詳見
     TARGET_COLLATION 的註解。

本版（配合 backup.py 全面改用 mysqldump）再新增：
  L. 認得 backup.py 產生的非資料表檔案，不再把它們當成資料表匯入：
       00_schema.sql   只讀取來源資料庫的字元集，【不執行】。
                       它含有 USE `來源庫`，直接匯入會把 session 切走，
                       在來源庫名下建出一個多餘的資料庫，而目標庫的
                       字元集完全沒被設定。
       zz_views.sql    檢視表依賴基底表，必須排在所有資料表之後匯入。
       zz_routines.sql 同上。
       zz_grants.sql   全是註解，完全不匯入。
  M. 支援 binary 編碼的備份檔。backup.py 已改用
     --default-character-set=binary --hex-blob 匯出（避免 Big5 舊資料
     在匯出時被轉碼），檔頭因此寫著 SET NAMES binary。匯入時沿用
     binary 是正確的（原樣灌回、不轉碼），但 binary【不可】拿去當
     資料庫的預設字元集——那會讓之後在該庫新建的資料表全部變成
     binary，中文無法正常比較排序。改為從 00_schema.sql 讀取來源
     資料庫真正的字元集。
  N. 步驟 3 的文字欄位查詢加上 TABLE_TYPE = 'BASE TABLE' 過濾。
     zz_views.sql 匯入的檢視表欄位原本會被撈進來做全表掃描檢查，
     白花時間，而步驟 4 只處理 BASE TABLE，永遠不會真的去 ALTER 它。
  O. 開始前比對 00_manifest.txt：檔案缺漏、大小不符、或備份當下就已
     標記 FAIL，都在確認對話框中明確列出。

本版（有損字元的門檻式處理）再新增：
  P. 「有損資料處理」三選一，預設「自動」：
       自動 — 有損筆數 <= LOSSY_AUTO_LIMIT（預設 10 筆）就直接取代
              並繼續轉換；超過門檻視為系統性問題，停止並要求人工判斷。
       停止 — 一律停止（本版之前的行為）。
       強制 — 不論多少筆一律取代。
     門檻的意義：少數幾筆是「個案」（造字、截斷的半個字），人工補得
     完；成千上萬筆代表編碼判斷本身就錯了（例如把雙重編碼的資料當成
     big5 匯入），這時取代成問號等於把錯誤沖進資料裡，絕不能自動做。
  Q. 取代分兩階段，因為目標字元在原編碼裡不一定存在：
       階段一（ALTER 之前）：以 SQL 的來回 CONVERT 把無法對應的字換成
              ASCII 問號。問號在任何字元集裡都合法，這步一定成功。
              整批 UPDATE 失敗時（來源位元組結構本身壞掉，CONVERT 直接
              報錯），退回用主鍵逐列修正，值在 Python 端解碼產生。
       階段二（ALTER 之後）：欄位已是 utf8mb4，才把問號換成 LOSSY_MARKER
              （預設 '〇'）。用問號當最終值太危險——它跟真正的問號無法
              區分，日後沒人看得出那裡原本有字。
  R. 取代前一律把原始位元組（HEX）、主鍵、轉換結果寫成
     charset_lossy_*.tsv 存證。資料庫裡的原始位元組被覆蓋後就再也回不
     來了，這個檔案是唯一的還原依據，務必隨備份一起保存。
"""

import configparser
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict

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

CHARSET_CHOICES = [
    "自動偵測",
    "utf8mb4",
    "utf8mb3",
    "utf8",
    "big5",
    "latin1",
    "binary",
]
ENGINE_FOLLOW_FILE = "依備份檔（建議）"
ENGINE_CHOICES = [ENGINE_FOLLOW_FILE, "MyISAM", "InnoDB"]

# ---------------------------------------------------------------------------
# backup.py 產生的非資料表檔案
#
# 檔名前綴是刻意設計的：00_ 排在最前、zz_ 排在最後，sorted() 掃目錄
# 剛好就是正確的還原順序。但它們的處理方式各不相同，不能一視同仁地
# 當作資料表匯入。
# ---------------------------------------------------------------------------
SCHEMA_FILE = "00_schema.sql"  # 只讀取來源字元集，不執行
VIEWS_FILE = "zz_views.sql"  # 依賴基底表，最後匯入
ROUTINES_FILE = "zz_routines.sql"  # 同上
GRANTS_FILE = "zz_grants.sql"  # 純註解，完全不匯入
MANIFEST_FILE = "00_manifest.txt"

INFO_FILES = {SCHEMA_FILE}  # 只讀取，不匯入
SKIP_FILES = {GRANTS_FILE}  # 完全略過
LAST_FILES = [VIEWS_FILE, ROUTINES_FILE]  # 排在所有資料表之後

# 還原後轉換 utf8mb4 時採用的 collation。
#
# 【必須與這兩處保持一致，否則會出事】
#   * classes/mysql_database.py 的 COLLATION_SUFFIX
#   * convert_sql.py 的同名設定
#
# collation 只影響比較與排序，不影響儲存，所以不一致不會弄壞資料。但只要
# 同一個資料庫裡的資料表 collation 不一致，把它們放進同一個 JOIN、UNION、
# CASE WHEN 或 IN (子查詢) 就會拋 Illegal mix of collations（錯誤 1267）。
# 那種錯誤通常幾個月後才在某支報表上突然爆出來，很難查。
#
# 選 general_ci 而非 unicode_ci 的理由不是它比較好，是它比較難搞錯：
# general_ci 是 MariaDB 的 utf8mb4 預設值，任何漏寫 COLLATE 的 CREATE
# TABLE 都會落在這裡。選 unicode_ci 的話，每一個漏寫的地方都是一顆未來的
# 1267 地雷。技術差異對本系統也不重要——unicode_ci 的優勢在歐語系的變音字
# 與展開規則，CJK 兩者都是按碼位比較，而中文排序本來就走 Big5 binary cast，
# 不靠 collation。
TARGET_COLLATION = "utf8mb4_general_ci"

# 一次 SELECT 內最多併入幾個欄位的檢查運算式（避免單句過於龐大）
CHECK_COLS_PER_QUERY = 20

# ---------------------------------------------------------------------------
# 有損字元的處理策略
# ---------------------------------------------------------------------------

# 「自動」模式下，全庫有損筆數在這個數字以內就直接取代並繼續轉換。
#
# 這個數字不是效能考量，是【性質判斷】的分界線：
#   個位數  → 個案。多半是 big5 造字區的罕用姓名字，或被 VARCHAR 截斷
#             留下的半個字。人工補得完，取代成標記字是合理的止血。
#   數百以上 → 系統性問題。幾乎一定是編碼判斷本身錯了（把雙重編碼、
#             或已經是 utf8 的資料當成 big5 匯入）。這時候取代成標記字
#             等於把錯誤永久沖進資料庫，而且會蓋掉「編碼選錯了」這個
#             唯一的線索。絕對不能自動做。
# 落在中間（十幾到上百）的情況少見，一律當成後者處理——停下來讓人看一眼
# 的成本，遠低於事後才發現一批病患姓名壞掉。
LOSSY_AUTO_LIMIT = 10

# 每個欄位最多存證幾筆原始資料（強制模式下有損筆數可能很多）
LOSSY_SAMPLE_LIMIT = 1000

# 階段一的中繼字元。ASCII 問號在任何字元集裡都是合法的單一位元組，
# 這是它唯一被選中的理由——不可拿它當最終值。
LOSSY_PLACEHOLDER = "?"

# 階段二的最終標記字元（欄位已轉成 utf8mb4 之後才寫入）。
#
# 用 '〇' 而不是問號：問號跟使用者自己打的問號無法區分，日後沒有任何人
# 看得出那個位置原本有字。'〇' 在病歷欄位裡幾乎不會自然出現，一眼可辨，
# 也方便日後 WHERE Name LIKE '%〇%' 撈出來補正。
# 若不想要兩階段，把這個值改成 LOSSY_PLACEHOLDER 即可自動跳過階段二。
LOSSY_MARKER = "〇"

LOSSY_STOP = "停止（預設，交由人工處理）"
LOSSY_AUTO = f"自動（{LOSSY_AUTO_LIMIT} 筆以內直接取代）"
LOSSY_FORCE = "強制取代（不論筆數）"
LOSSY_CHOICES = [LOSSY_AUTO, LOSSY_STOP, LOSSY_FORCE]

# 逐列修正時，把 HEX 解回文字用的 Python 編解碼器（讀取用，寬鬆）。
# big5 一律用 cp950：它是 Big5 的 Windows 超集，涵蓋範圍較大，
# 用純 big5 解碼反而會把一些正常的字判成錯誤。
CHARSET_CODECS = {
    "big5": "cp950",
    "big5hkscs": "big5hkscs",
    "cp950": "cp950",
    "gbk": "gbk",
    "gb2312": "gbk",
    "latin1": "latin-1",
    "ascii": "ascii",
    "utf8": "utf-8",
    "utf8mb3": "utf-8",
    "utf8mb4": "utf-8",
}

# 寫回時用的編解碼器（嚴格）。
#
# 【這張表存在的理由，別把它跟上面那張合併】
# 讀取要寬鬆、寫回要嚴格，兩者不能是同一個。cp950 認得一些 MariaDB 的
# big5 字元集沒有的字——最經典的是歐元符號 €（cp950 的 0xA3E1）。
# 用 cp950 解出 € 再原封不動送回伺服器，而欄位在階段一時還是 big5，
# 伺服器就直接拋 1366 Incorrect string value，整個還原被中斷。
# 所以寫回前一定要再用嚴格編解碼器來回一次，把欄位裝不下的字元
# 換成問號。
STRICT_CODECS = {
    "big5": "big5",
    "cp950": "big5",
    "big5hkscs": "big5hkscs",
    "gbk": "gbk",
    "gb2312": "gb2312",
    "latin1": "latin-1",
    "ascii": "ascii",
    "utf8": "utf-8",
    "utf8mb3": "utf-8",
    "utf8mb4": "utf-8",
}

# 部分舊版伺服器不認得 utf8mb3 這個名稱（10.6 以後才有），
# 在 SQL 的 CONVERT ... USING 裡改用 utf8。
SQL_CHARSET_ALIASES = {"utf8mb3": "utf8"}

# 匯入每個 .sql 檔時前後加掛的語句
IMPORT_PROLOGUE = (
    b"SET SESSION unique_checks=0;\n"
    b"SET SESSION foreign_key_checks=0;\n"
    b"SET SESSION autocommit=0;\n"
)
IMPORT_EPILOGUE = b"\nCOMMIT;\n"


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


def fmt_secs(seconds):
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m} 分 {s} 秒"
    h, m = divmod(m, 60)
    return f"{h} 小時 {m} 分 {s} 秒"


def split_sql_files(folder):
    """
    把目錄中的 .sql 分成三類。

    回傳 (table_files, last_files, info_files)：
      table_files — 一般資料表，照字母序匯入
      last_files  — 檢視表、routines，必須排在所有資料表之後
      info_files  — 只讀取不匯入（目前只有 00_schema.sql）

    zz_grants.sql 全是註解，直接排除。
    """
    try:
        all_files = sorted(f for f in os.listdir(folder) if f.endswith(".sql"))
    except OSError:
        return [], [], []

    table_files = [
        f
        for f in all_files
        if f not in SKIP_FILES and f not in INFO_FILES and f not in LAST_FILES
    ]
    last_files = [f for f in LAST_FILES if f in all_files]
    info_files = [f for f in INFO_FILES if f in all_files]
    return table_files, last_files, info_files


def read_source_db_charset(folder):
    """
    從 00_schema.sql 讀出來源資料庫的字元集與 collation。

    這個檔的內容形如：
        CREATE DATABASE IF NOT EXISTS `yokang` /*!40100 DEFAULT CHARACTER
        SET utf8mb4 COLLATE utf8mb4_general_ci */;
        USE `yokang`;

    只解析、不執行——裡面的 USE 會把 session 切到來源資料庫名稱，
    直接匯入會建出一個多餘的資料庫，而目標庫什麼都沒設定到。

    回傳 (charset, collation)，讀不到則回傳 (None, None)。
    """
    try:
        with open(
            os.path.join(folder, SCHEMA_FILE), encoding="utf-8", errors="replace"
        ) as f:
            text = f.read()
    except OSError:
        return None, None

    charset = re.search(r"CHARACTER\s+SET\s+(\w+)", text, re.IGNORECASE)
    collation = re.search(r"COLLATE\s+(\w+)", text, re.IGNORECASE)
    return (
        charset.group(1) if charset else None,
        collation.group(1) if collation else None,
    )


def verify_against_manifest(folder):
    """
    比對 00_manifest.txt 與實際檔案，回傳問題描述清單。

    manifest 由 backup.py 產生，每行格式為：
        檔名<TAB>位元組數<TAB>OK|FAIL<TAB>錯誤訊息

    沒有 manifest（舊備份或其他工具產生）時回傳空清單，不視為錯誤。
    """
    path = os.path.join(folder, MANIFEST_FILE)
    if not os.path.exists(path):
        return []

    problems = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        return [f"無法讀取 {MANIFEST_FILE}：{e}"]

    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue

        name, size, status = parts[0], parts[1], parts[2]
        message = parts[3] if len(parts) > 3 else ""

        if status != "OK":
            problems.append(
                f"{name}：備份當下就標記為 {status}"
                + (f"（{message}）" if message else "")
            )
            continue

        full_path = os.path.join(folder, name)
        if not os.path.exists(full_path):
            problems.append(f"{name}：manifest 有記錄但檔案不存在")
            continue

        try:
            actual = os.path.getsize(full_path)
        except OSError as e:
            problems.append(f"{name}：無法取得檔案大小（{e}）")
            continue

        if str(actual) != size:
            problems.append(f"{name}：大小不符（manifest {size}／實際 {actual}）")

    return problems


def detect_sql_charset(folder, sql_files, max_files=3, sample_bytes=4 * 1024 * 1024):
    """
    偵測 .sql 備份檔的內容編碼。回傳 (charset, 說明) 或 (None, 原因)。
    判斷順序：
      1. 檔頭的 SET NAMES 聲明（mysqldump 標準檔頭，最權威）。
      2. UTF-8 BOM。
      3. 位元組結構：整份樣本能以嚴格 UTF-8 解碼 → utf8mb4；
         否則能以 cp950（Big5 的 Windows 超集）解碼 → big5。
    純 ASCII 內容會被判為 utf8mb4，選任何編碼匯入結果皆相同，無影響。

    注意：新版 backup.py 以 --default-character-set=binary 匯出，
    檔頭會寫 SET NAMES binary，此處會如實回傳 "binary"。那是正確的
    匯入編碼（原樣灌回、不轉碼），但不可拿去當資料庫的預設字元集，
    呼叫端須另行處理。
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


def inspect_dump_format(folder, sql_files, max_files=3):
    """
    粗略判斷備份檔是否使用 extended-insert（一句 INSERT 帶多列）。
    一列一句 INSERT 會讓匯入變成大量來回，是常見的效能陷阱。
    回傳 (是否疑似逐列 INSERT, 說明字串)。
    """
    for name in sql_files[:max_files]:
        path = os.path.join(folder, name)
        try:
            size = os.path.getsize(path)
            if size < 512 * 1024:  # 小檔看不出來，換下一個
                continue
            with open(path, "rb") as f:
                head = f.read(2 * 1024 * 1024)
        except OSError:
            continue
        inserts = head.count(b"INSERT INTO")
        if inserts == 0:
            continue
        avg = len(head) / inserts
        if avg < 400:
            return True, (
                f"{name} 前 2MB 內有 {inserts} 句 INSERT（平均每句約 "
                f"{avg:.0f} bytes），疑似逐列 INSERT（匯出時未使用 "
                f"extended-insert）。重新匯出時加上 --opt 可大幅加快還原。"
            )
        return False, f"{name} 使用批次 INSERT（平均每句約 {avg:.0f} bytes），正常。"
    return False, ""


def scan_dump_engines(folder, sql_files, head_bytes=64 * 1024):
    """
    掃描備份檔中 CREATE TABLE 的 ENGINE= 宣告。

    mysqldump 會把 DROP TABLE / CREATE TABLE 放在檔案最前面，之後才是
    INSERT，因此只讀檔頭即可，不必讀完整個檔案。

    回傳 (engine_counts, myisam_files)：
      engine_counts — {引擎名稱大寫: 張數}
      myisam_files  — 宣告 ENGINE=MyISAM 的檔名清單
    """
    engine_counts = defaultdict(int)
    myisam_files = []
    pattern = re.compile(rb"ENGINE\s*=\s*(\w+)", re.IGNORECASE)

    for name in sql_files:
        try:
            with open(os.path.join(folder, name), "rb") as f:
                head = f.read(head_bytes)
        except OSError:
            continue
        found = pattern.findall(head)
        if not found:
            continue
        for raw in found:
            engine = raw.decode("ascii", errors="replace").upper()
            engine_counts[engine] += 1
            if engine == "MYISAM" and name not in myisam_files:
                myisam_files.append(name)

    return dict(engine_counts), myisam_files


def to_ascii_safe(text):
    """把所有非 ASCII 字元換成中繼問號。最後的保險，任何字元集都存得下。"""
    return "".join(ch if ord(ch) < 128 else LOSSY_PLACEHOLDER for ch in text or "")


def sanitize_hex(hex_value, charset):
    """
    把原始位元組（HEX 字串）在 Python 端解碼成【欄位存得下】的文字。

    只在伺服器端的整批 CONVERT 失敗時才用得到——那代表位元組結構本身
    就壞掉（例如被 VARCHAR 截斷、只剩半個 Big5 字），MariaDB 的 CONVERT
    會直接報錯而不是給你問號。Python 的 errors='replace' 沒有這個問題，
    壞掉的位元組變成 U+FFFD，再統一換成中繼問號。

    兩道轉換缺一不可：
      讀取（寬鬆，cp950）— 盡量把還救得回來的字解出來。
      寫回（嚴格，big5）— 確保每個字元在【欄位目前的字元集】裡都存在。
                          少了這道，cp950 才有的字（€ 等）會原封不動送給
                          伺服器，寫進 big5 欄位時直接噴 1366。
    """
    key = (charset or "").lower()
    read_codec = CHARSET_CODECS.get(key, "utf-8")
    write_codec = STRICT_CODECS.get(key, read_codec)

    try:
        raw = bytes.fromhex(hex_value or "")
    except (ValueError, TypeError):
        return LOSSY_PLACEHOLDER

    try:
        text = raw.decode(read_codec, errors="replace")
    except LookupError:  # 認不得的編碼名稱
        text = raw.decode("utf-8", errors="replace")
    text = text.replace("\ufffd", LOSSY_PLACEHOLDER)

    try:
        text = text.encode(write_codec, errors="replace").decode(
            write_codec, errors="replace"
        )
    except LookupError:
        pass
    return text.replace("\ufffd", LOSSY_PLACEHOLDER)


def write_lossy_evidence(folder, rows):
    """
    把被取代前的原始位元組寫成 TSV 存證，回傳檔案路徑。

    這個檔案是唯一的還原依據：資料庫裡的原始位元組一旦被覆蓋，
    就再也回不來了。優先寫在備份目錄，不可寫時退回程式所在目錄。
    """
    if not rows:
        return ""

    name = f"charset_lossy_{time.strftime('%Y%m%d_%H%M%S')}.tsv"
    header = "資料表\t欄位\t主鍵\t原字元集\t原始HEX\t轉換後\n"
    body = "\n".join(
        "\t".join(
            [
                item["table"],
                item["column"],
                item["pk_text"],
                item["charset"],
                item["hex"] or "",
                (item["converted"] or "").replace("\t", " ").replace("\n", " "),
            ]
        )
        for item in rows
    )

    for base in (folder, os.path.dirname(os.path.abspath(__file__))):
        path = os.path.join(base, name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(header)
                f.write(body + "\n")
            return path
        except OSError:
            continue
    return ""


def run_import(cmd, env, full_path):
    """
    以管線方式送出 prologue + 檔案內容 + COMMIT。
    回傳 (returncode, stderr 字串)。

    注意：寫完之後【不可】自行呼叫 proc.stdin.close()。
    Popen.communicate() 內部會先做一次 self.stdin.flush()，
    而它只攔截 BrokenPipeError；對已關閉的檔案物件會拋出
    ValueError: flush of closed file（Windows 分支尤其明顯），
    真正的 mysql 錯誤訊息反而被蓋掉。交給 communicate() 關即可。
    """
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **subprocess_flags(),
    )
    write_error = ""
    try:
        proc.stdin.write(IMPORT_PROLOGUE)
        with open(full_path, "rb") as f:
            shutil.copyfileobj(f, proc.stdin, 4 * 1024 * 1024)
        proc.stdin.write(IMPORT_EPILOGUE)
    except Exception as e:
        # 多半代表 mysql 已因 SQL 錯誤提早結束；真正原因在 stderr
        write_error = f"（送入資料中斷：{type(e).__name__}: {e}）"

    try:
        _, err = proc.communicate()
    except Exception as e:
        try:
            proc.kill()
            _, err = proc.communicate()
        except Exception:
            err = b""
        write_error += f"（communicate 失敗：{type(e).__name__}: {e}）"

    msg = err.decode("utf-8", errors="replace").strip()
    if write_error:
        msg = (msg + " " + write_error).strip()
    rc = proc.returncode
    if rc == 0 and write_error:
        rc = 1
    return rc, msg


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
        self._pk_cache = {}

    def log(self, msg):
        self.sig_log.emit(msg)

    # -- 持久性設定的暫時放寬 -------------------------------------------
    def _relax_durability(self, cur):
        """回傳原值 dict（成功時）或 None（無權限/失敗）。"""
        try:
            cur.execute(
                "SELECT @@GLOBAL.innodb_flush_log_at_trx_commit, @@GLOBAL.sync_binlog"
            )
            old_flush, old_sync = cur.fetchone()
            cur.execute("SET GLOBAL innodb_flush_log_at_trx_commit = 2")
            cur.execute("SET GLOBAL sync_binlog = 0")
            self.log(
                f"已暫時放寬持久性設定："
                f"innodb_flush_log_at_trx_commit {old_flush}→2、"
                f"sync_binlog {old_sync}→0（結束後會還原）。"
            )
            return {"flush": old_flush, "sync": old_sync}
        except Exception as e:
            self.log(f"（無法調整持久性設定，略過此優化：{e}）")
            return None

    def _restore_durability(self, cur, saved):
        if not saved:
            return
        try:
            cur.execute(
                "SET GLOBAL innodb_flush_log_at_trx_commit = %s" % int(saved["flush"])
            )
            cur.execute("SET GLOBAL sync_binlog = %s" % int(saved["sync"]))
            self.log(
                f"已還原持久性設定："
                f"innodb_flush_log_at_trx_commit={saved['flush']}、"
                f"sync_binlog={saved['sync']}。"
            )
        except Exception as e:
            self.log(
                f"⚠ 持久性設定還原失敗：{e}\n"
                f"  請手動執行："
                f"SET GLOBAL innodb_flush_log_at_trx_commit={saved['flush']}; "
                f"SET GLOBAL sync_binlog={saved['sync']};"
            )

    # -- 有損字元的強制取代 ---------------------------------------------
    def _pk_columns(self, cur, db, table):
        """回傳資料表的主鍵欄位（依序），沒有主鍵則回傳空清單。"""
        key = (db, table)
        if key in self._pk_cache:
            return self._pk_cache[key]

        cur.execute(
            """SELECT COLUMN_NAME FROM information_schema.STATISTICS
               WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                 AND INDEX_NAME = 'PRIMARY'
               ORDER BY SEQ_IN_INDEX""",
            (db, table),
        )
        cols = [r[0] for r in cur.fetchall()]
        self._pk_cache[key] = cols
        return cols

    def _force_lossy_convert(self, cur, db, table, col, cs, condition, evidence):
        """
        階段一：把無法無損轉換的資料原地換成中繼問號，換之前先存證。

        用來回 CONVERT 一次完成：內層轉 utf8mb4 時無法對應的字變成問號，
        外層轉回原字元集就是合法的 0x3F，同一欄裡其他正常的字原封不動。

        回傳 (實際更動筆數, 說明字串)。
        """
        pk_cols = self._pk_columns(cur, db, table)
        pk_select = "".join(f"`{c}`, " for c in pk_cols)
        start_index = len(evidence)

        # 先存證。原始位元組被覆蓋後就再也回不來了，這步不能省。
        cur.execute(
            f"SELECT {pk_select}HEX(`{col}`), CONVERT(`{col}` USING utf8mb4) "
            f"FROM `{db}`.`{table}` WHERE {condition} "
            f"LIMIT {LOSSY_SAMPLE_LIMIT}"
        )
        for row in cur.fetchall():
            pk_values = list(row[: len(pk_cols)])
            evidence.append(
                {
                    "table": table,
                    "column": col,
                    "charset": cs,
                    "pk_cols": pk_cols,
                    "pk_values": pk_values,
                    "pk_text": (
                        ", ".join(f"{c}={v}" for c, v in zip(pk_cols, pk_values))
                        or "（此表無 PRIMARY KEY）"
                    ),
                    "hex": row[len(pk_cols)],
                    "converted": row[len(pk_cols) + 1],
                }
            )
        sampled = evidence[start_index:]

        sql_cs = SQL_CHARSET_ALIASES.get((cs or "").lower(), cs)
        try:
            cur.execute(
                f"UPDATE `{db}`.`{table}` SET `{col}` = "
                f"CONVERT(CONVERT(`{col}` USING utf8mb4) USING {sql_cs}) "
                f"WHERE {condition}"
            )
            return cur.rowcount, ""
        except Exception as e:
            # 位元組結構本身壞掉時 CONVERT 會直接報錯，退回逐列修正
            if not pk_cols:
                raise RuntimeError(
                    f"{table}.{col} 整批取代失敗，且該表沒有 PRIMARY KEY，"
                    f"無法逐列修正：{e}"
                ) from e
            self.log(f"  ⚠ {table}.{col} 整批取代失敗（{e}），改用主鍵逐列修正 …")

        # 逐列修正：單列失敗只記錄、不中斷。這整個功能的目的就是
        # 「不要讓幾筆資料毀掉整鍋粥」，錯誤處理本身當然也要遵守。
        where = " AND ".join(f"`{c}` <=> %s" for c in pk_cols)
        update_sql = f"UPDATE `{db}`.`{table}` SET `{col}` = %s WHERE {where}"
        changed = 0
        unresolved = []
        for item in sampled:
            value = sanitize_hex(item["hex"], cs)
            last_error = None
            # 第二次嘗試把非 ASCII 全部拿掉：字會少得多，但保證存得進去。
            for candidate in (value, to_ascii_safe(value)):
                try:
                    cur.execute(update_sql, [candidate, *item["pk_values"]])
                    changed += cur.rowcount
                    last_error = None
                    break
                except Exception as e:  # noqa: BLE001
                    last_error = e
            if last_error is not None:
                unresolved.append(item["pk_text"])
                self.log(f"    ✗ {item['pk_text']} 無法修正：{last_error}")

        note = "逐列修正"
        if unresolved:
            note += f"，{len(unresolved)} 筆仍未修正"
        if len(sampled) >= LOSSY_SAMPLE_LIMIT:
            note += f"（僅處理前 {LOSSY_SAMPLE_LIMIT} 筆，可能仍有殘留）"
        return changed, note

    def _apply_lossy_marker(self, cur, db, evidence, skip_tables):
        """
        階段二：欄位已轉成 utf8mb4 之後，把中繼問號換成最終標記字元。

        必須排在 ALTER 之後——欄位還是 big5 的時候寫不進 '〇'，
        寫進去只會又變成一個問號。

        回傳 (更動筆數, 略過的欄位清單)。
        """
        if LOSSY_MARKER == LOSSY_PLACEHOLDER:
            return 0, []

        updated = 0
        skipped = []
        for item in evidence:
            table, col = item["table"], item["column"]
            if table in skip_tables or not item["pk_cols"]:
                label = f"{table}.{col}"
                if label not in skipped:
                    skipped.append(label)
                continue
            where = " AND ".join(f"`{c}` <=> %s" for c in item["pk_cols"])
            try:
                cur.execute(
                    f"UPDATE `{db}`.`{table}` SET `{col}` = "
                    f"REPLACE(`{col}`, %s, %s) WHERE {where}",
                    [LOSSY_PLACEHOLDER, LOSSY_MARKER, *item["pk_values"]],
                )
                updated += cur.rowcount
            except Exception as e:
                label = f"{table}.{col}（{e}）"
                if label not in skipped:
                    skipped.append(label)
        return updated, skipped

    # -- 主流程 -----------------------------------------------------------
    def run(self):
        conn = None
        cur = None
        saved_durability = None
        try:
            p = self.p
            db = p["database"]
            file_charset = p["file_charset"]
            engine_choice = p["engine"]
            follow_file_engine = engine_choice == ENGINE_FOLLOW_FILE
            to_utf8mb4 = p["to_utf8mb4"]
            lossy_mode = p["lossy_mode"]

            t_start = time.time()
            t_import = t_check = t_alter = t_analyze = 0.0

            # 資料表檔與物件檔分開：檢視表、routines 依賴基底表，
            # 必須排在所有資料表之後；00_schema.sql 只讀不匯入。
            table_files, last_files, info_files = split_sql_files(p["sql_folder"])
            sql_files = table_files + last_files
            total = len(sql_files)
            if total == 0:
                raise RuntimeError("指定目錄中沒有任何可匯入的 .sql 檔案。")

            self.log(f"找到 {len(table_files)} 個資料表檔案。")
            if last_files:
                self.log(
                    "另有物件檔案（將排在資料表之後匯入）：" + "、".join(last_files)
                )
            if info_files:
                self.log(f"參考檔案（只讀取不匯入）：{'、'.join(info_files)}")

            # 編碼偵測只看資料表檔——00_schema.sql 與 zz_grants.sql 是
            # backup.py 自行產生的 UTF-8 文字，不代表備份資料的編碼。
            if file_charset == "自動偵測":
                detected, reason = detect_sql_charset(p["sql_folder"], table_files)
                if not detected:
                    raise RuntimeError(
                        f"無法自動判斷備份檔編碼（{reason}）。\n"
                        f"請在「備份檔編碼」手動選擇正確的編碼後重新執行。"
                    )
                file_charset = detected
                self.log(f"自動偵測備份檔編碼：{file_charset}（{reason}）")

            slow_dump, dump_note = inspect_dump_format(p["sql_folder"], table_files)
            if dump_note:
                self.log(("⚠ " if slow_dump else "") + dump_note)

            # 備份檔宣告的引擎（覆蓋風險已在主視窗確認，這裡留下記錄）
            dump_engines, dump_myisam = scan_dump_engines(p["sql_folder"], table_files)
            if dump_engines:
                self.log(
                    "備份檔宣告的引擎："
                    + "、".join(f"{e} {c} 張" for e, c in sorted(dump_engines.items()))
                )
            if dump_myisam and follow_file_engine:
                self.log(
                    f"⚠ 備份檔中有 {len(dump_myisam)} 張表宣告 ENGINE=MyISAM，"
                    f"「{ENGINE_FOLLOW_FILE}」會照原樣還原成 MyISAM。"
                )

            self.log(
                f"目標資料庫：{db}；備份檔編碼：{file_charset}；"
                f"引擎：{engine_choice}；"
                f"轉換為 utf8mb4：{'是' if to_utf8mb4 else '否'}"
                + (f"；有損資料：{lossy_mode}" if to_utf8mb4 else "")
            )

            conn = mysql.connector.connect(
                host=p["host"],
                port=p["port"],
                user=p["user"],
                password=p["password"],
                charset="utf8mb4",
                # 一定要明確指定 collation。mysql-connector-python 內建一張
                # charset → collation 對照表，utf8mb4 會對到 MySQL 8 的預設值
                # utf8mb4_0900_ai_ci；MariaDB 沒有這個 collation，連線當下就會
                # 拋 1273 Unknown collation，連第一次查詢都到不了。
                collation="utf8mb4_general_ci",
                connection_timeout=10,
                # mysql.connector 預設 autocommit=False。若不明確開啟，
                # 步驟 3 的檢查查詢會開啟一個交易並持續到步驟 4 第一句
                # DDL 隱含提交為止，期間 InnoDB 持有 read view、擋住
                # purge，undo log 會一直累積。這裡全是 DDL 與唯讀查詢，
                # 開啟 autocommit 沒有任何副作用。
                autocommit=True,
            )
            cur = conn.cursor()

            # ---------- 1. 建立（或確認）目標資料庫 ----------
            self.log("\n[步驟 1/5] 確認目標資料庫 …")

            # binary 是「傳輸時不轉碼」的設定，不是資料庫的字元集。
            # 拿它去 CREATE DATABASE 會讓之後在該庫新建的資料表全部
            # 變成 binary，中文無法正常比較排序。真正的字元集寫在各表的
            # CREATE TABLE 與 00_schema.sql 裡。
            if file_charset == "binary":
                source_charset, source_collation = read_source_db_charset(
                    p["sql_folder"]
                )
                db_charset = "utf8mb4" if to_utf8mb4 else (source_charset or "utf8mb4")
                self.log(
                    f"備份檔以 binary 匯出（原樣保留位元組，不轉碼）；"
                    f"目標資料庫預設字元集採用 {db_charset}"
                    + (
                        f"（讀自 {SCHEMA_FILE}：{source_charset} / {source_collation}）"
                        if source_charset
                        else "（找不到 00_schema.sql，退回 utf8mb4）"
                    )
                )
            else:
                db_charset = "utf8mb4" if to_utf8mb4 else file_charset

            cur.execute(
                "SELECT COUNT(*) FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = %s",
                (db,),
            )
            if cur.fetchone()[0] == 0:
                # 明確帶上 COLLATE，不依賴「charset 的預設 collation」。
                # 目前兩者剛好相同，但寫死才不會在有人改 TARGET_COLLATION
                # 時悄悄產生不一致。非 utf8mb4 的情形（未勾選轉換）維持
                # 由伺服器決定。
                if db_charset == "utf8mb4":
                    cur.execute(
                        f"CREATE DATABASE `{db}` DEFAULT CHARACTER SET utf8mb4 "
                        f"COLLATE {TARGET_COLLATION}"
                    )
                    self.log(f"已建立資料庫 `{db}`（utf8mb4 / {TARGET_COLLATION}）。")
                else:
                    cur.execute(
                        f"CREATE DATABASE `{db}` DEFAULT CHARACTER SET {db_charset}"
                    )
                    self.log(f"已建立資料庫 `{db}`（預設字元集 {db_charset}）。")
            else:
                self.log(f"資料庫 `{db}` 已存在，直接使用。")
                # （已含資料表的覆蓋確認在按下開始前的主視窗完成）

            if p["relax_durability"]:
                saved_durability = self._relax_durability(cur)

            # ---------- 2. 逐檔匯入 ----------
            self.log(
                f"\n[步驟 2/5] 逐檔匯入（以 {file_charset} 編碼讀取，每檔一個交易）…"
            )
            t0_phase = time.time()
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
                rc, err = run_import(cmd, env, full_path)
                if rc != 0:
                    failed.append((sql_file, err))
                    self.log(f"  ✗ [{i}/{total}] {sql_file} 失敗：{err}")
                else:
                    self.log(
                        f"  ✓ [{i}/{total}] {sql_file}（{time.time() - t0:.1f} 秒）"
                    )
            t_import = time.time() - t0_phase

            if failed:
                detail = "\n  ".join(f"{n}：{e}" for n, e in failed)
                raise RuntimeError(
                    f"{len(failed)}/{total} 個檔案匯入失敗，"
                    f"資料庫【不完整】，請勿直接使用：\n  {detail}\n"
                    f"修正問題後可重新執行（同名資料表會被覆蓋，可安全重跑）。"
                )

            self.log(f"全部 {total} 個檔案匯入成功（耗時 {fmt_secs(t_import)}）。")

            # ---------- 3. 字元集無損檢查（可選） ----------
            normalized = []
            forced = []
            lossy_evidence = []
            evidence_path = ""
            tables_need_rebuild = set()  # 有非 utf8mb4 文字欄位 → 需重建
            skipped_empty = 0
            if to_utf8mb4:
                self.log("\n[步驟 3/5] 檢查所有文字資料能否無損轉換為 utf8mb4 …")
                t0_phase = time.time()
                # 只查 BASE TABLE：檢視表的欄位不能也不需要 ALTER，
                # 撈進來只會白做一次全表掃描。
                cur.execute(
                    """
                    SELECT c.TABLE_NAME, c.COLUMN_NAME, c.CHARACTER_SET_NAME
                    FROM information_schema.COLUMNS c
                    JOIN information_schema.TABLES t
                      ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
                     AND t.TABLE_NAME   = c.TABLE_NAME
                    WHERE c.TABLE_SCHEMA = %s
                      AND t.TABLE_TYPE = 'BASE TABLE'
                      AND c.CHARACTER_SET_NAME IS NOT NULL
                      AND c.CHARACTER_SET_NAME <> 'utf8mb4'
                    ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION""",
                    (db,),
                )
                text_cols = cur.fetchall()

                cols_by_table = defaultdict(list)
                for table, col, cs in text_cols:
                    cols_by_table[table].append((col, cs))

                # 原本是 tables_need_rebuild = set(cols_by_table.keys())，
                # 也就是「字元集不是 utf8mb4」的表才重建。那會漏掉
                # 「字元集已是 utf8mb4、但 collation 不是目標值」的表——
                # MariaDB 11.4 起 utf8mb4 的預設 collation 是 uca1400_ai_ci，
                # 沒帶 COLLATE 的 ALTER 全會落在那裡，而它們的
                # CHARACTER_SET_NAME 就是 utf8mb4，上面那個查詢篩不出來。
                cur.execute(
                    """
                    SELECT DISTINCT c.TABLE_NAME
                    FROM information_schema.COLUMNS c
                    JOIN information_schema.TABLES t
                      ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
                     AND t.TABLE_NAME   = c.TABLE_NAME
                    WHERE c.TABLE_SCHEMA = %s
                      AND t.TABLE_TYPE = 'BASE TABLE'
                      AND c.COLLATION_NAME IS NOT NULL
                      AND c.COLLATION_NAME <> %s""",
                    (db, TARGET_COLLATION),
                )
                tables_need_rebuild = {r[0] for r in cur.fetchall()}

                # lossy 的每一項：(表, 欄, 原字元集, 筆數, WHERE 條件)
                # 條件要一起留著，強制取代時才知道要更新哪些列。
                lossy = []
                n_tables_to_check = len(cols_by_table)
                for idx, table in enumerate(sorted(cols_by_table.keys()), start=1):
                    self.sig_progress.emit(idx, n_tables_to_check or 1)
                    cols = cols_by_table[table]

                    # 空表不必掃描
                    cur.execute(f"SELECT 1 FROM `{db}`.`{table}` LIMIT 1")
                    if not cur.fetchall():
                        skipped_empty += 1
                        continue

                    t0 = time.time()
                    for start in range(0, len(cols), CHECK_COLS_PER_QUERY):
                        chunk = cols[start : start + CHECK_COLS_PER_QUERY]
                        selects = []
                        conditions = []
                        for col, cs in chunk:
                            # 第一級：嚴格位元組來回比對（NULL 視為相等）
                            strict_ne = (
                                f"NOT (CAST(CONVERT(CONVERT(`{col}` USING utf8mb4)"
                                f" USING {cs}) AS BINARY)"
                                f" <=> CAST(`{col}` AS BINARY))"
                            )
                            # 第二級：判定是否「真正有損」。
                            # 真正有損 = 轉為 utf8mb4 後字元內容不穩定，
                            # 或轉換產生新的 '?'（無法對應的字被取代）。
                            # 否則為同義異碼，轉換後字義不變，僅位元組正規化。
                            u1 = f"CONVERT(`{col}` USING utf8mb4)"
                            truly = (
                                f"NOT (CAST(CONVERT(CONVERT({u1} USING {cs})"
                                f"     USING utf8mb4) AS BINARY)"
                                f"     <=> CAST({u1} AS BINARY))"
                                f" OR (LENGTH({u1}) - LENGTH(REPLACE({u1}, '?', '')))"
                                f"    > (LENGTH(`{col}`)"
                                f"       - LENGTH(REPLACE(`{col}`, '?', '')))"
                            )
                            selects.append(f"SUM({strict_ne})")
                            selects.append(f"SUM(({strict_ne}) AND ({truly}))")
                            conditions.append(f"({strict_ne}) AND ({truly})")

                        # 整張表只掃一次，所有欄位的計數一次算完
                        cur.execute(
                            f"SELECT {', '.join(selects)} FROM `{db}`.`{table}`"
                        )
                        row = cur.fetchone()

                        for j, (col, cs) in enumerate(chunk):
                            bad = int(row[j * 2] or 0)
                            truly_lossy = int(row[j * 2 + 1] or 0)
                            if not bad:
                                continue
                            if truly_lossy:
                                lossy.append(
                                    (table, col, cs, truly_lossy, conditions[j])
                                )
                                self.log(
                                    f"  ✗ {table}.{col}：{truly_lossy} 筆無法無損轉換"
                                )
                            if bad - truly_lossy > 0:
                                normalized.append(
                                    f"{table}.{col}（{bad - truly_lossy} 筆）"
                                )
                                self.log(
                                    f"  ⚠ {table}.{col}：{bad - truly_lossy} 筆"
                                    f"含同義異碼符號，轉換後將正規化為標準"
                                    f" Unicode 編碼（字義不變），放行。"
                                )
                    self.log(
                        f"  · [{idx}/{n_tables_to_check}] {table}"
                        f"（{len(cols)} 欄，{time.time() - t0:.1f} 秒）"
                    )

                t_check = time.time() - t0_phase

                # ----- 有損資料的處置 -----
                if lossy:
                    total_lossy = sum(n for _t, _c, _cs, n, _w in lossy)
                    detail = "\n  ".join(
                        f"{t}.{c}（{n} 筆，原字元集 {cs}）" for t, c, cs, n, _w in lossy
                    )

                    if lossy_mode == LOSSY_FORCE:
                        do_force = True
                    elif lossy_mode == LOSSY_STOP:
                        do_force = False
                    else:  # 自動：只有少量個案才自行處理
                        do_force = total_lossy <= LOSSY_AUTO_LIMIT

                    if not do_force:
                        over_limit = (
                            lossy_mode != LOSSY_STOP and total_lossy > LOSSY_AUTO_LIMIT
                        )
                        raise RuntimeError(
                            "以下欄位含有無法無損轉換為 utf8mb4 的資料"
                            f"（共 {total_lossy} 筆；轉換後字元會遺失或變成 '?'，"
                            "常見原因：big5 造字區的罕用字），"
                            "已停止字元集轉換：\n  "
                            + detail
                            + (
                                f"\n筆數超過自動處理上限（{LOSSY_AUTO_LIMIT} 筆）。"
                                "這麼多筆通常代表「備份檔編碼」選錯了"
                                "（例如把已是 utf8 或雙重編碼的資料當成 big5 匯入），"
                                "而不是真的有這麼多罕用字——"
                                "請先確認編碼設定，不要直接改用強制取代。"
                                if over_limit
                                else ""
                            )
                            + f"\n資料已完整還原為原編碼（{file_charset}），"
                            "可直接使用。請先確認並處理上述資料，"
                            "或取消勾選轉換選項後重新執行。"
                        )

                    self.log(
                        f"\n⚠ 共 {total_lossy} 筆無法無損轉換"
                        + (
                            f"（未超過 {LOSSY_AUTO_LIMIT} 筆，依「自動」模式處理）"
                            if lossy_mode == LOSSY_AUTO
                            else "（依「強制取代」模式處理）"
                        )
                        + f"，將以 '{LOSSY_MARKER}' 取代，原始位元組先存證。"
                    )
                    for table, col, cs, _n, condition in lossy:
                        changed, note = self._force_lossy_convert(
                            cur, db, table, col, cs, condition, lossy_evidence
                        )
                        forced.append(f"{table}.{col}（{changed} 筆）")
                        self.log(
                            f"  → {table}.{col}：{changed} 筆已取代"
                            + (f"（{note}）" if note else "")
                        )

                    evidence_path = write_lossy_evidence(
                        p["sql_folder"], lossy_evidence
                    )
                    if evidence_path:
                        self.log(f"  原始資料存證：{evidence_path}")
                    else:
                        self.log(
                            "  ⚠ 存證檔寫入失敗！原始位元組已無其他備份，"
                            "請立即從備份檔重新確認這些資料。"
                        )

                if n_tables_to_check:
                    self.log(
                        f"檢查完成：{len(text_cols)} 個文字欄位"
                        f"（分佈於 {n_tables_to_check} 張表，"
                        f"其中 {skipped_empty} 張為空表已略過）"
                        + ("已處理有損資料" if forced else "皆可無損轉換")
                        + (
                            f"；{len(normalized)} 個欄位含同義異碼，將正規化"
                            if normalized
                            else ""
                        )
                        + f"。耗時 {fmt_secs(t_check)}。"
                    )
                else:
                    self.log("所有文字欄位已是 utf8mb4，無須無損檢查。")
            else:
                self.log("\n[步驟 3/5] 未勾選字元集轉換，略過。")

            # ---------- 4. 一次 ALTER 完成字元集 + 引擎 ----------
            self.log("\n[步驟 4/5] 套用字元集／引擎變更 …")
            t0_phase = time.time()
            cur.execute(
                "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY TABLE_NAME",
                (db,),
            )
            tables_info = cur.fetchall()

            plans = []  # (table, [alter specs], 說明)
            for table, tbl_engine, tbl_coll in tables_info:
                specs = []
                notes = []
                if to_utf8mb4:
                    if table in tables_need_rebuild:
                        specs.append(
                            f"CONVERT TO CHARACTER SET utf8mb4 "
                            f"COLLATE {TARGET_COLLATION}"
                        )
                        notes.append("字元集")
                    # 原本判斷 startswith("utf8mb4")——但 utf8mb4_uca1400_ai_ci
                    # 也是 utf8mb4 開頭，會被判定成「已經正確」而完全不處理。
                    elif (tbl_coll or "") != TARGET_COLLATION:
                        # 沒有非 utf8mb4 的文字欄位，只是預設字元集不符：
                        # 改中繼資料即可，不需重建資料
                        specs.append(
                            f"DEFAULT CHARACTER SET utf8mb4 COLLATE {TARGET_COLLATION}"
                        )
                        notes.append("預設字元集")
                if not follow_file_engine:
                    if (tbl_engine or "").upper() != engine_choice.upper():
                        specs.append(f"ENGINE={engine_choice}")
                        notes.append(f"引擎→{engine_choice}")
                if specs:
                    plans.append((table, specs, "、".join(notes)))

            if follow_file_engine:
                self.log("資料引擎依備份檔原樣保留，不做引擎轉換。")

            alter_failed = []
            if not plans:
                self.log("沒有需要變更的資料表。")
            else:
                self.log(f"{len(plans)} 張表需要變更，逐張處理 …")
                for i, (table, specs, notes) in enumerate(plans, start=1):
                    self.sig_progress.emit(i, len(plans))
                    t0 = time.time()
                    sql = f"ALTER TABLE `{db}`.`{table}` " + ", ".join(specs)
                    try:
                        cur.execute(sql)
                        self.log(
                            f"  ✓ [{i}/{len(plans)}] {table}"
                            f"（{notes}，{time.time() - t0:.1f} 秒）"
                        )
                    except Exception as e:
                        alter_failed.append((table, notes, str(e)))
                        self.log(
                            f"  ✗ [{i}/{len(plans)}] {table}（{notes}）失敗：{e}"
                            f"（該表維持原狀，資料未受影響）"
                        )
                if to_utf8mb4:
                    try:
                        cur.execute(
                            f"ALTER DATABASE `{db}` CHARACTER SET utf8mb4 "
                            f"COLLATE {TARGET_COLLATION}"
                        )
                    except Exception as e:
                        self.log(f"  ⚠ 資料庫預設字元集設定失敗：{e}")

            # 階段二：欄位已是 utf8mb4，把中繼問號換成最終標記字元。
            # ALTER 失敗的表要跳過——它的欄位還是舊字元集，寫不進標記字。
            marker_skipped = []
            if lossy_evidence:
                failed_tables = {t for t, _n, _e in alter_failed}
                n_marked, marker_skipped = self._apply_lossy_marker(
                    cur, db, lossy_evidence, failed_tables
                )
                if n_marked:
                    self.log(
                        f"  · 已將 {n_marked} 筆的取代字元標記為 '{LOSSY_MARKER}'。"
                    )
                if marker_skipped:
                    self.log(
                        f"  ⚠ {len(marker_skipped)} 個欄位無法標記"
                        f"（維持 '{LOSSY_PLACEHOLDER}'）：" + "、".join(marker_skipped)
                    )
            t_alter = time.time() - t0_phase

            # ---------- 5. 更新統計資訊 + 結構體檢 ----------
            # 大量匯入後 InnoDB 的取樣統計可能失準，優化器會選錯索引，
            # 症狀是「還原完的資料庫查詢特別慢」。ANALYZE 只重算統計、
            # 不重建資料，很快。務必排在步驟 4 之後——ALTER 會重建表，
            # 順序顛倒的話統計立刻又失效。
            self.log("\n[步驟 5/5] 更新統計資訊 …")
            t0_phase = time.time()
            analyze_failed = []
            n_analyze = len(tables_info)
            for i, (table, _eng, _coll) in enumerate(tables_info, start=1):
                self.sig_progress.emit(i, n_analyze or 1)
                try:
                    cur.execute(f"ANALYZE TABLE `{db}`.`{table}`")
                    cur.fetchall()  # ANALYZE 會回傳結果列，必須取完
                except Exception as e:
                    analyze_failed.append(table)
                    self.log(f"  ⚠ {table} 統計更新失敗：{e}")
            if analyze_failed:
                self.log(
                    f"{n_analyze - len(analyze_failed)}/{n_analyze} 張表統計已更新，"
                    f"{len(analyze_failed)} 張失敗（不影響資料正確性）。"
                )
            else:
                self.log(f"{n_analyze} 張表統計已全部更新。")

            # 缺少 PRIMARY KEY 的資料表：InnoDB 會自建隱藏的 6-byte
            # rowid，效能較差，之後要轉 PostgreSQL 也會卡。僅提醒。
            cur.execute(
                """
                SELECT t.TABLE_NAME
                FROM information_schema.TABLES t
                WHERE t.TABLE_SCHEMA = %s
                  AND t.TABLE_TYPE = 'BASE TABLE'
                  AND NOT EXISTS (
                        SELECT 1 FROM information_schema.STATISTICS s
                        WHERE s.TABLE_SCHEMA = t.TABLE_SCHEMA
                          AND s.TABLE_NAME  = t.TABLE_NAME
                          AND s.INDEX_NAME  = 'PRIMARY')
                ORDER BY t.TABLE_NAME""",
                (db,),
            )
            no_pk_tables = [r[0] for r in cur.fetchall()]
            if no_pk_tables:
                self.log(
                    f"⚠ {len(no_pk_tables)} 張表沒有 PRIMARY KEY："
                    + "、".join(no_pk_tables)
                )
            t_analyze = time.time() - t0_phase

            # ---------- 核對 ----------
            cur.execute(
                "SELECT ENGINE, COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "GROUP BY ENGINE",
                (db,),
            )
            engine_rows = cur.fetchall()
            engine_summary = ", ".join(f"{e}: {c} 張" for e, c in engine_rows)
            n_myisam = sum(c for e, c in engine_rows if (e or "").upper() == "MYISAM")
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
                (db,),
            )
            n_tables = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'VIEW'",
                (db,),
            )
            n_views = cur.fetchone()[0]
            cur.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (db,),
            )
            db_cs, db_coll = cur.fetchone()

            self._restore_durability(cur, saved_durability)
            saved_durability = None

            t_total = time.time() - t_start

            # ---------- 摘要 ----------
            lines = [
                f"資料庫 `{db}` 還原完成：{total} 個檔案全部匯入成功，"
                f"共 {n_tables} 張資料表"
                + (f"、{n_views} 個檢視表。" if n_views else "。"),
                f"引擎分佈：{engine_summary}；字元集：{db_cs} / {db_coll}。",
                f"耗時：總計 {fmt_secs(t_total)}"
                f"（匯入 {fmt_secs(t_import)}、"
                f"無損檢查 {fmt_secs(t_check)}、"
                f"ALTER 轉換 {fmt_secs(t_alter)}、"
                f"統計更新 {fmt_secs(t_analyze)}）。",
            ]
            if normalized:
                lines.append(
                    f"{len(normalized)} 個欄位的同義異碼符號已正規化"
                    f"（字義不變）：" + "、".join(normalized)
                )

            ok = True

            # 有損取代放在最前面。這是整份摘要裡唯一「資料被永久改掉」的
            # 事情，不能埋在耗時統計後面。
            if forced:
                lines.insert(
                    0,
                    f"⚠ {len(forced)} 個欄位含無法轉換的字元，已取代為"
                    f" '{LOSSY_MARKER}'："
                    + "、".join(forced)
                    + (
                        f"\n　原始位元組存證：{evidence_path}"
                        if evidence_path
                        else "\n　⚠ 存證檔寫入失敗，請立即從備份檔重新確認這些資料。"
                    )
                    + f"\n　這些字在資料庫內已無法復原。可用"
                    f" LIKE '%{LOSSY_MARKER}%' 撈出來人工補正；"
                    "若是病患姓名，請優先處理（會影響健保申報與 IC 卡對照）。",
                )
                if marker_skipped:
                    lines.insert(
                        1,
                        f"　（其中 {len(marker_skipped)} 個欄位無法標記，"
                        f"仍為 '{LOSSY_PLACEHOLDER}'："
                        + "、".join(marker_skipped)
                        + "）",
                    )

            # 還原結果仍含 MyISAM：多半來自轉換前產生的舊備份檔。
            # 這是靜默的退步，一定要讓使用者看到。
            if n_myisam:
                lines.append(
                    f"⚠ 還原結果仍有 {n_myisam} 張 MyISAM 資料表"
                    + ("（來自轉換前產生的舊備份檔）。" if follow_file_engine else "。")
                    + "MyISAM 沒有交易與 crash safety，"
                    "請在「資料引擎」選 InnoDB 重新執行，"
                    "或還原後手動 ALTER TABLE ... ENGINE=InnoDB。"
                )
                ok = False

            if no_pk_tables:
                lines.append(
                    f"提醒：{len(no_pk_tables)} 張表沒有 PRIMARY KEY，"
                    f"InnoDB 會自建隱藏 rowid，效能較差，建議補上："
                    + "、".join(no_pk_tables)
                )

            if analyze_failed:
                lines.append(
                    f"注意：{len(analyze_failed)} 張表統計更新失敗"
                    f"（不影響資料正確性，可日後手動 ANALYZE TABLE）："
                    + "、".join(analyze_failed)
                )

            if alter_failed:
                lines.append(
                    f"注意：{len(alter_failed)} 項變更失敗（該表維持原狀，"
                    f"資料完整）："
                    + "、".join(f"{t}（{n}）" for t, n, _ in alter_failed)
                )
                ok = False

            if GRANTS_FILE in os.listdir(p["sql_folder"]):
                lines.append(
                    f"備份中含 {GRANTS_FILE}（使用者權限，全為註解未匯入）。"
                    f"若這是搬到新主機，請開啟該檔人工建立所需帳號與權限。"
                )

            lines.append("建議抽查主要資料表的筆數（如 cases、patient）確認內容。")

            summary = "\n".join(lines)
            self.log("\n=== 還原結束 ===\n" + summary)
            self.sig_finished.emit(ok, summary)

        except Exception as e:
            self.log(f"\n⚠ 已停止：{e}")
            if cur is not None and saved_durability:
                self._restore_durability(cur, saved_durability)
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


class SqlRestoreWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SQL 備份還原工具")
        self.resize(620, 660)
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
        self.charset_combo.setCurrentText("utf8mb4")
        self.charset_combo.setToolTip(
            "須與備份檔匯出時的編碼一致。\n"
            "新版 backup.py 以 binary 匯出（不轉碼、原樣保留位元組），\n"
            "選 binary 或維持「自動偵測」即可；\n"
            "目標資料庫的預設字元集會另從 00_schema.sql 取得。"
        )
        eng_label = QLabel("資料引擎:")
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(ENGINE_CHOICES)
        self.engine_combo.setCurrentText("InnoDB")
        self.engine_combo.setToolTip(
            "備份檔的 CREATE TABLE 已帶 ENGINE=xxx。\n"
            "選「依備份檔」表示照原樣還原（建議）。\n"
            "選 MyISAM/InnoDB 會在還原後強制轉換，"
            "每張表都要重建一次，非常耗時。"
        )
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

        # 有損資料的處理策略
        lossy_row = QHBoxLayout()
        lossy_label = QLabel("有損資料:")
        lossy_label.setFixedWidth(90)
        self.lossy_combo = QComboBox()
        self.lossy_combo.addItems(LOSSY_CHOICES)
        self.lossy_combo.setCurrentText(LOSSY_AUTO)
        self.lossy_combo.setToolTip(
            f"遇到無法無損轉換為 utf8mb4 的資料時怎麼辦。\n\n"
            f"自動：{LOSSY_AUTO_LIMIT} 筆以內視為個案（造字、截斷的半個字），\n"
            f"　　　直接取代為 '{LOSSY_MARKER}' 並繼續；超過則停止。\n"
            f"停止：一律停止，交由人工判斷。\n"
            f"強制：不論多少筆一律取代——請先確認「備份檔編碼」沒選錯。\n\n"
            f"取代前會把原始位元組寫成 charset_lossy_*.tsv 存證，\n"
            f"但資料庫裡的原始資料無法復原。"
        )
        lossy_row.addWidget(lossy_label)
        lossy_row.addWidget(self.lossy_combo)
        layout.addLayout(lossy_row)

        self.durability_checkbox = QCheckBox(
            "還原期間暫時放寬 InnoDB 持久性設定以加速（需 SUPER 權限，結束後自動還原）"
        )
        self.durability_checkbox.setChecked(True)
        self.durability_checkbox.setToolTip(
            "暫時設定 innodb_flush_log_at_trx_commit=2、sync_binlog=0。\n"
            "還原期間若主機斷電，最多損失最後 1 秒的寫入——\n"
            "但反正還原失敗就重跑，因此對這個用途是安全的。\n"
            "注意：這是全域設定，會影響同一台伺服器上的其他資料庫，\n"
            "請勿在正式營運時段對線上主機使用。"
        )
        layout.addWidget(self.durability_checkbox)

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

        table_files, last_files, info_files = split_sql_files(folder)
        n_sql = len(table_files) + len(last_files)
        if n_sql == 0:
            QMessageBox.warning(self, "提示", "指定目錄中沒有任何可匯入的 .sql 檔案。")
            return

        # 目標資料庫若已含資料表，開始前明確警告覆蓋風險
        try:
            probe = mysql.connector.connect(
                host=self.host_input.text().strip(),
                port=port,
                user=self.user_input.text().strip(),
                password=self.password_input.text(),
                charset="utf8mb4",
                # 一定要明確指定 collation。mysql-connector-python 內建一張
                # charset → collation 對照表，utf8mb4 會對到 MySQL 8 的預設值
                # utf8mb4_0900_ai_ci；MariaDB 沒有這個 collation，連線當下就會
                # 拋 1273 Unknown collation，連第一次查詢都到不了。
                collation="utf8mb4_general_ci",
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

        # 備份完整性：比對 backup.py 產生的 00_manifest.txt。
        # 檔案缺漏、被截斷、或備份當下就已標記 FAIL，都在這裡先攔下來。
        manifest_problems = verify_against_manifest(folder)
        if manifest_problems:
            preview = "\n".join(f"　{item}" for item in manifest_problems[:8])
            if len(manifest_problems) > 8:
                preview += f"\n　…等共 {len(manifest_problems)} 項"
            warn += (
                f"\n\n⚠ 備份檔與 {MANIFEST_FILE} 不符（{len(manifest_problems)} 項）：\n"
                f"{preview}\n"
                f"這份備份可能不完整，還原後請務必核對資料筆數。"
            )

        engine_choice = self.engine_combo.currentText()
        if engine_choice != ENGINE_FOLLOW_FILE:
            warn += (
                f"\n\n⚠ 你選擇了強制轉換引擎為 {engine_choice}。"
                f"與備份檔不符的每張表都會被重建一次，會明顯拖慢還原。"
                f"若只是要照原樣還原，請改選「{ENGINE_FOLLOW_FILE}」。"
            )

        # 備份檔宣告的引擎。轉換前產生的舊備份仍寫著 ENGINE=MyISAM，
        # 「依備份檔」會照原樣還原成 MyISAM——必須在開始前就講清楚，
        # 而不是等跑完才在摘要裡發現。
        dump_engines, dump_myisam = scan_dump_engines(folder, table_files)
        engine_note = ""
        if dump_engines:
            engine_note = "、".join(
                f"{e} {c} 張" for e, c in sorted(dump_engines.items())
            )
        if dump_myisam and engine_choice == ENGINE_FOLLOW_FILE:
            preview = "、".join(dump_myisam[:5])
            if len(dump_myisam) > 5:
                preview += f" 等 {len(dump_myisam)} 個檔案"
            warn += (
                f"\n\n⚠ 備份檔中有 {len(dump_myisam)} 個檔案宣告 "
                f"ENGINE=MyISAM（{preview}），"
                f"多半是轉換為 InnoDB 之前產生的舊備份。\n"
                f"目前選「{ENGINE_FOLLOW_FILE}」會照原樣還原成 MyISAM，"
                f"失去交易與 crash safety。\n"
                f"若要一次到位，請將「資料引擎」改選 InnoDB。"
            )
        elif dump_myisam and engine_choice == "MyISAM":
            warn += (
                "\n\n⚠ 你選擇了 MyISAM。MyISAM 沒有交易與 crash safety，"
                "不建議用於正式資料。"
            )

        to_utf8mb4 = self.utf8mb4_checkbox.isChecked()
        lossy_mode = self.lossy_combo.currentText()

        if to_utf8mb4 and lossy_mode == LOSSY_FORCE:
            warn += (
                f"\n\n⚠ 有損資料設為「強制取代」。無法轉換的字會全部變成 "
                f"'{LOSSY_MARKER}'，不論多少筆，資料庫內無法復原。\n"
                f"若筆數異常地多，通常是「備份檔編碼」選錯了——"
                f"請先確認編碼，不要用強制取代蓋過去。"
            )
        elif to_utf8mb4 and lossy_mode == LOSSY_AUTO:
            warn += (
                f"\n\n· 有損資料設為「自動」：{LOSSY_AUTO_LIMIT} 筆以內會直接取代為 "
                f"'{LOSSY_MARKER}' 並繼續（原始位元組另存 tsv），"
                f"超過則停止讓你判斷。"
            )

        # 非資料表檔案的處理方式，讓使用者一眼看到，不必猜
        object_note = ""
        if last_files:
            object_note += f"\n物件檔案（排在資料表之後匯入）：{'、'.join(last_files)}"
        if info_files:
            object_note += f"\n參考檔案（只讀取不匯入）：{'、'.join(info_files)}"
        if GRANTS_FILE in os.listdir(folder):
            object_note += f"\n權限檔案（全為註解，不匯入）：{GRANTS_FILE}"

        answer = QMessageBox.question(
            self,
            "還原前確認",
            f"將從目錄匯入 {len(table_files)} 個資料表檔案到資料庫「{database}」。"
            + object_note
            + f"\n備份檔編碼：{self.charset_combo.currentText()}"
            f"（須與備份檔匯出時的編碼一致）\n"
            f"資料引擎：{engine_choice}"
            + (f"（備份檔宣告：{engine_note}）\n" if engine_note else "\n")
            + f"轉換為 utf8mb4：{'是（含無損檢查）' if to_utf8mb4 else '否'}"
            + (f"\n有損資料：{lossy_mode}" if to_utf8mb4 else "")
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
            "engine": engine_choice,
            "to_utf8mb4": to_utf8mb4,
            "lossy_mode": lossy_mode,
            "relax_durability": self.durability_checkbox.isChecked(),
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
