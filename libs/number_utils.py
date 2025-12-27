# 數字 2014.10.05
# -*- coding: UTF-8 -*-

import math
from decimal import Decimal,  ROUND_HALF_UP


def get_integer(value):
    if value is None or value == '':
        return 0
    else:
        try:
            value = str(value).replace(',', '')
            return int(float(value))
        except ValueError:
            return 0


def get_integer_without_zero(value):
    if value is None or value == '':
        return None
    else:
        return int(float(value))


def get_float(value):
    if value is None or value == '':
        return 0.0

    try:
        value = float(value)
    except ValueError:
        value = 0.0

    return value


# 傳統的四捨五入
def round_up(value):
    round_up_str = Decimal(str(value)).quantize(Decimal('1'), ROUND_HALF_UP)

    return int(round_up_str)


def round_up_ex(value, decimal_format):
    value = Decimal(str(value))  # 確保不使用浮點數
    return value.quantize(Decimal(decimal_format), rounding=ROUND_HALF_UP)


def str_to_int(string):
    if string == '':
        return None
    else:
        return int(string)


# 無條件進位
def ceil(value):
    return math.ceil(value)
