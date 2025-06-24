from utils.problem_info import ProblemInfo

class ThemeInfo(ProblemInfo):
    def __init__(self, hexcode, rect):
        self.hexcode = hexcode
        super().__init__(0, rect)