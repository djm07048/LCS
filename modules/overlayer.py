import fitz
from utils.ratio import Ratio
from utils.coord import Coord
from utils.path import *

class PdfManager:
    def __init__(self):
        self.open_pdfs = {}
    
    def get_doc(self, pdf_file):
        if pdf_file not in self.open_pdfs:
            self.open_pdfs[pdf_file] = fitz.open(pdf_file)
        return self.open_pdfs[pdf_file]

class Overlayer:
    def __init__(self, doc):
        self.doc = doc
        self.pdf_manager = PdfManager()
        pass
    def add_page(self, base):
        rect = base.src_rect
        with fitz.open(base.src_pdf) as file:
            new_page = self.doc.new_page(width=rect.width, height=rect.height)
            new_page.show_pdf_page(fitz.Rect(0,0,rect.width,rect.height), file, base.src_page_num, clip=rect)

    def text_overlay(self, page_num, coord, font_file, size, text, color, text_align):
        font = fitz.Font(fontfile=RESOURCES_PATH+"/fonts/"+font_file)
        page = self.doc.load_page(page_num)
        tw = fitz.TextWriter(page.rect)
        x = coord.x
        y = coord.y
        if text_align == fitz.TEXT_ALIGN_CENTER:
            x -= font.text_length(text, size) / 2
        elif text_align == fitz.TEXT_ALIGN_RIGHT:
            x -= font.text_length(text, size)
        
        tw.append((x, y), text, font, size)
        tw.write_text(page, color=color)
        pass

    def shape_overlay(self, page_num, coord, rect, color, radius = None):
        page = self.doc.load_page(page_num)
        page.draw_rect(fitz.Rect(coord.x, coord.y, coord.x + rect.width, coord.y + rect.height), color=color, fill=color, radius=radius)

    def line_overlay(self, page_num, coord, start, end, color, width):
        page = self.doc.load_page(page_num)
        page.draw_line(fitz.Point(coord.x + start.x, coord.y + start.y), fitz.Point(coord.x + end.x, coord.y + end.y), color, width)

    def pdf_overlay(self, page_num, coord, component):
        file = self.pdf_manager.get_doc(component.src_pdf)
        page = self.doc.load_page(page_num)
        x0 = coord.x
        y0 = coord.y
        x1 = x0 + component.src_rect.width
        y1 = y0 + component.src_rect.height
        '''page = file[component.src_page_num]  # 페이지 가져오기
        clip_rect = fitz.Rect(x0, y0, x1, y1)  # 자르고자 하는 영역 설정
        page.set_cropbox(clip_rect)  # 해당 영역으로 페이지 자르기'''
        page.show_pdf_page(fitz.Rect(x0, y0, x1, y1), file, component.src_page_num, clip=component.src_rect)
        pass

    def pdf_overlay_with_resize(self, page_num, coord, component, ratio):
        file = self.pdf_manager.get_doc(component.src_pdf)
        page = self.doc.load_page(page_num)
        x0 = coord.x
        y0 = coord.y
        x1 = x0 + component.src_rect.width * ratio
        y1 = y0 + component.src_rect.height * ratio
        '''page = file[component.src_page_num]  # 페이지 가져오기
        clip_rect = fitz.Rect(x0, y0, x1, y1)  # 자르고자 하는 영역 설정
        page.set_cropbox(clip_rect)  # 해당 영역으로 페이지 자르기'''
        page.show_pdf_page(fitz.Rect(x0, y0, x1, y1), file, component.src_page_num, clip=component.src_rect)
        pass

    def get_bound_coords(self, page_num, coord, component, ratio):
        x0 = coord.x
        y0 = coord.y
        x1 = x0 + component.src_rect.width * ratio
        y1 = y0 + component.src_rect.height * ratio
        L = Coord(x0, (y0 + y1) /2, 0)
        R = Coord(x1, (y0 + y1) /2, 0)
        T = Coord((x0 + x1) /2, y0,0)
        B = Coord((x0 + x1) /2, y1, 0)
        bound_dict = {"page_num": page_num, "L":L, "R":R, "T":T, "B":B}
        return bound_dict

#TODO: object resolver