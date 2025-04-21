import pandas as pd
import numpy as np
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QLabel, QLineEdit, QMessageBox,
                             QTabWidget, QGroupBox, QRadioButton, QFileDialog, QGridLayout)
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


def Qday_65N_solstice(eccentricity=0.0167, obliquity=0.4091, perihelion=1.7963, S0=1367):
    """
    지구의 궤도 매개변수(이심률, 기울기, 근일점)를 이용하여
    북위 65도에서 하지 때의 대기 상단 일일 평균 일사량을 계산합니다.
    """
    # 북위 65도를 라디안으로 변환
    latitude = 65.0 * np.pi / 180.0

    # 일일 평균 일사량 계산
    Q_day = S0 * (1 + eccentricity * np.sin(perihelion + np.pi)) ** 2 * np.sin(latitude) * np.sin(obliquity)

    # 음수 값이 나올 경우 0으로 설정 (물리적으로 불가능한 값 방지)
    return max(0, Q_day)


def laskar(start_time=-1000, end_time=20):
    """
    Laskar 등(2004)의 데이터를 기반으로 한 데이터 파일에서
    지구 궤도의 이심률, 기울기, 세차운동의 시계열을 읽어옵니다.
    """
    try:
        # 데이터 로드 - 여러 경로 시도
        possible_paths = [
            'milan.csv']

        orbit = None
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    orbit = pd.read_csv(path)
                    print(f"데이터 파일을 성공적으로 로드했습니다: {path}")
                    break
            except Exception as e:
                continue

        if orbit is None:
            raise FileNotFoundError("orbit.csv 파일을 찾을 수 없습니다.")

        # 데이터 추출
        data = orbit[(orbit['kiloyear'] >= start_time) & (orbit['kiloyear'] <= end_time)]

        if data.empty:
            raise ValueError(f"지정된 기간({start_time}~{end_time})에 해당하는 데이터가 없습니다.")

        # 일사량 계산
        insolation = np.array([
            Qday_65N_solstice(
                eccentricity=ecc,
                obliquity=obl,
                perihelion=per
            ) for ecc, obl, per in zip(data['eccentricity'].values,
                                       data['obliquity'].values,
                                       data['perihelion'].values)
        ])

        # 데이터프레임 반환
        return pd.DataFrame({
            'time': data['kiloyear'],
            'eccentricity': data['eccentricity'],
            'obliquity': data['obliquity'],
            'perihelion': data['perihelion'],
            'insolation': insolation
        })
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {e}")
        return None


def global_insol(S0=1367, ecc=0.0167, eps=0.4091, perih=1.7963, nLats=181, nLons=181):
    """
    지구의 궤도 매개변수(이심률, 기울기, 세차운동)를 기반으로
    각 위도와 연중 시간에 따른 대기 상단 일일 평균 일사량을 계산하고
    결과를 2D 배열로 반환합니다.

    개선: 음수 일사량 방지 로직 추가
    """
    # 위도, 경도, 그리고 각 지점에서의 일사량을 저장할 배열 설정
    lat = np.zeros(nLats)
    lon = np.zeros(nLons)
    Qday = np.zeros((nLons, nLats))

    # 모든 지점에 대해 루프
    for j in range(nLats):
        for i in range(nLons):

            # 이 [i,j] 쌍에 대한 위도와 경도
            lat[j] = (-90 + j * 180 / (nLats - 1)) * np.pi / 180
            lon[i] = (-180 + i * 360 / (nLons - 1)) * np.pi / 180

            # 연중 이 시간(경도)에 대한 적위
            dec = eps * np.sin(lon[i])

            # 일출 시 시간각
            arg = np.tan(lat[j]) * np.tan(dec)
            if arg > 1:
                h0 = np.pi  # 영원한 여름 낮
            elif arg < -1:
                h0 = 0  # 영원한 겨울 밤
            else:
                h0 = np.arccos(-arg)  # 일반적인 일출/일몰

            # 지구-태양 거리(평균 대 실제 비율)
            R0_div_RE = 1 + ecc * np.cos(lon[i] - perih)

            # 이 위도와 시간에 대한 일일 평균 일사량
            insolation_value = S0 / np.pi * (R0_div_RE) ** 2 * \
                               (h0 * np.sin(lat[j]) * np.sin(dec) + np.cos(lat[j]) * np.cos(dec) * np.sin(h0))

            # 음수 값이 나오면 0으로 설정 (물리적으로 의미가 없는 값 방지)
            Qday[i, j] = max(0, insolation_value)

    # 라디안에서 도로 변환하여 반환
    return {
        'lat': lat * 180 / np.pi,
        'lon': lon * 180 / np.pi,
        'Qday': Qday
    }

