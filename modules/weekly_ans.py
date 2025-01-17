from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import SolutionInfo
from utils.overlay_object import *
from utils.coord import Coord
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
    with open("resources/topic.json", encoding='UTF8') as file:
        topic_data = json.load(file)
    return topic_data[unit_code]

def append_new_list_to_paragraph(paragraph: ParagraphOverlayObject, num, overlayer, base):
    if num % 2 == 0:
        overlayer.add_page(base)
        #append left area
        paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(25.5), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 0)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)
        pass
    else:
        #append right area on last page
        paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(136.5), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 0)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)
        pass
    pass

def add_child_to_paragraph(paragraph: ParagraphOverlayObject, child: OverlayObject, num, overlayer, base):
    if paragraph.add_child(child): return num
    append_new_list_to_paragraph(paragraph, num, overlayer, base)
    paragraph.add_child(child)
    return num+1

def bake_unit_cover(resources_pdf, resources_doc, unit_code, num):
    component = Component(resources_pdf, 2+(num-1)%3, resources_doc.load_page(2).rect)
    unit_cover = AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(30))
    unit_cover.add_child(ComponentOverlayObject(0, Coord(0,0,0), component))
    unit_cover.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(49), Ratio.mm_to_px(6), 1), "resources/fonts/Pretendard-Bold.ttf", 13, f"{num}. {get_unit_title(unit_code)}", tuple([int(num%3 == 1)]*3), fitz.TEXT_ALIGN_CENTER))
    return unit_cover

def bake_unit(resources_pdf, resources_doc, unit_code, num, problem_num, unit_problem_answers):
    unit = bake_unit_cover(resources_pdf, resources_doc, unit_code, num)
    component = Component(resources_pdf, 5+(num-1)%3, resources_doc.load_page(5).rect)
    cnt = len(unit_problem_answers)
    for i in range(1,(cnt-1)//5+1):
        unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), component))
        unit.height += component.src_rect.height
    if cnt%5 != 0:
        rect = resources_doc.load_page(5).rect
        rect.x1 = rect.x0 + Ratio.mm_to_px(9.8) * 2 * (cnt%5) - 1
        last_component = Component(resources_pdf, 5+(num-1)%3, rect)
        unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), last_component))
        unit.height += last_component.src_rect.height
    
    default_y = Ratio.mm_to_px(30+6.5)
    default_num_x = Ratio.mm_to_px(4.9)
    default_ans_x = Ratio.mm_to_px(14.7)
    for i in range(len(unit_problem_answers)):
        unit.add_child(TextOverlayObject(0, Coord(default_num_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(10)*(i//5), 1), "resources/fonts/Pretendard-Medium.ttf", 13, f"{i+problem_num}", tuple([int(num%3 == 1)]*3), fitz.TEXT_ALIGN_CENTER))
        unit.add_child(TextOverlayObject(0, Coord(default_ans_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(10)*(i//5), 1), "resources/fonts/NanumSquareNeo-cBd.ttf", 13, f"{unit_problem_answers[i]}", tuple([0]), fitz.TEXT_ALIGN_CENTER))
    return unit

def get_problem_answer(item_pdf):
    with fitz.open(item_pdf) as file:
        ic = ItemCropper()
        solutions_info = ic.get_solution_infos_from_file(file, 10)
        answer = ic.get_answer_from_file(file)
        return answer

def build():
    new_doc = fitz.open()

    #setup
    problem_dict = get_problem_dict("input\weekly2")
    problem_list = get_problem_list("input\weekly2\item_list.txt")

    resources_pdf = "resources/weekly_ans_resources.pdf"
    resources_doc = fitz.open(resources_pdf)

    overlayer = Overlayer(new_doc)
    base = Component(resources_pdf, 1, resources_doc.load_page(1).rect)
    paragraph = ParagraphOverlayObject()
    paragraph_cnt = 0
    unit_num = 0
    problem_num = 0
    before_unit = '---'
    unit_problem_answers = []
    problem_list.append('-----')
    for problem in problem_list:
        problem_num += 1
        if before_unit != problem[2:5] and before_unit != '---':
            unit_num += 1
            unit = bake_unit(resources_pdf, resources_doc, before_unit, unit_num, problem_num-len(unit_problem_answers), unit_problem_answers)
            unit_problem_answers = []
            paragraph_cnt = add_child_to_paragraph(paragraph, unit, paragraph_cnt, overlayer, base)
            paragraph.add_child(AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(15)))
        before_unit = problem[2:5]
        if before_unit == '---':
            break
        unit_problem_answers.append(get_problem_answer(problem_dict[problem]))

    paragraph.overlay(overlayer, Coord(0,0,0))
    new_doc.save("output/weekly_ans_test.pdf")
    resources_doc.close()
    pass