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

# problem.rect width를 110으로 확대하였음!!


class KiceCropper:
    def __init__(self, pdf_name: str) -> None:
        self.pdf_name = pdf_name
        self.base_name = os.path.basename(self.pdf_name)
        self.KICEtopic = None
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
            new_rect.x0 = new_rect.x1 - Ratio.mm_to_px(110)
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

        # 특정 파일에 대해서만 20번째 문제 x0 조정
        target_file = r'T:\Software\LCS\input\temp2\2026학년도 6월 지1.pdf'
        if self.pdf_name == target_file and len(ret) >= 20:
            original_rect = ret[19].rect  # 20번째 문제 (인덱스 19)
            adjusted_rect = fitz.Rect(
                original_rect.x0,
                original_rect.y0 - Ratio.mm_to_px(2.3),
                original_rect.x1,
                original_rect.y1
            )
            ret[19].rect = adjusted_rect
            print(
                f"📝 '{os.path.basename(self.pdf_name)}' 파일의 20번째 문제 x0 조정: {original_rect.x0:.1f} → {adjusted_rect.x0:.1f} (Δ={Ratio.mm_to_px(10):.1f}px)")

        ret.pop()
        return ret

    def extract_problems(self, accuracy=1) -> int:
        with fitz.open(self.pdf_name) as file:
            self.infos = self.get_problem_infos_from_file(file, accuracy)
            return len(self.infos)

    def cite_from_json(self, cite: str) -> str | None:
        if cite not in self.KICEtopic:
            return None
        code = self.KICEtopic[cite]
        return code

    def save_original(self) -> None:            #TODO: key값이 없을 때 처리
        with open(RESOURCES_PATH + "/KICEtopic.json", encoding="UTF-8") as file:
            self.KICEtopic = json.load(file)
        with fitz.open(self.pdf_name) as kice_doc:
            for i in range(len(self.infos)):
                key = f'{self.base_name[:-7]} {i+1}번 {self.base_name[-6:-4]}'
                problem_rect = self.infos[i].rect
                kice_page = kice_doc.load_page(self.infos[i].page_num)

                full_doc = fitz.open()
                full_doc.insert_pdf(kice_doc, from_page=self.infos[i].page_num, to_page=self.infos[i].page_num)
                full_page = full_doc.load_page(0)
                # 여기서 full_page가 cmyk colorspace가 아니라서 문제가 발생함
                # cmyk로 만든 dummy pdf로부터 잘라서 가져오도록 바꾸어야 함,

                if problem_rect.x0 > 0:
                    full_page.add_redact_annot(fitz.Rect(0, 0, problem_rect.x0, full_page.rect.height))
                if problem_rect.y0 > 0:
                    full_page.add_redact_annot(fitz.Rect(0, 0, full_page.rect.width, problem_rect.y0))
                if problem_rect.x1 < full_page.rect.width:
                    full_page.add_redact_annot(fitz.Rect(problem_rect.x1, 0, full_page.rect.width, full_page.rect.height))
                if problem_rect.y1 < full_page.rect.height:
                    full_page.add_redact_annot(fitz.Rect(0, problem_rect.y1, full_page.rect.width, full_page.rect.height))

                full_page.apply_redactions()

                full_doc.new_page(width=problem_rect.width, height=problem_rect.height)

                new_doc = fitz.open()
                new_doc.insert_pdf(full_doc, from_page=1, to_page=1)
                new_page = new_doc.load_page(0)
                full_doc.delete_page(1)
                # 여기서 new_page가 cmyk colorspace가 아니라서 문제가 발생함

                new_page.show_pdf_page(
                    new_page.rect,
                    full_doc,
                    0,
                    clip=problem_rect
                )

                new_page.set_mediabox(new_page.rect)
                new_page.set_cropbox(new_page.rect)
                new_page.draw_rect(fitz.Rect(0, 0, Ratio.mm_to_px(4), Ratio.mm_to_px(5)), color=(0, 0, 0, 0), fill=(0, 0, 0, 0))

                code = self.cite_from_json(key)
                if code is None:
                    PdfUtils.save_to_pdf(new_doc, KICE_DB_PATH + f"/지1/{key}_original.pdf", garbage=4)
                    print(f"saved original for {key}: {KICE_DB_PATH + f'/지1/{key}_original.pdf'}")
                else:
                    PdfUtils.save_to_pdf(new_doc, code2original(code), garbage=4)
                    print(f"saved original for {code}: {code2original(code)}")
                #new_doc.save(f"output/original/{self.base_name[:-7]} {i+1}번 {self.base_name[-6:-4]}_original.pdf")

    def bake_origin(self, source):
        text = TextOverlayObject(0, Coord(0,0,0), "Pretendard-Regular.ttf", 12, source, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        text.get_width()
        box = ShapeOverlayObject(0, Coord(0, 0, 0), Rect(0,0,Ratio.mm_to_px(4)+text.get_width(),Ratio.mm_to_px(5.5)), (0, 0, 0, 0.5), 0.5/5.5)
        text.coord = Coord(box.rect.width/2, Ratio.mm_to_px(4.3), 0)
        box.add_child(text)
        return box
    def save_caption_from_original(self):
        with open(RESOURCES_PATH + "/KICEtopic.json", encoding="UTF-8") as file:
            self.KICEtopic = json.load(file)

        for i in range(len(self.infos)):
            new_doc = fitz.open()
            overlayer = Overlayer(new_doc)
            cite = f'{self.base_name[:-7]} {i+1}번 {self.base_name[-6:-4]}'
            if self.cite_from_json(cite):
                code = self.cite_from_json(cite)
                original_pdf = code2original(code)
            else:
                original_pdf = KICE_DB_PATH + f"/지1/{cite}_original.pdf"
            origin = self.bake_origin(cite)
            origin.coord = Coord(Ratio.mm_to_px(0.25), Ratio.mm_to_px(0.25), 0)
            with fitz.open(original_pdf) as file:
                page = file.load_page(0)
                component = Component(original_pdf, 0, page.rect)
                co = ComponentOverlayObject(0, Coord(0, origin.get_height() + Ratio.mm_to_px(2), 0), component)
            base = AreaOverlayObject(0, Coord(0,0,0), origin.get_height() + co.get_height() + Ratio.mm_to_px(2))
            base.add_child(origin)
            base.add_child(co)
            new_doc.new_page(width=component.src_rect.width, height=base.get_height())
            base.overlay(overlayer, Coord(0,0,0))

            PdfUtils.save_to_pdf(new_doc, original_pdf.replace("_original.pdf", "_caption.pdf"), garbage=4)
            print(f"saved caption for {cite}: {original_pdf.replace('_original.pdf', '_caption.pdf')}")


from utils.path import *
def save_caption_from_original_indie(item_code):
    new_doc = fitz.open()
    overlayer = Overlayer(new_doc)
    original_pdf = code2original(item_code)
    modification_pdf = code2modified(item_code)
    citation = code2cite(item_code)

    # bake_origin
    text = TextOverlayObject(0, Coord(0, 0, 0), "Pretendard-Regular.ttf", 12, citation, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
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
    PdfUtils.save_to_pdf(new_doc, code2caption(item_code), garbage=4)

if __name__ == '__main__':
    from pathlib import Path

    folder_path = Path(r"T:\Software\LCS\input\temp2")
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
