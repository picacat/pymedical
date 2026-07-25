import sys
from libs import class_utils
from libs import system_utils

database = class_utils.get_db()
config_file = database.CONFIG_FILE
system_settings = class_utils.get_system_settings(database, config_file)
cpay = class_utils.get_cpay(system_settings)

if not cpay.connected:
    print('Error! cpay.exe not executed')
    sys.exit(0)

total_fee = 10
cpay.start_payment(total_fee)
while (True):
    receipt_fee = cpay.get_payment()
    if receipt_fee >= total_fee:
        cpay.cancel_payment()
        break

