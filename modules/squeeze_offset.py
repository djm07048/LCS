from utils.overlay_object import *
from utils.coord import Coord
from modules.overlayer import Overlayer
from utils.path import *
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.parse_code import *
import fitz

class OffsetBuilder:  # TODO 모듈화가 제대로 안됨.. 수정 필요
    def __init__(self, book_doc):
        self.offset_pdf = RESOURCES_PATH + "/squeeze_off_resources.pdf"
        self.offset_doc = fitz.open(self.offset_pdf)
        self.book_doc = book_doc

    def get_component_on_book_pdf(self, page_num):
        return Component(self.book_doc.name, page_num, self.book_doc.load_page(page_num).rect)

    def get_component_on_offset_pdf(self, page_num):
        if page_num < self.offset_doc.page_count:
            return Component(self.offset_pdf, page_num, self.offset_doc.load_page(page_num).rect)
        else:
            raise IndexError(f"page {page_num} not in document")

    def build(self):
        new_doc = fitz.open()
        overlayer = Overlayer(new_doc)
        ob = OffsetBuilder(self.book_doc)  # Pass the book_doc argument

        # Use the total number of pages in book_doc
        total_pages = ob.book_doc.page_count

        ratio = 203.9 / 210.0 * 0.8

        for i in range(total_pages):
            overlayer.add_page(ob.get_component_on_offset_pdf(0))
            component = ob.get_component_on_book_pdf(i)
            oo = ResizedComponentOverlayObject(i, Coord(0, 0, 0), component, ratio)

            oo.overlay(overlayer, Coord(Ratio.mm_to_px(11.342), Ratio.mm_to_px(12.605), 1))

        return overlayer.doc

    def save(self, output_pdf):
        self.build().save(output_pdf)


