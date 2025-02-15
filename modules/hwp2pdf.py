import os
import time
import pythoncom
import win32com.client as win32
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from utils.overlay_object import *
from utils.parse_code import *
from utils.coord import Coord
from utils.ratio import Ratio
import fitz
from pyhwpx import Hwp
from hwps.printer import *

hwp_lock = Lock()

def code2path(item_code):
    section = parse_code(item_code)["section"]
    topic = parse_code(item_code)["topic"]
    if section == 'KC':
        item_path = KICE_DB_PATH
    else:
        item_path = ITEM_DB_PATH
    hwp_path = os.path.join(item_path, topic, item_code, f"{item_code}.hwp")
    hwp_Main_path = os.path.join(item_path, topic, item_code, f"{item_code}_Main.hwp")

    return hwp_path, hwp_Main_path



def convert_hwp_to_pdf(hwp_path):
    """HWP를 PDF로 변환하는 함수"""
    pdf_path = hwp_path.replace('.hwp', '.pdf')

    hwp = Hwp(visible=False)

    try:
        for attempt in range(3):

            # 1) HWP와 PDF 파일 존재 여부 및 생성 시간 체크
            if os.path.exists(hwp_path) and os.path.exists(pdf_path):
                hwp_time = os.path.getmtime(hwp_path)
                pdf_time = os.path.getmtime(pdf_path)
                # PDF가 HWP보다 나중에 생성되었으며 10kb 이상이면 변환 불필요
                if pdf_time > hwp_time:
                    pdf_size = os.path.getsize(pdf_path)
                    if pdf_size > 10 * 1024:
                        return pdf_path
                        break

            # 2) PDF 변환 시도 (최대 3회)
            pythoncom.CoInitialize()
            if attempt > 1:
                print(f"Failed to convert {hwp_path} to PDF. Retrying...")
                time.sleep(0.1)

            hwp = None
            try:
                with hwp_lock:
                    hwp = Hwp(visible=False)
                    print_pdf(hwp_path, pdf_path)
                    hwp.Quit()
                    return pdf_path
            except Exception as e:
                print(f"Error converting {hwp_path} to PDF: {e}")

            finally:
                if hwp:
                    try:
                        hwp.Quit()
                    except:
                        pass
                pythoncom.CoUninitialize()

    except Exception as e:
        print(f"Error in convert_hwp_to_pdf: {e}")
        return None

def create_pdfs(item_codes, log_callback=None):
    existing_paths = []
    for code in item_codes:
        hwp_path, hwp_Main_path = code2path(code)
        if os.path.exists(hwp_path):
            existing_paths.append(hwp_path)
        if os.path.exists(hwp_Main_path):
            existing_paths.append(hwp_Main_path)
    total_files = len(existing_paths)

    completed = 0

    # CPU 코어 수를 고려하여 최적의 worker 수 결정
    # HWP 변환은 리소스를 많이 사용하므로 worker 수를 제한
    max_workers = min(os.cpu_count() // 2 or 1, 2)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(convert_hwp_to_pdf, file): file
            for file in existing_paths
        }

        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                pdf_path = future.result()
                if pdf_path:
                    completed += 1
                    progress = int((completed / total_files) * 100)
                    if log_callback:
                        log_callback(f"Progress: {progress}% - Converted: {os.path.basename(file)}")
            except Exception as e:
                if log_callback:
                    log_callback(f"Error processing {file}: {str(e)}")

        # Ensure progress reaches 100%
        if log_callback:
            log_callback("Progress: 100% - PDF creation completed.")