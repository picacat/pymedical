# -*- coding: UTF-8 -*-
# 讀卡機應用 2024.06.25 掛號機用

from PyQt5 import QtCore

from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.System import readers


class ICCard:
    def __init__(self, basic_data=None):
        self.basic_data = basic_data or {}

    def set_basic_data(self, data):
        self.basic_data = data

    def set_patient_id(self, patient_id):
        self.basic_data['patient_id'] = patient_id


# 讀卡機觀察者
class SmartCardObserver(CardObserver, QtCore.QObject):
    card_inserted = QtCore.pyqtSignal('QString')
    card_removed = QtCore.pyqtSignal('QString')

    SelectAPDU = [
            0x00, 0xA4, 0x04, 0x00, 0x10, 0xD1, 0x58, 0x00,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x11, 0x00]
    ReadProfileAPDU = [0x00, 0xca, 0x11, 0x00, 0x02, 0x00, 0x00]

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        CardObserver.__init__(self)
        self.card_monitor = CardMonitor()
        self.card_monitor.addObserver(self)
        self.card_removed_flag = False

    def stop(self):
        """停止監聽讀卡機"""
        try:
            if self.card_monitor is not None:
                self.card_monitor.deleteObserver(self)
        except Exception:
            pass

    def _read_nhi_card(self):
        reader = readers()[0]

        connection = reader.createConnection()
        connection.connect()
        data, sw1, sw2 = connection.transmit(self.SelectAPDU)
        data, sw1, sw2 = connection.transmit(self.ReadProfileAPDU)

        card_number = ''.join(chr(i) for i in data[0:12])
        name = f'{bytes(data[12:32]).decode("big5")}'
        name = name.strip()
        uid = ''.join(chr(i) for i in data[32:42])
        birthday = ''.join(chr(i) for i in data[42:49])
        gender = ''.join(chr(i) for i in data[49:50])
        card_date = ''.join(chr(i) for i in data[50:57])

        return card_number, name, uid, birthday, gender, card_date

    def update(self, observable, actions):
        (added_cards, removed_cards) = actions
        for _ in added_cards:  # card inserted
            self.card_inserted.emit('card_inserted')

        if removed_cards and not self.card_removed_flag:  # card removed
            self.card_removed_flag = True
            self.card_removed.emit('card_removed')

    def check_initial_card(self):
        """
        啟動監聽後，主動檢查目前讀卡機裡是不是已經有卡。
        若有 → 直接發出 card_inserted signal。
        """
        basic_data = self.get_nhi_basic_data()
        if basic_data:
            # 有讀到卡 → 代表現在就有卡插著
            self.card_removed_flag = False
            self.card_inserted.emit('card_inserted')

    def get_nhi_basic_data(self):
        try:
            card_number, name, uid, birthday, gender, card_date = self._read_nhi_card()
            basic_data = {
                'card_number': card_number,
                'name': name,
                'patient_id': uid,
                'birthday': birthday,
                'gender': gender,
                'card_date': card_date,
            }
        except Exception:
            basic_data = None

        return basic_data
