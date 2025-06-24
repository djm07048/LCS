from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import ThemeInfo
from utils.overlay_object import *
from utils.coord import Coord
from utils.path import *
from item_cropper import ItemCropper
import json
import os
import json

# exam = 모의고사
# test = 문제지
# ans = 정답
# sol = 해설지


class ExamSol():
    def __init__(self, items):
        self.items = items
        # {item_code1: {'number': 1, 'score': 2, 'para': '1L'},
        #  item_code2: {'number': 2, 'score': 2, 'para': '1R'}, ...}

