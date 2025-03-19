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
import json
from modules.squeeze_ans import AnswerBuilder

class AnswerBuilderSqueezeMini(AnswerBuilder):
    def build(self):
        new_doc = fitz.open()
        
        self.resources_pdf = RESOURCES_PATH + "/squeeze_ans_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

        self.overlayer = Overlayer(new_doc)

        base = self.get_component_on_resources(1)
        paragraph = ParagraphOverlayObject()

        paragraph_cnt = 0
        unit_problem_answers = []
        unit_problem_numbers = []
        unit_num = 0

        mainitems_whole = []
        for topic_set in self.mainitems:
            mainitems_whole.extend(topic_set[1])

        def custom_sort_key(item):
            mainsub = item["mainsub"]
            try:
                return (0, int(mainsub))
            except ValueError:
                return (1, mainsub)

        mainitems_whole.sort(key=custom_sort_key)

        for item in mainitems_whole:
            if not item["item_num"]:
                item["item_num"] = item["mainsub"]
        mainitems_whole = [('Mini', mainitems_whole)]

        for topic_set in mainitems_whole:
            for item in topic_set[1]:
                item_code = item["item_code"]
                item_pdf = code2pdf(item_code)
                if item_code[5:7] == 'KC':
                    number = item["item_num"]
                else:
                    number = item["mainsub"]
                unit_problem_numbers.append(number)
                unit_problem_answers.append(self.get_problem_answer(item_pdf))
            unit_num += 1

            unit = self.bake_unit(topic_set[0], unit_num, unit_problem_numbers, unit_problem_answers)
            unit_problem_answers = []
            unit_problem_numbers = []
            paragraph_cnt = self.add_child_to_paragraph(paragraph, unit, paragraph_cnt, self.overlayer, base)
            paragraph.add_child(AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(15)))


        paragraph.overlay(self.overlayer, Coord(0,0,0))
        #new_doc.save("output/squeeze_ans_test.pdf")
        self.resources_doc.close()
        return new_doc
        pass