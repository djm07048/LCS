# gui_duplex.py
#   - GUI for builder_duplex.py

# input
# item_num = 순서를 정해줌
# item_code = 'E1aaaSV261620'
# related_item_codes = 'E1aaaKC210612', 'E1aaaZG250001'
# theory_code = 'WIND UP 고체편 120p'

import json

def get_reference_data():
    with open('reference_data.json', 'r') as f:
        data = json.load(f)
    return data

def code2ref(item_code):
    # item_code -> item_ref
    # 'E1aaaZG250001' -> 'Squeeze 고체4 K번'
    data = get_reference_data()


# item별로 page를 제작함.