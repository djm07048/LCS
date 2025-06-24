from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import SolutionInfo
from utils.overlay_object import *
from utils.coord import Coord
from utils.path import *
from item_cropper import ItemCropper
import json
# KC이면 문항은 original, 해설은 Main에서 가져옴
# NC or 자작이면 문항은 pdf, 해설도 pdf에서 가져옴


class SWProBuilder:
    def __init__(self, items, curr_page):
        self.items = items
        self.curr_page = curr_page
        self.item_cropper = ItemCropper()
        #self.theme_cropper = ThemeCropper()
        self.resources_pdf = RESOURCES_PATH + '/sweep_pro_resources.pdf'
        self.resources_doc = fitz.open(self.resources_pdf)
        self.space_btw_problem = Ratio.mm_to_px(25)
        self.theme_dictionary = self.get_theme_json()

        result = {}
        for item in self.items:
            theme = item["theme"]
            if theme not in result:
                result[theme] = []

            # item_code를 키로, 나머지를 값으로 하는 딕셔너리 추가
            item_data = {k: v for k, v in item.items() if k != "item_code"}
            result[theme].append({item["item_code"]: item_data})
        self.items_by_theme = result
        print(f"Items by theme: {self.items_by_theme}")

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

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

    def arabic2roman(self, number):
        return chr(0x2160 + number - 1)
    # bake title
    def bake_theme_name(self, theme_code, theme_number):
        theme_name = self.get_theme_name(theme_code)

        compo = self.get_component_on_resources(0)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(3.25), Ratio.mm_to_px(6.67), 0),
                                      "GowunBatang-Bold.ttf", 16, f"{self.arabic2roman(theme_number)}" + ". ", (0.2, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        x0 = Ratio.mm_to_px(3.25) + to_number.get_width()
        to_name = TextOverlayObject(0, Coord(x0, Ratio.mm_to_px(6.31), 0),
                                      "Pretendard-SemiBold.ttf", 16, theme_name, (0.2, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        box.add_child(to_number)
        box.add_child(to_name)
        box.rect = compo.src_rect

        return box

    def bake_theme_quotation(self, theme_code):
        theme_quotation = self.get_theme_quotation(theme_code)

        compo_lt = self.get_component_on_resources(1)
        compo_rt = self.get_component_on_resources(2)

        box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(8))
        box.add_child(ComponentOverlayObject(0, Coord(0, 0, 0), compo_lt))

        to_quotation = TextOverlayObject(0, Coord(Ratio.mm_to_px(5.5), Ratio.mm_to_px(5.88), 0),
                                      "강원교육모두 Bold.ttf", 12, theme_quotation, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        x0 = Ratio.mm_to_px(5.5) + to_quotation.get_width()
        box.add_child(to_quotation)
        box.add_child(ComponentOverlayObject(0, Coord(x0, 0, 0), compo_rt))

        box.rect = compo_lt.src_rect    #x1 수정해야

        return box

    def bake_theme_input(self, theme_code):
        box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(12))
        compo_bar1 = self.get_component_on_resources(3)
        box.add_child(ComponentOverlayObject(0, Coord(0, 0, 0), compo_bar1))
        # 여기에 theme cropper로 자른 것을 넣어주기
        compo_bar2 = self.get_component_on_resources(3)
        box.add_child(ComponentOverlayObject(0, Coord(0, Ratio.mm_to_px(6), 0), compo_bar2))
        return box


    def bake_theme_whole(self, theme_code, theme_number):
        theme_box = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(0))
        theme_name = self.bake_theme_name(theme_code, theme_number)
        theme_box.add_child(theme_name)
        curr_y = theme_name.get_height()
        theme_quotation = self.bake_theme_quotation(theme_code)
        theme_quotation.coord.y = curr_y
        curr_y += theme_quotation.get_height()
        theme_box.add_child(theme_quotation)
        theme_input = self.bake_theme_input(theme_code)
        theme_input.coord.y = curr_y
        curr_y += theme_input.get_height()
        theme_box.add_child(theme_input)
        theme_box.height = curr_y
        return theme_box

    def bake_item(self, item_code):
        for item in self.items:
            if item['item_code'] == item_code:
                item_number = item['number']
                item_type = item['type']
                item_plus = item['plus']

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


        compo_problem = self.get_problem_component(item_code)
        co_problem = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(13), 0), compo_problem)
        box.add_child(co_problem)
        box.height = Ratio.mm_to_px(13) + co_problem.get_height() + self.space_btw_problem
        return box

    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num, overlayer: Overlayer,
                                     local_start_page):
        x0_list = [[Ratio.mm_to_px(14), Ratio.mm_to_px(262 - 18 - 110)],
                   [Ratio.mm_to_px(18), Ratio.mm_to_px(262 - 14 - 110)]]
        y0 = Ratio.mm_to_px(22)
        y1 = Ratio.mm_to_px(347)
        height = y1 - y0

        # 현재 작업 중인 페이지의 절대 번호 계산
        current_absolute_page = local_start_page + overlayer.doc.page_count - 1

        # 페이지 타입 확인 (좌수/우수)
        page_side = current_absolute_page % 2  # 0: 좌수, 1: 우수

        # 현재 num에 해당하는 컬럼 (다음이 아닌 현재!)
        current_column = num % 2  # 0: 1단, 1: 2단

        x0 = x0_list[page_side][current_column]

        print(f"  새 리스트 생성: 페이지 {current_absolute_page + 1}({'좌수' if page_side == 0 else '우수'}) {current_column + 1}단")

        # 새 리스트 생성
        doc_page_index = overlayer.doc.page_count - 1
        paragraph_list = ListOverlayObject(doc_page_index, Coord(x0, y0, 0), height, 2)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)

    def add_child_to_paragraph(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num,
                               overlayer: Overlayer, local_start_page):
        # 현재 위치 정보
        current_doc_page = overlayer.doc.page_count - 1
        current_absolute_page = local_start_page + current_doc_page
        current_side = "좌수" if current_absolute_page % 2 == 0 else "우수"
        current_column = (num % 2) + 1

        child_info = self.get_child_info(child)

        if paragraph.add_child(child):
            print(f"✓ {child_info} → 페이지 {current_absolute_page + 1}({current_side}) {current_column}단")
            return num

        print(f"⚠ {child_info} → 현재 위치 공간 부족")

        # 새 리스트 생성
        self.append_new_list_to_paragraph(paragraph, num, overlayer, local_start_page)

        # **우수 2단에서 끝나면** 새 페이지 생성
        if num % 2 == 1:  # 2단(우수)에서 다음으로 넘어갈 때
            new_absolute_page = local_start_page + overlayer.doc.page_count
            template_page_num = 20 - (new_absolute_page % 2)
            overlayer.add_page(self.get_component_on_resources(template_page_num))
            new_side = "좌수" if new_absolute_page % 2 == 0 else "우수"
            print(f"📄 새 페이지 생성: 페이지 {new_absolute_page + 1}({new_side})")

        # 다시 추가 시도
        paragraph.add_child(child)

        # 최종 위치 정보
        final_doc_page = overlayer.doc.page_count - 1
        final_absolute_page = local_start_page + final_doc_page
        final_side = "좌수" if final_absolute_page % 2 == 0 else "우수"
        final_column = (num % 2) + 1
        print(f"✓ {child_info} → 페이지 {final_absolute_page + 1}({final_side}) {final_column}단")

        num += 1
        return num

    def get_child_info(self, child):
        """child 객체에서 디버깅용 정보 추출"""
        if hasattr(child, 'children') and child.children:
            for sub_child in child.children:
                if hasattr(sub_child, 'text'):
                    text = sub_child.text.strip()
                    if text.endswith('.'):  # 테마 번호 (I., II., III. 등)
                        return f"테마 {text}"
                    elif text.isdigit() or (len(text) == 2 and text.isdigit()):  # 문항 번호
                        return f"문항 {int(text):02d}번"
        return f"{type(child).__name__}"

    def build_page_pro(self):
        local_start_page = self.curr_page

        pro_doc = fitz.open()
        self.overlayer = Overlayer(pro_doc)
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        theme_number = 1
        for theme_code in self.items_by_theme.keys():
            theme_whole = self.bake_theme_whole(theme_code, theme_number)
            # 테마 제목 추가
            paragraph_cnt = self.add_child_to_paragraph(paragraph, theme_whole, paragraph_cnt, self.overlayer,
                                                        local_start_page)
            # 문항 추가
            # 더 간단한 수정
            for item_dict in self.items_by_theme[theme_code]:
                for item_code in item_dict.keys():  # 딕셔너리의 키 반복
                    item_whole = self.bake_item(item_code)
                    paragraph_cnt = self.add_child_to_paragraph(paragraph, item_whole, paragraph_cnt, self.overlayer,
                                                                local_start_page)
            theme_number += 1
        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += pro_doc.page_count

        return pro_doc

if __name__ == "__main__":
    items = [
              {
                "item_code": "E1nekZG260101",
                "number": 1,
                "type": "대표",
                "plus": "없음",
                "theme": "aaga",
                "fig": []
              },
              {
                "item_code": "E1aagKC210920",
                "number": 2,
                "type": "기본",
                "plus": "고난도",
                "theme": "aaga",
                "fig": []
              },
              {
                "item_code": "E1aagKC240920",
                "number": 3,
                "type": "발전",
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
                "type": "기본",
                "plus": "고난도",
                "theme": "aagc",
                "fig": []
              },
              {
                "item_code": "E1aagKC240920",
                "number": 7,
                "type": "발전",
                "plus": "없음",
                "theme": "aagc",
                "fig": []
              },
              {
                "item_code": "E1aagKC250617",
                "number": 8,
                "type": "대표",
                "plus": "없음",
                "theme": "aagc",
                "fig": []
              },
              {
                "item_code": "E1aagZG250005",
                "number": 9,
                "type": "발전",
                "plus": "고난도",
                "theme": "aagc",
                "fig": []
              }
            ]
    builder = SWProBuilder(items, 1)

    pro_doc = builder.build_page_pro()
    pro_doc.save("sweep_pro_output.pdf")