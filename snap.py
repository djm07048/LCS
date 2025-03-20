import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QScrollArea)
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QMouseEvent, QFontDatabase
import random


class Object:
    def __init__(self, id, rect, activated=False, column=None, order=None):
        self.id = id
        self.rect = rect
        self.activated = activated
        self.column = column
        self.order = order
        # Random color will be assigned in init_objects
        self.color = QColor(255, 200, 100)  # Default color for objects
        self.is_dragging = False
        self.drag_offset = QPoint()

    def contains(self, point):
        return self.rect.contains(point)

    def draw(self, painter):
        # Draw with rounded corners for a nicer look
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(Qt.black, 2))

        # Draw rounded rectangle
        painter.drawRoundedRect(self.rect, 10, 10)

        # Draw the object number in the center only if activated
        if self.activated:
            # Create a contrasting color for text based on background brightness
            brightness = (self.color.red() * 299 + self.color.green() * 587 + self.color.blue() * 114) / 1000
            text_color = QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255)

            painter.setFont(QFont('Arial', 12, QFont.Bold))
            painter.setPen(QPen(text_color))
            painter.drawText(self.rect, Qt.AlignCenter, str(self.id))


class Column:
    def __init__(self, name, rect):
        self.name = name
        self.rect = rect
        self.color = QColor(200, 200, 255, 100)  # Light blue with transparency
        self.objects = []  # Objects in this column

    def contains(self, point):
        return self.rect.contains(point)

    def draw(self, painter):
        # Draw with a solid fill to prevent transparency artifacts
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(self.rect)

        # Draw column name
        painter.setFont(QFont('Arial', 10))
        painter.drawText(self.rect.left() + 5, self.rect.top() + 15, self.name)


class ObjectManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)

        # Set fixed column width
        self.fixed_column_width = 100  # Fixed width for each column in pixels

        # Initialize columns
        self.columns = []
        self.init_columns()

        # Initialize objects
        self.objects = []
        self.init_objects()

        # Set dragging variables
        self.dragging_object = None
        self.start_drag_pos = QPoint()

        # Object numbering dictionary
        self.object_numbering = {}
        self.update_object_numbering()

        # Setup UI
        self.setMouseTracking(True)

    def init_columns(self):
        # Clear old columns first
        self.columns = []

        # Define column dimensions
        column_height = 500  # 고정된 높이 (픽셀)

        # Create 8 columns (1L, 1R, 2L, 2R, 3L, 3R, 4L, 4R) with fixed width
        column_names = ["1L", "1R", "2L", "2R", "3L", "3R", "4L", "4R"]

        for i, name in enumerate(column_names):
            x = i * self.fixed_column_width
            y = 0
            rect = QRect(x, y, self.fixed_column_width, column_height)
            self.columns.append(Column(name, rect))

    def init_objects(self):
        # Create some initial objects in the unactivated area with varying heights and colors
        object_width = 80
        unactivated_area_y = int(self.height() * 0.7) if self.height() > 0 else 450
        unactivated_area_height = int(self.height() * 0.3) if self.height() > 0 else 150

        # Define a variety of colors
        colors = [
            QColor(255, 200, 100),  # Original orange
            QColor(100, 200, 255),  # Light blue
            QColor(255, 150, 150),  # Light red
            QColor(150, 255, 150),  # Light green
            QColor(200, 150, 255),  # Light purple
            QColor(255, 255, 150),  # Light yellow
            QColor(150, 255, 200),  # Mint
            QColor(255, 180, 180)  # Pink
        ]

        # Calculate spacing to distribute objects evenly
        total_width = self.width()
        objects_count = 10
        padding = 20  # Horizontal padding between objects

        # Calculate the total width needed for all objects with padding
        total_objects_width = objects_count * object_width + (objects_count - 1) * padding

        # Calculate the starting x position to center the objects
        start_x = (total_width - total_objects_width) // 2

        for i in range(10):  # Create 10 initial objects
            # Randomize height between 40 and 80 pixels
            object_height = 40 + (i % 5) * 10  # Heights: 40, 50, 60, 70, 80 pixels

            # Choose color based on index (distribute colors evenly)
            color = colors[i % len(colors)]

            # Calculate x position with even spacing
            x = start_x + (i * (object_width + padding))
            y = unactivated_area_y

            rect = QRect(x, y, object_width, object_height)

            # Create object with the specific height and color
            obj = Object(i + 1, rect)
            obj.color = color
            self.objects.append(obj)


    def update_object_numbering(self):
        # Sort objects by column and then by order within column
        activated_objects = [obj for obj in self.objects if obj.activated]
        unactivated_objects = [obj for obj in self.objects if not obj.activated]

        # Sort activated objects by column name and then by order
        activated_objects.sort(key=lambda o: (
            self.get_column_index(o.column),
            o.order if o.order is not None else 0
        ))

        # Renumber all objects
        self.object_numbering = {}
        counter = 1

        # Number activated objects only
        for obj in activated_objects:
            obj.id = counter
            self.object_numbering[counter] = f"Object {counter}"
            counter += 1

        # Print debug info
        print("Object numbering updated:")
        for obj in activated_objects:
            print(f"Object {obj.id}: column={obj.column}, order={obj.order}, activated={obj.activated}")

    def get_column_index(self, column_name):
        for i, col in enumerate(self.columns):
            if col.name == column_name:
                return i
        return -1

    def get_column_by_name(self, name):
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def get_column_at_point(self, point):
        for col in self.columns:
            if col.contains(point):
                return col
        return None

    def adjust_objects_position(self):
        # 각 컬럼의 객체 위치 조정
        for column in self.columns:
            objects_in_column = [obj for obj in self.objects if obj.activated and obj.column == column.name]

            if not objects_in_column:
                continue

            # 순서대로 객체 정렬
            objects_in_column.sort(key=lambda o: o.order if o.order is not None else 0)

            # 컬럼 크기 정의
            column_width = column.rect.width()
            column_height = column.rect.height()
            total_objects = len(objects_in_column)

            if total_objects == 1:
                # 하나의 객체만 있을 때는 중앙 정렬
                obj = objects_in_column[0]
                # 수평 중앙 정렬
                obj_width = obj.rect.width()
                center_x = column.rect.left() + (column_width - obj_width) // 2
                # 수직 중앙 정렬 (또는 원하는 위치)
                obj.rect.moveLeft(center_x)
                obj.rect.moveTop(column.rect.top() + 20)  # 상단에서 약간 여백 추가
                obj.order = 0  # 순서 설정
            else:
                # 여러 객체가 있을 경우
                # 객체들의 총 높이 계산
                total_object_height = sum(obj.rect.height() for obj in objects_in_column)

                # 객체 간 간격 계산
                available_height = column_height - total_object_height - 40  # 상하 여백 40px
                spacing = available_height // (total_objects - 1) if total_objects > 1 else 0

                # 계산된 간격으로 각 객체 배치
                current_y = column.rect.top() + 20  # 상단 여백 시작

                for i, obj in enumerate(objects_in_column):
                    # 수평 중앙 정렬
                    obj_width = obj.rect.width()
                    center_x = column.rect.left() + (column_width - obj_width) // 2
                    obj.rect.moveLeft(center_x)

                    # 마지막 객체인 경우 컬럼 하단을 넘지 않도록 조정
                    if i == total_objects - 1:
                        bottom_pos = column.rect.bottom() - 20  # 하단 여백
                        if obj.rect.height() + current_y > bottom_pos:
                            current_y = bottom_pos - obj.rect.height()

                    # 드래그 중인 객체는 이동하지 않음
                    if hasattr(obj, 'is_dragging') and obj.is_dragging:
                        continue

                    obj.rect.moveTop(current_y)
                    current_y += obj.rect.height() + spacing

    def transfer_object(self, obj, release_point):
        target_column = self.get_column_at_point(release_point)

        if obj.activated:
            # 이미 활성화된 객체인 경우
            if target_column is None:
                # Case 1: 비활성화 - 컬럼 밖으로 드롭
                obj.activated = False
                obj.column = None
                obj.order = None

            elif target_column.name == obj.column:
                # Case 2: 같은 컬럼 내 이동
                objects_in_column = [o for o in self.objects if
                                     o.activated and o.column == target_column.name and o != obj]

                if not objects_in_column:
                    # 컬럼 내 유일한 객체인 경우
                    obj.order = 0
                else:
                    # 드래그한 객체의 현재 순서
                    original_order = obj.order

                    # 다른 객체들을 순서대로 정렬
                    objects_in_column.sort(key=lambda o: o.order if o.order is not None else 0)

                    # 마우스 위치에 따른 목표 위치 찾기
                    target_position = -1
                    for i, other_obj in enumerate(objects_in_column):
                        if release_point.y() < other_obj.rect.center().y():
                            target_position = i
                            break

                    if target_position == -1:  # 목표 위치를 찾지 못했다면 맨 끝에 배치
                        target_position = len(objects_in_column)

                    # 순서 업데이트 - 스마트폰 스타일 재정렬
                    if original_order < target_position:
                        # 아래로 이동 - 기존 위치와 새 위치 사이의 객체들은 위로 이동
                        for o in objects_in_column:
                            if original_order < o.order <= target_position:
                                o.order -= 1
                        obj.order = target_position
                    elif original_order > target_position:
                        # 위로 이동 - 새 위치와 기존 위치 사이의 객체들은 아래로 이동
                        for o in objects_in_column:
                            if target_position <= o.order < original_order:
                                o.order += 1
                        obj.order = target_position

            else:
                # Case 3: Intercolumn transfer - 다른 컬럼으로 이동
                new_column = target_column
                old_column_name = obj.column
                original_order = obj.order

                # 새 컬럼에 이미 3개의 객체가 있는지 확인
                objects_in_new_column = [o for o in self.objects if o.activated and o.column == new_column.name]
                objects_in_old_column = [o for o in self.objects if
                                         o.activated and o.column == old_column_name and o != obj]

                # 스왑이 필요한지 확인
                if len(objects_in_new_column) >= 3:
                    # 가장 가까운 객체와 스왑
                    # Y좌표 기준으로 가장 가까운 객체 찾기
                    objects_in_new_column.sort(key=lambda o: abs(o.rect.center().y() - release_point.y()))
                    object_to_swap = objects_in_new_column[0]  # 가장 가까운 객체

                    # 스왑할 객체의 원래 위치 저장
                    swap_original_column = object_to_swap.column
                    swap_original_order = object_to_swap.order

                    # 스왑할 객체를 드래그한 객체의 출발 위치로 이동
                    object_to_swap.column = old_column_name
                    object_to_swap.order = original_order

                    # 드래그한 객체를 새 컬럼으로 이동
                    obj.column = new_column.name

                    # 새 컬럼에서 순서 결정
                    remaining_objects = [o for o in objects_in_new_column if o != object_to_swap]

                    # Y 좌표에 따른 위치 결정
                    target_position = -1
                    for i, other_obj in enumerate(sorted(remaining_objects, key=lambda o: o.order)):
                        if release_point.y() < other_obj.rect.center().y():
                            target_position = i
                            break

                    if target_position == -1:
                        target_position = len(remaining_objects)

                    # 새 순서 할당
                    obj.order = target_position

                    # 삽입 지점 이후 객체들의 순서 조정
                    for o in remaining_objects:
                        if o.order >= target_position:
                            o.order += 1

                    # 이전 컬럼의 객체들 재정렬
                    if objects_in_old_column:
                        objects_in_old_column.sort(key=lambda o: o.order if o.order is not None else 0)
                        for i, o in enumerate(objects_in_old_column):
                            o.order = i

                elif len(objects_in_new_column) < 3:
                    # 스왑 불필요, 객체 컬럼 업데이트
                    obj.column = new_column.name

                    # 새 컬럼에서 순서 결정
                    objects_in_new_column.sort(key=lambda o: o.order if o.order is not None else 0)

                    # Y 좌표에 따른 목표 위치 찾기
                    target_position = -1
                    for i, other_obj in enumerate(objects_in_new_column):
                        if release_point.y() < other_obj.rect.center().y():
                            target_position = i
                            break

                    if target_position == -1:
                        target_position = len(objects_in_new_column)

                    # 새 순서 할당
                    obj.order = target_position

                    # 삽입 지점 이후 객체들의 순서 조정
                    for o in objects_in_new_column:
                        if o.order >= target_position:
                            o.order += 1

                    # 이전 컬럼의 객체들 재정렬
                    if objects_in_old_column:
                        objects_in_old_column.sort(key=lambda o: o.order if o.order is not None else 0)
                        for i, o in enumerate(objects_in_old_column):
                            o.order = i

        else:
            # 비활성화된 객체인 경우
            if target_column is not None:
                # Case 4: 활성화 - 비활성화된 객체가 컬럼에 드롭됨
                new_column = target_column

                # 새 컬럼에 이미 3개의 객체가 있는지 확인
                objects_in_new_column = [o for o in self.objects if o.activated and o.column == new_column.name]

                if len(objects_in_new_column) >= 3:
                    # 가장 가까운 객체와 스왑해야 함
                    # Y 좌표 기준으로 가장 가까운 객체 찾기
                    objects_in_new_column.sort(key=lambda o: abs(o.rect.center().y() - release_point.y()))
                    object_to_swap = objects_in_new_column[0]  # 가장 가까운 객체

                    # 스왑할 객체를 비활성화하고 드래그한 객체의 원래 위치로 이동
                    object_to_swap.activated = False
                    object_to_swap.column = None
                    object_to_swap.order = None

                    # 드래그한 객체 활성화 및 새 컬럼에 배치
                    obj.activated = True
                    obj.column = new_column.name

                    # 새 컬럼에서 위치 결정
                    remaining_objects = [o for o in objects_in_new_column if o != object_to_swap]

                    # Y 좌표에 따른 위치 결정
                    target_position = -1
                    for i, other_obj in enumerate(sorted(remaining_objects, key=lambda o: o.order)):
                        if release_point.y() < other_obj.rect.center().y():
                            target_position = i
                            break

                    if target_position == -1:
                        target_position = len(remaining_objects)

                    # 새 순서 할당
                    obj.order = target_position

                    # 삽입 지점 이후 객체들의 순서 조정
                    for o in remaining_objects:
                        if o.order >= target_position:
                            o.order += 1

                else:
                    # 스왑 불필요, 객체 활성화
                    obj.activated = True
                    obj.column = new_column.name

                    # 새 컬럼에서 순서 결정
                    objects_in_new_column.sort(key=lambda o: o.order if o.order is not None else 0)

                    # Y 좌표에 따른 위치 찾기
                    target_position = -1
                    for i, other_obj in enumerate(objects_in_new_column):
                        if release_point.y() < other_obj.rect.center().y():
                            target_position = i
                            break

                    if target_position == -1:
                        target_position = len(objects_in_new_column)

                    # 새 순서 할당
                    obj.order = target_position

                    # 삽입 지점 이후 객체들의 순서 조정
                    for o in objects_in_new_column:
                        if o.order >= target_position:
                            o.order += 1

    def paintEvent(self, event):
        painter = QPainter(self)

        # Enable antialiasing for smoother drawing
        painter.setRenderHint(QPainter.Antialiasing)

        # Clear the entire widget area first to prevent artifacts
        painter.fillRect(self.rect(), QColor(240, 240, 240))

        # Calculate the total width needed for all columns
        total_columns_width = len(self.columns) * self.fixed_column_width

        # Draw columns
        for column in self.columns:
            # Only draw columns if they are visible in the viewport
            if column.rect.right() >= 0 and column.rect.left() <= self.width():
                column.draw(painter)

        # Draw unactivated area
        unactivated_area = QRect(0, int(self.height() * 0.7), self.width(), int(self.height() * 0.3))
        painter.setBrush(QBrush(QColor(220, 220, 220)))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(unactivated_area)
        painter.drawText(10, int(self.height() * 0.7) + 20, "Unactivated Objects Area")

        # Draw objects
        for obj in self.objects:
            if obj != self.dragging_object:  # Don't draw the object being dragged here
                # Only draw objects that are visible in the viewport
                if obj.rect.right() >= 0 and obj.rect.left() <= self.width():
                    obj.draw(painter)

        # Draw the dragging object on top
        if self.dragging_object:
            self.dragging_object.draw(painter)

        # Ensure painter is ended properly
        painter.end()

    def resizeEvent(self, event):
        # Recalculate column dimensions on resize
        old_columns = self.columns.copy()
        self.columns = []  # Clear current columns
        self.init_columns()

        # Update object positions based on new column positions
        for i, obj in enumerate(self.objects):
            if obj.activated and obj.column:
                # Find the matching new column
                for new_col in self.columns:
                    if obj.column == new_col.name:
                        # Keep the same relative position in the new column
                        obj.rect.moveLeft(new_col.rect.left())

        # Completely adjust all object positions
        self.adjust_objects_position()

        # Force a complete repaint
        self.update()

        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Check if we're clicking on an object
            for obj in reversed(self.objects):  # Check from top to bottom
                if obj.contains(event.pos()):
                    self.dragging_object = obj
                    self.dragging_object.is_dragging = True
                    self.dragging_object.drag_offset = event.pos() - obj.rect.topLeft()
                    self.start_drag_pos = event.pos()

                    # Move the dragging object to the end of the list so it's drawn on top
                    self.objects.remove(obj)
                    self.objects.append(obj)
                    break

    def mouseMoveEvent(self, event):
        if self.dragging_object and self.dragging_object.is_dragging:
            # Move the object with the mouse
            new_pos = event.pos() - self.dragging_object.drag_offset

            # Constrain horizontal position within the widget
            new_pos.setX(max(0, min(new_pos.x(), self.width() - self.dragging_object.rect.width())))

            # Constrain vertical position within the widget
            new_pos.setY(max(0, min(new_pos.y(), self.height() - self.dragging_object.rect.height())))

            self.dragging_object.rect.moveTopLeft(new_pos)

            # Dynamic reordering during drag (preview effect)
            if self.dragging_object.activated:
                current_column = self.get_column_at_point(event.pos())
                if current_column and current_column.name == self.dragging_object.column:
                    # We're dragging within the same column - do a live preview reordering
                    objects_in_column = [o for o in self.objects if
                                         o.activated and
                                         o.column == current_column.name and
                                         o != self.dragging_object]

                    if objects_in_column:
                        # Get current order of dragged object
                        original_order = self.dragging_object.order

                        # Find where the dragged object would be inserted
                        target_position = -1
                        for i, other_obj in enumerate(sorted(objects_in_column, key=lambda o: o.order)):
                            if event.pos().y() < other_obj.rect.center().y():
                                target_position = i
                                break

                        if target_position == -1:  # If we didn't find a position, it would go at the end
                            target_position = len(objects_in_column)

                        # Calculate temporary positions for smooth animation
                        column_height = current_column.rect.height()
                        object_height = self.dragging_object.rect.height()

                        # Calculate spacing between objects
                        available_height = column_height - (
                                    len(objects_in_column) + 1) * object_height - 40  # 40px for padding
                        spacing = available_height // (len(objects_in_column)) if len(objects_in_column) > 0 else 0

                        # Update objects - simulate the move without actually changing orders
                        temp_positions = {}

                        # Determine which objects need to move
                        if original_order < target_position:
                            # Moving downward - objects between old and new position move up
                            for o in objects_in_column:
                                if original_order < o.order <= target_position:
                                    # This object should move up one position
                                    temp_positions[o] = o.order - 1
                                else:
                                    # This object stays in place
                                    temp_positions[o] = o.order
                        elif original_order > target_position:
                            # Moving upward - objects between new and old position move down
                            for o in objects_in_column:
                                if target_position <= o.order < original_order:
                                    # This object should move down one position
                                    temp_positions[o] = o.order + 1
                                else:
                                    # This object stays in place
                                    temp_positions[o] = o.order
                        else:
                            # No change in position
                            for o in objects_in_column:
                                temp_positions[o] = o.order

                        # Now animate the objects toward their temporary positions
                        for o in objects_in_column:
                            temp_order = temp_positions[o]
                            target_top = current_column.rect.top() + 20 + temp_order * (object_height + spacing)

                            # Ensure the target position is within column boundaries
                            if target_top + o.rect.height() > current_column.rect.bottom() - 20:
                                target_top = current_column.rect.bottom() - 20 - o.rect.height()

                            current_top = o.rect.top()

                            # Smooth animation - move a portion of the way to the target
                            animation_step = 0.1  # 이 값을 낮추면 부드럽게 밀리는 속도가 감소합니다
                            new_top = int(current_top + animation_step * (target_top - current_top))

                            # Ensure the new position is within column boundaries
                            new_top = max(current_column.rect.top() + 20,
                                          min(new_top, current_column.rect.bottom() - 20 - o.rect.height()))

                            o.rect.moveTop(new_top)

            self.update()  # Redraw

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging_object:
            try:
                # Make sure the event position is within widget bounds
                # If mouse is released outside the widget, use the last valid position
                contained_pos = QPoint(
                    max(0, min(event.pos().x(), self.width() - 1)),
                    max(0, min(event.pos().y(), self.height() - 1))
                )

                # Store the original state before transfer for potential restore
                original_state = {
                    'activated': self.dragging_object.activated,
                    'column': self.dragging_object.column,
                    'order': self.dragging_object.order,
                    'rect': QRect(self.dragging_object.rect)
                }

                # Remember original positions of all objects
                original_positions = {}
                for obj in self.objects:
                    original_positions[obj] = QRect(obj.rect)

                # Transfer the object based on release position
                self.transfer_object(self.dragging_object, contained_pos)

                # Reset dragging state
                self.dragging_object.is_dragging = False
                drag_obj = self.dragging_object
                self.dragging_object = None

                # Adjust positions and update numbering
                self.adjust_objects_position()
                self.update_object_numbering()

                # If the dragged object returned to its original position, display status message
                if (drag_obj.activated == original_state['activated'] and
                        drag_obj.column == original_state['column'] and
                        drag_obj.order == original_state['order']):
                    self.parent().statusBar().showMessage("Transfer not allowed due to constraints", 3000)

                # Ensure all objects are redrawn correctly
                for obj in self.objects:
                    if obj.activated:
                        print(f"After transfer: Object {obj.id} in column {obj.column} with order {obj.order}")

                self.update()  # Redraw
            except Exception as e:
                # Handle any errors during mouse release
                print(f"Error in mouse release: {e}")
                import traceback
                traceback.print_exc()
                # Reset dragging state in case of error
                if self.dragging_object:
                    self.dragging_object.is_dragging = False
                    self.dragging_object = None
                self.update()  # Ensure UI is updated


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Column Object Manager")
        self.setGeometry(100, 100, 800, 600)

        # Central widget with scroll area
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_layout.addWidget(self.scroll_area)

        # Container widget for the object manager
        self.container = QWidget()
        self.scroll_area.setWidget(self.container)

        # Layout for container
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Object manager widget
        self.object_manager = ObjectManagerWidget()
        container_layout.addWidget(self.object_manager)

        # Status bar
        self.statusBar().showMessage("Ready")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Make sure the container is at least as wide as needed for all columns
        total_width = self.object_manager.fixed_column_width * 8  # 8 columns
        self.container.setMinimumWidth(total_width)
        # Update the entire window after resize
        self.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set application-wide attributes for better rendering
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())