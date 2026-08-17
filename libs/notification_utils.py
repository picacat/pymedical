# -*- coding: UTF-8 -*-
"""
站台間訊息通知 —— 以資料庫 notification 表取代 UDP broadcast

架構對應
--------
    udp_socket_client  →  NotificationClient   （20 幾支程式，只發送）
    udp_socket_server  →  NotificationServer   （只有 pymedical，接收）

    UDPSocketServer (8881) → CHANNEL_WAITING_LIST  （原 CSV 格式不變）
    VoiceServer     (9991) → CHANNEL_CALL_NUMBER   （原 JSON 格式不變）

發送端沒有 timer、沒有游標、沒有 socket、沒有生命週期，就只是一句
INSERT。20 幾支程式各建一個實例的總成本趨近於零。

接收端不再是 QThread，改用 QTimer 在主執行緒輪詢，因此：
  * 關閉程式時不會卡在 recvfrom 等封包
  * update_signal 直接在主執行緒發出，不需要跨執行緒佇列
  * 不再需要 socket 重建、port 佔用、防火牆白名單

設計要點
--------
  * 啟動時從 MAX(NotificationKey) 開始，不回放歷史。
    重要：select_record() 在連線失敗時回傳 []，與「空資料表」無法從
    回傳值區分。若把失敗當成 0，第一次連上時會把整張表當作新訊息全部
    重播一次——候診名單靠合併還撐得住，但叫號語音會把保留期內的號碼
    全部念一遍。因此 last_key 用 None 表示「尚未初始化」。
  * 失效通知類的 channel 會自動合併，避免站台卡住後補撈造成連環觸發。
    叫號絕對不合併——每一則都是不同的病人。
  * 過期訊息在讀取端過濾，不靠刪除。刪除會跟讀取端賽跑，過濾不會。
  * 交易進行中不輪詢（database 是單一連線）。
  * 連線失敗時自動退避，避免每秒重連洗版。
"""

from PyQt5 import QtCore

# ---- Channel 定義：只表示「發生了什麼事」，發送者身分放 Source ----
CHANNEL_WAITING_LIST = "waiting_list"  # 候診名單變更（掛號、看診、批價、藥局）
CHANNEL_CALL_NUMBER = "call_number"  # 叫號語音播報（JSON，含 sentence）
CHANNEL_BULLETIN = "bulletin"  # 候診看板重讀（原 UDP 9991 的 refresh_wait）
CHANNEL_SYSTEM = "system"  # 系統公告、更新通知

# 「失效通知」類 channel：補撈到多則時只處理最新一則。
# 語意上等價，因為接收端收到後本來就是自己回資料庫查現況。
#
# CHANNEL_CALL_NUMBER 絕對不能放進來 —— 每一則都是不同的病人，
# 合併會導致中間的號碼被跳過不播。
COALESCE_CHANNELS = frozenset([CHANNEL_WAITING_LIST, CHANNEL_BULLETIN])

# 各 channel 的時效上限（秒）。超過就直接丟棄，不送到接收端。
# 沒列在這裡的 channel 不設限。
#
#   call_number  : 播報五分鐘前的叫號是錯的，設 60 秒
#   waiting_list : 不設限。它是失效通知，處理方式是「回頭查現在的名單」，
#                  不管多舊，處理結果永遠正確
#   bulletin     : 同上，refresh_wait 是失效通知，不設限
MAX_AGE_SECONDS = {
    CHANNEL_CALL_NUMBER: 60,
}

DEFAULT_INTERVAL = 500  # 輪詢間隔（毫秒）
FAILURE_INTERVAL = 5000  # 連續失敗後的退避間隔（毫秒）
FAILURE_THRESHOLD = 3  # 連續失敗幾次才退避
# 連續幾次沒收到訊息就檢查一次編號有沒有倒退（AUTO_INCREMENT 歸零）。
# 500ms × 120 約一分鐘一次，成本是一次索引查找。
RESYNC_CHECK_POLLS = 120


