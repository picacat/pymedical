
import socket


# 要開啟防火牆 8880, 8881, 9990, 9991
class UDPSocketClient:
    def __init__(self, parent=None):
        # super(UDPSocketClient, database).__init__(parent)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.buffer_size = 1024
        self._init_socket_client()

    def _init_socket_client(self):
        host = '255.255.255.255'
        port = 8881
        self.server_address = (host, port)
        self.server_address2 = (host, 8880)  # pybulletin 使用

    def send_data(self, data):
        try:
            self.client.sendto(bytes(data, 'utf-8'), self.server_address)
            self.client.sendto(bytes(data, 'utf-8'), self.server_address2)  # pybulletin 使用
        except OSError:
            return

        # received_data, address = self.client.recvfrom(self.buffer_size)

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass

        
class VoiceClient:
    def __init__(self, parent=None):
        # super(UDPSocketClient, database).__init__(parent)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.buffer_size = 1024
        self._init_socket_client()

    def _init_socket_client(self):
        host = '255.255.255.255'
        port = 9991
        self.server_address = (host, port)
        self.server_address2 = (host, 9990)

    def send_data(self, data):
        try:
            self.client.sendto(bytes(data, 'utf-8'), self.server_address)
            self.client.sendto(bytes(data, 'utf-8'), self.server_address2)
        except OSError:
            return

        # received_data, address = self.client.recvfrom(self.buffer_size)
 
    def close(self):
        try:
            self.client.close()
        except Exception:
            pass
