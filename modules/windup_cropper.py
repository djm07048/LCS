import fitz
from fitz import Page, Rect
import numpy as np
import os

from utils.direction import Direction
from utils.pdf_utils import PdfUtils
from utils.ratio import Ratio
from utils.problem_info import ProblemInfo
from utils.solution_info import SolutionInfo

from utils.overlay_object import *
from overlayer import Overlayer
from utils.coord import Coord
from utils.path import *
class WindupCropper:
    def __init__(self):
        self.src_pdf = None

    def get_piece_area(self, page_number: int) -> Rect:
        if page_number % 2 != 0:  # Left page
            rect = Rect(85 - 2, 70 - 2, 237 + 2, 350 + 2)
        else:                       # Right page
            rect = Rect(282.8 - 237 - 2, 70 - 2, 282.8 - 85 + 2, 350 + 2)
        return Ratio.rect_mm_to_px(rect)

    def get_piece_rect(self, page: Page, accuracy=1) -> Rect:
        area = self.get_piece_area(page_number=page.number)
        na = PdfUtils.pdf_clip_to_array(page, area, fitz.Matrix(1, accuracy))
        na = na.mean(axis=1, dtype=np.uint32) // 255

        problem_rect = PdfUtils.trim_whitespace(page, area, Direction.DOWN, accuracy)
        problem_rect = PdfUtils.trim_whitespace(page, problem_rect, Direction.UP, accuracy, padding=(0, 1, 0, 1))

        print(f'wc, pagenum: {page.number} / problemrect: {Ratio.px_to_mm(problem_rect)}')

        return problem_rect


class WindupBuilder:
    def __init__(self):
        pass

    def get_piece_component(self, src_pdf, page_num):
        wc = WindupCropper()
        with fitz.open(src_pdf) as file:
            page = file.load_page(page_num)
            component = Component(src_pdf, page_num, wc.get_piece_rect(page, accuracy = 1))
        return component

    def overlay_piece_component(self, component):
        new_doc = fitz.open()
        new_doc.new_page(width=component.src_rect.width, height=component.src_rect.height)
        overlayer = Overlayer(new_doc)

        page = AreaOverlayObject(0, Coord(0,0,0), height=component.src_rect.height)
        component = self.get_piece_component(component.src_pdf, component.src_page_num)
        page.add_child(ComponentOverlayObject(0, Coord(0,0,0), component))

        #TODO: Add Caption

        page.overlay(overlayer, Coord(0,0,0))

        return new_doc

    def save_piece_component(self, component, output_folder):
        new_doc = self.overlay_piece_component(component)
        new_doc.save(os.path.join(output_folder, f"piece_{component.src_page_num}.pdf"))
        new_doc.close()

if __name__ == '__main__':
    input_file = r"C:\Users\user\Desktop\LAB\Duplex\Windup 천체.pdf"
    output_folder = r"C:\Users\user\Desktop\LAB\Duplex\output"

    builder = WindupBuilder()
    for i in range(20):
        component = builder.get_piece_component(input_file, i)  # Assuming page number 0 for example
        builder.save_piece_component(component, output_folder)