# 保留天數。錨定在午夜而非滾動視窗，對齊診所的一天，也比較好推理。
#   0 = 只保留今天（刪除今天 00:00 之前的所有通知）
#   1 = 保留今天和昨天
#
# 這個值的下限不是「資料的價值期」，而是「最慢的讀取端可能停多久」。
# 0 是安全的：被刪的都是昨天以前的列，要漏訊息的話，該站台得從昨天就
# 卡住不動且中間沒人重開——那台早就不能用了，重開時 _max_key() 會重新
# 對齊。（游標是數字不是列的參照，指向的列被刪掉不影響比較。）
PURGE_KEEP_DAYS = 0
PURGE_BATCH_SIZE = 1000
PURGE_MAX_BATCHES = 500  # 迴圈上限，防止異常情況下無限跑


def _log(message):
    """永不拋例外的訊息輸出。

    Windows 上以 pythonw.exe 執行時 sys.stdout 是 None，print() 會拋
    AttributeError。本模組的訊息輸出有多處寫在 except 區塊裡，print
    自己炸掉就會往外傳到業務流程，違反「通知失敗不影響本業」的前提。
    """
    try:
        print(message)
    except Exception:
        pass


# 字元集優先序：能存中文、且該伺服器版本支援的第一個。
#   utf8mb4  MySQL 5.5.3+ / MariaDB 全部
#   utf8     MySQL 4.1+（utf8mb3），5.0/5.1 的唯一選擇
#   big5     極舊環境的最後手段
CHARSET_CANDIDATES = (
    ("utf8mb4", "utf8mb4_general_ci"),
    ("utf8", "utf8_general_ci"),
    ("big5", "big5_chinese_ci"),
)

# 這些字元集存不了中文，資料表若是這些就自動轉換
UNUSABLE_CHARSETS = ("latin1", "ascii", "latin2", "swe7", "hp8", "dec8")


def _table_exists(database):
    return bool(database.select_record("SHOW TABLES LIKE 'notification'"))


def _pick_charset_clause(database):
    """依伺服器實際支援挑字元集。

    不能寫死：utf8mb4 在 MySQL 5.0/5.1 不存在，寫死會讓建表整個失敗。
    也不能不指定：會繼承資料庫預設，舊客戶端常是 latin1，存不了中文。
    """
    for charset, collation in CHARSET_CANDIDATES:
        try:
            rows = database.select_record(f"SHOW CHARACTER SET LIKE '{charset}'")
        except Exception:
            continue
        if rows:
            return f" DEFAULT CHARSET={charset} COLLATE={collation}", charset

    return "", None  # 都查不到就交給伺服器預設


def _current_charset(database):
    try:
        rows = database.select_record(
            "SELECT TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification'"
        )
    except Exception:
        return None
    if not rows:
        return None
    collation = rows[0].get("TABLE_COLLATION")
    return str(collation).split("_")[0] if collation else None


def ensure_table(database):
    """確保 notification 資料表存在且字元集能存中文。

    刻意不透過 check_system_db() / create_table() 建表，因為那條路徑
    沒辦法依伺服器版本挑字元集：
      * .sql 寫死 utf8mb4 → MySQL 5.0/5.1 不支援，建表失敗
      * .sql 不寫字元集   → 繼承資料庫預設，latin1 舊庫存不了中文
      * 交給 create_table() 附加 → 產生不存在的 big5_general_ci

    開機時呼叫一次即可，冪等，失敗只回傳 False 不拋例外。

    Returns:
        bool: 資料表是否可用
    """
    try:
        if _table_exists(database):
            charset = _current_charset(database)
            if charset in UNUSABLE_CHARSETS:
                clause, target = _pick_charset_clause(database)
                if target:
                    _log(
                        f"（notification 字元集為 {charset}，存不了中文，"
                        f"自動轉為 {target}）"
                    )
                    database.exec_sql(
                        f"ALTER TABLE notification CONVERT TO CHARACTER SET {target}"
                    )
            return True

        charset_clause, _ = _pick_charset_clause(database)
        engine = getattr(database, "engine", None)
        engine_clause = f" ENGINE={engine}" if engine else ""

        database.exec_sql(
            "CREATE TABLE IF NOT EXISTS notification ("
            " NotificationKey BIGINT NOT NULL AUTO_INCREMENT,"
            " Channel VARCHAR(32) NOT NULL DEFAULT '',"
            " Source VARCHAR(64) NOT NULL DEFAULT '',"
            " Message TEXT,"
            " CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
            " PRIMARY KEY (NotificationKey),"
            " KEY idx_created (CreatedAt)"
            ")" + engine_clause + charset_clause
        )
        ok = _table_exists(database)
        _log(
            f"（notification 資料表已建立{charset_clause}）"
            if ok
            else "（notification 資料表建立失敗）"
        )
        return ok
    except Exception as e:
        _log(f"（notification 資料表檢查失敗：{e}）")
        return False


