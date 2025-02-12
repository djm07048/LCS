from fitz import Rect
import fitz
from utils.component import Component, ComponentType
from utils.coord import Coord
import copy
from utils.path import *
class OverlayObject():
    def __init__(self, page_num: int, coord: Coord):
        self.page_num = page_num
        self.coord = coord
        self.child = []
    
    def add_child(self, obj: 'OverlayObject'):
        new_obj = copy.deepcopy(obj)
        new_obj.update_page_num(self.page_num)
        self.child.append(copy.deepcopy(new_obj))

    def update_page_num(self, page_num: int):
        self.page_num = page_num
        for oo in self.child:
            oo.update_page_num(page_num)

    def overlay(self, overlayer, absolute_coord):
        for oo in self.child:
            oo.overlay(overlayer, absolute_coord + oo.coord)
        pass

    def get_height(self):
        pass

class ListOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, height, align):
        super().__init__(page_num, coord)
        self.ls = []
        self.height = height
        self.align = align
        self.left_height = height

    def overlay(self, overlayer, absolute_coord):
        #TODO
        if self.align == 0:
            curr_height = 0
            for oo in self.child:
                oo.overlay(overlayer, absolute_coord + Coord(0, curr_height, 0))
                curr_height += oo.get_height()
        elif self.align == 1:
            curr_height = 0
            for oo in self.child:
                oo.overlay(overlayer, absolute_coord + Coord(0, curr_height, 0))
                curr_height += oo.get_height() + self.left_height / max(len(self.child)-1, 1)
        elif self.align == 2:
            curr_height = 0
            for oo in self.child:
                oo.overlay(overlayer, absolute_coord + Coord(0, curr_height, 0))
                curr_height += oo.get_height() + self.left_height / len(self.child)
        pass
    def add_child(self, obj: OverlayObject):
        if obj.get_height() > self.left_height:
            return False
        else:
            super().add_child(obj)
            self.left_height -= obj.get_height()
        return True
    
    def set_height(self, height):
        self.height = height
        self.left_height = height
        for oo in self.child:
            self.left_height -= oo.get_height()

    def get_height(self):
        return self.height - self.left_height
    pass

class ParagraphOverlayObject(OverlayObject):
    def __init__(self):
        self.child = []
    
    def add_paragraph_list(self, paragraph_list: ListOverlayObject):
        self.child.append(copy.deepcopy(paragraph_list))

    def add_child(self, obj: 'OverlayObject'):
        if self.child and self.child[-1].add_child(obj):
            return True
            pass
        else:
            #should append new list
            return False
        
    def overlay(self, overlayer, absolute_coord):
        for oo in self.child:
            oo.overlay(overlayer, absolute_coord + oo.coord)

    def get_coord(self):
        return self.coord


class AreaOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, height):
        self.height = height
        super().__init__(page_num, coord)

    def get_height(self):
        return self.height

class ComponentOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, component):
        self.component = component
        super().__init__(page_num, coord)

    def overlay(self, overlayer, absolute_coord):
        overlayer.pdf_overlay(self.page_num, absolute_coord, self.component)
        super().overlay(overlayer, absolute_coord)
    pass

    def get_height(self):
        return self.component.src_rect.height
    
class ResizedComponentOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, component, ratio):
        self.ratio = ratio
        self.component = component
        self.end= [{'L': [0, 0], 'R': [0, 0], 'T': [0, 0], 'B': [0, 0]}]
        super().__init__(page_num, coord)

    def overlay(self, overlayer, absolute_coord):
        overlayer.pdf_overlay_with_resize(self.page_num, absolute_coord, self.component, self.ratio)
        super().overlay(overlayer, absolute_coord)
    pass

    def get_height(self):
        return self.component.src_rect.height*self.ratio

    def get_end_coords(self):


        return self.end
    
class ShapeOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, rect, color, radius = None):
        self.rect = rect
        self.color = color
        self.radius = radius
        super().__init__(page_num, coord)

    def overlay(self, overlayer, absolute_coord):
        overlayer.shape_overlay(self.page_num, absolute_coord, self.rect, self.color, self.radius)
        super().overlay(overlayer, absolute_coord)
    pass

    def get_height(self):
        return self.rect.height

class LineOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, start, end, color, width):
        self.start = start
        self.end = end
        self.color = color
        self.width = width
        super().__init__(page_num, coord)

    def overlay(self, overlayer, absolute_coord):
        overlayer.line_overlay(self.page_num, absolute_coord, self.start, self.end, self.color, self.width)
        super().overlay(overlayer, absolute_coord)
    pass

    def get_height(self):
        return None

class TextOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, font, size, text, color, text_align):
        self.font = font
        self.size = size
        self.text = text
        self.color = color
        self.text_align = text_align
        super().__init__(page_num, coord)

    def overlay(self, overlayer, absolute_coord):
        overlayer.text_overlay(self.page_num, absolute_coord, self.font, self.size, self.text, self.color, self.text_align)
        super().overlay(overlayer, absolute_coord)

    def get_height(self):
        #Error: text in paragraph should be wrapped by area
        return None

    def get_width(self):
        font = fitz.Font(fontfile=RESOURCES_PATH+"/fonts/"+self.font)
        return font.text_length(self.text, self.size)