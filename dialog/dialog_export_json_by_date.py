import os

from PyQt5 import QtCore, QtWidgets


class DialogExportJsonByDate(QtWidgets.QDialog):
    def __init__(self, parent=None, start_date=None, end_date=None, default_dir=None):
        super().__init__(parent)
        self.setWindowTitle("依日期匯出JSON病歷資料")
        self.setMinimumWidth(560)

        today = QtCore.QDate.currentDate()
        self._default_dir = default_dir or os.path.expanduser("~")
        self._path_edited = False  # 使用者手動改過路徑就不再自動覆蓋

        self.dateEdit_start = QtWidgets.QDateEdit(start_date or today)
        self.dateEdit_end = QtWidgets.QDateEdit(end_date or today)
        for date_edit in (self.dateEdit_start, self.dateEdit_end):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")

        self.lineEdit_file = QtWidgets.QLineEdit()
        self.toolButton_browse = QtWidgets.QToolButton()
        self.toolButton_browse.setText("...")

        file_layout = QtWidgets.QHBoxLayout()
        file_layout.addWidget(self.lineEdit_file)
        file_layout.addWidget(self.toolButton_browse)

        form = QtWidgets.QFormLayout()
        form.addRow("開始日期", self.dateEdit_start)
        form.addRow("結束日期", self.dateEdit_end)
        form.addRow("匯出檔案", file_layout)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("匯出")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttonBox)

        self.dateEdit_start.dateChanged.connect(self._update_default_file_name)
        self.dateEdit_end.dateChanged.connect(self._update_default_file_name)
        self.lineEdit_file.textEdited.connect(self._on_path_edited)
        self.toolButton_browse.clicked.connect(self._browse_file)
        self.buttonBox.accepted.connect(self._accept)
        self.buttonBox.rejected.connect(self.reject)

        self.checkBox_mask = QtWidgets.QCheckBox(
            "遮蔽個人資料 (姓名、身分證號、電話、地址...)"
        )
        self.checkBox_mask.setChecked(True)  # 預設遮蔽
        form.addRow("", self.checkBox_mask)

        self._update_default_file_name()

    def mask_sensitive(self):
        return self.checkBox_mask.isChecked()

    def _default_file_name(self):
        return f"{self.start_date()}至{self.end_date()}病歷資料.json"

    def _update_default_file_name(self):
        if self._path_edited:
            return

        # 保留目前選定的目錄, 只換檔名
        current = self.lineEdit_file.text().strip()
        directory = os.path.dirname(current) if current else self._default_dir
        self.lineEdit_file.setText(os.path.join(directory, self._default_file_name()))

    def _on_path_edited(self, _text):
        self._path_edited = True

    def _browse_file(self):
        current = self.lineEdit_file.text().strip() or os.path.join(
            self._default_dir, self._default_file_name()
        )
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "匯出JSON檔案", current, "json檔案 (*.json)"
        )
        if not file_name:
            return

        if not file_name.lower().endswith(".json"):
            file_name += ".json"

        self.lineEdit_file.setText(file_name)
        # 檔名仍是預設格式時, 日期變動照樣自動更新檔名
        self._path_edited = os.path.basename(file_name) != self._default_file_name()

    def _accept(self):
        if self.dateEdit_start.date() > self.dateEdit_end.date():
            QtWidgets.QMessageBox.warning(self, "日期錯誤", "開始日期不可大於結束日期.")
            return

        file_name = self.file_name()
        if not file_name:
            QtWidgets.QMessageBox.warning(self, "檔案錯誤", "請指定匯出檔案名稱.")
            return

        directory = os.path.dirname(file_name)
        if directory and not os.path.isdir(directory):
            QtWidgets.QMessageBox.warning(self, "路徑錯誤", f"目錄不存在:\n{directory}")
            return

        # 手打路徑時 QFileDialog 不會問覆蓋, 這裡補問
        if os.path.exists(file_name):
            reply = QtWidgets.QMessageBox.question(
                self,
                "檔案已存在",
                f"{file_name}\n已存在, 是否覆蓋?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        self.accept()

    def start_date(self):
        return self.dateEdit_start.date().toString("yyyy-MM-dd")

    def end_date(self):
        return self.dateEdit_end.date().toString("yyyy-MM-dd")

    def file_name(self):
        file_name = self.lineEdit_file.text().strip()
        if file_name and not file_name.lower().endswith(".json"):
            file_name += ".json"
        return file_name
