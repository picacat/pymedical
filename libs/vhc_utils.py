# -*- coding: UTF-8 -*-
# 虛擬健保卡整合視訊門診api
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtCore

import json
import requests
import datetime

from threading import Thread
from queue import Queue

VHC_URL = 'https://vhcapp.nhi.gov.tw/vhc/cloud/tlm/'


def _get_rocid(clinic_id, patient_id):
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    import base64

    current_date = datetime.datetime.now().strftime('%Y%m%d')
    iv_date = datetime.datetime.now().strftime('%y%m%d')
    key = clinic_id + current_date + '0' * 14
    iv = clinic_id + iv_date
    cipher = AES.new(key=key.encode(), mode=AES.MODE_CBC, iv=iv.encode())
    rocid = cipher.encrypt(pad(patient_id.encode(), AES.block_size))

    return base64.b64encode(rocid)


def _post_data(url, command):
    headers = {'Content-Type': 'application/json'}
    json_data = json.dumps(command)

    response = requests.post(url=url, headers=headers, data=json_data)
    result = json.loads(response.content)

    return result


def _get_req_code_thread(out_queue, system_settings, patient_id):
    url = VHC_URL + 'GetVHCTeleMedicineReqCode'
    clinic_id = system_settings.field('院所代號')
    token = system_settings.field('虛擬健保卡授權憑證')
    rocid = _get_rocid(clinic_id, patient_id).decode()
    command = {
        "HospID": clinic_id,
        "sToken": token,
        "ROCID": rocid,
    }
    result = _post_data(url, command)
    response_body = result['responseBody']
    error_code = int(response_body['ErrorCode'])
    req_code = response_body['ReqCode']

    out_queue.put((error_code, req_code))


def get_vhc_req_code(system_settings, patient_id):
    title = '請求授權就醫序號'
    message = '<font size="5" color="red"><b>請求虛擬健保卡授權中, 請稍後...</b></font>'
    hint = '正在與與健保IDC資訊中心連線, 會花費一些時間.'
    msg_box = message_box(title, message, hint)
    msg_box.show()
    msg_queue = Queue()
    QtCore.QCoreApplication.processEvents()
    t = Thread(target=_get_req_code_thread, args=(msg_queue, system_settings, patient_id,))
    t.start()
    (error_code, req_code) = msg_queue.get()
    msg_box.close()

    if error_code != 0:
        req_code = 'error'

    return req_code


def message_box(title, message, hint):
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setInformativeText(hint)
    msg_box.setStandardButtons(QMessageBox.NoButton)

    return msg_box


def _get_qrcode_thread(out_queue, system_settings, patient_id, req_code):
    url = VHC_URL + 'getQRCodeByVHCTLMRReqCode'
    clinic_id = system_settings.field('院所代號')
    token = system_settings.field('虛擬健保卡授權憑證')
    rocid = _get_rocid(clinic_id, patient_id).decode()
    command = {
        "HospID": clinic_id,
        "sToken": token,
        "ROCID": rocid,
        "ReqCode": req_code,
    }
    result = _post_data(url, command)
    response_body = result['responseBody']
    error_code = int(response_body['ErrorCode'])
    qrcode = response_body['QRCode']
    message = response_body['message']

    out_queue.put((qrcode, error_code, message))


def get_vhc_qrcode(system_settings, patient_id, req_code):
    title = '請求就醫序號'
    message = '<font size="5" color="red"><b>請求虛擬健保卡QR Code中, 請稍後...</b></font>'
    hint = '正在與與健保IDC資訊中心連線, 會花費一些時間.'
    msg_box = message_box(title, message, hint)
    msg_box.show()
    msg_queue = Queue()
    QtCore.QCoreApplication.processEvents()
    t = Thread(target=_get_qrcode_thread, args=(msg_queue, system_settings, patient_id, req_code,))
    t.start()
    (qrcode, error_code, message) = msg_queue.get()
    msg_box.close()

    return qrcode, error_code, message


def get_vhc_req_code_from_wait(database, wait_key):
    if wait_key in ['', None]:
        return None

    sql = f'''
        SELECT VHCReqCode FROM wait
        WHERE
            WaitKey = {wait_key}
    '''
    rows = database.select_record(sql)
    if len(rows) <= 0:
        return None

    row = rows[0]
    req_code = row['VHCReqCode']

    return req_code
