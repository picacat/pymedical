import importlib
import sys


# 資料庫類別
def get_db(config_file=None, backend="mysql", **kwargs):
    from classes import db

    module = importlib.reload(db)
    object = module.get_database(backend=backend, config_file=config_file, **kwargs)

    return object


# mssql 資料庫類別
def get_mssql_db(**kwargs):
    from classes import mssql_db

    module = importlib.reload(mssql_db)
    object = module.Database(**kwargs)

    return object


# 系統設定類別
def get_system_settings(database, config_file, station_no=None):
    from classes import system_settings

    module = importlib.reload(system_settings)
    object = module.SystemSettings(database, config_file, station_no)

    return object


# 訊息廣播設定-伺服器
def get_socket_server(parent=None, default_port=None):
    from classes import udp_socket_server

    module = importlib.reload(udp_socket_server)
    object = module.UDPSocketServer(parent, default_port)

    return object


# 訊息廣播設定-客戶端
def get_socket_client():
    from classes import udp_socket_client

    module = importlib.reload(udp_socket_client)
    object = module.UDPSocketClient()

    return object


# 語音廣播設定-伺服端
def get_voice_server(parent=None, default_port=None):
    from classes import udp_socket_server

    module = importlib.reload(udp_socket_server)
    object = module.VoiceServer(parent, default_port)

    return object


# 語音廣播設定-客戶端
def get_voice_client():
    from classes import udp_socket_client

    module = importlib.reload(udp_socket_client)
    object = module.VoiceClient()

    return object


# 讀卡機控制軟體
def get_cshis(parent, database, system_settings):
    if system_settings.field("使用讀卡機") != "Y":
        return None

    if sys.platform == "win32":
        if system_settings.field("讀卡機控制軟體版本") == "cshis6":
            from classes import cshis6_win32 as cshis
        else:
            from classes import cshis_win32 as cshis
    else:
        from classes import cshis

    module = importlib.reload(cshis)
    object = module.CSHIS(parent, database, system_settings)

    return object


# 虛擬健保卡讀卡機控制軟體
def get_vhccshis(parent, database, system_settings, qrcode):
    if sys.platform == "win32":
        if system_settings.field("讀卡機控制軟體版本") == "cshis6":
            from classes import cshis6_win32 as cshis

            module = importlib.reload(cshis)
            object = module.CSHIS(
                parent,
                database,
                system_settings,
                ic_card_type="虛擬健保卡",
                qrcode=qrcode,
            )
        else:
            from classes import vhccshis_win32 as vhccshis

            module = importlib.reload(vhccshis)
            object = module.VHCCSHIS(parent, database, system_settings, qrcode)
    else:
        from classes import vhccshis

        module = importlib.reload(vhccshis)
        object = module.VHCCSHIS(parent, database, system_settings, qrcode)

    return object


# 健保卡控制軟體加值作業
def get_cshisx(database, system_settings):
    if sys.platform == "win32":
        from classes import cshisx_win32 as cshisx
    else:
        from classes import cshisx

    module = importlib.reload(cshisx)
    object = module.CSHISX(database, system_settings)

    return object


# hca 函數庫
def get_hca_api(database, system_settings):
    if sys.platform == "win32":
        from classes import hca_api_win32 as hca_api
    else:
        from classes import hca_api

    module = importlib.reload(hca_api)
    object = module.HCAAPI(database, system_settings)

    return object


# table_widget
def get_table_widget(tableWidget, database):
    from classes import table_widget

    module = importlib.reload(table_widget)
    object = module.TableWidget(tableWidget, database)

    return object


# get star rating instance
def get_star_rating(star_count):
    from classes import star_rating

    return star_rating.StarRating(star_count)  # instance of StarRating


# five star rating
def get_star_rating_delegate(parent, database, tableWidget_past_history):
    from classes import star_rating

    module = importlib.reload(star_rating)
    object = module.StarDelegate(parent, database, tableWidget_past_history)

    return object


def get_address(address_str):
    from classes import address

    module = importlib.reload(address)
    object = module.Address(address_str)

    return object


# 零錢機
def get_coin_sys(system_settings):
    from classes import coin_sys

    module = importlib.reload(coin_sys)
    object = module.CoinSys(system_settings)

    return object


# 零錢機
def get_cpay(system_settings):
    from classes import cpay

    module = importlib.reload(cpay)
    object = module.CPay(system_settings)

    return object


# 捷特威零錢機
def get_jetway(system_settings):
    from classes import jetway

    module = importlib.reload(jetway)
    object = module.Jetway(system_settings)

    return object


# ic資料上傳
def get_ic_upload_xml1(
    parent, database, system_settings, tableWidget_ic_record, upload_type
):
    from classes import ic_upload_xml_1

    module = importlib.reload(ic_upload_xml_1)
    object = module.ICUploadXML1(
        parent, database, system_settings, tableWidget_ic_record, upload_type
    )

    return object


# ic資料上傳 新格式
def get_ic_upload_xml2(
    parent, database, system_settings, tableWidget_ic_record, upload_type
):
    from classes import ic_upload_xml_2

    module = importlib.reload(ic_upload_xml_2)
    object = module.ICUploadXML2(
        parent, database, system_settings, tableWidget_ic_record, upload_type
    )

    return object


def get_dict_autocomplete(text_edit, database, clinic_type, match_mode="prefix"):
    from classes import dict_autocomplete

    module = importlib.reload(dict_autocomplete)
    object = module.DictAutoComplete(text_edit, database, clinic_type, match_mode)

    return object
