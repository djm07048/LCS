import fitz
from fitz import Page, Rect
import numpy as np
import os
import json

from utils.direction import Direction
from utils.pdf_utils import PdfUtils
from utils.ratio import Ratio
from utils.problem_info import ProblemInfo
from utils.overlay_object import *
from utils.path import *
from modules.overlayer import Overlayer


#warning: 2014학년도 대수능 지2: 22문항이 정상임

class KiceCropper:
    def __init__(self, pdf_name: str) -> None:
        self.pdf_name = pdf_name
        self.base_name = os.path.basename(self.pdf_name)
    def get_problems_area(self, page: Page, accuracy = 1, offset = 1, padding = (0,0,0,0)) -> Rect:
        #trim left and right
        rect = page.rect
        new_rect = PdfUtils.trim_whitespace(page, rect, Direction.LEFT, accuracy)
        new_rect.x1 -= new_rect.x0 - rect.x0

        # trim up and down
        na = PdfUtils.pdf_clip_to_array(page, new_rect, fitz.Matrix(1, accuracy))
        na = na.mean(axis=1, dtype=np.uint32)
        na = np.where(na < 10, 0, na)
        na = na.mean(axis=1, dtype=np.uint32)

        upper_bound = na.argmin()
        lower_bound = 0
        flag = False
        for y in range(upper_bound, na.shape[0]):
            if na[y] == 255:
                lower_bound = y
                break

        new_rect.y0 = upper_bound / accuracy
        new_rect.y1 = lower_bound / accuracy
        new_rect.y0 += offset
        new_rect.y1 += offset

        # Apply padding
        new_rect.x0 -= Ratio.mm_to_px(padding[0])
        new_rect.y0 -= Ratio.mm_to_px(padding[1])
        new_rect.x1 += Ratio.mm_to_px(padding[2])
        new_rect.y1 += Ratio.mm_to_px(padding[3])

        return new_rect

    def get_problem_rects(self, page: Page, accuracy=1) -> list[Rect]:
        rects = []
        area = self.get_problems_area(page, accuracy, offset=2)

        mid = (area.x0 + area.x1) / 2

        left_area = Rect(area)
        left_area.x1 = mid - Ratio.mm_to_px(5)
        left_area = PdfUtils.trim_whitespace(page, left_area, Direction.RIGHT, accuracy)
        left_area.x0 = left_area.x1 - Ratio.mm_to_px(112.5)
        left_area.x1 += Ratio.mm_to_px(0.5)
        rects += self.get_problem_rects_from_area(page, left_area, accuracy)

        right_area = Rect(area)
        right_area = PdfUtils.trim_whitespace(page, right_area, Direction.RIGHT, accuracy)
        right_area.x0 = right_area.x1 - Ratio.mm_to_px(112.5)
        right_area.x1 += Ratio.mm_to_px(0.5)
        rects += self.get_problem_rects_from_area(page, right_area, accuracy)

        return rects

    def get_problem_rects_from_area(self, page: Page, area: Rect, accuracy=1, number_offset=7) -> list[Rect]:
        number_rect = PdfUtils.trim_whitespace(page, area, Direction.LEFT, accuracy)
        number_rect.x1 = number_rect.x0 + number_offset

        na = PdfUtils.pdf_clip_to_array(page, number_rect, fitz.Matrix(1, accuracy))
        na = na.mean(axis=1, dtype=np.uint32) // 255

        upper_bounds = []
        flag = False
        for y in range(na.shape[0]):
            if np.array_equal(na[y], [1, 1, 1]):
                flag = True
            elif flag and np.array_equal(na[y], [0, 0, 0]):
                flag = False
                upper_bounds.append(y)

        lower_bounds = upper_bounds[1:] + [na.shape[0]]
        for i in range(len(lower_bounds)):
            lower_bounds[i] -= accuracy

        rects = []
        for i in range(len(upper_bounds)):
            new_rect = Rect(area)
            new_rect.y1 = new_rect.y0 + lower_bounds[i] / accuracy
            new_rect.y0 += upper_bounds[i] / accuracy
            rects.append(new_rect)

        ret = []
        for rect in rects:
            new_rect = PdfUtils.trim_whitespace(page, rect, Direction.DOWN, accuracy)
            new_rect.x0 = new_rect.x1 - Ratio.mm_to_px(109)
            new_rect.y0 -= Ratio.mm_to_px(0.5)
            new_rect.y1 += Ratio.mm_to_px(0.5)
            ret.append(new_rect)

        return ret

    def get_problem_infos_from_file(self, file: fitz.Document, accuracy=1) -> list[ProblemInfo]:
        ret = []
        for page_num in range(file.page_count):
            page = file.load_page(page_num)
            rects = self.get_problem_rects(page, accuracy)
            for rect in rects:
                ret.append(ProblemInfo(page_num, rect))
        ret.pop()
        return ret

    def extract_problems(self, accuracy=1) -> int:
        with fitz.open(self.pdf_name) as file:
            self.infos = self.get_problem_infos_from_file(file, accuracy)
            return len(self.infos)

    def get_question_code(self, key: str) -> str | None:
        subject_code = {
            '물1': 'P1',
            '물2': 'P2',
            '화1': 'C1',
            '화2': 'C2',
            '생1': 'B1',
            '생2': 'B2',
            '지1': 'E1',
            '지2': 'E2',
        }
        month_code = {
            '6월': '06',
            '9월': '09',
            '대수능': '11',
            '예비시행': '01',
        }
        with open(RESOURCES_PATH + "/KICEtopic.json", encoding="UTF-8") as file:
            topic_code = json.load(file)

        parts = key.split(' ')
        if key not in topic_code:
            return None
        code = topic_code[key]
        return code

    def save_original(self) -> None:
        with open(RESOURCES_PATH + "/KICEtopic.json", encoding="UTF-8") as file:
            KICEtopic = json.load(file)
        with fitz.open(self.pdf_name) as file:
            for i in range(len(self.infos)):
                rect = self.infos[i].rect
                new_doc = fitz.open()
                new_page = new_doc.new_page(width=rect.width, height=rect.height)
                new_page.show_pdf_page(fitz.Rect(0,0,rect.width,rect.height), file, self.infos[i].page_num, clip=rect)
                new_page.draw_rect(fitz.Rect(0, 0, Ratio.mm_to_px(2.5), Ratio.mm_to_px(5)), color=(1,1,1), fill=(1,1,1))
                key = f'{self.base_name[:-7]} {i+1}번 {self.base_name[-6:-4]}'
                code = self.get_question_code(key)
                if code is None:
                    PdfUtils.save_to_pdf(new_doc, KICE_DB_PATH + f"/others/{key}_original.pdf", garbage=4)
                else:
                    PdfUtils.save_to_pdf(new_doc, KICE_DB_PATH + f"/{code[2:5]}/{code}/{code}_original.pdf", garbage=4)
                #new_doc.save(f"output/original/{self.base_name[:-7]} {i+1}번 {self.base_name[-6:-4]}_original.pdf")

    def save_caption(self, caption_point: tuple, font_size: int) -> None:
        with fitz.open(self.pdf_name) as file:
            for i in range(len(self.infos)):
                rect = self.infos[i].rect
                new_doc = fitz.open()
                new_page = new_doc.new_page(width=rect.width, height=rect.height+Ratio.mm_to_px(caption_point[1]))
                new_page.show_pdf_page(fitz.Rect(0, Ratio.mm_to_px(caption_point[1]),rect.width,rect.height+Ratio.mm_to_px(caption_point[1])), file, self.infos[i].page_num, clip=rect)
                new_page.draw_rect(fitz.Rect(0, Ratio.mm_to_px(caption_point[1]), Ratio.mm_to_px(6), Ratio.mm_to_px(caption_point[1]+5)), color=(1,1,1), fill=(1,1,1))
                font = fitz.Font(fontfile="Eulyoo1945-Regular.ttf")
                tw = fitz.TextWriter(new_page.rect)
                tw.append((Ratio.mm_to_px(caption_point[0]), font_size), f"{os.path.basename(self.pdf_name)[:-4]} {i+1}번 지1", font, font_size)
                tw.write_text(new_page, color=(0,0,0))
                new_doc.save(f"output/caption/{self.base_name[:-7]} {i+1}번 {self.base_name[-6:-4]}_caption.pdf")
                #PdfUtils.extract_to_pdf(file, infos[i].page_num, infos[i].rect, f"output/caption/{os.path.basename(pdf_name)[:-4]} {i+1}번 지1_caption.pdf")


    def bake_origin(self, source):
        text = TextOverlayObject(0, Coord(0,0,0), "Pretendard-Regular.ttf", 12, source, (1,1,1), fitz.TEXT_ALIGN_CENTER)
        text.get_width()
        box = ShapeOverlayObject(0, Coord(0, 0, 0), Rect(0,0,Ratio.mm_to_px(4)+text.get_width(),Ratio.mm_to_px(5.5)), (0,0,0,0.5), 0.5/5.5)
        text.coord = Coord(box.rect.width/2, Ratio.mm_to_px(4.3), 0)
        box.add_child(text)
        return box

    def code_to_text(self, problem_code):
        subject_text = {
            'P1' : '물1',
            'P2' : '물2',
            'C1' : '화1',
            'C2' : '화2',
            'B1' : '생1',
            'B2' : '생2',
            'E1' : '지1',
            'E2' : '지2',
        }
        month_text = {
            '06' : '6월',
            '09' : '9월',
            '11' : '대수능',
            '01' : '예비시행',
        }
        return f"20{problem_code[7:9]}학년도 {month_text[problem_code[9:11]]} {int(problem_code[11:13])}번 {subject_text[problem_code[0:2]]}"

    def save_caption_from_original(self):
        for i in range(len(self.infos)):
            new_doc = fitz.open()
            overlayer = Overlayer(new_doc)
            key = f'{self.base_name[:-7]} {i+1}번 {self.base_name[-6:-4]}'
            code = self.get_question_code(key)
            if code is None:
                continue
            origin = self.bake_origin(self.code_to_text(code))
            origin.coord = Coord(Ratio.mm_to_px(0.25), Ratio.mm_to_px(0.25), 0)
            original_pdf = KICE_DB_PATH + f"/{code[2:5]}/{code}/{code}_original.pdf"
            with fitz.open(original_pdf) as file:
                page = file.load_page(0)
                component = Component(original_pdf, 0, page.rect)
                co = ComponentOverlayObject(0, Coord(0, origin.get_height() + Ratio.mm_to_px(2), 0), component)
            base = AreaOverlayObject(0, Coord(0,0,0), origin.get_height() + co.get_height() + Ratio.mm_to_px(2))
            base.add_child(origin)
            base.add_child(co)
            new_page = new_doc.new_page(width=component.src_rect.width, height=base.get_height())
            base.overlay(overlayer, Coord(0,0,0))
            PdfUtils.save_to_pdf(new_doc, KICE_DB_PATH + f"/{code[2:5]}/{code}/{code}_caption.pdf", garbage=4)


