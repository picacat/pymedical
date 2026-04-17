# download api 2020.02.10

# -*- coding: UTF-8 -*-
import ssl
import urllib
from queue import Empty, Queue
from threading import Thread

from PyQt5 import QtCore

from libs import dialog_utils


def _download_file_thread(out_queue, download_file_name, url):
    QtCore.QCoreApplication.processEvents()

    context = ssl._create_unverified_context()
    u = urllib.request.urlopen(url, context=context)
    data = u.read()
    u.close()
    with open(download_file_name, "wb") as f:
        f.write(data)

    out_queue.put(download_file_name)


# 下載dropbox資料
def download_dropbox_file(file_name, url, title, message, hint, timeout=10):
    msg_box = dialog_utils.message_box(title, message, hint)
    msg_box.show()

    msg_queue = Queue()
    QtCore.QCoreApplication.processEvents()

    t = Thread(target=_download_file_thread, args=(msg_queue, file_name, url))
    t.start()

    try:
        download_file_name = msg_queue.get(timeout=timeout)
        msg_box.close()
        return download_file_name
    except Empty:
        msg_box.close()
        print("⚠️ 無法下載更新檔，可能沒有網路或下載逾時，將跳過更新。")
        return None
