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

    # ins_prescript_record.py
    self.dict_autocomplete = class_utils.get_dict_autocomplete(
        self.textEdit_main_complaint,  # Qt Designer 裡既有的 QTextEdit
        self.database,
        "主訴",
    )

DictAutoComplete 不是 QTextEdit 的替代品，而是「附加」在你既有的 QTextEdit 上：
- 一建立就會去資料庫撈 ClinicType = clinic_type 的全部資料放進記憶體快取
- 監聽該 QTextEdit 的 textChanged，輸入文字時即時在記憶體裡過濾、彈出下拉清單
- 同時比對 ClinicName（內容包含）與 InputCode（前綴比對，給快速縮碼輸入用）
- 清單依 HitRate 由高到低排序；使用者選擇某筆後，HitRate +1 並回寫資料庫
- 上下鍵選擇、Enter/Tab 套用、Esc 或找不到符合項目時自動關閉清單
  （這部分由 QCompleter 內建處理，不需要額外寫鍵盤事件邏輯）
"""

from dataclasses import dataclass

from PyQt5.QtCore import QEvent, QObject, QStringListModel, Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QCompleter

# ---------------------------------------------------------------------------
# 資料層：負責跟 clinic table 互動
# ---------------------------------------------------------------------------


@dataclass
class ClinicItem:
    clinic_key: int
    clinic_name: str
    input_code: str
    hit_rate: int


class ClinicRepository:
    """
    包一層在你既有的 database 物件外面，集中管理跟 clinic table 有關的 SQL。

        self.database.select_record(sql, params) -> 查詢
            （mysql-connector-python，dictionary=True，所以每筆回傳的是 dict，
             key 是欄位名稱，例如 row["ClinicKey"]）
        self.database.update_record(table_name, fields, primary_key, key_value, data) -> 寫入/更新
    """

    def __init__(self, database):
        self.database = database

    def load_by_type(self, clinic_type):
        """一次撈出某個 ClinicType 的全部資料，給建立時呼叫"""
        sql = """
            SELECT ClinicKey, ClinicName, InputCode, HitRate
            FROM clinic
            WHERE ClinicType = %s AND ClinicName IS NOT NULL
            ORDER BY HitRate DESC, ClinicName ASC
        """
        params = (clinic_type,)
        rows = self.database.select_record(sql, params)

        return [
            ClinicItem(
                clinic_key=row["ClinicKey"],
                clinic_name=row["ClinicName"],
                input_code=row["InputCode"] or "",
                hit_rate=row["HitRate"] or 0,
            )
            for row in rows
        ]

    def bump_hit_rate(self, clinic_key):
        """使用者選用某筆關鍵字後呼叫，累加熱門度（共用既有的 db_utils.increment_hit_rate）"""
        from libs import db_utils

        db_utils.increment_hit_rate(self.database, "clinic", "ClinicKey", clinic_key)


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
            if kw in item.clinic_name.lower()
            or (item.input_code and item.input_code.lower().startswith(kw))
        ]
        # 已經依 HitRate 預先排序過了（load_by_type 的 ORDER BY），這裡維持原順序即可
        return matched[:limit]

    def get_by_name(self, name):
        return self._by_name.get(name)

    def refresh(self, items):
        """如果之後要支援重新整理快取（例如後台異動後），呼叫這個"""
        self.__init__(items)


# ---------------------------------------------------------------------------
# 控制層：掛載到既有 QTextEdit 上
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
        print(
            f"[dict_autocomplete] 建立新的 DictAutoComplete, clinic_type={clinic_type}"
        )  # 暫時除錯用
        super().__init__(parent or text_edit)
        self.text_edit = text_edit
        self._prefix_start_pos = None

        self.repo = ClinicRepository(database)
        try:
            items = self.repo.load_by_type(clinic_type)
        except Exception as e:
            print(f"載入 {clinic_type} 關鍵字失敗，將以空清單啟動：{e}")
            items = []
        self.cache = ClinicCache(items)

        self.completer = QCompleter(self.text_edit)
        self.completer.setModel(QStringListModel([], self.completer))
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        # 過濾邏輯已經在 ClinicCache.search 裡自己做了，這裡關掉 Qt 內建過濾
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.completer.setWidget(self.text_edit)
        self.completer.activated.connect(self._insert_completion)

        # 文字一有變動（打字、刪除、貼上都算）就重新計算要不要顯示清單
        # 上下鍵選擇 / Enter,Tab 套用 / Esc 關閉，這些都是 QCompleter 內建處理，不用自己寫
        self.text_edit.textChanged.connect(self._on_text_changed)

        # 額外處理：popup 顯示時按 Tab 不要插入 Tab 字元
        self.text_edit.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.text_edit and event.type() == QEvent.KeyPress:
            print(
                f"[dict_autocomplete] key={event.key()}, popup_visible={self.completer.popup().isVisible()}"
            )  # 暫時除錯用

        if (
            watched is self.text_edit
            and event.type() == QEvent.KeyPress
            and self.completer.popup().isVisible()
        ):
            key = event.key()

            # Enter / Tab：套用目前反白的項目，並吃掉這個按鍵
            # （不能依賴 QTextEdit 預設行為，否則 Enter 會變成換行）
            if key in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab, Qt.Key_Backtab):
                self._accept_current_completion()
                return True

            # Esc：直接關閉清單，不做其他事
            if key == Qt.Key_Escape:
                self.completer.popup().hide()
                return True

            # Up/Down/PageUp/PageDown 等導覽鍵交給 QCompleter 內建機制轉發給 popup，這裡不處理

        return super().eventFilter(watched, event)

    def _accept_current_completion(self):
        """套用目前在下拉清單中反白的項目"""
        popup = self.completer.popup()
        index = popup.currentIndex()
        if index.isValid():
            completion = index.data()
            self._insert_completion(completion)
        else:
            popup.hide()

    def _insert_completion(self, completion):
        print(
            f"[dict_autocomplete] _insert_completion 被呼叫, completion={completion!r}"
        )  # 暫時除錯用
        cursor = self.text_edit.textCursor()
        if self._prefix_start_pos is not None:
            cursor.setPosition(self._prefix_start_pos)
            cursor.setPosition(
                self.text_edit.textCursor().position(), QTextCursor.KeepAnchor
            )
        cursor.insertText(completion)
        self.text_edit.setTextCursor(cursor)

        # 使用者真的選用了這個關鍵字 -> 累加熱門度（寫回資料庫，並同步更新記憶體快取，方便排序）
        item = self.cache.get_by_name(completion)
        if item:
            try:
                self.repo.bump_hit_rate(item.clinic_key)
                item.hit_rate += 1
            except Exception as e:
                # 累加熱門度失敗不該影響輸入體驗，記錄就好
                print(f"更新 HitRate 失敗: {e}")

        # 套用完成後把清單收起來，避免 insertText 觸發的 textChanged 又把同一筆結果跳出來
        self.completer.popup().hide()

    # 中文沒有空白分詞，QTextCursor.WordUnderCursor 對中文不準，改自己往前掃描
    # 遇到空白/標點/換行才停止，回傳 (目前輸入片段, 該片段在文件中的起始位置)
    _DELIMITERS = " \t\n,，。.;；:：、"

    def _text_under_cursor(self):
        prefix, _ = self._get_prefix_and_start()
        return prefix

    def _get_prefix_and_start(self):
        cursor = self.text_edit.textCursor()
        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()
        text_before_cursor = block_text[:pos_in_block]

        i = len(text_before_cursor)
        while i > 0 and text_before_cursor[i - 1] not in self._DELIMITERS:
            i -= 1

        prefix = text_before_cursor[i:]
        start_pos = cursor.position() - len(prefix)
        return prefix, start_pos

    def _on_text_changed(self):
        prefix, start_pos = self._get_prefix_and_start()
        self._prefix_start_pos = start_pos

        if len(prefix) < 1:
            self.completer.popup().hide()
            return

        results = self.cache.search(prefix)
        if not results:
            self.completer.popup().hide()
            return

        names = [item.clinic_name for item in results]
        self.completer.setCompletionPrefix(prefix)
        self.completer.model().setStringList(names)
        self.completer.popup().setCurrentIndex(
            self.completer.completionModel().index(0, 0)
        )

        rect = self.text_edit.cursorRect()
        rect.setWidth(
            self.completer.popup().sizeHintForColumn(0)
            + self.completer.popup().verticalScrollBar().sizeHint().width()
        )
        self.completer.complete(rect)
