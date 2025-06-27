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
        self.left_height = height       #남아있는 height

    def overlay(self, overlayer, absolute_coord):
        #TODO
        if self.align == 0:         #top-align
            curr_height = 0
            for oo in self.child:
                oo.overlay(overlayer, absolute_coord + Coord(0, curr_height, 0))
                curr_height += oo.get_height()
        elif self.align == 1:       #justify
            curr_height = 0
            for oo in self.child:
                oo.overlay(overlayer, absolute_coord + Coord(0, curr_height, 0))
                curr_height += oo.get_height() + self.left_height / max(len(self.child)-1, 1)
        elif self.align == 2:      #semi-justify
            curr_height = 0
            for oo in self.child:
                oo.overlay(overlayer, absolute_coord + Coord(0, curr_height, 0))
                curr_height += oo.get_height() + self.left_height / len(self.child)
        elif self.align == 3:  #bottom-align
            curr_y = self.height
            for oo in self.child:
                curr_y -= oo.get_height()
                oo.overlay(overlayer, absolute_coord + Coord(0, curr_y, 0))

        pass
    def add_child(self, obj: OverlayObject):
        if obj.get_height() > self.left_height:
            return False
        else:
            super().add_child(obj)
            self.left_height -= obj.get_height()
        return True

    def reverse_child(self):
        self.child.reverse()

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
    def __init__(self, page_num, coord, font, size, text, color, text_align, weight=None):
        self.font = font
        self.size = size
        self.text = text
        self.color = color
        self.text_align = text_align
        self.weight = weight
        super().__init__(page_num, coord)

    def overlay(self, overlayer, absolute_coord):
        overlayer.text_overlay(self.page_num, absolute_coord, self.font, self.size, self.text, self.color, self.text_align, self.weight)
        super().overlay(overlayer, absolute_coord)

    def get_height(self):
        #Error: text in paragraph should be wrapped by area
        return None

    def get_width(self):
        try:
            font_path = RESOURCES_PATH + "/fonts/" + self.font
            font = fitz.Font(fontfile=font_path)
            if self.weight is not None and hasattr(font, 'set_variation'):
                font.set_variation(wght=self.weight)
            return font.text_length(self.text, self.size)
        except Exception as e:
            print(f"Weight {self.weight}에서 폭 계산 실패: {e}")
            return self.get_width()  # 기본 방식으로 fallback


class ImageOverlayObject(OverlayObject):
    def __init__(self, page_num, coord, image_path, dpi=300, max_width=None, max_height=None):
        """
        이미지 오버레이 객체 (top-center 정렬)

        Args:
            page_num: 페이지 번호
            coord: 이미지 배치 기준 좌표 (중심선의 상단 지점)
            image_path: 이미지 파일 경로
            dpi: 이미지 해상도 (기본값: 300)
            max_width: 최대 너비 제한 (None이면 제한 없음)
            max_height: 최대 높이 제한 (None이면 제한 없음)
        """
        self.image_path = image_path
        self.dpi = dpi
        self.max_width = max_width
        self.max_height = max_height
        self._calculated_height = None
        super().__init__(page_num, coord)

    def overlay(self, overlayer, absolute_coord):
        """absolute_coord는 x값이 중심선에 주의!!!!!!!"""
        overlayer.image_overlay(
            self.page_num,
            absolute_coord,
            self.image_path,
            self.dpi,
            self.max_width,
            self.max_height
        )
        super().overlay(overlayer, absolute_coord)

    def get_height(self):
        """이미지의 실제 높이 계산"""
        if self._calculated_height is None:
            try:
                # 이미지 파일 존재 확인
                if not os.path.exists(self.image_path):
                    print(f"이미지 파일을 찾을 수 없습니다: {self.image_path}")
                    self._calculated_height = 0
                    return self._calculated_height

                # 이미지 크기 계산
                img_doc = fitz.open(self.image_path)
                img_page = img_doc.load_page(0)

                # 닫기 전에 필요한 값들을 모두 추출
                original_height = img_page.rect.height
                original_width = img_page.rect.width

                img_doc.close()  # 값 추출 후 닫기

                # DPI 적용
                scale_factor = self.dpi / 72.0
                scaled_height = original_height * scale_factor
                scaled_width = original_width * scale_factor

                # 최대 크기 제한 적용
                if self.max_height is not None:
                    if self.max_width is not None:
                        # 종횡비 유지하면서 크기 조정
                        width_ratio = self.max_width / scaled_width
                        height_ratio = self.max_height / scaled_height
                        resize_ratio = min(width_ratio, height_ratio, 1.0)
                        self._calculated_height = scaled_height * resize_ratio
                    else:
                        self._calculated_height = min(scaled_height, self.max_height)
                else:
                    self._calculated_height = scaled_height

            except Exception as e:
                print(f"이미지 높이 계산 실패: {e}")
                self._calculated_height = 0

        return self._calculated_height