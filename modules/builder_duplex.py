import json
import fitz
from utils.overlay_object import *
from utils.component import Component
from modules.overlayer import Overlayer
from utils.ratio import Ratio
from utils.path import *
from utils.pdf_utils import PdfUtils

from duplex_item import DuplexItemBuilder

new_doc = fitz.open()


class DXBuilder:
    def __init__(self, items):
        self.items = {
            item['item_code']: {
                'list_rel_item_code': item['list_rel_item_code'],
                'list_theory_piece_code': item['list_theory_piece_code']
            }
            for item in items
        }
        print(self.items)

    def add_page_num(self, overlayer):
        for num in range(1, overlayer.doc.page_count):  # 5P부터 시작
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
        for i in self.items.keys():
            if log_callback:
                log_callback(f"Building {i}")

            builder = DuplexItemBuilder(i, self.items[i]['list_rel_item_code'], self.items[i]['list_theory_piece_code'], 0)

            doc_sd = builder.build_page_sd()
            new_doc.insert_pdf(doc_sd)
            builder.page += doc_sd.page_count
            doc_sd.close()

            if len(builder.list_rel_item_code) > 0:
                doc_rel = builder.build_page_rel()
                new_doc.insert_pdf(doc_rel)
                builder.page += doc_rel.page_count
                doc_rel.close()

            if len(builder.list_theory_piece_code) > 0:
                doc_theory = builder.build_page_theory()
                new_doc.insert_pdf(doc_theory)
                builder.page += doc_theory.page_count
                doc_theory.close()

            if len(builder.list_rel_item_code) > 0:
                doc_sol = builder.build_page_sol()
                new_doc.insert_pdf(doc_sol)
                builder.page += doc_sol.page_count
                doc_sol.close()

        new_doc_overlayer = Overlayer(new_doc)
        self.add_page_num(new_doc_overlayer)
        PdfUtils.save_to_pdf(new_doc, output, garbage=4)
        new_doc.close()

        if log_callback:
            log_callback(f"Building {output} Done")
        pass