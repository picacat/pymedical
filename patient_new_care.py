# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import patient_utils


# 初診照護病歷 2020.10.05
class PatientNewCare(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PatientNewCare, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_widget_list()
        self._set_signal()

        self._read_patient_new_care()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PATIENT_NEW_CARE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        for widget in self.all_widget_list:
            widget.clicked.connect(self._set_check_box_color)

        self.ui.toolButton_symptom.clicked.connect(lambda: self._insert_field('Symptom'))
        self.ui.toolButton_tongue.clicked.connect(lambda: self._insert_field('Tongue'))
        self.ui.toolButton_pulse.clicked.connect(lambda: self._insert_field('Pulse'))
        self.ui.toolButton_diagnostic.clicked.connect(lambda: self._insert_field('DiseaseName1'))

    def _set_check_box_color(self):
        sender = self.sender()
        if sender.isChecked():
            sender.setStyleSheet('color:darkred; font-weight:bold')
        else:
            sender.setStyleSheet(None)

    def _set_widget_list(self):
        self.past_history_widget_list = [
            self.ui.checkBox3_1,
            self.ui.checkBox3_2,
            self.ui.checkBox3_3,
            self.ui.checkBox3_4,
            self.ui.checkBox3_5,
            self.ui.checkBox3_6,
            self.ui.checkBox3_7,
            self.ui.checkBox3_8,
            self.ui.checkBox3_9,
        ]
        self.diet_widget_list = [
            self.ui.checkBox4_1,
            self.ui.checkBox4_2,
            self.ui.checkBox4_3,
            self.ui.checkBox4_4,
        ]
        self.allergy_widget_list = [
            self.ui.checkBox4_5,
            self.ui.checkBox4_6,
            self.ui.checkBox4_7,
        ]
        self.smoke_widget_list = [
            self.ui.checkBox4_8,
            self.ui.checkBox4_9,
        ]
        self.alcohol_widget_list = [
            self.ui.checkBox4_10,
            self.ui.checkBox4_11,
        ]
        self.family_widget_list = [
            self.ui.checkBox5_1,
            self.ui.checkBox5_2,
            self.ui.checkBox5_3,
            self.ui.checkBox5_4,
            self.ui.checkBox5_5,
            self.ui.checkBox5_6,
            self.ui.checkBox5_7,
            self.ui.checkBox5_8,
        ]
        self.consciousness_widget_list = [
            self.ui.checkBox_11,
            self.ui.checkBox_12,
            self.ui.checkBox_13,
            self.ui.checkBox_14,
            self.ui.checkBox_15,
        ]
        self.physique_widget_list = [
            self.ui.checkBox_16,
            self.ui.checkBox_17,
            self.ui.checkBox_18,
            self.ui.checkBox_19,
            self.ui.checkBox_1a,
            self.ui.checkBox_1b,
            self.ui.checkBox_1c,
        ]
        self.smell_widget_list = [
            self.ui.checkBox_21,
            self.ui.checkBox_22,
            self.ui.checkBox_23,
        ]
        self.voice_widget_list = [
            self.ui.checkBox_24,
            self.ui.checkBox_25,
            self.ui.checkBox_26,
            self.ui.checkBox_27,
            self.ui.checkBox_28,
            self.ui.checkBox_29,
        ]
        self.emotion_widget_list = [
            self.ui.checkBox_31,
            self.ui.checkBox_32,
            self.ui.checkBox_33,
            self.ui.checkBox_34,
            self.ui.checkBox_35,
            self.ui.checkBox_36,
            self.ui.checkBox_37,
            self.ui.checkBox_38,
            self.ui.checkBox_39,
            self.ui.checkBox_40,
        ]
        self.sleep_widget_list = [
            self.ui.checkBox_41,
            self.ui.checkBox_42,
            self.ui.checkBox_43,
            self.ui.checkBox_44,
            self.ui.checkBox_45,
            self.ui.checkBox_46,
            self.ui.checkBox_47,
            self.ui.checkBox_48,
            self.ui.checkBox_49,
        ]
        self.face_widget_list = [
            self.ui.checkBox_50,
            self.ui.checkBox_51,
        ]
        self.chest_widget_list = [
            self.ui.checkBox_52,
            self.ui.checkBox_53,
            self.ui.checkBox_54,
            self.ui.checkBox_55,
            self.ui.checkBox_56,
            self.ui.checkBox_57,
            self.ui.checkBox_58,
            self.ui.checkBox_59,
        ]
        self.belly_widget_list = [
            self.ui.checkBox_201,
            self.ui.checkBox_202,
            self.ui.checkBox_203,
            self.ui.checkBox_204,
            self.ui.checkBox_205,
            self.ui.checkBox_206,
            self.ui.checkBox_207,
            self.ui.checkBox_208,
            self.ui.checkBox_209,
            self.ui.checkBox_210,
            self.ui.checkBox_211,
            self.ui.checkBox_212,
            self.ui.checkBox_213,
            self.ui.checkBox_214,
            self.ui.checkBox_215,
            self.ui.checkBox_216,
            self.ui.checkBox_217,
        ]
        self.excretion_widget_list = [
            self.ui.checkBox_151,
            self.ui.checkBox_152,
            self.ui.checkBox_153,
            self.ui.checkBox_154,
            self.ui.checkBox_155,
            self.ui.checkBox_156,
            self.ui.checkBox_157,
            self.ui.checkBox_158,
            self.ui.checkBox_159,
            self.ui.checkBox_160,
            self.ui.checkBox_161,
            self.ui.checkBox_162,
            self.ui.checkBox_163,
            self.ui.checkBox_164,
            self.ui.checkBox_165,
        ]
        self.back_widget_list = [
            self.ui.checkBox_301,
            self.ui.checkBox_302,
            self.ui.checkBox_303,
            self.ui.checkBox_304,
            self.ui.checkBox_305,
            self.ui.checkBox_306,
            self.ui.checkBox_307,
            self.ui.checkBox_308,
            self.ui.checkBox_309,
        ]
        self.limbs_widget_list = [
            self.ui.checkBox_331,
            self.ui.checkBox_332,
            self.ui.checkBox_333,
            self.ui.checkBox_334,
            self.ui.checkBox_335,
            self.ui.checkBox_336,
            self.ui.checkBox_337,
            self.ui.checkBox_338,
            self.ui.checkBox_339,
            self.ui.checkBox_340,
            self.ui.checkBox_341,
            self.ui.checkBox_342,
        ]

        self.all_widget_list = (
           self.past_history_widget_list +
           self.diet_widget_list +
           self.allergy_widget_list +
           self.smoke_widget_list +
           self.alcohol_widget_list +
           self.family_widget_list +
           self.consciousness_widget_list +
           self.physique_widget_list +
           self.smell_widget_list +
           self.voice_widget_list +
           self.emotion_widget_list +
           self.sleep_widget_list +
           self.face_widget_list +
           self.chest_widget_list +
           self.belly_widget_list +
           self.excretion_widget_list +
           self.back_widget_list +
           self.limbs_widget_list
        )

    # *********************** 讀檔 *************************
    def _read_patient_new_care(self):
        if self.patient_key is None:
            return

        sql = f'''
            SELECT Value FROM patient_new_care
            WHERE
                PatientKey = {self.patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self.ui.label_empty_chart.hide()

        self._read_symptom()
        self._read_current_history()
        self._read_past_history()
        self._read_personal_history()
        self._read_family_history()
        self._read_physical_exam()
        self._read_chinese_diagnostic()
        self._read_diagnostic()
        self._read_self_care()
        self._read_diet_instruction()

    def _read_symptom(self):
        self._set_line_edit(self.ui.lineEdit_symptom, '主訴')

    def _read_current_history(self):
        self._set_line_edit(self.ui.lineEdit_current_history, '現病史')

    def _read_past_history(self):
        self._set_check_box(self.past_history_widget_list, '過去病史')
        self._set_line_edit(self.ui.lineEdit_other_past_history, '其他傷病史')

    def _read_personal_history(self):
        self._set_check_box(self.diet_widget_list, '飲食習慣')
        self._set_check_box(self.allergy_widget_list, '過敏')
        self._set_check_box(self.smoke_widget_list, '抽煙')
        self._set_check_box(self.alcohol_widget_list, '喝酒')
        self._set_line_edit(self.ui.lineEdit_allergy_drug, '過敏藥物')
        self._set_line_edit(self.ui.lineEdit_allergy_food, '過敏食物')
        self._set_line_edit(self.ui.lineEdit_smoke_freq, '抽煙頻率')
        self._set_line_edit(self.ui.lineEdit_alcohol_freq, '喝酒頻率')
        self._set_line_edit(self.ui.lineEdit_alcohol, '酒類')

    def _read_family_history(self):
        self._set_check_box(self.family_widget_list, '家族病史')
        self._set_line_edit(self.ui.lineEdit_cancer, '癌症')
        self._set_line_edit(self.ui.lineEdit_other_family_history, '其他家族病史')

    def _read_physical_exam(self):
        self._set_line_edit(self.ui.lineEdit_bph, '收縮壓')
        self._set_line_edit(self.ui.lineEdit_bpl, '舒張壓')
        self._set_line_edit(self.ui.lineEdit_pulse_freq, '脈搏')
        self._set_line_edit(self.ui.lineEdit_temperature, '體溫')
        self._set_line_edit(self.ui.lineEdit_physical_exam, '理學檢查')
        self._set_line_edit(self.ui.lineEdit_lab_exam, '實驗室數據')
        self._set_line_edit(self.ui.lineEdit_exam_descript, '其他補充說明')

    def _read_chinese_diagnostic(self):
        self._read_look()
        self._read_smell()
        self._read_query()
        self._read_touch()

    def _read_look(self):
        self._set_check_box(self.consciousness_widget_list, '意識')
        self._set_check_box(self.physique_widget_list, '體格')
        self._set_line_edit(self.ui.lineEdit_tongue, '舌診')

    def _read_smell(self):
        self._set_check_box(self.smell_widget_list, '氣味')
        self._set_check_box(self.voice_widget_list, '聲音')
        self._set_line_edit(self.ui.lineEdit_smell, '特殊氣味')
        self._set_line_edit(self.ui.lineEdit_voice, '其他聲音')

    def _read_query(self):
        self._set_check_box(self.emotion_widget_list, '情志')
        self._set_line_edit(self.ui.lineEdit_emotion, '其他情志')

        self._set_check_box(self.sleep_widget_list, '睡眠')
        self._set_line_edit(self.ui.lineEdit_sleep, '其他睡眠')

        self._set_check_box(self.face_widget_list, '五官')
        self._set_line_edit(self.ui.lineEdit_face, '其他五官')

        self._set_check_box(self.chest_widget_list, '胸部')
        self._set_line_edit(self.ui.lineEdit_chest, '胸部部位')
        self._set_line_edit(self.ui.lineEdit_cough_time, '咳嗽時間')
        self._set_line_edit(self.ui.lineEdit_cough_type, '咳嗽性質')
        self._set_line_edit(self.ui.lineEdit_sputum, '痰色')

        self._set_check_box(self.belly_widget_list, '腹部')
        self._set_line_edit(self.ui.lineEdit_belly, '腹部部位')
        self._set_line_edit(self.ui.lineEdit_defecate, '排便說明')
        self._set_check_box(self.excretion_widget_list, '二便')

        self._set_check_box(self.back_widget_list, '腰背')
        self._set_line_edit(self.ui.lineEdit_back, '其他腰背')

        self._set_check_box(self.limbs_widget_list, '四肢')
        self._set_line_edit(self.ui.lineEdit_limbs, '四肢部位')
        self._set_line_edit(self.ui.lineEdit_other_limbs, '其他四肢')

    def _read_touch(self):
        self._set_line_edit(self.ui.lineEdit_pulse, '脈象')

    def _read_diagnostic(self):
        self._set_line_edit(self.ui.lineEdit_diagnostic, '診斷')

    def _read_self_care(self):
        self._set_line_edit(self.ui.lineEdit_self_care, '自我照護')

    def _read_diet_instruction(self):
        self._set_line_edit(self.ui.lineEdit_diet_instruction, '飲食指導')

    def _set_line_edit(self, line_edit, field_name):
        value = patient_utils.read_patient_new_care(self.database, self.patient_key, field_name)
        if value is not None:
            line_edit.setText(value)

    def _set_check_box(self, widget_list, field_name):
        for widget in widget_list:
            field = f'{field_name}-{widget.text()}'
            value = patient_utils.read_patient_new_care(self.database, self.patient_key, field)
            if value == '是':
                widget.setChecked(True)
                widget.setStyleSheet('color:darkred; font-weight:bold')

    # *********************** 存檔 *************************
    def save_patient_new_care(self, patient_key):
        self.patient_key = patient_key

        self.database.exec_sql(f'DELETE FROM patient_new_care WHERE PatientKey = {self.patient_key}')
        self._save_symptom()
        self._save_current_history()
        self._save_past_history()
        self._save_personal_history()
        self._save_family_history()
        self._save_physical_exam()
        self._save_chinese_diagnostic()
        self._save_diagnostic()
        self._save_self_care()
        self._save_diet_instruction()

    def _save_symptom(self):
        self._save_line_edit(self.ui.lineEdit_symptom, '主訴')

    def _save_current_history(self):
        self._save_line_edit(self.ui.lineEdit_current_history, '現病史')

    def _save_past_history(self):
        self._save_check_box(self.past_history_widget_list, '過去病史')
        self._save_line_edit(self.ui.lineEdit_other_past_history, '其他傷病史')

    def _save_personal_history(self):
        self._save_check_box(self.diet_widget_list, '飲食習慣')
        self._save_check_box(self.allergy_widget_list, '過敏')
        self._save_check_box(self.smoke_widget_list, '抽煙')
        self._save_check_box(self.alcohol_widget_list, '喝酒')

        self._save_line_edit(self.ui.lineEdit_allergy_drug, '過敏藥物')
        self._save_line_edit(self.ui.lineEdit_allergy_food, '過敏食物')
        self._save_line_edit(self.ui.lineEdit_smoke_freq, '抽煙頻率')
        self._save_line_edit(self.ui.lineEdit_alcohol_freq, '喝酒頻率')
        self._save_line_edit(self.ui.lineEdit_alcohol, '酒類')

    def _save_family_history(self):
        self._save_check_box(self.family_widget_list, '家族病史')
        self._save_line_edit(self.ui.lineEdit_cancer, '癌症')
        self._save_line_edit(self.ui.lineEdit_other_family_history, '其他家族病史')

    def _save_physical_exam(self):
        self._save_line_edit(self.ui.lineEdit_bph, '收縮壓')
        self._save_line_edit(self.ui.lineEdit_bpl, '舒張壓')
        self._save_line_edit(self.ui.lineEdit_pulse_freq, '脈搏')
        self._save_line_edit(self.ui.lineEdit_temperature, '體溫')
        self._save_line_edit(self.ui.lineEdit_physical_exam, '理學檢查')
        self._save_line_edit(self.ui.lineEdit_lab_exam, '實驗室數據')
        self._save_line_edit(self.ui.lineEdit_exam_descript, '其他補充說明')

    def _save_chinese_diagnostic(self):
        self._save_look()
        self._save_smell()
        self._save_query()
        self._save_touch()

    def _save_look(self):
        self._save_check_box(self.consciousness_widget_list, '意識')
        self._save_check_box(self.physique_widget_list, '體格')
        self._save_line_edit(self.ui.lineEdit_tongue, '舌診')

    def _save_smell(self):
        self._save_check_box(self.smell_widget_list, '氣味')
        self._save_check_box(self.voice_widget_list, '聲音')
        self._save_line_edit(self.ui.lineEdit_smell, '特殊氣味')
        self._save_line_edit(self.ui.lineEdit_voice, '其他聲音')

    def _save_query(self):
        self._save_check_box(self.emotion_widget_list, '情志')
        self._save_line_edit(self.ui.lineEdit_emotion, '其他情志')

        self._save_check_box(self.sleep_widget_list, '睡眠')
        self._save_line_edit(self.ui.lineEdit_sleep, '其他睡眠')

        self._save_check_box(self.face_widget_list, '五官')
        self._save_line_edit(self.ui.lineEdit_face, '其他五官')

        self._save_check_box(self.chest_widget_list, '胸部')
        self._save_line_edit(self.ui.lineEdit_chest, '胸部部位')
        self._save_line_edit(self.ui.lineEdit_cough_time, '咳嗽時間')
        self._save_line_edit(self.ui.lineEdit_cough_type, '咳嗽性質')
        self._save_line_edit(self.ui.lineEdit_sputum, '痰色')

        self._save_check_box(self.belly_widget_list, '腹部')
        self._save_line_edit(self.ui.lineEdit_belly, '腹部部位')
        self._save_line_edit(self.ui.lineEdit_defecate, '排便說明')
        self._save_check_box(self.excretion_widget_list, '二便')

        self._save_check_box(self.back_widget_list, '腰背')
        self._save_line_edit(self.ui.lineEdit_back, '其他腰背')

        self._save_check_box(self.limbs_widget_list, '四肢')
        self._save_line_edit(self.ui.lineEdit_limbs, '四肢部位')
        self._save_line_edit(self.ui.lineEdit_other_limbs, '其他四肢')

    def _save_touch(self):
        self._save_line_edit(self.ui.lineEdit_pulse, '脈象')

    def _save_diagnostic(self):
        self._save_line_edit(self.ui.lineEdit_diagnostic, '診斷')

    def _save_self_care(self):
        self._save_line_edit(self.ui.lineEdit_self_care, '自我照護')

    def _save_diet_instruction(self):
        self._save_line_edit(self.ui.lineEdit_diet_instruction, '飲食指導')

    def _save_line_edit(self, line_edit, field_name):
        value = string_utils.xstr(line_edit.text()[:200])
        if value != '':
            patient_utils.write_patient_new_care(self.database, self.patient_key, field_name, value)

    def _save_check_box(self, widget_list, field_name):
        for widget in widget_list:
            if widget.isChecked():
                field = f'{field_name}-{widget.text()}'
                patient_utils.write_patient_new_care(self.database, self.patient_key, field, '是')

    def _insert_field(self, field_name):
        tool_button_name = self.sender().objectName()
        if 'symptom' in tool_button_name:
            line_edit = self.ui.lineEdit_symptom
        elif 'tongue' in tool_button_name:
            line_edit = self.ui.lineEdit_tongue
        elif 'pulse' in tool_button_name:
            line_edit = self.ui.lineEdit_pulse
        elif 'diagnostic' in tool_button_name:
            line_edit = self.ui.lineEdit_diagnostic
        else:
            return

        sql = f'''
            SELECT {field_name} FROM cases
            WHERE
                PatientKey = {self.patient_key} AND
                {field_name} IS NOT NULL
            ORDER BY CaseDate LIMIT 1
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        line_edit.setText(string_utils.get_str(row[field_name], 'utf8'))
