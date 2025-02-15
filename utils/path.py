KICE_DB_PATH = r'T:\THedu\KiceDB'
ITEM_DB_PATH = r'T:\THedu\ItemDB'

RESOURCES_PATH = 'T:/Software/LCS/resources'

INPUT_PATH = 'T:/Software/LCS/input'
OUTPUT_PATH = 'T:/Software/LCS/output'
BOOK_DB_PATH = 'T:/Software/LCS/input/BookDB'

def get_item_path(item_code):
    if item_code[5:7] == 'KC': return KICE_DB_PATH
    else: return ITEM_DB_PATH