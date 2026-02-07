# 字串 2018.01.29
# -*- coding: UTF-8 -*-

import re
import unicodedata

try:
    import pypinyin
except Exception:
    pass

import itertools
from string import ascii_uppercase

phonetic_list = [
    "ㄅ",
    "ㄆ",
    "ㄇ",
    "ㄈ",
    "ㄉ",
    "ㄊ",
    "ㄋ",
    "ㄌ",
    "ㄍ",
    "ㄎ",
    "ㄏ",
    "ㄐ",
    "ㄑ",
    "ㄒ",
    "ㄓ",
    "ㄔ",
    "ㄕ",
    "ㄖ",
    "ㄗ",
    "ㄘ",
    "ㄙ",
    "ㄧ",
    "ㄨ",
    "ㄩ",
    "ㄚ",
    "ㄛ",
    "ㄜ",
    "ㄝ",
    "ㄞ",
    "ㄟ",
    "ㄠ",
    "ㄡ",
    "ㄢ",
    "ㄣ",
    "ㄤ",
    "ㄥ",
    "ㄦ",
]

phonetic_table = {
    "ㄅ": "1",
    "ㄆ": "q",
    "ㄇ": "a",
    "ㄈ": "z",
    "ㄉ": "2",
    "ㄊ": "w",
    "ㄋ": "s",
    "ㄌ": "x",
    "ㄍ": "e",
    "ㄎ": "d",
    "ㄏ": "c",
    "ㄐ": "r",
    "ㄑ": "f",
    "ㄒ": "v",
    "ㄓ": "5",
    "ㄔ": "t",
    "ㄕ": "g",
    "ㄖ": "b",
    "ㄗ": "y",
    "ㄘ": "h",
    "ㄙ": "n",
    "ㄧ": "u",
    "ㄨ": "j",
    "ㄩ": "m",
    "ㄚ": "8",
    "ㄛ": "i",
    "ㄜ": "k",
    "ㄝ": ",",
    "ㄞ": "9",
    "ㄟ": "o",
    "ㄠ": "l",
    "ㄡ": ".",
    "ㄢ": "0",
    "ㄣ": "p",
    "ㄤ": ";",
    "ㄥ": "/",
    "ㄦ": "-",
}

encoded_phonetic_table = {
    "1": "ㄅ",
    "q": "ㄆ",
    "a": "ㄇ",
    "z": "ㄈ",
    "2": "ㄉ",
    "w": "ㄊ",
    "s": "ㄋ",
    "x": "ㄌ",
    "e": "ㄍ",
    "d": "ㄎ",
    "c": "ㄏ",
    "r": "ㄐ",
    "f": "ㄑ",
    "v": "ㄒ",
    "5": "ㄓ",
    "t": "ㄔ",
    "g": "ㄕ",
    "b": "ㄖ",
    "y": "ㄗ",
    "h": "ㄘ",
    "n": "ㄙ",
    "u": "ㄧ",
    "j": "ㄨ",
    "m": "ㄩ",
    "8": "ㄚ",
    "i": "ㄛ",
    "k": "ㄜ",
    ",": "ㄝ",
    "9": "ㄞ",
    "o": "ㄟ",
    "l": "ㄠ",
    ".": "ㄡ",
    "0": "ㄢ",
    "p": "ㄣ",
    ";": "ㄤ",
    "/": "ㄥ",
    "-": "ㄦ",
}


# 清除不必要的字元
def strip_string(in_string):
    try:
        in_string = re.sub(
            r"\([^)]*\)", "", in_string
        )  # 把 in_string(xxx) 中的 (xxx) 去除
    except TypeError:
        return

    remap = [chr(i) for i in range(32, 127)]  # 去除非中文字元
    for char in remap:
        in_string = in_string.replace(char, "")

    return in_string


# 清除不必要的ascii字元
def replace_ascii_char(ascii_char_list, in_string):
    for ascii_char in ascii_char_list:
        in_string = in_string.replace(ascii_char, "")

    return in_string


