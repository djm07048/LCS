import sys
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QComboBox, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QMessageBox, QSizePolicy)
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt
from scipy.interpolate import griddata
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
import warnings # Import warnings
# --- SVG 폰트 설정 추가 ---
matplotlib.rcParams['svg.fonttype'] = 'path'

# Use Qt5Agg backend
matplotlib.use('Qt5Agg')
# Suppress specific Matplotlib warnings if needed (optional)
warnings.filterwarnings("ignore", message="Attempting to set identical bottom == top")
warnings.filterwarnings("ignore", message="Attempting to set identical left == right")
import os
import json

class DataProcessor:
    def __init__(self):
        pass

    def import_data(self, path):
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    def data_to_dataframe(self, data):
        """
        데이터를 가공하여 다음과 같은 계층 구조의 멀티인덱스 데이터프레임을 생성합니다:
        1차: time
        2차: column (time, longitude, latitude 제외)
        3차: (longitude, latitude) 좌표 튜플

        Parameters:
        -----------
        data : dict
            입력 데이터. 'table' 키가 있어야 하며, 'columnNames'와 'rows' 항목이 포함되어야 함

        Returns:
        --------
        pandas.DataFrame
            생성된 3단계 멀티인덱스 데이터프레임
        """
        import pandas as pd
        import numpy as np

        # 데이터가 유효한지 확인
        if not isinstance(data, dict) or 'table' not in data:
            raise ValueError("입력 데이터는 'table' 키를 포함하는 딕셔너리여야 합니다.")

        if 'columnNames' not in data['table'] or 'rows' not in data['table']:
            raise ValueError("테이블 데이터에 'columnNames'와 'rows'가 포함되어야 합니다.")

        # 컬럼 이름 목록
        column_names = data['table']['columnNames']

        # 필요한 인덱스 컬럼 위치 찾기
        time_idx = column_names.index('time')
        lon_idx = column_names.index('longitude')
        lat_idx = column_names.index('latitude')

        # 값 컬럼 (인덱스로 사용될 컬럼 제외)
        value_column_indices = [i for i, name in enumerate(column_names)
                                if name not in ['time', 'longitude', 'latitude']]

        # 데이터를 재구성하기 위한 리스트
        records = []

        for row in data['table']['rows']:
            # 필수 인덱스 필드가 누락된 경우 스킵
            if (row[time_idx] is None or row[lon_idx] is None or row[lat_idx] is None):
                continue

            time_val = row[time_idx]
            lon_val = row[lon_idx]
            lat_val = row[lat_idx]
            coords = (lon_val, lat_val)

            # 각 값 컬럼에 대해 레코드 생성
            for col_idx in value_column_indices:
                col_name = column_names[col_idx]
                value = row[col_idx]

                if value is not None:  # None 값은 제외
                    records.append({
                        'time': time_val,
                        'column': col_name,
                        'coords': coords,
                        'value': value
                    })

        # 데이터프레임 생성
        df = pd.DataFrame(records)

        # 시간 데이터를 datetime으로 변환
        df['time'] = pd.to_datetime(df['time'])

        # 멀티인덱스 설정 (time -> column -> coords)
        df = df.set_index(['time', 'column', 'coords'])

        # 데이터프레임을 피벗하여 단일 값 컬럼으로 변환
        df = df['value'].unstack(level='column')

        # 인덱스에서 좌표 정보 추출하여 별도 컬럼으로 추가
        df['longitude'] = [coord[0] for coord in df.index.get_level_values('coords')]
        df['latitude'] = [coord[1] for coord in df.index.get_level_values('coords')]

        return df

    def get_column_names(self, df):
        return df.columns.tolist()

