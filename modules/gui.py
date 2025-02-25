from utils.path import *
from utils.parse_code import *
from os import environ
import subprocess
import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QComboBox, QMessageBox, QLineEdit, QMenu,
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QGridLayout, QInputDialog,
                             QHeaderView, QCheckBox, QDialog, QVBoxLayout, QLabel, QSizePolicy)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal)
from PyQt5.QtGui import QColor
from main import build_squeeze_paper
from PyQt5.QtGui import QIcon
from hwps.multi_printer import *
from rasterizer import *
from utils.path import *
from utils.parse_code import *
import traceback

def suppress_qt_warnings():
    environ["QT_DEVICE_PIXEL_RATIO"] = "0"
    environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    environ["QT_SCREEN_SCALE_FACTORS"] = "1"
    environ["QT_SCALE_FACTOR"] = "1"


class QPushButton(QPushButton):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

# Add the following import at the top
from PyQt5.QtWidgets import QTextEdit

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
        self.initUI()
        self.load_kice_topics()
        self.loadData()
        self.add_context_menu()
        self.sort_pool_by_order()

        self.setWindowTitle('Lab Contents Software ver.1.0.0. Powered by THedu')

    def initUI(self):
        self.setWindowTitle('Database Manager')
        self.setGeometry(100, 100, 1300, 600)  # Adjusted width to accommodate log window

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout()
        main_widget.setLayout(layout)

        # Pool section
        pool_layout = QVBoxLayout()

        # Top buttons for Pool
        pool_top_layout = QVBoxLayout()
        self.deselect_btn = QPushButton('DESELECT POOL')
        self.sort_btn = QPushButton('SORT POOL')
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Search Item Code...')

        pool_top_layout.addWidget(self.deselect_btn)
        pool_top_layout.addWidget(self.sort_btn)
        pool_top_layout.addWidget(self.search_input)
        pool_layout.addLayout(pool_top_layout)

        # Pool table with fixed dimensions
        self.pool_table = QTableWidget()
        self.pool_table.setColumnCount(3)
        self.pool_table.setFixedHeight(550)
        pool_layout.addWidget(self.pool_table)
        self.pool_table.setHorizontalHeaderLabels(['Item Code', 'Topic', 'Order'])

        # Set fixed column widths for Pool table
        self.pool_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.pool_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.pool_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)

        self.pool_table.setColumnWidth(0, 120)  # Item Code
        self.pool_table.setColumnWidth(1, 50)  # Topic
        self.pool_table.setColumnWidth(2, 0)  # Order (hidden)

        # Calculate and set fixed total width
        total_width = sum([self.pool_table.columnWidth(i) for i in range(3)])  # Exclude hidden Order column
        self.pool_table.setFixedWidth(total_width + 50)

        # Hide Order column
        self.pool_table.hideColumn(2)

        # Middle buttons
        button_layout = QVBoxLayout()
        self.transfer_btn = QPushButton('→')
        self.add_btn = QPushButton('+')
        self.remove_btn = QPushButton('-')
        self.up_btn = QPushButton('▲')
        self.down_btn = QPushButton('▼')
        button_layout.addWidget(self.transfer_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addWidget(self.up_btn)
        button_layout.addWidget(self.down_btn)

        # List section
        list_layout = QVBoxLayout()

        # Top buttons for List
        list_top_layout = QVBoxLayout()
        self.list_deselect_btn = QPushButton('DESELECT LIST')
        self.list_sort_btn = QPushButton('SORT LIST')
        self.list_renumber_btn = QPushButton('RENUMBER')
        list_top_layout.addWidget(self.list_deselect_btn)
        list_top_layout.addWidget(self.list_sort_btn)
        list_top_layout.addWidget(self.list_renumber_btn)
        list_layout.addLayout(list_top_layout)

        # List table with fixed dimensions
        self.list_table = QTableWidget()
        self.list_table.setColumnCount(6)
        self.list_table.setFixedHeight(550)
        self.list_table.setHorizontalHeaderLabels(['Item Code', 'Item Num',
                                                   'FC_para', 'Mainsub', 'Topic in Book', 'Order'])

        # Set fixed column widths for List table
        self.list_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.list_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)

        # Set exact column widths
        self.list_table.setColumnWidth(0, 140)  # Item Code
        self.list_table.setColumnWidth(1, 80)  # Item Num
        self.list_table.setColumnWidth(2, 80)  # FC_para
        self.list_table.setColumnWidth(3, 80)  # Mainsub
        self.list_table.setColumnWidth(4, 100)  # Topic in Book
        self.list_table.setColumnWidth(5, 0)  # Order (hidden)

        # Calculate and set fixed total width
        total_width = sum([self.list_table.columnWidth(i) for i in range(5)])  # Exclude hidden Order column
        self.list_table.setFixedWidth(550)
        # Hide Order column
        self.list_table.hideColumn(5)

        list_layout.addWidget(self.list_table)

        # Right buttons
        right_button_layout = QVBoxLayout()
        self.book_name_input = QComboBox()
        self.load_book_names()
        self.delete_pdfs_btn = QPushButton('DELETE PDFs As Shown')
        self.create_pdfs_btn = QPushButton('CREATE PDFs As Shown')
        self.export_json_btn = QPushButton('EXPORT JSON to DB')
        self.build_squeeze_paper_by_gui_btn = QPushButton('BUILD squeeze from DB')
        self.rasterize_pdf_btn = QPushButton('RASTERIZE PDF from DB')
        self.open_naive_pdf_btn = QPushButton('OPEN NAIVE PDF')
        self.open_rasterized_pdf_btn = QPushButton('OPEN RASTERIZED PDF')
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)

        right_button_layout.addWidget(self.book_name_input)
        right_button_layout.addWidget(self.delete_pdfs_btn)
        right_button_layout.addWidget(self.create_pdfs_btn)
        right_button_layout.addWidget(self.export_json_btn)
        right_button_layout.addWidget(self.build_squeeze_paper_by_gui_btn)
        right_button_layout.addWidget(self.rasterize_pdf_btn)
        right_button_layout.addWidget(self.open_naive_pdf_btn)
        right_button_layout.addWidget(self.open_rasterized_pdf_btn)

        right_button_layout.addStretch()

        right_button_layout.addWidget(self.log_window)
        self.log_window.setFixedHeight(300)
        # Log window


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
        self.list_sort_btn.clicked.connect(self.sort_list_by_order)
        self.list_renumber_btn.clicked.connect(self.renumber_list_items)

        self.pool_table.horizontalHeader().sectionClicked.connect(self.show_filter_dialog)
        self.list_table.horizontalHeader().sectionClicked.connect(self.sort_list)

        self.book_name_input.currentIndexChanged.connect(self.load_selected_book)
        self.delete_pdfs_btn.clicked.connect(self.delete_pdfs_gui)
        self.create_pdfs_btn.clicked.connect(self.create_pdfs_gui)
        self.export_json_btn.clicked.connect(self.export_to_json)
        self.build_squeeze_paper_by_gui_btn.clicked.connect(self.build_squeeze_paper_by_gui)
        self.rasterize_pdf_btn.clicked.connect(self.rasterize_pdf_by_gui)
        self.open_naive_pdf_btn.clicked.connect(self.open_naive_pdf)
        self.open_rasterized_pdf_btn.clicked.connect(self.open_rasterized_pdf)


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
            for col in range(self.list_table.columnCount() - 1):  # order 컬럼 제외
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
        if obj in [self.pool_table, self.list_table]:
            if event.type() == event.KeyPress and event.key() == Qt.Key_Shift:
                obj.setSelectionMode(QTableWidget.MultiSelection)
                obj.setSelectionBehavior(QTableWidget.SelectRows)
            elif event.type() == event.KeyRelease and event.key() == Qt.Key_Shift:
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

        # Load from KICE_DB_PATH
        for folder in os.listdir(KICE_DB_PATH):
            folder_path = os.path.join(KICE_DB_PATH, folder)
            if os.path.isdir(folder_path):
                for subfolder in os.listdir(folder_path):
                    if len(subfolder) == 13 and is_valid_item(folder_path, subfolder, original_pdf=True):
                        parsed = self.parse_code(subfolder)
                        order = parsed["topic"] + parsed["section"] + parsed["number"] + parsed["subject"]
                        self.pool_data.append({
                            'item_code': subfolder,
                            'topic': parsed["topic"],
                            'order': order
                        })
                        serial_num += 1

        # Load from ITEM_DB_PATH
        for folder in os.listdir(ITEM_DB_PATH):
            folder_path = os.path.join(ITEM_DB_PATH, folder)
            if os.path.isdir(folder_path):
                for subfolder in os.listdir(folder_path):
                    if len(subfolder) == 13 and is_valid_item(folder_path, subfolder, original_pdf=False):
                        parsed = self.parse_code(subfolder)
                        order = parsed["topic"] + parsed["section"] + parsed["number"] + parsed["subject"]
                        self.pool_data.append({
                            'item_code': subfolder,
                            'topic': parsed["topic"],
                            'order': order
                        })
                        serial_num += 1

        self.update_pool_table()

    def update_pool_table(self, data=None):
        if data is None:
            data = self.pool_data
        self.pool_table.setRowCount(len(data))
        for i, item in enumerate(data):
            item_code = item['item_code']
            item_code_item = QTableWidgetItem(item_code)

            if parse_code(item_code)["section"] == "KC" and item_code not in self.kice_topics:
                item_code_item.setBackground(QColor('pink'))
            if parse_code(item_code)["section"] == "KC" and item_code in self.kice_topics:
                item_code_item.setBackground(QColor('lightgreen'))
            if parse_code(item_code)["section"] != "KC":
                item_code_item.setBackground(QColor('lightblue'))

            self.pool_table.setItem(i, 0, item_code_item)
            self.pool_table.setItem(i, 1, QTableWidgetItem(item['topic']))
            self.pool_table.setItem(i, 2, QTableWidgetItem(str(item['order'])))

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
                self.list_table.setItem(current_row, 2, QTableWidgetItem(""))
                self.list_table.setItem(current_row, 3, QTableWidgetItem(""))
                self.list_table.setItem(current_row, 4, QTableWidgetItem(parsed["topic"]))
                self.list_table.setItem(current_row, 5, QTableWidgetItem(order))

    def add_empty_row(self):
        current_row = self.list_table.rowCount()
        self.list_table.insertRow(current_row)

        self.list_table.setItem(current_row, 0, QTableWidgetItem(str(current_row + 1)))
        for i in range(1, 6):
            self.list_table.setItem(current_row, i, QTableWidgetItem(""))

    def sort_pool_by_order(self):
        # Get currently displayed items
        current_items = []
        for row in range(self.pool_table.rowCount()):
            item_code = self.pool_table.item(row, 0).text()
            topic = self.pool_table.item(row, 1).text()
            order = self.pool_table.item(row, 2).text()
            current_items.append({'item_code': item_code, 'topic': topic, 'order': order})

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
        if column == 1:  # Item Num column
            data.sort(key=lambda x: float('inf') if not x[column] else int(x[column]), reverse=reverse)
        else:
            data.sort(key=lambda x: x[column], reverse=reverse)

        for i, row_data in enumerate(data):
            for j, cell_data in enumerate(row_data):
                self.list_table.setItem(i, j, QTableWidgetItem(cell_data))

    def order_column(self, item_code):
        parsed = self.parse_code(item_code)
        order = parsed["topic"] + parsed["section"] + parsed["number"] + parsed["subject"]
        return order

    def sort_list_by_order(self):
        if not self.show_warning_dialog("Are you sure you want to sort the list by order?"):
            return

        # Extract all data from the table
        data = []
        for row in range(self.list_table.rowCount()):
            row_data = {
                'item_code': self.list_table.item(row, 0).text() if self.list_table.item(row, 0) else "",
                'item_num': self.list_table.item(row, 1).text() if self.list_table.item(row, 1) else "",
                'fc_para': self.list_table.item(row, 2).text() if self.list_table.item(row, 2) else "",
                'mainsub': self.list_table.item(row, 3).text() if self.list_table.item(row, 3) else "",
                'topic_in_book': self.list_table.item(row, 4).text() if self.list_table.item(row, 4) else "",
                'order': self.list_table.item(row,4).text() + parse_code(self.list_table.item(row, 0).text())["section"] +
                parse_code(self.list_table.item(row, 0).text())["number"] + parse_code(self.list_table.item(row, 0).text())["subject"]
            }
            data.append(row_data)

        # Sort data by order
        data.sort(key=lambda x: x['order'])

        # Update table with sorted data and reassign order values
        self.list_table.setRowCount(0)
        for idx, row_data in enumerate(data):
            row_count = self.list_table.rowCount()
            self.list_table.insertRow(row_count)
            self.list_table.setItem(row_count, 0, QTableWidgetItem(row_data['item_code']))
            self.list_table.setItem(row_count, 1, QTableWidgetItem(row_data['item_num']))
            self.list_table.setItem(row_count, 2, QTableWidgetItem(row_data['fc_para']))
            self.list_table.setItem(row_count, 3, QTableWidgetItem(row_data['mainsub']))
            self.list_table.setItem(row_count, 4, QTableWidgetItem(row_data['topic_in_book']))
            self.list_table.setItem(row_count, 5, QTableWidgetItem(str(idx + 1)))  # Update order column

    # Add a similar method for the list table
    def update_list_table(self, data=None):
        if data is None:
            data = self.list_data
        self.list_table.setRowCount(len(data))
        for i, item in enumerate(data):
            item_code = item['item_code']

            # 색상 결정
            if parse_code(item_code)["section"] == "KC":
                if parse_item_caption_path(item_code):
                    row_color = QColor('lightgreen')
                else:
                    row_color = QColor('pink')
            else:
                row_color = QColor('lightblue')

            # 각 컬럼의 아이템 생성 및 색상 설정
            item_code_item = QTableWidgetItem(item_code)
            item_code_item.setBackground(row_color)
            self.list_table.setItem(i, 0, item_code_item)

            # 나머지 컬럼들도 같은 색상 적용
            columns = [
                str(item.get('item_num', '')),
                str(item.get('FC_para', '')),
                str(item.get('mainsub', '')),
                str(item.get('topic_in_book', '')),
                str(item.get('order', ''))
            ]

            for col, value in enumerate(columns, 1):  # 1부터 시작해서 나머지 컬럼 처리
                table_item = QTableWidgetItem(value)
                table_item.setBackground(row_color)
                self.list_table.setItem(i, col, table_item)

    def show_filter_dialog(self, column):
        if column == 1:  # Topic column
            dialog = FilterDialog(self)
            dialog.exec_()

    def renumber_list_items(self):
        if not self.show_warning_dialog("Are you sure you want to renumber the list items?"):
            return
        next_item_number = 1
        next_main_number = 1
        for i in range(self.list_table.rowCount()):
            section = parse_code(self.list_table.item(i, 0).text())["section"]
            item_num = self.list_table.item(i, 1)
            main_num = self.list_table.item(i, 3)

            # 비어있지 않은 경우에만 번호 매기기
            if section == "KC":
                self.list_table.setItem(i, 1, QTableWidgetItem(str(next_item_number)))
                next_item_number += 1
            # -1과 0은 그대로 유지
            if section != "KC":
                self.list_table.setItem(i, 3, QTableWidgetItem(chr(next_main_number+64)))
                next_main_number += 1

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
                pdf_path = parse_item_pdf_path(item_code)
                Main_path = parse_item_Main_path(item_code)
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

    def create_pdfs_gui(self):
        if not self.show_warning_dialog("Are you sure you want to create PDFs?"):
            return
        item_list = []
        for row in range(self.list_table.rowCount()):
            item_code = self.list_table.item(row, 0).text() if self.list_table.item(row, 0) else None
            item_list.append(item_code)
        self.log_message("Starting PDF creation...")

        self.pdf_thread = PDFCreationThread(item_list)
        self.pdf_thread.progress_signal.connect(self.log_message)
        self.pdf_thread.start()
    # Sort ComboBox Options
    def load_book_names(self):
        self.book_name_input.clear()
        book_names = [file_name for file_name in os.listdir(BOOK_DB_PATH) if file_name.endswith('.json')]
        book_names.sort()  # Sort book names in ascending order
        self.book_name_input.addItems(book_names)

    def load_selected_book(self):
        book_name = self.book_name_input.currentText()
        book_path = os.path.join(BOOK_DB_PATH, book_name)

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
                    # order 값 생성
                    parsed = self.parse_code(item_code)
                    order = parsed["topic"] + parsed["section"] + parsed["number"] + parsed["subject"]
                    self.list_table.setItem(row_count, 5, QTableWidgetItem(order))

                if row_data.get('item_num') is not None:
                    self.list_table.setItem(row_count, 1, QTableWidgetItem(str(row_data['item_num'])))

                if row_data.get('FC_para') is not None:
                    self.list_table.setItem(row_count, 2, QTableWidgetItem(str(row_data['FC_para'])))

                if row_data.get('mainsub') is not None:
                    self.list_table.setItem(row_count, 3, QTableWidgetItem(str(row_data['mainsub'])))

                if row_data.get('topic_in_book') is not None:
                    self.list_table.setItem(row_count, 4, QTableWidgetItem(str(row_data['topic_in_book'])))

        except Exception as e:
            self.log_message(f"Error loading book: {e}")

    def export_to_json(self):
        if not self.show_warning_dialog("Are you sure you want to export to JSON?"):
            return

        book_name = self.book_name_input.currentText()
        data = []

        # 컬럼과 JSON 키 매핑
        column_mapping = {
            0: 'item_code',  # 첫 번째 컬럼은 item_code
            1: 'item_num',  # 두 번째 컬럼은 item_num
            2: 'FC_para',  # 세 번째 컬럼은 FC_para
            3: 'mainsub',  # 네 번째 컬럼은 mainsub
            4: 'topic_in_book'  # 다섯 번째 컬럼은 topic_in_book
        }

        # JSON에서 원하는 키 순서
        json_order = ['item_num', 'item_code', 'FC_para', 'mainsub', 'topic_in_book']

        for row in range(self.list_table.rowCount()):
            temp_data = {}
            # 먼저 테이블에서 데이터 추출
            for col, key in column_mapping.items():
                item = self.list_table.item(row, col)
                if item is not None and item.text().strip():
                    if key in ['FC_para', 'item_num']:
                        temp_data[key] = int(item.text())
                    else:
                        temp_data[key] = item.text()
                else:
                    temp_data[key] = None

            # 원하는 순서로 데이터 재구성
            row_data = {key: temp_data[key] for key in json_order}
            data.append(row_data)

        self.log_message("Starting JSON export...")
        try:
            with open(os.path.join(BOOK_DB_PATH, book_name), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.log_message("JSON export completed successfully.")
        except Exception as e:
            self.log_message(f"Error during JSON export: {e}")

    def build_squeeze_paper_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to build the squeeze paper?"):
            return
        if not self.show_warning_dialog("Please Ensure that Every PDF file is Updated"):
            return
        book_name = self.book_name_input.currentText()
        input_path = os.path.join(BOOK_DB_PATH, book_name)
        output_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '.pdf'))
        self.log_message("Starting squeeze paper build...")
        try:
            build_squeeze_paper(input=input_path, output=output_path, log_callback=self.log_message)
        except Exception as e:
            error_message = f"Error during squeeze paper build: {e}\n{traceback.format_exc()}"
            self.log_message(error_message)

    def rasterize_pdf_by_gui(self):
        if not self.show_warning_dialog("Are you sure you want to rasterize the PDF?"):
            return
        book_name = self.book_name_input.currentText()
        self.log_message("Starting PDF rasterization...")
        try:
            add_watermark_and_rasterize(os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '.pdf'),
                                        os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_R.pdf'))
            self.log_message("PDF rasterization completed successfully.")
        except Exception as e:
            self.log_message(f"Error during PDF rasterization: {e}")

    def open_naive_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.replace('.json', '.pdf'))
        if os.path.exists(pdf_path):
            try:
                os.startfile(pdf_path)
                self.log_message(f"Opened PDF: {pdf_path}")
            except Exception as e:
                self.log_message(f"Error opening PDF: {e}")
        else:
            self.log_message(f"PDF not found: {pdf_path}")

    def open_rasterized_pdf(self):
        book_name = self.book_name_input.currentText()
        pdf_path = os.path.join(OUTPUT_PATH, book_name.split('.')[0] + '_R.pdf')
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

    def show_context_menu(self, pos):
        sender = self.sender()
        row = sender.rowAt(pos.y())

        if row >= 0:
            item_code = sender.item(row, 0).text()
            menu = QMenu()
            open_hwp_action = menu.addAction("Open item HWP")
            open_folder_action = menu.addAction("Open Folder")
            refractor_action = menu.addAction("Refractor Item Code")
            action = menu.exec_(sender.mapToGlobal(pos))
            if action == open_folder_action:
                self.open_item_folder(item_code)
            elif action == refractor_action:
                self.refractor_item_code(item_code)
            elif action == open_hwp_action:
                self.open_item_hwp(item_code)

    def open_item_hwp(self, item_code):
        # Base folder selection
        base_path = KICE_DB_PATH if item_code[5:7] == 'KC' else ITEM_DB_PATH
        topic = item_code[2:5]

        # Construct and normalize path
        hwp_path = os.path.normpath(os.path.join(base_path, topic, item_code, f"{item_code}.hwp"))

        if os.path.exists(hwp_path):
            try:
                os.startfile(hwp_path)
            except Exception as e:
                print(f"Error: {e}")

    def open_item_folder(self, item_code):
        # Base folder selection
        base_path = KICE_DB_PATH if item_code[5:7] == 'KC' else ITEM_DB_PATH
        topic = item_code[2:5]

        # Construct and normalize path
        folder_path = os.path.normpath(os.path.join(base_path, topic, item_code))

        if os.path.exists(folder_path):
            if os.name == 'nt':
                try:
                    subprocess.run(['explorer', folder_path], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")

    def refractor_item_code(self, item_code):
        try:
            new_code, ok = QInputDialog.getText(self, 'Refractor Item Code',
                                                f'Enter new 13-character item code'
                                                f'\nOriginal = {item_code}'
                                                f'\nInput Below:')

            if ok and len(new_code) == 13:
                # 원본 코드의 정보 파싱
                old_base_path = KICE_DB_PATH if item_code[5:7] == 'KC' else ITEM_DB_PATH
                old_topic = item_code[2:5]
                old_topic_path = os.path.join(old_base_path, old_topic)
                old_item_path = os.path.join(old_topic_path, item_code)

                # 새 코드의 정보 파싱
                new_base_path = KICE_DB_PATH if new_code[5:7] == 'KC' else ITEM_DB_PATH
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

            else:
                if ok:  # 사용자가 OK를 눌렀지만 코드 길이가 잘못된 경우
                    QMessageBox.warning(self, 'Error',
                                        'The new item code must be exactly 13 characters long.')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An unexpected error occurred: {str(e)}')

    def eventFilter(self, obj, event):
        if obj in [self.pool_table, self.list_table]:
            if event.type() == event.KeyPress:
                if event.key() == Qt.Key_Shift:
                    obj.setSelectionMode(QTableWidget.MultiSelection)
                    obj.setSelectionBehavior(QTableWidget.SelectRows)
                elif event.key() == Qt.Key_Escape:
                    if self.pool_table.hasFocus():
                        self.deselect_pool_items()
                    elif self.list_table.hasFocus():
                        self.deselect_list_items()
                elif event.key() == Qt.Key_Delete:
                    if self.list_table.hasFocus():
                        self.remove_selected_rows()
                elif event.key() == Qt.Key_Backspace:
                    if self.list_table.hasFocus():
                        self.remove_selected_rows()
            elif event.type() == event.KeyRelease and event.key() == Qt.Key_Shift:
                obj.setSelectionMode(QTableWidget.NoSelection)
        return super().eventFilter(obj, event)


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

        topics = {key: f"{key} : {value}" for key, value in topics_data.items()}

        # 상단 버튼들
        top_buttons = QHBoxLayout()
        select_all_btn = QPushButton('Select All')
        select_none_btn = QPushButton('Select None')
        apply_btn = QPushButton('Apply Filter')
        top_buttons.addWidget(select_all_btn)
        top_buttons.addWidget(select_none_btn)
        top_buttons.addWidget(apply_btn)
        layout.addLayout(top_buttons)

        # 메인 그리드 레이아웃
        self.checkboxes = []
        self.category_checkboxes = {}
        main_layout = QHBoxLayout()  # 수평 레이아웃으로 변경

        # 왼쪽 카테고리 버튼들을 위한 레이아웃
        category_layout = QVBoxLayout()
        stretch_factors = [1, 2, 1, 2, 1, 1, 2, 2, 2, 2, 1, 1, 2, 1, 1, 1]
        title_factors = ['고체1', '고체2', '고체3', '고체4', '고체5',
                         '유체1', '유체2', '유체3', '유체4', '유체5',
                         '천체1', '천체2', '천체3', '천체4', '천체5', '천체6']

        # 오른쪽 체크박스들을 위한 그리드 레이아웃
        checkbox_grid = QGridLayout()

        grouped_topics = self.group_topics_by_category(topics)
        current_row = 0

        for i, (category, group) in enumerate(grouped_topics.items()):
            # 카테고리 버튼은 왼쪽 레이아웃에 추가
            category_btn = QPushButton(title_factors[i] + ': ' + category)
            category_layout.addWidget(category_btn)
            category_layout.setStretch(i, stretch_factors[i])

            self.category_checkboxes[category] = []

            # 체크박스들은 오른쪽 그리드에 4열로 배치
            count = 0
            for key, display_text in group:
                cb = QCheckBox(display_text)
                cb.setChecked(False)
                self.checkboxes.append(cb)
                self.category_checkboxes[category].append(cb)
                checkbox_grid.addWidget(cb, current_row, count)
                count += 1
                if count >= 4:  # 4열로 변경
                    current_row += 1
                    count = 0

            if count > 0:  # 마지막 행이 4개 미만일 경우 다음 행으로
                current_row += 1

            # 카테고리 버튼 클릭 이벤트
            category_btn.clicked.connect(lambda checked, cat=category: self.toggle_category(cat))

        # 카테고리 레이아웃을 왼쪽에 배치
        category_widget = QWidget()
        category_widget.setLayout(category_layout)
        category_widget.setFixedWidth(150)  # 적절한 너비 설정
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

    def group_topics_by_category(self, topics):
        grouped_topics = {}
        for key, value in topics.items():
            category = value[0]
            if category in grouped_topics:
                grouped_topics[category].append((key, value))
            else:
                grouped_topics[category] = [(key, value)]
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