
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QVBoxLayout

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils
from libs import date_utils


# 過去病歷視窗
class DialogMedicalRecordPastHistory(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordPastHistory, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.patient_key = args[3]
        self.call_from = args[4]

        self.ui = None
        self.copy_medical_record = True
        self.total_pages = 1
        self.current_page = 1
        self.count_per_page = number_utils.get_integer(self.system_settings.field('過去病歷一頁筆數'))
        if self.count_per_page <= 0:  # 預設值
            self.count_per_page = 30

        self.show_massager = self.system_settings.field('過去病歷顯示推拿師父')
        self.date_format = self.system_settings.field('日期格式')
        self.folk_massage_item = self.system_settings.field('民俗調理項目名稱')
        self.show_simple = self.system_settings.field('過去病歷顯示精簡顯示頁')

        self._set_ui()
        self._set_signal()
        self._set_past_history_count()
        self._read_past_history(self.current_page)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_PAST_HISTORY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('拷貝病歷')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_past_history = class_utils.get_table_widget(self.ui.tableWidget_past_history, self.database)
        self.table_widget_simple_view = class_utils.get_table_widget(self.ui.tableWidget_simple_view, self.database)
        self.table_widget_past_history.set_column_hidden([0])
        self._set_table_width()
        if self.call_from in ['門診掛號', '病歷查詢', '診斷證明', '預約掛號']:
            self.ui.groupBox_copy_option.setVisible(False)
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setVisible(False)
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('關閉')

        self.ui.tabWidget_past_history.setCurrentIndex(0)
        self.ui.label_count_per_page.setText(f'每頁顯示{self.count_per_page}筆')

        if self.show_massager == 'Y':
            self.ui.tableWidget_past_history.setHorizontalHeaderItem(
                10, QtWidgets.QTableWidgetItem('推拿師父')
            )
        else:
            star_rating_delegate = class_utils.get_star_rating_delegate(
                self, self.database, self.ui.tableWidget_past_history)
            self.ui.tableWidget_past_history.setItemDelegate(star_rating_delegate)

            self.ui.tableWidget_past_history.setEditTriggers(
                QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.SelectedClicked)
            self.ui.tableWidget_past_history.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        if self.show_simple != 'Y':
            self.ui.tabWidget_past_history.removeTab(1)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 135, 60, 90, 70, 30, 220, 35, 90, 70, 120, 50]
        self.table_widget_past_history.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_past_history.itemSelectionChanged.connect(self._past_history_changed)
        # self.ui.tableWidget_past_history.doubleClicked.connect(self._edit_past_history)
        self.ui.tabWidget_past_history.currentChanged.connect(self._tab_changed)    # 切換分頁
        self.ui.pushButton_top.clicked.connect(self._top_record)
        self.ui.pushButton_next.clicked.connect(self._next_record)
        self.ui.pushButton_prev.clicked.connect(self._prev_record)
        self.ui.pushButton_bottom.clicked.connect(self._bottom_record)
        self.ui.spinBox_move_page.valueChanged.connect(self._spin_box_move_page)

    def _tab_changed(self, i):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        tab_name = self.ui.tabWidget_past_history.tabText(i)

        if tab_name == '處方精簡顯示':
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def accepted_button_clicked(self):
        if not self.copy_medical_record:
            return

        case_key = self.table_widget_past_history.field_value(0)

        if self.ui.radioButton_ins_prescript.isChecked():
            copy_ins_prescript_to = '健保處方'
        else:
            copy_ins_prescript_to = '自費處方'

        case_utils.copy_past_medical_record(
            self.database, self.system_settings, self.parent, case_key,
            self.ui.checkBox_diagnostic.isChecked(),
            self.ui.checkBox_remark.isChecked(),
            self.ui.checkBox_disease.isChecked(),
            self.ui.checkBox_ins_prescript.isChecked(),
            copy_ins_prescript_to,
            self.ui.checkBox_ins_treat.isChecked(),
            self.ui.checkBox_self_prescript.isChecked(),
            self.ui.checkBox_self_prescript_to_ins.isChecked(),
            self.ui.checkBox_not_overwrite.isChecked(),
        )

    def get_past_case_key(self):
        case_key = self.table_widget_past_history.field_value(0)

        return case_key

    def _set_past_history_count(self):
        case_key_exclude = ''
        if self.call_from == '病歷登錄' and self.case_key is not None:
            case_key_exclude = f'AND CaseKey != {self.case_key}'

        if self.system_settings.field('過去病歷顯示民俗調理') == 'Y':
            massage_condition = ''
        else:
            massage_condition = 'AND TreatType != "民俗調理"'

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                cases.PatientKey = {self.patient_key}
                {massage_condition}
                {case_key_exclude}
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self.total_pages = int(row_count / self.count_per_page)
        if row_count % self.count_per_page > 0:
            self.total_pages += 1

        if self.total_pages == 0:
            self.total_pages = 1

        self.ui.spinBox_move_page.setMaximum(self.total_pages)
        self.ui.label_total_pages.setText(f'共{self.total_pages}頁')
        self._set_page_button()

    def _set_page_button(self):
        self.ui.label_current_page.setText(f'第{self.current_page}頁')
        self.ui.spinBox_move_page.setValue(self.current_page)

    def _spin_box_move_page(self):
        self.current_page = self.ui.spinBox_move_page.value()

        self._read_past_history(self.current_page)
        self._set_page_button()

    def _top_record(self):
        self.current_page = 1

        self._read_past_history(self.current_page)
        self._set_page_button()

    def _prev_record(self):
        if self.current_page > 1:
            self.current_page -= 1

        self._read_past_history(self.current_page)
        self._set_page_button()

    def _next_record(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

        self._read_past_history(self.current_page)
        self._set_page_button()

    def _bottom_record(self):
        self.current_page = self.total_pages

        self._read_past_history(self.current_page)
        self._set_page_button()

    def _read_past_history(self, page=1):
        case_key_exclude = ''
        if self.call_from == '病歷登錄' and self.case_key is not None:
            case_key_exclude = f'AND CaseKey != {self.case_key}'

        if self.system_settings.field('過去病歷顯示民俗調理') == 'Y':
            massage_condition = ''
        else:
            massage_condition = 'AND TreatType != "民俗調理"'

        start_index = ((page-1) * self.count_per_page)
        ins_type_list = string_utils.xstr(nhi_utils.INS_TYPE)[1:-1]
        sql = f'''
            SELECT
                CaseKey, Name, PatientKey, CaseDate, TreatType, Card, Continuance,
                DiseaseCode1, DiseaseName1,
                InsType, SpecialCode, Injury, CurativeEffect, Doctor, Massager, TotalFee
            FROM cases
            WHERE
                cases.PatientKey = {self.patient_key}
                {massage_condition}
                {case_key_exclude}
            ORDER BY CaseDate DESC, FIELD(cases.InsType, {ins_type_list})
            LIMIT {start_index}, {self.count_per_page}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            br = '<br>' * 12
            html = f'''
                {br}
                <center><b>無過去病歷</b></center>
            '''
            self.ui.textEdit_medical_record.setHtml(html)
            self.ui.groupBox_copy_option.setEnabled(False)
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

            return

        self._set_group_box_title(rows[0])
        self.table_widget_past_history.set_db_data(sql, self._set_table_data)

        if self.call_from == '病歷查詢' and self.case_key is not None:
            self._locate_medical_record()

        self._past_history_changed()

        if self.show_simple == 'Y':
            self._set_simple_view(rows)

        del rows

    def _set_table_data(self, row_no, row):
        case_key = row['CaseKey']
        if row['InsType'] == '健保':
            medicine_set = 1
        else:
            medicine_set = 2

        pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set=medicine_set)
        if pres_days == 0:
            pres_days = None

        special_code = string_utils.xstr(row['SpecialCode'])
        disease_name1 = string_utils.xstr(row['DiseaseName1'])
        injury = string_utils.xstr(row['Injury'])
        treat_type = string_utils.xstr(row['TreatType'])

        card = string_utils.xstr(row['Card'])
        if card == '免卡':
            card = None

        star_count = number_utils.get_integer(row['CurativeEffect'])
        star = class_utils.get_star_rating(star_count)  # get instance
        curative_effect = QtWidgets.QTableWidgetItem()
        curative_effect.setData(0, star)
        if self.show_massager == 'Y':
            curative_effect = string_utils.xstr(row['Massager'])

        total_fee = number_utils.get_integer(row['TotalFee'])
        total_fee = string_utils.xstr(f'{total_fee:,}')
        if row['InsType'] == '健保':
            self_pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set=2)
            if self_pres_days > 0:
                total_fee += f'\n{self_pres_days}日藥'

        case_date = string_utils.xstr(row['CaseDate'].date())
        if self.date_format == '民國年':
            case_date = date_utils.date_to_zh_tw_date(case_date)

        if injury == '主訴職災':
            case_date_label = None
        else:
            case_date_label = case_date

        medical_record_data = [
            string_utils.xstr(row['CaseKey']),
            case_date_label,
            string_utils.xstr(row['InsType']),
            treat_type,
            card,
            string_utils.xstr(row['Continuance']),
            disease_name1,
            string_utils.xstr(pres_days),
            string_utils.xstr(row['Doctor']),
            total_fee,
            curative_effect,
        ]

        for column in range(len(medical_record_data)):
            self.ui.tableWidget_past_history.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record_data[column])
            )
            if column in [0, 7, 9]:
                self.ui.tableWidget_past_history.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [5]:
                self.ui.tableWidget_past_history.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            try:
                if self.folk_massage_item in [None, '']:
                    folk_massage_item = '民俗調理'

                sql = f'''
                    SELECT PrescriptKey FROM prescript
                    WHERE
                        CaseKey = {case_key} AND
                        MedicineSet >= 2 AND
                        MedicineName NOT IN ("{folk_massage_item}", "民俗調理")
                    LIMIT 1
                '''
                pres_rows = self.database.select_record(sql)
            except Exception:
                pres_rows = []

            if row['InsType'] == '自費' or number_utils.get_integer(row['TotalFee']) > 0 or len(pres_rows) > 0:
                if row['TreatType'] == '民俗調理':
                    self.ui.tableWidget_past_history.item(
                        row_no, column).setForeground(
                        QtGui.QColor('darkMagenta')
                    )
                elif len(pres_rows) > 0:
                    self.ui.tableWidget_past_history.item(
                        row_no, column).setForeground(
                        QtGui.QColor('blue')
                    )

            if row['Continuance'] == 1:
                self.ui.tableWidget_past_history.item(
                    row_no, column).setBackground(
                    QtGui.QColor('lightgray')
                )

        if special_code != '' and disease_name1 != '':
            self.ui.tableWidget_past_history.item(row_no, 6).setForeground(QtGui.QColor('red'))
        if number_utils.get_integer(pres_days) > 7:
            self.ui.tableWidget_past_history.item(row_no, 7).setForeground(QtGui.QColor('red'))

        button_open = QtWidgets.QPushButton(self.ui.tableWidget_past_history)
        button_open.setIcon(QtGui.QIcon('./icons/gtk-open.svg'))
        button_open.setFlat(True)
        button_open.clicked.connect(self._edit_past_history)
        if self.call_from == '門診掛號':
            button_open.setEnabled(False)

        self.ui.tableWidget_past_history.setCellWidget(row_no, 11, button_open)
        self._set_injury(row_no, case_date, injury)

    def _set_injury(self, row_no, case_date, injury):
        if injury != '主訴職災':
            self.ui.tableWidget_past_history.setCellWidget(row_no, 1, None)
            return

        case_date += f'<br><font size="2" color="red">({injury})</font>'
        case_date_label = QtWidgets.QLabel()
        case_date_label.setStyleSheet('padding: 1px')
        case_date_label.setText(case_date)

        self.ui.tableWidget_past_history.setCellWidget(row_no, 1, case_date_label)

    def _get_patient_data(self):
        sql = f'''
            SELECT Gender, Birthday FROM patient
            WHERE
                PatientKey = {self.patient_key}
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None, None

        row = rows[0]
        gender = string_utils.xstr(row['Gender'])
        birthday = string_utils.xstr(row['Birthday'])

        return gender, birthday

    def _set_group_box_title(self, row):
        patient_key = string_utils.xstr(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        gender, birthday = self._get_patient_data()

        if self.system_settings.field('日期格式') == '民國年':
            try:
                birthday = date_utils.date_to_zh_tw_date(birthday)
            except Exception:
                pass

        self.ui.groupBox_history_list.setTitle(f'{name} 過去病歷一覽表 (雙擊療效欄位, 可輸入療效顆星, 並於輸入後按右邊存檔按鈕儲存療效)')
        self.ui.groupBox_medical_record.setTitle(
            f'病歷號: {patient_key} {name}({gender}) 出生日期: {birthday}  病歷內容'
        )

    def _past_history_changed(self):
        case_key = self.table_widget_past_history.field_value(0)

        self._set_copy_prescript_check_box()
        html = case_utils.get_medical_record_html(self.database, self.system_settings, case_key)
        self.ui.textEdit_medical_record.setHtml(html)

    def _set_copy_prescript_check_box(self):
        case_key = self.table_widget_past_history.field_value(0)
        ins_type = self.table_widget_past_history.field_value(2)

        self.ui.checkBox_ins_prescript.setChecked(False)  # 健保療程2-6次預設不拷貝藥品
        self.ui.checkBox_ins_prescript.setEnabled(False)  # 健保療程2-6次預設不拷貝藥品

        self.ui.radioButton_ins_prescript.setEnabled(False)
        self.ui.radioButton_self_prescript.setEnabled(False)

        self.ui.checkBox_ins_treat.setChecked(False)
        self.ui.checkBox_ins_treat.setEnabled(False)

        if ins_type == '健保':
            sql = f'''
                SELECT Treatment FROM cases
                WHERE
                    CaseKey = {case_key}
            '''
            rows = self.database.select_record(sql)
            treatment = string_utils.xstr(rows[0]['Treatment'])

            if treatment != '':
                self.ui.checkBox_ins_treat.setEnabled(True)
                self.ui.checkBox_ins_treat.setChecked(True)

            sql = f'''
                SELECT PrescriptKey FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                self.ui.checkBox_ins_prescript.setEnabled(True)
                self.ui.radioButton_ins_prescript.setEnabled(True)
                self.ui.radioButton_self_prescript.setEnabled(True)
                if treatment == '' or self.system_settings.field('預設拷貝健保針傷科處方用藥') == 'Y':
                    self.ui.checkBox_ins_prescript.setChecked(True)  # 預設非療程才拷貝藥品

        # if self.system_settings.field('健保自費分開') == 'Y':
        #     sql = f'''
        #         SELECT InsType FROM cases
        #         WHERE
        #             CaseKey = {self.case_key}
        #     '''
        #     rows = self.database.select_record(sql)
        #     if len(rows) > 0 and string_utils.xstr(rows[0]['InsType']) == '健保':
        #         self.ui.checkBox_self_prescript.setEnabled(False)
        #         self.ui.radioButton_self_prescript.setEnabled(False)
        #         return
        #     elif ins_type == '健保':  # 目前病歷為自費且過去病歷為健保病歷
        #         self.ui.radioButton_ins_prescript.setEnabled(False)
        #         self.ui.radioButton_self_prescript.setChecked(True)

        if self.system_settings.field('預設拷貝備註') == 'Y':
            self.ui.checkBox_remark.setChecked(True)
        else:
            self.ui.checkBox_remark.setChecked(False)

        sql = f'''
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            copy_self_prescript = True
        else:
            copy_self_prescript = False

        self.ui.checkBox_self_prescript.setEnabled(copy_self_prescript)
        self.ui.checkBox_self_prescript.setChecked(copy_self_prescript)
        self.ui.checkBox_not_overwrite.setEnabled(copy_self_prescript)

        if copy_self_prescript:
            if self.system_settings.field('預設拷貝自費處方') == 'Y':
                self.ui.checkBox_self_prescript.setChecked(True)
            else:
                self.ui.checkBox_self_prescript.setChecked(False)

        try:
            if self.parent.ins_type == '自費':
                if ins_type == '自費':
                    self.ui.checkBox_self_prescript.setChecked(True)

                self.ui.radioButton_self_prescript.setChecked(True)
        except AttributeError:
            pass

    def _edit_past_history(self):
        case_key = self.table_widget_past_history.field_value(0)

        if self.call_from == '診斷證明':
            parent = self.parent.parent.parent
        else:
            parent = self.parent.parent

        parent.open_medical_record(case_key, '過去病歷')

        self.copy_medical_record = False

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def _locate_medical_record(self):
        for row_no in range(self.ui.tableWidget_past_history.rowCount()):
            item = self.ui.tableWidget_past_history.item(row_no, 0)
            self.ui.tableWidget_past_history.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)
            self.ui.tableWidget_past_history.selectRow(row_no)

            if item.text() == string_utils.xstr(self.case_key):
                break

    def _set_simple_view(self, rows):
        self.ui.tableWidget_simple_view.setRowCount(0)

        col_count = self.ui.tableWidget_simple_view.columnCount()
        row_count = int(len(rows) / col_count)
        if len(rows) % col_count > 0:
            row_count += 1

        self.ui.tableWidget_simple_view.setRowCount(row_count)

        for row_no in range(row_count):
            for col_no in range(0, col_count):
                try:
                    row = rows[row_no * col_count + col_no]
                except IndexError:
                    break

                html = self._get_medical_record_html(row)

                text_edit = QtWidgets.QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setHtml(html)

                v_layout = QVBoxLayout()
                v_layout.addWidget(text_edit)
                widget = QtWidgets.QWidget()
                widget.setLayout(v_layout)

                self.ui.tableWidget_simple_view.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem('')
                )
                self.ui.tableWidget_simple_view.item(
                    row_no, col_no).setBackground(
                    QtGui.QColor('lightGray')
                )
                self.ui.tableWidget_simple_view.setCellWidget(
                    row_no, col_no, widget
                )

    # 取得病歷html格式
    def _get_medical_record_html(self, row):
        if string_utils.xstr(row['InsType']) == '健保':
            card = string_utils.xstr(row['Card'])
            if number_utils.get_integer(row['Continuance']) >= 1:
                card += '-' + str(row['Continuance'])

            card = f'<b>健保</b>: {card}'
        else:
            card = '<b>自費</b>'

        case_date = string_utils.xstr(row['CaseDate'].date())
        doctor = string_utils.xstr(row['Doctor'])
        medical_record = f'<b>日期</b>: {case_date} {card} <b>醫師</b>:{doctor}<hr>'
        disease_code1 = string_utils.xstr(row['DiseaseCode1'])
        disease_name1 = string_utils.xstr(row['DiseaseName1'])
        if disease_code1 != '':
            medical_record += f'<b>主診斷</b>: {disease_code1} {disease_name1}<br>'

        medical_record = f'''
            <div style="width: 95%;">
                {medical_record}
            </div>
        '''

        case_key = row['CaseKey']
        prescript_record = case_utils.get_prescript_record(self.database, self.system_settings, case_key)

        html = f'''
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    {medical_record}
                    {prescript_record}
                </body>
            </html>
        '''

        return html
