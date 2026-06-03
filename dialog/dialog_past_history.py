# 掛號顯示過去病歷

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint, QSettings, QSize

from libs import (
    case_utils,
    class_utils,
    cshis_utils,
    date_utils,
    dialog_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 掛號過去病歷視窗
class DialogPastHistory(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPastHistory, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.patient = None
        self.medical_record = None

        self.settings = QSettings("__settings.ini", QSettings.IniFormat)

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 關閉
    # def closeEvent(self, a0: QtGui.QCloseEvent):
    #     self.settings.setValue("dialog_history_size", self.size())
    #     self.settings.setValue("dialog_history_pos", self.pos())

    # 關閉
    def done(self, r: int) -> None:
        ui_utils.save_settings(self, "dialog_history")
        super().done(r)

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PAST_HISTORY, self)
        ui_utils.restore_settings(
            self, "dialog_history", QSize(858, 769), QPoint(1054, 225)
        )

        # self.ui.resize(self.settings.value("dialog_history_size", QSize(858, 769)))

        # screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()

        # pos = self.settings.value("dialog_history_pos")
        # if pos is not None and pos.x() < screen_width:
        #     self.ui.move(self.settings.value("dialog_history_pos", QPoint(1054, 225)))

        self.table_widget_past_history = class_utils.get_table_widget(
            self.ui.tableWidget_past_history, self.database
        )
        self.table_widget_past_history.set_column_hidden([0, 1])

        system_utils.set_css(self, self.system_settings)
        # system_utils.center_window(self)  # 不要置中
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("關閉")

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_past_history.doubleClicked.connect(
            self._open_medical_record
        )

    def _open_medical_record(self):
        user_name = system_utils.get_user_name(self.system_settings)
        if (
            personnel_utils.get_permission(
                self.database, "病歷查詢", "調閱病歷", user_name
            )
            != "Y"
        ):
            return

        case_key = self.table_widget_past_history.field_value(0)
        if case_key is None:
            return

        patient_key = self.table_widget_past_history.field_value(1)
        dialog = dialog_utils.get_dialog_medical_record_past_history(
            self, self.database, self.system_settings, case_key, patient_key, "門診掛號"
        )

        dialog.exec_()
        dialog.deleteLater()

    def accepted_button_clicked(self):
        self.close()

    def show_past_history(self, patient_key, ic_card=None):
        self.read_data(patient_key)
        if len(self.medical_record) <= 0:
            return

        name = string_utils.xstr(self.patient["Name"])
        self.ui.groupBox_past_history.setTitle(f"{name}的過去病歷")
        self.ui.groupBox_ic_card.setVisible(False)
        self.show()

        if ic_card is not None:
            self._set_ic_card_treatment_data(ic_card)

    def read_data(self, patient_key):
        sql = f"""
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        """
        self.patient = self.database.select_record(sql)[0]
        massage_condition = ' AND TreatType NOT IN ("民俗調理") '
        if self.system_settings.field("掛號過去病歷顯示民俗調理") == "Y":
            massage_condition = ""

        sql = f"""
            SELECT * FROM cases
            WHERE
                PatientKey = {patient_key}
                {massage_condition}
            ORDER BY CaseDate DESC
            LIMIT 60
        """
        self.medical_record = self.database.select_record(sql)
        self.table_widget_past_history.set_db_data(sql, self._set_table_data)
        self._adjust_column()
        self.ui.tableWidget_past_history.resizeRowsToContents()

    def _adjust_column(self):
        massager_count = personnel_utils.get_person_count(self.database, "推拿師父")
        doctor_count = personnel_utils.get_person_count(self.database, "全部醫師")

        if self.system_settings.field("掛號過去病歷顯示主訴") != "Y":
            self.ui.tableWidget_past_history.setColumnHidden(13, True)

        if massager_count <= 0:
            self.ui.tableWidget_past_history.setColumnHidden(10, True)

        if doctor_count <= 0:
            self.ui.tableWidget_past_history.setColumnHidden(9, True)

    def _set_table_data(self, row_no, row):
        pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])
        if pres_days == 0:
            pres_days = ""

        disease_list = [
            string_utils.xstr(row["DiseaseName1"]),
            string_utils.xstr(row["DiseaseName2"]),
        ]
        symptom = string_utils.get_str(row["Symptom"], "utf8")
        treat_type = string_utils.xstr(row["TreatType"])

        case_date = string_utils.xstr(row["CaseDate"].date())
        if self.system_settings.field("日期格式") == "民國年":
            case_date = date_utils.date_to_zh_tw_date(case_date)

        if string_utils.xstr(row["ApplyType"]) == "不申報":
            case_date += "\n" + "(不申報)"

        past_history_row = [
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["PatientKey"]),
            case_date,
            string_utils.xstr(row["InsType"]),
            string_utils.xstr(row["Share"]),
            treat_type,
            string_utils.xstr(row["Card"]),
            string_utils.int_to_str(row["Continuance"]).strip("0"),
            string_utils.xstr(pres_days),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["Massager"]),
            ", ".join(disease_list),
            string_utils.get_str(row["Remark"], "utf8").replace("\n", ""),
            symptom,
        ]

        for column in range(len(past_history_row)):
            self.ui.tableWidget_past_history.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(past_history_row[column])
            )
            if column in [7, 8]:
                self.ui.tableWidget_past_history.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

            item = self.ui.tableWidget_past_history.item(row_no, column)
            if item is None:
                continue

            if row["InsType"] == "自費":
                item.setForeground(QtGui.QColor("blue"))
            elif "針灸" in treat_type:
                item.setForeground(QtGui.QColor("darkGreen"))
            elif "傷科" in treat_type:
                item.setForeground(QtGui.QColor("darkRed"))

    def _set_ic_card_treatment_data(self, ic_card):
        if self.system_settings.field("使用讀卡機") != "Y":
            self.ui.groupBox_ic_card.setVisible(False)
            return

        if self.system_settings.field("讀取卡片就醫記錄") != "Y":
            self.ui.groupBox_ic_card.setVisible(False)
            return

        self.ui.groupBox_ic_card.setVisible(True)
        try:
            ic_card.read_treatment_no_need_hpc()
        except Exception:
            self.ui.groupBox_ic_card.setVisible(False)
            return

        treatment_data = ic_card.treatment_data

        html = cshis_utils.get_treatments_html(self.database, treatment_data)
        self.ui.textEdit_treatment_data.setHtml(html)
