#from sweep_ans import SWAnsBuilder
from sweep_pro import SWProBuilder
from sweep_sol import SWSolBuilder
from sweep_toc import SWTocBuilder
from modules.overlayer import Overlayer
from utils.coord import Coord
from utils.overlay_object import *
from utils.pdf_utils import PdfUtils
from utils.ratio import Ratio

new_doc = fitz.open()


class SWBuilder:
    def __init__(self, items):
        self.items = {
            item['item_code']: {
                'number': item['number'],
                'type': item['type'],
                'plus': item['plus'],
                'theme': item['theme'],
                'fig': item['fig']
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
            log_callback("Sweep Paper Build Start")
            log_callback(f"Building {output}")


        new_doc = fitz.open()
        curr_page_new = 0
        theme_number = 1

        SWTB = SWTocBuilder(self.items, curr_page_new)
        blank_toc_page = SWTB.add_blank_toc_page()
        new_doc.insert_pdf(blank_toc_page)

        SWPB = SWProBuilder(self.items, curr_page_new)

        theme_pages = [curr_page_new]
        # Add the quick answer page
        for theme_code in SWPB.items_by_theme.keys():
            pro_doc = SWPB.build_page_pro(theme_code, theme_number)
            new_doc.insert_pdf(pro_doc)
            pro_doc.close()

        curr_page_new = SWPB.curr_page

        SWSB = SWSolBuilder(self.items, curr_page_new)
        total_doc = fitz.open()
        theme_number = 1
        for theme_code in SWSB.items_by_theme.keys():
            theme_pages.append(SWPB.curr_page)
            sol_doc = fitz.open()
            print(f"Processing theme: {theme_code}, 시작 페이지: {SWSB.curr_page}")
            item_dict = SWSB.items_by_theme[theme_code]
            for item_code in item_dict.keys():
                item_info = SWSB.get_item_info(item_code, theme_code)
                item_type = item_info['type']
                if item_type == '대표':
                    print(f"{SWSB.curr_page} 대표 문항: {item_code}, theme code: {theme_code}")
                    page_rep_sol_lt = SWSB.build_page_rep_sol_lt(item_code, theme_code, theme_number)
                    sol_doc.insert_pdf(page_rep_sol_lt)
                    page_rep_sol_rt = SWSB.build_page_rep_sol_rt(item_code, theme_code, theme_number)
                    sol_doc.insert_pdf(page_rep_sol_rt)
                else:
                    print(f"{SWSB.curr_page} 기본 또는 발전 문항: {item_code}, theme code: {theme_code}")
                    page_sub_sol = SWSB.build_page_sub_sol(item_code, theme_code, theme_number)
                    sol_doc.insert_pdf(page_sub_sol)
            print(f"Theme {theme_code} 완료, 현재 페이지: {SWSB.curr_page}")
            if SWSB.curr_page % 2 == 0:  # 현재 페이지가 홀수면 빈 페이지 추가
                print(f"홀수 페이지이므로 메모 페이지 추가: {theme_code}")
                page_memo = SWSB.build_page_memo(theme_code, theme_number)
                sol_doc.insert_pdf(page_memo)
            total_doc.insert_pdf(sol_doc)
            theme_number += 1
        new_doc.insert_pdf(total_doc)
        total_doc.close()
        curr_page_new = SWSB.curr_page


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