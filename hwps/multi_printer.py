import os
import time
import subprocess
import sys
import uuid
from glob import glob
from tqdm import tqdm
from hwps.ezpdf import *
from utils.path import *
from utils.overlay_object import *
from pathlib import Path
from pyhwpx import Hwp
import utils.path
import pythoncom
import win32com.client as win32
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from utils.overlay_object import *
from utils.coord import Coord
from utils.ratio import Ratio
import fitz
from pyhwpx import Hwp
from utils.path import *

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


def safe_file_move(src_path, dest_path, max_retries=5, delay=0.5):
    """Safely move a file with retry logic for file lock issues"""
    for attempt in range(max_retries):
        try:
            if os.path.exists(src_path):
                # Try to remove destination file if it exists
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except PermissionError:
                        time.sleep(delay)
                        continue

                # Try to move the file
                os.rename(src_path, dest_path)
                return True
        except (PermissionError, FileExistsError, OSError) as e:
            if attempt < max_retries - 1:
                print(f"File move attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 1.5  # Exponential backoff
            else:
                print(f"Failed to move file after {max_retries} attempts: {e}")
                return False
    return False


def convert_hwp_to_pdf(hwp_path):
    pdf_path = hwp_path.replace('.hwp', '.pdf')
    try:
        for attempt in range(3):

            # 1) HWP와 PDF 파일 존재 여부 및 생성 시간 체크
            if os.path.exists(hwp_path) and os.path.exists(pdf_path):
                hwp_time = os.path.getmtime(hwp_path)
                pdf_time = os.path.getmtime(pdf_path)
                # TODO: Main pdf은 if 없이 무조건 생성됨
                # PDF가 HWP보다 나중에 생성되었으며 10kb 이상이면 변환 불필요
                if pdf_time > hwp_time:
                    pdf_size = os.path.getsize(pdf_path)
                    if pdf_size > 10 * 1024:
                        return pdf_path

            # 2) PDF 변환 시도 (최대 3회)
            pythoncom.CoInitialize()

            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    time.sleep(0.5)
                except PermissionError:
                    # If we can't remove the existing file, skip this conversion
                    print(f"Cannot remove existing PDF file: {pdf_path}")
                    pythoncom.CoUninitialize()
                    continue

            if attempt > 1:
                print(f"Failed to convert {hwp_path} to PDF. Retrying...")
                time.sleep(1.0)  # Longer delay on retry

            hwp = None

            # Create unique temporary filename to avoid conflicts
            unique_id = str(uuid.uuid4())[:8]
            temp_filename = f"{Path(pdf_path).stem}_{unique_id}.pdf"
            temporary_pdf_path = str(Path(TEMPORARY_PATH) / temp_filename)

            try:
                with hwp_lock:
                    ''''
                    if parse_code(Path(hwp_path).stem.split('_')[0])["section"] == "KC":
                        hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
                        hwp.XHwpWindows.Item(0).Visible = False
                        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")  # 보안 모듈 pass
                        hwp.Open(hwp_path)
                        hwp.XHwpDocuments.Item(0).XHwpPrint.filename = temporary_pdf_path
                        hwp.XHwpDocuments.Item(0).XHwpPrint.RunToPDF()
                    else:
                        hwp = None
                        print_pdf(hwp_path, temporary_pdf_path)
                    
                    모든 file을 동일한 방식으로 ez pdf 로 변환하는 로직으로 수정하였기 때문에 주석처리함
                
                    '''
                    hwp = None
                    print_pdf(hwp_path, temporary_pdf_path)

                    time.sleep(1.0)  # Give more time for file operations to complete

                    # Use safe file move with retry logic
                    if safe_file_move(temporary_pdf_path, pdf_path):
                        print(f"Converted {hwp_path} to {pdf_path}")
                        return pdf_path
                    else:
                        print(f"Failed to move temporary file for {hwp_path}")

            except Exception as e:
                print(f"Error converting {hwp_path} to PDF: {e}")
                # Clean up temporary file if it exists
                if os.path.exists(temporary_pdf_path):
                    try:
                        os.remove(temporary_pdf_path)
                    except:
                        pass

            finally:
                if hwp:
                    try:
                        hwp.Quit()
                        time.sleep(0.5)  # Give HWP time to properly close
                    except:
                        pass
                pythoncom.CoUninitialize()

        print(f"Failed to convert {hwp_path} after {3} attempts")
        return None

    except Exception as e:
        print(f"Error in convert_hwp_to_pdf: {e}")
        return None


def create_theme_pdfs_printer(theme_codes, log_callback=None):
    if not theme_codes:
        if log_callback:
            log_callback("No theme codes provided.")
        return

    existing_paths = []
    for theme_code in theme_codes:
        theme_hwp = os.path.join(THEME_PATH, f"{theme_code}.hwp")
        if os.path.exists(theme_hwp):
            existing_paths.append(theme_hwp)
            if log_callback:
                log_callback(f"Adding theme file: {theme_hwp}")
        else:
            if log_callback:
                log_callback(f"Theme file not found: {theme_hwp}")

    if not existing_paths:
        if log_callback:
            log_callback("No existing theme files to process.")
        return

    if log_callback:
        log_callback(f"Processing {len(existing_paths)} theme files...")

    # 단일 스레드로 처리 (파일 충돌 방지)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_file = {
            executor.submit(convert_hwp_to_pdf, file): file
            for file in existing_paths
        }

        completed = 0
        total = len(existing_paths)

        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                pdf_path = future.result()
                completed += 1
                progress = int((completed / total) * 100)

                if pdf_path:
                    if log_callback:
                        log_callback(f"Progress: {progress}% - Converted: {os.path.basename(file)}")
                else:
                    if log_callback:
                        log_callback(f"Progress: {progress}% - Failed to convert: {os.path.basename(file)}")
            except Exception as e:
                completed += 1
                progress = int((completed / total) * 100)
                if log_callback:
                    log_callback(f"Progress: {progress}% - Error processing {file}: {str(e)}")

        if log_callback:
            log_callback("Theme PDF creation completed.")


