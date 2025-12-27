# 虛擬健保卡作業 2022.05.01

import json
from queue import Queue
from threading import Thread

import requests
from libs import (case_utils, cshis_utils, date_utils, nhi_utils, number_utils,
                  prescript_utils, string_utils, system_utils)
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox, QPushButton

VHC_URL = 'http://localhost:3033/'


# 虛擬健保卡 2022.05.01
class VHCCSHIS(QtWidgets.QDialog):
    def __init__(self, parent=None, *args):
        super(VHCCSHIS, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.qrcode = args[2]

        self.ic_card_type = '虛擬健保卡'
        self.basic_data = cshis_utils.BASIC_DATA
        self.treat_data = cshis_utils.TREAT_DATA
        self.treatment_data = cshis_utils.TREATMENT_DATA
        self.critical_illness_data = []
        self._set_qrcode()

    def _set_qrcode(self):
        if self.qrcode is None:
            self.qrcode = self._get_qrcode()

        if self.qrcode is None:
            return False

        if not self.upload_qrcode(self.qrcode):
            self.qrcode = None
            return False

        return True

    def _get_qrcode(self):
        qrcode = None

        system_utils.set_keyboard_layout('英文')
        qrcode, ok = QInputDialog.getText(
            self, '虛擬健保卡', '請讀取虛擬健保卡', QLineEdit.Normal, '')
        if not ok or qrcode == '':
            qrcode = None

        return qrcode

    def __del__(self):
        # self._close_com()
        pass

    def _post_data(self, url, command):
        headers = {'Content-Type': 'application/json'}
        json_data = json.dumps(command)

        response = requests.post(url=url, headers=headers, data=json_data)
        result = json.loads(response.content)

        return result

    def _open_com(self):
        url = VHC_URL + 'VHC/VHCcsOpenCom'
        command = {
        }

        result = self._post_data(url, command)

        error_code = int(result['ERRORCODE'])
        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '開啟虛擬健保卡讀卡機連接埠')
            return False

        return True

    def _close_com(self):
        url = VHC_URL + 'VHC/VHCcsCloseCom'
        command = {
        }

        result = self._post_data(url, command)

        error_code = int(result['ERRORCODE'])
        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '開啟虛擬健保卡讀卡機連接埠')
            return False

        return True

    def upload_qrcode(self, qrcode):
        # self._open_com()

        url = VHC_URL + 'QRCodeReader/uploadqrcode'
        command = {
            "QRCodeString": qrcode
        }

        result = self._post_data(url, command)

        error_code = int(result['ERRORCODE'])
        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '讀取虛擬健保卡QR Code')
            return False

        return True

    def _get_error_code(self, result):
        try:
            error_code = int(result['ERRORCODE'])
        except Exception:
            try:
                error_code = int(result['errorCode'])
            except Exception:
                error_code = int(result['statusCode'])

        return error_code

    def read_basic_data(self):
        if self.qrcode is None:
            return False

        url = VHC_URL + 'VHC/VHChisGetBasicData'
        command = {
        }
        result = self._post_data(url, command)
        error_code = self._get_error_code(result)

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '讀取虛擬健保卡資料')
            return False

        buffer = result['pBuffer']
        pbuffer = bytes(buffer, 'big5')
        self.basic_data = cshis_utils.decode_basic_data(pbuffer)

        return True

    def read_register_basic_data(self):
        if self.qrcode is None:
            return False

        url = VHC_URL + 'VHC/VHChisGetRegisterBasic'
        command = {
        }
        result = self._post_data(url, command)
        error_code = self._get_error_code(result)

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '讀取虛擬健保資料')
            return False

        buffer = result['pBuffer']
        pbuffer = bytes(buffer, 'big5')
        self.basic_data = cshis_utils.decode_register_basic_data(pbuffer)

        return True

    def get_seq_number_256(self, treat_item, baby_treat, treat_after_check):
        url = VHC_URL + 'VHC/VHChisGetSeqNumber256N1'
        
        command = {
            "cTreatItem": treat_item + ' ',
            "cBabyTreat": baby_treat + ' ',
            "cTreatAfterCheck": treat_after_check,
        }
        result = self._post_data(url, command)

        error_code = self._get_error_code(result)
        if error_code not in [0, 5010, 5174]:
            cshis_utils.show_ic_card_message(error_code, '取得虛擬健保卡就醫序號')
            return False

        buffer = result['pBuffer']
        pbuffer = bytes(buffer, 'ascii')

        self.treat_data = cshis_utils.decode_treat_data(pbuffer)

        return True

    def return_seq_number(self, treat_date):
        url = VHC_URL + 'VHC/VHCcsUnGetSeqNumber'
        command = {
            "pUnTreatDate": treat_date + ' '
        }
        result = self._post_data(url, command)

        error_code = self._get_error_code(result)

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '虛擬健保卡退掛')
            return False

        return True

    def write_ic_card(self, write_type, patient_key, course, share_type, treat_after_check=None, treat_type=None):
        if self.qrcode is None:
            return False

        treat_item = cshis_utils.get_treat_item(course, share_type)
        if write_type in ['全部', '掛號寫卡']:
            if not self.get_seq_number_256(treat_item, ' ', treat_after_check):
                return False

        return self

    def insert_correct_ic_card(self, patient_key):
        if not self.read_basic_data():
            return False

        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('病患資料有誤')
            msg_box.setText(
                f'''
                    <font size="5" color="red">
                        <b>找不到病歷號{patient_key}, 請重新插卡.</b>
                    </font>
                '''
            )
            msg_box.setInformativeText("請確定插入的健保卡是否為此病患所有.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()

            return False

        row = rows[0]
        patient_id = string_utils.xstr(row['ID'])
        patient_name = string_utils.xstr(row['Name'])
        if patient_id != '' and patient_id != self.basic_data['patient_id']:
            ic_card_name = self.basic_data['name']
            ic_card_id = self.basic_data['patient_id']
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle('健保卡身分不符')
            msg_box.setText(f'''
                <font size="5" color="red">
                    <b>此健保卡基本資料為<br>
                </font>
                <font size="5" color="blue">
                  {ic_card_name}: {ic_card_id}<br>
                </font>
                <font size="5" color="red">
                  與現行掛號病患<br>
                </font>
                <font size="5" color="blue">
                  {patient_name}: {patient_id}<br>
                </font>
                <font size="5" color="red">
                  身分證號不相符, 請檢查是否插入錯誤的健保卡.</b>
                </font>
            ''')
            msg_box.setInformativeText("請確定插入的健保卡是否為此病患所有.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return False

        if patient_id == '':
            sql = f'''
                UPDATE patient
                SET
                    ID = "{patient_id}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        if string_utils.xstr(row['CardNo']) == '':
            card_no = self.basic_data['card_no']
            sql = f'''
                UPDATE patient
                SET
                    CardNo = "{card_no}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        if row['Birthday'] != self.basic_data['birthday']:
            birthday = self.basic_data['birthday']
            sql = f'''
                UPDATE patient
                SET
                    Birthday = "{birthday}"
                WHERE
                    PatientKey = {patient_key}
            '''
            self.database.exec_sql(sql)

        return True

    # ic 醫令寫卡
    def write_ic_medical_record(self, case_key, treat_after_check):
        if self.qrcode is None:
            return False

        doctor_id = self.write_ic_treatment(case_key, treat_after_check)  # 寫入病名, 費用
        if doctor_id is None:
            return

        if not self.write_prescript_signature(case_key):  # 寫入醫令簽章
            return

        case_utils.update_xml(
            self.database, 'cases', 'Security', 'prescript_sign_time',
            date_utils.now_to_str(), 'CaseKey', case_key
        )  # 更新健保寫卡資料

    def rewrite_ic_prescript(self, case_key):
        if self.qrcode is None:
            return False

        if not self.write_prescript_signature(case_key):  # 寫入醫令簽章
            return

        case_utils.update_xml(
            self.database, 'cases', 'Security', 'prescript_sign_time',
            date_utils.now_to_str(), 'CaseKey', case_key
        )  # 更新健保寫卡資料

    # 寫入病名及費用
    def write_ic_treatment(self, case_key, treat_after_check):
        sql = f'''
            SELECT
                PatientKey, DiseaseCode1, DiseaseCode2, DiseaseCode3, DiseaseCode4,
                DiagShareFee, DrugShareFee, InsTotalFee, Security
            FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        case_row = self.database.select_record(sql)[0]
        patient_key = case_row['PatientKey']

        sql = f'''
            SELECT ID, Birthday FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        patient_row = self.database.select_record(sql)[0]

        ic_card_time = case_utils.extract_security_xml(case_row['Security'], '寫卡時間')
        reg_datetime = date_utils.west_datetime_to_nhi_datetime(ic_card_time)
        patient_id = string_utils.xstr(patient_row['ID'])
        patient_birthday = string_utils.xstr(patient_row['Birthday'])

        if patient_id == '' or patient_birthday == '':
            patient_id, patient_birthday = self._update_patient(patient_key)

        birthday_nhi_datetime = date_utils.west_date_to_nhi_date(patient_birthday)

        disease_code1 = string_utils.xstr(case_row['DiseaseCode1'])
        disease_code2 = string_utils.xstr(case_row['DiseaseCode2'])
        disease_code3 = string_utils.xstr(case_row['DiseaseCode3'])
        disease_code4 = string_utils.xstr(case_row['DiseaseCode4'])

        disease_code1 = f'{disease_code1:<7}'
        disease_code2 = f'{disease_code2:<7}'
        disease_code3 = f'{disease_code3:<7}'
        disease_code4 = f'{disease_code4:<7}'
        filler = ' ' * 7
        data_write = f'{treat_after_check}{disease_code1}{disease_code2}{disease_code3}{disease_code4}{filler}{filler}'

        doctor_id = self.write_treatment_code(
            reg_datetime, patient_id, birthday_nhi_datetime, data_write
        )
        if doctor_id is None:
            return doctor_id

        ins_total_fee = string_utils.xstr(case_row['InsTotalFee'])
        share_fee = string_utils.xstr(
            (number_utils.get_integer(case_row['DiagShareFee']) +
             number_utils.get_integer(case_row['DrugShareFee']))
        )

        ins_total_fee = f'{ins_total_fee:0>8}'
        share_fee = f'{share_fee:0>8}'
        hospital_fee = '0' * 8
        hospital_share_fee1 = '0' * 7
        hospital_share_fee2 = '0' * 7
        data_write = f'{ins_total_fee}{share_fee}{hospital_fee}{hospital_share_fee1}{hospital_share_fee2}'

        self.write_treatment_fee(reg_datetime, patient_id, birthday_nhi_datetime, data_write)

        return doctor_id

    def write_treatment_code_thread(
            self, out_queue, registration_datetime, patient_id, patient_birthday, data_write):
        url = VHC_URL + 'VHC/VHChisWriteTreatmentCode'

        command = {
            "pDateTime": registration_datetime + ' ',
            "pPatientID": patient_id + ' ',
            "pPatientBirthDate": patient_birthday + ' ',
            "pDataWrite": data_write + ' ',
        }
        result = self._post_data(url, command)
        error_code = self._get_error_code(result)

        if error_code != 0:
            doctor_id = None
        else:
            doctor_id = result['pBufferDocID']

        out_queue.put((error_code, doctor_id))

    # 就醫診療資料寫入作業
    def write_treatment_code(self, registration_datetime, patient_id, patient_birthday, data_write):
        title = '寫入診察資料'
        message = '<font size="5" color="red"><b>健保讀卡機正在寫入診察資料中, 請稍後...</b></font>'
        hint = '正在與與健保IDC資訊中心連線, 會花費一些時間.'
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(target=self.write_treatment_code_thread,
                   args=(msg_queue, registration_datetime, patient_id, patient_birthday, data_write,))
        t.start()
        (error_code, out_doctor_id) = msg_queue.get()
        msg_box.close()

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '虛擬健保卡寫入診察資料')
            return None

        doctor_id = out_doctor_id.strip()

        return doctor_id

    def write_treatment_fee_thread(
            self, out_queue, registration_datetime, patient_id, patient_birthday, data_write):
        url = VHC_URL + 'VHC/VHChisWriteTreatmentFee'
        command = {
            "pDateTime": registration_datetime + ' ',
            "pPatientID": patient_id + ' ',
            "pPatientBirthDate": patient_birthday + ' ',
            "pDataWrite": data_write + ' ',
        }
        result = self._post_data(url, command)
        error_code = self._get_error_code(result)

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '虛擬健保卡資料寫入作業')
            return False

        out_queue.put(error_code)

    # 就醫費用資料寫入作業
    def write_treatment_fee(self, registration_datetime, patient_id, patient_birthday, data_write):
        title = '寫入診察費用資料'
        message = '<font size="5" color="red"><b>健保讀卡機正在寫入診察費用資料中, 請稍後...</b></font>'
        hint = '正在與與健保IDC資訊中心連線, 會花費一些時間.'
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(target=self.write_treatment_fee_thread,
                   args=(msg_queue, registration_datetime, patient_id, patient_birthday, data_write,))
        t.start()
        error_code = msg_queue.get()
        msg_box.close()

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '健保卡寫入診察費用資料')
            return None

        return True

    # 寫入處方簽章
    def write_prescript_signature(self, case_key):
        sql = f'''
            SELECT CaseKey, PatientKey, Treatment, Security FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        case_row = self.database.select_record(sql)[0]

        sql = f'''
            SELECT * FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1
        '''
        rows = self.database.select_record(sql)
        dosage_row = rows[0] if len(rows) > 0 else None

        patient_key = case_row['PatientKey']
        sql = f'''
            SELECT ID, Birthday FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        patient_row = self.database.select_record(sql)[0]

        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1 AND
                InsCode IS NOT NULL
        '''
        prescript_rows = self.database.select_record(sql)

        if string_utils.xstr(case_row['Treatment']) in nhi_utils.INS_TREAT:
            if not self.write_treat_signature(case_row, dosage_row, patient_row):
                return False

        if len(prescript_rows) > 0:
            if not self.write_medicine_signature(case_row, patient_row, prescript_rows, dosage_row):
                return False

        return True

    # 寫入處置處方簽章
    def write_treat_signature(self, case_row, dosage_row, patient_row):
        ic_card_time = case_utils.extract_security_xml(case_row['Security'], '寫卡時間')
        reg_datetime = date_utils.west_datetime_to_nhi_datetime(ic_card_time)  # 就診日期時間 13 bytes: EEEmmddHHMMSS
        patient_id = string_utils.xstr(patient_row['ID'])
        patient_birthday = string_utils.xstr(patient_row['Birthday'])
        birthday_nhi_datetime = date_utils.west_date_to_nhi_date(patient_birthday)

        treat_code = nhi_utils.get_treat_code(
            self.database, case_row['CaseKey']
        )
        usage = ''  # 處置免填
        days = 0
        total_dosage = 1

        order_type = '3'                        # 醫令類別 1 bytes: 1-非長期藥品 2-長期藥品 3-診療 4-特殊材料
        treat_code = f'{treat_code:<12}'        # 診療項目代號 12 bytes
        treat_position = ' ' * 6                # 診療部位 6 bytes
        usage = f'{usage:<18}'                  # 用法 18 bytes
        days = f'{days:0>2}'                    # 天數 2 bytes: 00
        total_dosage = f'{total_dosage:0>7}'    # 總量 7 bytes: 00000.0
        deliver = '03'                          # 交付處方註記 2 bytes: 01-自行調劑 02-交付調劑 03-自行執行

        data_write = f'{reg_datetime}{order_type}{treat_code}{treat_position}{usage}{days}{total_dosage}{deliver}'

        treat_sign = self.write_treat_sign(reg_datetime, patient_id, birthday_nhi_datetime, data_write)
        if treat_sign is None:
            return

        case_key = case_row['CaseKey']
        self.database.exec_sql(f'''
            DELETE FROM presextend
            WHERE
                PrescriptKey = {case_key} AND
                ExtendType = "處置簽章"
        ''')
        fields = [
            'PrescriptKey', 'ExtendType', 'Content',
        ]
        data = [
            case_row['CaseKey'], '處置簽章', treat_sign,
        ]
        self.database.insert_record('presextend', fields, data)

        return True

    def write_treat_sign_thread(
            self, out_queue, registration_datetime, patient_id, patient_birthday, data_write):
        url = VHC_URL + 'VHC/VHChisWritePrescriptionSign'

        command = {
            "pDateTime": registration_datetime + ' ',
            "pPatientID": patient_id + ' ',
            "pPatientBirthDate": patient_birthday + ' ',
            "pDataWrite": data_write,
        }
        result = self._post_data(url, command)
        error_code = self._get_error_code(result)

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '虛擬健保卡處方箋寫入作業')
            return False

        if error_code != 0:
            pBuffer = None
        else:
            pBuffer = result['pBuffer']

        out_queue.put((error_code, pBuffer))

    def write_treat_sign(self, registration_datetime, patient_id, patient_birthday, data_write):
        title = '取得處置簽章'
        message = '<font size="5" color="red"><b>健保讀卡機取得處置簽章中, 請稍後...</b></font>'
        hint = '正在與與健保IDC資訊中心連線, 會花費一些時間.'
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(target=self.write_treat_sign_thread,
                   args=(msg_queue, registration_datetime, patient_id, patient_birthday, data_write, ))
        t.start()
        (error_code, buffer) = msg_queue.get()
        msg_box.close()

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '虛擬健保卡處方箋寫入作業')
            treat_sign = None
        else:
            treat_sign = buffer

        return treat_sign

    # 寫入藥品處方簽章
    def write_medicine_signature(self, case_row, patient_row, prescript_rows, dosage_row):
        ic_card_time = case_utils.extract_security_xml(case_row['Security'], '寫卡時間')
        reg_datetime = date_utils.west_datetime_to_nhi_datetime(ic_card_time)  # 就診日期時間 13 bytes: EEEmmddHHMMSS
        patient_id = string_utils.xstr(patient_row['ID'])
        patient_birthday = string_utils.xstr(patient_row['Birthday'])
        birthday_nhi_datetime = date_utils.west_date_to_nhi_date(patient_birthday)

        try:
            usage = (prescript_utils.get_usage_code(dosage_row['Packages']) +
                     prescript_utils.get_instruction_code(dosage_row['Instruction']))
        except Exception:
            usage = ''

        days = number_utils.get_integer(dosage_row['Days'])

        data_write = ''
        for row in prescript_rows:
            try:
                total_dosage = row['Dosage'] * dosage_row['Days']
            except TypeError:
                total_dosage = 0

            order_type = '1'                                    # 醫令類別 1 bytes: 1-非長期藥品 2-長期藥品 3-診療 4-特殊材料
            ins_code = f'{row["InsCode"]:<12}'                  # 診療項目代號 12 bytes
            treat_position = ' ' * 6                            # 診療部位 6 bytes
            usage = f'{usage:<18}'                              # 用法 18 bytes
            days = f'{days:0>2}'                                # 天數 2 bytes: 00
            total_dosage = f'{total_dosage:0>7.1f}'             # 總量 7 bytes: 00000.0
            deliver = '01'                                      # 交付處方註記 2 bytes: 01-自行調劑 02-交付調劑 03-自行執行

            data_write += f'{reg_datetime}{order_type}{ins_code}{treat_position}{usage}{days}{total_dosage}{deliver}'

        prescript_sign_list = self.write_multi_prescript_sign(
            reg_datetime, patient_id, birthday_nhi_datetime, data_write, len(prescript_rows)
        )
        if prescript_sign_list is None:
            return False

        for row, prescript_sign in zip(prescript_rows, prescript_sign_list):
            prescript_key = row['PrescriptKey']
            sql = f'''
                DELETE FROM presextend
                WHERE
                    PrescriptKey = {prescript_key} AND
                    ExtendType = "處方簽章"
            '''
            self.database.exec_sql(sql)
            fields = [
                'PrescriptKey', 'ExtendType', 'Content',
            ]
            data = [
                row['PrescriptKey'], '處方簽章', prescript_sign,
            ]
            self.database.insert_record('presextend', fields, data)

        return True

    def write_multi_prescript_sign_thread(
            self, out_queue, registration_datetime, patient_id, patient_birthday, data_write, write_count):
        url = VHC_URL + 'VHC/VHChisWriteMultiPrescriptSign'

        command = {
            "pDateTime": registration_datetime + ' ',
            "pPatientID": patient_id + ' ',
            "pPatientBirthDate": patient_birthday + ' ',
            "pDataWrite": data_write,
        }
        result = self._post_data(url, command)
        error_code = self._get_error_code(result)

        if error_code != 0:
            pBuffer = None
        else:
            pBuffer = result['pBuffer']

        out_queue.put((error_code, pBuffer))

    def write_multi_prescript_sign(self, registration_datetime, patient_id, patient_birthday,
                                   data_write, write_count):
        title = '取得處方簽章'
        message = '<font size="5" color="red"><b>健保讀卡機取得處方簽章中, 請稍後...</b></font>'
        hint = '正在與與健保IDC資訊中心連線, 會花費一些時間.'
        msg_box = self._message_box(title, message, hint)
        msg_box.show()
        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(target=self.write_multi_prescript_sign_thread,
                   args=(msg_queue, registration_datetime, patient_id, patient_birthday, data_write, write_count,))
        t.start()
        (error_code, buffer) = msg_queue.get()
        msg_box.close()

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '虛擬健保卡處方箋寫入作業')
            prescript_sign_list = None
        else:
            chunks, chunk_size = len(buffer), 40
            prescript_sign_list = [buffer[i:i + chunk_size] for i in range(0, chunks, chunk_size)]

        return prescript_sign_list

    @staticmethod
    def _message_box(title, message, hint):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setInformativeText(hint)
        msg_box.setStandardButtons(QMessageBox.NoButton)

        return msg_box

    def do_thread(self, nhi_thread, *args):
        msg_box = None
        try:
            operation = args[0]
        except IndexError:
            operation = None

        try:
            show_warning = args[3]
        except Exception:
            show_warning = True

        if operation:
            msg_box = self._message_box('健保讀卡機作業', args[1], args[2])
            msg_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()
        t = Thread(target=nhi_thread, args=(msg_queue,))
        t.start()
        error_code = msg_queue.get()
        if msg_box:
            msg_box.close()

        if error_code != 0 or show_warning:
            cshis_utils.show_ic_card_message(error_code, operation)

        return error_code

    def gen_cloud_medical_token(self):
        if self.qrcode is None:
            return False

        url = VHC_URL + 'VHC/GenCloudMedicalToken'
        command = {
        }
        result = self._post_data(url, command)
        error_code = self._get_error_code(result)

        if error_code != 0:
            cshis_utils.show_ic_card_message(error_code, '讀取雲端藥歷')
            return False

        return True
