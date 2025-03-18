import os
import time
import subprocess
import sys
from glob import glob
from tqdm import tqdm
from hwps.ezpdf import *
from utils.parse_code import *
from utils.path import *
from utils.overlay_object import *
from pathlib import Path
from pyhwpx import Hwp

import pythoncom
import win32com.client as win32
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from utils.parse_code import *
from utils.overlay_object import *
from utils.parse_code import *
from utils.coord import Coord
from utils.ratio import Ratio
import fitz
from pyhwpx import Hwp

hwp_lock = Lock()

def code2path(item_code):
    hwp_path = code2pdf(item_code).replace('.pdf', '.hwp')
    hwp_Main_path = code2Main(item_code).replace('.pdf', '.hwp')

    return hwp_path, hwp_Main_path


def font_integrity_test(pdf_path):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        fonts = page.get_fonts()
        for font in fonts:
            if font[2] == "Type3":
                doc.close()
                return False
    doc.close()
    return True

def print_pdf(hwp_path, pdf_path):
    pythoncom.CoInitialize()

    try:
        hwp = Hwp(visible=False)
        hwp.open(hwp_path, arg="setcurdir:true")
        sec_def = hwp.HParameterSet.HSecDef
        hwp.HAction.GetDefault("PageSetup", sec_def.HSet)

        act = hwp.CreateAction("Print")
        pset = act.CreateSet()
        act.GetDefault(pset)
        if os.path.exists(pdf_path):  # 저장하려는 이름의 파일이 있으면
            os.remove(pdf_path)  # 해당 파일 삭제
        pset.SetItem("Collate", 1)
        pset.SetItem("UserOrder", 0)
        pset.SetItem("PrintToFile", 0)
        pset.SetItem("PrinterName", "ezPDF Builder Supreme")
        pset.SetItem("UsingPagenum", 1)
        pset.SetItem("ReverseOrder", 0)
        pset.SetItem("Pause", 0)
        pset.SetItem("PrintImage", 1)
        pset.SetItem("PrintDrawObj", 1)
        pset.SetItem("PrintClickHere", 0)
        pset.SetItem("PrintAutoFootnoteLtext", "^f")
        pset.SetItem("PrintAutoFootnoteCtext", "^t")
        pset.SetItem("PrintAutoFootnoteRtext", "^P쪽 중 ^p쪽")
        pset.SetItem("PrintAutoHeadnoteLtext", "^c")
        pset.SetItem("PrintAutoHeadnoteCtext", "^n")
        pset.SetItem("PrintAutoHeadnoteRtext", "^p")
        pset.SetItem("PrintFormObj", 1)
        pset.SetItem("PrintMarkPen", 0)
        pset.SetItem("PrintMemo", 0)
        pset.SetItem("PrintMemoContents", 0)
        pset.SetItem("PrintRevision", 1)
        pset.SetItem("PrintBarcode", 1)
        pset.SetItem("Device", 0)
        pset.SetItem("UseHft2Ttf", 0)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        ezpdf_path = os.path.join(project_root, "hwps", "ezpdf.py")
        process1 = subprocess.Popen([sys.executable, ezpdf_path, pdf_path])
        act.Execute(pset)
        process1.wait()

    except Exception as e:
        print(f"Error in print_pdf: {e}")

    finally:
        try:
            if hwp:
                hwp.Quit()
        except:
            pass
        pythoncom.CoUninitialize()


def convert_hwp_to_pdf(hwp_path):
    pdf_path = hwp_path.replace('.hwp', '.pdf')
    try:
        for attempt in range(3):

            # 1) HWP와 PDF 파일 존재 여부 및 생성 시간 체크
            if os.path.exists(hwp_path) and os.path.exists(pdf_path):
                hwp_time = os.path.getmtime(hwp_path)
                pdf_time = os.path.getmtime(pdf_path)
                # PDF가 HWP보다 나중에 생성되었으며 10kb 이상이면서 font_integrity_test를 통과하면 변환 불필요
                if pdf_time > hwp_time:
                    pdf_size = os.path.getsize(pdf_path)
                    if pdf_size > 10 * 1024:
                        if font_integrity_test(pdf_path):
                            return pdf_path
                            break

            # 2) PDF 변환 시도 (최대 3회)
            pythoncom.CoInitialize()
            if attempt > 1:
                print(f"Failed to convert {hwp_path} to PDF. Retrying...")
                time.sleep(0.5)

            else:
                pass

            hwp = None
            try:
                with hwp_lock:
                    if parse_code(Path(hwp_path).stem.split('_')[0])["section"] == "KC":
                        hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
                        hwp.XHwpWindows.Item(0).Visible = False
                        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")  # 보안 모듈 pass
                        hwp.Open(hwp_path)
                        hwp.XHwpDocuments.Item(0).XHwpPrint.filename = pdf_path
                        hwp.XHwpDocuments.Item(0).XHwpPrint.RunToPDF()
                        pass
                    else:
                        hwp = None
                        print_pdf(hwp_path, pdf_path)
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


def main():
    item_codes = ["E1bafZG250001", "E1bafZG250002", "E1bafZG250003", "E1bafZG250004", "E1bafZG250005", "E1baaKC210607"]
    create_pdfs(item_codes)

if __name__ == "__main__":
    main()