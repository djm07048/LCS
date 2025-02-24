import io
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import CMYKColor
from PyPDF2 import PdfReader, PdfWriter
import fitz
from utils.path import *


def create_watermark(output_path, page_width, page_height):
    """워터마크 PDF 생성"""
    font_path = RESOURCES_PATH + r"\fonts\Eulyoo1945-Regular.ttf"
    pdfmetrics.registerFont(TTFont('Eulyoo1945', font_path))

    c = canvas.Canvas(output_path)
    c.setPageSize((page_width, page_height))

    c.setFillColor(CMYKColor(0, 0, 0, 0.3))
    c.setFillAlpha(0.5)
    c.setFont('Eulyoo1945', 40)

    text = "THEDU"
    text_width = c.stringWidth(text, 'Eulyoo1945', 40)
    text_height = 40

    for y in range(-int(page_height), int(page_height * 2), int(text_height * 2)):
        for x in range(-int(page_width), int(page_width * 2), int(text_width)):
            c.saveState()
            c.translate(x, y)
            c.rotate(45)
            c.drawString(0, 0, text)
            c.restoreState()

    c.save()
    return output_path


def add_watermark_and_rasterize(source_pdf, output_pdf, dpi=200, compression_quality=70):
    """
    PDF에 워터마크를 추가하고 레스터화한 후 압축하는 함수

    Args:
        source_pdf (str): 원본 PDF 경로
        output_pdf (str): 출력 PDF 경로
        dpi (int): 해상도 (기본값: 200)
        compression_quality (int): 압축 품질 (1-100, 기본값: 30)
    """
    try:
        reader = PdfReader(source_pdf)
        writer = PdfWriter()

        # 첫 페이지 크기로 워터마크 생성
        first_page = reader.pages[0]
        watermark_path = "temp_watermark.pdf"
        create_watermark(watermark_path, float(first_page.mediabox.width), float(first_page.mediabox.height))
        watermark = PdfReader(watermark_path)
        watermark_page = watermark.pages[0]

        # 각 페이지에 워터마크 추가 후 레스터화
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            # 워터마크 추가
            page.merge_page(watermark_page)

            # 현재 페이지를 임시 PDF로 저장
            temp_writer = PdfWriter()
            temp_writer.add_page(page)
            temp_bytes = io.BytesIO()
            temp_writer.write(temp_bytes)
            temp_bytes.seek(0)

            # PyMuPDF로 레스터화
            doc = fitz.open("pdf", temp_bytes.getvalue())
            pdfpage = doc[0]

            # DPI 설정
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)

            # 이미지로 변환 (압축 설정 적용)
            pix = pdfpage.get_pixmap(matrix=mat, alpha=False)
            img_data = pix.tobytes("jpeg", compression_quality)

            # 다시 PDF로 변환
            img_doc = fitz.open()
            img_page = img_doc.new_page(width=pix.width, height=pix.height)
            img_page.insert_image(
                fitz.Rect(0, 0, pix.width, pix.height),
                stream=img_data
            )

            # PDF 압축 설정 적용
            pdf_bytes = img_doc.tobytes(
                garbage=4,  # 최대 가비지 컬렉션
                deflate=True,  # 디플레이트 압축 사용
                clean=True  # 불필요한 데이터 제거
            )

            # 최종 PDF에 추가
            raster_reader = PdfReader(io.BytesIO(pdf_bytes))
            writer.add_page(raster_reader.pages[0])

            # 메모리 정리
            doc.close()
            img_doc.close()

        # 최종 PDF 저장
        with open(output_pdf, 'wb') as output_file:
            writer.write(output_file)

        # 임시 파일 삭제
        import os
        if os.path.exists(watermark_path):
            os.remove(watermark_path)

        return True

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return False