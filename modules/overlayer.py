import fitz
import os
from utils.ratio import Ratio
from utils.coord import Coord
from utils.path import *
import traceback

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
            new_page.set_mediabox(new_page.rect)
            new_page.set_cropbox(new_page.rect)
        pass

    def text_overlay(self, page_num, coord, font_file, size, text, color, text_align):
        font_path = RESOURCES_PATH + "/fonts/" + font_file
        font = fitz.Font(fontfile=font_path)
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

        font_name = os.path.splitext(os.path.basename(font_file))[0]

        page.insert_font(
            fontname=font_name,
            fontfile=font_path
        )

    def shape_overlay(self, page_num, coord, rect, color, radius = None):
        page = self.doc.load_page(page_num)
        page.draw_rect(fitz.Rect(coord.x, coord.y, coord.x + rect.width, coord.y + rect.height), color=color, fill=color, radius=radius)

    def line_overlay(self, page_num, coord, start, end, color, width):
        page = self.doc.load_page(page_num)
        page.draw_line(fitz.Point(coord.x + start.x, coord.y + start.y), fitz.Point(coord.x + end.x, coord.y + end.y), color, width)

    def pdf_overlay(self, page_num, coord, component):
        src_pdf_reader = fitz.open(component.src_pdf)

        try:
            # 원본 페이지 로드
            original_page = src_pdf_reader.load_page(component.src_page_num)

            # 새로운 PDF 문서 생성 및 페이지 복사
            temp_doc = fitz.open()
            new_pdf_page = temp_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
            new_pdf_page.show_pdf_page(new_pdf_page.rect, src_pdf_reader, component.src_page_num)

            src_crop_rect = component.src_rect

            # 새로운 PDF 생성
            dst_page = self.doc.load_page(page_num)

            # 원본 페이지의 전체 영역을 계산
            full_rect = new_pdf_page.rect

            # 원하는 영역 외의 부분에 대해 편집 주석 추가
            if component.src_rect.x0 > 0:
                new_pdf_page.add_redact_annot(fitz.Rect(0, 0, component.src_rect.x0, full_rect.height))
            if component.src_rect.y0 > 0:
                new_pdf_page.add_redact_annot(fitz.Rect(0, 0, full_rect.width, component.src_rect.y0))
            if component.src_rect.x1 < full_rect.width:
                new_pdf_page.add_redact_annot(fitz.Rect(component.src_rect.x1, 0, full_rect.width, full_rect.height))
            if component.src_rect.y1 < full_rect.height:
                new_pdf_page.add_redact_annot(fitz.Rect(0, component.src_rect.y1, full_rect.width, full_rect.height))

            # 편집 적용
            new_pdf_page.apply_redactions()

            x0 = coord.x
            y0 = coord.y
            x1 = x0 + src_crop_rect.width
            y1 = y0 + src_crop_rect.height

            dst_crop_rect = fitz.Rect(x0, y0, x1, y1)

            # 수정된 페이지의 내용을 새 페이지로 복사하면서 위치 조정
            dst_page.show_pdf_page(
                dst_crop_rect,
                temp_doc,
                0,  # temp_doc의 첫 번째 (유일한) 페이지
                clip=src_crop_rect
            )

            # cropbox와 mediabox를 명시적으로 설정
            dst_page.set_mediabox(dst_page.rect)
            dst_page.set_cropbox(dst_page.rect)

            temp_doc.close()

        except Exception as e:
            print(traceback.format_exc())

        src_pdf_reader.close()


    def pdf_overlay_with_resize(self, page_num, coord, component, ratio):
        src_pdf_reader = fitz.open(component.src_pdf)

        try:
            # 원본 페이지 로드
            original_page = src_pdf_reader.load_page(component.src_page_num)

            # 새로운 PDF 문서 생성 및 페이지 복사
            temp_doc = fitz.open()
            new_pdf_page = temp_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
            new_pdf_page.show_pdf_page(new_pdf_page.rect, src_pdf_reader, component.src_page_num)

            src_crop_rect = component.src_rect

            # 새로운 PDF 생성
            dst_page = self.doc.load_page(page_num)

            # 원본 페이지의 전체 영역을 계산
            full_rect = new_pdf_page.rect

            # 원하는 영역 외의 부분에 대해 편집 주석 추가
            if component.src_rect.x0 > 0:
                new_pdf_page.add_redact_annot(fitz.Rect(0, 0, component.src_rect.x0, full_rect.height))
            if component.src_rect.y0 > 0:
                new_pdf_page.add_redact_annot(fitz.Rect(0, 0, full_rect.width, component.src_rect.y0))
            if component.src_rect.x1 < full_rect.width:
                new_pdf_page.add_redact_annot(fitz.Rect(component.src_rect.x1, 0, full_rect.width, full_rect.height))
            if component.src_rect.y1 < full_rect.height:
                new_pdf_page.add_redact_annot(fitz.Rect(0, component.src_rect.y1, full_rect.width, full_rect.height))

            # 편집 적용
            new_pdf_page.apply_redactions()

            x0 = coord.x
            y0 = coord.y
            x1 = x0 + src_crop_rect.width * ratio
            y1 = y0 + src_crop_rect.height * ratio

            dst_crop_rect = fitz.Rect(x0, y0, x1, y1)

            # 수정된 페이지의 내용을 새 페이지로 복사하면서 위치 조정
            dst_page.show_pdf_page(
                dst_crop_rect,
                temp_doc,
                0,  # temp_doc의 첫 번째 (유일한) 페이지
                clip=src_crop_rect
            )

            # cropbox와 mediabox를 명시적으로 설정
            dst_page.set_mediabox(dst_page.rect)
            dst_page.set_cropbox(dst_page.rect)

            temp_doc.close()

        except Exception as e:
            print(traceback.format_exc())

        src_pdf_reader.close()

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