
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from lxml import etree as ET

from libs import ui_utils
from libs import string_utils
from libs import system_utils
from libs import xml_utils
from libs import db_utils
from libs import module_utils
from libs import update_utils
from libs import dialog_utils
from libs import log_utils
from libs import personnel_utils
import os


# 診察詞庫 2018.11.22
class DictDiagnostic(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictDiagnostic, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_DIAGNOSTIC, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        tab_sympton = module_utils.get_dict_symptom(self, *self.args)
        tab_tongue = module_utils.get_dict_tongue(self, *self.args)
        tab_pulse = module_utils.get_dict_pulse(self, *self.args)
        tab_remark = module_utils.get_dict_remark(self, *self.args)
        tab_disease = module_utils.get_dict_disease(self, *self.args)
        tab_disease_custom = module_utils.get_dict_disease_custom(self, *self.args)
        tab_distinguish = module_utils.get_dict_distinguish(self, *self.args)
        tab_cure = module_utils.get_dict_cure(self, *self.args)

        self.ui.tabWidget_diagnostic.addTab(tab_sympton, '主訴資料')
        self.ui.tabWidget_diagnostic.addTab(tab_tongue, '舌診資料')
        self.ui.tabWidget_diagnostic.addTab(tab_pulse, '脈象資料')
        self.ui.tabWidget_diagnostic.addTab(tab_remark, '備註資料')
        self.ui.tabWidget_diagnostic.addTab(tab_disease, '病名資料')
        self.ui.tabWidget_diagnostic.addTab(tab_disease_custom, '自訂病名')
        self.ui.tabWidget_diagnostic.addTab(tab_distinguish, '辨證資料')
        self.ui.tabWidget_diagnostic.addTab(tab_cure, '治則資料')
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_dict_diagnostic_groups_json.setEnabled(False)
            self.ui.action_export_dict_diagnostic_json.setEnabled(False)
            self.ui.action_export_disease_groups.setEnabled(False)
            self.ui.action_export_icd10_json.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_template)
        self.ui.action_export_dict_diagnostic_groups_json.triggered.connect(
            self._export_dict_diagnostic_groups_json
        )
        self.ui.action_export_dict_diagnostic_json.triggered.connect(self._export_dict_diagnostic_json)
        self.ui.action_export_disease_groups.triggered.connect(self._export_disease_groups)
        self.ui.action_import_disease_groups.triggered.connect(self._import_disease_groups)
        self.ui.action_export_icd10_json.triggered.connect(self._export_icd10_json)
        self.ui.action_convert_chronic_disease.triggered.connect(self._convert_chronic_disease)
        self.ui.action_convert_2023_ICD10.triggered.connect(self._convert_2023_ICD10)
        self.ui.action_convert_2023_ICD10_input_code.triggered.connect(self._convert_2023_ICD10_input_code)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_template(self):
        self.close_all()
        self.close_tab()

    def _export_disease_groups(self):
        options = QFileDialog.Options()

        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getSaveFileName(
            self, "匯出病名類別詞庫",
            'disease_groups.xml',
            "所有檔案 (*);;xml檔 (*.xml)", options=options
        )
        if not file_name:
            return

        sql = '''
            SELECT ICDCode, Groups FROM icd10
            WHERE
                Groups IS NOT NULL AND LENGTH(Groups) > 0
            ORDER BY ICDCode
        '''
        rows = self.database.select_record(sql)

        root = ET.Element('groups')
        for row in rows:
            disease_groups = ET.SubElement(root, 'disease_groups')
            icd = ET.SubElement(disease_groups, 'icd')
            icd.text = string_utils.xstr(row['ICDCode'])
            groups = ET.SubElement(disease_groups, 'groups')
            groups.text = string_utils.xstr(row['Groups'])

        tree = ET.ElementTree(root)
        tree.write(file_name, pretty_print=True, xml_declaration=True, encoding="utf-8")

    def _import_disease_groups(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(
            self, "匯入病名類別詞庫",
            'disease_groups.xml',
            "所有檔案 (*);;xml檔 (*.xml)", options=options
        )
        if not filename:
            return

        tree = ET.parse(filename)

        root = tree.getroot()
        groups = root.xpath('//groups/disease_groups')

        row_count = len(groups)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在匯入病名類別中, 請稍後...', '取消', 0, row_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for row_no, row in enumerate(groups):
            progress_dialog.setValue(row_no)
            data = xml_utils.convert_node_to_dict(row)
            groups = data['groups']
            icd_code = data['icd']
            sql = f'''
                UPDATE icd10
                SET
                    Groups = "{groups}"
                WHERE
                    ICDCode = "{icd_code}"
            '''
            self.database.exec_sql(sql)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

    def _export_dict_diagnostic_groups_json(self):
        options = QFileDialog.Options()
        json_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出診察類別JSON檔案", 'diagnostic_groups.json',
            "json檔案 (*.json)",
            options=options
        )
        if not json_file_name:
            return

        sql = '''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType IN ("主訴", "舌診", "脈象", "辨證", "治則", "備註")
            ORDER BY DictGroupsKey
        '''
        rows = self.database.select_record(sql)

        json_data = db_utils.mysql_to_json(rows)
        text_file = open(json_file_name, "w", encoding='utf8')
        text_file.write(str(json_data))
        text_file.close()

        system_utils.show_message_box(
            QMessageBox.Information,
            'JSON資料匯出完成',
            f'<h3>{json_file_name}匯出完成.</h3>',
            'JSON 檔案格式.'
        )

    def _export_dict_diagnostic_json(self):
        options = QFileDialog.Options()
        json_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出診察JSON檔案", 'diagnostic.json',
            "json檔案 (*.json)",
            options=options
        )
        if not json_file_name:
            return

        sql = '''
            SELECT * FROM clinic
            ORDER BY ClinicKey
        '''
        rows = self.database.select_record(sql)

        json_data = db_utils.mysql_to_json(rows)
        text_file = open(json_file_name, "w", encoding='utf8')
        text_file.write(str(json_data))
        text_file.close()

        system_utils.show_message_box(
            QMessageBox.Information,
            'JSON資料匯出完成',
            f'<h3>{json_file_name}匯出完成.</h3>',
            'JSON 檔案格式.'
        )

    def _export_icd10_json(self):
        options = QFileDialog.Options()
        json_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出病名JSON檔案", 'icd10.json',
            "json檔案 (*.json)",
            options=options
        )
        if not json_file_name:
            return

        sql = '''
            SELECT * FROM icd10
            WHERE
                ICDCode IS NOT NULL AND LENGTH(ICDCode) > 0
            ORDER BY ICDCode
        '''
        rows = self.database.select_record(sql)

        json_data = db_utils.mysql_to_json(rows)
        text_file = open(json_file_name, "w", encoding='utf8')
        text_file.write(str(json_data))
        text_file.close()

        system_utils.show_message_box(
            QMessageBox.Information,
            'JSON資料匯出完成',
            f'<h3>{json_file_name}匯出完成.</h3>',
            'JSON 檔案格式.'
        )

    def _convert_chronic_disease(self):
        msg_box = dialog_utils.get_message_box(
            '匯入慢性病資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定匯入新版慢性病範圍病名?</b></font>',
            '注意！資料匯入後, 將無法回復!'
        )
        convert_data = msg_box.exec_()
        if not convert_data:
            return

        update_utils.update_chronic_condition(self.parent, self.database)
        system_utils.show_message_box(
            QMessageBox.Information,
            '匯入完成',
            '<h3>新版慢性病資料匯入完成.</h3>',
            'JSON 檔案格式.'
        )

    def _convert_2023_ICD10(self):
        msg_box = dialog_utils.get_message_box(
            '更新2023年版ICD10', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定更新2023年新版ICD10資料?</b></font>',
            '注意！更新過程會花費較長時間!'
        )
        convert_data = msg_box.exec_()
        if not convert_data:
            return

        update_utils.update_2023_icd10(self.parent, self.database)
        update_utils.delete_2023_icd10(self.parent, self.database)
        os.remove('complicated_treatment_disease.json')
        self.parent.get_treatment_list_from_db()
        self.parent.get_treatment_list_from_json()

        station_no = self.system_settings.field('工作站編號')
        self.database.exec_sql('''
            DELETE FROM system_log
            WHERE
                LogType = "資料轉檔" AND
                LogName = "2023ICD10轉檔" AND
                Log = "已轉檔"
        ''')
        self.database.exec_sql(f'''
            DELETE FROM system_log
            WHERE
                LogType = "資料轉檔" AND
                LogName = "2023ICD10轉檔" AND
                Log = "{station_no}"
        ''')
        log_utils.write_system_log(self.database, '資料轉檔', '2023ICD10轉檔', '已轉檔')
        log_utils.write_system_log(self.database, '資料轉檔', '2023ICD10轉檔', station_no)

        system_utils.show_message_box(
            QMessageBox.Information,
            '更新入完成',
            '<h3>2023年版ICD10更新完成.</h3>',
            '恭喜您.')

    def _convert_2023_ICD10_input_code(self):
        msg_box = dialog_utils.get_message_box(
            '更新2023年版ICD10輸入碼', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定更新2023年新版ICD10輸入碼資料?</b></font>',
            '注意！更新過程會花費較長時間!'
        )
        convert_data = msg_box.exec_()
        if not convert_data:
            return

        update_utils.update_2023_icd10_input_code(self.parent, self.database)

        system_utils.show_message_box(
            QMessageBox.Information,
            '更新入完成',
            '<h3>2023年版ICD10更新完成.</h3>',
            '恭喜您.')
