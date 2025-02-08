import fitz
from fitz import Page, Rect
import numpy as np
import os

from utils.direction import Direction
from utils.pdf_utils import PdfUtils
from utils.ratio import Ratio
from utils.problem_info import ProblemInfo
from utils.solution_info import SolutionInfo

class ItemCropper:
    def __init__(self):
        pass

    def get_problem_area(self) -> Rect:
        rect = Rect(26.5, 13, 135.5, 420)
        return Ratio.rect_mm_to_px(rect)
    
    def get_problem_rect(self, page: Page, accuracy = 1) -> Rect:
        area = self.get_problem_area()
        na = PdfUtils.pdf_clip_to_array(page, area, fitz.Matrix(1, accuracy))
        na = na.mean(axis=1, dtype=np.uint32) // 255

        red_line = 0
        for y in range(na.shape[0])[::-1]:
            if np.array_equal(na[y], [1,0,0]):
                red_line = y
                break
        
        area.y1 = area.y0 + y / accuracy - Ratio.mm_to_px(1) - 1

        problem_rect = PdfUtils.trim_whitespace(page, area, Direction.DOWN, accuracy)
        problem_rect = PdfUtils.trim_whitespace(page, problem_rect, Direction.UP, accuracy)
        return problem_rect
    
    def get_problem_rect_from_file(self, file: fitz.Document, accuracy = 1) -> Rect:
        page = file.load_page(0)
        return self.get_problem_rect(page, accuracy)
    
    def rgb_normalize(self, na : np.ndarray) -> np.ndarray:
        na = 255 - (((270 - na) // 30) * 30)
        na = np.where(na > 255, 0, na)
        return na
    
    def rgb_to_hex(self, r, g, b):
        return f"{r:02X}{g:02X}{b:02X}"
    
    def get_solution_component_area(self):
        rect = Rect(174, 0, 274, 420)
        return Ratio.rect_mm_to_px(rect)
    
    def get_TF_area(self):
        rect = Rect(152, 0, 174, 420)
        return Ratio.rect_mm_to_px(rect)

    def get_solution_bar_area(self):
        rect = Rect(140, 0, 142, 420)
        return Ratio.rect_mm_to_px(rect)

    def get_solution_infos_from_file(self, file: fitz.Document, accuracy = 1) -> list[SolutionInfo]:
        page = file.load_page(0)
        rect = self.get_solution_bar_area()
        na = PdfUtils.pdf_clip_to_array(page, rect, fitz.Matrix(1, accuracy))
        na = self.rgb_normalize(na)

        solutions = dict()
        for y in range(na.shape[0]):
            for x in range(na.shape[1]):
                if np.count_nonzero(na[y][x]) < 3:
                    curr = na[y][x]
                    hexcode = self.rgb_to_hex(curr[0], curr[1], curr[2])
                    if hexcode in solutions:
                        solutions[hexcode].rect.y0 = min(solutions[hexcode].rect.y0, y / accuracy)
                        solutions[hexcode].rect.y1 = max(solutions[hexcode].rect.y1, y / accuracy)
                    else:
                        solutions[hexcode] = SolutionInfo(hexcode, self.get_solution_component_area())
                        solutions[hexcode].rect.y0 = y / accuracy
                        solutions[hexcode].rect.y1 = y / accuracy
        
        #srect = solutions["00FF00"].rect
        #text = page.get_text("text", clip=srect)
        #print(text[2:])
        self.solutions = solutions
        return list(solutions.values())
    
    def get_TF_of_solutions_from_file(self, file: fitz.Document, accuracy = 1):
        page = file.load_page(0)
        rect = self.get_TF_area()
        rectT = Rect(rect)
        rectT.x1 = (rectT.x0 + rectT.x1) / 2
        rectF = Rect(rect)
        rectF.x0 = (rectF.x0 + rectF.x1) / 2

        solutionTF = dict()
        for sid, solution in self.solutions.items():
            solution_rectT = Rect(rectT)
            solution_rectT.y0 = solution.rect.y0
            solution_rectT.y1 = solution.rect.y1
            naT = PdfUtils.pdf_clip_to_array(page, solution_rectT, fitz.Matrix(accuracy, accuracy))
            isT = (naT.mean(dtype=np.uint32) // 255) == 0

            solution_rectF = Rect(rectF)
            solution_rectF.y0 = solution.rect.y0
            solution_rectF.y1 = solution.rect.y1
            naF = PdfUtils.pdf_clip_to_array(page, solution_rectF, fitz.Matrix(accuracy, accuracy))
            isF = (naF.mean(dtype=np.uint32) // 255) == 0

            if isT^isF:
                if isT:
                    solutionTF[sid] = 1
                elif isF:
                    solutionTF[sid] = 0
            else:
                solutionTF[sid] = -1
        
        self.solutionTF = solutionTF
        return solutionTF
    
    def get_answer_from_file(self, file: fitz.Document):
        page = file.load_page(0)
        try:
            srect = self.solutions["00FF00"].rect
        except:
            print(file.name)
        text = page.get_text("text", clip=srect)
        return text[2:3]