def global_insol_time(S0=1367, ecc=0.0167, eps=0.4091, perih=1.7963, nLats=181, nLons=181):
    """
    지구의 궤도 매개변수(이심률, 기울기, 세차운동)를 기반으로
    각 위도와 연중 시간에 따른 대기 상단 일일 평균 일사량을 계산합니다.
    lon = -180은 1월 1일, lon = 180은 다음해 1월 1일에 해당합니다.

    개선:
    - 시간축을 1월 1일부터 다음해 1월 1일까지로 조정
    - 음수 일사량 방지 로직 추가
    """
    # 위도, 경도, 그리고 각 지점에서의 일사량을 저장할 배열 설정
    lat = np.zeros(nLats)
    lon = np.zeros(nLons)
    Qday = np.zeros((nLons, nLats))

    # 시간 시프트 값 (추분에서 1월 1일까지의 근사적 각도 시프트)
    time_shift = 100

    # 모든 지점에 대해 루프
    for j in range(nLats):
        for i in range(nLons):
            # 이 [i,j] 쌍에 대한 위도와 경도
            lat[j] = (-90 + j * 180 / (nLats - 1)) * np.pi / 180
            lon[i] = (-180 + i * 360 / (nLons - 1)) * np.pi / 180

            # 시간에 해당하는 각도 계산 (이것이 실제 계산에 사용됨)
            # lon[i]는 표시 좌표로 사용, time_angle은 실제 계산에 사용
            time_angle = (lon[i] * 180/np.pi + time_shift) % 360
            if time_angle > 180:
                time_angle -= 360
            time_angle *= np.pi / 180

            # 연중 이 시간에 대한 적위 (시간 각도 사용)
            dec = eps * np.sin(time_angle)

            # 일출 시 시간각
            arg = np.tan(lat[j]) * np.tan(dec)
            if arg > 1:
                h0 = np.pi  # 영원한 여름 낮
            elif arg < -1:
                h0 = 0  # 영원한 겨울 밤
            else:
                h0 = np.arccos(-arg)  # 일반적인 일출/일몰

            # 지구-태양 거리(평균 대 실제 비율) - 시간 각도 사용
            R0_div_RE = 1 + ecc * np.cos(time_angle - perih)

            # 이 위도와 시간에 대한 일일 평균 일사량
            insolation_value = S0 / np.pi * (R0_div_RE) ** 2 * \
                              (h0 * np.sin(lat[j]) * np.sin(dec) + np.cos(lat[j]) * np.cos(dec) * np.sin(h0))

            # 음수 값이 나오면 0으로 설정 (물리적으로 의미가 없는 값 방지)
            Qday[i, j] = max(0, insolation_value)

    # 라디안에서 도로 변환하여 반환 (원래 함수와 동일한 반환 구조)
    return {
        'lat': lat * 180 / np.pi,
        'lon': lon * 180 / np.pi,
        'Qday': Qday
    }

class OrbitInsolationApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # 윈도우 설정
        self.setWindowTitle("Global Orbital Insolation")
        self.setGeometry(100, 100, 1200, 800)

        # 메인 위젯 및 레이아웃 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 탭 위젯 생성
        self.tabs = QTabWidget()

        # 절댓값 구하기 탭
        self.absolute_tab = QWidget()
        self.setup_absolute_tab()
        self.tabs.addTab(self.absolute_tab, "절댓값 구하기")

        # 편차 구하기 탭
        self.difference_tab = QWidget()
        self.setup_difference_tab()
        self.tabs.addTab(self.difference_tab, "편차 구하기")

        # 직접 입력하여 절댓값 구하기 탭
        self.direct_absolute_tab = QWidget()
        self.setup_direct_absolute_tab()
        self.tabs.addTab(self.direct_absolute_tab, "직접 입력하여 절댓값 구하기")

        # 직접 입력하여 편차 구하기 탭
        self.direct_difference_tab = QWidget()
        self.setup_direct_difference_tab()
        self.tabs.addTab(self.direct_difference_tab, "직접 입력하여 편차 구하기")

        # 탭 위젯을 메인 레이아웃에 추가
        self.main_layout.addWidget(self.tabs)

        # 결과 표시 영역 설정
        self.setup_result_area()

        # 초기 상태 설정
        self.current_insol_data = None
        self.diff_insol_data = None
        self.current_mode = "absolute"  # 기본 모드는 절댓값
        self.actual_year = 0.0
        self.actual_year1 = 0.0
        self.actual_year2 = 0.0

        # 상태 바 추가
        self.statusBar().showMessage("Ready")

    def setup_absolute_tab(self):
        layout = QVBoxLayout(self.absolute_tab)

        # 입력 영역 컨테이너
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)

        # 년도 입력 필드 (단일 연도)
        self.abs_year_label = QLabel("년도 (천년):")
        input_layout.addWidget(self.abs_year_label)

        self.abs_year_input = QLineEdit("0")  # 현재 시점을 기본값으로
        self.abs_year_input.setFixedWidth(100)
        input_layout.addWidget(self.abs_year_input)

        # 확인 버튼
        self.abs_confirm_button = QPushButton("확인")
        self.abs_confirm_button.clicked.connect(self.calculate_absolute_insolation)
        input_layout.addWidget(self.abs_confirm_button)

        # 저장 버튼 그룹
        save_widget = QWidget()
        save_layout = QHBoxLayout(save_widget)

        # SVG로 저장 버튼
        self.abs_save_svg_button = QPushButton("SVG로 저장")
        self.abs_save_svg_button.clicked.connect(lambda: self.save_to_file("svg"))
        self.abs_save_svg_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.abs_save_svg_button)

        # PNG로 저장 버튼
        self.abs_save_png_button = QPushButton("PNG로 저장")
        self.abs_save_png_button.clicked.connect(lambda: self.save_to_file("png"))
        self.abs_save_png_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.abs_save_png_button)

        # 여백을 위한 스페이서 추가
        input_layout.addWidget(save_widget)
        input_layout.addStretch()

        # 레이아웃에 입력 영역 추가
        layout.addWidget(input_widget)

    def setup_difference_tab(self):
        layout = QVBoxLayout(self.difference_tab)

        # 입력 영역 컨테이너 1
        input1_group = QGroupBox("기준 연도 (Input 1)")
        input1_layout = QHBoxLayout(input1_group)

        # 년도 입력 필드 1
        self.diff_year1_label = QLabel("년도 (천년):")
        input1_layout.addWidget(self.diff_year1_label)

        self.diff_year1_input = QLineEdit("0")  # 현재 시점을 기본값으로
        self.diff_year1_input.setFixedWidth(100)
        input1_layout.addWidget(self.diff_year1_input)

        # 입력 영역 컨테이너 2
        input2_group = QGroupBox("비교 연도 (Input 2)")
        input2_layout = QHBoxLayout(input2_group)

        # 년도 입력 필드 2
        self.diff_year2_label = QLabel("년도 (천년):")
        input2_layout.addWidget(self.diff_year2_label)

        self.diff_year2_input = QLineEdit("-20")  # 2만년 전을 기본값으로
        self.diff_year2_input.setFixedWidth(100)
        input2_layout.addWidget(self.diff_year2_input)

        # 입력 영역 컨테이너 3 (버튼)
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)

        # 확인 버튼
        self.diff_confirm_button = QPushButton("확인")
        self.diff_confirm_button.clicked.connect(self.calculate_difference_insolation)
        button_layout.addWidget(self.diff_confirm_button)

        # 저장 버튼 그룹
        save_widget = QWidget()
        save_layout = QHBoxLayout(save_widget)

        # SVG로 저장 버튼
        self.diff_save_svg_button = QPushButton("SVG로 저장")
        self.diff_save_svg_button.clicked.connect(lambda: self.save_to_file("svg"))
        self.diff_save_svg_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.diff_save_svg_button)

        # PNG로 저장 버튼
        self.diff_save_png_button = QPushButton("PNG로 저장")
        self.diff_save_png_button.clicked.connect(lambda: self.save_to_file("png"))
        self.diff_save_png_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.diff_save_png_button)

        button_layout.addWidget(save_widget)

        # 레이아웃에 입력 영역 추가
        layout.addWidget(input1_group)
        layout.addWidget(input2_group)
        layout.addWidget(button_widget)

    def setup_direct_absolute_tab(self):
        layout = QVBoxLayout(self.direct_absolute_tab)

        # 입력 영역 컨테이너
        input_group = QGroupBox("궤도 매개변수 직접 입력")
        input_layout = QGridLayout(input_group)

        # Obliquity (기울기) 입력
        self.direct_abs_obliquity_label = QLabel("Obliquity (각도):")
        input_layout.addWidget(self.direct_abs_obliquity_label, 0, 0)

        self.direct_abs_obliquity_input = QLineEdit("23.5")  # 기본값
        input_layout.addWidget(self.direct_abs_obliquity_input, 0, 1)

        # Eccentricity (이심률) 입력
        self.direct_abs_eccentricity_label = QLabel("Eccentricity:")
        input_layout.addWidget(self.direct_abs_eccentricity_label, 1, 0)

        self.direct_abs_eccentricity_input = QLineEdit("0.0167")  # 기본값
        input_layout.addWidget(self.direct_abs_eccentricity_input, 1, 1)

        # Perihelion (근일점) 입력
        self.direct_abs_perihelion_label = QLabel("Perihelion (각도):")
        input_layout.addWidget(self.direct_abs_perihelion_label, 2, 0)

        self.direct_abs_perihelion_input = QLineEdit("102.9")  # 기본값
        input_layout.addWidget(self.direct_abs_perihelion_input, 2, 1)

        # 정보 라벨 추가
        info_label = QLabel(r"※ 각도 값은 자동으로 라디안으로 변환됩니다.\n현재=102.9도\n다른 시기=(세차 운동한 각도)+102.9도")
        info_label.setStyleSheet("color: blue;")
        input_layout.addWidget(info_label, 3, 0, 1, 2)

        # 버튼 컨테이너
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)

        # 확인 버튼
        self.direct_abs_confirm_button = QPushButton("확인")
        self.direct_abs_confirm_button.clicked.connect(self.calculate_direct_absolute_insolation)
        button_layout.addWidget(self.direct_abs_confirm_button)

        # 저장 버튼 그룹
        save_widget = QWidget()
        save_layout = QHBoxLayout(save_widget)

        # SVG로 저장 버튼
        self.direct_abs_save_svg_button = QPushButton("SVG로 저장")
        self.direct_abs_save_svg_button.clicked.connect(lambda: self.save_to_file("svg"))
        self.direct_abs_save_svg_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.direct_abs_save_svg_button)

        # PNG로 저장 버튼
        self.direct_abs_save_png_button = QPushButton("PNG로 저장")
        self.direct_abs_save_png_button.clicked.connect(lambda: self.save_to_file("png"))
        self.direct_abs_save_png_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.direct_abs_save_png_button)

        button_layout.addWidget(save_widget)

        # 레이아웃에 입력 영역과 버튼 추가
        layout.addWidget(input_group)
        layout.addWidget(button_widget)

    def setup_direct_difference_tab(self):
        layout = QVBoxLayout(self.direct_difference_tab)

        # 입력 영역 컨테이너 1 (Input 1)
        input1_group = QGroupBox("기준 매개변수 (Input 1)")
        input1_layout = QGridLayout(input1_group)

        # Input 1 Obliquity (기울기) 입력
        self.direct_diff_obliquity1_label = QLabel("Obliquity (각도):")
        input1_layout.addWidget(self.direct_diff_obliquity1_label, 0, 0)

        self.direct_diff_obliquity1_input = QLineEdit("23.5")  # 기본값
        input1_layout.addWidget(self.direct_diff_obliquity1_input, 0, 1)

        # Input 1 Eccentricity (이심률) 입력
        self.direct_diff_eccentricity1_label = QLabel("Eccentricity:")
        input1_layout.addWidget(self.direct_diff_eccentricity1_label, 1, 0)

        self.direct_diff_eccentricity1_input = QLineEdit("0.0167")  # 기본값
        input1_layout.addWidget(self.direct_diff_eccentricity1_input, 1, 1)

        # Input 1 Perihelion (근일점) 입력
        self.direct_diff_perihelion1_label = QLabel("Perihelion (각도):")
        input1_layout.addWidget(self.direct_diff_perihelion1_label, 2, 0)

        self.direct_diff_perihelion1_input = QLineEdit("102.9")  # 기본값
        input1_layout.addWidget(self.direct_diff_perihelion1_input, 2, 1)

        # 입력 영역 컨테이너 2 (Input 2)
        input2_group = QGroupBox("비교 매개변수 (Input 2)")
        input2_layout = QGridLayout(input2_group)

        # Input 2 Obliquity (기울기) 입력
        self.direct_diff_obliquity2_label = QLabel("Obliquity (각도):")
        input2_layout.addWidget(self.direct_diff_obliquity2_label, 0, 0)

        self.direct_diff_obliquity2_input = QLineEdit("22.0")  # 기본값
        input2_layout.addWidget(self.direct_diff_obliquity2_input, 0, 1)

        # Input 2 Eccentricity (이심률) 입력
        self.direct_diff_eccentricity2_label = QLabel("Eccentricity:")
        input2_layout.addWidget(self.direct_diff_eccentricity2_label, 1, 0)

        self.direct_diff_eccentricity2_input = QLineEdit("0.02")  # 기본값
        input2_layout.addWidget(self.direct_diff_eccentricity2_input, 1, 1)

        # Input 2 Perihelion (근일점) 입력
        self.direct_diff_perihelion2_label = QLabel("Perihelion (각도):")
        input2_layout.addWidget(self.direct_diff_perihelion2_label, 2, 0)

        self.direct_diff_perihelion2_input = QLineEdit("90.0")  # 기본값
        input2_layout.addWidget(self.direct_diff_perihelion2_input, 2, 1)

        # 정보 라벨 추가
        info_label = QLabel("※ 각도 값은 자동으로 라디안으로 변환됩니다.")
        info_label.setStyleSheet("color: blue;")

        # 버튼 컨테이너
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)

        # 확인 버튼
        self.direct_diff_confirm_button = QPushButton("확인")
        self.direct_diff_confirm_button.clicked.connect(self.calculate_direct_difference_insolation)
        button_layout.addWidget(self.direct_diff_confirm_button)

        # 저장 버튼 그룹
        save_widget = QWidget()
        save_layout = QHBoxLayout(save_widget)

        # SVG로 저장 버튼
        self.direct_diff_save_svg_button = QPushButton("SVG로 저장")
        self.direct_diff_save_svg_button.clicked.connect(lambda: self.save_to_file("svg"))
        self.direct_diff_save_svg_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.direct_diff_save_svg_button)

        # PNG로 저장 버튼
        self.direct_diff_save_png_button = QPushButton("PNG로 저장")
        self.direct_diff_save_png_button.clicked.connect(lambda: self.save_to_file("png"))
        self.direct_diff_save_png_button.setEnabled(False)  # 처음에는 비활성화
        save_layout.addWidget(self.direct_diff_save_png_button)

        button_layout.addWidget(save_widget)

        # 레이아웃에 입력 영역과 버튼 추가
        layout.addWidget(input1_group)
        layout.addWidget(input2_group)
        layout.addWidget(info_label)
        layout.addWidget(button_widget)

    def setup_result_area(self):
        # 결과 표시 영역 (Matplotlib Figure)
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.main_layout.addWidget(self.canvas)

        # Matplotlib 툴바 추가
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.main_layout.addWidget(self.toolbar)

    def calculate_absolute_insolation(self):
        try:
            # 상태 표시
            self.statusBar().showMessage("계산 중...")

            # 입력값 가져오기 (단일 연도)
            year = float(self.abs_year_input.text())

            # 원하는 연도 주변의 데이터를 가져오기 위해 작은 범위 설정
            # 정확한 연도가 없을 수 있으므로 약간의 여유를 둠
            margin = 1.0  # 1천년의 여유
            result = laskar(start_time=year - margin, end_time=year + margin)

            if result is None or result.empty:
                QMessageBox.critical(self, "계산 오류", "궤도 데이터를 계산하는 중 오류가 발생했습니다.")
                self.statusBar().showMessage("계산 오류")
                return

            # 입력 연도와 가장 가까운 데이터 선택
            result['year_diff'] = abs(result['time'] - year)
            closest_index = result['year_diff'].idxmin()
            current_params = result.loc[closest_index]

            # 선택된 연도의 실제 값 확인
            actual_year = current_params['time']

            # 글로벌 일사량 계산
            self.current_insol_data = global_insol_time(
                ecc=current_params['eccentricity'],
                eps=current_params['obliquity'],
                perih=current_params['perihelion']
            )

            # 사용된 실제 연도 저장 (플롯 타이틀용)
            self.actual_year = actual_year

            # 현재 모드 설정
            self.current_mode = "absolute"

            # 결과 표시
            self.plot_insolation()

            # 저장 버튼 활성화
            self.abs_save_svg_button.setEnabled(True)
            self.abs_save_png_button.setEnabled(True)

            # 상태 업데이트
            self.statusBar().showMessage(f"절댓값 계산 완료: 연도 = {actual_year:.2f}k")

        except ValueError:
            QMessageBox.warning(self, "입력 오류", "년도는 숫자로 입력해야 합니다.")
            self.statusBar().showMessage("입력 오류")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"계산 중 오류가 발생했습니다: {str(e)}")
            self.statusBar().showMessage(f"오류: {str(e)}")

    def calculate_difference_insolation(self):
        try:
            # 상태 표시
            self.statusBar().showMessage("차이 계산 중...")

            # 입력값 가져오기 (두 개의 연도)
            year1 = float(self.diff_year1_input.text())  # 기준 연도
            year2 = float(self.diff_year2_input.text())  # 비교 연도

            # 첫 번째 연도의 데이터 계산
            margin = 1.0
            result1 = laskar(start_time=year1 - margin, end_time=year1 + margin)

            if result1 is None or result1.empty:
                QMessageBox.critical(self, "계산 오류", "첫 번째 연도의 궤도 데이터를 계산하는 중 오류가 발생했습니다.")
                self.statusBar().showMessage("첫 번째 연도 계산 오류")
                return

            # 첫 번째 연도와 가장 가까운 데이터 선택
            result1['year_diff'] = abs(result1['time'] - year1)
            closest_index1 = result1['year_diff'].idxmin()
            params1 = result1.loc[closest_index1]

            # 두 번째 연도의 데이터 계산
            result2 = laskar(start_time=year2 - margin, end_time=year2 + margin)

            if result2 is None or result2.empty:
                QMessageBox.critical(self, "계산 오류", "두 번째 연도의 궤도 데이터를 계산하는 중 오류가 발생했습니다.")
                self.statusBar().showMessage("두 번째 연도 계산 오류")
                return

            # 두 번째 연도와 가장 가까운 데이터 선택
            result2['year_diff'] = abs(result2['time'] - year2)
            closest_index2 = result2['year_diff'].idxmin()
            params2 = result2.loc[closest_index2]

            # 선택된 연도의 실제 값 확인
            self.actual_year1 = params1['time']
            self.actual_year2 = params2['time']

            # 두 연도의 글로벌 일사량 계산
            insol1 = global_insol_time(
                ecc=params1['eccentricity'],
                eps=params1['obliquity'],
                perih=params1['perihelion']
            )

            insol2 = global_insol_time(
                ecc=params2['eccentricity'],
                eps=params2['obliquity'],
                perih=params2['perihelion']
            )

            # 두 일사량의 차이 계산 (insol1 - insol2)
            self.diff_insol_data = {
                'lat': insol1['lat'],
                'lon': insol1['lon'],
                'Qday': insol1['Qday'] - insol2['Qday']
            }

            # 현재 모드 설정
            self.current_mode = "difference"

            # 결과 표시
            self.plot_difference()

            # 저장 버튼 활성화
            self.diff_save_svg_button.setEnabled(True)
            self.diff_save_png_button.setEnabled(True)

            # 상태 업데이트
            self.statusBar().showMessage(f"차이 계산 완료: {self.actual_year1:.2f}k - {self.actual_year2:.2f}k")

        except ValueError:
            QMessageBox.warning(self, "입력 오류", "년도는 숫자로 입력해야 합니다.")
            self.statusBar().showMessage("입력 오류")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"계산 중 오류가 발생했습니다: {str(e)}")
            self.statusBar().showMessage(f"오류: {str(e)}")

    def calculate_direct_absolute_insolation(self):
        try:
            # 상태 표시
            self.statusBar().showMessage("직접 입력 절댓값 계산 중...")

            # 입력값 가져오기
            obliquity_deg = float(self.direct_abs_obliquity_input.text())
            eccentricity = float(self.direct_abs_eccentricity_input.text())
            perihelion_deg = float(self.direct_abs_perihelion_input.text())

            # 각도값을 라디안으로 변환
            obliquity_rad = np.radians(obliquity_deg)
            perihelion_rad = np.radians(perihelion_deg)

            # 글로벌 일사량 계산
            self.current_insol_data = global_insol_time(
                ecc=eccentricity,
                eps=obliquity_rad,
                perih=perihelion_rad
            )

            # 타이틀용 정보 저장
            self.direct_abs_params = {
                'obliquity': obliquity_deg,
                'eccentricity': eccentricity,
                'perihelion': perihelion_deg
            }

            # 현재 모드 설정
            self.current_mode = "direct_absolute"

            # 결과 표시
            self.plot_direct_absolute()

            # 저장 버튼 활성화
            self.direct_abs_save_svg_button.setEnabled(True)
            self.direct_abs_save_png_button.setEnabled(True)

            # 상태 업데이트
            self.statusBar().showMessage(
                f"직접 입력 절댓값 계산 완료: Obliquity={obliquity_deg}°, Ecc={eccentricity}, Peri={perihelion_deg}°")

        except ValueError:
            QMessageBox.warning(self, "입력 오류", "모든 입력값은 숫자로 입력해야 합니다.")
            self.statusBar().showMessage("입력 오류")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"계산 중 오류가 발생했습니다: {str(e)}")
            self.statusBar().showMessage(f"오류: {str(e)}")

    def calculate_direct_difference_insolation(self):
        try:
            # 상태 표시
            self.statusBar().showMessage("직접 입력 차이 계산 중...")

            # 입력값 가져오기 (Input 1)
            obliquity1_deg = float(self.direct_diff_obliquity1_input.text())
            eccentricity1 = float(self.direct_diff_eccentricity1_input.text())
            perihelion1_deg = float(self.direct_diff_perihelion1_input.text())

            # 입력값 가져오기 (Input 2)
            obliquity2_deg = float(self.direct_diff_obliquity2_input.text())
            eccentricity2 = float(self.direct_diff_eccentricity2_input.text())
            perihelion2_deg = float(self.direct_diff_perihelion2_input.text())

            # 각도값을 라디안으로 변환 (Input 1)
            obliquity1_rad = np.radians(obliquity1_deg)
            perihelion1_rad = np.radians(perihelion1_deg)

            # 각도값을 라디안으로 변환 (Input 2)
            obliquity2_rad = np.radians(obliquity2_deg)
            perihelion2_rad = np.radians(perihelion2_deg)

            # 두 세트의 글로벌 일사량 계산
            insol1 = global_insol_time(
                ecc=eccentricity1,
                eps=obliquity1_rad,
                perih=perihelion1_rad
            )

            insol2 = global_insol_time(
                ecc=eccentricity2,
                eps=obliquity2_rad,
                perih=perihelion2_rad
            )

            # 두 일사량의 차이 계산 (insol1 - insol2)
            self.diff_insol_data = {
                'lat': insol1['lat'],
                'lon': insol1['lon'],
                'Qday': insol1['Qday'] - insol2['Qday']
            }

            # 타이틀용 정보 저장
            self.direct_diff_params1 = {
                'obliquity': obliquity1_deg,
                'eccentricity': eccentricity1,
                'perihelion': perihelion1_deg
            }

            self.direct_diff_params2 = {
                'obliquity': obliquity2_deg,
                'eccentricity': eccentricity2,
                'perihelion': perihelion2_deg
            }

            # 현재 모드 설정
            self.current_mode = "direct_difference"

            # 결과 표시
            self.plot_direct_difference()

            # 저장 버튼 활성화
            self.direct_diff_save_svg_button.setEnabled(True)
            self.direct_diff_save_png_button.setEnabled(True)

            # 상태 업데이트
            self.statusBar().showMessage("직접 입력 차이 계산 완료")

        except ValueError:
            QMessageBox.warning(self, "입력 오류", "모든 입력값은 숫자로 입력해야 합니다.")
            self.statusBar().showMessage("입력 오류")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"계산 중 오류가 발생했습니다: {str(e)}")
            self.statusBar().showMessage(f"오류: {str(e)}")

    def plot_insolation(self):
        if self.current_insol_data is None:
            return

        # 그림 초기화
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # x, y 레이블 설정
        x_labels = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
            'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'JAN']
        y_labels = ['SP', '60 S', '30 S', 'EQ', '30N', '60 N', 'NP']

        # 컬러맵 설정
        cmap = 'gray_r'  # 시각적으로 더 명확한 컬러맵

        # 데이터에서 최소/최대값 검사
        min_val = np.min(self.current_insol_data['Qday'])
        max_val = np.max(self.current_insol_data['Qday'])

        # 상태 업데이트에 최소/최대값 포함
        self.statusBar().showMessage(
            f"절댓값 계산 완료: 연도 = {self.actual_year:.2f}k, 최소값: {min_val:.2f}, 최대값: {max_val:.2f} W·m⁻²")

        # 음수 값이 존재하는지 확인
        has_negative = (min_val < 0)
        if has_negative:
            print(f"경고: 음수 일사량 값이 발견되었습니다! 최소값: {min_val:.2f} W·m⁻²")
            QMessageBox.warning(self, "계산 경고",
                                f"음수 일사량 값이 발견되었습니다!\n최소값: {min_val:.2f} W·m⁻²\n이론적으로 일사량은 음수가 될 수 없습니다.")

        # 컬러 이미지 플롯 그리기
        im = ax.contourf(self.current_insol_data['lon'], self.current_insol_data['lat'],
                         self.current_insol_data['Qday'].T, levels=20, cmap=cmap)

        # 등고선 라인 추가
        contour = ax.contour(self.current_insol_data['lon'], self.current_insol_data['lat'],
                             self.current_insol_data['Qday'].T, colors='k', alpha=0.5)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%1.0f')  # 등고선에 값 표시

        # 축 설정
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_xticks(np.arange(-180, 181, 30))
        ax.set_xticklabels(x_labels)
        ax.set_yticks(np.arange(-90, 91, 30))
        ax.set_yticklabels(y_labels)

        # 그리드 추가
        ax.grid(True, linestyle='--', alpha=0.3)

        # 레이블 설정
        ax.set_xlabel('Month')
        ax.set_ylabel('Latitude')
        ax.set_title(f"Global Insolation\nYear: {self.actual_year:.2f}k" +
                     '\n' + r'$W \cdot m^{-2}$')

        # 컬러바 추가
        cbar = self.figure.colorbar(im, ax=ax, label=r'$W \cdot m^{-2}$')

        # 궤도 매개변수 텍스트 추가
        orbit_params = self.get_orbit_params(self.actual_year)
        if orbit_params:
            param_text = (f"Eccentricity: {orbit_params['eccentricity']:.4f}\n"
                          f"Obliquity: {orbit_params['obliquity']:.4f} rad\n"
                          f"Perihelion: {orbit_params['perihelion']:.4f} rad")
            self.figure.text(0.02, 0.02, param_text, fontsize=8)

        # 그림 업데이트
        self.figure.tight_layout()
        self.canvas.draw()

    def plot_difference(self):
        if self.diff_insol_data is None:
            return

        # 그림 초기화
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # x, y 레이블 설정
        x_labels = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
            'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'JAN']
        y_labels = ['SP', '60 S', '30 S', 'EQ', '30N', '60 N', 'NP']

        # 블루-화이트-레드 컬러맵 사용 (차이 플롯용)
        cmap = 'gray_r'  # 더 뚜렷한 적청 대비 컬러맵

        # 차이 데이터의 최대 절댓값 계산
        max_abs = np.max(np.abs(self.diff_insol_data['Qday']))

        # 최소/최대값 구하기
        min_val = np.min(self.diff_insol_data['Qday'])
        max_val = np.max(self.diff_insol_data['Qday'])

        # 상태 업데이트에 최소/최대값 포함
        self.statusBar().showMessage(
            f"차이 계산 완료: {self.actual_year1:.2f}k - {self.actual_year2:.2f}k, 최소값: {min_val:.2f}, 최대값: {max_val:.2f} W·m⁻²")

        # 대칭 범위 설정 (양수/음수 값이 같은 색상 범위를 갖도록)
        vmin, vmax = -max_abs, max_abs

        # 컬러 이미지 플롯 그리기
        im = ax.contourf(self.diff_insol_data['lon'], self.diff_insol_data['lat'],
                         self.diff_insol_data['Qday'].T, levels=20, cmap=cmap,
                         vmin=vmin, vmax=vmax, extend='both')

        # 등고선 라인 추가
        contour = ax.contour(self.diff_insol_data['lon'], self.diff_insol_data['lat'],
                             self.diff_insol_data['Qday'].T, colors='k', alpha=0.5)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%1.0f')  # 등고선에 값 표시

        # 축 설정
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_xticks(np.arange(-180, 181, 30))
        ax.set_xticklabels(x_labels)
        ax.set_yticks(np.arange(-90, 91, 30))
        ax.set_yticklabels(y_labels)

        # 그리드 추가
        ax.grid(True, linestyle='--', alpha=0.3)

        # 레이블 설정
        ax.set_xlabel('Month')
        ax.set_ylabel('Latitude')
        ax.set_title(f"Insolation Difference\nYear1: {self.actual_year1:.2f}k - Year2: {self.actual_year2:.2f}k" +
                     '\n' + r'$W \cdot m^{-2}$')

        # 컬러바 추가
        cbar = self.figure.colorbar(im, ax=ax, label=r'$W \cdot m^{-2}')

        # 궤도 매개변수 차이 텍스트 추가
        orbit_params1 = self.get_orbit_params(self.actual_year1)
        orbit_params2 = self.get_orbit_params(self.actual_year2)

        if orbit_params1 and orbit_params2:
            param_diff_text = (
                f"Δ Eccentricity: {orbit_params1['eccentricity'] - orbit_params2['eccentricity']:.4f}\n"
                f"Δ Obliquity: {orbit_params1['obliquity'] - orbit_params2['obliquity']:.4f} rad\n"
                f"Δ Perihelion: {orbit_params1['perihelion'] - orbit_params2['perihelion']:.4f} rad"
            )
            self.figure.text(0.02, 0.02, param_diff_text, fontsize=8)

        # 그림 업데이트
        self.figure.tight_layout()
        self.canvas.draw()

    def plot_direct_absolute(self):
        if self.current_insol_data is None:
            return

        # 그림 초기화
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # x, y 레이블 설정
        x_labels = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
            'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'JAN']
        y_labels = ['SP', '60 S', '30 S', 'EQ', '30N', '60 N', 'NP']

        # 컬러맵 설정
        cmap = 'gray_r'  # 시각적으로 더 명확한 컬러맵

        # 데이터에서 최소/최대값 검사
        min_val = np.min(self.current_insol_data['Qday'])
        max_val = np.max(self.current_insol_data['Qday'])

        # 상태 업데이트에 최소/최대값 포함
        self.statusBar().showMessage(
            f"직접 입력 절댓값 계산 완료: 최소값: {min_val:.2f}, 최대값: {max_val:.2f} W·m⁻²")

        # 음수 값이 존재하는지 확인
        has_negative = (min_val < 0)
        if has_negative:
            print(f"경고: 음수 일사량 값이 발견되었습니다! 최소값: {min_val:.2f} W·m⁻²")
            QMessageBox.warning(self, "계산 경고",
                                f"음수 일사량 값이 발견되었습니다!\n최소값: {min_val:.2f} W·m⁻²\n이론적으로 일사량은 음수가 될 수 없습니다.")

        # 컬러 이미지 플롯 그리기
        im = ax.contourf(self.current_insol_data['lon'], self.current_insol_data['lat'],
                         self.current_insol_data['Qday'].T, levels=20, cmap=cmap)

        # 등고선 라인 추가
        contour = ax.contour(self.current_insol_data['lon'], self.current_insol_data['lat'],
                             self.current_insol_data['Qday'].T, colors='k', alpha=0.5)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%1.0f')  # 등고선에 값 표시

        # 축 설정
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_xticks(np.arange(-180, 181, 30))
        ax.set_xticklabels(x_labels)
        ax.set_yticks(np.arange(-90, 91, 30))
        ax.set_yticklabels(y_labels)

        # 그리드 추가
        ax.grid(True, linestyle='--', alpha=0.3)

        # 레이블 설정
        ax.set_xlabel('Month')
        ax.set_ylabel('Latitude')
        ax.set_title(f"Global Insolation (Direct Input)\n" +
                     f"Obliquity: {self.direct_abs_params['obliquity']}°, " +
                     f"Eccentricity: {self.direct_abs_params['eccentricity']}, " +
                     f"Perihelion: {self.direct_abs_params['perihelion']}°\n" +
                     r'$W \cdot m^{-2}$')

        # 컬러바 추가
        cbar = self.figure.colorbar(im, ax=ax, label=r'$W \cdot m^{-2}$')

        # 궤도 매개변수 텍스트 추가 (라디안 값)
        obliquity_rad = np.radians(self.direct_abs_params['obliquity'])
        perihelion_rad = np.radians(self.direct_abs_params['perihelion'])

        param_text = (f"Eccentricity: {self.direct_abs_params['eccentricity']:.4f}\n"
                      f"Obliquity: {obliquity_rad:.4f} rad ({self.direct_abs_params['obliquity']}°)\n"
                      f"Perihelion: {perihelion_rad:.4f} rad ({self.direct_abs_params['perihelion']}°)")
        self.figure.text(0.02, 0.02, param_text, fontsize=8)

        # 그림 업데이트
        self.figure.tight_layout()
        self.canvas.draw()

    def plot_direct_difference(self):
        if self.diff_insol_data is None:
            return

        # 그림 초기화
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # x, y 레이블 설정
        x_labels = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
            'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'JAN']
        y_labels = ['SP', '60 S', '30 S', 'EQ', '30N', '60 N', 'NP']

        # 블루-화이트-레드 컬러맵 사용 (차이 플롯용)
        cmap = 'gray_r'  # 더 뚜렷한 적청 대비 컬러맵

        # 차이 데이터의 최대 절댓값 계산
        max_abs = np.max(np.abs(self.diff_insol_data['Qday']))

        # 최소/최대값 구하기
        min_val = np.min(self.diff_insol_data['Qday'])
        max_val = np.max(self.diff_insol_data['Qday'])

        # 상태 업데이트에 최소/최대값 포함
        self.statusBar().showMessage(
            f"직접 입력 차이 계산 완료: 최소값: {min_val:.2f}, 최대값: {max_val:.2f} W·m⁻²")

        # 대칭 범위 설정 (양수/음수 값이 같은 색상 범위를 갖도록)
        vmin, vmax = -max_abs, max_abs

        # 컬러 이미지 플롯 그리기
        im = ax.contourf(self.diff_insol_data['lon'], self.diff_insol_data['lat'],
                         self.diff_insol_data['Qday'].T, levels=20, cmap=cmap,
                         vmin=vmin, vmax=vmax, extend='both')

        # 등고선 라인 추가
        contour = ax.contour(self.diff_insol_data['lon'], self.diff_insol_data['lat'],
                             self.diff_insol_data['Qday'].T, colors='k', alpha=0.5)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%1.0f')  # 등고선에 값 표시

        # 축 설정
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_xticks(np.arange(-180, 181, 30))
        ax.set_xticklabels(x_labels)
        ax.set_yticks(np.arange(-90, 91, 30))
        ax.set_yticklabels(y_labels)

        # 그리드 추가
        ax.grid(True, linestyle='--', alpha=0.3)

        # 레이블 설정
        ax.set_xlabel('Month')
        ax.set_ylabel('Latitude')

        # 제목에 입력 정보 표시
        ax.set_title(f"Insolation Difference (Direct Input)\n" +
                     f"Input1: Obl={self.direct_diff_params1['obliquity']}°, " +
                     f"Ecc={self.direct_diff_params1['eccentricity']}, " +
                     f"Peri={self.direct_diff_params1['perihelion']}°\n" +
                     f"Input2: Obl={self.direct_diff_params2['obliquity']}°, " +
                     f"Ecc={self.direct_diff_params2['eccentricity']}, " +
                     f"Peri={self.direct_diff_params2['perihelion']}°\n" +
                     r'$W \cdot m^{-2}$')

        # 컬러바 추가
        cbar = self.figure.colorbar(im, ax=ax, label=r'$W \cdot m^{-2}')

        # 궤도 매개변수 차이 텍스트 추가
        # 각도 값을 라디안으로 변환
        obliquity1_rad = np.radians(self.direct_diff_params1['obliquity'])
        perihelion1_rad = np.radians(self.direct_diff_params1['perihelion'])

        obliquity2_rad = np.radians(self.direct_diff_params2['obliquity'])
        perihelion2_rad = np.radians(self.direct_diff_params2['perihelion'])

        param_diff_text = (
            f"Δ Eccentricity: {self.direct_diff_params1['eccentricity'] - self.direct_diff_params2['eccentricity']:.4f}\n"
            f"Δ Obliquity: {obliquity1_rad - obliquity2_rad:.4f} rad ({self.direct_diff_params1['obliquity'] - self.direct_diff_params2['obliquity']:.1f}°)\n"
            f"Δ Perihelion: {perihelion1_rad - perihelion2_rad:.4f} rad ({self.direct_diff_params1['perihelion'] - self.direct_diff_params2['perihelion']:.1f}°)"
        )
        self.figure.text(0.02, 0.02, param_diff_text, fontsize=8)

        # 그림 업데이트
        self.figure.tight_layout()
        self.canvas.draw()

    def get_orbit_params(self, year):
        """주어진 연도에 대한 궤도 매개변수를 찾아 반환합니다."""
        try:
            margin = 1.0
            result = laskar(start_time=year - margin, end_time=year + margin)

            if result is None or result.empty:
                return None

            result['year_diff'] = abs(result['time'] - year)
            closest_index = result['year_diff'].idxmin()
            params = result.loc[closest_index]

            return {
                'eccentricity': params['eccentricity'],
                'obliquity': params['obliquity'],
                'perihelion': params['perihelion']
            }
        except Exception:
            return None

    def save_to_file(self, format_type):
        """현재 그림을 지정된 형식으로 저장합니다."""
        if (self.current_mode in ["absolute", "direct_absolute"] and self.current_insol_data is None) or \
                (self.current_mode in ["difference", "direct_difference"] and self.diff_insol_data is None):
            QMessageBox.warning(self, "저장 오류", "저장할 데이터가 없습니다.")
            return

        try:
            # 기본 파일 이름 설정
            default_filename = "orbit_insolation"
            if self.current_mode == "absolute":
                default_filename += f"_{self.actual_year:.2f}k"
            elif self.current_mode == "difference":
                default_filename += f"_diff_{self.actual_year1:.2f}k_vs_{self.actual_year2:.2f}k"
            elif self.current_mode == "direct_absolute":
                default_filename += "_direct_abs"
            elif self.current_mode == "direct_difference":
                default_filename += "_direct_diff"

            # 저장 경로 다이얼로그 열기
            file_path, _ = QFileDialog.getSaveFileName(
                self, "그림 저장",
                default_filename + "." + format_type,
                f"{format_type.upper()} Files (*.{format_type})"
            )

            if not file_path:  # 사용자가 취소한 경우
                return

            # 파일 형식이 선택된 형식과 일치하는지 확인
            if not file_path.lower().endswith("." + format_type):
                file_path += "." + format_type

            # 그림 저장
            self.figure.savefig(file_path, format=format_type, bbox_inches='tight', dpi=300)

            # 저장 성공 메시지
            QMessageBox.information(self, "저장 성공", f"그래프가 성공적으로 저장되었습니다.\n경로: {file_path}")
            self.statusBar().showMessage(f"파일 저장 완료: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류가 발생했습니다: {str(e)}")
            self.statusBar().showMessage(f"저장 오류: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OrbitInsolationApp()
    window.show()
    sys.exit(app.exec_())