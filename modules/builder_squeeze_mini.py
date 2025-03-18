import json
import fitz
from modules.squeeze_mini_toc import TocBuilder
from modules.squeeze_mini_main import MainsolBuilder
from modules.squeeze_mini_ans import AnswerBuilderSqueezeMini
from modules.overlayer import Overlayer
from utils.overlay_object import *
from utils.component import Component
from utils.ratio import Ratio
from utils.path import *
from utils.pdf_utils import PdfUtils


# topic이 유일하다고 가정하여 진행한다!

class SQMiniBuilder:
    def __init__(self, items):
        self.topics = []
        self.items = dict()
        self.proitems = dict()
        self.mainitems = dict()
        for item in items:
            topic = item['topic_in_book']
            if topic in self.items:
                self.items[topic].append(item)
            else:
                self.topics.append(topic)
                self.items[topic] = []
                self.items[topic].append(item)
            if item['item_num']:
                if topic in self.proitems:
                    self.proitems[topic].append(item)
                else:
                    self.proitems[topic] = []
                    self.proitems[topic].append(item)
            if item['mainsub']:
                if topic in self.mainitems:
                    self.mainitems[topic].append(item)
                else:
                    self.mainitems[topic] = []
                    self.mainitems[topic].append(item)

    def add_page_num(self, overlayer):
        for num in range(4, overlayer.doc.page_count):  # 4P부터 시작
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
            log_callback("squeeze mini Paper Build Start")
        total = fitz.open()

        tb = TocBuilder()
        tb.topic_num = len(self.topics)
        new_doc = tb.build_empty()  # empty page 격의 toc를 overlay
        total.insert_pdf(new_doc)

        fc_pages = []
        toc_pages = []
        index = 1

        for topic_set in self.items.items():
            topic_pages = (topic_set[0], {"Flow": 0, "Main": 0, "Problem": 0, "End": 0})
            # topic_set은 (topic, items:list of self.items which matches the topic)의 형태

            # Find the corresponding pro_topic_set
            main_topic_set = next((main_set for main_set in self.mainitems.items() if main_set[0] == topic_set[0]),
                                  None)

            if log_callback:
                log_callback(f"Building topic {topic_set[0]}")

            result = fitz.open()

            topic_pages[1]["Main"] = int(total.page_count)

            if log_callback:
                log_callback("  (2) Building Main Solution...")
            mb = MainsolBuilder(main_topic_set[0], main_topic_set[1])
            new_doc = mb.build()
            flag = 0
            if new_doc is not None:
                flag = 1
                overlayer = Overlayer(result)
                overlayer.add_page(
                    Component(RESOURCES_PATH + "/squeeze_pro_resources.pdf", 4, result.load_page(0).rect))
                result.insert_pdf(new_doc)
                if log_callback:
                    log_callback("Done!")
            else:
                if log_callback:
                    log_callback("Skipped!")

            topic_pages[1]["Problem"] = int(total.page_count + result.page_count + 1)

            # Overlay current topic's TOC to the total document
            # get current topic's pages

            if log_callback:
                log_callback("  (4) Overlaying Table of Contents...")

            if log_callback:
                log_callback(f"Building topic {topic_set[0]} Complete! [{index}/{len(self.items)}]")
            total.insert_pdf(result)

            topic_pages[1]["End"] = int(total.page_count)

            toc_pages.append(topic_pages)
            index += 1

        ans_page = int(total.page_count + 1)

        if log_callback:
            log_callback("Building Solutions...")
        ab = AnswerBuilderSqueezeMini(self.proitems.items(), self.mainitems.items())
        new_doc = ab.build()
        total.insert_pdf(new_doc)

        sol_page = int(total.page_count + 1)

        if log_callback:
            log_callback("Done!")

        # Add Memo pages due to the number of pages
        if not total.page_count % 4 == 3:  # 4k+3 형태가 아닐 때
            for i in range((3 - total.page_count % 4) % 4):  # 필요한 페이지 수만큼
                src_pdf = RESOURCES_PATH + "/squeeze_pro_resources.pdf"
                src_doc = fitz.open(src_pdf)
                total.insert_pdf(src_doc, from_page=4, to_page=4)

        total.insert_pdf(fitz.open(RESOURCES_PATH + "/squeeze_toc_resources.pdf"), from_page=6, to_page=6)

        # Overlay TOC to the total document
        bake_toc = TocBuilder()
        bake_toc.bake_topic_toc(total, toc_pages, ans_page, sol_page)

        if log_callback:
            log_callback("Post-processing...")
        overlayer = Overlayer(total)
        '''for i in range(len(fc_pages)):
            if i < len(fc_pages):
                topic_list = self.bake_topic_list(fc_pages[i][0] + 1, i)
                topic_list.overlay(overlayer, Coord(Ratio.mm_to_px(159), Ratio.mm_to_px(16.5), 0))
                if fc_pages[i][1] == 2:
                    topic_list = self.bake_topic_list(fc_pages[i][0] + 3, i)
                    topic_list.overlay(overlayer, Coord(Ratio.mm_to_px(159), Ratio.mm_to_px(16.5), 0))'''

        self.add_page_num(overlayer)

        '''ob = OffsetBuilder(book_doc=total)
        new_doc = ob.build()
'''

        if log_callback:
            log_callback("Done!")

        PdfUtils.save_to_pdf(total, output, garbage=4)
        if log_callback:
            log_callback(f"Build Complete! ({output})")
        pass