from utils.parse_code import *
def save_caption_from_original_indie(item_code):
    new_doc = fitz.open()
    overlayer = Overlayer(new_doc)
    original_pdf = parse_item_original_path(item_code)
    modification_pdf = original_pdf.replace('_original', '_modification')
    citation = parse_code_citation(item_code)

    # bake_origin
    text = TextOverlayObject(0, Coord(0, 0, 0), "Pretendard-Regular.ttf", 12, citation, (1, 1, 1), fitz.TEXT_ALIGN_CENTER)
    text.get_width()
    box = ShapeOverlayObject(0, Coord(0, 0, 0), Rect(0, 0, Ratio.mm_to_px(4) + text.get_width(), Ratio.mm_to_px(5.5)),
                             (0, 0, 0, 0.5), 0.5 / 5.5)
    text.coord = Coord(box.rect.width / 2, Ratio.mm_to_px(4.3), 0)
    box.add_child(text)
    origin = box

    box.coord = Coord(Ratio.mm_to_px(0.25), Ratio.mm_to_px(0.25), 0)

    # bake_caption
    with fitz.open(original_pdf) as file:
        page = file.load_page(0)
        component = Component(original_pdf, 0, page.rect)
        co = ComponentOverlayObject(0, Coord(0, origin.get_height() + Ratio.mm_to_px(2), 0), component)
        mo_height = 0
        if os.path.exists(modification_pdf):
            modification = Component(modification_pdf, 0, page.rect)
            mo = ComponentOverlayObject(0, Coord(0, origin.get_height() + co.get_height() + Ratio.mm_to_px(10), 0), modification)
            mo_height = mo.get_height()


    base = AreaOverlayObject(0, Coord(0, 0, 0), origin.get_height() + co.get_height() + mo_height + Ratio.mm_to_px(2))
    base.add_child(origin)
    base.add_child(co)
    if os.path.exists(modification_pdf):
        base.add_child(mo)

    new_page = new_doc.new_page(width=component.src_rect.width, height=base.get_height())
    base.overlay(overlayer, Coord(0, 0, 0))
    PdfUtils.save_to_pdf(new_doc, parse_item_caption_path(item_code), garbage=4)

if __name__ == '__main__':
    from pathlib import Path

    folder_path = Path(INPUT_PATH + '/temp')
    pdf_files = sorted(folder_path.glob('*.pdf'))

    for pdf_file in pdf_files:
        pdf_src_path = str(pdf_file)
        item_code = pdf_file.stem
        print(item_code, end=' ')
        kc = KiceCropper(pdf_name=pdf_src_path)
        ret = kc.extract_problems(accuracy=10)
        print(f'extracted {ret} items')
        kc.save_original()
        kc.save_caption_from_original()

