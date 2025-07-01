from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import ThemeInfo
from utils.overlay_object import *
from utils.coord import Coord
from utils.path import *
from item_cropper import ItemCropper
import json
from theme_cropper import ThemeCropper
# KC이면 문항은 original, 해설은 Main에서 가져옴
# NC or 자작이면 문항은 pdf, 해설도 pdf에서 가져옴


class SWSolBuilder:
    def __init__(self, items, curr_page):
        self.items = items
        self.items_dict = {item['item_code']: item for item in self.items}
        self.curr_page = curr_page
        self.resources_pdf = RESOURCES_PATH + '/sweep_pro_resources.pdf'
        self.resources_doc = fitz.open(self.resources_pdf)

        self.duplex_item_pdf = RESOURCES_PATH + '/duplex_item_resources.pdf'
        self.duplex_item_doc = fitz.open(self.duplex_item_pdf)
        self.theme_dictionary = self.get_theme_json()
        print(self.items)
        result = {}
        for item in self.items:
            theme = item["theme"]
            if theme not in result:
                result[theme] = dict()

            # item_code를 키로, 나머지를 값으로 하는 딕셔너리 추가
            item_data = {k: v for k, v in item.items() if k != "item_code"}
            result[theme].update({item["item_code"]: item_data})
        self.items_by_theme = result
        print(f"Items by theme: {self.items_by_theme}")


    def get_theme_json(self):
        theme_json_path = Path(RESOURCES_PATH) / 'theme.json'
        if not theme_json_path.exists():
            raise FileNotFoundError(f"Theme JSON file not found: {theme_json_path}")
        with open(theme_json_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def get_theme_name(self, theme_code):
        return self.theme_dictionary.get(theme_code)[0]

    def get_theme_quotation(self, theme_code):
        return self.theme_dictionary.get(theme_code)[1]

    def get_theme_type_dict(self):
        theme_type_dict = {
            "Off": 4,
            "On": 5
        }
        return theme_type_dict

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def get_component_on_duplex_item_resources(self, page_num):
        return Component(self.duplex_item_pdf, page_num, self.duplex_item_doc.load_page(page_num).rect)

    def get_image_path(self, item_code, image_name):
        item_folder = code2folder(item_code)
        image_stem = f"{item_code}_{image_name}.png"
        image_path = os.path.join(item_folder, image_stem)
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        return image_path

    def get_problem_component(self, item_code):
        ic = ItemCropper()
        if item_code[5:7] == 'KC':
            item_pdf = code2original(item_code)
            trimmed_pdf = item_pdf.replace('.pdf', '_trimmed.pdf')
            if os.path.exists(trimmed_pdf):
                item_pdf = trimmed_pdf
        else:
            item_pdf = code2pdf(item_code)

        with fitz.open(item_pdf) as file:
            page = file.load_page(0)
            component = Component(item_pdf, 0, page.rect) if item_code[5:7] == 'KC' \
                else Component(item_pdf, 0, ic.get_problem_rect_from_file(file, accuracy=1))
        return component

    def bake_theme_bulb_object(self, theme_info, theme_code):
        so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        theme_pdf = os.path.join(THEME_PATH, f'{theme_code}.pdf')
        theme_compo = Component(theme_pdf, 0, theme_info.rect)

        theme_type_dict = self.get_theme_type_dict()
        commentary_data = self.get_commentary_data()

        if theme_info.hexcode not in commentary_data:
            # Handle the missing key case
            print(f"Warning: Hexcode {theme_info.hexcode} not found in commentary data.")
            return None

        commentary_key = commentary_data[theme_info.hexcode]
        if commentary_key not in theme_type_dict:
            # Handle the missing key case
            print(f"Warning: Commentary key {commentary_key} not found in solution type dictionary.")
            return None
        so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(8), Ratio.mm_to_px(0), 2), theme_compo))
        so.height = theme_compo.src_rect.height
        return so

    def bake_lj(self, theme_code):
        theme_pdf = os.path.join(THEME_PATH, f'{theme_code}.pdf')
        print(f"Loading theme PDF: {theme_pdf}")
        with fitz.open(theme_pdf) as file:
            tc = ThemeCropper()
            themes_info = tc.get_theme_infos_from_file(file, 10)

        box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(0))
        curr_y = 0
        header_lj = self.get_component_on_resources(13)
        header_lj_cco = ComponentOverlayObject(0, Coord(0, curr_y, 0), header_lj)
        box.add_child(header_lj_cco)
        curr_y += header_lj.src_rect.height
        print(themes_info)
        commentary_data = self.get_commentary_data()
        for theme_info in themes_info:
            commentary_key = commentary_data[theme_info.hexcode]
            if commentary_key == "On":
                theme_bulb_object = self.bake_theme_bulb_object(theme_info, theme_code)
                theme_bulb_object.coord.y = curr_y
                curr_y += theme_bulb_object.height + Ratio.mm_to_px(1)  # 1mm 여백 추가
                box.add_child(theme_bulb_object)
        compo_bar = self.get_component_on_resources(3)
        compo_bar_cco = ComponentOverlayObject(0, Coord(0, curr_y, 0), compo_bar)
        box.add_child(compo_bar_cco)
        curr_y += compo_bar.src_rect.height
        box.height = curr_y + Ratio.mm_to_px(5)        #5의 여백 추가하기
        return box

    def bake_md(self, item_code, theme_code):
        box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(0))
        header_md = self.get_component_on_resources(14)
        header_md_cco = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0), 0), header_md)
        box.add_child(header_md_cco)
        curr_y = header_md.src_rect.height
        item = self.bake_item(item_code, theme_code)
        item.coord.y = curr_y
        box.add_child(item)
        curr_y += item.get_height()
        box.height = curr_y
        return box

    def bake_image(self, item_code, curr_y, image):
        box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(0))
        header_js = self.get_component_on_resources(15)
        header_js_cco = ComponentOverlayObject(0, Coord(0, curr_y, 0), header_js)
        box.add_child(header_js_cco)
        curr_x = header_js.src_rect.width
        text_js = TextOverlayObject(0, Coord(curr_x, curr_y + Ratio.mm_to_px(6.4),0),
                                      "GmarketSansTTFMedium.ttf", 15, image,
                                      (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        box.add_child(text_js)
        curr_y += header_js.src_rect.height + Ratio.mm_to_px(3)  # 3mm 여백 추가
        image_path = self.get_image_path(item_code, image)
        image_overlay = ImageOverlayObject(0, Coord(Ratio.mm_to_px(55), curr_y, 0), image_path,
                                           max_width= Ratio.mm_to_px(90), max_height=Ratio.mm_to_px(90))
        box.add_child(image_overlay)
        curr_y += image_overlay.get_height() + Ratio.mm_to_px(5)
        memo = self.get_component_on_resources(25)
        memo_cco = ComponentOverlayObject(0, Coord(0, curr_y, 0), memo)
        box.add_child(memo_cco)
        curr_y += memo.src_rect.height + Ratio.mm_to_px(20)  # 20mm 여백 추가
        # image_comment를 추가해야 함!
        return box, curr_y

    def bake_js(self, item_code, theme_code):
        box_whole = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(0))
        image_list = self.get_item_info(item_code, theme_code).get('fig', [])
        curr_y = 0
        for image in image_list:
            box, curr_new_y = self.bake_image(item_code, curr_y, image)
            box_whole.add_child(box)
            curr_y = curr_new_y
        box_whole.height = curr_y
        return box_whole

    def build_page_memo(self, theme_code, theme_number):
        local_start_page = self.curr_page
        doc_memo = fitz.open()
        overlayer = Overlayer(doc_memo)
        self.add_page_with_index(overlayer, 24, local_start_page, theme_code, theme_number)
        # 완료 후 전역 카운터 업데이트
        self.curr_page += doc_memo.page_count

        return doc_memo
    def build_page_rep_sol_lt(self, item_code, theme_code, theme_number):
        # 로컬 페이지 기준점 설정
        local_start_page = self.curr_page
        doc_rep_sol_lt = fitz.open()
        overlayer = Overlayer(doc_rep_sol_lt)
        current_page_index = local_start_page + overlayer.doc.page_count - 1
        template_page_num = 21 + (current_page_index % 2)

        self.add_page_with_index(overlayer, template_page_num, local_start_page, theme_code, theme_number)

        # 페이지 전체 컨테이너 생성 (문서 내 0번 페이지)
        page_container = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(371))

        # 좌단/ 로직 점검하기 추가
        lj_box = self.bake_lj(theme_code)
        curr_x = Ratio.mm_to_px(18 - (current_page_index % 2) * 4)
        curr_y = Ratio.mm_to_px(38)
        lj_box.coord = Coord(curr_x, curr_y, 0)
        curr_y += lj_box.get_height()
        page_container.add_child(lj_box)

        # 좌단/ 문항 다시보기 추가 (로컬 기준)
        md_box = self.bake_md(item_code, theme_code)
        curr_x = Ratio.mm_to_px(18 - (current_page_index % 2) * 4 - 0.762)
        md_box.coord = Coord(curr_x, curr_y, 0)
        curr_y += md_box.get_height()
        page_container.add_child(md_box)

        # 우단/ 자료 살펴보기 부분 추가해야함.
        js_box = self.bake_js(item_code, theme_code)
        curr_x = Ratio.mm_to_px(140 - (current_page_index % 2) * 4)
        curr_y = Ratio.mm_to_px(38)
        js_box.coord = Coord(curr_x, curr_y, 0)
        curr_y += js_box.get_height()
        page_container.add_child(js_box)

        # 전체 컨테이너 오버레이
        page_container.overlay(overlayer, Coord(0, 0, 0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += doc_rep_sol_lt.page_count

        return doc_rep_sol_lt

    def build_page_rep_sol_rt(self, item_code, theme_code, theme_number):
        # 로컬 페이지 기준점 설정
        local_start_page = self.curr_page
        doc_rep_sol_rt = fitz.open()
        overlayer = Overlayer(doc_rep_sol_rt)
        current_page_index = local_start_page + overlayer.doc.page_count - 1
        template_page_num = 21 + (current_page_index % 2)

        self.add_page_with_index(overlayer, template_page_num, local_start_page, theme_code, theme_number)

        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        item_pdf = code2pdf(item_code)
        header_py = self.get_component_on_resources(16)
        header_py_cco = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0), 0), header_py)
        self.add_child_to_paragraph_rep_rt(paragraph, header_py_cco, paragraph_cnt, overlayer, local_start_page, theme_code,
                                           theme_number)
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)
        for solution_info in solutions_info:
            so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], item_pdf)
            paragraph_cnt = self.add_child_to_paragraph_rep_rt(paragraph, so, paragraph_cnt, overlayer, local_start_page, theme_code, theme_number)

        paragraph.overlay(overlayer, Coord(0, 0, 0))
        print(f"Paragraph count: {paragraph_cnt}")
        if paragraph_cnt == 0:      #좌단만 존재하는 경우, 우단에 메모를 넣음
            compo_memo = self.get_component_on_resources(23)
            compo_memo_cco = ComponentOverlayObject(0, Coord(0, 0, 0), compo_memo)
            compo_memo_cco.overlay(overlayer, Coord(0, 0, 0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += doc_rep_sol_rt.page_count

        return doc_rep_sol_rt

    def get_sol_type_dict(self):
        sol_type_dict = {
            "HA": 9,        #ㄱ
            "HB": 10,       #ㄴ
            "HC": 11,       #ㄷ
            "HD": 12,       #ㄹ
            "HE": 13,       #ㅁ
            "NA": 14,       #1
            "NB": 15,       #2
            "NC": 16,       #3
            "ND": 17,       #4
            "NE": 18,       #5
            "EA": 19,       #A
            "EB": 20,       #B
            "EC": 21,       #C
            "arrow": 22,        #화살표
            "clip": 23,         #클립
            "check": 24,        #체크
            "exc_mark": 25,     #느낌표
            "answer": 26,
            "SA": 27,       #linking 1
        }
        return sol_type_dict

    def get_problem_answer(self, item_pdf):
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            answer = ic.get_answer_from_file(file)
            return answer

    def get_commentary_data(self):
        with open(RESOURCES_PATH + "/commentary.json") as file:
            commentary_data = json.load(file)
        return commentary_data

    def append_new_list_to_paragraph_rep(self, paragraph: ParagraphOverlayObject, num, overlayer: Overlayer, local_start_page, align):
        # 페이지 레이아웃 설정
        x0_list = [[Ratio.mm_to_px(14), Ratio.mm_to_px(136)], [Ratio.mm_to_px(18), Ratio.mm_to_px(140)]]
        y0 = Ratio.mm_to_px(38)
        y1 = Ratio.mm_to_px(347)
        height = y1 - y0

        # 현재 페이지의 짝/홀수 확인 (우수/좌수)
        current_absolute_page = local_start_page + overlayer.doc.page_count - 1
        page_side = current_absolute_page % 2

        # 좌단 -> 우단 순으로 적재
        # num이 짝수(0,2,4...)면 좌단, 홀수(1,3,5...)면 우단
        column = num % 2

        # 좌표 선택
        x0 = x0_list[page_side][column]

        # 새 리스트 생성 및 추가
        doc_page_index = overlayer.doc.page_count - 1
        paragraph_list = ListOverlayObject(doc_page_index, Coord(x0, y0, 0), height, align)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)

    def add_child_to_paragraph_rep_rt(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num, overlayer: Overlayer,
                                   local_start_page, theme_code, theme_number=1):

        # 기존 리스트에 추가 가능하면 추가하고 num 그대로 반환
        if paragraph.add_child(child):
            return num

        # 첫 번째 리스트인 경우 (num=0)
        if num == 0:
            # 첫 번째 리스트 생성 (좌단)
            self.append_new_list_to_paragraph_rep(paragraph, num, overlayer, local_start_page, align=0)
            paragraph.add_child(child)
            return num + 1

        # 이전 열 확인 (num-1의 열)
        prev_column = (num - 1) % 2

        # 이전 열이 우단(1)이면 다음 페이지로 넘어감 (좌단->우단 순서에서)
        if prev_column == 1:  # 우단이 채워짐 -> 새 페이지 필요
            # 현재 페이지의 짝/홀수 확인
            new_absolute_page = local_start_page + overlayer.doc.page_count - 1
            template_page_num = 20 + (new_absolute_page % 2)

            self.add_page_with_index(overlayer, template_page_num, local_start_page, theme_code, theme_number)

        self.append_new_list_to_paragraph_rep(paragraph, num, overlayer, local_start_page, align = 0)
        paragraph.add_child(child)
        return num + 1

    def append_new_list_to_paragraph_sub(self, paragraph: ParagraphOverlayObject, num, overlayer: Overlayer, local_start_page, align):
        # 페이지 레이아웃 설정
        x0_list = [[Ratio.mm_to_px(14), Ratio.mm_to_px(136)], [Ratio.mm_to_px(18), Ratio.mm_to_px(140)]]
        y0 = Ratio.mm_to_px(38)
        y1 = Ratio.mm_to_px(347)
        height = y1 - y0

        # 현재 페이지의 짝/홀수 확인 (우수/좌수)
        current_absolute_page = local_start_page + overlayer.doc.page_count - 1
        page_side = current_absolute_page % 2

        # 우단 -> 좌단 순으로 적재
        # num이 짝수(0,2,4...)면 우단, 홀수(1,3,5...)면 좌단
        column = (num + 1) % 2

        # 좌표 선택
        x0 = x0_list[page_side][column]

        # 새 리스트 생성 및 추가
        doc_page_index = overlayer.doc.page_count - 1
        paragraph_list = ListOverlayObject(doc_page_index, Coord(x0, y0, 0), height, align)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)


    def add_child_to_paragraph_sub(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num, overlayer: Overlayer,
                                   local_start_page, theme_code, theme_number=1, align=3):

        # 기존 리스트에 추가 가능하면 추가하고 num 그대로 반환
        if paragraph.add_child(child):
            return num

        # 첫 번째 리스트인 경우 (num=0)
        if num == 0:
            # 첫 번째 리스트 생성 (우단)
            self.append_new_list_to_paragraph_sub(paragraph, num, overlayer, local_start_page, align)
            paragraph.add_child(child)
            return num + 1

        # 두 번째 이상의 리스트인 경우

        # 이전 열 확인 (num-1의 열)
        prev_column = (num - 1) % 2

        # 이전 열이 좌단(1)이면 다음 페이지로 넘어감 (우단->좌단 순서에서)
        if prev_column == 1:  # 좌단이 채워짐 -> 새 페이지 필요
            # 현재 페이지의 짝/홀수 확인
            new_absolute_page = local_start_page + overlayer.doc.page_count - 1
            template_page_num = 20 + (new_absolute_page % 2)

            self.add_page_with_index(overlayer, template_page_num, local_start_page, theme_code, theme_number)

        # 새 리스트 추가
        self.append_new_list_to_paragraph_sub(paragraph, num, overlayer, local_start_page, align)
        paragraph.add_child(child)
        return num + 1

    def add_page_with_index(self, overlayer, resource_page_num, local_start_page, theme_code, theme_number):
        def arabic2roman(number):
            return chr(0x2160 + number - 1)

        overlayer.add_page(self.get_component_on_resources(resource_page_num))

        current_page_index = overlayer.doc.page_count - 1
        page_num = local_start_page + current_page_index
        print(f"Adding page with index: {resource_page_num}, theme_number: {theme_number}, current_page_index: {current_page_index}, page_num: {page_num}")

        if page_num % 2 == 1:       # 좌수
            theme_name = self.get_theme_name(theme_code)
            box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(18))

            to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(7.7), 0),
                                          "GowunBatang-Bold.ttf", 26, f"{arabic2roman(theme_number)}" + ". ",
                                          (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

            x0 = to_number.get_width()
            to_name = TextOverlayObject(0, Coord(x0, Ratio.mm_to_px(7), 0),
                                        "Pretendard-SemiBold.ttf", 24, theme_name, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
            box.add_child(to_number)
            box.add_child(to_name)
            box.height = Ratio.mm_to_px(18)
            box.overlay(overlayer, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(18), 0))

        else:       # 우수
            theme_quotation = self.get_theme_quotation(theme_code)
            compo_lt = self.get_component_on_resources(11)
            compo_rt = self.get_component_on_resources(12)

            box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(18))
            box.add_child(ComponentOverlayObject(0, Coord(0, 0, 0), compo_lt))
            width = compo_lt.src_rect.width
            to_quotation = TextOverlayObject(0, Coord(width, Ratio.mm_to_px(9.76), 0),
                                             "강원교육모두 Bold.ttf", 24, theme_quotation, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
            width += to_quotation.get_width()
            box.add_child(to_quotation)
            box.add_child(ComponentOverlayObject(0, Coord(width, 0, 0), compo_rt))
            width += compo_rt.src_rect.width
            x0 = Ratio.mm_to_px(262 - 18) - width
            box.overlay(overlayer, Coord(x0, Ratio.mm_to_px(18), 0))

        index_object = self.get_component_on_resources(18 - (page_num % 2))
        x0 = Ratio.mm_to_px(0) if page_num % 2 == 1 else Ratio.mm_to_px(242)
        y0 = Ratio.mm_to_px(20 + 70 * theme_number)

        page_num_object = ComponentOverlayObject(current_page_index, Coord(x0, y0, 10), index_object)


        to = TextOverlayObject(current_page_index, Coord(Ratio.mm_to_px(10), Ratio.mm_to_px(17.27), 10),
                               "GowunBatang-Bold.ttf", 16, arabic2roman(theme_number),
                               (0, 0, 0, 1), fitz.TEXT_ALIGN_CENTER)

        page_num_object.add_child(to)
        page_num_object.overlay(overlayer, page_num_object.coord)

    def get_item_info(self, item_code, theme_code):
        """
        아이템 코드에 해당하는 아이템 정보를 반환합니다.
        :param item_code: 아이템 코드 (예: 'E1nekZG260101')
        :return: 아이템 정보 딕셔너리
        """

        item_dict = self.items_by_theme.get(theme_code, [])
        if item_code not in item_dict:
            raise ValueError(f"Item code {item_code} not found in items.")
        return item_dict[item_code]

    def bake_item(self, item_code, theme_code):
        item_info = self.get_item_info(item_code, theme_code)
        item_number = item_info['number']
        item_type = item_info['type']
        item_plus = item_info['plus']

        box = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(1.5), Ratio.mm_to_px(9.31), 0),
                                      "BebasNeue-Regular.ttf", 32, f"{item_number:02d}", (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT)
        box.add_child(to_number)

        type_dict = {
            '대표': 6,
            '기본': 7,
            '발전': 8
        }

        plus_dict = {
            '고난도': 9,
            '신유형': 10
        }

        to_type = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(110 - 18), Ratio.mm_to_px(0), 0),
                                         self.get_component_on_resources(type_dict[item_type]))

        if plus_dict.get(item_plus):
            to_plus = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(110 - 18), Ratio.mm_to_px(0), 0),
                                             self.get_component_on_resources(plus_dict[item_plus]))
            to_type.coord.x -= Ratio.mm_to_px(22)
            box.add_child(to_type)
            box.add_child(to_plus)
        else:
            box.add_child(to_type)

        if item_code[5:7] == 'KC':
            citation = code2cite(item_code)
            to_citation = TextOverlayObject(0, Coord(Ratio.mm_to_px(15), Ratio.mm_to_px(8.8), 0),
                                            "Pretendard-Medium.ttf", 10, citation, (0, 0, 0, 0.7),
                                            fitz.TEXT_ALIGN_LEFT)
            box.add_child(to_citation)

        compo_problem = self.get_problem_component(item_code)
        co_problem = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(13), 0), compo_problem)
        box.add_child(co_problem)
        box.height = Ratio.mm_to_px(13) + co_problem.get_height()
        return box

    def bake_solution_object(self, solution_info, TF, item_pdf):
        so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        so_compo = Component(item_pdf, 0, solution_info.rect)

        sol_type_dict = self.get_sol_type_dict()
        commentary_data = self.get_commentary_data()

        if solution_info.hexcode not in commentary_data:
            # Handle the missing key case
            print(f"Warning: Hexcode {solution_info.hexcode} not found in commentary data.")
            return None

        commentary_key = commentary_data[solution_info.hexcode]
        if commentary_key not in sol_type_dict:
            # Handle the missing key case
            print(f"Warning: Commentary key {commentary_key} not found in solution type dictionary.")
            return None
        if self.get_commentary_data()[solution_info.hexcode] == "answer":
            so_compo = self.get_component_on_duplex_item_resources(26)
            so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2), Ratio.mm_to_px(0), 2), so_compo))
            answer = self.get_problem_answer(item_pdf)
            to = TextOverlayObject(0, Coord(Ratio.mm_to_px(24.5 + 2), Ratio.mm_to_px(5), 2),
                                    "NanumSquareNeo-cBd.ttf", 16,
                                    str(answer), (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
            so.add_child(to)
            so.height = so_compo.src_rect.height + Ratio.mm_to_px(3.5)
        elif self.get_commentary_data()[solution_info.hexcode] == "SA":  # 말풍선
            shade = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(2), 0, -1), Rect(0, 0, Ratio.mm_to_px(105), so_compo.src_rect.height + Ratio.mm_to_px(5)),
                                       (0.2, 0, 0, 0))
            bar = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(1.9),0,  5),
                                     Rect(0, 0, Ratio.mm_to_px(0.2), so_compo.src_rect.height + Ratio.mm_to_px(5)),
                                     (1, 0, 0, 0))
            compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2.5 + 2), Ratio.mm_to_px(2.5), 2),
                                           so_compo)
            so.add_child(shade)
            so.add_child(bar)
            so.add_child(compo)
            so.height = so_compo.src_rect.height + Ratio.mm_to_px(5 + 5 + 2.5)
        else:       #정오 선지
            res_page_num = self.get_sol_type_dict()[self.get_commentary_data()[solution_info.hexcode]]
            type_component = self.get_component_on_duplex_item_resources(res_page_num)
            so.add_child(ComponentOverlayObject(0, Coord(0, 0, 0), type_component))

            OX_component = None
            if TF == 1:
                OX_component = self.get_component_on_duplex_item_resources(7)
            if TF == 0:
                OX_component = self.get_component_on_duplex_item_resources(8)
            if OX_component is not None:
                so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 100), OX_component))

            so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(6.5), Ratio.mm_to_px(6), 2), so_compo))
            so.height = solution_info.rect.height + Ratio.mm_to_px(7)

        return so

    def build_page_sub_sol(self, item_code, theme_code, theme_number):
        # 로컬 페이지 기준점 설정
        local_start_page = self.curr_page
        doc_sub_sol = fitz.open()
        overlayer = Overlayer(doc_sub_sol)
        current_page_index = local_start_page + overlayer.doc.page_count - 1
        template_page_num = 21 + (current_page_index % 2)

        self.add_page_with_index(overlayer, template_page_num, local_start_page, theme_code, theme_number)

        # 페이지 전체 컨테이너 생성 (문서 내 0번 페이지)
        page_container = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(371))

        # 문제 컴포넌트 추가 (로컬 기준)
        problem_cco = self.bake_item(item_code, theme_code)
        problem_x = Ratio.mm_to_px(18 - (current_page_index % 2) * 4 - 0.762)
        problem_cco.coord = Coord(problem_x, Ratio.mm_to_px(38), 0)
        page_container.add_child(problem_cco)

        # 전체 컨테이너 오버레이
        page_container.overlay(overlayer, Coord(0, 0, 0))

        # 솔루션 부분 (로컬 기준으로 처리)
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        item_pdf = code2pdf(item_code)
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)

        solutions_info.reverse()
        for solution_info in solutions_info:
            so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], item_pdf)
            paragraph_cnt = self.add_child_to_paragraph_sub(paragraph, so, paragraph_cnt, overlayer, local_start_page, theme_code, theme_number)

        paragraph.overlay(overlayer, Coord(0, 0, 0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += doc_sub_sol.page_count

        return doc_sub_sol

if __name__ == "__main__":
    items = [
              {
                "item_code": "E1nekZG260101",
                "number": 1,
                "type": "대표",
                "plus": "없음",
                "theme": "aagc",
                "fig": ["그림", "그림2"]
              },
              {
                "item_code": "E1aagKC210920",
                "number": 2,
                "type": "기본",
                "plus": "신유형",
                "theme": "aagc",
                "fig": []
              },
              {
                "item_code": "E1aagKC240920",
                "number": 3,
                "type": "대표",
                "plus": "없음",
                "theme": "aagb",
                "fig": []
              },
              {
                "item_code": "E1aagKC250617",
                "number": 4,
                "type": "대표",
                "plus": "없음",
                "theme": "aagb",
                "fig": []
              },
              {
                "item_code": "E1aagZG250005",
                "number": 5,
                "type": "발전",
                "plus": "고난도",
                "theme": "aagb",
                "fig": []
              },
              {
                "item_code": "E1aagKC210920",
                "number": 6,
                "type": "대표",
                "plus": "고난도",
                "theme": "aaga",
                "fig": []
              },
              {
                "item_code": "E1aagKC240920",
                "number": 7,
                "type": "발전",
                "plus": "없음",
                "theme": "aaga",
                "fig": []
              },
              {
                "item_code": "E1aagKC250617",
                "number": 8,
                "type": "발전",
                "plus": "없음",
                "theme": "aaga",
                "fig": []
              },
              {
                "item_code": "E1aagZG250005",
                "number": 9,
                "type": "발전",
                "plus": "고난도",
                "theme": "aaga",
                "fig": []
              }
            ]
    SWSB = SWSolBuilder(items, 1)
    total_doc = fitz.open()
    theme_number = 1
    for theme_code in SWSB.items_by_theme.keys():
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
    path = Path(OUTPUT_PATH) / 'sweep_sol.pdf'
    total_doc.save(path, deflate=True, garbage=4, clean=True)