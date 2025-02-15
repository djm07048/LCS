import subprocess
import sys
import os
from glob import glob
from tqdm import tqdm

from hwps.ezpdf import *
from pyhwpx import Hwp


def change_extension(file_path, new_extension):
    base = os.path.splitext(file_path)[0]
    return f"{base}.{new_extension}"


def print_pdf(hwp_path, pdf_path, hwp = Hwp(visible=False)):
    hwp.open(hwp_path, arg="setcurdir:true")
    sec_def = hwp.HParameterSet.HSecDef
    hwp.HAction.GetDefault("PageSetup", sec_def.HSet)
    width = sec_def.PageDef.PaperWidth
    height = sec_def.PageDef.PaperHeight

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

    process1 = subprocess.Popen([sys.executable, "ezpdf.py", pdf_path])  # 파일경로 지정창 접근해서 "확인" 버튼 눌러주는 코드(아래 Execute가 실행되고 나서 작동)
    act.Execute(pset)
    process1.wait()  # 확인 누르고 프로세스 종료