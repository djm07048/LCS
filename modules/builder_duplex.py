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
        self.items = items
        self.item_dict = []
        for item in self.items:
            unit_item_code = item['item_code'],
            list_rel_item_code = item['list_rel_item_code'],
            list_theory_piece_code = item['list_theory_piece_code'],
            page = 0
            self.item_dict.append([unit_item_code, list_rel_item_code, list_theory_piece_code, page])

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
        for i in self.item_dict:
            if log_callback:
                log_callback(f"Building {i[0]}")

            builder = DuplexItemBuilder(i[0], i[1], i[2], i[3])

            doc_sd = builder.build_page_sd()

            # builder.page += doc_sd.page_count
            doc_rel = builder.build_page_rel()

            # builder.page += doc_rel.page_count
            doc_theory = builder.build_page_theory()

            # builder.page += doc_theory.page_count
            doc_sol = builder.build_page_sol()

            new_doc.insert_pdf(doc_sd)
            new_doc.insert_pdf(doc_rel)
            new_doc.insert_pdf(doc_theory)
            new_doc.insert_pdf(doc_sol)

        new_doc_overlayer = Overlayer(new_doc)
        self.add_page_num(new_doc_overlayer)
        PdfUtils.save_to_pdf(new_doc, output, garbage=4)
        new_doc.close()
        doc_sd.close()
        doc_rel.close()
        doc_theory.close()
        doc_sol.close()

        if log_callback:
            log_callback(f"Building {output} Done")
        pass