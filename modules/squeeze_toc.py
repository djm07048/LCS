import pathlib

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

class TocBuilder:
    def __init__(self):
        self.page_amount = 0
        self.topic_num = 0
        self.resources_pdf = RESOURCES_PATH + f"/squeeze_toc_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

    def get_unit_title(self, unit_code):
        with open(RESOURCES_PATH+"/topic.json", encoding='UTF8') as file:
            topic_data = json.load(file)
        return topic_data[unit_code]

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def get_topic_location(self):
        topic_loc_list = []

        topic_loc_dict = {
            1: ["R4"],
            2: ["R3", "R4"],
            3: ["R2", "R3", "R4"],
            4: ["L3", "L4", "R3", "R4"],
            5: ["L3", "L4", "R2", "R3", "R4"],
            6: ["L2", "L3", "L4", "R2", "R3", "R4"],
            7: ["L2", "L3", "L4", "R1", "R2", "R3", "R4"]
        }

        loc_coord_dict = {
            "L1" : [1, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(53), 1)],
            "L2" : [1, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(113), 1)],
            "L3" : [1, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(173), 1)],
            "L4" : [1, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(233), 1)],
            "R1" : [2, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(53), 1)],
            "R2" : [2, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(113), 1)],
            "R3" : [2, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(173), 1)],
            "R4" : [2, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(233), 1)],
        }

        for topic in topic_loc_dict[self.topic_num]:
            topic_loc_list.append(loc_coord_dict[topic])

        return topic_loc_list


    def build_empty(self):
        new_doc = fitz.open()

        self.overlayer = Overlayer(new_doc)

        self.page_amount = 3

        self.overlayer.add_page(self.get_component_on_resources(0))

        if self.topic_num < 4:
            self.overlayer.add_page(self.get_component_on_resources(1))
            self.overlayer.add_page(self.get_component_on_resources(2))
        else:
            self.overlayer.add_page(self.get_component_on_resources(3))
            self.overlayer.add_page(self.get_component_on_resources(4))

        self.resources_doc.close()
        return new_doc

    def bake_topic_toc(self, total_doc, toc_pages, ans_page, sol_page):
        self.topic_num = len(toc_pages)
        topic_loc_list = self.get_topic_location()
        for i in range(self.topic_num):
            topic_loc = topic_loc_list[i]

            flow_page = toc_pages[i][1]["Flow"]
            main_page = toc_pages[i][1]["Main"]
            pro_page = toc_pages[i][1]["Problem"]

            topic_area = AreaOverlayObject(topic_loc[0], Coord(0, 0, 1), 0)
            component = Component(self.resources_pdf, 5, self.resources_doc.load_page(5).rect)
            to_object = ComponentOverlayObject(0, Coord(0, 0, 1), component)
            topic_area.height += to_object.get_height()
            unit_title = self.get_unit_title(toc_pages[i][0])

            # Component를 새로 하나 만들고, 거기에 to_title, to_flow, to_main, to_pro를 overlay
            to_num = TextOverlayObject(0, Coord(Ratio.mm_to_px(34.5), Ratio.mm_to_px(47), 1), "Montserrat-Bold.ttf",
                                       100, f"{int(i + 1)}", (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
            to_title = TextOverlayObject(0, Coord(Ratio.mm_to_px(80), Ratio.mm_to_px(21), 1), "Pretendard-Bold.ttf",
                                         23.5, f"{unit_title}", (1, 0, 0, 0),
                                         fitz.TEXT_ALIGN_LEFT)  # TODO cmyk 75 40 0 0으로 색상 변경
            to_flow = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(36), 1), "Pretendard-Bold.ttf", 16,
                                        f"{flow_page}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)
            to_main = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(45), 1), "Pretendard-Bold.ttf", 16,
                                        f"{main_page}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)
            to_pro = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(54), 1), "Pretendard-Bold.ttf", 16,
                                       f"{pro_page}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)

            topic_area.add_child(to_object)
            topic_area.add_child(to_num)
            topic_area.add_child(to_title)
            topic_area.add_child(to_flow)
            topic_area.add_child(to_main)
            topic_area.add_child(to_pro)

            topic_area.overlay(overlayer=Overlayer(total_doc), absolute_coord=topic_loc[1])

        topic_area = AreaOverlayObject(2, Coord(0, 0, 1), 371)
        to_ans = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(313), 1), "Pretendard-Bold.ttf", 16,
                                   f"{ans_page}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)
        to_sol = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(340), 1), "Pretendard-Bold.ttf", 16,
                                    f"{sol_page}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)
        topic_area.add_child(to_ans)
        topic_area.add_child(to_sol)
        topic_area.overlay(overlayer=Overlayer(total_doc), absolute_coord=Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0), 1))