def purge_old_records(database, keep_days=PURGE_KEEP_DAYS):
    """清理舊通知。開機時呼叫一次即可。

    做成模組層級的函式，這樣不依賴 NotificationServer 物件是否建立成功，
    也方便直接放進 pymedical 現有的 reset_wait() 一起做。

    分批刪除，避免第一次執行時單一交易刪掉大量資料。
    MySQLDatabase 沒有取得 affected rows 的方法（exec_sql 回傳的是
    lastrowid），所以改用 idx_created 做一次 LIMIT 1 的存在性查詢判斷
    是否還有殘留——成本等同一次索引查找。

    本函式是冪等的，多台站台各自呼叫也不會出錯。

    Args:
        database: MySQLDatabase 實例
        keep_days (int): 0 = 只保留今天；1 = 保留今天和昨天，以此類推

    Returns:
        int: 實際執行的批次數。0 代表沒有東西需要清理。
    """
    # 先取得目前最大編號，清理時一定保留這一列。
    #
    # 若把資料表清空，AUTO_INCREMENT 會歸零 —— MyISAM 立即發生，InnoDB 在
    # 伺服器重啟後重算 MAX+1 也一樣。新訊息的編號就會小於仍在運行的站台
    # 手上的游標（WHERE NotificationKey > 500 對上編號 1），那台從此收不到
    # 任何訊息，而且不會有任何錯誤。診所電腦不關機，這一定會踩到。
    batches = 0
    try:
        rows = database.select_record(
            "SELECT MAX(NotificationKey) AS MaxKey FROM notification"
        )
        if not rows:
            return 0  # 查詢失敗

        max_key = rows[0]["MaxKey"]
        if max_key is None:
            return 0  # 空資料表，沒東西可清

        if keep_days <= 0:
            condition = "CreatedAt < CURDATE() AND NotificationKey < %s"
            params = (max_key,)
        else:
            condition = (
                "CreatedAt < CURDATE() - INTERVAL %s DAY AND NotificationKey < %s"
            )
            params = (keep_days, max_key)

        for _ in range(PURGE_MAX_BATCHES):
            rows = database.select_record(
                "SELECT NotificationKey FROM notification "
                "WHERE " + condition + " LIMIT 1",
                params,
            )
            if not rows:
                break

            database.exec_sql(
                "DELETE FROM notification WHERE "
                + condition
                + f" LIMIT {PURGE_BATCH_SIZE}",
                params,
            )
            batches += 1
    except Exception as e:
        # 清理失敗不能擋住系統啟動
        _log(f"（通知清理失敗：{e}）")

    return batches


