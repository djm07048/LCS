import json
import fitz
from modules.squeeze_toc import TocBuilder
from modules.squeeze_flow import FlowBuilder
from modules.squeeze_pro import ProblemBuilder
from modules.squeeze_main import MainsolBuilder
from modules.squeeze_ans import AnswerBuilder
from modules.squeeze_sol import SolutionBuilder
from modules.overlayer import Overlayer
from utils.overlay_object import *
from utils.component import Component
from utils.ratio import Ratio
from utils.path import *
from utils.pdf_utils import PdfUtils

class SQBuilder:
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

            if item['mainsub']:
                if topic in self.mainitems:
                    self.mainitems[topic].append(item)
                else:
                    self.mainitems[topic] = []
                    self.mainitems[topic].append(item)

            if item['item_num']:
                if topic in self.proitems:
                    self.proitems[topic].append(item)
                else:
                    self.proitems[topic] = []
                    self.proitems[topic].append(item)
        print(f"Total {len(self.items)} topics found.")
        print(f"pro: {self.proitems}")
        print(f"main: {self.mainitems}")

    def bake_topic_list(self, page_num, topic_num):
        resources_pdf = RESOURCES_PATH + "/squeeze_main_resources.pdf"
        resources_doc = fitz.open(resources_pdf)
        topic_list = AreaOverlayObject(page_num, Coord(0,0,0), Ratio.mm_to_px(8))
        for i in range(len(self.topics)):
            if topic_num == i:
                box = Component(resources_pdf, 8, resources_doc.load_page(8).rect)
            else:
                box = Component(resources_pdf, 7, resources_doc.load_page(7).rect)
            box_object = ComponentOverlayObject(page_num, Coord(Ratio.mm_to_px(i*8 - 8), 0, 0), box)
            topic_list.add_child(box_object)
        return topic_list

    def add_page_num(self, overlayer, start_page_num, end_page_num):
        for num in range(start_page_num, end_page_num): #4P부터 시작
            if num % 2:
                page_num_object = TextOverlayObject(num-1, Coord(Ratio.mm_to_px(244), Ratio.mm_to_px(358.5), -1), "Pretendard-Bold.ttf", 14, f"{num}", (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)
            else:
                page_num_object = TextOverlayObject(num-1, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(358.5), -1), "Pretendard-Bold.ttf", 14, f"{num}", (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
            page_num_object.overlay(overlayer, page_num_object.coord)

    def build(self, output, log_callback=None):
        if log_callback:
            log_callback("squeeze Paper Build Start")
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
            pro_topic_set = next((pro_set for pro_set in self.proitems.items() if pro_set[0] == topic_set[0]), None)
            main_topic_set = next((main_set for main_set in self.mainitems.items() if main_set[0] == topic_set[0]),
                                  None)

            if log_callback:
                log_callback(f"Building topic {topic_set[0]}")

            topic_pages[1]["Flow"] = int(total.page_count + 1)

            if log_callback:
                log_callback("  (1) Building Flow...")
            result = fitz.open()
            fb = FlowBuilder(topic_set[0], topic_set[1], index)
            new_doc = fb.build()
            fc_pages.append((total.page_count, (fb.overlayer.doc.page_count + 1) // 2))
            result.insert_pdf(new_doc)
            if log_callback:
                log_callback("Done!")


            # Initialize flag
            flag = 0

            # Only build main solution if main_topic_set exists (is not None)
            if main_topic_set is not None:
                topic_pages[1]["Main"] = int(total.page_count + result.page_count + 2)
                if log_callback:
                    log_callback("  (2) Building Main Solution...")
                mb = MainsolBuilder(main_topic_set[0], main_topic_set[1])
                new_doc = mb.build()
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
                        log_callback("Main solution build returned None!")
            else:
                topic_pages[1]["Main"] = -1         # 존재하지 않음을 표현
                if log_callback:
                    log_callback("  (2) No main items found for this topic, skipping main solution...")

            topic_pages[1]["Problem"] = int(total.page_count + result.page_count + 1)

            if log_callback:
                log_callback("  (3) Building Problems...")
            pb = ProblemBuilder(pro_topic_set[0], pro_topic_set[1], flag)
            new_doc = pb.build()
            if log_callback:
                log_callback("Done!")
            result.insert_pdf(new_doc)

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
        ab = AnswerBuilder(self.proitems.items(), self.mainitems.items())
        new_doc = ab.build()
        total.insert_pdf(new_doc)

        sol_page = int(total.page_count + 1)

        sb = SolutionBuilder(self.proitems.items())
        new_doc = sb.build()
        total.insert_pdf(new_doc)

        if log_callback:
            log_callback("Done!")

        end_page_num = int(total.page_count + 1)
        # Add Memo pages due to the number of pages
        if not total.page_count % 4 == 2:  # 4k+1 형태가 아닐 때
            for i in range((2 - total.page_count % 4) % 4):  # 필요한 페이지 수만큼
                src_pdf = RESOURCES_PATH + "/squeeze_pro_resources.pdf"
                src_doc = fitz.open(src_pdf)
                total.insert_pdf(src_doc, from_page=4, to_page=4)

        tb = TocBuilder()
        ban_doc = tb.build_ban()
        total.insert_pdf(ban_doc)
        total.insert_pdf(fitz.open(RESOURCES_PATH + "/squeeze_toc_resources.pdf"), from_page=6, to_page=6)

        # Overlay TOC to the total document
        bake_toc = TocBuilder()
        bake_toc.bake_topic_toc(total, toc_pages, ans_page, sol_page)

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

        start_page_num = 2 * (len(self.topics) // 7) + 6

        self.add_page_num(overlayer, start_page_num, end_page_num)

        '''ob = OffsetBuilder(book_doc=total)
        new_doc = ob.build()
    '''

        if log_callback:
            log_callback("Done!")

        PdfUtils.save_to_pdf(total, output, garbage=4)
        if log_callback:
            log_callback(f"Build Complete! ({output})")
        pass