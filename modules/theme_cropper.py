import fitz
from fitz import Page, Rect
import numpy as np
import os

from utils.direction import Direction
from utils.pdf_utils import PdfUtils
from utils.ratio import Ratio
from utils.problem_info import ProblemInfo
from utils.solution_info import ThemeInfo


class ThemeCropper:
    def __init__(self):
        pass

    def rgb_normalize(self, na: np.ndarray) -> np.ndarray:
        na = 255 - (((270 - na) // 30) * 30)
        na = np.where(na > 255, 0, na)
        return na

    def rgb_to_hex(self, r, g, b):
        return f"{r:02X}{g:02X}{b:02X}"

    def get_theme_component_area(self):
        rect = Rect(53, 0, 153, 420)
        return Ratio.rect_mm_to_px(rect)

    def get_theme_bar_area(self):
        rect = Rect(19, 0, 21, 420)
        return Ratio.rect_mm_to_px(rect)

    def get_theme_infos_from_file(self, file: fitz.Document, accuracy=1) -> list[ThemeInfo]:
        page = file.load_page(0)
        rect = self.get_theme_bar_area()
        na = PdfUtils.pdf_clip_to_array(page, rect, fitz.Matrix(1, accuracy))
        na = self.rgb_normalize(na)

        themes = dict()
        for y in range(na.shape[0]):
            for x in range(na.shape[1]):
                if np.count_nonzero(na[y][x]) < 3:
                    curr = na[y][x]
                    hexcode = self.rgb_to_hex(curr[0], curr[1], curr[2])
                    if hexcode in themes:
                        themes[hexcode].rect.y0 = min(themes[hexcode].rect.y0, y / accuracy)
                        themes[hexcode].rect.y1 = max(themes[hexcode].rect.y1, y / accuracy)
                    else:
                        themes[hexcode] = ThemeInfo(hexcode, self.get_theme_component_area())
                        themes[hexcode].rect.y0 = y / accuracy
                        themes[hexcode].rect.y1 = y / accuracy

        # srect = themes["00FF00"].rect
        # text = page.get_text("text", clip=srect)
        # print(text[2:])
        self.solutions = themes
        return list(themes.values())