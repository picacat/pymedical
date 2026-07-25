from libs import string_utils


PAYMENT_ITEMS = [
    '現金',
    '自費券',
    '100券',
    '100現',
    '推薦單:醫師',
    '推薦單:小姐',
    '抽成實領:體蒸',
    '抽成實領:足蒸',
    '抽成實領:丹田',
    '抽成實領:專案',
    'OTC',
    '療程券',
    '專案',
    '美容',
]

TREAT_TYPE = [
    '養生館', '購買商品',
]


def get_massage_prescript_item(database, massage_case_key):
    sql = f'''
        SELECT MedicineName FROM massage_prescript
        WHERE
            MassageCaseKey = {massage_case_key}
        ORDER BY MassagePrescriptKey
    '''
    rows = database.select_record(sql)

    massage_item = []
    for row in rows:
        massage_item.append(string_utils.xstr(row['MedicineName']))

    return ', '.join(massage_item)
