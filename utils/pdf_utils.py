import fitz
from fitz import Rect, Page
import numpy as np
from pathlib import Path
from utils.ratio import *
from utils.direction import Direction

class PdfUtils:
    @staticmethod
    def pdf_clip_to_array(page: Page, rect: Rect, scale = fitz.Matrix(1, 1)) -> np.ndarray:
        pix = page.get_pixmap(clip=rect, matrix=scale)
        na = np.frombuffer(buffer=pix.samples,dtype=np.uint8)
        na = na.reshape((pix.height, pix.width, 3))
        return na
    
    @staticmethod
    def trim_whitespace(page: Page, rect: Rect, direction: Direction, accuracy = 1, padding=(0,0,0,0)) -> Rect:
        scale = fitz.Matrix(accuracy, 1) if direction.value % 2 == 1 else fitz.Matrix(1, accuracy)
        na = PdfUtils.pdf_clip_to_array(page, rect, scale)

        if direction.value % 2 == 1:
            na = np.swapaxes(na, 0, 1)
        na = na.mean(axis=1, dtype=np.uint32) // 255
        if direction.value >= 2:
            na = na[::-1]
        
        trim_amount = 0
        for i in range(na.shape[0]):
            if na[i].mean() < 1:
                trim_amount = i
                break
        
        new_rect = Rect(rect)
        if direction == Direction.UP:
            new_rect.y0 += trim_amount / accuracy
        elif direction == Direction.LEFT:
            new_rect.x0 += trim_amount / accuracy
        elif direction == Direction.DOWN:
            new_rect.y1 -= trim_amount / accuracy
        elif direction == Direction.RIGHT:
            new_rect.x1 -= trim_amount / accuracy

        # Apply padding
        new_rect.x0 -= Ratio.mm_to_px(padding[0])
        new_rect.y0 -= Ratio.mm_to_px(padding[1])
        new_rect.x1 += Ratio.mm_to_px(padding[2])
        new_rect.y1 += Ratio.mm_to_px(padding[3])

        return new_rect
    
    @staticmethod
    def extract_to_pdf(file: fitz.Document, page_num: int, rect: Rect, file_name: str) -> None:
        new_doc = fitz.open()
        new_page = new_doc.new_page(width=rect.width, height=rect.height)
        new_page.show_pdf_page(fitz.Rect(0,0,rect.width,rect.height), file, page_num, clip=rect)
        new_doc.save(file_name)

    @staticmethod
    def save_to_pdf(file: fitz.Document, file_name: str, garbage=4) -> None:        #garbage=4로 해야 모든 서체 포함됨
        path = Path(file_name)
        paths = list(path.parents)[::-1]
        for parent_path in paths:
            if parent_path.exists() == False:
                parent_path.mkdir()
        file.save(file_name, garbage=garbage)