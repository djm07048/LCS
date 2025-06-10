from utils.path import *
from utils.ratio import Ratio
import fitz
import traceback
import os
from utils.ratio import Ratio
from overlayer import *

def kice_trimmer(src_pdf, trim_height=0):
    dst_doc = None
    temp_doc= None
    src_doc = fitz.open(src_pdf)


    try:
        # 원본 페이지 로드
        original_page = src_doc.load_page(0)
        x0 = 0
        y0 = 0
        x1 = original_page.rect.width
        y1 = original_page.rect.height
        original_rect = fitz.Rect(x0, y0, x1, y1)
        original_page.set_cropbox(original_rect)
        original_page.set_mediabox(original_rect)

        # 새로운 PDF 문서 생성 및 페이지 복사
        temp_doc = fitz.open()
        temp_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
        new_pdf_page = temp_doc.load_page(0)
        new_pdf_page.show_pdf_page(new_pdf_page.rect, src_doc, 0)

        src_crop_rect = original_page.rect - fitz.Rect(0, 0, 0, Ratio.mm_to_px(float(trim_height)))

        print(original_page.rect.x0, original_page.rect.y0, original_page.rect.x1, original_page.rect.y1)
        print(src_crop_rect.x0, src_crop_rect.y0, src_crop_rect.x1, src_crop_rect.y1)

        # 새로운 PDF 생성
        dst_doc = fitz.open()
        dst_doc.new_page(width=src_crop_rect.width, height=src_crop_rect.height)
        dst_page = dst_doc.load_page(0)
        print(dst_page.rect.x0, dst_page.rect.y0, dst_page.rect.x1, dst_page.rect.y1)

        # 원하는 영역 외의 부분에 대해 편집 주석 추가
        if src_crop_rect.y1 < new_pdf_page.rect.y1:
            new_pdf_page.add_redact_annot(fitz.Rect(0, src_crop_rect.y1, new_pdf_page.rect.x1, new_pdf_page.rect.y1))

        # 편집 적용
        new_pdf_page.apply_redactions()

        # 수정된 페이지의 내용을 새 페이지로 복사하면서 위치 조정
        dst_page.show_pdf_page(
            src_crop_rect,
            temp_doc,
            0,  # temp_doc의 첫 번째 (유일한) 페이지
            clip=src_crop_rect
        )

        # cropbox와 mediabox를 명시적으로 설정
        dst_page.set_mediabox(dst_page.rect)
        dst_page.set_cropbox(dst_page.rect)

        output_path = src_pdf.replace(".pdf", "_trimmed.pdf")
        dst_doc.save(output_path, garbage=4, deflate=True, clean=True)

        temp_doc.close()
        dst_doc.close()


    except Exception as e:
        print(traceback.format_exc())

    src_doc.close()


def redact_pdf(pdf_file_path, output_pdf_path):
    pdf_reader = fitz.open(pdf_file_path)
    page = pdf_reader.load_page(0)
    crop_rect = page.rect

    try:
        # 원본 페이지 로드
        original_page = pdf_reader.load_page(0)

        # 새로운 PDF 문서 생성 및 페이지 복사
        temp_doc = fitz.open()
        pdf_page = temp_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
        pdf_page.show_pdf_page(pdf_page.rect, pdf_reader, 0)

        # 새로운 PDF 생성
        output_pdf = fitz.open()
        new_page = output_pdf.new_page(width=crop_rect.width, height=crop_rect.height)

        # 원본 페이지의 전체 영역을 계산
        full_rect = pdf_page.rect

        # 원하는 영역 외의 부분에 대해 편집 주석 추가
        if crop_rect.x0 > 0:
            pdf_page.add_redact_annot(fitz.Rect(0, 0, crop_rect.x0, full_rect.height))
        if crop_rect.y0 > 0:
            pdf_page.add_redact_annot(fitz.Rect(0, 0, full_rect.width, crop_rect.y0))
        if crop_rect.x1 < full_rect.width:
            pdf_page.add_redact_annot(fitz.Rect(crop_rect.x1, 0, full_rect.width, full_rect.height))
        if crop_rect.y1 < full_rect.height:
            pdf_page.add_redact_annot(fitz.Rect(0, crop_rect.y1, full_rect.width, full_rect.height))

        # 편집 적용
        pdf_page.apply_redactions()

        # 수정된 페이지의 내용을 새 페이지로 복사하면서 위치 조정
        new_page.show_pdf_page(
            new_page.rect,
            temp_doc,
            0,  # temp_doc의 첫 번째 (유일한) 페이지
            clip=crop_rect
        )

        # cropbox와 mediabox를 명시적으로 설정
        new_page.set_mediabox(new_page.rect)
        new_page.set_cropbox(new_page.rect)

        output_pdf.save(output_pdf_path)
        output_pdf.close()
        temp_doc.close()

    except Exception as e:
        print(f'pdf 저장시 에러 발생: {str(e)}')
        print('상세 로그:')
        print(traceback.format_exc())

    pdf_reader.close()


