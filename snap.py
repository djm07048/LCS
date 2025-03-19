import sys
import math
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen


class Marker:
    def __init__(self, x, y, size=10, index=0):
        self.x = int(x)  # x 좌표 (고정됨)
        self.y = int(y)  # y 좌표 (변경 가능)
        self.size = int(size)  # 마커 크기
        self.original_y = int(y)  # 원래 y 좌표 (초기값 저장)
        self.attached_object = None  # 부착된 객체
        self.index = index  # 마커 인덱스

    def contains(self, point):
        # 포인트가 마커 내에 있는지 확인
        return (abs(point.x() - self.x) <= self.size and
                abs(point.y() - self.y) <= self.size)

    def get_rect(self):
        # 마커의 사각형 영역 반환
        return QRect(self.x - self.size // 2, self.y - self.size // 2,
                     self.size, self.size)


class DraggableObject:
    def __init__(self, x, y, width, height, color, obj_id):
        self.x = int(x)  # x 좌표
        self.y = int(y)  # y 좌표
        self.width = int(width)  # 객체 너비
        self.height = int(height)  # 객체 높이
        self.color = color  # 객체 색상
        self.obj_id = obj_id  # 객체 고유 ID
        self.attached_marker = None  # 현재 부착된 마커
        self.original_marker = None  # 원래 부착된 마커
        self.is_dragging = False  # 드래그 중인지 여부
        self.drag_offset_x = 0  # 드래그 시 x 오프셋
        self.drag_offset_y = 0  # 드래그 시 y 오프셋

    def contains(self, point):
        # 포인트가 객체 내에 있는지 확인
        return (self.x <= point.x() <= self.x + self.width and
                self.y <= point.y() <= self.y + self.height)

    def get_rect(self):
        # 객체의 사각형 영역 반환
        return QRect(self.x, self.y, self.width, self.height)

    def get_top_left(self):
        # 객체의 좌상단 좌표 반환
        return QPoint(self.x, self.y)

    def get_bottom_right(self):
        # 객체의 우하단 좌표 반환
        return QPoint(self.x + self.width, self.y + self.height)


class MarkerSnapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # UI 초기화
        self.setWindowTitle('마커 스냅 애플리케이션')
        self.setGeometry(50, 50, 1600, 900)  # 윈도우 크기 증가

        # 현재 드래그 중인 객체
        self.dragging_object = None

        # 상태 표시 레이블
        self.status_label = QLabel('객체를 드래그하여 마커에 스냅하세요', self)
        self.status_label.setGeometry(10, 10, 700, 30)

        # 마커 초기 위치 설정
        self.init_markers()

        # 객체 생성
        self.init_objects()

        self.show()

    def init_markers(self):
        # 8개 컬럼에 각 3개의 마커 생성 (총 24개)
        marker_size = 10
        columns = 8
        rows = 3

        # 마커 간격 계산
        window_width = 1500
        window_height = 700
        h_margin = 100
        v_margin = 100

        column_width = (window_width - 2 * h_margin) / (columns - 1)
        row_height = (window_height - 2 * v_margin) / (rows - 1)

        # 마커 생성
        self.markers = []
        marker_index = 0

        for col in range(columns):
            x = h_margin + col * column_width
            for row in range(rows):
                y = v_margin + row * row_height
                self.markers.append(Marker(x, y, marker_size, marker_index))
                marker_index += 1

        # 마커 레이블 생성
        self.marker_labels = []
        for i, marker in enumerate(self.markers):
            label = QLabel(f"{i + 1}", self)  # 1부터 시작하는 번호 표시
            label.setGeometry(int(marker.x - 15), int(marker.y - 15), 30, 30)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: red; font-weight: bold;")
            self.marker_labels.append(label)

    def init_objects(self):
        # 20개의 객체 생성
        object_width = 100  # 너비를 줄여 화면에 맞게 조정

        # 다양한 높이와 색상으로 객체 생성
        colors = [
            QColor(255, 100, 100),  # 빨간색
            QColor(100, 100, 255),  # 파란색
            QColor(100, 255, 100),  # 초록색
            QColor(255, 255, 100),  # 노란색
            QColor(255, 100, 255),  # 분홍색
            QColor(100, 255, 255),  # 하늘색
            QColor(255, 150, 50),  # 주황색
            QColor(150, 50, 255),  # 보라색
            QColor(50, 150, 150),  # 청록색
            QColor(200, 100, 50)  # 갈색
        ]

        # 20개 객체 생성
        self.objects = []
        for i in range(20):
            # 객체 높이는 50~100 사이에서 변화
            height = 50 + (i % 6) * 10
            # 색상은 반복해서 사용
            color = colors[i % len(colors)]

            # 초기 위치 설정
            if i < 8:  # 처음 8개 객체는 첫 번째 행의 마커에 배치
                x = self.markers[i * 3].x
                y = self.markers[i * 3].y
                obj = DraggableObject(x, y, object_width, height, color, i)
                self.objects.append(obj)
                self.attach_object_to_marker(obj, self.markers[i * 3])
            else:  # 나머지 객체는 화면 하단에 분산 배치
                x = 100 + (i % 8) * 180
                y = 750 + (i // 8) * 60
                self.objects.append(DraggableObject(x, y, object_width, height, color, i))

        # 마커 위치 재조정
        self.adjust_marker_positions()

    def attach_object_to_marker(self, obj, marker):
        # 객체를 마커에 부착하는 함수

        # 이전에 부착된 마커가 있으면 연결 해제
        if obj.attached_marker:
            obj.attached_marker.attached_object = None

        # 새 마커에 부착
        obj.x = int(marker.x)
        obj.y = int(marker.y)
        obj.attached_marker = marker
        marker.attached_object = obj

        # 원래 마커가 설정되지 않았으면 설정
        if obj.original_marker is None:
            obj.original_marker = marker

        self.update_status(f"객체 {obj.obj_id + 1}이(가) 마커 {marker.index + 1}에 부착됨")

    def update_status(self, message):
        # 상태 메시지 업데이트
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
        print(message)  # 콘솔에도 출력하여 디버깅에 도움

    def update_marker_labels(self):
        # 마커 레이블 위치 업데이트
        for i, marker in enumerate(self.markers):
            # float 값을 정수로 변환
            x = int(marker.x - 15)
            y = int(marker.y - 15)
            self.marker_labels[i].setGeometry(x, y, 30, 30)

    def paintEvent(self, event):
        # 화면 그리기 이벤트
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 마커 그리기
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(Qt.red))
        for marker in self.markers:
            painter.drawEllipse(marker.get_rect())

        # 객체 그리기
        for obj in self.objects:
            painter.setBrush(QBrush(obj.color))
            painter.drawRect(obj.get_rect())

    def mousePressEvent(self, event):
        # 마우스 누름 이벤트
        if event.button() == Qt.LeftButton:
            # 객체가 클릭되었는지 확인
            for obj in self.objects:
                if obj.contains(event.pos()):
                    # 드래그 시작
                    self.dragging_object = obj
                    obj.is_dragging = True
                    # 드래그 오프셋 설정 (객체 내 클릭 위치)
                    obj.drag_offset_x = event.pos().x() - obj.x
                    obj.drag_offset_y = event.pos().y() - obj.y

                    # 드래그 시작 상태 업데이트
                    self.update_status(f"객체 {obj.obj_id + 1} 드래그 시작")
                    break

    def mouseMoveEvent(self, event):
        # 마우스 이동 이벤트
        if self.dragging_object:
            # 객체 위치 업데이트 (정수로 변환)
            self.dragging_object.x = int(event.pos().x() - self.dragging_object.drag_offset_x)
            self.dragging_object.y = int(event.pos().y() - self.dragging_object.drag_offset_y)

            # Move 상태 표시
            self.update_status(
                f"Move: 객체 {self.dragging_object.obj_id + 1} 이동 중 ({self.dragging_object.x}, {self.dragging_object.y})")
            self.update()  # 화면 갱신

    def mouseReleaseEvent(self, event):
        # 마우스 릴리즈 이벤트
        if event.button() == Qt.LeftButton and self.dragging_object:
            try:
                # 드래그 중인 객체와 원래 마커 저장
                dragged_obj = self.dragging_object
                source_marker = dragged_obj.attached_marker

                if source_marker is None:
                    # 부착된 마커가 없으면 원래 마커로 설정
                    if dragged_obj.original_marker:
                        source_marker = dragged_obj.original_marker
                    else:
                        # 원래 마커도 없으면 첫 번째 마커로 설정
                        source_marker = self.markers[0]
                        dragged_obj.original_marker = source_marker

                # 객체의 좌상단 위치 가져오기
                object_top_left = dragged_obj.get_top_left()

                # 가장 가까운 마커 찾기 (현재 부착된 마커 제외)
                closest_marker = None
                closest_distance = float('inf')

                for marker in self.markers:
                    # 현재 부착된 마커는 건너뛰기
                    if marker == source_marker:
                        continue

                    # 마커와 객체 좌상단 거리 계산
                    distance = math.sqrt(
                        (marker.x - object_top_left.x()) ** 2 +
                        (marker.y - object_top_left.y()) ** 2
                    )

                    # 더 가까운 마커 발견 시 업데이트
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_marker = marker

                # Transfer vs Retrieve 결정 (거리가 100 이하면 Transfer)
                if closest_marker is not None and closest_distance <= 100:
                    # Transfer - 객체를 새 마커로 이동
                    self.update_status(
                        f"Transfer: 객체 {dragged_obj.obj_id + 1}을(를) 마커 {closest_marker.index + 1}로 이동 (거리: {closest_distance:.1f})")
                    self.handle_transfer(dragged_obj, closest_marker, source_marker)
                else:
                    # Retrieve - 객체를 원래 마커로 되돌림
                    self.update_status(f"Retrieve: 객체 {dragged_obj.obj_id + 1}을(를) 마커 {source_marker.index + 1}로 복귀")
                    self.attach_object_to_marker(dragged_obj, source_marker)

                # 마커 위치 재조정
                self.adjust_marker_positions()

            except Exception as e:
                # 예외 발생 시 출력 (디버깅용)
                import traceback
                print(f"Error in mouseReleaseEvent: {e}")
                traceback.print_exc()
            finally:
                # 드래그 상태 초기화 (예외가 발생해도 실행됨)
                if self.dragging_object:
                    self.dragging_object.is_dragging = False
                    self.dragging_object = None
                self.update()  # 화면 갱신
                self.update_marker_labels()  # 마커 레이블 위치 업데이트

    def handle_transfer(self, obj, target_marker, source_marker):
        # Transfer 처리 함수
        try:
            print(f"handle_transfer: 객체 {obj.obj_id + 1}을(를) 마커 {target_marker.index + 1}로 이동")

            # 대상 마커에 이미 객체가 있는 경우 AutoTransfer 처리
            displaced_object = target_marker.attached_object
            if displaced_object and displaced_object != obj:
                print(f"AutoTransfer: 마커 {target_marker.index + 1}에 있던 객체 {displaced_object.obj_id + 1} 이동")

                # 같은 x 좌표를 가진 마커 중 적절한 마커 찾기
                x_coord = target_marker.x

                # 자동 이동할 마커 선택 (같은 x좌표)
                same_column_markers = [m for m in self.markers
                                       if m.x == x_coord and m != target_marker]

                # 빈 마커가 있는지 확인
                empty_markers = [m for m in same_column_markers if m.attached_object is None]

                if empty_markers:
                    # 빈 마커가 있으면, 그 중 하나로 이동
                    best_marker = empty_markers[0]
                    print(f"빈 마커 찾음: 객체 {displaced_object.obj_id + 1}을(를) 마커 {best_marker.index + 1}로 이동")

                    # 객체 연결 해제 후 새 마커에 부착
                    target_marker.attached_object = None
                    displaced_object.attached_marker = None
                    self.attach_object_to_marker(displaced_object, best_marker)
                else:
                    # 빈 마커가 없으면, 원래 객체가 있던 마커(source_marker)로 이동
                    if source_marker:
                        print(f"스왑: 객체 {displaced_object.obj_id + 1}을(를) 마커 {source_marker.index + 1}로 이동")

                        # 완전한 스왑을 위해 객체와 마커 관계 모두 해제
                        if source_marker.attached_object:
                            temp_obj = source_marker.attached_object
                            temp_obj.attached_marker = None
                            source_marker.attached_object = None

                        # 대상 마커에서 객체 연결 해제
                        target_marker.attached_object = None
                        displaced_object.attached_marker = None

                        # 먼저 displaced_object를 source_marker에 부착
                        self.attach_object_to_marker(displaced_object, source_marker)
                    else:
                        # source_marker가 없는 경우, 화면 하단으로 이동
                        print(f"적절한 스왑 대상이 없음: 객체 {displaced_object.obj_id + 1}을(를) 화면 하단으로 이동")

                        # 객체 연결 해제
                        target_marker.attached_object = None
                        displaced_object.attached_marker = None

                        # 새 위치로 이동
                        displaced_object.x = 300 + (displaced_object.obj_id * 50)
                        displaced_object.y = 750

            # 드래그한 객체를 대상 마커에 부착
            # 기존 연결 해제
            if obj.attached_marker:
                obj.attached_marker.attached_object = None
            obj.attached_marker = None

            # 새 마커에 부착
            self.attach_object_to_marker(obj, target_marker)

        except Exception as e:
            # 예외 발생 시 출력 (디버깅용)
            import traceback
            print(f"Error in handle_transfer: {e}")
            traceback.print_exc()

    def adjust_marker_positions(self):
        # 마커 위치 재조정 함수
        try:
            # x 좌표별로 마커 그룹화 (컬럼)
            columns = {}
            for marker in self.markers:
                if marker.x not in columns:
                    columns[marker.x] = []
                columns[marker.x].append(marker)

            # 각 컬럼별로 마커 위치 조정
            for x, markers_in_column in columns.items():
                print(f"\n컬럼 {x}의 마커 위치 조정 시작")

                # 원래 y 위치로 마커 정렬
                markers_in_column.sort(key=lambda m: m.original_y)

                # 컬럼의 상단과 하단 경계 결정
                top_marker = min(markers_in_column, key=lambda m: m.original_y)
                bottom_marker = max(markers_in_column, key=lambda m: m.original_y)
                top_boundary = top_marker.original_y
                bottom_boundary = bottom_marker.original_y

                print(f"  상단 경계: {top_boundary}, 하단 경계: {bottom_boundary}")

                # 객체 또는 마커의 높이 정보 수집
                elements_info = []
                for marker in markers_in_column:
                    if marker.attached_object:
                        # 객체가 부착된 경우
                        obj = marker.attached_object
                        print(f"  마커 {marker.index + 1}에 객체 {obj.obj_id + 1} 부착됨, 높이: {obj.height}")
                        elements_info.append((marker, obj.height))
                    else:
                        # 객체가 없는 경우 마커 자체 높이 사용
                        print(f"  마커 {marker.index + 1}에 부착된 객체 없음")
                        elements_info.append((marker, marker.size))

                # 총 공간과 요소 간 간격 계산
                total_space = bottom_boundary - top_boundary
                total_element_height = sum(height for _, height in elements_info)
                num_gaps = len(elements_info) - 1

                print(f"  총 공간: {total_space}, 총 요소 높이: {total_element_height}, 간격 수: {num_gaps}")

                # 간격이 없으면 (마커가 1개면) 조정 필요 없음
                if num_gaps <= 0:
                    print("  마커가 1개뿐이므로 조정 불필요")
                    continue

                # 요소 간 간격 계산
                gap_size = max(10, (total_space - total_element_height) / num_gaps)
                print(f"  계산된 간격 크기: {gap_size}")

                # 새 위치 설정
                current_y = top_boundary

                for idx, (marker, height) in enumerate(elements_info):
                    # 마커 위치 업데이트
                    marker.y = int(current_y)
                    print(f"  마커 {marker.index + 1} 위치 조정: y={marker.y}")

                    # 부착된 객체 위치도 업데이트
                    if marker.attached_object:
                        marker.attached_object.y = int(current_y)
                        print(f"  객체 {marker.attached_object.obj_id + 1} 위치 조정: y={marker.attached_object.y}")

                    # 다음 요소의 위치 계산
                    if idx < len(elements_info) - 1:
                        current_y += height + gap_size

        except Exception as e:
            # 예외 발생 시 출력 (디버깅용)
            import traceback
            print(f"Error in adjust_marker_positions: {e}")
            traceback.print_exc()

        # 마커 레이블 위치 업데이트
        self.update_marker_labels()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MarkerSnapApp()
    sys.exit(app.exec_())