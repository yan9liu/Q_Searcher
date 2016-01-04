
def is_legal(uchar):
    """判断是否非汉字，数字和英文字符"""
    if is_chinese(uchar) or is_number(uchar) or is_alphabet(uchar):
        return True
    else:
        return False


def is_chinese(uchar):
    """判断一个unicode是否是汉字"""
    if uchar >= u'\u4e00' and uchar<=u'\u9fa5':
        return True
    else:
        return False
 

def is_number(uchar):
    """判断一个unicode是否是数字"""
    if uchar >= u'\u0030' and uchar<=u'\u0039':
        return True
    else:
        return False
 

def is_alphabet(uchar):
    """判断一个unicode是否是英文字母"""
    if ((uchar >= u'\u0041' and uchar<=u'\u005a') or 
        (uchar >= u'\u0061' and uchar<=u'\u007a')):
        return True
    else:
        return False


def normalize_query(query):
    norm = []
    for uchar in query:
        if is_legal(uchar):
            norm.append(uchar.lower())
    return "".join(norm)