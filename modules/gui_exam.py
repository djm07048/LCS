from utils.path import *
from os import environ
import shutil
import subprocess
import sys
import os
from utils.data import *
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QComboBox, QMessageBox, QLineEdit, QMenu,
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QGridLayout, QInputDialog,
                             QHeaderView, QCheckBox, QDialog, QVBoxLayout, QLabel, QSizePolicy, QTextEdit)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QTimer)
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QPushButton,
                             QListWidget, QListWidgetItem, QAbstractItemView)

from main import build_exam_test
from main import build_duplex
from PyQt5.QtGui import QIcon
from hwps.multi_printer import *
from rasterizer import *
from utils.path import *
from utils.coord import Coord
from utils.ratio import Ratio

from overlayer import *
from utils.overlay_object import *

import traceback
from PyQt5.QtCore import Qt, QSortFilterProxyModel

def suppress_qt_warnings():
    environ["QT_DEVICE_PIXEL_RATIO"] = "0"
    environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    environ["QT_SCREEN_SCALE_FACTORS"] = "1"
    environ["QT_SCALE_FACTOR"] = "1"

class QPushButtonGui(QPushButton):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

class ColoredTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_manager = parent

    def get_topic_quater(self, topic):
        file = RESOURCES_PATH + "/test_topic.json"
        with open(file, 'r', encoding='UTF8') as f:
            topic_data = json.load(f)
        if topic in topic_data:
            return topic_data[topic]
        else:
            raise ValueError(f"Topic {topic} not found in topic data.")

    def get_topic_color_code(self, topic):
        topic_color_code = ["#FF8A80", "#FFAB91", "#FFCDD2", "#FF9800", "#FFC107",
                            "#FFD54F", "#81C784", "#A5D6A7", "#C8E6C9", "#2196F3",
                            "#42A5F5", "#64B5F6", "#90CAF9", "#B39DDB", "#CE93D8",
                            "#E1BEE7", "#F0D5D4", "#C4B5A0", "#D4C4B0", "#E4D4C0"]

        color = topic_color_code[topic - 1]
        return QColor(color)

    def setItem(self, row, column, item):
        super().setItem(row, column, item)

        # col = 0이고 item이 있을 때만 색상 적용
        if column == 0 and item and item.text():
            item_code = item.text()
            if len(item_code) >= 5:  # 유효한 item_code인지 확인
                try:
                    topic = item_code[2:5]  # item_code[2:5]로 topic 추출
                    quater = self.get_topic_quater(topic)
                    color = self.get_topic_color_code(quater)
                    item.setBackground(color)
                except (ValueError, KeyError, IndexError):
                    pass  # 색상 적용 실패 시 기본 색상 유지

        # Topic 테이블 업데이트를 지연 처리로 변경
        if hasattr(self.parent_manager, 'schedule_topic_update'):
            self.parent_manager.schedule_topic_update()

class PDFCreationThread(QThread):
    progress_signal = pyqtSignal(str)

    def __init__(self, item_list):
        super().__init__()
        self.item_list = item_list

    def run(self):
        try:
            create_pdfs(self.item_list, log_callback=self.log_message)
        except Exception as e:
            self.progress_signal.emit(f"Error during PDF creation: {e}")

    def log_message(self, message):
        self.progress_signal.emit(message)

class DatabaseManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.topic_order_data = None
        self.topic_update_scheduled = False
        self.original_pool_data = []

        self.initUI()
        self.load_kice_topics()
        self.list_used_items = self.get_list_used_items()
        print("List used items:", self.list_used_items)
        self.loadData()
        self.load_topic_table()  # 새로 추가
        self.add_context_menu()
        self.sort_pool_by_order()

        self.setWindowTitle('Lab Contents Software ver.2.0.0. Powered by THedu')

    def initUI(self):
        self.setWindowTitle('Database Manager')
        self.setGeometry(100, 100, 1550, 700)  # Adjusted width to accommodate log window

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout()
        main_widget.setLayout(layout)

        # Pool section
        pool_layout = QVBoxLayout()

        # Top buttons for Pool
        pool_top_layout = QVBoxLayout()
        self.deselect_btn = QPushButtonGui('DESELECT POOL')
        self.sort_btn = QPushButtonGui('SORT POOL')
        self.filter_btn = QPushButtonGui('FILTER TOPICS')  # 새로 추가
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Search Item Code...')

        pool_top_layout.addWidget(self.deselect_btn)
        pool_top_layout.addWidget(self.sort_btn)
        pool_top_layout.addWidget(self.filter_btn)  # 새로 추가
        pool_top_layout.addWidget(self.search_input)
        pool_layout.addLayout(pool_top_layout)

        # Pool table with fixed dimensions
        self.pool_table = QTableWidget()
        self.pool_table.setColumnCount(4)
        self.pool_table.setFixedHeight(650)

        pool_layout.addWidget(self.pool_table)
        self.pool_table.setHorizontalHeaderLabels(['Item Code', 'Topic', 'Order', 'reference'])

        # Set fixed column widths for Pool table
        self.pool_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.pool_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.pool_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.pool_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)

        self.pool_table.setColumnWidth(0, 120)  # Item Code
        self.pool_table.setColumnWidth(1, 50)  # Topic
        self.pool_table.setColumnWidth(2, 0)  # Order (hidden)
        self.pool_table.setColumnWidth(3, 80)  # Hidden column for Order

        # Calculate and set fixed total width
        total_width = sum([self.pool_table.columnWidth(i) for i in range(4)])  # Exclude hidden Order column
        self.pool_table.setFixedWidth(total_width + 50)

        # Hide Order column
        self.pool_table.hideColumn(2)

        # Middle buttons
        button_layout = QVBoxLayout()
        self.transfer_btn = QPushButtonGui('→')
        self.add_btn = QPushButtonGui('+')
        self.remove_btn = QPushButtonGui('-')
        self.up_btn = QPushButtonGui('▲')
        self.down_btn = QPushButtonGui('▼')
        button_layout.addWidget(self.transfer_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addWidget(self.up_btn)
        button_layout.addWidget(self.down_btn)

        # List section
        list_layout = QVBoxLayout()

        # Top buttons for List
        list_top_layout = QVBoxLayout()
        self.list_deselect_btn = QPushButtonGui('DESELECT LIST')
        self.list_renumber_btn = QPushButtonGui('RENUMBER')
        list_top_layout.addWidget(self.list_deselect_btn)
        list_top_layout.addWidget(self.list_renumber_btn)
        list_layout.addLayout(list_top_layout)

        # List table with fixed dimensions
        self.list_table = ColoredTableWidget(self)
        self.list_table.setColumnCount(6)
        self.list_table.setFixedHeight(700)
        self.list_table.setHorizontalHeaderLabels(['Item Code', '번', '점', '단', '문항', '개념'])

        # Set fixed column widths for List table
        self.list_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)

        # Set exact column widths
        self.list_table.setColumnWidth(0, 120)  # Item Code
        self.list_table.setColumnWidth(1, 30)  # number
        self.list_table.setColumnWidth(2, 30)  # score
        self.list_table.setColumnWidth(3, 50)  # para
        self.list_table.setColumnWidth(4, 50)  # list_rel_item_code
        self.list_table.setColumnWidth(5, 50)  # list_theory_piece_code

        # Calculate and set fixed total width
        self.list_table.setFixedWidth(350)
        list_layout.addWidget(self.list_table)

        # Header
        self.list_table.horizontalHeader().sectionClicked.connect(self.sort_list)

        # Right buttons
        right_button_layout = QVBoxLayout()
        self.book_name_input = QComboBox()
        self.load_book_names()
        self.delete_pdfs_btn = QPushButtonGui('DELETE PDFs As Shown')
        self.create_pdfs_btn = QPushButtonGui('CREATE PDFs As Shown')
        self.create_rel_pdfs_btn = QPushButtonGui('CREATE REL PDFs As Shown')
        self.export_json_btn = QPushButtonGui('EXPORT JSON to DB')
        self.add_item_folder = QPushButtonGui('ADD ITEM FOLDER As Shown')

        self.merge_pdfs_btn = QPushButtonGui('MERGE PDFs')
        self.open_merged_pdf_btn = QPushButtonGui('open MERGED')
        self.build_exam_test_by_gui_btn = QPushButtonGui('build TEST')
        self.open_naive_test_pdf_btn = QPushButtonGui('open TEST')
        self.rasterize_exam_test_pdf_btn = QPushButtonGui('raster TEST')
        self.open_rasterized_test_pdf_btn = QPushButtonGui('open TEST_R')
        self.build_duplex_paper_by_gui_btn = QPushButtonGui('build DX')
        self.open_naive_duplex_pdf_btn = QPushButtonGui('open DX')
        self.rasterize_duplex_pdf_btn = QPushButtonGui('raster DX')
        self.open_rasterized_duplex_pdf_btn = QPushButtonGui('open DX_R')
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)

        right_button_layout.addWidget(self.book_name_input)
        right_button_layout.addWidget(self.delete_pdfs_btn)
        right_button_layout.addWidget(self.create_pdfs_btn)
        right_button_layout.addWidget(self.create_rel_pdfs_btn)
        right_button_layout.addWidget(self.export_json_btn)
        right_button_layout.addWidget(self.add_item_folder)

        right_layout_hz_0 = QHBoxLayout()
        right_layout_hz_0.addWidget(self.merge_pdfs_btn)
        right_layout_hz_0.addWidget(self.open_merged_pdf_btn)
        right_button_layout.addLayout(right_layout_hz_0)


        right_layout_hz_1 = QHBoxLayout()
        right_layout_hz_1.addWidget(self.build_exam_test_by_gui_btn)
        right_layout_hz_1.addWidget(self.open_naive_test_pdf_btn)
        right_button_layout.addLayout(right_layout_hz_1)

        right_layout_hz_2 = QHBoxLayout()
        right_layout_hz_2.addWidget(self.rasterize_exam_test_pdf_btn)
        right_layout_hz_2.addWidget(self.open_rasterized_test_pdf_btn)
        right_button_layout.addLayout(right_layout_hz_2)

        right_layout_hz_3 = QHBoxLayout()
        right_layout_hz_3.addWidget(self.build_duplex_paper_by_gui_btn)
        right_layout_hz_3.addWidget(self.open_naive_duplex_pdf_btn)
        right_button_layout.addLayout(right_layout_hz_3)

        right_layout_hz_4 = QHBoxLayout()
        right_layout_hz_4.addWidget(self.rasterize_duplex_pdf_btn)
        right_layout_hz_4.addWidget(self.open_rasterized_duplex_pdf_btn)
        right_button_layout.addLayout(right_layout_hz_4)


        right_button_layout.addStretch()

        right_button_layout.addWidget(self.log_window)

        # Topic section - 3개 테이블로 분할
        topic_layout = QVBoxLayout()

        # Topic 테이블들을 담을 수평 레이아웃
        topic_tables_layout = QHBoxLayout()

        # 3개의 Topic 테이블 생성
        self.topic_tables = []
        self.quater_squares = []  # 정사각형들을 저장할 리스트 추가
        topic_labels = ['고체', '유체', '천체']
        quater_counts = [6, 7, 7]  # 각 그룹별 정사각형 개수
        quater_ranges = [(1, 6), (7, 13), (14, 20)]  # 각 그룹의 quater 범위

        for i in range(3):
            # 각 테이블별 수직 레이아웃
            table_layout = QVBoxLayout()

            # 레이블 추가
            label = QLabel(topic_labels[i])
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold; font-size: 20px;")
            table_layout.addWidget(label)

            # 정사각형들을 위한 수평 레이아웃 추가
            squares_layout = QHBoxLayout()
            squares_layout.setSpacing(2)  # 정사각형 간격

            # 해당 그룹의 정사각형들 생성
            group_squares = []
            start_quater, end_quater = quater_ranges[i]

            for quater in range(start_quater, end_quater + 1):
                square = QLabel()
                square.setFixedSize(20, 20)  # 20x20 픽셀 정사각형
                square.setStyleSheet("border: 1px solid black; background-color: white;")
                square.setAlignment(Qt.AlignCenter)
                square.setText(str(quater))
                square.setStyleSheet(
                    f"border: 1px solid black; background-color: white; font-size: 10px; font-weight: bold;")
                squares_layout.addWidget(square)
                group_squares.append(square)

            self.quater_squares.append(group_squares)
            table_layout.addLayout(squares_layout)

            # 테이블 생성
            topic_table = QTableWidget()
            topic_table.setColumnCount(3)
            topic_table.setFixedHeight(700)  # 정사각형 공간을 위해 높이 조정
            topic_table.setHorizontalHeaderLabels(['Code', 'Name', '번호'])

            # 컬럼 너비 설정
            topic_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            topic_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
            topic_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)

            topic_table.setColumnWidth(0, 33)  # Code
            topic_table.setColumnWidth(1, 110)  # Name
            topic_table.setColumnWidth(2, 25)  # 번호

            topic_table.setFixedWidth(170)

            # 행 번호 숨기기
            topic_table.horizontalHeader().setVisible(False)
            # 행 번호 숨기기
            topic_table.verticalHeader().setVisible(False)

            # 팔레트를 사용한 배경색 설정
            palette = topic_table.palette()
            palette.setColor(QPalette.Base, QColor("white"))
            topic_table.setPalette(palette)
            topic_table.setAlternatingRowColors(False)

            # 컬럼 너비 설정

            # 헤더 높이 조정
            topic_table.horizontalHeader().setFixedHeight(20)

            table_layout.addWidget(topic_table)
            self.topic_tables.append(topic_table)

            # Topic 테이블에 컨텍스트 메뉴 설정 (각 테이블마다)
            topic_table.setContextMenuPolicy(Qt.CustomContextMenu)
            topic_table.customContextMenuRequested.connect(self.show_topic_context_menu)

            # 테이블 레이아웃을 위젯으로 감싸기
            table_widget = QWidget()
            table_widget.setLayout(table_layout)
            topic_tables_layout.addWidget(table_widget)

        topic_layout.addLayout(topic_tables_layout)

        # Add layouts to main layout
        layout.addLayout(pool_layout)
        layout.addLayout(button_layout)
        layout.addLayout(list_layout)
        layout.addLayout(topic_layout)  # 새로 추가
        layout.addLayout(right_button_layout)

        # Set selection mode and event filters
        self.pool_table.setSelectionMode(QTableWidget.SingleSelection)
        self.pool_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pool_table.installEventFilter(self)

        self.list_table.setSelectionMode(QTableWidget.SingleSelection)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.installEventFilter(self)

        # Connect SIGNAL
        self.deselect_btn.clicked.connect(self.deselect_pool_items)
        self.sort_btn.clicked.connect(self.sort_pool_by_order)
        self.search_input.textChanged.connect(self.filter_pool_table)

        self.transfer_btn.clicked.connect(self.transfer_items)
        self.add_btn.clicked.connect(self.add_empty_row)
        self.remove_btn.clicked.connect(self.remove_selected_rows)
        self.up_btn.clicked.connect(self.move_row_up)
        self.down_btn.clicked.connect(self.move_row_down)

        self.list_deselect_btn.clicked.connect(self.deselect_list_items)
        self.list_renumber_btn.clicked.connect(self.renumber_list_items)

        self.filter_btn.clicked.connect(self.show_filter_dialog)

        self.book_name_input.currentIndexChanged.connect(self.load_selected_book)
        self.delete_pdfs_btn.clicked.connect(self.delete_pdfs_gui)
        self.create_pdfs_btn.clicked.connect(self.create_pdfs_gui)
        self.add_item_folder.clicked.connect(self.add_item_folder_gui)
        self.create_rel_pdfs_btn.clicked.connect(self.create_rel_pdfs_gui)
        self.merge_pdfs_btn.clicked.connect(self.merge_pdfs_gui)
        self.export_json_btn.clicked.connect(self.export_to_json)
        self.build_exam_test_by_gui_btn.clicked.connect(self.build_exam_test_by_gui)
        self.build_duplex_paper_by_gui_btn.clicked.connect(self.build_duplex_by_gui)
        self.rasterize_exam_test_pdf_btn.clicked.connect(self.rasterize_exam_test_pdf_by_gui)
        self.rasterize_duplex_pdf_btn.clicked.connect(self.rasterize_duplex_pdf_by_gui)
        self.open_merged_pdf_btn.clicked.connect(self.open_merged_pdf)
        self.open_naive_test_pdf_btn.clicked.connect(self.open_naive_test_pdf)
        self.open_rasterized_test_pdf_btn.clicked.connect(self.open_rasterized_test_pdf)
        self.open_naive_duplex_pdf_btn.clicked.connect(self.open_naive_duplex_pdf)
        self.open_rasterized_duplex_pdf_btn.clicked.connect(self.open_rasterized_duplex_pdf)

        # 셀 클릭 이벤트 연결
        self.list_table.cellClicked.connect(self.handle_cell_click)

        # 우측 버튼 레이아웃에 태그 관리 UI 추가
        self.tag_management_frame = QWidget()
        self.tag_management_frame.setVisible(False)  # 초기에는 숨김
        self.tag_management_frame.setFixedWidth(240)
        tag_management_layout = QVBoxLayout(self.tag_management_frame)

        # 태그 관리 영역 제목
        tag_title_label = QLabel("태그 관리")
        tag_title_label.setAlignment(Qt.AlignCenter)
        tag_management_layout.addWidget(tag_title_label)

        # 태그 입력 영역
        tag_input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("새 태그 입력 후 Enter")
        self.tag_input.returnPressed.connect(self.add_tag)
        self.tag_add_btn = QPushButton("+")
        self.tag_add_btn.setMaximumWidth(30)
        self.tag_add_btn.clicked.connect(self.add_tag)
        tag_input_layout.addWidget(self.tag_input)
        tag_input_layout.addWidget(self.tag_add_btn)
        tag_management_layout.addLayout(tag_input_layout)

        # 태그 목록 영역
        self.tag_list = QListWidget()
        self.tag_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.tag_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tag_list.model().rowsMoved.connect(self.on_tags_reordered)
        self.tag_list.installEventFilter(self)
        tag_management_layout.addWidget(self.tag_list)

        # 태그 버튼 영역
        tag_button_layout = QHBoxLayout()
        self.tag_remove_btn = QPushButton("삭제")
        self.tag_remove_btn.clicked.connect(self.remove_selected_tag)
        self.tag_save_btn = QPushButton("저장")
        self.tag_save_btn.clicked.connect(self.save_tags)
        self.tag_cancel_btn = QPushButton("취소")
        self.tag_cancel_btn.clicked.connect(self.cancel_tag_edit)
        tag_button_layout.addWidget(self.tag_remove_btn)
        tag_button_layout.addWidget(self.tag_save_btn)
        tag_button_layout.addWidget(self.tag_cancel_btn)
        tag_management_layout.addLayout(tag_button_layout)

        # 태그 관리 프레임을 우측 레이아웃에 추가
        right_button_layout.addWidget(self.tag_management_frame)

        self.tag_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tag_list.customContextMenuRequested.connect(self.show_tag_context_menu)

        # 현재 편집 중인 셀 위치 저장 변수
        self.current_edit_row = -1
        self.current_edit_col = -1

    def log_message(self, message):
        self.log_window.append(message)

    def show_warning_dialog(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        return msg_box.exec_() == QMessageBox.Ok

    def check_and_remove_empty_rows(self):
        for row in range(self.list_table.rowCount() - 1, -1, -1):
            is_empty = True
            for col in range(self.list_table.columnCount()):
                item = self.list_table.item(row, col)
                if item and item.text().strip():  # 내용이 있으면
                    is_empty = False
                    break
            if is_empty:
                self.list_table.removeRow(row)

    def remove_selected_rows(self):
        # 태그 관리 프레임이 열려있다면 닫기
        if self.tag_management_frame.isVisible():
            self.save_tags()
        if not self.show_warning_dialog("Are you sure you want to remove these rows?"):
            return
        selected_rows = sorted(set(item.row() for item in self.list_table.selectedItems()), reverse=True)
        for row in selected_rows:
            self.list_table.removeRow(row)

    def eventFilter(self, obj, event):
        # 각 위젯별 이벤트 처리
        if event.type() == event.KeyPress:
            key = event.key()

            # 태그 리스트에서의 키 처리
            if obj == self.tag_list:
                if key == Qt.Key_Delete:
                    # 태그 리스트에서 DELETE 키는 선택된 태그 삭제
                    self.remove_selected_tag()
                    return True
                elif key == Qt.Key_Escape:
                    # 태그 리스트에서 ESC 키는 태그 저장
                    self.save_tags()
                    return True

            # 테이블에서의 키 처리
            elif obj in [self.pool_table, self.list_table]:
                if key == Qt.Key_Shift:
                    # SHIFT 키는 다중 선택 모드로 변경
                    obj.setSelectionMode(QTableWidget.MultiSelection)
                    obj.setSelectionBehavior(QTableWidget.SelectRows)
                elif key == Qt.Key_Escape:
                    # ESC 키 처리
                    if self.tag_management_frame.isVisible():
                        # 태그 에디터가 보이는 상태에서는 태그 저장
                        self.save_tags()
                    elif self.pool_table.hasFocus():
                        # POOL 테이블에서는 선택 해제
                        self.deselect_pool_items()
                    elif self.list_table.hasFocus():
                        # LIST 테이블에서는 선택 해제
                        self.deselect_list_items()
                elif key == Qt.Key_Delete or key == Qt.Key_Backspace:
                    # DELETE 또는 BACKSPACE 키는 LIST 테이블에서 선택된 행 삭제
                    if self.list_table.hasFocus():
                        self.remove_selected_rows()

        # SHIFT 키 해제 처리
        elif event.type() == event.KeyRelease and event.key() == Qt.Key_Shift:
            if obj in [self.pool_table, self.list_table]:
                obj.setSelectionMode(QTableWidget.NoSelection)

        return super().eventFilter(obj, event)

    def parse_code(self, code: str) -> dict:
        parsed_code = {
            "subject": code[0:2],
            "topic": code[2:5],
            "section": code[5:7],
            "number": code[7:13]
        }
        return parsed_code

    def sort_list(self, column):
        if column in self.list_sort_order:
            self.list_sort_order[column] = not self.list_sort_order[column]
        else:
            self.list_sort_order[column] = True

        data = []
        for row in range(self.list_table.rowCount()):
            row_data = []
            for col in range(self.list_table.columnCount()):
                item = self.list_table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        reverse = not self.list_sort_order[column]
        if column == 1 or column == 2:  # Item Num column
            data.sort(key=lambda x: float('inf') if not x[column] else int(x[column]), reverse=reverse)
        else:
            data.sort(key=lambda x: x[column], reverse=reverse)

        for i, row_data in enumerate(data):
            for j, cell_data in enumerate(row_data):
                self.list_table.setItem(i, j, QTableWidgetItem(cell_data))

    def sort_list_by_number_in_ascending_order(self):
        data = []
        for row in range(self.list_table.rowCount()):
            row_data = []
            for col in range(self.list_table.columnCount()):
                item = self.list_table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        data.sort(key=lambda x: int(x[1]) if x[1].isdigit() else float('inf'))

        for i, row_data in enumerate(data):
            for j, cell_data in enumerate(row_data):
                self.list_table.setItem(i, j, QTableWidgetItem(cell_data))

    def get_list_used_items(self):
        # HISTORY_DB_PATH 내의 모든 JSON 파일 가져오기
        all_files = [f for f in os.listdir(HISTORY_DB_PATH) if f.endswith('.json')]
        print(f"All JSON files: {all_files}")
    
        # EX_로 시작하는 파일들을 가나다순으로 정렬
        ex_files = sorted([f for f in all_files if f.startswith('EX_')])
        print(f"EX_ files: {ex_files}")
    
        list_used_items = dict()
    
        # EX_ 파일들에서 검색
        for ex_file in ex_files:
            file_path = os.path.join(HISTORY_DB_PATH, ex_file)
            print(f"Checking file: {ex_file}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"File loaded successfully, {len(data)} items")
    
            # 리스트 형태의 JSON에서 list_rel_item_code 내의 item_code 검색
            for i, item in enumerate(data):
                list_rel_item_code = item.get('list_rel_item_code', [])
    
                if isinstance(list_rel_item_code, list):
                    for index, rel_item_code in enumerate(list_rel_item_code):
                        output = item.get('number')
                        order = chr(index + 65)
                        file_identifier = ex_file.split('_')[1].replace('회.json', '')
                        result = f'{int(file_identifier)}회 {output}{order}번'
                        rel_item = {rel_item_code: result}
                        list_used_items.update(rel_item)
        return list_used_items

    def loadData(self):
        self.pool_data = []
        self.list_sort_order = {}
        serial_num = 1

        # Helper function to check if item is valid
        def is_valid_item(folder_path, subfolder, original_pdf=True):
            # hwp file / pdf file 둘 중 하나라도 있으면 존재하는 것으로 산정.
            if not os.path.isdir(os.path.join(folder_path, subfolder)):
                return False

            hwp_path = os.path.join(folder_path, subfolder, f"{subfolder}.hwp")
            if original_pdf == True:
                pdf_path = os.path.join(folder_path, subfolder, f"{subfolder}_original.pdf")
            else:
                pdf_path = os.path.join(folder_path, subfolder, f"{subfolder}.pdf")

            return os.path.exists(hwp_path) or os.path.exists(pdf_path)
        for base_path in [KICE_DB_PATH, NICE_DB_PATH, ITEM_DB_PATH]:
            # Load from KICE_DB_PATH
            for folder in os.listdir(base_path):
                folder_path = os.path.join(base_path, folder)
                if os.path.isdir(folder_path):
                    for subfolder in os.listdir(folder_path):
                        if len(subfolder) == 13 and is_valid_item(folder_path, subfolder, original_pdf=True):
                            parsed = self.parse_code(subfolder)
                            order = parsed["topic"] + parsed["section"] + parsed["number"] + parsed["subject"]
                            if self.list_used_items.get(subfolder):
                                reference = self.list_used_items.get(subfolder)
                            else:
                                reference = ""
                            self.pool_data.append({
                                'item_code': subfolder,
                                'topic': parsed["topic"],
                                'order': order,
                                'reference': reference
                            })
                            serial_num += 1

        self.original_pool_data = self.pool_data.copy()

        self.update_pool_table()
        
    def update_pool_table(self, data=None):
        if data is None:
            data = self.pool_data
        self.pool_table.setRowCount(len(data))
        for i, item in enumerate(data):
            item_code = item['item_code']
            item_code_item = QTableWidgetItem(item_code)

            # reference 키를 안전하게 가져오기
            reference = item.get('reference', '')  # 키가 없으면 빈 문자열

            if parse_code(item_code)["section"] == "KC" and item_code not in self.kice_topics:
                item_code_item.setBackground(QColor('pink'))
            if parse_code(item_code)["section"] == "KC" and item_code in self.kice_topics:
                if reference:  # item['reference'] 대신 reference 사용
                    item_code_item.setBackground(QColor('green'))
                else:
                    item_code_item.setBackground(QColor('lightgreen'))
            if parse_code(item_code)["section"] == "NC":
                if reference:  # item['reference'] 대신 reference 사용
                    item_code_item.setBackground(QColor('yellow'))
                else:
                    item_code_item.setBackground(QColor('lightyellow'))
            if parse_code(item_code)["section"] != "KC" and parse_code(item_code)["section"] != "NC":
                if reference:  # item['reference'] 대신 reference 사용
                    item_code_item.setBackground(QColor('blue'))
                else:
                    item_code_item.setBackground(QColor('lightblue'))

            self.pool_table.setItem(i, 0, item_code_item)
            self.pool_table.setItem(i, 1, QTableWidgetItem(item['topic']))
            self.pool_table.setItem(i, 2, QTableWidgetItem(str(item['order'])))
            self.pool_table.setItem(i, 3, QTableWidgetItem(reference))  # 안전하게 사용

    def load_kice_topics(self):
        with open(RESOURCES_PATH + '/KICEtopic.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        self.kice_topics = set(data.values())

    def filter_pool_table(self, text):
        filtered_data = [item for item in self.pool_data if text.lower() in item['item_code'].lower()]
        self.update_pool_table(filtered_data)

    def transfer_items(self):
        selected_rows = sorted(set(item.row() for item in self.pool_table.selectedItems()))

        for row in selected_rows:
            item_code = self.pool_table.item(row, 0).text()
            order = self.pool_table.item(row, 2).text()
            parsed = self.parse_code(item_code)

            exists = False
            for i in range(self.list_table.rowCount()):
                if self.list_table.item(i, 0) and self.list_table.item(i, 0).text() == item_code:
                    exists = True
                    break

            if not exists:
                current_row = self.list_table.rowCount()
                self.list_table.insertRow(current_row)

                self.list_table.setItem(current_row, 0, QTableWidgetItem(item_code))
                self.list_table.setItem(current_row, 1, QTableWidgetItem(str(current_row + 1)))
                self.list_table.setItem(current_row, 2, QTableWidgetItem(str(2)))
                self.list_table.setItem(current_row, 3, QTableWidgetItem("1L"))

                # 태그 컬럼에 빈 JSON 배열 설정
                self.list_table.setItem(current_row, 4, QTableWidgetItem("[]"))
                self.list_table.setItem(current_row, 5, QTableWidgetItem("[]"))

    def add_empty_row(self):
        current_row = self.list_table.rowCount()
        self.list_table.insertRow(current_row)

        self.list_table.setItem(current_row, 0, QTableWidgetItem(""))
        self.list_table.setItem(current_row, 1, QTableWidgetItem(str(current_row + 1)))
        self.list_table.setItem(current_row, 2, QTableWidgetItem(str(2)))
        self.list_table.setItem(current_row, 3, QTableWidgetItem("1L"))

        # 태그 컬럼에 빈 JSON 배열 설정
        self.list_table.setItem(current_row, 4, QTableWidgetItem("[]"))
        self.list_table.setItem(current_row, 5, QTableWidgetItem("[]"))

    def sort_pool_by_order(self):
        # Get currently displayed items
        current_items = []
        for row in range(self.pool_table.rowCount()):
            item_code = self.pool_table.item(row, 0).text()
            topic = self.pool_table.item(row, 1).text()
            order = self.pool_table.item(row, 2).text()
            reference = self.pool_table.item(row, 3).text()
            current_items.append({'item_code': item_code, 'topic': topic, 'order': order, 'reference': reference})

        # Sort current items
        current_items.sort(key=lambda x: x['order'])
        self.update_pool_table(current_items)

    def deselect_pool_items(self):
        self.pool_table.clearSelection()

    # LIST와 관련된 기능들
    def deselect_list_items(self):
        self.list_table.clearSelection()

    def move_row_up(self):
        # 태그 관리 프레임이 열려있다면 닫기
        if self.tag_management_frame.isVisible():
            self.save_tags()
        selected_rows = sorted(set(item.row() for item in self.list_table.selectedItems()))
        if not selected_rows or selected_rows[0] <= 0:
            return

        # Move each selected row up one position
        for row in selected_rows:
            if row > 0:  # Can't move up if already at top
                # Save current row and row above data
                current_row_data = []
                above_row_data = []

                for col in range(self.list_table.columnCount()):
                    current_item = self.list_table.item(row, col)
                    above_item = self.list_table.item(row - 1, col)
                    current_row_data.append(current_item.text() if current_item else "")
                    above_row_data.append(above_item.text() if above_item else "")

                # Swap the rows
                for col in range(self.list_table.columnCount()):
                    self.list_table.setItem(row - 1, col, QTableWidgetItem(current_row_data[col]))
                    self.list_table.setItem(row, col, QTableWidgetItem(above_row_data[col]))

                # Update selection to follow moved row
                self.list_table.selectRow(row - 1)

        self.check_and_remove_empty_rows()

    def move_row_down(self):
        # 태그 관리 프레임이 열려있다면 닫기
        if self.tag_management_frame.isVisible():
            self.save_tags()
        selected_rows = sorted(set(item.row() for item in self.list_table.selectedItems()), reverse=True)
        if not selected_rows or selected_rows[-1] >= self.list_table.rowCount() - 1:
            return

        # Move each selected row down one position
        for row in selected_rows:
            if row < self.list_table.rowCount() - 1:  # Can't move down if already at bottom
                # Save current row and row below data
                current_row_data = []
                below_row_data = []

                for col in range(self.list_table.columnCount()):
                    current_item = self.list_table.item(row, col)
                    below_item = self.list_table.item(row + 1, col)
                    current_row_data.append(current_item.text() if current_item else "")
                    below_row_data.append(below_item.text() if below_item else "")

                # Swap the rows
                for col in range(self.list_table.columnCount()):
                    self.list_table.setItem(row + 1, col, QTableWidgetItem(current_row_data[col]))
                    self.list_table.setItem(row, col, QTableWidgetItem(below_row_data[col]))

                # Update selection to follow moved row
                self.list_table.selectRow(row + 1)

        self.check_and_remove_empty_rows()

    def show_filter_dialog(self):
        dialog = FilterDialog(self)
        dialog.exec_()

    def renumber_list_items(self):
        if not self.show_warning_dialog("Are you sure you want to renumber the list items?"):
            return
        next_item_number = 1
        for i in range(self.list_table.rowCount()):
            if self.list_table.item(i, 0).text():
                # 비어있지 않은 경우에만 번호 매기기
                self.list_table.setItem(i, 1, QTableWidgetItem(str(next_item_number)))
                next_item_number += 1

    def delete_pdfs_gui(self):
        if not self.show_warning_dialog("Are you sure you want to DELETE PDFs?"):
            return

        if not self.show_warning_dialog("Are you REALLY sure you want to DELETE PDFs?"):
            return

        if not self.show_warning_dialog("ARE YOU REALLY SURE YOU WANT TO DELETE PDFs?"):
            return

        for row in range(self.list_table.rowCount()):
            item_code = self.list_table.item(row, 0).text() if self.list_table.item(row, 0) else None
            if item_code:
                pdf_path = code2pdf(item_code)
                Main_path = code2Main(item_code)
                if pdf_path:
                    try:
                        os.remove(pdf_path) if os.path.exists(pdf_path) else None
                        self.log_message(f"Deleted PDF: {pdf_path}")
                    except Exception as e:
                        self.log_message(f"Error deleting PDF: {e}")
                if Main_path:
                    try:
                        os.remove(Main_path) if os.path.exists(Main_path) else None
                        self.log_message(f"Deleted PDF: {Main_path}")
                    except Exception as e:
                        self.log_message(f"Error deleting PDF: {e}")

    def refresh_folder(self, folder_path):
        """Windows API를 사용하여 폴더를 새로고침합니다."""
        try:
            import ctypes
            from ctypes import wintypes

            # SHChangeNotify 함수를 사용하여 폴더 새로고침
            SHCNE_UPDATEDIR = 0x00001000
            SHCNF_PATH = 0x0001

            shell32 = ctypes.WinDLL('shell32')
            shell32.SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_PATH, folder_path, None)
            print(f"폴더 새로고침 완료: {folder_path}")
            return True
        except Exception as e:
            print(f"폴더 새로고침 실패: {e}")
            return False

    def create_pdfs_gui(self):
        if not self.show_warning_dialog("Are you sure you want to create PDFs?"):
            return
        item_list = []
        item_folder_list = []
        for row in range(self.list_table.rowCount()):
            item_code = self.list_table.item(row, 0).text() if self.list_table.item(row, 0) else None
            item_list.append(item_code)
            item_folder = code2folder(item_code)
            item_folder_list.append(item_folder)
        self.log_message("Starting PDF creation...")

        for item_folder in item_folder_list:
            if os.path.exists(item_folder):
                self.refresh_folder(item_folder)

        time.sleep(3)

        self.pdf_thread = PDFCreationThread(item_list)
        self.pdf_thread.progress_signal.connect(self.log_message)
        self.pdf_thread.start()

    def create_rel_pdfs_gui(self):
        if not self.show_warning_dialog("Are you sure you want to create REL PDFs?"):
            return
        item_list = []
        item_folder_list = []

        for row in range(self.list_table.rowCount()):
            item_code = self.list_table.item(row, 4).text() if self.list_table.item(row, 4) else None
            if not item_code:
                continue  # Skip if item_code is None or empty

            # JSON 파싱 시도
            try:
                item_codes = json.loads(item_code) if item_code.startswith("[") and item_code.endswith("]") else [
                    item_code]
            except json.JSONDecodeError:
                print(f"Invalid JSON format in item_code: {item_code}")
                continue

            for item in item_codes:
                item_list.append(item)
                item_folder = code2folder(item)
                item_folder_list.append(item_folder)

        self.log_message("Starting PDF creation...")

        for item_folder in item_folder_list:
            if os.path.exists(item_folder):
                self.refresh_folder(item_folder)

        time.sleep(3)

        self.pdf_thread = PDFCreationThread(item_list)
        self.pdf_thread.progress_signal.connect(self.log_message)
        self.pdf_thread.start()

    def add_item_folder_gui(self):
        if not self.show_warning_dialog("Are you sure you want to create Item Folders?"):
            return
        item_list = []
        for row in range(self.list_table.rowCount()):
            item_code = self.list_table.item(row, 0).text() if self.list_table.item(row, 0) else None
            item_list.append(item_code)
        self.log_message("Starting Creating Item Folder...")

        template_folder = RESOURCES_PATH + r"\item_template"

        for item_code in item_list:
            item_folder = code2folder(item_code)
            if not os.path.exists(item_folder):
                shutil.copytree(template_folder, item_folder)
                for root, dirs, files in os.walk(item_folder):
                    for file in files:
                        if 'item_template' in file:
                            old_file_path = os.path.join(root, file)
                            new_file_path = os.path.join(root, file.replace('item_template', item_code))
                            os.rename(old_file_path, new_file_path)
                    for dir in dirs:
                        if 'item_template' in dir:
                            old_dir_path = os.path.join(root, dir)
                            new_dir_path = os.path.join(root, dir.replace('item_template', item_code))
                            os.rename(old_dir_path, new_dir_path)

                self.log_message(f"Created item folder for {item_code}")
            else:
                self.log_message(f"Item folder for {item_code} already exists")
    def merge_pdfs_gui(self):
        if not self.show_warning_dialog("Are you sure you want to merge PDFs?"):
            return
        book_name = self.book_name_input.currentText()
        self.log_message("Starting PDF merge...")
        try:
            pdf_list = []
            for row in range(self.list_table.rowCount()):
                if self.list_table.item(row, 1):
                    item_code = self.list_table.item(row, 0).text()
                    pdf_path = code2pdf(item_code)
                    item_num = self.list_table.item(row, 1).text()
                    pdf_list.append((item_num, item_code, pdf_path))
                else:
                    pass
            def custom_sort_key(item):
                try:
                    # Try to convert the item to an integer
                    return (0, int(item[0]))
                except ValueError:
                    # If it fails, return a tuple that ensures non-numeric values are sorted after numeric values
                    return (1, item[0])

            pdf_list.sort(key=custom_sort_key)

            doc = fitz.open()
            for pdf in pdf_list:
                doc.insert_pdf(fitz.open(pdf[2]))
                cur_page = doc.page_count - 1

                to = AreaOverlayObject(cur_page, Coord(0, 0, 0), Coord(Ratio.mm_to_px(297), Ratio.mm_to_px(420), 0))

                tonum = TextOverlayObject(cur_page, Coord(Ratio.mm_to_px(170), Ratio.mm_to_px(20), 0),
                                                    "Pretendard-Bold.ttf", 30, f"{pdf[0]}", (1, 0, 0, 0),
                                                    fitz.TEXT_ALIGN_RIGHT)
                tocode = TextOverlayObject(cur_page, Coord(Ratio.mm_to_px(260), Ratio.mm_to_px(20), 0),
                                                    "Pretendard-Bold.ttf", 20, f"{pdf[1]}", (0, 0, 0, 1),
                                                    fitz.TEXT_ALIGN_RIGHT)
                to.add_child(tonum)
                to.add_child(tocode)

                overlayer = Overlayer(doc)
                to.overlay(overlayer, Coord(0, 0, 0))

            doc.save(os.path.join(OUTPUT_PATH, f"Merged_{book_name.replace('.json', '.pdf')}"))
            self.log_message("PDFs merged successfully.")
            doc.close()

        except Exception as e:
            error_message = f"Error during PDF merge: {e}\n{traceback.format_exc()}"
            self.log_message(error_message)

    def load_book_names(self):
        self.book_name_input.clear()
        book_names = [file_name for file_name in os.listdir(EXAM_DB_PATH) if file_name.endswith('.json')]
        book_names.sort()  # Sort book names in ascending order
        self.book_name_input.addItems(book_names)

    def load_selected_book(self):
        book_name = self.book_name_input.currentText()
        book_path = os.path.join(EXAM_DB_PATH, book_name)

        # 기존 내용 초기화
        self.list_table.setRowCount(0)

        # JSON 파일 읽기
        try:
            with open(book_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # JSON 데이터를 테이블에 로드
            for row_data in data:
                row_count = self.list_table.rowCount()
                self.list_table.insertRow(row_count)

                # 각 컬럼에 대해 None이 아닐 때만 QTableWidgetItem을 설정
                if row_data.get('item_code') is not None:
                    item_code = row_data['item_code']
                    self.list_table.setItem(row_count, 0, QTableWidgetItem(str(item_code)))

                if row_data.get('number') is not None:
                    self.list_table.setItem(row_count, 1, QTableWidgetItem(str(row_data['number'])))

                if row_data.get('score') is not None:
                    self.list_table.setItem(row_count, 2, QTableWidgetItem(str(row_data['score'])))

                if row_data.get('para') is not None:
                    self.list_table.setItem(row_count, 3, QTableWidgetItem(str(row_data['para'])))

                # Parse 'list_rel_item_code' as a list
                if row_data.get('list_rel_item_code') is not None:
                    self.list_table.setItem(row_count, 4, QTableWidgetItem(json.dumps(row_data['list_rel_item_code'])))

                # Parse 'list_theory_piece_code' as a list
                if row_data.get('list_theory_piece_code') is not None:
                    self.list_table.setItem(row_count, 5, QTableWidgetItem(json.dumps(row_data['list_theory_piece_code'])))

        except Exception as e:
            self.log_message(f"Error loading book: {e}")

    def export_to_json(self):
        if not self.show_warning_dialog("Are you sure you want to export to JSON?"):
            return

        book_name = self.book_name_input.currentText()
        output_path = os.path.join(EXAM_DB_PATH, book_name)

        data = []

        # JSON에서 원하는 키 순서
        json_keys = ['item_code', 'number', 'score', 'para', 'list_rel_item_code', 'list_theory_piece_code']

        for row in range(self.list_table.rowCount()):
            temp_data = {}
            # 각 열의 데이터를 추출하여 딕셔너리에 추가
            temp_data['item_code'] = self.list_table.item(row, 0).text() if self.list_table.item(row, 0) else None
            temp_data['number'] = int(self.list_table.item(row, 1).text()) if self.list_table.item(row, 1) else None
            temp_data['score'] = int(self.list_table.item(row, 2).text()) if self.list_table.item(row, 2) else None
            temp_data['para'] = self.list_table.item(row, 3).text() if self.list_table.item(row, 3) else None
            # Parse 'list_rel_item_code' as a list
            #TODO: 작은 따옴표와 큰 따옴표를 구분하는 issue
            if self.list_table.item(row, 4) and self.list_table.item(row, 4).text():
                try:
                    temp_data['list_rel_item_code'] = json.loads(self.list_table.item(row, 4).text())
                except json.JSONDecodeError:
                    temp_data['list_rel_item_code'] = []  # Default to an empty list if parsing fails
            else:
                temp_data['list_rel_item_code'] = []

            # Parse 'list_theory_piece_code' as a list
            if self.list_table.item(row, 5) and self.list_table.item(row, 5).text():
                try:
                    temp_data['list_theory_piece_code'] = json.loads(self.list_table.item(row, 5).text())
                except json.JSONDecodeError:
                    temp_data['list_theory_piece_code'] = []  # Default to an empty list if parsing fails
            else:
                temp_data['list_theory_piece_code'] = []
            # 딕셔너리를 리스트에 추가
            data.append(temp_data)

        # JSON 파일로 저장
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log_message(f"Exported to JSON successfully: {output_path}")
        except Exception as e:
            self.log_message(f"Error exporting to JSON: {e}")

    def build_exam_test_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to build the EXAM TEST?"):
            return
        if not self.show_warning_dialog("Please Ensure that Every PDF file is Updated"):
            return

        book_name = self.book_name_input.currentText()

        # Validate book_name
        if not book_name.endswith('.json'):
            self.log_message(f"Invalid book name: {book_name}")
            return

        input_path = os.path.join(EXAM_DB_PATH, book_name)
        output_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '_TEST.pdf'))

        self.log_message("Starting exam test build...")
        try:
            build_exam_test(input=input_path, output=output_path, log_callback=self.log_message)
        except Exception as e:
            error_message = f"Error during exam test build: {e}\n{traceback.format_exc()}"
            self.log_message(error_message)

    def build_duplex_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to build the DUPLEX paper?"):
            return
        if not self.show_warning_dialog("Please Ensure that Every PDF file is Updated"):
            return
        book_name = self.book_name_input.currentText()
        input_path = os.path.join(EXAM_DB_PATH, book_name)
        output_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '_DX.pdf'))
        self.log_message("Starting DUPLEX paper build...")
        try:
            build_duplex(input=input_path, output=output_path, log_callback=self.log_message)
        except Exception as e:
            error_message = f"Error during DUPLEX paper build: {e}\n{traceback.format_exc()}"
            self.log_message(error_message)

    def rasterize_exam_test_pdf_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to rasterize the PDF?"):
            return
        book_name = self.book_name_input.currentText()
        self.log_message("Starting PDF rasterization...")
        try:
            add_watermark_and_rasterize(os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_TEST.pdf'),
                                        os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_TEST_R.pdf'))
            print(f"Rasterized PDF saved to: {os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_TEST_R.pdf')}")
            self.log_message("TEST PDF rasterization completed successfully.")
        except Exception as e:
            self.log_message(f"Error during PDF rasterization: {e}")

    def rasterize_duplex_pdf_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to rasterize the PDF?"):
            return
        book_name = self.book_name_input.currentText()
        self.log_message("Starting PDF rasterization...")
        try:
            add_watermark_and_rasterize(os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_DX.pdf'),
                                        os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_DX_R.pdf'))
            self.log_message("DX PDF rasterization completed successfully.")
        except Exception as e:
            self.log_message(f"Error during PDF rasterization: {e}")

    def open_merged_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, f"Merged_{book_name.replace('.json', '.pdf')}")
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                self.log_message(f"Opened merged PDF: {pdf_path}")
            except Exception as e:
                self.log_message(f"Error opening merged PDF: {e}")
        else:
            self.log_message(f"Merged PDF not found: {pdf_path}")
    def open_naive_test_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '_TEST.pdf'))
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                self.log_message(f"Opened PDF: {pdf_path}")
            except Exception as e:
                self.log_message(f"Error opening PDF: {e}")
        else:
            self.log_message(f"PDF not found: {pdf_path}")

    def open_naive_duplex_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '_DX.pdf'))
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                self.log_message(f"Opened PDF: {pdf_path}")
            except Exception as e:
                self.log_message(f"Error opening PDF: {e}")
        else:
            self.log_message(f"PDF not found: {pdf_path}")

    def open_rasterized_test_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_TEST_R.pdf')
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                self.log_message(f"Opened rasterized PDF: {pdf_path}")
            except Exception as e:
                self.log_message(f"Error opening rasterized PDF: {e}")
        else:
            self.log_message(f"Rasterized PDF not found: {pdf_path}")

    def open_rasterized_duplex_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_DX_R.pdf')
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                self.log_message(f"Opened rasterized PDF: {pdf_path}")
            except Exception as e:
                self.log_message(f"Error opening rasterized PDF: {e}")
        else:
            self.log_message(f"Rasterized PDF not found: {pdf_path}")

    def add_context_menu(self):
        self.pool_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pool_table.customContextMenuRequested.connect(self.show_context_menu)

        self.list_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_table.customContextMenuRequested.connect(self.show_context_menu)

    # DatabaseManager 클래스에 추가할 메서드들

    def show_context_menu(self, pos):
        """가장 간단한 컨텍스트 메뉴 - QAction 데이터 사용"""
        try:
            sender = self.sender()
            if not sender:
                return

            row = sender.rowAt(pos.y())
            col = sender.columnAt(pos.x())

            if row < 0 or col < 0:
                return

            item_code = ""
            if sender.item(row, 0) and sender.item(row, 0).text():
                item_code = sender.item(row, 0).text()

            menu = QMenu(self)

            # POOL 또는 LIST 테이블의 col = 0, 1, 2 열
            if sender in [self.pool_table, self.list_table] and col in [0, 1, 2]:
                if item_code:
                    action1 = menu.addAction("Open item HWP")
                    action1.setData({'type': 'hwp', 'code': item_code})
                    action1.triggered.connect(self.handle_context_action)

                    action2 = menu.addAction("Open Folder")
                    action2.setData({'type': 'folder', 'code': item_code})
                    action2.triggered.connect(self.handle_context_action)

                    action3 = menu.addAction("Refractor Item Code")
                    action3.setData({'type': 'refactor', 'code': item_code})
                    action3.triggered.connect(self.handle_context_action)

                    menu.addSeparator()

                # Swap to xx 옵션
                for i in range(1, 21):
                    action = menu.addAction(f"Swap to {i:02d}")
                    action.setData({'type': 'swap', 'row': row, 'number': i, 'sender': sender})
                    action.triggered.connect(self.handle_context_action)

            # LIST 테이블의 col = 3 열
            elif sender == self.list_table and col == 3:
                move_options = ["1L", "1R", "2L", "2R", "3L", "3R", "4L", "4R"]

                for option in move_options:
                    action = menu.addAction(f"Move to {option}")
                    action.setData({'type': 'para', 'row': row, 'para': option})
                    action.triggered.connect(self.handle_context_action)

            if not menu.isEmpty():
                menu.exec_(sender.mapToGlobal(pos))

        except Exception as e:
            self.log_message(f"Context menu error: {str(e)}")

    def handle_context_action(self):
        """컨텍스트 메뉴 액션 처리"""
        try:
            action = self.sender()
            if not action or not action.data():
                return

            data = action.data()
            action_type = data.get('type')

            if action_type == 'hwp':
                self.open_item_hwp(data['code'])
            elif action_type == 'folder':
                self.open_item_folder(data['code'])
            elif action_type == 'refactor':
                self.refractor_item_code_by_gui(data['code'])
            elif action_type == 'swap':
                self.safe_swap_item_number(data['row'], data['number'], data['sender'])
            elif action_type == 'para':
                self.safe_change_item_para(data['row'], data['para'])

        except Exception as e:
            self.log_message(f"Context action error: {str(e)}")

    def safe_swap_item_number(self, row, dst_number, sender=None):
        """안전한 번호 변경"""
        try:
            if sender is None:
                sender = self.list_table
            self.swap_item_number(row, dst_number, sender)
        except Exception as e:
            self.log_message(f"Swap error: {str(e)}")

    def safe_change_item_para(self, row, new_para):
        """안전한 para 변경"""
        try:
            if row < 0 or row >= self.list_table.rowCount():
                self.log_message(f"Invalid row: {row}")
                return

            self.list_table.setItem(row, 3, QTableWidgetItem(str(new_para)))
            self.log_message(f"Changed row {row} para to {new_para}")

        except Exception as e:
            self.log_message(f"Para change error: {str(e)}")

    def safe_swap_item_number(self, row, new_number, sender):
        """swap_item_number의 안전한 래퍼 함수"""
        try:
            if sender == self.pool_table:
                # POOL 테이블에서의 스왑
                self.swap_item_number(row, new_number, sender)
            else:
                self.swap_item_number(row, new_number, sender)
        except Exception as e:
            self.log_message(f"Error during swap: {str(e)}")

    def safe_change_item_para(self, row, new_para):
        """change_item_para의 안전한 래퍼 함수"""
        try:
            self.change_item_para(row, new_para)
        except Exception as e:
            self.log_message(f"Error during para change: {str(e)}")

    def open_item_hwp(self, item_code):
        # Construct and normalize path
        hwp_path = code2hwp(item_code)
        if os.path.exists(hwp_path):
            try:
                os.startfile(hwp_path)
            except Exception as e:
                print(f"Error: {e}")

    def open_item_folder(self, item_code):
        folder_path = code2folder(item_code)
        if os.path.exists(folder_path):
            if os.name == 'nt':
                try:
                    subprocess.run(['explorer', folder_path], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")

    def refractor_item_code(self, item_code, new_code):
        # TODO: 기존 json file의 item_code까지 변경
        # 원본 코드의 정보 파싱
        if item_code[5:7] == 'KC':
            old_base_path = KICE_DB_PATH
        elif item_code[5:7] == 'NC':
            old_base_path = NICE_DB_PATH
        else:
            old_base_path = ITEM_DB_PATH
        topic = item_code[2:5]
        old_topic = item_code[2:5]
        old_topic_path = os.path.join(old_base_path, old_topic)
        old_item_path = os.path.join(old_topic_path, item_code)

        # 새 코드의 정보 파싱
        if item_code[5:7] == 'KC':
            new_base_path = KICE_DB_PATH
        elif item_code[5:7] == 'NC':
            new_base_path = NICE_DB_PATH
        else:
            new_base_path = ITEM_DB_PATH
        new_topic = new_code[2:5]
        new_topic_path = os.path.join(new_base_path, new_topic)
        new_item_path = os.path.join(new_topic_path, new_code)

        try:
            # 기본 검증
            if not os.path.exists(old_item_path):
                raise FileNotFoundError(f"원본 폴더를 찾을 수 없습니다: {old_item_path}")
            if os.path.exists(new_item_path):
                raise FileExistsError(f"대상 폴더가 이미 존재합니다: {new_item_path}")
            if not os.access(os.path.dirname(old_item_path), os.W_OK):
                raise PermissionError(f"폴더 {old_item_path}에 대한 쓰기 권한이 없습니다")

            # 새로운 topic 폴더가 없으면 생성
            if not os.path.exists(new_topic_path):
                os.makedirs(new_topic_path)

            # 폴더 이동
            os.rename(old_item_path, new_item_path)

            # 이동된 폴더 내의 파일 이름 변경
            for root, dirs, files in os.walk(new_item_path):
                for file_name in files:
                    if item_code in file_name:
                        old_file_path = os.path.join(root, file_name)
                        new_file_name = file_name.replace(item_code, new_code)
                        new_file_path = os.path.join(root, new_file_name)
                        os.rename(old_file_path, new_file_path)

            # 이전 topic 폴더가 비어있으면 삭제
            if old_topic != new_topic and not os.listdir(old_topic_path):
                os.rmdir(old_topic_path)

            QMessageBox.information(self, 'Success',
                                    f'Item code changed from {item_code} to {new_code}')

            # 테이블 데이터 새로고침
            self.loadData()
            self.update_pool_table()

        except FileNotFoundError as e:
            QMessageBox.critical(self, 'Error', str(e))
        except FileExistsError as e:
            QMessageBox.critical(self, 'Error', str(e))
        except PermissionError as e:
            QMessageBox.critical(self, 'Error', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'예상치 못한 오류가 발생했습니다: {str(e)}') #


    def refractor_item_code_by_gui(self, item_code):
        try:
            new_code, ok = QInputDialog.getText(self, 'Refractor Item Code',
                                                f'Enter new 13-character item code'
                                                f'\nOriginal = {item_code}'
                                                f'\nInput Below:', text=item_code)

            if ok and len(new_code) == 13:
                self.refractor_item_code(item_code, new_code)

            else:
                if ok:  # 사용자가 OK를 눌렀지만 코드 길이가 잘못된 경우
                    QMessageBox.warning(self, 'Error',
                                        'The new item code must be exactly 13 characters long.')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An unexpected error occurred: {str(e)}')

    def change_item_para(self, row, new_para):
        """항목 para 값 변경"""
        if self.list_table.item(row, 3):
            self.list_table.setItem(row, 3, QTableWidgetItem(str(new_para)))
            self.log_message(f"Changed item para to {new_para}")

    def swap_item_number(self, row, dst_number, sender=None):
        """
        항목 번호 변경 함수
        """
        try:
            # 인자 유효성 검사
            if row < 0 or not isinstance(dst_number, int) or dst_number < 1:
                self.log_message(f"Invalid arguments: row={row}, dst_number={dst_number}")
                return

            # sender가 지정되지 않았으면 list_table로 간주
            if sender is None:
                sender = self.list_table

            # POOL 테이블에서 선택한 경우
            if sender == self.pool_table:
                # POOL 테이블에서 선택한 행의 col=0 값 가져오기
                pool_item_code = ""
                if self.pool_table.item(row, 0) and self.pool_table.item(row, 0).text():
                    pool_item_code = self.pool_table.item(row, 0).text()
                else:
                    self.log_message("Error: Selected row in POOL has no item code")
                    return

                # LIST에 동일한 항목 코드가 이미 추가되어 있는지 확인
                dst_row = -1
                for r in range(self.list_table.rowCount()):
                    if (self.list_table.item(r, 0) and
                            self.list_table.item(r, 0).text() and
                            self.list_table.item(r, 0).text() == pool_item_code):  # str() 제거
                        dst_row = r
                        break

                # 이미 추가되어 있다면 번호 swap 수행
                if dst_row >= 0:
                    self.swap_item_number_in_list(dst_row, dst_number)
                    self.log_message(f"Found existing item '{pool_item_code}', swapped to number {dst_number}")
                # 아직 추가되어 있지 않다면
                else:
                    # 해당하는 번호가 존재하는지 확인 (초기화 추가)
                    exist_row = -1  # 변수 초기화 추가
                    for r in range(self.list_table.rowCount()):
                        if (self.list_table.item(r, 1) and
                                self.list_table.item(r, 1).text() and
                                self.list_table.item(r, 1).text() == str(dst_number)):
                            exist_row = r
                            break

                    # 이미 해당 번호를 사용하는 행이 있다면
                    if exist_row >= 0:
                        # 존재하는 번호가 있다면, 그 행의 문항코드만 수정
                        self.list_table.setItem(exist_row, 0, QTableWidgetItem(pool_item_code))
                        self.log_message(f"Updated item code at row {exist_row} to '{pool_item_code}'")
                    # 해당 번호를 사용하는 행이 없다면
                    else:
                        # 존재하는 번호가 없다면, 새 행을 추가
                        current_row = self.list_table.rowCount()
                        self.list_table.insertRow(current_row)

                        # 새 행에 데이터 설정
                        self.list_table.setItem(current_row, 0, QTableWidgetItem(pool_item_code))
                        self.list_table.setItem(current_row, 1, QTableWidgetItem(str(dst_number)))
                        self.list_table.setItem(current_row, 2, QTableWidgetItem("2"))  # 기본 score
                        self.list_table.setItem(current_row, 3, QTableWidgetItem("1L"))  # 기본 para
                        self.list_table.setItem(current_row, 4, QTableWidgetItem("[]"))  # 빈 태그
                        self.list_table.setItem(current_row, 5, QTableWidgetItem("[]"))  # 빈 태그

                        self.log_message(f"Created new row with number {dst_number} and added item '{pool_item_code}'")
            # LIST 테이블에서 선택한 경우
            else:
                self.swap_item_number_in_list(row, dst_number)

            # LIST 테이블을 col=1 기준으로하여 오름차순 정렬
            self.sort_list_by_number_in_ascending_order()
        except Exception as e:
            self.log_message(f"Error in swap_item_number: {str(e)}")

    def swap_item_number_in_list(self, row, dst_number):
        """
        LIST 테이블 내에서 항목 번호 변경 로직

        src_number의 유효성과 dst_number를 가진 행의 존재 여부에 따라 4가지 경우를 처리
        """
        try:
            # 현재 행의 번호(src_number) 가져오기
            src_number = None
            if self.list_table.item(row, 1) and self.list_table.item(row, 1).text():
                try:
                    src_number = int(self.list_table.item(row, 1).text())
                except ValueError:
                    src_number = None

            # 현재 행이 이미 dst_number를 가지고 있는지 확인
            if src_number is not None and src_number == dst_number:
                self.log_message(f"Row already has number {dst_number}")
                return

            # dst_number를 가진 다른 행 찾기 (현재 행 제외)
            dst_row = -1
            for r in range(self.list_table.rowCount()):
                if r == row:  # 현재 행은 제외
                    continue

                if (self.list_table.item(r, 1) and
                        self.list_table.item(r, 1).text() and
                        self.list_table.item(r, 1).text() == str(dst_number)):
                    dst_row = r
                    break

            # src_number가 1-20 사이 자연수인지 확인
            is_valid_src = (src_number is not None and 1 <= src_number <= 20)

            # 조건에 따른 처리
            # 1) src number가 20 이하 자연수 & dst number를 갖는 cell 존재
            if is_valid_src and dst_row >= 0:
                # 현재 행의 number를 dst_number로 변경
                self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
                # dst_number를 갖고 있던 행의 number를 src_number로 변경
                self.list_table.setItem(dst_row, 1, QTableWidgetItem(str(src_number)))

                # 현재 행의 단을 dst의 단으로 변경
                if self.list_table.item(dst_row, 3):
                    self.list_table.setItem(row, 3, QTableWidgetItem(self.list_table.item(dst_row, 3).text()))
                # dst_number를 갖고 있던 행의 단을 src의 단으로 변경
                if self.list_table.item(row, 3):
                    self.list_table.setItem(dst_row, 3, QTableWidgetItem(self.list_table.item(row, 3).text()))
                self.log_message(f"Swapped numbers: {src_number} ↔ {dst_number}")

            # 2) src number가 20 이하 자연수 & dst number를 갖는 cell 없음
            elif is_valid_src and dst_row < 0:
                # 현재 행의 number를 dst_number로 변경
                self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
                self.log_message(f"Changed number from {src_number} to {dst_number}")

            # 3) src number가 20 이하 자연수 아님 & dst number를 갖는 cell 존재
            elif not is_valid_src and dst_row >= 0:
                # 현재 행의 number를 dst_number로 변경
                self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
                # dst_number를 갖고 있던 행의 number를 null로 변경
                self.list_table.setItem(dst_row, 1, QTableWidgetItem(""))
                self.log_message(f"Changed number to {dst_number} and cleared previous {dst_number}")

            # 4) src number가 20 이하 자연수 아님 & dst number를 갖는 cell 없음
            else:
                # 현재 행의 number를 dst_number로 변경
                self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
                self.log_message(f"Changed number to {dst_number}")

        except Exception as e:
            self.log_message(f"Error in swap_item_number_in_list: {str(e)}")

    def swap_item_number_in_list(self, row, dst_number):
        """
        항목 번호 변경 (고급 버전)
        sender가 self.list_table인 경우:
        1) src number가 20 이하 자연수이면서 dst number를 갖는 cell이 있는 경우:
           현재 행의 number를 dst_number로 바꾸고, dst_number를 갖고 있던 행의 number를 src_number로 바꿈
        2) src number가 20 이하 자연수이면서 dst number를 갖는 cell이 없는 경우:
           현재 행의 number를 dst_number로 바꿈
        3) src number가 20 이하 자연수가 아니면서 dst number를 갖는 cell이 있는 경우:
           현재 행의 number를 dst_number로 바꾸고, dst_number를 갖고 있던 행의 number를 null로 바꿈
        4) src number가 20 이하 자연수가 아니면서 dst number를 갖는 cell이 없는 경우:
           현재 행의 number를 dst_number로 바꿈
        """
        # 현재 행의 번호(src_number) 가져오기
        src_number = None
        if self.list_table.item(row, 1) and self.list_table.item(row, 1).text():
            try:
                src_number = int(self.list_table.item(row, 1).text())
            except ValueError:
                src_number = None

        # dst_number를 가진 행 찾기
        dst_row = -1
        for r in range(self.list_table.rowCount()):
            if (self.list_table.item(r, 1) and
                    self.list_table.item(r, 1).text() and
                    self.list_table.item(r, 1).text() == str(dst_number)):
                dst_row = r
                break

        # src_number가 1-20 사이 자연수인지 확인
        is_valid_src = (src_number is not None and 1 <= src_number <= 20)

        # 조건에 따른 처리
        # 1) src number가 20 이하 자연수 & dst number를 갖는 cell 존재
        if is_valid_src and dst_row >= 0:
            # 현재 행의 number를 dst_number로 변경
            self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
            # dst_number를 갖고 있던 행의 number를 src_number로 변경
            self.list_table.setItem(dst_row, 1, QTableWidgetItem(str(src_number)))
            self.log_message(f"Swapped numbers: {src_number} ↔ {dst_number}")

        # 2) src number가 20 이하 자연수 & dst number를 갖는 cell 없음
        elif is_valid_src and dst_row < 0:
            # 현재 행의 number를 dst_number로 변경
            self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
            self.log_message(f"Changed number from {src_number} to {dst_number}")

        # 3) src number가 20 이하 자연수 아님 & dst number를 갖는 cell 존재
        elif not is_valid_src and dst_row >= 0:
            # 현재 행의 number를 dst_number로 변경
            self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
            # dst_number를 갖고 있던 행의 number를 null로 변경
            self.list_table.setItem(dst_row, 1, QTableWidgetItem(""))
            self.log_message(f"Changed number to {dst_number} and cleared previous {dst_number}")

        # 4) src number가 20 이하 자연수 아님 & dst number를 갖는 cell 없음
        else:
            # 현재 행의 number를 dst_number로 변경
            self.list_table.setItem(row, 1, QTableWidgetItem(str(dst_number)))
            self.log_message(f"Changed number to {dst_number}")

    #TAG
    def show_tag_context_menu(self, pos):
        """태그 리스트에서 우클릭 시 컨텍스트 메뉴 표시"""
        try:
            # 클릭한 위치의 아이템 가져오기
            item = self.tag_list.itemAt(pos)
            if not item:
                return

            # 아이템의 텍스트를 item_code로 사용
            item_code = item.text()

            # 코드가 항목 코드 형식(13자리)인지 확인
            if len(item_code) == 13:
                # 컨텍스트 메뉴 생성
                menu = QMenu(self)

                # 메뉴 항목 추가
                menu.addAction("Open item HWP", lambda: self.open_item_hwp(item_code))
                menu.addAction("Open Folder", lambda: self.open_item_folder(item_code))
                menu.addAction("Refractor Item Code", lambda: self.refractor_item_code_by_gui(item_code))

                # 메뉴 표시
                menu.exec_(self.tag_list.mapToGlobal(pos))

                # 메뉴 객체 정리
                menu.deleteLater()

        except Exception as e:
            self.log_message(f"태그 컨텍스트 메뉴 오류: {str(e)}")
    def add_tag(self):
        """새 태그 추가"""
        tag_text = self.tag_input.text().strip()
        if tag_text:
            # 중복 검사
            existing_tags = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]
            if tag_text not in existing_tags:
                item = QListWidgetItem(tag_text)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.tag_list.addItem(item)
                self.tag_input.clear()

    def remove_selected_tag(self):
        """선택된 태그 삭제"""
        selected_items = self.tag_list.selectedItems()
        if selected_items:
            for item in selected_items:
                self.tag_list.takeItem(self.tag_list.row(item))

    def on_tags_reordered(self):
        """태그 순서가 변경되었을 때 호출"""
        # 순서 변경 시 특별한 처리가 필요하면 여기에 구현

    def save_tags(self):
        """태그 편집 완료 및 저장"""
        if self.current_edit_row >= 0 and self.current_edit_col >= 0:
            # 현재 태그 목록 가져오기
            tags = [self.tag_list.item(i).text() for i in range(self.tag_list.count())]

            # JSON 형식으로 변환하여 셀에 저장
            json_str = json.dumps(tags)
            self.list_table.setItem(self.current_edit_row, self.current_edit_col,
                                    QTableWidgetItem(json_str))

            # 셀 배경색 변경하여 수정되었음을 표시
            if tags:  # 태그가 있는 경우만 색상 변경
                self.list_table.item(self.current_edit_row, self.current_edit_col).setBackground(
                    QColor(230, 255, 230))  # 연한 녹색

            # 편집 상태 초기화
            self.tag_management_frame.setVisible(False)
            self.current_edit_row = -1
            self.current_edit_col = -1

    def cancel_tag_edit(self):
        """태그 편집 취소"""
        self.tag_management_frame.setVisible(False)
        self.current_edit_row = -1
        self.current_edit_col = -1

    # list_table의 셀 클릭 이벤트를 처리하는 메소드

    def handle_cell_click(self, row, col):
        """셀 클릭 시 태그 관리 UI 표시 (태그 컬럼인 경우)"""
        # 태그 관련 컬럼인 경우 (4, 5번 컬럼)
        if col in [4, 5]:
            # 현재 편집 중인 셀 정보 저장
            self.current_edit_row = row
            self.current_edit_col = col

            # 현재 셀의 태그 가져오기
            current_tags = []
            cell_item = self.list_table.item(row, col)

            if cell_item and cell_item.text():
                try:
                    # JSON 형식으로 되어 있는지 체크
                    if cell_item.text().startswith('[') and cell_item.text().endswith(']'):
                        text = cell_item.text().replace("'", "\"")  # 작은따옴표를 큰따옴표로 변환
                        try:
                            current_tags = json.loads(text)
                        except json.JSONDecodeError:
                            # 작은따옴표를 썼을 때 파싱 실패하는 경우 수동으로 파싱
                            text = cell_item.text().strip('[]')
                            if text:
                                # 쉼표로 구분된 항목을 파싱
                                items = [item.strip().strip("'\"") for item in text.split(',')]
                                current_tags = items
                    else:
                        # 단일 문자열인 경우
                        current_tags = [cell_item.text()] if cell_item.text().strip() else []
                except Exception as e:
                    self.log_message(f"태그 파싱 오류: {e}")
                    current_tags = []

            # 태그 목록 초기화 및 로드
            self.tag_list.clear()
            for tag in current_tags:
                if tag:  # 빈 태그는 추가하지 않음
                    item = QListWidgetItem(tag)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    self.tag_list.addItem(item)

            # 태그 관리 UI 표시
            self.tag_management_frame.setVisible(True)
            self.tag_input.setFocus()
        else:
            # 태그 관련 컬럼이 아닌 경우 태그 관리 UI 숨김
            if self.tag_management_frame.isVisible():
                # 태그 편집 중이었다면 자동으로 저장
                if self.current_edit_row >= 0 and self.current_edit_col >= 0:
                    self.save_tags()
                else:
                    self.cancel_tag_edit()

    def load_topic_table(self):
        """Topic 테이블 초기 로드 - 3개 테이블로 분할"""
        # Load topics from JSON files
        with open(RESOURCES_PATH + '/topic.json', 'r', encoding='utf-8') as f:
            topics_data = json.load(f)

        with open(RESOURCES_PATH + '/test_topic.json', 'r', encoding='utf-8') as f:
            order_data = json.load(f)

        # Filter Dialog와 동일한 방식으로 정렬
        grouped_topics = self.group_topics_by_order(topics_data, order_data)

        # 테이블에 데이터 로드 - order 값에 따라 3개 테이블로 분할
        topic_groups = [[], [], []]  # 3개 그룹

        for order_value in sorted(grouped_topics.keys()):
            for topic_code in grouped_topics[order_value]:
                topic_data = {
                    'code': topic_code,
                    'name': f'{order_value}) {topics_data[topic_code]}',
                    'order': order_value
                }

                # order 값에 따라 그룹 분할
                if 1 <= order_value <= 6:
                    topic_groups[0].append(topic_data)
                elif 7 <= order_value <= 13:
                    topic_groups[1].append(topic_data)
                else:  # 14-20
                    topic_groups[2].append(topic_data)

        # 각 테이블에 데이터 로드
        for table_idx, topics in enumerate(topic_groups):
            table = self.topic_tables[table_idx]
            table.setRowCount(len(topics))

            for i, topic in enumerate(topics):
                table.setItem(i, 0, QTableWidgetItem(topic['code']))
                table.setItem(i, 1, QTableWidgetItem(topic['name']))
                table.setItem(i, 2, QTableWidgetItem(""))  # 초기에는 빈 문자열

        # 초기 업데이트
        self.update_topic_table()

    def group_topics_by_order(self, topics_data, order_data):
        """FilterDialog와 동일한 그룹화 함수"""
        grouped_topics = {}

        for key, topic_name in topics_data.items():
            if key in order_data:
                order_value = order_data[key]
                if order_value not in grouped_topics:
                    grouped_topics[order_value] = []
                grouped_topics[order_value].append(key)

        # 각 그룹 내에서 키 순서대로 정렬
        order_keys = list(order_data.keys())
        for order_value in grouped_topics:
            grouped_topics[order_value].sort(key=lambda x: order_keys.index(x) if x in order_keys else float('inf'))

        return grouped_topics

    def update_topic_table(self):
        """3개 Topic 테이블의 번호 컬럼과 색상 업데이트 + 정사각형 업데이트 (디버깅 버전)"""
        # 캐시된 order_data 사용
        order_data = self.load_topic_order_data()

        # LIST 테이블에서 각 topic별 번호들 수집
        topic_numbers = {}
        quater_has_items = set()  # 문항이 있는 quater들을 저장

        print("=== DEBUG: Scanning LIST table ===")
        print(f"LIST table has {self.list_table.rowCount()} rows")

        for row in range(self.list_table.rowCount()):
            item_code_item = self.list_table.item(row, 0)
            number_item = self.list_table.item(row, 1)

            if item_code_item and item_code_item.text() and len(item_code_item.text()) == 13:
                item_code = item_code_item.text()
                topic = item_code[2:5]
                number_text = number_item.text() if number_item else ""

                print(
                    f"Row {row}: {item_code} -> topic: '{topic}', number: '{number_text}' (length: {len(number_text)})")

                if number_item and number_item.text().strip():  # .strip() 추가로 공백 제거
                    if topic not in topic_numbers:
                        topic_numbers[topic] = []
                    topic_numbers[topic].append(number_item.text().strip())

                    # 해당 topic의 quater 추가
                    if topic in order_data:
                        quater = order_data[topic]
                        quater_has_items.add(quater)
                        print(f"  -> ✓ Added quater {quater} for topic '{topic}'")
                    else:
                        print(f"  -> ✗ Topic '{topic}' NOT FOUND in order_data")
                else:
                    print(f"  -> No valid number for this item")
            else:
                item_code_text = item_code_item.text() if item_code_item else "None"
                print(
                    f"Row {row}: Invalid item_code: '{item_code_text}' (length: {len(item_code_text) if item_code_text else 0})")

        print(f"=== Topic numbers collected: {topic_numbers} ===")
        print(f"=== Final quater_has_items: {sorted(quater_has_items)} ===")

        # 3개 Topic 테이블 모두 업데이트
        for table in self.topic_tables:
            for row in range(table.rowCount()):
                topic_code_item = table.item(row, 0)
                if topic_code_item:
                    topic_code = topic_code_item.text()

                    # 번호 컬럼 업데이트
                    numbers = topic_numbers.get(topic_code, [])
                    numbers.sort(key=lambda x: int(x) if x.isdigit() else float('inf'))
                    numbers_text = ', '.join(numbers)
                    table.setItem(row, 2, QTableWidgetItem(numbers_text))

                    # 색상 업데이트 (캐시된 데이터 사용)
                    try:
                        if topic_code in order_data and numbers:  # 번호가 있을 때만 색칠
                            quater = order_data[topic_code]
                            color = self.get_topic_color_code(quater)

                            # 전체 행에 색상 적용
                            for col in range(3):
                                item = table.item(row, col)
                                if item:
                                    item.setBackground(color)
                        else:
                            # 번호가 없으면 색상 제거
                            for col in range(3):
                                item = table.item(row, col)
                                if item:
                                    item.setBackground(QColor("white"))  # 기본 색상

                    except (ValueError, KeyError, IndexError):
                        pass

        # 정사각형들 업데이트
        print(f"=== Updating squares with quaters: {sorted(quater_has_items)} ===")
        self.update_quater_squares(quater_has_items)

    def update_quater_squares(self, quater_has_items):
        """정사각형들의 색칠 상태 업데이트 (디버깅 버전)"""
        quater_ranges = [(1, 6), (7, 13), (14, 20)]  # 각 그룹의 quater 범위

        print("=== DEBUG: Updating squares ===")
        for group_idx, squares_group in enumerate(self.quater_squares):
            start_quater, end_quater = quater_ranges[group_idx]
            print(f"Group {group_idx}: quaters {start_quater}-{end_quater}")

            for square_idx, square in enumerate(squares_group):
                quater = start_quater + square_idx

                if quater in quater_has_items:
                    # 문항이 있는 quater는 색칠
                    color = self.get_topic_color_code(quater)
                    square.setStyleSheet(
                        f"border: 1px solid black; background-color: {color.name()}; font-size: 10px; font-weight: bold; color: white;")
                    print(f"  -> Square {quater}: COLORED with {color.name()}")
                else:
                    # 문항이 없는 quater는 흰색
                    square.setStyleSheet(
                        f"border: 1px solid black; background-color: white; font-size: 10px; font-weight: bold; color: black;")
                    print(f"  -> Square {quater}: WHITE")

    def get_topic_color_code(self, quater):
        """Topic 색상 코드 반환"""
        topic_color_code = ["#FF8A80", "#FFAB91", "#FFCDD2", "#FF9800", "#FFC107",
                            "#FFD54F", "#81C784", "#A5D6A7", "#C8E6C9", "#2196F3",
                            "#42A5F5", "#64B5F6", "#90CAF9", "#B39DDB", "#CE93D8",
                            "#E1BEE7", "#F0D5D4", "#C4B5A0", "#D4C4B0", "#E4D4C0"]
        color = topic_color_code[quater - 1]
        return QColor(color)

    def load_topic_order_data(self):
        """test_topic.json 데이터를 한 번만 로드하여 캐시"""
        if self.topic_order_data is None:
            with open(RESOURCES_PATH + '/test_topic.json', 'r', encoding='utf-8') as f:
                self.topic_order_data = json.load(f)
        return self.topic_order_data

    def schedule_topic_update(self):
        """Topic 테이블 업데이트를 지연시켜 배치로 처리"""
        if not self.topic_update_scheduled:
            self.topic_update_scheduled = True
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.perform_topic_update)  # 100ms 후 실행

    def perform_topic_update(self):
        """실제 Topic 테이블 업데이트 수행"""
        self.topic_update_scheduled = False
        self.update_topic_table()
    def show_topic_context_menu(self, pos):
        """Topic 테이블 우클릭 컨텍스트 메뉴 표시"""
        try:
            sender = self.sender()
            if not sender:
                return

            row = sender.rowAt(pos.y())
            col = sender.columnAt(pos.x())

            # 유효한 셀 위치인지 확인
            if row < 0 or col < 0:
                return

            # 선택된 topic code 가져오기
            topic_code_item = sender.item(row, 0)
            if not topic_code_item or not topic_code_item.text():
                return

            topic_code = topic_code_item.text()

            # 컨텍스트 메뉴 생성
            menu = QMenu(self)

            # Filter QUATER 액션
            filter_quater_action = menu.addAction("Filter QUATER")
            filter_quater_action.triggered.connect(lambda: self.filter_by_quater(topic_code))

            # Filter TOPIC 액션
            filter_topic_action = menu.addAction("Filter TOPIC")
            filter_topic_action.triggered.connect(lambda: self.filter_by_topic(topic_code))

            # 메뉴 표시
            menu.exec_(sender.mapToGlobal(pos))

            # 메뉴 객체 정리
            menu.deleteLater()

        except Exception as e:
            self.log_message(f"Topic context menu error: {str(e)}")

    def filter_by_quater(self, topic_code):
        """선택된 topic의 quater로 필터링"""
        try:
            # topic_code의 quater 찾기
            order_data = self.load_topic_order_data()
            if topic_code not in order_data:
                self.log_message(f"Topic {topic_code} not found in order data")
                return

            target_quater = order_data[topic_code]

            # 같은 quater에 속하는 모든 topic 찾기
            topics_in_quater = [code for code, quater in order_data.items() if quater == target_quater]

            # POOL 테이블 필터링
            filtered_data = [item for item in self.pool_data if item['topic'] in topics_in_quater]
            self.update_pool_table(filtered_data)
            self.sort_pool_by_order()

            self.log_message(f"Filtered by quater {target_quater}: {len(topics_in_quater)} topics")

        except Exception as e:
            self.log_message(f"Error filtering by quater: {str(e)}")

    def filter_by_topic(self, topic_code):
        """선택된 topic으로 필터링"""
        try:
            # 해당 topic만으로 필터링
            filtered_data = [item for item in self.pool_data if item['topic'] == topic_code]
            self.update_pool_table(filtered_data)
            self.sort_pool_by_order()

            self.log_message(f"Filtered by topic {topic_code}: {len(filtered_data)} items")

        except Exception as e:
            self.log_message(f"Error filtering by topic: {str(e)}")


class FilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Filter Topics')
        layout = QVBoxLayout()

        # Load topics from JSON file
        with open(RESOURCES_PATH + '/topic.json', 'r', encoding='utf-8') as f:
            topics_data = json.load(f)

        # Load test_topic.json for sorting order
        with open(RESOURCES_PATH + '/test_topic.json', 'r', encoding='utf-8') as f:
            order_data = json.load(f)

        # 상단 버튼들
        top_buttons = QHBoxLayout()
        select_all_btn = QPushButtonGui('Select All')
        select_none_btn = QPushButtonGui('Select None')
        apply_btn = QPushButtonGui('Apply Filter')
        top_buttons.addWidget(select_all_btn)
        top_buttons.addWidget(select_none_btn)
        top_buttons.addWidget(apply_btn)
        layout.addLayout(top_buttons)

        # 메인 그리드 레이아웃
        self.checkboxes = []
        self.category_checkboxes = {}
        main_layout = QHBoxLayout()

        # 왼쪽 카테고리 버튼들을 위한 레이아웃
        category_layout = QVBoxLayout()

        # 오른쪽 체크박스들을 위한 그리드 레이아웃
        checkbox_grid = QGridLayout()

        # order_data의 value로 그룹화하고 정렬
        grouped_topics = self.group_topics_by_order(topics_data, order_data)
        current_row = 0

        for i, order_value in enumerate(sorted(grouped_topics.keys())):
            group = grouped_topics[order_value]

            # 카테고리 버튼 (order_value를 카테고리명으로 사용)
            category_btn = QPushButtonGui(f'Group {order_value}')
            category_layout.addWidget(category_btn)

            # Group 12에만 stretch factor를 2로 설정, 나머지는 1
            if order_value == 12 or order_value == 4:
                category_layout.setStretch(i, 2)
            else:
                category_layout.setStretch(i, 1)

            self.category_checkboxes[order_value] = []

            # 체크박스들을 오른쪽 그리드에 4열로 배치
            count = 0
            for key in group:
                display_text = f'{key} : {topics_data[key]}'
                cb = QCheckBox(display_text)
                cb.setChecked(False)
                self.checkboxes.append(cb)
                self.category_checkboxes[order_value].append(cb)
                checkbox_grid.addWidget(cb, current_row, count)
                count += 1
                if count >= 4:
                    current_row += 1
                    count = 0

            if count > 0:
                current_row += 1

            # 카테고리 버튼 클릭 이벤트
            category_btn.clicked.connect(lambda checked, cat=order_value: self.toggle_category(cat))

        # 카테고리 레이아웃을 왼쪽에 배치
        category_widget = QWidget()
        category_widget.setLayout(category_layout)
        category_widget.setFixedWidth(150)
        main_layout.addWidget(category_widget)

        # 체크박스 그리드를 오른쪽에 배치
        checkbox_widget = QWidget()
        checkbox_widget.setLayout(checkbox_grid)
        main_layout.addWidget(checkbox_widget)

        layout.addLayout(main_layout)
        self.setLayout(layout)

        select_all_btn.clicked.connect(self.select_all)
        select_none_btn.clicked.connect(self.select_none)
        apply_btn.clicked.connect(self.apply_filter)

    def group_topics_by_order(self, topics_data, order_data):
        """order_data의 value로 그룹화하고 각 그룹 내에서 key 순서대로 정렬"""
        grouped_topics = {}

        for key, topic_name in topics_data.items():
            if key in order_data:
                order_value = order_data[key]
                if order_value not in grouped_topics:
                    grouped_topics[order_value] = []
                grouped_topics[order_value].append(key)

        # 각 그룹 내에서 키 순서대로 정렬 (order_data에 나타나는 순서대로)
        order_keys = list(order_data.keys())
        for order_value in grouped_topics:
            grouped_topics[order_value].sort(key=lambda x: order_keys.index(x) if x in order_keys else float('inf'))

        return grouped_topics

    def toggle_category(self, category):
        checkboxes = self.category_checkboxes.get(category, [])
        if not checkboxes:
            return

        all_checked = all(cb.isChecked() for cb in checkboxes)
        for cb in checkboxes:
            cb.setChecked(not all_checked)

    def select_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)

    def select_none(self):
        for cb in self.checkboxes:
            cb.setChecked(False)

    def apply_filter(self):
        selected_topics = [cb.text().split(' : ')[0] for cb in self.checkboxes if cb.isChecked()]
        filtered_data = [item for item in self.parent.pool_data if item['topic'] in selected_topics]
        self.parent.update_pool_table(filtered_data)
        self.parent.sort_pool_by_order()
        self.accept()

if __name__ == '__main__':

    suppress_qt_warnings()

    app = QApplication(sys.argv)
    app.beep = lambda: None
    app_icon = QIcon(r'T:\Software\LCS\resources\symbol\symbol.png')
    app.setWindowIcon(app_icon)
    app.setStyle('Fusion')  # Apply Fusion style
    ex = DatabaseManager()
    ex.show()
    sys.exit(app.exec_())