# 整數轉字串(零不顯示)
def int_to_str(number):
    if number is None:
        number = ""
    else:
        number = str(number)

    return number


def remove_control_characters(string):
    return "".join(ch for ch in string if unicodedata.category(ch)[0] != "C")


# 移除非法的字元
def remove_illegal_characters(string):
    illegal_characters_list = ["\n", "\r", "\t", "\\", "'", '"', "\x00"]
    for character in illegal_characters_list:
        string = string.replace(character, "")

    return string


# 移除非法的字元
def remove_quote_characters(string):
    illegal_characters_list = ["\\", "'", '"']
    for character in illegal_characters_list:
        string = string.replace(character, "")

    return string


# 更改欄位內容編碼 2015/01/22
def get_str(in_string, encoding):
    if not in_string:
        return ""

    if type(in_string).__name__ in ["int", "float"]:
        try:
            out_string = xstr(in_string)
        except TypeError:
            out_string = ""

        return out_string

    try:
        out_string = str(in_string, encoding=encoding)
    except Exception:
        try:
            out_string = str(in_string, encoding="big5", errors="replace")
        except Exception:
            out_string = in_string

    if type(out_string) is bytes:
        out_string = str(in_string, encoding="big5", errors="replace")

    # return html.escape(out_string.strip())
    return out_string.strip()


def xstr(string):
    if string is None:
        return ""

    return str(string)


def remove_square_square_brackets(string):
    string = xstr(string)

    string = re.sub(r"[0-9]", "", string)
    string = re.sub(r"\(.*?\)", "", string)
    string = re.sub(r"\[.*?\]", "", string)

    return string


def remove_not_chinese_character(s):
    # 如果沒有中文，就直接回傳
    if not re.search(r"[\u4e00-\u9fff]", s):
        return s

    # 若有中文，就移除所有非中文
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


def get_mask_name(name):
    name = xstr(name)
    if name == "":
        return ""

    mask_name_list = list(name)
    mask_name_list[1] = "〇"

    mask_name = "".join(mask_name_list)

    return mask_name


def get_mask_id(patient_id, length):
    patient_id = xstr(patient_id)
    if patient_id == "":
        return ""

    mask_id_list = list(patient_id)
    for i, count in zip(range(len(mask_id_list) - 1, -1, -1), range(len(mask_id_list))):
        if count >= length:
            break

        mask_id_list[i] = "*"

    mask_id = "".join(mask_id_list)

    return mask_id


def remove_bom(string):
    if string.startswith("\ufeff"):
        string = string[1:]

    return string


def str_to_none(in_list):
    for i in range(len(in_list)):
        if str(in_list[i]) == "":
            in_list[i] = None


# 轉換注音字母為英數字母
def phonetic_to_str(in_str):
    ansi_str = ""
    for char in in_str:
        try:
            phn_str = phonetic_table[char]
        except KeyError:
            phn_str = char

        ansi_str += phn_str

    return ansi_str


# 轉換注音字母為英數字母
def str_to_phonetic(in_str):
    ansi_str = ""
    for char in in_str:
        try:
            phn_str = encoded_phonetic_table[char]
        except KeyError:
            phn_str = char

        ansi_str += phn_str

    return ansi_str


def get_formatted_str(field_type, raw_value):
    value = xstr(raw_value)

    if value == "":
        return value

    try:
        if field_type in ["日劑量", "總量"]:
            value = f"{raw_value:.1f}"
        elif field_type == "次劑量":
            value = f"{raw_value:.2f}"
        elif field_type == "單價":
            value = f"{raw_value:.2f}"
        else:
            value = f"{raw_value:.1f}"
    except ValueError:
        pass

    return value


def get_check_box(checked):
    if checked:
        return "🗹"
    else:
        return "☐"


def barcode_128a(input_data):
    checksum = 103
    for ii, char in enumerate(input_data):
        ascii_str = ord(char)
        if ascii_str >= 32:
            checksum += (ascii_str - 32) * (ii + 1)
        else:
            checksum += (ascii_str + 64) * (ii + 1)

    checksum = checksum % 103
    if checksum < 95:
        checksum += 32
    else:
        checksum += 100

    result = chr(203) + str(input_data) + chr(checksum) + chr(206)

    return result