def native_pdf_crop(pdf_file_path, page_no, crop_box, output_file_path):
    pdf_reader = fitz.open(pdf_file_path)

    try:
        # 원본 페이지 로드
        original_page = pdf_reader.load_page(page_no)

        # 새로운 PDF 문서 생성 및 페이지 복사
        temp_doc = fitz.open()
        pdf_page = temp_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
        pdf_page.show_pdf_page(pdf_page.rect, pdf_reader, page_no)

        crop_rect = fitz.Rect(int(crop_box[0]), int(crop_box[1]), int(crop_box[2]), int(crop_box[3]))

        # 새로운 PDF 생성
        output_pdf = fitz.open()
        new_page = output_pdf.new_page(width=crop_rect.width, height=crop_rect.height)

        # 원본 페이지의 전체 영역을 계산
        full_rect = pdf_page.rect

        # 원하는 영역 외의 부분에 대해 편집 주석 추가
        if crop_rect.x0 > 0:
            pdf_page.add_redact_annot(fitz.Rect(0, 0, crop_rect.x0, full_rect.height))
        if crop_rect.y0 > 0:
            pdf_page.add_redact_annot(fitz.Rect(0, 0, full_rect.width, crop_rect.y0))
        if crop_rect.x1 < full_rect.width:
            pdf_page.add_redact_annot(fitz.Rect(crop_rect.x1, 0, full_rect.width, full_rect.height))
        if crop_rect.y1 < full_rect.height:
            pdf_page.add_redact_annot(fitz.Rect(0, crop_rect.y1, full_rect.width, full_rect.height))

        # 편집 적용
        pdf_page.apply_redactions()

        # temp_doc의 실제 유효 영역을 사용
        temp_page = temp_doc.load_page(0)
        valid_rect = temp_page.rect & crop_rect  # 교집합으로 유효 영역만 사용

        new_page.show_pdf_page(
            new_page.rect,
            temp_doc,
            0,
            clip=valid_rect  # 유효한 영역만 사용
        )
        # cropbox와 mediabox를 명시적으로 설정
        new_page.set_mediabox(new_page.rect)
        new_page.set_cropbox(new_page.rect)

        output_pdf.save(os.path.join(output_file_path))
        output_pdf.close()
        temp_doc.close()

    except Exception as e:
        print(f'pdf 저장시 에러 발생: {str(e)}')
        print('상세 로그:')
        print(traceback.format_exc())

    pdf_reader.close()


