from utils.parse_code import *
from utils.ratio import Ratio
import fitz
import traceback

def kice_trimmer(src_pdf, trim_height=0):
    dst_doc = None
    temp_doc= None
    src_doc = fitz.open(src_pdf)


    try:
        # 원본 페이지 로드
        original_page = src_doc.load_page(0)

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

#trim_specs = [("E1baaKC230601", 19.5), ('E1baaKC250904', 12.0), ('E2babKC150902', 15.0), ('E2babKC151106', 15.0), ('E1badKC240912',20.0), ('E2bafKC160912', 10.0)]
trim_specs = [('E2babKC150902', 15.0)]

for item in trim_specs:
    kice_trimmer(parse_item_original_path(item[0]), trim_height=item[1])
    kice_trimmer(parse_item_caption_path(item[0]), trim_height=item[1])
