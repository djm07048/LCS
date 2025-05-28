from utils.path import *
import os
import json


def search_latest_reference_in_rel_items(item_code):
    """디버깅 버전"""
    print(f"\n=== Searching for: {item_code} ===")

    try:
        if not os.path.exists(HISTORY_DB_PATH):
            print(f"HISTORY_DB_PATH does not exist: {HISTORY_DB_PATH}")
            return False

        # HISTORY_DB_PATH 내의 모든 JSON 파일 가져오기
        all_files = [f for f in os.listdir(HISTORY_DB_PATH) if f.endswith('.json')]
        print(f"All JSON files: {all_files}")

        # EX_로 시작하는 파일들을 가나다순으로 정렬
        ex_files = sorted([f for f in all_files if f.startswith('EX_')])
        print(f"EX_ files: {ex_files}")

        # EX_ 파일들에서 검색
        for ex_file in ex_files:
            file_path = os.path.join(HISTORY_DB_PATH, ex_file)
            print(f"Checking file: {ex_file}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"File loaded successfully, {len(data)} items")

                # 리스트 형태의 JSON에서 list_rel_item_code 내의 item_code 검색
                for i, item in enumerate(data):
                    list_rel_item_code = item.get('list_rel_item_code', [])

                    if isinstance(list_rel_item_code, list):
                        for index, rel_item_code in enumerate(list_rel_item_code):
                            if rel_item_code == item_code:
                                output = item.get('number')
                                order = chr(index + 65)
                                file_identifier = ex_file.split('_')[1].replace('회.json', '')
                                result = f'정태혁 모의고사 {int(file_identifier)}회 {output}{order}번'
                                print(f"FOUND MATCH! Returning: {result}")
                                return result

            except Exception as e:
                print(f"Error reading {ex_file}: {e}")
                continue

        print("No matches found, returning '신규 문항'")
        return False

    except Exception as e:
        print(f"Unexpected error in search function: {e}")
        return False

def search_latest_reference_in_all_items(item_code):
    """
    HISTORY_DB_PATH에서 item_code를 찾아 참조 정보를 반환하는 함수

    Args:
        item_code (str): 찾을 문항 코드

    Returns:
        str: 참조 정보 또는 '신규 문항'
    """
    if not os.path.exists(HISTORY_DB_PATH):
        return '신규 문항'

    # HISTORY_DB_PATH 내의 모든 JSON 파일 가져오기
    all_files = [f for f in os.listdir(HISTORY_DB_PATH) if f.endswith('.json')]

    # SQ_로 시작하는 파일들을 가나다순으로 정렬
    sq_files = sorted([f for f in all_files if f.startswith('SQ_')])

    # EX_로 시작하는 파일들을 가나다순으로 정렬
    ex_files = sorted([f for f in all_files if f.startswith('EX_')])

    # 1. SQ_ 파일들에서 먼저 검색
    for sq_file in sq_files:
        file_path = os.path.join(HISTORY_DB_PATH, sq_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 리스트 형태의 JSON에서 item_code 검색
            for item in data:
                if item.get('item_code') == item_code and item.get('mainsub'):
                    # mainsub이 null이 아니면 mainsub 사용, 아니면 item_num 사용
                    output = item.get('mainsub')
                    # 파일명에서 SQ_ 이후 부분 추출 (확장자 제거)
                    file_identifier = sq_file.split('_')[1].replace('.json', '')
                    return f'Squeeze {file_identifier} {output}번'

        except (json.JSONDecodeError, FileNotFoundError, KeyError, IndexError) as e:
            print(f"Error reading {sq_file}: {e}")
            continue

    # 2. EX_ 파일들에서 검색
    for ex_file in ex_files:
        file_path = os.path.join(HISTORY_DB_PATH, ex_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 리스트 형태의 JSON에서 item_code 검색
            for item in data:
                if item.get('item_code') == item_code:
                    output = item.get('number')
                    # 파일명에서 EX_ 이후 부분 추출 (확장자 제거)
                    file_identifier = ex_file.split('_')[1].replace('회.json', '')
                    return f'정태혁 모의고사 {int(file_identifier)}회 {output}번'

        except (json.JSONDecodeError, FileNotFoundError, KeyError, IndexError) as e:
            print(f"Error reading {ex_file}: {e}")
            continue

    # 3. 모든 파일에서 찾지 못한 경우
    return '신규 문항'

if __name__ == "__main__":
    # 테스트용 코드
    item_codes = ["E1nfcZG260102", "E1nekKC250603", "E1nekZG250002", "E1pffZG260202"]
    for item_code in item_codes:
        result = search_latest_reference_in_rel_items(item_code)
        print(result)  # 예시 출력: Squeeze 123 1번from utils.path import *
import os
import json


def search_latest_reference_in_rel_items(item_code):
    """디버깅 버전"""
    print(f"\n=== Searching for: {item_code} ===")

    try:
        if not os.path.exists(HISTORY_DB_PATH):
            print(f"HISTORY_DB_PATH does not exist: {HISTORY_DB_PATH}")
            return False

        # HISTORY_DB_PATH 내의 모든 JSON 파일 가져오기
        all_files = [f for f in os.listdir(HISTORY_DB_PATH) if f.endswith('.json')]
        print(f"All JSON files: {all_files}")

        # EX_로 시작하는 파일들을 가나다순으로 정렬
        ex_files = sorted([f for f in all_files if f.startswith('EX_')])
        print(f"EX_ files: {ex_files}")

        list_rel_items = []

        # EX_ 파일들에서 검색
        for ex_file in ex_files:
            file_path = os.path.join(HISTORY_DB_PATH, ex_file)
            print(f"Checking file: {ex_file}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"File loaded successfully, {len(data)} items")

                # 리스트 형태의 JSON에서 list_rel_item_code 내의 item_code 검색
                for i, item in enumerate(data):
                    list_rel_item_code = item.get('list_rel_item_code', [])

                    if isinstance(list_rel_item_code, list):
                        for index, rel_item_code in enumerate(list_rel_item_code):
                            output = item.get('number')
                            order = chr(index + 65)
                            file_identifier = ex_file.split('_')[1].replace('회.json', '')
                            result = f'정태혁 모의고사 {int(file_identifier)}회 {output}{order}번'
                            rel_item = {'item_code': rel_item_code, 'result': result}
                            list_rel_items.append(rel_item)

            except Exception as e:
                print(f"Error reading {ex_file}: {e}")
                continue

        print("No matches found, returning '신규 문항'")
        return False

    except Exception as e:
        print(f"Unexpected error in search function: {e}")
        return False

def search_latest_reference_in_all_items(item_code):
    """
    HISTORY_DB_PATH에서 item_code를 찾아 참조 정보를 반환하는 함수

    Args:
        item_code (str): 찾을 문항 코드

    Returns:
        str: 참조 정보 또는 '신규 문항'
    """
    if not os.path.exists(HISTORY_DB_PATH):
        return '신규 문항'

    # HISTORY_DB_PATH 내의 모든 JSON 파일 가져오기
    all_files = [f for f in os.listdir(HISTORY_DB_PATH) if f.endswith('.json')]

    # SQ_로 시작하는 파일들을 가나다순으로 정렬
    sq_files = sorted([f for f in all_files if f.startswith('SQ_')])

    # EX_로 시작하는 파일들을 가나다순으로 정렬
    ex_files = sorted([f for f in all_files if f.startswith('EX_')])

    # 1. SQ_ 파일들에서 먼저 검색
    for sq_file in sq_files:
        file_path = os.path.join(HISTORY_DB_PATH, sq_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 리스트 형태의 JSON에서 item_code 검색
            for item in data:
                if item.get('item_code') == item_code and item.get('mainsub'):
                    # mainsub이 null이 아니면 mainsub 사용, 아니면 item_num 사용
                    output = item.get('mainsub')
                    # 파일명에서 SQ_ 이후 부분 추출 (확장자 제거)
                    file_identifier = sq_file.split('_')[1].replace('.json', '')
                    return f'Squeeze {file_identifier} {output}번'

        except (json.JSONDecodeError, FileNotFoundError, KeyError, IndexError) as e:
            print(f"Error reading {sq_file}: {e}")
            continue

    # 2. EX_ 파일들에서 검색
    for ex_file in ex_files:
        file_path = os.path.join(HISTORY_DB_PATH, ex_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 리스트 형태의 JSON에서 item_code 검색
            for item in data:
                if item.get('item_code') == item_code:
                    output = item.get('number')
                    # 파일명에서 EX_ 이후 부분 추출 (확장자 제거)
                    file_identifier = ex_file.split('_')[1].replace('회.json', '')
                    return f'정태혁 모의고사 {int(file_identifier)}회 {output}번'

        except (json.JSONDecodeError, FileNotFoundError, KeyError, IndexError) as e:
            print(f"Error reading {ex_file}: {e}")
            continue

    # 3. 모든 파일에서 찾지 못한 경우
    return '신규 문항'

if __name__ == "__main__":
    # 테스트용 코드
    item_codes = ["E1nfcZG260102", "E1nekKC250603", "E1nekZG250002", "E1pffZG260202"]
    for item_code in item_codes:
        result = search_latest_reference_in_rel_items(item_code)
        print(result)  # 예시 출력: Squeeze 123 1번