class GraphGenerator:
    def __init__(self):
        pass
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Control Panel 0: File, Time, Save ---
        control_panel0 = QWidget()
        control_layout0 = QHBoxLayout(control_panel0)
        control_layout0.setAlignment(Qt.AlignLeft)

        self.load_button = QPushButton("Load DATA")
        self.load_button.clicked.connect(self.data_to_dataframe)
        control_layout0.addWidget(self.load_button)

        self.save_button = QPushButton("Export SVG")
        self.save_button.clicked.connect(self.save_svg)
        control_layout0.addWidget(self.save_button)

        self.draw_button = QPushButton("Draw")
        self.save_button.clicked.connect(self.update_plot)
        control_layout0.addWidget(self.draw_button)

        control_layout0.addStretch(1)
        main_layout.addWidget(control_panel0)

        # --- Control Panel 1: Time, Column ---
        control_panel1 = QWidget()
        control_layout1 = QHBoxLayout(control_panel1)
        control_layout1.setAlignment(Qt.AlignLeft)

        self.time_combo = QComboBox()
        self.time_combo.addItems(self.get_time_names())
        control_layout1.addWidget(self.time_combo)

        self.column_combo = QComboBox()
        self.column_combo.addItems(self.get_column_names())
        control_layout1.addWidget(self.column_combo)

        control_layout1.addStretch(1)
        main_layout.addLayout(control_panel1)

        # --- Control Panel 2: Custom Color Levels ---
        control_panel2 = QWidget()
        control_layout2 = QHBoxLayout(control_panel2)
        control_layout2.setAlignment(Qt.AlignLeft)

        self.level_start_label = QLabel("Level Start:")
        control_layout2.addWidget(self.level_start_label)
        # --- Request 1: Initialize empty, enable later ---
        self.level_start_input = QLineEdit("") # Start empty
        self.level_start_input.setPlaceholderText("Auto (Min)") # Hint for default
        self.level_start_input.setFixedWidth(80)
        control_layout2.addWidget(self.level_start_input)

        self.level_end_label = QLabel("Level End:")
        control_layout2.addWidget(self.level_end_label)
        # --- Request 1: Initialize empty, enable later ---
        self.level_end_input = QLineEdit("") # Start empty
        self.level_end_input.setPlaceholderText("Auto (Max)") # Hint for default
        self.level_end_input.setFixedWidth(80)
        control_layout2.addWidget(self.level_end_input)

        self.level_num_label = QLabel("Level Number:")
        control_layout2.addWidget(self.level_num_label)
        self.level_num_input = QLineEdit("11")
        self.level_num_input.setValidator(QIntValidator(2, 100))
        self.level_num_input.setFixedWidth(60)
        control_layout2.addWidget(self.level_num_input)

        control_layout2.addStretch(1)
        main_layout.addWidget(control_panel2)

        # Load column names from the default JSON file
        column_names = self.get_column_names

        self.data_value_label = QComboBox()
        self.data_value_label.setFixedWidth(200)
        self.data_value_label.setEnabled(True)
        control_layout2.addWidget(self.data_value_label)

        # Figure canvas
        self.figure = Figure(figsize=(10, 8)) # Slightly taller figure for better layout
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        # Status label
        self.status_label = QLabel("Please load a JSON file")
        main_layout.addWidget(self.status_label)
    def generate_graph(self, time, column, levels):
        """
        특정 시간과 컬럼에 대한 공간 데이터를 지도에 시각화합니다.

        Parameters:
        -----------
        time : str
            조회할 시간 (예: '2023-01-01 00:00:00')
        column : str
            조회할 데이터 컬럼명 (예: '1D_AirTemperature_value')
        levels : list
            np.linspace(min_val_data, max_val_data, level_num)
        Returns:
        --------
        None
        """
        try:
            # 데이터프레임에서 해당 시간과 컬럼에 대한 데이터 추출
            data_series = self.df.loc[time, column]

            # 그래프 초기화
            self.figure.clear()
            projection = ccrs.PlateCarree(central_longitude=180)
            ax = self.figure.add_subplot(111, projection=projection)

            # 지도 경계 설정
            lon_min, lon_max = 90, 300
            lat_min, lat_max = -30, 30

            # 데이터 포인트 추출
            valid_values = []
            valid_lons = []
            valid_lats = []

            # Series의 인덱스는 좌표 튜플 (coords), 값은 데이터 값
            for coords, value in data_series.items():
                if not np.isnan(value):
                    lon, lat = coords  # coords는 (longitude, latitude) 형태의 튜플
                    valid_lons.append(lon)
                    valid_lats.append(lat)
                    valid_values.append(value)

            valid_count = len(valid_values)

            # 유효한 데이터가 없는 경우 처리
            if valid_count == 0:
                ax.text(0.5, 0.5, f"No valid data available for\n{time}",
                        ha='center', va='center', transform=ax.transAxes, color='red', zorder=10)
                ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
                self._add_gridlines(ax)
                self.figure.tight_layout(pad=2.0)
                self.canvas.draw()
                self.status_label.setText(f"No valid data points found for {time}")
                return

            # 지도 특성 추가 (대륙, 바다 등)
            ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='white', edgecolor='black', linewidth=0.3,
                           zorder=3)

            # 보간 및 등고선 플로팅을 위한 준비
            if valid_count > 3:  # 4개 이상의 포인트가 있어야 cubic 보간 가능
                # 그리드 정의
                grid_res = 0.5  # 해상도 (도 단위)
                lon_grid = np.arange(lon_min, lon_max + grid_res, grid_res)
                lat_grid = np.arange(lat_min, lat_max + grid_res, grid_res)
                lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

                # 보간 (cubic)
                interp_method = 'cubic'
                points = np.vstack((valid_lons, valid_lats)).T

                try:
                    from scipy.interpolate import griddata
                    grid_iso = griddata(points, valid_values, (lon_mesh, lat_mesh),
                                        method=interp_method, fill_value=np.nan)

                    if np.all(np.isnan(grid_iso)):
                        raise ValueError("Interpolation resulted in all NaNs.")


                    # 등고선 플로팅
                    contourf = ax.contourf(lon_mesh, lat_mesh, grid_iso,
                                           levels=levels,
                                           cmap='viridis', extend='both',
                                           transform=ccrs.PlateCarree(),
                                           zorder=2)

                    # 컬러바 추가
                    cbar = self.figure.colorbar(contourf, ax=ax,
                                                label=f'{column}',
                                                orientation='vertical',
                                                shrink=0.7, pad=0.08)

                    # 소수점 한 자리까지 표시하도록 틱 레이블 포맷팅
                    tick_labels = [f"{level:.1f}" for level in levels]
                    cbar.set_ticks(levels)
                    cbar.set_ticklabels(tick_labels)

                    self.status_label.setText(
                        f"Plotting {column} for {time}. Valid Points: {valid_count}. "
                        f"Data Range: [{levels[0]:.2f}, {levels[-1]:.2f}].")

                except Exception as e:
                    # 보간 실패 시 데이터 포인트만 표시
                    self.status_label.setText(f"Interpolation failed: {str(e)}. Displaying points only.")
                    ax.scatter(valid_lons, valid_lats, c=valid_values,
                               cmap='viridis', s=30, alpha=0.8,
                               edgecolors='black', linewidths=0.5,
                               transform=ccrs.PlateCarree(), zorder=5)

                    # 컬러바 추가 (산점도용)
                    norm = plt.Normalize(levels[0], levels[-1])
                    sm = plt.cm.ScalarMappable(cmap='viridis', norm=norm)
                    sm.set_array([])
                    cbar = self.figure.colorbar(sm, ax=ax, label=f'{column}')

            else:  # 보간에 충분한 포인트가 없는 경우
                # 메시지만 표시하고 데이터를 그리지 않음
                self.status_label.setText(
                    f"Insufficient data for interpolation ({valid_count} points). At least 4 points required.")
                ax.text(0.5, 0.5,
                        f"Insufficient data ({valid_count} points)\nAt least 4 points required for interpolation",
                        ha='center', va='center', transform=ax.transAxes, color='orange', zorder=10)

            # 지도 범위와 그리드라인 설정
            ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
            self._add_gridlines(ax)

            # 제목 설정
            ax.set_title(f"{column} for {time}", pad=20)

            # 레이아웃 조정 및 그리기
            self.figure.tight_layout(pad=2.0, rect=[0, 0, 1, 0.95])
            self.canvas.draw()

        except Exception as e:
            # 일반적인 에러 처리
            self.status_label.setText(f"Error generating graph: {str(e)}")
            import traceback
            traceback.print_exc()

            # 에러 메시지 표시
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Error generating graph:\n{str(e)}",
                    ha='center', va='center', transform=ax.transAxes, color='red', wrap=True)
            self.canvas.draw()

    def _add_gridlines(self, ax):
        """Adds and configures gridlines for the given axes object."""
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                          linewidth=0.3, color='black', linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        # --- Request 4: 경도를 30도 간격으로 ---
        # This locator already sets 30-degree intervals correctly for the typical range
        gl.xlocator = mticker.FixedLocator(np.arange(-180, 181, 30)) # Use standard -180 to 180 range for locator
        gl.ylocator = mticker.FixedLocator([-30, -15, 0, 15, 30]) # Keep existing latitude lines

        # Use custom formatters that handle the 0-360 range correctly if needed,
        # but PlateCarree often handles wrapping. Let's refine the longitude formatter.
        def lon_formatter(lon, pos):
             # Normalize lon to be within -180 to 180 for display logic
             lon_norm = lon % 360
             if lon_norm > 180:
                 lon_norm -= 360

             if np.isclose(lon_norm, 180) or np.isclose(lon_norm, -180): return '180°'
             if np.isclose(lon_norm, 0): return '0°'
             if 0 < lon_norm < 180: return f'{int(lon_norm)}°E'
             if -180 < lon_norm < 0: return f'{int(abs(lon_norm))}°W'
             return f'{int(lon)}°' # Fallback

        gl.xformatter = mticker.FuncFormatter(lon_formatter)

        def lat_formatter(lat, pos):
            if np.isclose(lat, 0): return 'EQ'
            if lat > 0: return f'{int(lat)}°N'
            return f'{int(abs(lat))}°S'
        gl.yformatter = mticker.FuncFormatter(lat_formatter)
        gl.xlabel_style = {'size': 9, 'color': 'black'} # Adjust label style
        gl.ylabel_style = {'size': 9, 'color': 'black'}

if __name__ == "__main__":
    # Mitigate potential HiDPI scaling issues with Qt/Matplotlib
    # Needs to be set before QApplication instantiation
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    path = r"C:\Users\user\AppData\Local\Programs\Python\Python312\LCS5\graphgen\merged_output_cleaned.json"

    window = GraphGenerator()
    window.setup_ui()
    window.show()
    sys.exit(app.exec_())