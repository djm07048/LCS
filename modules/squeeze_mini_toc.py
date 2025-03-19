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
from modules.squeeze_toc import TocBuilder
import json

class TocBuilderSqueezeMini(TocBuilder):
    def bake_topic_toc(self, total_doc, toc_pages, ans_page, sol_page):
        self.topic_num = len(toc_pages)
        topic_loc_list = self.get_topic_location()
        for i in range(self.topic_num):
            topic_loc = topic_loc_list[i]

            flow_page = toc_pages[i][1]["Flow"]
            main_page = toc_pages[i][1]["Main"]
            pro_page = toc_pages[i][1]["Problem"]

            topic_area = AreaOverlayObject(topic_loc[0], Coord(0, 0, 1), 0)
            component = Component(self.resources_pdf, 7, self.resources_doc.load_page(7).rect)
            to_object = ComponentOverlayObject(0, Coord(0, 0, 1), component)
            topic_area.height += to_object.get_height()
            unit_title = self.get_unit_title(toc_pages[i][0])

            # Component를 새로 하나 만들고, 거기에 to_title, to_flow, to_main, to_pro를 overlay
            to_num = TextOverlayObject(0, Coord(Ratio.mm_to_px(34.5), Ratio.mm_to_px(57), 1), "Montserrat-Bold.ttf",
                                       120, f"*", (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
            to_title = TextOverlayObject(0, Coord(Ratio.mm_to_px(80), Ratio.mm_to_px(37), 1), "Pretendard-Bold.ttf",
                                         23.5, f"{unit_title}", (1, 0, 0, 0),
                                         fitz.TEXT_ALIGN_LEFT)
            to_title_page = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(37-1), 1), "Pretendard-Bold.ttf", 16,
                                        f"{5}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)

            topic_area.add_child(to_object)
            topic_area.add_child(to_num)
            topic_area.add_child(to_title)
            topic_area.add_child(to_title_page)

            topic_area.overlay(overlayer=Overlayer(total_doc), absolute_coord=topic_loc[1])

        topic_area = AreaOverlayObject(2, Coord(0, 0, 1), 371)
        to_ans = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(313), 1), "Pretendard-Bold.ttf", 16,
                                   f"{ans_page}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)
        to_sol = TextOverlayObject(0, Coord(Ratio.mm_to_px(217), Ratio.mm_to_px(340), 1), "Pretendard-Bold.ttf", 16,
                                    f"{sol_page}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)
        topic_area.add_child(to_ans)
        topic_area.add_child(to_sol)
        topic_area.overlay(overlayer=Overlayer(total_doc), absolute_coord=Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0), 1))