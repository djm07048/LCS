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
import warnings  # Import warnings

# --- SVG 폰트 설정 추가 ---
matplotlib.rcParams['svg.fonttype'] = 'path'

# Use Qt5Agg backend
matplotlib.use('Qt5Agg')
# Suppress specific Matplotlib warnings if needed (optional)
warnings.filterwarnings("ignore", message="Attempting to set identical bottom == top")
warnings.filterwarnings("ignore", message="Attempting to set identical left == right")


# python
class MoInsVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pacific Ocean MoIns Data Visualizer (Cubic Interpolation)")
        self.setGeometry(100, 100, 1100, 900)

        # Data
        self.data = None
        self.times = []
        self.file_path = None
        self.cached_data_by_time = {}  # 시간별로 데이터를 캐싱
        self.cached_interpolations = {}  # 시간별로 인터폴레이션 결과 캐싱
        self.current_min_val = None
        self.current_max_val = None

        # UI Setup
        self.setup_ui()

    def extract_times(self):
        # 기존 extract_times 메서드에서 시간별 데이터 캐싱 추가
        if not self.data or 'table' not in self.data or 'rows' not in self.data['table'] or 'columnNames' not in \
                self.data['table']:
            self.times = []
            self.time_combo.clear()
            self.time_combo.setEnabled(False)
            QMessageBox.warning(self, "Data Error", "JSON data is missing 'table', 'rows', or 'columnNames'.")
            return

        try:
            column_names = self.data['table']['columnNames']
            time_index = column_names.index('time')
            rows = self.data['table'].get('rows', [])

            valid_times = set()
            self.cached_data_by_time = {}  # 시간별 데이터 초기화

            for row in rows:
                if row and len(row) > time_index and row[time_index] is not None:
                    time_str = str(row[time_index])
                    valid_times.add(time_str)
                    if time_str not in self.cached_data_by_time:
                        self.cached_data_by_time[time_str] = []
                    self.cached_data_by_time[time_str].append(row)

            self.times = sorted(list(valid_times))

            self.time_combo.blockSignals(True)
            self.time_combo.clear()
            if self.times:
                self.time_combo.addItems(self.times)
                self.time_combo.setEnabled(True)
                self.time_combo.setCurrentIndex(0)
            else:
                self.time_combo.setEnabled(False)
                self.status_label.setText("File loaded, but no valid time entries found.")
            self.time_combo.blockSignals(False)

        except ValueError:
            QMessageBox.warning(self, "Data Error", "'time' column not found in JSON data.")
            self.times = []
            self.time_combo.clear()
            self.time_combo.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred extracting times: {str(e)}")
            self.times = []
            self.time_combo.clear()
            self.time_combo.setEnabled(False)

    def update_data_columns(self):
        """Update data_value_label with all column names from the data"""
        if not self.data or 'table' not in self.data or 'columnNames' not in self.data['table']:
            return

        column_names = self.data['table']['columnNames']
        self.data_value_label.blockSignals(True)
        self.data_value_label.clear()
        self.data_value_label.addItems(column_names)

        # Set default to a numeric column if possible, avoiding lat/lon/time
        default_index = 0
        for i, col in enumerate(column_names):
            if col not in ['time', 'longitude', 'latitude'] and col.startswith('iso') or '_depth' in col:
                default_index = i
                break

        self.data_value_label.setCurrentIndex(default_index)
        self.data_value_label.blockSignals(False)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Control Panel 1: File, Time, Save ---
        control_panel1 = QWidget()
        control_layout1 = QHBoxLayout(control_panel1)
        control_layout1.setAlignment(Qt.AlignLeft)

        self.load_button = QPushButton("Load JSON File")
        self.load_button.clicked.connect(self.load_json_file)
        control_layout1.addWidget(self.load_button)

        self.time_label = QLabel("Select Time:")
        control_layout1.addWidget(self.time_label)

        self.time_combo = QComboBox()
        self.time_combo.setMinimumWidth(450)
        self.time_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.time_combo.setEnabled(False)
        control_layout1.addWidget(self.time_combo)

        # --- Requirement 1: Add Submit button to top-right corner ---
        self.submit_button = QPushButton("Submit")
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self.update_plot)
        control_layout1.addWidget(self.submit_button)

        self.save_button = QPushButton("Export SVG")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_svg)
        control_layout1.addWidget(self.save_button)

        control_layout1.addStretch(1)
        main_layout.addWidget(control_panel1)

        # --- Control Panel 2: Custom Color Levels ---
        control_panel2 = QWidget()
        control_layout2 = QHBoxLayout(control_panel2)
        control_layout2.setAlignment(Qt.AlignLeft)

        self.level_start_label = QLabel("Level Start:")
        control_layout2.addWidget(self.level_start_label)

        # --- Requirement 4: Make level_start required, no defaults ---
        self.level_start_input = QLineEdit("")
        self.level_start_input.setPlaceholderText("Required")
        self.level_start_input.setValidator(QDoubleValidator())
        self.level_start_input.setFixedWidth(80)
        self.level_start_input.setEnabled(False)
        control_layout2.addWidget(self.level_start_input)

        self.level_end_label = QLabel("Level End:")
        control_layout2.addWidget(self.level_end_label)

        # --- Requirement 4: Make level_end required, no defaults ---
        self.level_end_input = QLineEdit("")
        self.level_end_input.setPlaceholderText("Required")
        self.level_end_input.setValidator(QDoubleValidator())
        self.level_end_input.setFixedWidth(80)
        self.level_end_input.setEnabled(False)
        control_layout2.addWidget(self.level_end_input)

        self.level_num_label = QLabel("Level Number:")
        control_layout2.addWidget(self.level_num_label)
        self.level_num_input = QLineEdit("11")
        self.level_num_input.setValidator(QIntValidator(2, 100))
        self.level_num_input.setFixedWidth(60)
        self.level_num_input.setEnabled(False)
        control_layout2.addWidget(self.level_num_input)

        # --- Data value selector ---
        self.data_value_label_text = QLabel("Data Column:")
        control_layout2.addWidget(self.data_value_label_text)


        self.data_value_label = QComboBox()
        self.data_value_label.setEnabled(False)
        self.data_value_label.setMinimumWidth(300)  # Make wider to fit column names
        control_layout2.addWidget(self.data_value_label)

        control_layout2.addStretch(1)
        main_layout.addWidget(control_panel2)

        # --- Requirement 5: Row for displaying min/max values ---
        minmax_panel = QWidget()
        minmax_layout = QHBoxLayout(minmax_panel)
        minmax_layout.setAlignment(Qt.AlignLeft)

        self.current_data_info = QLabel("Data min/max: Not calculated")
        minmax_layout.addWidget(self.current_data_info)

        minmax_layout.addStretch(1)
        main_layout.addWidget(minmax_panel)

        # Figure canvas
        self.figure = Figure(figsize=(10, 8))  # Slightly taller figure for better layout
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        # Status label
        self.status_label = QLabel("Please load a JSON file")
        main_layout.addWidget(self.status_label)

    def load_json_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.json)")

        if file_path:
            try:
                with open(file_path, 'r') as file:
                    self.data = json.load(file)

                self.file_path = file_path
                self.extract_times()
                self.update_data_columns()  # Update data columns dropdown

                # Enable relevant UI elements
                self.time_combo.setEnabled(True)
                self.save_button.setEnabled(True)
                self.submit_button.setEnabled(True)  # Enable submit button after loading file
                self.level_start_input.setEnabled(True)
                self.level_end_input.setEnabled(True)
                self.level_num_input.setEnabled(True)
                self.data_value_label.setEnabled(True)

                self.status_label.setText(f"Loaded file: {self.file_path}")

                # Reset min/max display
                self.current_min_val = None
                self.current_max_val = None
                self.current_data_info.setText("Data min/max: Not calculated")

                # Clear the figure on new file
                self.figure.clear()
                self.canvas.draw()

            except FileNotFoundError:
                QMessageBox.warning(self, "Error", f"File not found: {file_path}")
                self.status_label.setText("Error: File not found.")
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Error", f"Could not decode JSON from file: {file_path}")
                self.status_label.setText("Error: Invalid JSON format.")
            except KeyError as e:
                QMessageBox.warning(self, "Error", f"Missing expected key in JSON data: {e}")
                self.status_label.setText(f"Error: Missing key '{e}' in JSON.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An unexpected error occurred while loading the file: {str(e)}")
                self.status_label.setText(f"Error loading file: {str(e)}")
                # Reset UI on critical error
                self.data = None
                self.times = []
                self.time_combo.clear()
                self.time_combo.setEnabled(False)
                self.save_button.setEnabled(False)
                self.submit_button.setEnabled(False)
                self.level_start_input.setEnabled(False)
                self.level_end_input.setEnabled(False)
                self.level_num_input.setEnabled(False)
                self.data_value_label.setEnabled(False)
                self.level_start_input.setText("")
                self.level_end_input.setText("")
                self.figure.clear()
                self.canvas.draw()

    def update_plot(self):
        # --- Requirement 2: Only runs when submit button is clicked ---
        if not self.data or not self.times or self.time_combo.currentIndex() < 0:
            self.figure.clear()  # Clear figure if no data/time
            self.canvas.draw()
            return

        # --- Requirement 4: Validate required inputs ---
        if not self.level_start_input.text() or not self.level_end_input.text():
            QMessageBox.warning(self, "Input Error", "Level Start and Level End are required fields.")
            self.status_label.setText("Error: Level Start and Level End values are required.")
            return

        try:
            selected_time = self.time_combo.currentText()
            interp_method = 'cubic'  # Hardcoded

            self.figure.clear()
            projection = ccrs.PlateCarree(central_longitude=180)
            # Use add_axes for more control if needed, but add_subplot is fine here
            ax = self.figure.add_subplot(111, projection=projection)

            lon_min, lon_max = 90, 300
            lat_min, lat_max = -30, 30

            data_value = self.data_value_label.currentText()  # Get selected data value

            # --- Data Filtering ---
            column_names = self.data['table']['columnNames']
            try:
                time_idx = column_names.index('time')
                lon_idx = column_names.index('longitude')
                lat_idx = column_names.index('latitude')
                iso_idx = column_names.index(data_value)
            except ValueError as e:
                QMessageBox.warning(self, "Data Error", f"Missing column in JSON data: {e}")
                self.status_label.setText(f"Error: Missing column {e}")
                self.canvas.draw()
                return

            # Filter rows based on the selected time (as string)
            all_data = [row for row in self.data['table']['rows']
                        if row and len(row) > max(time_idx, lon_idx, lat_idx, iso_idx) and str(
                    row[time_idx]) == selected_time]

            valid_count = 0
            valid_values = np.array([])  # Initialize

            if all_data:
                # Extract data carefully, converting value to float, handle None
                lons = np.array([row[lon_idx] for row in all_data], dtype=float)
                lats = np.array([row[lat_idx] for row in all_data], dtype=float)
                iso_values = np.array([float(row[iso_idx]) if row[iso_idx] is not None else np.nan for row in all_data])

                # Identify valid data points (non-NaN in all relevant columns)
                valid_indices = ~np.isnan(iso_values) & ~np.isnan(lons) & ~np.isnan(lats)
                valid_lons = lons[valid_indices]
                valid_lats = lats[valid_indices]
                valid_values = iso_values[valid_indices]  # This is the array for min/max
                valid_count = len(valid_values)  # Count of actual valid points

                # --- Requirement 5: Calculate and display min/max values ---
                if valid_count > 0:
                    self.current_min_val = np.nanmin(valid_values)
                    self.current_max_val = np.nanmax(valid_values)
                    self.current_data_info.setText(
                        f"Data min/max: [{self.current_min_val:.3f}, {self.current_max_val:.3f}]")
                else:
                    self.current_min_val = None
                    self.current_max_val = None
                    self.current_data_info.setText("Data min/max: No valid data")

            # --- Get Custom Levels from QLineEdit ---
            try:
                level_start_text = self.level_start_input.text()
                level_end_text = self.level_end_input.text()
                level_num_text = self.level_num_input.text()

                # Check if inputs are valid before conversion
                if not level_start_text or not level_end_text or not level_num_text:
                    raise ValueError("Level inputs cannot be empty")

                level_start = float(level_start_text)
                level_end = float(level_end_text)
                level_num = int(level_num_text)

                if level_num < 2:
                    level_num = 2
                    self.level_num_input.setText(str(level_num))
                if level_start >= level_end:
                    # Only raise error if values are actually different, avoid issues with min=max
                    if not np.isclose(level_start, level_end):
                        raise ValueError("Level Start must be less than Level End.")
                    else:  # If min and max are the same, create a small range
                        level_end = level_start + 1e-6  # Add a tiny amount
                        if level_num == 2:  # Linspace needs distinct start/end
                            levels = np.array([level_start, level_end])
                        else:  # Create levels around the single value
                            levels = np.linspace(level_start - 1e-6 * (level_num // 2),
                                                 level_end + 1e-6 * (level_num // 2), level_num)

                # Generate levels using linspace if start != end
                if not np.isclose(level_start, level_end):
                    levels = np.linspace(level_start, level_end, level_num)

                level_info = f"Levels: {level_num} ({level_start:.2f} to {level_end:.2f})"

            except ValueError as e:
                # Handle cases where conversion fails or inputs are invalid
                QMessageBox.warning(self, "Input Error", f"Invalid number format or range in Level inputs: {e}")
                self.status_label.setText(f"Error: Invalid level input ({e})")
                # Add map features even if levels fail, but don't plot data
                # --- Request 2: Remove Coastline ---
                # ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.5, edgecolor='black') # Removed

                # --- Request 3: White continents, bring to front ---
                ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='white', edgecolor='black', linewidth=0.3,
                               zorder=3)  # White, zorder=3
                ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.3, linestyle=':',
                               zorder=4)  # Borders on top of land

                ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
                self._add_gridlines(ax)  # Helper function for gridlines
                ax.set_title(f"{data_value} ($W \cdot m^{{-2}}$) for {selected_time} - Input Error", pad=20)
                self.figure.tight_layout(pad=2.0)
                self.canvas.draw()
                return  # Stop plot update here

            # --- Features ---
            # Draw LAND first, with higher zorder
            ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='white', edgecolor='black', linewidth=0.5,
                           zorder=3)

            # --- Interpolation and Plotting ---
            if valid_count > 3:  # Need at least 4 points for cubic interpolation
                # --- Grid Definition ---
                # Define grid based on desired map extent for interpolation
                grid_res = 2.5  # Resolution in degrees, adjust as needed

                lon_grid = np.arange(lon_min, lon_max + grid_res, grid_res)
                lat_grid = np.arange(lat_min, lat_max + grid_res, grid_res)
                lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

                # --- Interpolation (Cubic Only) ---
                grid_iso = None
                points = np.vstack((valid_lons, valid_lats)).T
                interp_status = f"Method: {interp_method}"
                try:
                    # Use original points for cubic interpolation
                    grid_iso = griddata(points, valid_values, (lon_mesh, lat_mesh),
                                        method=interp_method, fill_value=np.nan)

                    # Check if interpolation produced valid results
                    if np.all(np.isnan(grid_iso)):
                        raise ValueError("Interpolation resulted in all NaNs.")

                        # NaN 값 마스킹 (NaN은 스무딩에서 제외)
                        mask = ~np.isnan(grid_iso)
                        grid_iso_smooth = np.copy(grid_iso)

                        # 마스크된 부분만 스무딩 적용
                        temp = np.where(mask, grid_iso, 0)
                        smoothed = gaussian_filter(temp, sigma=1.5)  # sigma 값 조절 가능 (1.0-3.0 추천)
                        grid_iso_smooth[mask] = smoothed[mask]

                        # 스무딩된 데이터로 업데이트
                        grid_iso = grid_iso_smooth
                        interp_status += ", smoothed"  # 상태 표시 업데이트

                    # 보간 결과 검증
                    if np.all(np.isnan(grid_iso)):
                        raise ValueError("Interpolation resulted in all NaNs.")
                except Exception as e:
                    self.status_label.setText(
                        f"{interp_method} interpolation failed for {selected_time}: {str(e)}. Check data.")
                    interp_status = f"Method: {interp_method} (Failed: {e})"
                    grid_iso = np.full(lon_mesh.shape, np.nan)  # Ensure grid_iso exists but is NaN

                # --- Plotting the Interpolated Data ---
                if grid_iso is not None and np.any(~np.isnan(grid_iso)):
                    contourf = ax.contourf(lon_mesh, lat_mesh, grid_iso,
                                           levels=levels,
                                           cmap='gray_r', extend='both',
                                           transform=ccrs.PlateCarree(),
                                           antialised=True,
                                           zorder=2)  # contourf below land (zorder=3)

                    # --- Colorbar ---
                    try:
                        # Add padding to prevent overlap with labels
                        cbar = self.figure.colorbar(contourf, ax=ax, label=rf'{data_value} ($W \cdot m^{{-2}}$)',
                                                    orientation='vertical', shrink=0.7, pad=0.08)  # Adjust shrink/pad
                        # Set ticks based on the custom levels
                        if len(levels) > 1:
                            cbar.set_ticks(levels)
                            # Format ticks - adjust precision as needed
                            tick_labels = [f"{level:.1f}" for level in levels]
                            cbar.set_ticklabels(tick_labels)
                        else:  # Handle case of single level (min=max)
                            cbar.set_ticks(levels)
                            cbar.set_ticklabels([f"{levels[0]:.1f}"])

                    except Exception as cbar_e:
                        print(f"Warning: Could not create colorbar: {cbar_e}")
                        # Proceed without colorbar if it fails

                else:
                    ax.text(0.5, 0.5, "Interpolation resulted\nin no plottable data",
                            ha='center', va='center', transform=ax.transAxes, color='red', zorder=10)

                self.status_label.setText(
                    f"Plotting for {selected_time}. Valid Points: {valid_count}. "
                    f"Data Range: [{self.current_min_val:.2f}, {self.current_max_val:.2f}]. {interp_status}. {level_info}")

            elif valid_count > 0:  # Less than 4 points, but some exist
                self.status_label.setText(
                    f"Insufficient valid data for interpolation ({valid_count} points) at {selected_time}. Displaying points only.")
                ax.text(0.5, 0.5, f"Insufficient data ({valid_count} points)\nCannot interpolate",
                        ha='center', va='center', transform=ax.transAxes, color='orange', zorder=10)
                # Plot the few available points
                ax.scatter(valid_lons, valid_lats, c='red', s=15, alpha=0.7,
                           edgecolors='black', linewidths=0.5, marker='o', label='Data Points',
                           transform=ccrs.PlateCarree(), zorder=5)
                level_info = "Levels not used (no interpolation)"

            else:  # No valid data points found for this time
                self.status_label.setText(f"No valid data points found for {selected_time}")
                ax.text(0.5, 0.5, f"No valid data available for\n{selected_time}",
                        ha='center', va='center', transform=ax.transAxes, color='red', zorder=10)
                level_info = "Levels not used (no data)"

            # --- Map Extent and Gridlines ---
            ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
            self._add_gridlines(ax)  # Use helper method

            ax.set_title(f"{data_value} ($W \cdot m^{{-2}}$) for {selected_time}", pad=20)
            # Use tight_layout with padding, adjust rect if necessary
            self.figure.tight_layout(pad=2.0, rect=[0, 0, 1, 0.95])  # Leave space at top for title

            self.canvas.draw()

        except Exception as e:
            # General exception handling during plotting
            self.status_label.setText(f"Error updating plot: {str(e)}")
            import traceback
            traceback.print_exc()  # Print detailed traceback to console
            QMessageBox.critical(self, "Plotting Error", f"An unexpected error occurred during plotting: {str(e)}")
            # Attempt to clear and display error on the figure
            try:
                self.figure.clear()
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, f"Error during plot update:\n{str(e)}",
                        ha='center', va='center', transform=ax.transAxes, color='red', wrap=True)
                self.canvas.draw()
            except Exception as draw_err:
                print(f"Further error trying to display error message on canvas: {draw_err}")

    # --- Helper function for gridlines ---
    def _add_gridlines(self, ax):
        """Adds and configures gridlines for the given axes object."""
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                          linewidth=0.3, color='black', linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        # --- Request 4: 경도를 30도 간격으로 ---
        # This locator already sets 30-degree intervals correctly for the typical range
        gl.xlocator = mticker.FixedLocator(np.arange(-180, 181, 30))  # Use standard -180 to 180 range for locator
        gl.ylocator = mticker.FixedLocator([-30, -15, 0, 15, 30])  # Keep existing latitude lines

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
            return f'{int(lon)}°'  # Fallback

        gl.xformatter = mticker.FuncFormatter(lon_formatter)

        def lat_formatter(lat, pos):
            if np.isclose(lat, 0): return 'EQ'
            if lat > 0: return f'{int(lat)}°N'
            return f'{int(abs(lat))}°S'

        gl.yformatter = mticker.FuncFormatter(lat_formatter)
        gl.xlabel_style = {'size': 9, 'color': 'black'}  # Adjust label style
        gl.ylabel_style = {'size': 9, 'color': 'black'}

    def save_svg(self):
        if not self.figure or not self.figure.get_axes():
            QMessageBox.warning(self, "Save Error", "Nothing to save. Plot might be empty or contain errors.")
            return

        base_filename = "pacific_iso_plot"
        if self.file_path:
            import os
            base_filename = os.path.splitext(os.path.basename(self.file_path))[0]

        time_str = "unknown_time"
        if self.time_combo.isEnabled() and self.time_combo.currentText():
            time_str = self.time_combo.currentText().replace(':', '-').replace(' ', '_')  # Sanitize time

        suggested_filename = f"{base_filename}_{time_str}_cubic.svg"

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Plot as SVG", suggested_filename,
                                                   "SVG Files (*.svg);;All Files (*)")

        if file_path:
            if not file_path.lower().endswith('.svg'):
                file_path += '.svg'

            try:
                # Ensure layout is calculated before saving
                self.figure.tight_layout(pad=2.0, rect=[0, 0, 1, 0.95])
                self.figure.savefig(file_path, format='svg', bbox_inches='tight', dpi=300)
                self.status_label.setText(f"Saved SVG to {file_path}")
                QMessageBox.information(self, "Success", f"Plot saved successfully to:\n{file_path}")
            except Exception as e:
                self.status_label.setText(f"Error saving SVG: {str(e)}")
                QMessageBox.critical(self, "Save Error", f"Could not save the file:\n{str(e)}")


if __name__ == "__main__":
    # Mitigate potential HiDPI scaling issues with Qt/Matplotlib
    # Needs to be set before QApplication instantiation
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    window = MoInsVisualizer()
    window.show()
    sys.exit(app.exec_())