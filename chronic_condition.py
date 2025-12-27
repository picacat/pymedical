from pyexcel_ods3 import get_data
import mysql.connector as mysql
import json

cnx = mysql.connect(
    host='localhost',
    user='root',
    password='620210',
    charset='utf8',
    buffered=True,
)
cursor = cnx.cursor(dictionary=True)

rows = get_data('chronic_condition.ods')['sheet1']

chronic_dict = {}
for row in rows:
    try:
        chronic_code = row[0]
        icd_code = row[2]
    except Exception:
        continue

    chronic_code = chronic_code[-4:]
    chronic_code = chronic_code.replace('（', '').replace('）', '')
    start_code = icd_code.split('-')[0]
    try:
        end_code = icd_code.split('-')[1]
    except Exception:
        end_code = None

    if end_code is None:
        sql = f'select ICDCode from icd10 where ICDCode = "{start_code}"'
    else:
        sql = f'select ICDCode from icd10 where ICDCode between "{start_code}" AND "{end_code}"'

    cursor.execute('use pymedical')
    cursor.execute(sql)
    rows = cursor.fetchall()
    for row in rows:
        chronic_dict[row['ICDCode']] = chronic_code

with open('chronic_condition.json', 'w') as f:
    json.dump(chronic_dict, f)

