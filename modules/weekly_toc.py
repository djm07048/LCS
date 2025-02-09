import pathlib

from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import SolutionInfo
from utils.overlay_object import *
from utils.coord import Coord
from utils.path import *
import json

class TocBuilder:
    def __init__(self, output):
        self.page_amount = 0
        self.output = output

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def build(self):
        new_doc = fitz.open()
        output_pdf_name = pathlib.PurePath(self.output).stem

        self.resources_pdf = RESOURCES_PATH + f"/TOC/TOC_{output_pdf_name}.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)
        self.overlayer = Overlayer(new_doc)

        self.page_amount = 3

        self.overlayer.add_page(self.get_component_on_resources(0))
        self.overlayer.add_page(self.get_component_on_resources(1))
        self.overlayer.add_page(self.get_component_on_resources(2))

        self.resources_doc.close()
        return new_doc