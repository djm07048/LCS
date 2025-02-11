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

class FlowBuilder:
    def __init__(self, topic, items, index):
        self.topic = topic
        self.items = items
        self.index = index

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def overlay_flowline(self):
        src_pdf = RESOURCES_PATH + f"/fc_flowline/{self.topic}.pdf"
        src_doc = fitz.open(src_pdf)
        num_pages = src_doc.page_count

        for page_num in range(num_pages):
            if page_num >= self.overlayer.doc.page_count:
                print(f"Error: Page {page_num} not in document")
                continue
            component = Component(src_pdf, page_num, src_doc.load_page(page_num).rect)
            co = ComponentOverlayObject(page_num, Coord(0, 0, 10), component)
            co.overlay(self.overlayer, Coord(0, 0, 10))

        src_doc.close()

    def get_unit_title(self):
        with open(RESOURCES_PATH+"/topic.json", encoding='UTF8') as file:
            topic_data = json.load(file)
        return topic_data[self.topic]

    def get_flow_right_page(self):
        src_pdf = RESOURCES_PATH+ f"/fc_additional/{self.topic}.pdf"
        src_doc = fitz.open(src_pdf)
        return Component(src_pdf, 0, src_doc.load_page(0).rect)

    def set_page(self):
        if self.page_amount == 1:
            self.overlayer.add_page(self.get_component_on_resources(2))
            self.overlayer.add_page(self.get_flow_right_page())
            #self.overlayer.add_page(self.get_component_on_resources(4))
        elif self.page_amount == 2:
            self.overlayer.add_page(self.get_component_on_resources(2))
            self.overlayer.add_page(self.get_component_on_resources(3))
        elif self.page_amount == 3:
            self.overlayer.add_page(self.get_component_on_resources(2))
            self.overlayer.add_page(self.get_component_on_resources(3))
            self.overlayer.add_page(self.get_component_on_resources(2))
            self.overlayer.add_page(self.get_flow_right_page())
            #self.overlayer.add_page(self.get_component_on_resources(4))
        elif self.page_amount == 4:
            self.overlayer.add_page(self.get_component_on_resources(2))
            self.overlayer.add_page(self.get_component_on_resources(3))
            self.overlayer.add_page(self.get_component_on_resources(2))
            self.overlayer.add_page(self.get_component_on_resources(3))

    def set_lists(self, page_num, k):
        paragraphs_base = ShapeOverlayObject(page_num, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(35), 0), Rect(0,0,Ratio.mm_to_px(262),Ratio.mm_to_px(k+22)), (0,0,0,0.05))
        paragraphs_base.add_child(ListOverlayObject(page_num, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(11), 1), Ratio.mm_to_px(k), 1))      #첫번째 단
        paragraphs_base.add_child(ListOverlayObject(page_num, Coord(Ratio.mm_to_px(97.25), Ratio.mm_to_px(11), 1), Ratio.mm_to_px(k), 1))   #두번째 단
        paragraphs_base.add_child(ListOverlayObject(page_num, Coord(Ratio.mm_to_px(174.5), Ratio.mm_to_px(11), 1), Ratio.mm_to_px(k), 1))   #세번째 단
        return paragraphs_base
    
    def get_lists_on_page(self):
        lists = []
        if self.page_amount == 1:
            lists.append(self.set_lists(0, 334))
        elif self.page_amount == 2:
            lists.append(self.set_lists(0, 220))
            lists.append(self.set_lists(1, 220))
        elif self.page_amount == 3:
            lists.append(self.set_lists(0, 220))
            lists.append(self.set_lists(1, 220))
            lists.append(self.set_lists(2, 334))
        elif self.page_amount == 4:
            lists.append(self.set_lists(0, 220))
            lists.append(self.set_lists(1, 220))
            lists.append(self.set_lists(2, 220))
            lists.append(self.set_lists(3, 220))
        return lists
    
    def get_item_list_on_paragraph(self):
        item_list = [[] for i in range(13)]
        for item in self.items:
            if item['FC_para'] is None: continue
            para_num = int(item['FC_para'])
            if para_num > 1:
                item_list[para_num//10].append((para_num%10,item['item_code']))
        
        self.item_lists = []
        for para in item_list:
            if len(para) != 0:
                self.item_lists.append(sorted(para))
    
    def build(self):
        new_doc = fitz.open()

        self.resources_pdf = RESOURCES_PATH+"/weekly_main_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)
        self.overlayer = Overlayer(new_doc)

        self.get_item_list_on_paragraph()
        self.page_amount = (len(self.item_lists)-1)//3+1
        self.set_page()

        para_lists = self.get_lists_on_page()
        for i in range(len(self.item_lists)):
            for item in self.item_lists[i]:
                item_code = item[1]
                item_pdf = get_item_path(item_code) + f"/{item_code[2:5]}/{item_code}/{item_code}_caption.pdf"
                with fitz.open(item_pdf) as file:
                    page = file.load_page(0)
                    rect = page.rect
                    component = Component(item_pdf, 0, page.rect)
                oo = ResizedComponentOverlayObject(i//3, Coord(Ratio.mm_to_px(0.175),Ratio.mm_to_px(0.175),0), component, 0.6)

                problem = ShapeOverlayObject(i//3, Coord(Ratio.mm_to_px(0.175),Ratio.mm_to_px(0.175),1), Rect(0,0,rect.width*0.6,rect.height*0.6), (0, 0, 0, 0))

                problem.add_child(oo)

                para_lists[i//3].child[i%3].add_child(problem)


        for para in para_lists:
            height = 0
            for oo in para.child:
                height = max(height, oo.get_height() + (len(oo.child)-1)*Ratio.mm_to_px(10))        #10이 para에서 최소 간격
            for oo in para.child:
                oo.set_height(height)
            para.rect.y1 = height + Ratio.mm_to_px(22)

        if len(para_lists) > 1:
            height = max(para_lists[0].child[0].height, para_lists[1].child[0].height)
            for oo in para_lists[0].child:
                oo.set_height(height)
            for oo in para_lists[1].child:
                oo.set_height(height)
            para_lists[0].rect.y1 = height + Ratio.mm_to_px(22)
            para_lists[1].rect.y1 = height + Ratio.mm_to_px(22)

        if len(para_lists) == 4:
            height = max(para_lists[2].child[0].height, para_lists[3].child[0].height)
            for oo in para_lists[2].child:
                oo.set_height(height)
            for oo in para_lists[3].child:
                oo.set_height(height)
            para_lists[2].rect.y1 = height + Ratio.mm_to_px(22)
            para_lists[3].rect.y1 = height + Ratio.mm_to_px(22)

        for para in para_lists:
            para.overlay(self.overlayer, Coord(0,Ratio.mm_to_px(35),0))
            y = para.coord.y + para.rect.height

            #최하단 띠지 삽입
            so = ShapeOverlayObject(para.page_num, Coord(0, y, 0), Rect(0,0,Ratio.mm_to_px(262),Ratio.mm_to_px(2)), (205/255, 216/255, 238/255))
            so.overlay(self.overlayer, Coord(0, y, 0))

        if len(para_lists) % 2 == 0:
            piv = len(para_lists)
            y = para_lists[piv-2].coord.y + para_lists[piv-2].rect.height
            so = ShapeOverlayObject(piv-2, Coord(Ratio.mm_to_px(20), y + Ratio.mm_to_px(16.25), 0), Rect(0,0,Ratio.mm_to_px(222),Ratio.mm_to_px(330.75)-y), (243/255, 246/255, 251/255))
            so.overlay(self.overlayer, Coord(Ratio.mm_to_px(20), y + Ratio.mm_to_px(16.25), 0))
            so = ShapeOverlayObject(piv-1, Coord(Ratio.mm_to_px(20), y + Ratio.mm_to_px(16.25), 0), Rect(0,0,Ratio.mm_to_px(222),Ratio.mm_to_px(330.75)-y), (243/255, 246/255, 251/255))
            so.overlay(self.overlayer, Coord(Ratio.mm_to_px(20), y + Ratio.mm_to_px(16.25), 0))
            
            so = ShapeOverlayObject(piv-2, Coord(Ratio.mm_to_px(20), y + Ratio.mm_to_px(16.25), 0), Rect(0,0,Ratio.mm_to_px(222), Ratio.mm_to_px(0.5/2.835)), (0.75, 0.45, 0, 0))
            so.overlay(self.overlayer, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(347), 0))
            so = ShapeOverlayObject(piv-1, Coord(Ratio.mm_to_px(20), y + Ratio.mm_to_px(16.25), 0), Rect(0,0,Ratio.mm_to_px(222), Ratio.mm_to_px(0.5/2.835)), (0.75, 0.45, 0, 0))
            so.overlay(self.overlayer, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(347), 0))


            #기출 Point, 빈출 선지를 FC 하단에 삽입합니다.
            component = self.get_component_on_resources(5)
            co = ComponentOverlayObject(piv-2, Coord(Ratio.mm_to_px(20),y+Ratio.mm_to_px(12),0), component)
            co.overlay(self.overlayer, Coord(Ratio.mm_to_px(20),y+Ratio.mm_to_px(12),0))
            component = self.get_component_on_resources(6)
            co = ComponentOverlayObject(piv-1, Coord(Ratio.mm_to_px(20),y+Ratio.mm_to_px(12),0), component)
            co.overlay(self.overlayer, Coord(Ratio.mm_to_px(20),y+Ratio.mm_to_px(12),0))

        for i in range(len(para_lists))[::2]:
            to = TextOverlayObject(i, Coord(Ratio.mm_to_px(36), Ratio.mm_to_px(19), 0), "Pretendard-Bold.ttf", 32.5, self.get_unit_title(), (0, 0, 0), fitz.TEXT_ALIGN_LEFT)
            to.overlay(self.overlayer, Coord(Ratio.mm_to_px(36), Ratio.mm_to_px(19), 0))
            ti = TextOverlayObject(i, Coord(Ratio.mm_to_px(23.1), Ratio.mm_to_px(19), 0), "Montserrat-Bold.ttf", 32.5, str(self.index), (1, 1, 1), fitz.TEXT_ALIGN_CENTER)
            ti.overlay(self.overlayer, Coord(Ratio.mm_to_px(23.1), Ratio.mm_to_px(19), 0))

        self.overlay_flowline()

        self.resources_doc.close()
        return new_doc