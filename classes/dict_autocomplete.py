"""
classes/dict_autocomplete.py
-----------------------------
給既有的 QTextEdit「掛上」自動完成功能（PyQt5 版）。

跟專案裡其他 classes 一樣，搭配 class_utils 的工廠函式使用：

    # class_utils.py
    def get_dict_autocomplete(text_edit, database, clinic_type):
        from classes import dict_autocomplete

        module = importlib.reload(dict_autocomplete)
        object = module.DictAutoComplete(text_edit, database, clinic_type)

        return object

    # medical_record.py（一定要在 _set_signal() 之後才建立，見下方說明）
    self.dict_autocomplete_symptom = class_utils.get_dict_autocomplete(
        self.ui.textEdit_symptom, self.database, "主訴"
    )

DictAutoComplete 不是 QTextEdit 的替代品，而是「附加」在你既有的 QTextEdit 上：
- 一建立就會去資料庫撈 ClinicType = clinic_type 的全部資料放進記憶體快取
- 監聽該 QTextEdit 的 textChanged，輸入文字時即時在記憶體裡過濾、彈出下拉清單
- 同時比對 ClinicName（內容包含）與 InputCode（前綴比對，給快速縮碼輸入用）
- 清單依中文字順序排序（長度優先，再依 Big5 編碼順序，跟舊系統的排序邏輯一致）
- 上下鍵選擇、Enter/Tab 套用、Esc 或找不到符合項目時自動關閉清單

實作上刻意不使用 QCompleter：QCompleter 的 popup 在某些環境下會把上下鍵整個
攔截掉、不透過任何我們攔得到的管道（eventFilter / keyPressEvent 都試過都攔不到），
導致「反白看起來有動，但實際選到的永遠是第一筆」這種難以除錯的問題。
改成自己刻一個 QListWidget 當下拉清單，所有鍵盤事件都經過我們自己接管的
keyPressEvent，狀態完全掌控在自己手上，才能保證可靠。

重要：這個 class 會接管 text_edit.keyPressEvent。如果 text_edit 在別的地方
（例如 medical_record.py 的 _set_signal()）也會設定 keyPressEvent，
請確保 DictAutoComplete 是在那之後才建立，不然我們接管的行為會被蓋掉。
"""

from dataclasses import dataclass

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QListWidget

# ---------------------------------------------------------------------------
# 資料層：負責跟 clinic table 互動
# ---------------------------------------------------------------------------


@dataclass
class ClinicItem:
    clinic_key: int
    clinic_name: str
    input_code: str