# ======================================================================
# 發送端 —— 取代 udp_socket_client
# ======================================================================
class NotificationClient(QtCore.QObject):
    """只負責發送。沒有 timer、沒有狀態，20 幾支程式各建一個都無所謂。

    用法：
        self.socket_client = NotificationClient(
            self, database=self.database, station=self.program_name,
        )
        self.socket_client.send_data(message)        # 呼叫端可以完全不動
    """

    def __init__(self, parent=None, database=None, station=""):
        super().__init__(parent)
        self.database = database
        self.station = station

    def connected(self):
        """相容舊介面。通知能不能送出，取決於資料庫連線。"""
        try:
            return self.database is not None and self.database.connected()
        except Exception:
            return False

    def broadcast(self, channel, message=""):
        """發送通知。message 只描述「什麼變了」，不要塞資料內容。

        若在 database.transaction() 區塊內呼叫，這筆 INSERT 會跟著該交易
        一起提交或回滾——資料與通知天然同步，這正是 Transactional Outbox
        模式想要的效果。UDP 做不到這件事。
        """
        try:
            self.database.exec_sql(
                "INSERT INTO notification (Channel, Source, Message) "
                "VALUES (%s, %s, %s)",
                (channel, self.station, message),
            )
        except Exception as e:
            # 通知失敗不能拖垮業務流程，但要留下痕跡
            _log(f"（通知發送失敗 channel={channel}：{e}）")

    def send_data(self, message, channel=CHANNEL_WAITING_LIST):
        """相容舊 udp_socket_client.send_data()，呼叫端一行都不用改"""
        self.broadcast(channel, message)

    def close(self):
        """相容舊 udp_socket_client.close()。

        發送端沒有 socket、沒有 timer、不持有 database 的生命週期，
        所以這裡沒有東西需要釋放。保留這個方法純粹是為了讓呼叫端的
        close_all() 不用改。
        """


