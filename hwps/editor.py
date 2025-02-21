import os
import pyhwpx
from pyhwpx import Hwp
# 3점 삭제

def delete_3jum(hwp_path):
    hwp = Hwp()
    hwp.XHwpWindows.Item(0).Visible = True
    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    hwp.Open(hwp_path)
    hwp.MoveDocBegin()
    while hwp.find("[3점]"):
        hwp.insert_text("")
    hwp.MoveDocEnd()
    hwp.save(hwp_path)



hwp_path = r"T:\THedu\ItemDB\cah\E1cahZG250001"
delete_3jum(hwp_path)