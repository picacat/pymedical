# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import string_utils, system_utils, ui_utils


# 輸入申復資料 2022.11.08
class DialogInsAppeal(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsAppeal, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_date = args[2]
        self.apply_period = args[3]
        self.apply_type_code = args[4]
        self.ins_appeal_key = args[5]

        self.ui = None
        self.clinic_id = self.system_settings.field("院所代號")
        self.ins_apply_key = None
        self.reject_code = "否"

        self._set_ui()
        self._set_signal()
        self._set_data()

        if self.ins_appeal_key is not None:
            self._edit_ins_appeal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INS_APPEAL, self)
        system_utils.set_css(self, self.system_settings)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("存檔")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.comboBox_case_type.currentIndexChanged.connect(self._case_type_changed)
        self.ui.spinBox_sequence.valueChanged.connect(self._sequence_changed)

    def _set_data(self):
        case_type_list = self._get_case_type_list()
        ui_utils.set_combo_box(self.ui.comboBox_case_type, case_type_list, None)
        ui_utils.set_combo_box(
            self.ui.comboBox_sample, ["統扣", "立意", "歸戶", "隨機", "全審"], "立意"
        )

    def _get_case_type_list(self):
        sql = f'''
            SELECT CaseType FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "全月" AND
                ClinicID = "{self.clinic_id}"
            GROUP BY CaseType
        '''
        rows = self.database.select_record(sql)

        case_type_list = []
        for row in rows:
            case_type_list.append(row["CaseType"])

        return case_type_list

    def _case_type_changed(self):
        case_type = self.ui.comboBox_case_type.currentText()
        if case_type in ["", None]:
            return

        sql = f'''
            SELECT MAX(Sequence) AS Max FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "全月" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "{case_type}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.spinBox_sequence.setMinimum(1)
        self.ui.spinBox_sequence.setMaximum(rows[0]["Max"])

    def _sequence_changed(self):
        case_type = self.ui.comboBox_case_type.currentText()
        if case_type in ["", None]:
            return

        sequence = self.ui.spinBox_sequence.value()
        if sequence == 0:
            return

        sql = f'''
            SELECT InsApplyKey, Name FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "全月" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "{case_type}" AND
                Sequence = {sequence}
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.lineEdit_name.setText(string_utils.xstr(row["Name"]))
        self.ins_apply_key = row["InsApplyKey"]

    def get_ins_apply_key(self):
        return self.ins_apply_key

    def get_ins_appeal_key(self):
        return self.ins_appeal_key

    def get_reject(self):
        return self.reject_code

    def accepted_button_clicked(self):
        self._save_ins_appeal()
        self.close()

    def rejected_button_clicked(self):
        self.close()

    def _save_ins_appeal(self):
        case_type = self.ui.comboBox_case_type.currentText()
        sequence = self.ui.spinBox_sequence.value()
        sample = self.ui.comboBox_sample.currentText()
        if self.ui.checkBox_reject_all.isChecked():
            self.reject_code = "是"
        else:
            self.reject_code = "否"

        point1 = self.ui.spinBox_point1.value()
        point2 = self.ui.spinBox_point2.value()
        point3 = self.ui.spinBox_point3.value()

        fields = [
            "InsApplyKey",
            "ClinicID",
            "ApplyDate",
            "ApplyPeriod",
            "ApplyType",
            "CaseType",
            "Sequence",
            "Sample",
            "Reject",
            "Point1",
            "Point2",
            "Point3",
        ]
        data = [
            self.ins_apply_key,
            self.clinic_id,
            self.apply_date,
            self.apply_period,
            self.apply_type_code,
            case_type,
            sequence,
            sample,
            self.reject_code,
            point1,
            point2,
            point3,
        ]

        if self.ins_appeal_key is not None:
            self.database.update_record(
                "insappeal", fields, "InsAppealKey", self.ins_appeal_key, data
            )
        else:
            self.ins_appeal_key = self.database.insert_record("insappeal", fields, data)

    def _edit_ins_appeal(self):
        sql = f"""
            SELECT * FROM insappeal
            WHERE
                InsAppealKey = {self.ins_appeal_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.comboBox_case_type.setCurrentText(string_utils.xstr(row["CaseType"]))
        self.ui.spinBox_sequence.setValue(row["Sequence"])
        self.ui.comboBox_sample.setCurrentText(string_utils.xstr(row["Sample"]))
        self.ui.spinBox_point1.setValue(row["Point1"])
        self.ui.spinBox_point2.setValue(row["Point2"])
        self.ui.spinBox_point3.setValue(row["Point3"])