class ClinicRepository:
    """
    包一層在你既有的 database 物件外面，集中管理跟 clinic table 有關的 SQL。

        self.database.select_record(sql, params) -> 查詢
            （mysql-connector-python，dictionary=True，所以每筆回傳的是 dict，
             key 是欄位名稱，例如 row["ClinicKey"]）
    """

    def __init__(self, database):
        self.database = database

    def load_by_type(self, clinic_type):
        """一次撈出某個 ClinicType 的全部資料，給建立時呼叫，依中文字順序排序"""
        sql = """
            SELECT ClinicKey, ClinicName, InputCode
            FROM clinic
            WHERE ClinicType = %s AND ClinicName IS NOT NULL
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` USING big5) AS BINARY)
        """
        params = (clinic_type,)
        rows = self.database.select_record(sql, params)

        return [
            ClinicItem(
                clinic_key=row["ClinicKey"],
                clinic_name=row["ClinicName"],
                input_code=row["InputCode"] or "",
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# 記憶體快取：把 ClinicRepository 撈回來的資料包裝成方便查詢的結構
# ---------------------------------------------------------------------------


class ClinicCache:
    def __init__(self, items):
        self._items = items
        # ClinicName 可能重複（理論上不應該，但保險起見用 dict 存第一筆）
        self._by_name = {}
        for item in items:
            self._by_name.setdefault(item.clinic_name, item)

    def search(self, keyword, limit=20):
        if not keyword:
            return []
        kw = keyword.strip().lower()
        matched = [
            item
            for item in self._items
            if item.clinic_name.lower().startswith(kw)
            or (item.input_code and item.input_code.lower().startswith(kw))
        ]
        # 已經依中文字順序預先排序過了（load_by_type 的 ORDER BY），這裡維持原順序即可
        return matched[:limit]

    def get_by_name(self, name):
        return self._by_name.get(name)

    def refresh(self, items):
        """如果之後要支援重新整理快取（例如後台異動後），呼叫這個"""
        self.__init__(items)


# ---------------------------------------------------------------------------
# 控制層：掛載到既有 QTextEdit 上，自己刻下拉清單
# ---------------------------------------------------------------------------


class DictAutoComplete(QObject):
    """
    把自動完成功能掛到一個既有的 QTextEdit 上。

    Args:
        text_edit (QTextEdit): 你已經建立好的 QTextEdit（例如 Qt Designer 產生的）
        database: 你既有的資料庫物件（要有 select_record / update_record 方法）
        clinic_type (str): 要載入的 ClinicType，例如 '主訴'
    """

    def __init__(self, text_edit, database, clinic_type, parent=None):
        super().__init__(parent or text_edit)
        self.text_edit = text_edit
        self._prefix_start_pos = None
        self._min_prefix_pos = None  # 上次套用完成的位置，往前掃描抓詞時碰到這裡就停止
        self._deleting = False  # 這次 textChanged 是不是因為刪字造成的

        self.repo = ClinicRepository(database)
        try:
            items = self.repo.load_by_type(clinic_type)
        except Exception as e:
            print(f"載入 {clinic_type} 關鍵字失敗，將以空清單啟動：{e}")
            items = []
        self.cache = ClinicCache(items)

        # 自己刻的下拉清單視窗：無邊框、不搶焦點，純粹拿來顯示 + 反白，
        # 所有鍵盤操作邏輯都在 DictAutoComplete 自己身上，不靠這個 widget 自己處理按鍵
        self.popup = QListWidget()
        self.popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.popup.setStyleSheet("""
            QListWidget {
                font-size: 18px;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
        """)
        self.popup.itemClicked.connect(self._on_item_clicked)
        self.popup.hide()

        # 文字一有變動（打字、刪除、貼上都算）就重新計算要不要顯示清單
        self.text_edit.textChanged.connect(self._on_text_changed)

        # 直接接管 keyPressEvent（跟專案裡其他地方的做法一致）。
        # 記下目前的 keyPressEvent，讓沒被我們攔截的按鍵可以照樣往下傳
        # （不管它原本是預設的，還是已經被其他程式碼接管過，例如 medical_record.py 的 _text_edit_key_press）。
        self._fallback_key_press_event = self.text_edit.keyPressEvent
        self.text_edit.keyPressEvent = self._key_press_event

        # 焦點離開時自動關閉下拉清單
        self._fallback_focus_out_event = self.text_edit.focusOutEvent
        self.text_edit.focusOutEvent = self._focus_out_event

    def _focus_out_event(self, event):
        self.popup.hide()
        self._fallback_focus_out_event(event)

    def _on_item_clicked(self, list_item):
        self._insert_completion(list_item.text())

    def _key_press_event(self, event):
        key = event.key()

        if self.popup.isVisible():
            # Enter / Tab：套用目前反白的項目，不讓它變成換行或插入 Tab 字元
            if key in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab, Qt.Key_Backtab):
                self._accept_current_completion()
                return

            # Esc：直接關閉清單
            if key == Qt.Key_Escape:
                self.popup.hide()
                return

            # 上下鍵：直接操作我們自己的 QListWidget，完全不假手他人
            if key in (Qt.Key_Up, Qt.Key_Down):
                self._move_selection(key)
                return

        # Backspace / Delete：正常刪字，但標記起來，讓 _on_text_changed 不要因為刪除又跳出清單
        if key == Qt.Key_Backspace:
            self._deleting = True
            # 邊界要跟著刪除動作同步縮小：如果這次刪掉的字還在邊界範圍內（殘留字），
            # 邊界就跟著往前退一格；退到底了（殘留字全刪光）才整個失效
            if self._min_prefix_pos is not None:
                cursor_pos = self.text_edit.textCursor().position()
                if cursor_pos <= self._min_prefix_pos:
                    self._min_prefix_pos -= 1
                    if self._min_prefix_pos < 0:
                        self._min_prefix_pos = None
        elif key == Qt.Key_Delete:
            self._deleting = True

        # 其餘按鍵，照原本的方式處理（可能是預設的 QTextEdit 行為，也可能是別的程式接管過的邏輯）
        self._fallback_key_press_event(event)

    def _move_selection(self, key):
        count = self.popup.count()
        if count == 0:
            return

        row = self.popup.currentRow()
        if row < 0:
            row = 0

        if key == Qt.Key_Down:
            row = min(row + 1, count - 1)
        else:
            row = max(row - 1, 0)

        self.popup.setCurrentRow(row)

    def _accept_current_completion(self):
        item = self.popup.currentItem()
        if item is None:
            self.popup.hide()
            return

        self._insert_completion(item.text())

    def _insert_completion(self, completion):
        cursor = self.text_edit.textCursor()
        if self._prefix_start_pos is not None:
            cursor.setPosition(self._prefix_start_pos)
            cursor.setPosition(
                self.text_edit.textCursor().position(), QTextCursor.KeepAnchor
            )

        insert_pos = (
            cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        )

        # 檢查插入點前一個字元：不是標點符號（也不是文件開頭）才在選字前面補逗號分隔，
        # 避免詞黏在一起，也避免前面已經有標點時重複加逗號
        text_to_insert = completion
        if insert_pos > 0:
            check_cursor = QTextCursor(self.text_edit.document())
            check_cursor.setPosition(insert_pos)
            check_cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
            preceding_char = check_cursor.selectedText()
            if preceding_char and preceding_char not in self._DELIMITERS:
                text_to_insert = ", " + completion

        cursor.insertText(text_to_insert)
        self.text_edit.setTextCursor(cursor)
        self._min_prefix_pos = (
            cursor.position()
        )  # 記下這個位置，之後掃描抓詞不會跨過來黏在一起

        # 套用完成後把清單收起來，避免 insertText 觸發的 textChanged 又把同一筆結果跳出來
        self.popup.hide()

    # 中文沒有空白分詞，改自己往前掃描，遇到空白/標點/換行才停止
    # 回傳 (目前輸入片段, 該片段在文件中的起始位置)
    _DELIMITERS = " \t\n,，。.;；:：、"

    def _get_prefix_and_start(self):
        cursor = self.text_edit.textCursor()
        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()
        text_before_cursor = block_text[:pos_in_block]
        block_start_abs = cursor.position() - pos_in_block

        # 掃描下限：不能跨過上次套用完成的邊界位置，避免跟前一個剛帶入的詞黏在一起
        min_i = 0
        if self._min_prefix_pos is not None:
            candidate = self._min_prefix_pos - block_start_abs
            if 0 <= candidate <= len(text_before_cursor):
                min_i = candidate

        i = len(text_before_cursor)
        while i > min_i and text_before_cursor[i - 1] not in self._DELIMITERS:
            i -= 1

        prefix = text_before_cursor[i:]
        start_pos = cursor.position() - len(prefix)
        return prefix, start_pos

    def _on_text_changed(self):
        if self._deleting:
            self._deleting = False
            self.popup.hide()
            return

        prefix, start_pos = self._get_prefix_and_start()
        self._prefix_start_pos = start_pos

        if len(prefix) < 1:
            self.popup.hide()
            return

        results = self.cache.search(prefix)
        if not results:
            self.popup.hide()
            # 這段前綴確定搜尋不到，把目前位置設成新的邊界，
            # 避免之後繼續打字又跟這段「已知搜尋失敗」的文字黏在一起，永遠比對不到
            self._min_prefix_pos = self.text_edit.textCursor().position()
            return

        if (
            len(results) == 1
            and results[0].clinic_name.lower() == prefix.strip().lower()
        ):
            # 只剩一筆而且完全打完了（不只是開頭符合），不用再跳清單出來選
            # 順便設新邊界，避免之後繼續打字又跟這個已經完成的詞黏在一起
            self.popup.hide()
            self._min_prefix_pos = self.text_edit.textCursor().position()
            return

        self.popup.clear()
        for item in results:
            self.popup.addItem(item.clinic_name)
        self.popup.setCurrentRow(0)

        self._position_popup()
        self.popup.show()

    def _position_popup(self):
        cursor_rect = self.text_edit.cursorRect()
        global_pos = self.text_edit.mapToGlobal(cursor_rect.bottomLeft())

        row_height = self.popup.sizeHintForRow(0) if self.popup.count() > 0 else 24
        visible_rows = min(self.popup.count(), 12)
        height = row_height * visible_rows + 4
        width = max(self.text_edit.width() // 2, 220)

        self.popup.setGeometry(global_pos.x(), global_pos.y(), width, height)
