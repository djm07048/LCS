import json
import fitz
from modules.weekly_flow import FlowBuilder
from modules.weekly_pro import ProblemBuilder
from modules.weekly_main import MainsolBuilder
from modules.weekly_ans import AnswerBuilder
from modules.weekly_sol import SolutionBuilder
from modules.overlayer import Overlayer
from utils.overlay_object import *
from utils.component import Component
from utils.ratio import Ratio
from utils.path import *
from utils.pdf_utils import PdfUtils

class Builder:
    def __init__(self, items):
        self.topics = []
        self.items = dict()
        for item in items:
            topic = item['topic_in_book']
            if topic in self.items:
                self.items[topic].append(item)
            else:
                self.topics.append(topic)
                self.items[topic] = []
                self.items[topic].append(item)

    def bake_topic_list(self, page_num, topic_num):
        resources_pdf = RESOURCES_PATH + "/weekly_main_resources.pdf"
        resources_doc = fitz.open(resources_pdf)
        topic_list = AreaOverlayObject(page_num, Coord(0,0,0), Ratio.mm_to_px(8))
        for i in range(len(self.topics)):
            if topic_num == i:
                box = Component(resources_pdf, 8, resources_doc.load_page(8).rect)
            else:
                box = Component(resources_pdf, 7, resources_doc.load_page(7).rect)
            box_object = ComponentOverlayObject(page_num, Coord(Ratio.mm_to_px(i*8), 0, 0), box)
            topic_list.add_child(box_object)
        return topic_list
    
    def add_page_num(self, overlayer):
        for num in range(4, overlayer.doc.page_count+4):
            if num % 2:
                page_num_object = TextOverlayObject(num-4, Coord(Ratio.mm_to_px(244), Ratio.mm_to_px(358.5), 4), "Pretendard-Bold.ttf", 14, f"{num}", (0, 0, 0), fitz.TEXT_ALIGN_RIGHT)
            else:
                page_num_object = TextOverlayObject(num-4, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(358.5), 4), "Pretendard-Bold.ttf", 14, f"{num}", (0, 0, 0), fitz.TEXT_ALIGN_LEFT)
            page_num_object.overlay(overlayer, page_num_object.coord)

    def build(self, output, log_callback=None):
        if log_callback:
            log_callback("Weekly Paper Build Start")
        total = fitz.open()
        fc_pages = []
        index = 1
        for topic_set in self.items.items():
            if log_callback:
                log_callback(f"Building topic {topic_set[0]}")

            if log_callback:
                log_callback("  (1) Building Flow...")
            result = fitz.open()
            fb = FlowBuilder(topic_set[0], topic_set[1], index)
            new_doc = fb.build()
            fc_pages.append((total.page_count, (fb.overlayer.doc.page_count + 1) // 2))
            result.insert_pdf(new_doc)
            if log_callback:
                log_callback("Done!")

            if log_callback:
                log_callback("  (2) Building Main Solution...")
            mb = MainsolBuilder(topic_set[0], topic_set[1])
            new_doc = mb.build()
            flag = 0
            if new_doc is not None:
                flag = 1
                overlayer = Overlayer(result)
                overlayer.add_page(Component(RESOURCES_PATH + "/weekly_pro_resources.pdf", 4, result.load_page(0).rect))

                result.insert_pdf(new_doc)
                if log_callback:
                    log_callback("Done!")
            else:
                if log_callback:
                    log_callback("Skipped!")

            if log_callback:
                log_callback("  (3) Building Problems...")
            pb = ProblemBuilder(topic_set[0], topic_set[1], flag)
            new_doc = pb.build()
            if log_callback:
                log_callback("Done!")
            result.insert_pdf(new_doc)

            if log_callback:
                log_callback(f"Building topic {topic_set[0]} Complete! [{index}/{len(self.items)}]")
            total.insert_pdf(result)
            index += 1

        if log_callback:
            log_callback("Building Solutions...")
        ab = AnswerBuilder(self.items.items())
        new_doc = ab.build()
        total.insert_pdf(new_doc)

        sb = SolutionBuilder(self.items.items())
        new_doc = sb.build()
        total.insert_pdf(new_doc)
        if log_callback:
            log_callback("Done!")

        if log_callback:
            log_callback("Post-processing...")
        overlayer = Overlayer(total)
        for i in range(len(fc_pages)):
            if i < len(fc_pages):
                topic_list = self.bake_topic_list(fc_pages[i][0] + 1, i)
                topic_list.overlay(overlayer, Coord(Ratio.mm_to_px(159), Ratio.mm_to_px(16.5), 0))
                if fc_pages[i][1] == 2:
                    topic_list = self.bake_topic_list(fc_pages[i][0] + 3, i)
                    topic_list.overlay(overlayer, Coord(Ratio.mm_to_px(159), Ratio.mm_to_px(16.5), 0))
        self.add_page_num(overlayer)
        if log_callback:
            log_callback("Done!")

        PdfUtils.save_to_pdf(total, output, garbage=4)
        if log_callback:
            log_callback(f"Build Complete! ({output})")
        pass