def barcode_128b(input_data):
    checksum = 104
    for ii, char in enumerate(input_data):
        ascii_str = ord(char)
        if ascii_str >= 32:
            checksum += (ascii_str - 32) * (ii + 1)
        else:
            checksum += (ascii_str + 64) * (ii + 1)

    checksum = checksum % 103
    if checksum < 95:
        checksum += 32
    else:
        checksum += 100

    result = chr(204) + str(input_data) + chr(checksum) + chr(206)

    return result


def barcode_128c(input_data):
    checksum = 105
    result = ""

    j = 1
    for ii in range(0, len(input_data), 2):
        v = int(input_data[ii : ii + 2])
        checksum += v * j
        if v < 95:
            result += chr(v + 32)
        else:
            result += chr(v + 100)

        j += 1

    checksum = checksum % 103
    if checksum < 95:
        checksum += 32
    else:
        checksum += 100

    result = chr(205) + result + chr(checksum) + chr(206)

    return result


def encode128(s):
    s = s.encode("ascii").decode("ascii")
    if s.isdigit() and len(s) % 2 == 0:
        # use Code 128C, pairs of digits
        codes = [105]
        for i in range(0, len(s), 2):
            codes.append(int(s[i : i + 2], 10))
    else:
        # use Code 128B and shift for Code 128A
        mapping = dict(
            (chr(c), [98, c + 64] if c < 32 else [c - 32]) for c in range(128)
        )
        codes = [104]
        for c in s:
            codes.extend(mapping[c])
    check_digit = (codes[0] + sum(i * x for i, x in enumerate(codes))) % 103
    codes.append(check_digit)
    codes.append(106)  # stop code
    chars = (b"\xd4" + bytes(range(33, 126 + 1)) + bytes(range(200, 211 + 1))).decode(
        "latin-1"
    )

    return "".join(chars[x] for x in codes)


def removeprefix(string, prefix):
    if not (isinstance(string, str) and isinstance(prefix, str)):
        raise TypeError("Param value type error")
    if string.startswith(prefix):
        return string[len(prefix) :]

    return string


def removesuffix(string, suffix):
    if not (isinstance(string, str) and isinstance(suffix, str)):
        raise TypeError("Param value type error")
    if string.endswith(suffix):
        return string[: -len(suffix)]

    return string


def get_yes_no_string(in_string, output_type=None):
    in_string = xstr(in_string)

    if output_type == "zh_tw":
        if in_string == "Y":
            return "是"
        elif in_string == "N":
            return "否"
        else:
            return ""
    elif output_type == "digit":
        if in_string == "Y":
            return "1"
        elif in_string == "N":
            return "0"
        else:
            return ""
    else:
        return in_string


def iter_all_strings():
    for size in itertools.count(1):
        for s in itertools.product(ascii_uppercase, repeat=size):
            yield "".join(s)


def get_cell_name(end="ZZ"):
    cell_list = []
    for s in iter_all_strings():
        cell_list.append(s)
        if s == end:
            break

    return cell_list


# 取得注音輸入碼
def get_input_code(text):
    # 取得完整的注音
    try:
        zhuyin_list = pypinyin.lazy_pinyin(text, style=pypinyin.Style.BOPOMOFO)
    except Exception:
        return ""

    # 取每個字的第一個注音符號
    abbreviation = "".join([zhuyin[0] for zhuyin in zhuyin_list if zhuyin])

    input_code = ""
    for phonetic in abbreviation:
        try:
            input_code += phonetic_table[phonetic]
        except Exception:
            continue

    return input_code


def shorten_middle(text, max_length=10):
    if len(text) <= max_length:
        return text

    half_length = (max_length - 3) // 2  # 3 is for "..."
    return text[:half_length] + "..." + text[-half_length:]
