from duplex_ans import DXAnswerBuilder
from duplex_item import DuplexItemBuilder
from duplex_pro import DuplexProBuilder
from modules.overlayer import Overlayer
from utils.coord import Coord
from utils.overlay_object import *
from utils.pdf_utils import PdfUtils
from utils.ratio import Ratio

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


    def add_page_num(self, overlayer, page_num):
        for num in range(7, page_num):  # 7P부터 시작
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

        front_doc = fitz.open()
        fdo = Overlayer(front_doc)
        fdo.add_page(DXAB.get_component_on_resources(11))        #front 도비라
        fdo.add_page(DXAB.get_component_on_resources(8))        #empty

        curr_page = new_doc.page_count + 2

        DXPB = DuplexProBuilder(self.items, curr_page)
        doc_pro = DXPB.build_page_pro()
        front_doc.insert_pdf(doc_pro)
        curr_page += doc_pro.page_count
        new_doc.insert_pdf(front_doc)
        doc_pro.close()


        back_doc = fitz.open()
        bdo = Overlayer(back_doc)
        if curr_page % 2 == 1:
            bdo.add_page(DXAB.get_component_on_resources(8))        #짝수쪽으로 맞춰주기
            curr_page += 1

        bdo.add_page(DXAB.get_component_on_resources(12))        #back 도비라
        bdo.add_page(DXAB.get_component_on_resources(8))        #empty

        curr_page += 2

        DXIB = DuplexItemBuilder(self.items, curr_page)
        DXIB.rel_ref = DXPB.rel_ref
        DXIB.rel_number = DXPB.rel_number


        for sd_code in self.items.keys():
            if log_callback:
                log_callback(f"Building {sd_code}")

            item_number = self.items[sd_code]['number']

            doc_sd_sol = DXIB.build_page_sd_sol(sd_code)
            back_doc.insert_pdf(doc_sd_sol)
            doc_sd_sol.close()

            doc_theory = DXIB.build_page_theory(sd_code, self.items[sd_code]['list_theory_piece_code'])
            back_doc.insert_pdf(doc_theory)
            doc_theory.close()

            for rel_code in self.items[sd_code]['list_rel_item_code']:
                doc_rel_sol = DXIB.build_page_rel_sol(sd_code, rel_code)
                back_doc.insert_pdf(doc_rel_sol)
                doc_rel_sol.close()


            DXIB.doc_page = 0
            '''
            메모 삽입 로직
            item_overlayer = Overlayer(item_doc)
            for i in range(item_doc.page_count):
                if i % 2 == 0:
                    item_overlayer.pdf_overlay(i, Coord(Ratio.mm_to_px(262 - 12), Ratio.mm_to_px(6 + (item_number * 16)), 0), DXIB.get_component_on_resources(5))
                else:
                    item_overlayer.pdf_overlay(i, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(6 + (item_number * 16)), 0), DXIB.get_component_on_resources(6))

            new_doc.insert_pdf(item_doc)

            item_doc.close()
            '''

        new_doc.insert_pdf(back_doc)

        curr_page = DXIB.curr_page
        page_num_end = curr_page

        # Memopage 삽입 로직, curr_page 제어 필요
        #Footer
        footer_doc = DXAB.build_footer_page(curr_page)
        new_doc.insert_pdf(footer_doc)
        curr_page += footer_doc.page_count
        footer_doc.close()

        # 페이지 번호 삽입
        new_doc_overlayer = Overlayer(new_doc)
        self.add_page_num(new_doc_overlayer, page_num_end + 1)
        PdfUtils.save_to_pdf(new_doc, output, garbage=4)
        new_doc.close()

        if log_callback:
            log_callback(f"Building {output} Done")
        pass