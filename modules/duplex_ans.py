from utils.coord import Coord
from utils.ratio import Ratio
import fitz
from utils.path import *
from utils.pdf_utils import PdfUtils
from utils.overlay_object import *
from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path


class DXAnswerBuilder:
    y_list = [114.538, 132.398, 150.23, 168.09, 185.949]
    x_answer_list = [55.536, 101.203, 146.87, 192.537]
    x_score_list = [69.929, 115.596, 161.264, 206.931]

    coord_dict = []
    for number in range(20):
        x_answer0 = x_answer_list[number // 5]
        x_score0 = x_score_list[number // 5]
        y0 = y_list[number % 5]
        coord_dict.append({
            "number": number,
            "answer_coord": Coord(Ratio.mm_to_px(x_answer0), Ratio.mm_to_px(y0), 0),
            "score_coord": Coord(Ratio.mm_to_px(x_score0), Ratio.mm_to_px(y0), 0)
        })

    print(f"coord_dict: {coord_dict}")

    def __init__(self, items, book_name):
        self.items = {}
        self.book_name = book_name
        ic = ItemCropper()

        for item_code, item_data in items.items():
            print(f"item_code: {item_code}, item_data: {item_data}")

            rel_item_answers = []
            for rel_item_code in item_data.get('list_rel_item_code', []):
                rel_item_pdf = code2pdf(rel_item_code)
                rel_answer = self.get_problem_answer(rel_item_pdf)
                rel_item_answers.append(rel_answer)

            dict_entry = {
                item_data['number']: {
                    'item_code': item_code,
                    'score': item_data['score'],  # int; 2 or 3
                    'answer': self.get_problem_answer(code2pdf(item_code)),  # int; 1, 2, 3, 4, 5
                    'rel_item_code': item_data['list_rel_item_code'],  # list of item codes
                    'rel_item_answer': rel_item_answers,  # list of answers
                }
            }
            self.items.update(dict_entry)

        print(f"items: {self.items}")

        self.resources_pdf = RESOURCES_PATH + "/duplex_answer_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

    def get_problem_answer(self, item_pdf):
        try:
            print(f"🔍 PDF 처리 시작: {item_pdf}")

            if not os.path.exists(item_pdf):
                print(f"❌ 파일 없음: {item_pdf}")
                return 0

            with fitz.open(item_pdf) as file:
                if file.page_count == 0:
                    print(f"❌ 빈 파일: {item_pdf}")
                    return 0

                ic = ItemCropper()
                solutions_info = ic.get_solution_infos_from_file(file, 10)
                answer = ic.get_answer_from_file(file)
                print(f"✅ 답안 추출: {answer}")

                answer_dict = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
                if answer in answer_dict:
                    answer = answer_dict[answer]
                else:
                    print(f"❌ 정답 못 찾음: {item_pdf}")
                    answer = 0
                return answer

        except Exception as e:
            print(f"❌ get_problem_answer 오류 - {item_pdf}: {e}")
            return 0
    def build_1p(self):
        return self.resources_doc.load_page(0)

    def get_component_on_header(self, output):
        filename = Path(output).stem

        if filename.split('_')[0] == "EX":  #
            page_num = int(filename.split('_')[-2][:-1]) - 1
            header_pdf = RESOURCES_PATH + "/exam_header_resources.pdf"
            header_doc = fitz.open(header_pdf)
            component = Component(header_pdf, page_num, header_doc.load_page(page_num).rect)

        elif filename.split('_')[0] == "SV":
            page_num = int(filename.split('_')[-2][:-1]) - 1
            header_pdf = RESOURCES_PATH + "/sweep_header_resources.pdf"
            header_doc = fitz.open(header_pdf)
            component = Component(header_pdf, page_num, header_doc.load_page(page_num).rect)

        else:
            kice_list = {"2606E1": 0, "2609E1": 1, "2611E1": 2, "2706E1": 3, "2709E1": 4, "2711E1": 5}
            page_num = kice_list[filename.split('_')[1]]
            header_pdf = RESOURCES_PATH + "/exam_header_kice_resources.pdf"
            header_doc = fitz.open(header_pdf)
            component = Component(header_pdf, page_num, header_doc.load_page(page_num).rect)

        return component

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def build_answer_page(self, output):
        new_doc = fitz.open()
        overlayer = Overlayer(new_doc)

        #page1
        overlayer.add_page(self.get_component_on_resources(9))

        #page2
        overlayer.add_page(self.get_component_on_resources(8))

        #page3
        overlayer.add_page(self.get_component_on_resources(0))

        for number in range(1, 21, 1):
            score = self.items[number]['score']
            answer = self.items[number]['answer']
            score_coord = self.coord_dict[number - 1]['score_coord']
            answer_coord = self.coord_dict[number - 1]['answer_coord']

            answer_compo = self.get_component_on_resources(answer)
            score_compo = self.get_component_on_resources(score + 4)

            overlayer.pdf_overlay(2, answer_coord, answer_compo)
            overlayer.pdf_overlay(2, score_coord, score_compo)

        header_component = self.get_component_on_header(output)
        header_width = header_component.src_rect.width
        overlayer.pdf_overlay(2, Coord(Ratio.mm_to_px(262/2) - header_width/2, Ratio.mm_to_px(47.5), 0), header_component)

        # page4
        overlayer.add_page(self.get_component_on_resources(8))

        new_doc.save(output.replace('.pdf', '_answer.pdf'), garbage=4, deflate=True, clean=True)
        return new_doc

    def build_footer_page(self, local_start_page):
        new_doc = fitz.open()
        overlayer = Overlayer(new_doc)

        exsiting_page_count = local_start_page + 2  # 마지막에 whole_answer_page 및 10번 page를 넣으므로 +1 + 1을 더해야 함
        empty_pages_needed = (4 - exsiting_page_count) % 4  # 4k -> 0 / 4k+1 -> 3 / 4k+2 -> 2 / 4k+3 -> 1
        for i in range(empty_pages_needed):
            overlayer.add_page(self.get_component_on_resources(8))
        whole_answer_doc = self.build_whole_answer_page()
        new_doc.insert_pdf(whole_answer_doc)
        overlayer.add_page(self.get_component_on_resources(10))
        return new_doc

    def build_whole_answer_page(self):
        new_doc = fitz.open()
        overlayer = Overlayer(new_doc)
        overlayer.add_page(self.get_component_on_resources(13))

        def get_item_box_coord(item_number):     #1 따위로 입력됨.
            y0_List = [60 + i * 13.5 for i in range(20)]

            y0 = y0_List[item_number - 1]  # 첫 글자
            return Coord(Ratio.mm_to_px(28), Ratio.mm_to_px(y0), 0)
        def get_rel_box_coord(item_number, rel_item_number):
            x0_List = {"A": 60, "B": 95, "C": 130, "D": 175, "E": 220}
            y0_List = [60 + i * 13.5 for i in range(20)]

            y0 = y0_List[item_number - 1]
            x0 = x0_List[rel_item_number]
            return Coord(Ratio.mm_to_px(x0), Ratio.mm_to_px(y0), 0)
        def bake_item_box(item_number, answer):
            answer_list = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
            answer_text = answer_list.get(answer, "X")  # 답이 없으면 "X"로 표시
            box_color = (0, 0, 0, 0.8) if item_number % 2 == 0 else (1, 0, 0, 0)  # 홀수는 별색, 짝수는 검정
            so = AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(14))
            shape = ShapeOverlayObject(0,  Coord(0,0,0), Rect(0, 0, Ratio.mm_to_px(14), Ratio.mm_to_px(11)),  box_color)
            to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(7), Ratio.mm_to_px(7.5), 0), "Montserrat-Bold.ttf", 18,
                                   str(item_number), (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
            to_answer = TextOverlayObject(0, Coord(Ratio.mm_to_px(21), Ratio.mm_to_px(7), 0), "NanumSquareNeo-cBd.ttf", 15,
                                   answer_text, (0, 0, 0, 1), fitz.TEXT_ALIGN_CENTER)
            so.add_child(shape)
            so.add_child(to_number)
            so.add_child(to_answer)
            return so

        def bake_rel_box(item_number, rel_item_number, rel_answer):
            answer_list = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
            answer_text = answer_list.get(rel_answer, "X")  # 답이 없으면 "X"로 표시
            compo = self.get_component_on_resources(15 - item_number % 2)  # 홀수는 별색, 짝수는 검정
            so = ComponentOverlayObject(0, Coord(0, 0, 0), compo)
            to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(10), Ratio.mm_to_px(7.5), 0), "Montserrat-Bold.ttf", 18,
                                   str(item_number) + str(rel_item_number), (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
            to_answer = TextOverlayObject(0, Coord(Ratio.mm_to_px(27), Ratio.mm_to_px(7), 0), "NanumSquareNeo-cBd.ttf", 15,
                                      answer_text, (0, 0, 0, 1), fitz.TEXT_ALIGN_CENTER)
            so.add_child(to_number)
            so.add_child(to_answer)
            return so

        for item_number, item_data in self.items.items():
            answer = item_data['answer']
            box_coord = get_item_box_coord(item_number)
            so = bake_item_box(item_number, answer)
            so.overlay(overlayer, box_coord)

            for i in range(len(item_data['rel_item_code'])):
                rel_item_number = chr(ord('A') + i)  # 'A', 'B', 'C', 'D' 순서로
                rel_item_answer = item_data['rel_item_answer'][i]
                box_coord = get_rel_box_coord(item_number, rel_item_number)
                so = bake_rel_box(item_number, rel_item_number, rel_item_answer)
                so.overlay(overlayer, box_coord)


        return new_doc