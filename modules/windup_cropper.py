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

    # width = 225 - 74 + 10 = 161
    # height (maximum) = 344 - 60 + 10 = 294

    # 262에 대하여 70% 축소 인쇄 2단으로 넣으면, 161 * 0.7 * 2 + 36.6 = 262

    def get_piece_area(self, page_number: int) -> Rect:
        if page_number % 2 != 0:  # Left page
            rect = Rect(74 + 10.4 - 5, 60 + 11.9, 225 + 10.4 + 5, 344 + 11.9)
        else:                       # Right page
            rect = Rect(37 + 10.4 - 5, 60 + 11.9, 188 + 10.4 + 5, 344 + 11.9)
        return Ratio.rect_mm_to_px(rect)

    def get_piece_rect(self, page: Page, accuracy=1) -> Rect:
        area = self.get_piece_area(page_number=page.number)
        na = PdfUtils.pdf_clip_to_array(page, area, fitz.Matrix(1, accuracy))
        na = na.mean(axis=1, dtype=np.uint32) // 255

        problem_rect = PdfUtils.trim_whitespace(page, area, Direction.DOWN, accuracy)
        problem_rect = PdfUtils.trim_whitespace(page, problem_rect, Direction.UP, accuracy, padding=(0, 5, 0, 5))
        # 상하 padding +5 적용 (좌우 padding +5는 area 정의 시 이미 적용함)

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
        new_doc.new_page(width=component.src_rect.width, height=component.src_rect.height + Ratio.mm_to_px(12))
        overlayer = Overlayer(new_doc)

        page = AreaOverlayObject(0, Coord(0,0,0), height=component.src_rect.height + Ratio.mm_to_px(12))
        component = self.get_piece_component(component.src_pdf, component.src_page_num)
        page.add_child(ComponentOverlayObject(0, Coord(0,Ratio.mm_to_px(12),0), component))

        file_name = component.src_pdf.split("\\")[-1].replace(".pdf", "")
        text_input = f"{file_name} {component.src_page_num + 1}p"
        to = TextOverlayObject(0, Coord(0, 0, 0), "Pretendard-Regular.ttf", 18, text_input, (0, 0, 0, 0),
                               fitz.TEXT_ALIGN_CENTER)
        to.get_width()
        box = ShapeOverlayObject(0, Coord(0, 0, 0),
                                 Rect(0, 0, Ratio.mm_to_px(6) + to.get_width(), Ratio.mm_to_px(9)),
                                 (0, 0, 0, 0.5), 1 / 8)
        to.coord = Coord(box.rect.width / 2, Ratio.mm_to_px(6.8), 0)
        box.add_child(to)
        page.add_child(box)
        page.overlay(overlayer, Coord(0,0,0))

        return new_doc

    def save_piece_component(self, component, output_folder):
        new_doc = self.overlay_piece_component(component)
        file_name = component.src_pdf.split("\\")[-1].replace(".pdf", "")
        new_doc.save(os.path.join(output_folder, f"{file_name} {component.src_page_num + 1}p.pdf"))
        new_doc.close()

if __name__ == '__main__':
    input_file = r"C:\Users\user\Desktop\LAB\Duplex\WIND UP 고체편.pdf"
    output_folder = r"C:\Users\user\Desktop\LAB\Duplex\output"

    builder = WindupBuilder()
    with fitz.open(input_file) as file:
        page_num = file.page_count
    for i in range(page_num):
        component = builder.get_piece_component(input_file, i)  # Assuming page number 0 for example
        builder.save_piece_component(component, output_folder)
