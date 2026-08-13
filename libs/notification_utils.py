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
CHANNEL_CALL_NUMBER = "call_number"  # 叫號語音播報
CHANNEL_BULLETIN = "bulletin"
CHANNEL_SYSTEM = "system"  # 系統公告、更新通知

# 「失效通知」類 channel：補撈到多則時只處理最新一則。
# 語意上等價，因為接收端收到後本來就是自己回資料庫查現況。
# CHANNEL_CALL_NUMBER 絕對不能放進來 —— 每一則都是不同的病人。
COALESCE_CHANNELS = frozenset([CHANNEL_WAITING_LIST])

# 各 channel 的時效上限（秒）。超過就直接丟棄，不送到接收端。
# 沒列在這裡的 channel 不設限。
#
#   call_number  : 播報五分鐘前的叫號是錯的，設 60 秒
#   waiting_list : 不設限。它是失效通知，處理方式是「回頭查現在的名單」，
#                  不管多舊，處理結果永遠正確
MAX_AGE_SECONDS = {
    CHANNEL_CALL_NUMBER: 60,
}

DEFAULT_INTERVAL = 500  # 輪詢間隔（毫秒）
FAILURE_INTERVAL = 5000  # 連續失敗後的退避間隔（毫秒）
FAILURE_THRESHOLD = 3  # 連續失敗幾次才退避
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
    if keep_days <= 0:
        condition = "CreatedAt < CURDATE()"
        params = ()
    else:
        condition = "CreatedAt < CURDATE() - INTERVAL %s DAY"
        params = (keep_days,)

    batches = 0
    try:
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
        print(f"（通知清理失敗：{e}）")

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
            print(f"（通知發送失敗 channel={channel}：{e}）")

    def send_data(self, message, channel=CHANNEL_WAITING_LIST):
        """相容舊 udp_socket_client.send_data()，呼叫端一行都不用改"""
        self.broadcast(channel, message)


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
    ):
        super().__init__(parent, database=database, station=station)

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
        except Exception:
            return None

        if not rows:
            # select_record() 失敗時回傳 []。SELECT MAX() 在空資料表上
            # 會回傳一列（MaxKey 為 NULL），所以 [] 一定代表查詢失敗。
            return None

        return rows[0]["MaxKey"] or 0

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

    def _on_failure(self):
        self._fail_count += 1
        if self._fail_count == FAILURE_THRESHOLD:
            self.timer.setInterval(FAILURE_INTERVAL)

    def _on_success(self):
        if self._fail_count:
            self._fail_count = 0
            self.timer.setInterval(self.interval)

    def _poll(self):
        # 防重入：接收端若呼叫 processEvents()，timer 可能在處理途中再次觸發
        if self._polling:
            return

        # 交易進行中不打擾，下一輪再說
        if getattr(self.database, "in_transaction", False):
            return

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

            if rows:
                self.last_key = rows[-1]["NotificationKey"]
                for row in self._coalesce(self._drop_expired(rows)):
                    try:
                        self.update_signal.emit(
                            row["Channel"] or "", row["Message"] or ""
                        )
                    except Exception as e:
                        print(f"（通知處理失敗，已略過此則：{e}）")
        except Exception as e:
            # 資料庫暫斷等等：游標不動，下一輪自動補回來
            self._on_failure()
            print(f"（通知輪詢失敗：{e}）")
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
            self.timer.setInterval(interval)

    def start(self):
        if not self.timer.isActive():
            self.last_key = None  # 重新啟動時跳過中間累積的訊息
            self.timer.start(self.interval)

    def stop(self):
        self.timer.stop()

    def stop_thread(self):
        """相容舊 UDPSocketServer.stop_thread()"""
        self.stop()
