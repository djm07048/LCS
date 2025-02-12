from utils.overlay_object import *
from utils.coord import Coord
from modules.overlayer import *
from utils.path import *
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.parse_code import *
import fitz


class OffsetBuilder:        #TODO builder 안에 넣을 수 있도록 모듈화
    def __init__(self):
        offset_pdf = RESOURCES_PATH + "/offset/A4.pdf"
        book_pdf = OUTPUT_PATH + "/SQ_고체1.pdf"
        self.book_pdf = book_pdf
        self.offset_pdf = offset_pdf
        self.offset_doc = fitz.open(offset_pdf)
        self.book_doc = fitz.open(book_pdf)

    def get_component_on_book_pdf(self, page_num):
        return Component(self.book_pdf, page_num, self.book_doc.load_page(page_num).rect)

    def get_component_on_offset_pdf(self, page_num):
        return Component(self.offset_pdf, page_num, self.offset_doc.load_page(page_num).rect)


    def build(self):

        new_doc = fitz.open()
        overlayer = Overlayer(new_doc)
        ob = OffsetBuilder()

        # Use the total number of pages in book_doc
        total_pages = ob.book_doc.page_count

        for i in range(total_pages):
            overlayer.add_page(ob.get_component_on_offset_pdf(0))
            component = ob.get_component_on_book_pdf(i)
            oo = ResizedComponentOverlayObject(i, Coord(0, 0, 0), component, 0.801)
            oo.overlay(overlayer, Coord(Ratio.mm_to_px(8.3), Ratio.mm_to_px(8.3), 1))

        return overlayer.doc

