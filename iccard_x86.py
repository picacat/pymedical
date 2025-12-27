# -*- coding: UTF-8 -*-

import ctypes


# 健保ICD卡 2018.03.31
class ICCard:
    def __init__(self, com_port):
        self.cshis = ctypes.windll.LoadLibrary('cshis.dll')
        self.cshis.csOpenCom(com_port - 1)

    def __del__(self):
        self.cshis.csCloseCom()

    def get_basic_data(self):
        patient = ctypes.create_string_buffer(72)  # c: char *
        patient_len = ctypes.c_int()  # c: int *
        patient_len.value = len(patient)
        self.cshis.hisGetBasicData(patient, ctypes.byref(patient_len))

        basic_data = {
            'card_no': patient[:12].decode('big5').strip(),
            'name': patient[12:32].decode('big5').strip(),
            'patient_id': patient[32:42].decode('big5').strip(),
            'birthday': patient[42:49].decode('big5').strip(),
            'gender':  patient[49:50].decode('big5').strip(),
            'card_date': patient[50:57].decode('big5').strip(),
            'cancel_mark': patient[57:58].decode('big5').strip(),
            'emg_phone': patient[58:72].decode('big5').strip(),
        }

        return basic_data
