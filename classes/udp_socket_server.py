
# -*- coding: UTF-8 -*-

import socket
from PyQt5 import QtCore


class UDPSocketServer(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, *args):
        super(UDPSocketServer, self).__init__(parent)
        self.parent = parent
        self.default_port = args[0]
        self.buffer_size = 1024
        self.socket_connected = False
        self.is_stop_thread = False
        self._init_socket_server()

    def __del__(self):
        self.server.close()
        # self.wait()

    def _init_socket_server(self):
        host = ''
        if self.default_port is not None:
            port = self.default_port
        else:
            port = 8881

        server_address = (host, port)
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.server.bind(server_address)
            self.socket_connected = True
        except OSError:
            pass
            # system_utils.show_message_box(
            #    QMessageBox.Critical,
            #    '驅動網路Socket失敗',
            #    '<h3>無法驅動網路Socket功能, 所有的廣播訊息將無法接收.</h3>',
            #    '請確定是否有其他的醫療系統正在使用中.'
            # )

    def connected(self):
        return self.socket_connected

    def stop_thread(self):
        self.is_stop_thread = True

    def run(self):
        data, client_address = None, None

        while True:
            if self.is_stop_thread:
                break

            try:
                data, client_address = self.server.recvfrom(self.buffer_size)
            except Exception:
                self.socket_connected = False
                self._init_socket_server()

            if data is not None:
                try:
                    self.update_signal.emit(str(data, 'utf-8'))
                except UnicodeDecodeError:
                    pass

                self.server.sendto(data, client_address)


class VoiceServer(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, *args):
        super(VoiceServer, self).__init__(parent)
        self.parent = parent
        self.default_port = args[0]
        self.buffer_size = 1024
        self.socket_connected = False
        self.is_stop_thread = False
        self._init_voice_server()

    def __del__(self):
        self.voice_server.close()
        self.wait()

    def _init_voice_server(self):
        host = ''
        if self.default_port is not None:
            port = self.default_port
        else:
            port = 9991

        server_address = (host, port)
        try:
            self.voice_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.voice_server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.voice_server.bind(server_address)
            self.voice_socket_connected = True
        except OSError:
            pass

    def connected(self):
        return self.socket_connected

    def stop_thread(self):
        self.is_stop_thread = True

    def run(self):
        data, client_address = None, None

        while True:
            if self.is_stop_thread:
                break

            try:
                data, client_address = self.voice_server.recvfrom(self.buffer_size)
            except Exception:
                self.socket_connected = False
                self._init_voice_server()

            if data is not None:
                try:
                    self.update_signal.emit(str(data, 'utf-8'))
                except UnicodeDecodeError:
                    pass

                self.voice_server.sendto(data, client_address)
