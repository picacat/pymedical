# 複雜性傷科選取視窗 2021.02.24
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import prescript_utils, system_utils, ui_utils


# 主視窗
class DialogComplicatedMassage(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.treatment = args[2]
        self.second_treatment = args[3]
        self.diag_time = args[4]
        self.table_widget_treat = args[5]

        self.ui = None
        self.position_keyword = "治療部位:"
        self.auxiliary_keyword = "輔助治療:"

        self.default_moderate_massage_time, self.default_highly_massage_time = (
            prescript_utils.get_default_complicated_massage_time(self.system_settings)
        )

        self._set_ui()
        self._set_signal()

        self._set_selected_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_COMPLICATED_MASSAGE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowTitle(self.treatment)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("確定")
        # if self.treatment in ['傷科治療', '一般傷科']:
        #     self.ui.label_treat_time.hide()
        #     self.ui.label_cure.hide()
        # else:
        #     self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.ui.label_message.setText("")
        if self.treatment in ["一般傷科"]:
            self.ui.label_message.setText("未滿七歲兒童傷科治療")
            self.ui.checkBox_5.setEnabled(False)
            self.ui.checkBox_6.setEnabled(False)
            self.ui.checkBox_7.setEnabled(False)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        if self.treatment in [
            "一般針灸",
            "電針",
            "中度複雜性針灸",
            "一般傷科",
            "中度複雜性傷科",
        ] and self.second_treatment in [None, ""]:
            minutes = 10
        elif self.treatment in [
            "高度複雜性針灸",
            "高度複雜性傷科",
            "中度複雜性傷科合併特殊疾病",
            "脫臼整復復位",
            "骨折復位",
        ] and self.second_treatment in [None, ""]:
            minutes = 20
        elif (
            "一般" in self.treatment
            and "一般" in self.second_treatment
            or "一般" in self.treatment
            and "中度" in self.second_treatment
        ):
            minutes = 10
        elif "一般" in self.treatment and "高度" in self.second_treatment:
            minutes = 20
        elif "中度" in self.treatment and "一般" in self.second_treatment:
            minutes = 10
        elif "中度" in self.treatment and "中度" in self.second_treatment:
            minutes = 20
        elif "中度" in self.treatment and "高度" in self.second_treatment:
            minutes = 30
        elif "高度" in self.treatment and "一般" in self.second_treatment:
            minutes = 20
        elif "高度" in self.treatment and "中度" in self.second_treatment:
            minutes = 30
        elif "高度" in self.treatment and "高度" in self.second_treatment:
            minutes = 40
        else:
            minutes = 20

        if minutes == 10 and self.default_moderate_massage_time > minutes:
            minutes = self.default_moderate_massage_time
        elif minutes == 20 and self.default_highly_massage_time > minutes:
            minutes = self.default_highly_massage_time

        self.ui.label_treat_time.setText(f"至少{minutes}分鐘")
        self.ui.spinBox_time.setMinimum(minutes)
        self.ui.spinBox_time.setValue(minutes)

        self.ui.timeEdit_start_time.setTime(self.diag_time.time())
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(minutes * 60)
        )
        self.ui.timeEdit_start_time.setCurrentSection(
            QtWidgets.QDateTimeEdit.MinuteSection
        )
        self.ui.timeEdit_end_time.setCurrentSection(
            QtWidgets.QDateTimeEdit.MinuteSection
        )

        if self.treatment in ["中度複雜性傷科", "高度複雜性傷科"]:
            self.ui.checkBox_5.setEnabled(False)
            self.ui.checkBox_6.setEnabled(False)
            self.ui.checkBox_7.setEnabled(False)

        if self.system_settings.field("院所名稱") == "信望愛中醫診所":
            self.ui.checkBox_2.setChecked(True)  # 刮痧
            self.ui.checkBox_3.setChecked(True)  # 熱療
            self.ui.checkBox_9.setChecked(True)  # 膏布
            # self.ui.spinBox_time.setValue(20)
            # self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

        self.treat_position_list = [
            self.ui.checkBox_c1,
            self.ui.checkBox_c2,
            self.ui.checkBox_c3,
            self.ui.checkBox_c4,
            self.ui.checkBox_c5,
            self.ui.checkBox_c6,
            self.ui.checkBox_lu1,
            self.ui.checkBox_lu2,
            self.ui.checkBox_lu3,
            self.ui.checkBox_lu4,
            self.ui.checkBox_lu5,
            self.ui.checkBox_lu6,
            self.ui.checkBox_lu7,
            self.ui.checkBox_lb1,
            self.ui.checkBox_lb2,
            self.ui.checkBox_lb3,
            self.ui.checkBox_lb4,
            self.ui.checkBox_lb5,
            self.ui.checkBox_lb6,
            self.ui.checkBox_ru1,
            self.ui.checkBox_ru2,
            self.ui.checkBox_ru3,
            self.ui.checkBox_ru4,
            self.ui.checkBox_ru5,
            self.ui.checkBox_ru6,
            self.ui.checkBox_ru7,
            self.ui.checkBox_rb1,
            self.ui.checkBox_rb2,
            self.ui.checkBox_rb3,
            self.ui.checkBox_rb4,
            self.ui.checkBox_rb5,
            self.ui.checkBox_rb6,
        ]

        self.treat_auxiliary_list = [
            self.ui.checkBox_1,
            self.ui.checkBox_2,
            self.ui.checkBox_3,
            self.ui.checkBox_4,
            self.ui.checkBox_5,
            self.ui.checkBox_6,
            self.ui.checkBox_7,
            self.ui.checkBox_8,
            self.ui.checkBox_9,
            self.ui.checkBox_10,
        ]

        self.treat_item_list = [
            self.ui.checkBox_item1,  # 正骨手法
            self.ui.checkBox_item2,
            self.ui.checkBox_item3,
            self.ui.checkBox_item4,
            self.ui.checkBox_item5,
            self.ui.checkBox_item6,
            self.ui.checkBox_item7,
            self.ui.checkBox_item8,
            self.ui.checkBox_item9,
            self.ui.checkBox_item10,
            self.ui.checkBox_item11,
            self.ui.checkBox_item12,
            self.ui.checkBox_item13,
            self.ui.checkBox_item14,
            self.ui.checkBox_item15,
            self.ui.checkBox_item16,
            self.ui.checkBox_item17,  # 理筋手法
            self.ui.checkBox_item18,
            self.ui.checkBox_item19,  # 其他
        ]

    def _set_selected_data(self):
        self._set_selected_position()
        self._set_selected_auxiliary()
        self._set_selected_treat_item()

        self._check_available()

    def _set_selected_position(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )
            if item is None:
                continue

            medicine_name = item.text()
            if self.position_keyword not in medicine_name:
                continue

            position = medicine_name.replace(self.position_keyword, "").strip()
            for check_box in self.treat_position_list:
                if check_box.text() == position:
                    check_box.setChecked(True)

    def _set_selected_auxiliary(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )
            if item is None:
                continue

            medicine_name = item.text()
            if self.auxiliary_keyword not in medicine_name:
                continue

            auxiliary_treat = medicine_name.replace(self.auxiliary_keyword, "").strip()
            for check_box in self.treat_auxiliary_list:
                if self.second_treatment is None and check_box.text() in [
                    "放血治療",
                    "艾灸治療",
                    "眼部特殊針灸",
                ]:
                    continue

                if check_box.text() == auxiliary_treat:
                    check_box.setChecked(True)

    def _set_selected_treat_item(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )
            if item is None:
                continue

            medicine_name = item.text()
            for check_box in self.treat_item_list:
                if check_box.text() == medicine_name:
                    check_box.setChecked(True)

    def _set_treat_time(self):
        self.ui.timeEdit_end_time.setTime(
            self.ui.timeEdit_start_time.time().addSecs(
                self.ui.spinBox_time.value() * 60
            )
        )

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

        self.ui.timeEdit_start_time.timeChanged.connect(self._set_treat_time)
        self.ui.timeEdit_end_time.timeChanged.connect(self._set_treat_time)
        self.ui.spinBox_time.valueChanged.connect(self._set_treat_time)

        for check_box in (
            self.treat_position_list + self.treat_auxiliary_list + self.treat_item_list
        ):
            check_box.clicked.connect(self._check_available)

    # def _check_available(self):
    #     position_count = 0
    #     for check_box in self.treat_position_list:
    #         if check_box.isChecked():
    #             check_box.setStyleSheet("color:blue; font-weight:bold")
    #             position_count += 1
    #         else:
    #             check_box.setStyleSheet(None)

    #     treatment_count = 0
    #     for check_box in self.treat_auxiliary_list:
    #         if check_box.isChecked():
    #             check_box.setStyleSheet("color:blue; font-weight:bold")
    #             treatment_count += 1
    #         else:
    #             check_box.setStyleSheet(None)

    #     for check_box in self.treat_item_list:
    #         if check_box.isChecked():
    #             check_box.setStyleSheet("color:blue; font-weight:bold")
    #         else:
    #             check_box.setStyleSheet(None)

    #     self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
    #     if position_count >= 1 and treatment_count >= 1:
    #         self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def _check_available(self):
        position_count = 0
        for check_box in self.treat_position_list:
            if check_box.isChecked():
                check_box.setStyleSheet("color:blue; font-weight:bold")
                position_count += 1
            else:
                check_box.setStyleSheet(None)

        self.ui.label_position_count.setText(f"合計部位: {position_count}個")

        treatment_count = 0
        for check_box in self.treat_auxiliary_list:
            if check_box.isChecked():
                check_box.setStyleSheet("color:blue; font-weight:bold")
                treatment_count += 1
            else:
                check_box.setStyleSheet(None)

        for check_box in self.treat_item_list:
            if check_box.isChecked():
                check_box.setStyleSheet("color:blue; font-weight:bold")
            else:
                check_box.setStyleSheet(None)

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        if position_count >= 2 and treatment_count >= 1:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def accepted_button_clicked(self):
        pass