# ======================================================================
# 接收端 —— 取代 udp_socket_server（只有 pymedical 需要）
# ======================================================================
class NotificationServer(NotificationClient):
    """輪詢接收，同時也能發送（繼承自 NotificationClient）。

    ⚠️ 必須把實例存成物件的屬性，並把 parent 傳進去。

        # 錯誤：函式結束後物件被回收，timer 跟著消失，
        #       不會有任何錯誤訊息，就是完全收不到訊息
        def _set_notification_server(self):
            srv = NotificationServer(None, database=self.database, ...)
            srv.update_signal.connect(...)

        # 正確
        def _set_notification_server(self):
            self.notification_server = NotificationServer(
                self, database=self.database, ...)
            self.notification_server.update_signal.connect(...)

    用法：
        self.socket_server = NotificationServer(
            self,
            database=self.database,
            station=self.program_name,
            channels=[CHANNEL_WAITING_LIST, CHANNEL_CALL_NUMBER],
        )
        self.socket_server.update_signal.connect(self._on_notification)

        def _on_notification(self, channel, message):
            if channel == CHANNEL_WAITING_LIST:
                self._refresh_waiting_data(message)
            elif channel == CHANNEL_CALL_NUMBER:
                self._broadcast_speech(message)
    """

    update_signal = QtCore.pyqtSignal(str, str)  # channel, message

    def __init__(
        self,
        parent=None,
        database=None,
        station="",
        channels=None,
        interval=DEFAULT_INTERVAL,
        coalesce_channels=None,
        max_age_seconds=None,
        handler=None,
    ):
        super().__init__(parent, database=database, station=station)

        # 建議用 handler 而不是 update_signal，見 _deliver() 的說明
        self.handler = handler

        self.channels = list(channels) if channels else []  # 空清單 = 全收
        self.coalesce_channels = (
            frozenset(coalesce_channels)
            if coalesce_channels is not None
            else COALESCE_CHANNELS
        )
        self.max_age_seconds = (
            dict(max_age_seconds)
            if max_age_seconds is not None
            else dict(MAX_AGE_SECONDS)
        )

        self.interval = interval
        self.last_key = None  # None = 尚未初始化，見模組說明
        self._polling = False
        self._fail_count = 0
        self._idle_polls = 0

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(interval)

    # ------------------------------------------------------------------
    # 接收
    # ------------------------------------------------------------------
    def _max_key(self):
        """取得目前最大編號。

        Returns:
            int:  成功（空資料表回傳 0）
            None: 查詢失敗，呼叫端必須維持未初始化狀態並稍後重試
        """
        try:
            rows = self.database.select_record(
                "SELECT MAX(NotificationKey) AS MaxKey FROM notification"
            )
            if not rows:
                # select_record() 失敗時回傳 []。SELECT MAX() 在空資料表
                # 上會回傳一列（MaxKey 為 NULL），[] 一定代表查詢失敗。
                return None
            return rows[0]["MaxKey"] or 0
        except Exception:
            # 連線失敗、回傳結構不如預期（KeyError/TypeError）都在這裡收掉
            return None

    def _fetch_new(self):
        # AgeSeconds 一律在伺服器端計算。診所裡各台電腦的系統時間常常
        # 差好幾分鐘，若拿本機時間去減 CreatedAt，時效判斷會完全失準。
        select_clause = (
            "SELECT NotificationKey, Channel, Message, "
            "TIMESTAMPDIFF(SECOND, CreatedAt, NOW()) AS AgeSeconds "
            "FROM notification "
        )
        order_clause = " ORDER BY NotificationKey"

        if self.channels:
            # 佔位符由 channel 數量產生，不含任何外部輸入
            placeholders = ", ".join(["%s"] * len(self.channels))
            where_clause = (
                "WHERE NotificationKey > %s AND Channel IN (" + placeholders + ")"
            )
            params = tuple([self.last_key] + self.channels)
        else:
            where_clause = "WHERE NotificationKey > %s"
            params = (self.last_key,)

        return self.database.select_record(
            select_clause + where_clause + order_clause, params
        )

    def _drop_expired(self, rows):
        """丟棄超過時效的訊息。游標已經前進，所以它們不會再出現。"""
        if not self.max_age_seconds:
            return rows

        result = []
        for row in rows:
            limit = self.max_age_seconds.get(row["Channel"] or "")
            if limit is not None and (row["AgeSeconds"] or 0) > limit:
                continue
            result.append(row)

        return result

    def _coalesce(self, rows):
        """失效通知類的 channel 只保留最新一則，其餘捨棄。

        正常情況每輪 0～1 列，這裡不會有任何作用；只有站台卡住後
        一次補撈多列時才會生效。
        """
        if not self.coalesce_channels:
            return rows

        newest = {}
        for index, row in enumerate(rows):
            channel = row["Channel"] or ""
            if channel in self.coalesce_channels:
                newest[channel] = index

        result = []
        for index, row in enumerate(rows):
            channel = row["Channel"] or ""
            if channel in self.coalesce_channels and newest[channel] != index:
                continue  # 同 channel 後面還有更新的，跳過
            result.append(row)

        return result

    def _resync_if_counter_reset(self):
        """偵測 AUTO_INCREMENT 歸零並重新對齊游標。

        purge 已經會保留最後一列來避免這件事，這裡是第二層保險：
        TRUNCATE、還原備份、手動清表都會讓編號從 1 重新開始，此時游標
        永遠大於新編號，站台會安靜地再也收不到訊息。
        """
        max_key = self._max_key()
        if max_key is None:
            return  # 查詢失敗，下次再說

        if max_key < self.last_key:
            print(
                f"（notification 編號倒退：游標 {self.last_key} → "
                f"資料表最大 {max_key}，重新對齊）"
            )
            self.last_key = max_key

    def _set_timer_interval(self, interval):
        """QTimer 操作一律包起來：物件若已被 C++ 端銷毀會拋 RuntimeError"""
        try:
            self.timer.setInterval(interval)
        except Exception:
            pass

    def _deliver(self, channel, message):
        """把訊息交給接收端。

        ⚠️ 優先使用 handler。PyQt5 自 5.5 起，對「從 C++ 呼叫的 Python
        程式碼中逃出的例外」會呼叫 qFatal() 直接中止整個程序 ——
        emit() 外面包 try/except 完全攔不到（實測確認）。只有事先安裝
        sys.excepthook 才能避免 abort。

        handler 是純 Python 呼叫，例外攔得住，處理函式出錯最多就是這一則
        訊息沒處理到，程式繼續跑。

        update_signal 保留給既有呼叫端相容，但若接收端可能拋例外，
        請改用 handler。
        """
        if self.handler is not None:
            try:
                self.handler(channel, message)
            except Exception as e:
                _log(f"（通知處理失敗，已略過此則：{e}）")
            return

        try:
            self.update_signal.emit(channel, message)
        except Exception as e:
            _log(f"（通知 signal 發送失敗：{e}）")

    def _on_failure(self):
        self._fail_count += 1
        if self._fail_count == FAILURE_THRESHOLD:
            self._set_timer_interval(FAILURE_INTERVAL)

    def _on_success(self):
        if self._fail_count:
            self._fail_count = 0
            self._set_timer_interval(self.interval)

    def _poll(self):
        # 防重入：接收端若呼叫 processEvents()，timer 可能在處理途中再次觸發
        if self._polling:
            return

        # 交易進行中不打擾，下一輪再說。
        # getattr 的預設值只擋 AttributeError，property 本身拋別的例外
        # 仍會逃出去，而這一行在主 try 之外，所以要自己包。
        try:
            if getattr(self.database, "in_transaction", False):
                return
        except Exception:
            pass  # 無法判斷交易狀態就照常輪詢

        self._polling = True
        try:
            # 尚未初始化（開機時資料庫還沒起來等等），先補做初始化
            if self.last_key is None:
                self.last_key = self._max_key()
                if self.last_key is None:
                    self._on_failure()
                else:
                    self._on_success()
                return  # 這一輪只做初始化

            rows = self._fetch_new()

            # select_record() 連線失敗時回傳 []，而「沒有新訊息」也是 []，
            # 兩者無法從回傳值區分（_max_key() 可以，因為 SELECT MAX() 一定
            # 會回傳一列）。改用連線狀態判斷：select_record() 內部重試失敗
            # 後 _reconnect() 會把 cnx 設為 None，此時 connected() 為 False。
            # 不這樣做的話退避永遠不會啟動，斷線期間每秒重連一次。
            if not self.database.connected():
                self._on_failure()
                return

            self._on_success()

            if not rows:
                # 閒置一段時間後檢查編號有沒有倒退。正常情況永遠不會觸發；
                # 會觸發代表有人 TRUNCATE、還原了備份、或手動清空資料表，
                # 導致 AUTO_INCREMENT 歸零。
                self._idle_polls += 1
                if self._idle_polls >= RESYNC_CHECK_POLLS:
                    self._idle_polls = 0
                    self._resync_if_counter_reset()
            else:
                self._idle_polls = 0
                self.last_key = rows[-1]["NotificationKey"]
                for row in self._coalesce(self._drop_expired(rows)):
                    self._deliver(row["Channel"] or "", row["Message"] or "")
        except Exception as e:
            # 資料庫暫斷等等：游標不動，下一輪自動補回來
            self._on_failure()
            _log(f"（通知輪詢失敗：{e}）")
        finally:
            self._polling = False

    # ------------------------------------------------------------------
    # 維護
    # ------------------------------------------------------------------
    def purge_old_records(self, keep_days=PURGE_KEEP_DAYS):
        """清理舊通知。委派給模組層級的同名函式，見該處說明。"""
        return purge_old_records(self.database, keep_days)

    # ------------------------------------------------------------------
    # 控制
    # ------------------------------------------------------------------
    def set_interval(self, interval):
        self.interval = interval
        if not self._fail_count:
            self._set_timer_interval(interval)

    def start(self):
        try:
            if not self.timer.isActive():
                self.last_key = None  # 重新啟動時跳過中間累積的訊息
                self.timer.start(self.interval)
        except Exception as e:
            _log(f"（通知輪詢啟動失敗：{e}）")

    def stop(self):
        # 關閉流程中呼叫，絕不可拋例外中斷 closeEvent
        try:
            self.timer.stop()
        except Exception:
            pass

    def stop_thread(self):
        """相容舊 UDPSocketServer.stop_thread()"""
        self.stop()

    def close(self):
        """覆寫發送端的 no-op close()：接收端有 timer，必須真的停掉。"""
        self.stop()
