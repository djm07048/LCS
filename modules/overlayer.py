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

    def text_overlay(self, page_num, coord, font_file, size, text, color, text_align, weight=None):
        """
        텍스트 오버레이 함수 (Variable Font weight 지원)

        Args:
            page_num: 페이지 번호
            coord: 좌표 객체
            font_file: 폰트 파일명
            size: 폰트 크기
            text: 텍스트 내용
            color: 색상
            text_align: 텍스트 정렬
            weight: Variable Font의 weight (None이면 기본값 사용)
        """
        font_path = RESOURCES_PATH + "/fonts/" + font_file

        try:
            # 폰트 로드
            font = fitz.Font(fontfile=font_path)

            # Variable Font weight 설정
            if weight is not None and hasattr(font, 'set_variation'):
                font.set_variation(wght=weight)

            page = self.doc.load_page(page_num)
            tw = fitz.TextWriter(page.rect)

            x = coord.x
            y = coord.y

            # 텍스트 정렬 계산
            if text_align == fitz.TEXT_ALIGN_CENTER:
                x -= font.text_length(text, size) / 2
            elif text_align == fitz.TEXT_ALIGN_RIGHT:
                x -= font.text_length(text, size)

            tw.append((x, y), text, font, size)
            tw.write_text(page, color=color)

            # 폰트 이름 처리 (Variable Font의 경우 weight 정보 포함)
            font_name = os.path.splitext(os.path.basename(font_file))[0]
            if weight is not None:
                font_name += f"-{weight}"

            page.insert_font(
                fontname=font_name,
                fontfile=font_path
            )

        except Exception as e:
            print(f"텍스트 오버레이 실패: {e}")
            # Fallback: weight 없이 기본 방식으로 시도
            if weight is not None:
                print(f"Weight {weight} 적용 실패, 기본 방식으로 재시도")
                self.text_overlay(page_num, coord, font_file, size, text, color, text_align, weight=None)

    # Variable Font Weight 상수 클래스
    class FontWeights:
        THIN = 100
        EXTRA_LIGHT = 200
        LIGHT = 300
        REGULAR = 400
        MEDIUM = 500
        SEMI_BOLD = 600
        BOLD = 700
        EXTRA_BOLD = 800
        BLACK = 900

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

    def image_overlay(self, page_num, coord, image_path, dpi=300, max_width=None, max_height=None):
        """
        DPI를 적용하여 이미지를 PDF 페이지에 오버레이 (top-center 정렬)

        Args:
            page_num: 페이지 번호
            coord: 이미지 배치 기준 좌표 (중심선의 상단 지점)
            image_path: 이미지 파일 경로
            dpi: 이미지 해상도 (기본값: 300)
            max_width: 최대 너비 제한 (None이면 제한 없음)
            max_height: 최대 높이 제한 (None이면 제한 없음)

        Returns:
            dict: 배치된 이미지의 경계 좌표 정보
        """
        try:
            # 이미지 파일 존재 확인
            if not os.path.exists(image_path):
                print(f"이미지 파일을 찾을 수 없습니다: {image_path}")
                return None

            # 페이지 로드
            page = self.doc.load_page(page_num)

            # 이미지를 PDF 문서로 변환
            img_doc = fitz.open(image_path)
            img_page = img_doc.load_page(0)

            # 원본 이미지 크기 (포인트 단위)
            original_rect = img_page.rect
            original_width = original_rect.width
            original_height = original_rect.height

            # DPI 변환 계산
            # 기본 PDF DPI는 72, 따라서 dpi/72가 스케일 팩터
            scale_factor = dpi / 72.0

            # DPI 적용된 크기 계산
            scaled_width = original_width * scale_factor
            scaled_height = original_height * scale_factor

            # 최대 크기 제한 적용 (항상 종횡비 유지)
            final_width = scaled_width
            final_height = scaled_height

            if max_width is not None or max_height is not None:
                # 종횡비 유지하면서 크기 조정
                width_ratio = max_width / scaled_width if max_width else float('inf')
                height_ratio = max_height / scaled_height if max_height else float('inf')

                # 더 작은 비율 적용
                resize_ratio = min(width_ratio, height_ratio, 1.0)  # 1.0을 넘지 않도록

                final_width = scaled_width * resize_ratio
                final_height = scaled_height * resize_ratio

            # Top-Center 정렬을 위한 좌표 계산
            # coord.x는 이미지의 중심선, coord.y는 이미지의 상단
            center_x = coord.x
            top_y = coord.y

            # 실제 배치 좌표 계산
            x0 = center_x - (final_width / 2)  # 중심에서 절반만큼 왼쪽으로
            y0 = top_y  # 상단은 그대로
            x1 = x0 + final_width
            y1 = y0 + final_height

            target_rect = fitz.Rect(x0, y0, x1, y1)

            # 이미지 삽입
            page.show_pdf_page(
                target_rect,
                img_doc,
                0,  # 첫 번째 페이지
                clip=original_rect
            )

            # 이미지 문서 닫기
            img_doc.close()

            # 경계 좌표 정보 반환
            bound_info = {
                "page_num": page_num,
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "width": final_width,
                "height": final_height,
                "center_x": center_x,  # 원래 지정한 중심점
                "center_y": (y0 + y1) / 2,  # 실제 이미지 중심점
                "dpi": dpi,
                "scale_factor": scale_factor
            }

            print(f"이미지 오버레이 완료 (Top-Center): {image_path}")
            print(f"기준점: ({center_x:.1f}, {top_y:.1f}), 실제위치: ({x0:.1f}, {y0:.1f})")
            print(f"크기: {final_width:.1f}x{final_height:.1f}")

            return bound_info

        except Exception as e:
            print(f"이미지 오버레이 실패: {e}")
            print(traceback.format_exc())
            return None


#TODO: object resolver