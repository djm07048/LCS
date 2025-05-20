import json
import fitz
from utils.overlay_object import *
from utils.component import Component
from modules.overlayer import Overlayer
from utils.ratio import Ratio
from utils.path import *
from utils.pdf_utils import PdfUtils

from duplex_item import DuplexItemBuilder
from duplex_ans import DXAnswerBuilder
from utils.coord import Coord

new_doc = fitz.open()


class DXBuilder:
    def __init__(self, items):
        self.items = {
            item['item_code']: {
                'number': item['number'],
                'score': item['score'],
                'para': item['para'],
                'list_rel_item_code': item['list_rel_item_code'],
                'list_theory_piece_code': item['list_theory_piece_code']
            }
            for item in items
        }

    def add_page_num(self, overlayer):
        for num in range(5, overlayer.doc.page_count):  # 5P부터 시작
            if num % 2:
                page_num_object = TextOverlayObject(num - 1, Coord(Ratio.mm_to_px(244), Ratio.mm_to_px(358.5), -1),
                                                    "Pretendard-Bold.ttf", 14, f"{num}", (0, 0, 0, 1),
                                                    fitz.TEXT_ALIGN_RIGHT)
            else:
                page_num_object = TextOverlayObject(num - 1, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(358.5), -1),
                                                    "Pretendard-Bold.ttf", 14, f"{num}", (0, 0, 0, 1),
                                                    fitz.TEXT_ALIGN_LEFT)
            page_num_object.overlay(overlayer, page_num_object.coord)

    def build(self, output, log_callback=None):
        if log_callback:
            log_callback("Duplex Paper Build Start")
            log_callback(f"Building {output}")

        new_doc = fitz.open()

        # Add the quick answer page
        DXAB = DXAnswerBuilder(self.items)
        ans_doc = DXAB.build_answer_page(output)
        new_doc.insert_pdf(ans_doc)
        ans_doc.close()

        for i in self.items.keys():

            item_doc = fitz.open()

            if log_callback:
                log_callback(f"Building {i}")

            DXIB = DuplexItemBuilder(i, self.items[i]['list_rel_item_code'], self.items[i]['list_theory_piece_code'], 0)
            item_number = self.items[i]['number']
            page_count = 0

            doc_sd = DXIB.build_page_sd()
            item_doc.insert_pdf(doc_sd)
            page_count += doc_sd.page_count
            doc_sd.close()

            if len(DXIB.list_theory_piece_code) > 0:
                doc_theory = DXIB.build_page_theory()
                item_doc.insert_pdf(doc_theory)
                page_count += doc_theory.page_count
                doc_theory.close()

            if len(DXIB.list_rel_item_code) > 0:
                doc_rel = DXIB.build_page_rel(item_number)
                item_doc.insert_pdf(doc_rel)
                page_count += doc_rel.page_count
                doc_rel.close()

            if len(DXIB.list_rel_item_code) > 0:
                doc_sol = DXIB.build_page_sol(item_number)
                item_doc.insert_pdf(doc_sol)
                page_count += doc_sol.page_count
                doc_sol.close()

            if page_count % 2 == 1:
                doc_memo = DXIB.build_page_memo()
                item_doc.insert_pdf(doc_memo)
                page_count += doc_memo.page_count
                doc_memo.close()

            item_overlayer = Overlayer(item_doc)
            for i in range(item_doc.page_count):
                if i % 2 == 0:
                    item_overlayer.pdf_overlay(i, Coord(Ratio.mm_to_px(262 - 12), Ratio.mm_to_px(6 + (item_number * 16)), 0), DXIB.get_component_on_resources(5))
                else:
                    item_overlayer.pdf_overlay(i, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(6 + (item_number * 16)), 0), DXIB.get_component_on_resources(6))

            new_doc.insert_pdf(item_doc)

            item_doc.close()

        #Footer
        footer_doc = DXAB.build_footer_page()
        new_doc.insert_pdf(footer_doc)
        footer_doc.close()

        new_doc_overlayer = Overlayer(new_doc)
        self.add_page_num(new_doc_overlayer)
        PdfUtils.save_to_pdf(new_doc, output, garbage=4)
        new_doc.close()

        if log_callback:
            log_callback(f"Building {output} Done")
        pass