def kice_trimmer_with_redaction(src_pdf, crop_rect):
    dst_doc = None
    temp_doc= None
    src_doc = fitz.open(src_pdf)


    try:
        # 원본 페이지 로드
        original_page = src_doc.load_page(0)
        x0 = 0
        y0 = 0
        x1 = original_page.rect.width
        y1 = original_page.rect.height
        original_rect = fitz.Rect(x0, y0, x1, y1)

        new_rect = fitz.Rect(crop_rect[0], crop_rect[1], crop_rect[2], crop_rect[3])
        original_page.set_cropbox(original_rect)
        original_page.set_mediabox(original_rect)

        # 새로운 PDF 문서 생성 및 페이지 복사
        temp_doc = fitz.open()
        temp_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
        new_pdf_page = temp_doc.load_page(0)
        new_pdf_page.show_pdf_page(new_pdf_page.rect, src_doc, 0)

        src_crop_rect = new_rect

        print(original_page.rect.x0, original_page.rect.y0, original_page.rect.x1, original_page.rect.y1)
        print(src_crop_rect.x0, src_crop_rect.y0, src_crop_rect.x1, src_crop_rect.y1)

        # 새로운 PDF 생성
        dst_doc = fitz.open()
        dst_doc.new_page(width=src_crop_rect.width, height=src_crop_rect.height)
        dst_page = dst_doc.load_page(0)
        print(dst_page.rect.x0, dst_page.rect.y0, dst_page.rect.x1, dst_page.rect.y1)

        # 간단하고 확실한 방법 - src_crop_rect 영역만 빼고 전체를 redact
        full_rect = new_pdf_page.rect

        # 전체 영역에서 crop_rect를 뺀 4개 영역만 redact
        # 위쪽
        if src_crop_rect.y0 > 0:
            new_pdf_page.add_redact_annot(fitz.Rect(0, 0, full_rect.width, src_crop_rect.y0))

        # 아래쪽
        if src_crop_rect.y1 < full_rect.height:
            new_pdf_page.add_redact_annot(fitz.Rect(0, src_crop_rect.y1, full_rect.width, full_rect.height))

        # 왼쪽 (crop_rect 높이 범위만)
        if src_crop_rect.x0 > 0:
            new_pdf_page.add_redact_annot(fitz.Rect(0, src_crop_rect.y0, src_crop_rect.x0, src_crop_rect.y1))

        # 오른쪽 (crop_rect 높이 범위만)
        if src_crop_rect.x1 < full_rect.width:
            new_pdf_page.add_redact_annot(
                fitz.Rect(src_crop_rect.x1, src_crop_rect.y0, full_rect.width, src_crop_rect.y1))

        # 편집 적용
        new_pdf_page.apply_redactions()

        # 수정된 페이지의 내용을 새 페이지로 복사하면서 위치 조정
        dst_page.show_pdf_page(
            src_crop_rect,
            temp_doc,
            0,  # temp_doc의 첫 번째 (유일한) 페이지
            clip=src_crop_rect
        )

        # cropbox와 mediabox를 명시적으로 설정
        dst_page.set_mediabox(dst_page.rect)
        dst_page.set_cropbox(dst_page.rect)

        output_path = src_pdf.replace(".pdf", "_trimmed.pdf")
        dst_doc.save(output_path, garbage=4, deflate=True, clean=True)

        temp_doc.close()
        dst_doc.close()


    except Exception as e:
        print(traceback.format_exc())

    src_doc.close()


def kice_trimmer_with_redaction_v2(src_pdf, crop_rect):
    try:
        # Component 클래스가 필요합니다 (src_rect 속성을 가진)
        class Component:
            def __init__(self, src_pdf, src_page_num, src_rect):
                self.src_pdf = src_pdf
                self.src_page_num = src_page_num
                self.src_rect = src_rect

        # 크롭 영역 설정
        src_rect = fitz.Rect(crop_rect[0], crop_rect[1], crop_rect[2], crop_rect[3])
        component = Component(src_pdf, 3, src_rect)

        # 새로운 PDF 문서 생성
        dst_doc = fitz.open()
        overlayer = Overlayer(dst_doc)

        # 크롭된 크기의 페이지 생성
        dst_doc.new_page(width=src_rect.width, height=src_rect.height)

        # Coord 클래스가 필요합니다
        class Coord:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        # (0, 0) 위치에 크롭된 내용 배치
        coord = Coord(0, 0, 0)

        # pdf_overlay 메서드 사용해서 크롭 및 redaction 적용
        overlayer.pdf_overlay(0, coord, component)

        # 결과 저장
        output_path = src_pdf.replace(".pdf", "_trimmed.pdf")
        dst_doc.save(output_path, garbage=4, deflate=True, clean=True)
        dst_doc.close()

        print(f"✅ 성공적으로 저장됨: {output_path}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print(traceback.format_exc())


pdf_path = r"T:\Software\LCS\input\지1지2\2026학년도 6월 지1.pdf"

x0 = Ratio.mm_to_px(157)
y0 = Ratio.mm_to_px(193.5)
x1 = Ratio.mm_to_px(297 - 30)
y1 = Ratio.mm_to_px(420 - 74.5)

crop_box = [x0, y0, x1, y1]

kice_trimmer_with_redaction_v2(pdf_path, crop_box)
#trim_specs = [("E2dbfKC150601", 15.5), ('E2dbcKC200601', 18.5), ('E2dbaKC190603', 11.0), ("E1ebjKC220601", 15.5), ("E2nefKC200914", 19), ("E1pfeKC210617", 8)]
#trim_specs = [("E1hdnKC140102", 20)]
#trim_specs = [("E1gcbKC220608", 9)]
#trim_specs = [("E1meiKC260619", 13.5)]
#trim_specs = [("E1ebhKC260620", 0)]
trim_specs = [("E1jdhKC160911", 8), ("E1iciKC220602", 15)]

for item in trim_specs:
    kice_trimmer(code2original(item[0]), item[1])
    kice_trimmer(code2caption(item[0]), item[1])
