from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import SolutionInfo
from utils.overlay_object import *
from utils.coord import Coord
from utils.parse_code import *
from utils.path import *
import json

def get_problem_dict(path):
    folder_path = Path(path)
    pdf_files = folder_path.glob('**/*.pdf')

    problem_dict = dict()
    for pdf_file in pdf_files:
        pdf_src_path = str(pdf_file)
        item_code = pdf_file.stem
        problem_dict[item_code] = pdf_src_path
    return problem_dict

def get_problem_list(file_path):
    with open(file_path, 'r') as file:
        return file.readline().split(',')

def get_unit_title(unit_code):
    with open(RESOURCES_PATH + "/topic.json", encoding='UTF8') as file:
        topic_data = json.load(file)
    return topic_data[unit_code]

class ProblemBuilder:
    def __init__(self, topic, proitems, page):
        self.topic = topic
        self.proitems = proitems
        self.page = page

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num):
        if num % 4 == 0:
            self.overlayer.add_page(self.get_component_on_resources(2+self.page))
            #append left area to left page
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(20-self.page*2), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 2)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            pass
        elif num % 4 == 1:
            #append right area to left page
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(136-self.page*2), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 2)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            pass
        elif num % 4 == 2:
            self.overlayer.add_page(self.get_component_on_resources(3-self.page))
            #append left area to right page
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(18+self.page*2), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 2)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            pass
        elif num % 4 == 3:
            #append right area to right page
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(134+self.page*2), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 2)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            pass
        pass

    def add_child_to_paragraph(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num):
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph(paragraph, num)
        paragraph.add_child(child)
        return num+1
    
    def add_unit_title(self, page_num, title):
        if page_num % 2 == self.page:
            unit_title_object = TextOverlayObject(page_num, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(14.5), 4), "Pretendard-ExtraBold.ttf", 18, title, (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT)
            unit_title_object.overlay(self.overlayer, unit_title_object.coord)
        # else:
        #     unit_title_object = TextOverlayObject(page_num, Coord(Ratio.mm_to_px(244), Ratio.mm_to_px(14.5), 4), "Pretendard-ExtraBold.ttf", 18, title, (1, 0, 0, 0), fitz.TEXT_ALIGN_RIGHT)

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

    def bake_problem_title(self, problem_num, source = None):
        problem_title = AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(17))
        num_object = TextOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(13), 4), "Pretendard-ExtraBold.ttf", 30, f"{problem_num}", (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT)
        problem_title.add_child(num_object)
        if source is not None:
            text = TextOverlayObject(0, Coord(0,0,0), "Pretendard-Regular.ttf", 12, source, (1,1,1), fitz.TEXT_ALIGN_CENTER)
            text.get_width()
            box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(27), Ratio.mm_to_px(7.5), 2), Rect(0,0,Ratio.mm_to_px(4)+text.get_width(),Ratio.mm_to_px(5.5)), (0,0,0,0.5), 0.5/5.5)
            text.coord = Coord(box.rect.width/2, Ratio.mm_to_px(4.3), 3)
            box.add_child(text)
            problem_title.add_child(box)
            pass
        else:
            with fitz.open(RESOURCES_PATH + "/squeeze_pro_resources.pdf") as file:
                compo = Component(RESOURCES_PATH + "/squeeze_pro_resources.pdf", 6, file.load_page(6).rect)
                box = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(27), Ratio.mm_to_px(7.5), 2), compo)
                problem_title.add_child(box)

        return problem_title

    def bake_problem(self, problem_code, problem_num):
        problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        if problem_code[5:7] == 'KC':  # kice problem
            item_code = problem_code
            item_pdf = parse_item_original_path(item_code)
            modified_pdf = parse_item_modified_path(item_code)
            problem_title = self.bake_problem_title(problem_num, self.code_to_text(problem_code))
            problem.add_child(problem_title)
            problem.height += problem_title.get_height()
            with fitz.open(item_pdf) as file:
                page = file.load_page(0)
                component = Component(item_pdf, 0, page.rect)
                problem_object = ComponentOverlayObject(0, Coord(0, problem.height, 0), component)
                white_box = ShapeOverlayObject(0, Coord(0, 0, 0), Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5.5)),
                                               (0, 0, 0))

                problem.add_child(problem_object)
                problem_object.add_child(white_box)

                problem.height += problem_object.get_height()

                if Path(modified_pdf).exists():
                    problem.height += Ratio.mm_to_px(10)

                    with fitz.open(modified_pdf) as mod_file:
                        mod_page = mod_file.load_page(0)
                        modified_box = ComponentOverlayObject(0, Coord(0, problem.height, 0),
                                                              Component(modified_pdf, 0, mod_page.rect))
                        problem.add_child(modified_box)
                        problem.height -= modified_box.get_height()

                    problem.height -= Ratio.mm_to_px(20)

                problem.height += Ratio.mm_to_px(280) - problem_object.get_height()
        else:  #TODO item problem, kice problem과 동기화 해야 함
            problem_title = self.bake_problem_title(problem_num)
            problem.add_child(problem_title)
            problem.height += problem_title.get_height()
            item_code = problem_code
            item_pdf = get_item_path(item_code) + f"/{item_code[2:5]}/{item_code}/{item_code}.pdf"
            with fitz.open(item_pdf) as file:
                ic = ItemCropper()
                prect = ic.get_problem_rect_from_file(file, 10)
                component = Component(item_pdf, 0, prect)
                problem_object = ComponentOverlayObject(0, Coord(0, problem.height, 0), component)
                white_box = ShapeOverlayObject(0, Coord(0, 0, 0), Rect(0, 0, Ratio.mm_to_px(2.5), Ratio.mm_to_px(5)),
                                               (0, 0, 0))
                problem_object.add_child(white_box)
                problem.add_child(problem_object)
                problem.height += problem_object.get_height()
                problem.height += Ratio.mm_to_px(280) - problem_object.get_height()
        return problem
    
    def get_unit_title(self, unit_code):
        with open(RESOURCES_PATH+"/topic.json", encoding='UTF8') as file:
            topic_data = json.load(file)
        return topic_data[unit_code]
    
    def build(self):
        new_doc = fitz.open()
        #setup
        self.problem_dict = get_problem_dict(ITEM_DB_PATH)

        self.resources_pdf = RESOURCES_PATH + "/squeeze_pro_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

        self.overlayer = Overlayer(new_doc)
        # baseL = self.get_component_on_resources(2)
        # baseR = self.get_component_on_resources(3)
        # baseM = self.get_component_on_resources(4)

        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0
        for item in self.proitems:
            problem_object = self.bake_problem(item['item_code'], item['item_num'])
            paragraph_cnt = self.add_child_to_paragraph(paragraph, problem_object, paragraph_cnt)
            pass

        paragraph.overlay(self.overlayer, Coord(0,0,0))

        for page_num in range(self.overlayer.doc.page_count):
            self.add_unit_title(page_num, self.get_unit_title(self.topic))

        if self.overlayer.doc.page_count % 2 != self.page:
            self.overlayer.add_page(self.get_component_on_resources(4))

        self.resources_doc.close()
        return new_doc
        pass