def convert_theme_hwp_to_pdf(hwp_path, log_callback=None):
    """테마 전용 HWP to PDF 변환 함수"""
    pdf_path = hwp_path.replace('.hwp', '.pdf')

    if log_callback:
        log_callback(f"Converting theme: {hwp_path}")

    try:
        # 기존 PDF 체크
        if os.path.exists(pdf_path):
            hwp_time = os.path.getmtime(hwp_path)
            pdf_time = os.path.getmtime(pdf_path)
            if pdf_time > hwp_time:
                pdf_size = os.path.getsize(pdf_path)
                if pdf_size > 10 * 1024:
                    if log_callback:
                        log_callback(f"Theme PDF already exists and is up to date: {pdf_path}")
                    return pdf_path

        # PDF 변환 시도
        for attempt in range(3):
            if log_callback:
                log_callback(f"Theme conversion attempt {attempt + 1}/3 for {os.path.basename(hwp_path)}")

            result = convert_hwp_to_pdf(hwp_path)
            if result:
                if log_callback:
                    log_callback(f"Successfully converted theme: {os.path.basename(hwp_path)}")
                return result

            if attempt < 2:
                time.sleep(2)  # 재시도 전 대기

        if log_callback:
            log_callback(f"Failed to convert theme after 3 attempts: {os.path.basename(hwp_path)}")
        return None

    except Exception as e:
        if log_callback:
            log_callback(f"Error converting theme {hwp_path}: {e}")
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

    # Reduce concurrency to minimize file conflicts
    # Use only 1 worker to avoid file locking issues
    max_workers = 1

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
                else:
                    if log_callback:
                        log_callback(f"Failed to convert: {os.path.basename(file)}")
            except Exception as e:
                if log_callback:
                    log_callback(f"Error processing {file}: {str(e)}")

        # Ensure progress reaches 100%
        if log_callback:
            log_callback("Progress: 100% - PDF creation completed.")
