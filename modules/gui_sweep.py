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
from main import build_sweep
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

from gui_exam import DatabaseManager

def suppress_qt_warnings():
    environ["QT_DEVICE_PIXEL_RATIO"] = "0"
    environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    environ["QT_SCREEN_SCALE_FACTORS"] = "1"
    environ["QT_SCALE_FACTOR"] = "1"


class QPushButtonGui(QPushButton):
    def __init__(self, parent=None):
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


class DatabaseManagerSweep(QMainWindow):
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
        self.add_context_menu()
        self.sort_pool_by_order()

        self.setWindowTitle('Lab Contents SWEEP Software ver.2.0.0. Powered by THedu')

    def initUI(self):
        self.setWindowTitle('Database Manager')
        self.setGeometry(100, 100, 1000, 700)  # Adjusted width to accommodate log window

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
        self.list_table.setHorizontalHeaderLabels(['Item Code', '번', '타입', '추가', '테마', '메모'])

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
        self.list_table.setColumnWidth(2, 70)  # type
        self.list_table.setColumnWidth(3, 70)  # plus
        self.list_table.setColumnWidth(4, 70)  # theme
        self.list_table.setColumnWidth(5, 90)  # memo

        # Calculate and set fixed total width
        self.list_table.setFixedWidth(470)
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
        self.build_sweep_by_gui_btn = QPushButtonGui('build SWEEP')
        self.open_naive_sweep_pdf_btn = QPushButtonGui('open SWEEP')
        self.rasterize_sweep_pdf_btn = QPushButtonGui('raster SWEEP')
        self.open_rasterized_sweep_pdf_btn = QPushButtonGui('open SWEEP_R')
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
        right_layout_hz_1.addWidget(self.build_sweep_by_gui_btn)
        right_layout_hz_1.addWidget(self.open_naive_sweep_pdf_btn)
        right_button_layout.addLayout(right_layout_hz_1)

        right_layout_hz_2 = QHBoxLayout()
        right_layout_hz_2.addWidget(self.rasterize_sweep_pdf_btn)
        right_layout_hz_2.addWidget(self.open_rasterized_sweep_pdf_btn)
        right_button_layout.addLayout(right_layout_hz_2)

        right_button_layout.addStretch()

        right_button_layout.addWidget(self.log_window)

        # Add layouts to main layout
        layout.addLayout(pool_layout)
        layout.addLayout(button_layout)
        layout.addLayout(list_layout)
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
        self.merge_pdfs_btn.clicked.connect(self.merge_pdfs_gui)
        self.export_json_btn.clicked.connect(self.export_to_json)
        self.build_sweep_by_gui_btn.clicked.connect(self.build_sweep_by_gui)
        self.rasterize_sweep_pdf_btn.clicked.connect(self.rasterize_sweep_pdf_by_gui)
        self.open_merged_pdf_btn.clicked.connect(self.open_merged_pdf)
        self.open_naive_sweep_pdf_btn.clicked.connect(self.open_naive_sweep_pdf)
        self.open_rasterized_sweep_pdf_btn.clicked.connect(self.open_rasterized_sweep_pdf)


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
        if not self.show_warning_dialog("Are you sure you want to remove these rows?"):
            return
        selected_rows = sorted(set(item.row() for item in self.list_table.selectedItems()), reverse=True)
        for row in selected_rows:
            self.list_table.removeRow(row)

    def eventFilter(self, obj, event):
        # 각 위젯별 이벤트 처리
        if event.type() == event.KeyPress:
            key = event.key()

            # 테이블에서의 키 처리
            if obj in [self.pool_table, self.list_table]:
                if key == Qt.Key_Shift:
                    # SHIFT 키는 다중 선택 모드로 변경
                    obj.setSelectionMode(QTableWidget.MultiSelection)
                    obj.setSelectionBehavior(QTableWidget.SelectRows)
                elif key == Qt.Key_Escape:
                    # ESC 키 처리
                    if self.pool_table.hasFocus():
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
                self.list_table.setItem(current_row, 2, QTableWidgetItem("대표"))
                self.list_table.setItem(current_row, 3, QTableWidgetItem())

                # 태그 컬럼에 빈 JSON 배열 설정
                self.list_table.setItem(current_row, 4, QTableWidgetItem())
                self.list_table.setItem(current_row, 5, QTableWidgetItem())

    def add_empty_row(self):
        current_row = self.list_table.rowCount()
        self.list_table.insertRow(current_row)

        self.list_table.setItem(current_row, 0, QTableWidgetItem(""))
        self.list_table.setItem(current_row, 1, QTableWidgetItem(str(current_row + 1)))
        self.list_table.setItem(current_row, 2, QTableWidgetItem("대표"))
        self.list_table.setItem(current_row, 3, QTableWidgetItem())
        self.list_table.setItem(current_row, 4, QTableWidgetItem())
        self.list_table.setItem(current_row, 5, QTableWidgetItem())

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
        book_names = [file_name for file_name in os.listdir(SWEEP_DB_PATH) if file_name.endswith('.json')]
        book_names.sort()  # Sort book names in ascending order
        self.book_name_input.addItems(book_names)

    def load_selected_book(self):
        book_name = self.book_name_input.currentText()
        book_path = os.path.join(SWEEP_DB_PATH, book_name)

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

                if row_data.get('type') is not None:
                    self.list_table.setItem(row_count, 2, QTableWidgetItem(str(row_data['type'])))

                if row_data.get('plus') is not None:
                    self.list_table.setItem(row_count, 3, QTableWidgetItem(str(row_data['plus'])))

                if row_data.get('theme') is not None:
                    self.list_table.setItem(row_count, 4, QTableWidgetItem(str(row_data['theme'])))

                if row_data.get('memo') is not None:
                    self.list_table.setItem(row_count, 5, QTableWidgetItem(str(row_data['memo'])))

        except Exception as e:
            self.log_message(f"Error loading book: {e}")

    def export_to_json(self):
        if not self.show_warning_dialog("Are you sure you want to export to JSON?"):
            return

        book_name = self.book_name_input.currentText()
        output_path = os.path.join(SWEEP_DB_PATH, book_name)

        data = []

        # JSON에서 원하는 키 순서
        json_keys = ['item_code', 'number', 'type', 'plus', 'theme', 'memo']

        for row in range(self.list_table.rowCount()):
            temp_data = {}
            # 각 열의 데이터를 추출하여 딕셔너리에 추가
            temp_data['item_code'] = self.list_table.item(row, 0).text() if self.list_table.item(row, 0) else None
            temp_data['number'] = int(self.list_table.item(row, 1).text()) if self.list_table.item(row, 1) else None
            temp_data['type'] = (self.list_table.item(row, 2).text()) if self.list_table.item(row, 2) else None
            temp_data['plus'] = self.list_table.item(row, 3).text() if self.list_table.item(row, 3) else None
            temp_data['theme'] = (self.list_table.item(row, 4).text()) if self.list_table.item(row, 4) else None
            temp_data['memo'] = self.list_table.item(row, 5).text() if self.list_table.item(row, 5) else None
            # 딕셔너리를 리스트에 추가
            data.append(temp_data)

        # JSON 파일로 저장
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log_message(f"Exported to JSON successfully: {output_path}")
        except Exception as e:
            self.log_message(f"Error exporting to JSON: {e}")

    def build_sweep_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to build the SWEEP paper?"):
            return
        if not self.show_warning_dialog("Please Ensure that Every PDF file is Updated"):
            return
        book_name = self.book_name_input.currentText()
        input_path = os.path.join(SWEEP_DB_PATH, book_name)
        output_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '_SW.pdf'))
        self.log_message("Starting SWEEP paper build...")
        try:
            build_sweep(input=input_path, output=output_path, log_callback=self.log_message)
        except Exception as e:
            error_message = f"Error during SWEEP paper build: {e}\n{traceback.format_exc()}"
            self.log_message(error_message)

    def rasterize_sweep_pdf_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to rasterize the PDF?"):
            return
        book_name = self.book_name_input.currentText()
        self.log_message("Starting PDF rasterization...")
        try:
            add_watermark_and_rasterize(os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_SW.pdf'),
                                        os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_SW_R.pdf'))
            print(f"Rasterized PDF saved to: {os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_SW_R.pdf')}")
            self.log_message("SWEEP PDF rasterization completed successfully.")
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

    def open_naive_sweep_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '_SW.pdf'))
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                self.log_message(f"Opened PDF: {pdf_path}")
            except Exception as e:
                self.log_message(f"Error opening PDF: {e}")
        else:
            self.log_message(f"PDF not found: {pdf_path}")

    def open_rasterized_sweep_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_SW_R.pdf')
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

            # POOL 또는 LIST 테이블의 col = 0, 1 열
            if sender in [self.pool_table, self.list_table] and col in [0, 1]:
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

                    action4 = menu.addAction("Filter Topic")
                    action4.setData({'type': 'filter', 'topic': item_code[2:5]})
                    action4.triggered.connect(self.handle_context_action)
                    menu.addSeparator()

                # Swap to xx 옵션
                action = menu.addAction(f"Swap to ???")
                action.setData({'type': 'swap', 'row': row, 'sender': sender})
                action.triggered.connect(self.handle_context_action)

            # LIST 테이블의 col = 2 열
            elif sender == self.list_table and col == 2:
                move_options = ["대표", "기본", "발전"]

                for option in move_options:
                    action = menu.addAction(f"Type: {option}")
                    action.setData({'type': 'type', 'row': row, 'para': option})
                    action.triggered.connect(self.handle_context_action)

            # LIST 테이블의 col = 3 열
            elif sender == self.list_table and col == 3:
                move_options = ["없음", "고난도", "신유형"]

                for option in move_options:
                    action = menu.addAction(f"Plus: {option}")
                    action.setData({'type': 'plus', 'row': row, 'para': option})
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
            elif action_type == 'filter':
                self.filter_by_topic(data['topic'])
            elif action_type == 'swap':
                # 사용자로부터 숫자 입력 받기
                dst_number, ok = QInputDialog.getInt(
                    self,
                    'Swap Number',
                    'Enter destination number:',
                    value=1,
                    min=1,
                    max=100
                )
                if ok:
                    self.safe_swap_item_number(data['row'], dst_number, data['sender'])
            elif action_type == 'type':
                self.safe_change_item_type(data['row'], data['type'])
            elif action_type == 'plus':
                self.safe_change_item_plus(data['row'], data['plus'])

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
        # 원본 코드의 정보 파싱
        if item_code[5:7] == 'KC':
            old_base_path = KICE_DB_PATH
        elif item_code[5:7] == 'NC':
            old_base_path = NICE_DB_PATH
        else:
            old_base_path = ITEM_DB_PATH
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
            QMessageBox.critical(self, 'Error', f'예상치 못한 오류가 발생했습니다: {str(e)}')

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

    def change_item_type(self, row, new_type):
        """항목 type 값 변경"""
        if self.list_table.item(row, 2):
            self.list_table.setItem(row, 2, QTableWidgetItem(str(new_type)))
            self.log_message(f"Changed item para to {new_type}")

    def change_item_plus(self, row, new_plus):
        """항목 type 값 변경"""
        if self.list_table.item(row, 3):
            self.list_table.setItem(row, 3, QTableWidgetItem(str(new_plus)))
            self.log_message(f"Changed item para to {new_plus}")
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
                        self.list_table.setItem(current_row, 2, QTableWidgetItem("기본"))  # 기본 타입
                        self.list_table.setItem(current_row, 3, QTableWidgetItem("없음"))  # 기본 plus
                        self.list_table.setItem(current_row, 4, QTableWidgetItem(""))  # 빈 테마
                        self.list_table.setItem(current_row, 5, QTableWidgetItem(""))  # 빈 메모

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
    ex = DatabaseManagerSweep()
    ex.show()
    sys.exit(app.exec_())