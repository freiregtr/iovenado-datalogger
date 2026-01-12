"""
IOVENADO DataLogger - CO2 View

Real-time chart display for MH-Z19C CO2 sensor.
Includes air quality level indicators.
"""

import time

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, Slot

from config.settings import (
    CO2_TIME_WINDOW,
    CO2_LEVEL_EXCELLENT, CO2_LEVEL_GOOD, CO2_LEVEL_MODERATE,
    COLOR_CO2, COLOR_CONNECTED, COLOR_DISCONNECTED
)


class CO2View(QWidget):
    """
    CO2 sensor display widget with real-time chart.
    Shows concentration in ppm with air quality level indicator.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.time_window = CO2_TIME_WINDOW
        self.start_time = time.time()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()

        title = QLabel("CO2 - MH-Z19C")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header.addWidget(title)

        header.addStretch()

        # Current value (large display)
        self.co2_label = QLabel("--- ppm")
        self.co2_label.setStyleSheet(f"""
            font-size: 48px;
            font-weight: bold;
            color: {COLOR_CO2};
        """)
        header.addWidget(self.co2_label)

        header.addStretch()

        # Air quality level
        level_container = QVBoxLayout()
        level_title = QLabel("Air Quality")
        level_title.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        level_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        level_container.addWidget(level_title)

        self.level_label = QLabel("---")
        self.level_label.setStyleSheet("color: #bdc3c7; font-size: 16px; font-weight: bold;")
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        level_container.addWidget(self.level_label)
        header.addLayout(level_container)

        # Status
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {COLOR_DISCONNECTED};
            padding: 5px 10px;
            border-radius: 3px;
            background-color: rgba(231, 76, 60, 0.2);
        """)
        header.addWidget(self.status_label)

        layout.addLayout(header)

        # Reference levels indicator
        levels_frame = QFrame()
        levels_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 1px solid #34495e;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        levels_layout = QHBoxLayout(levels_frame)
        levels_layout.setSpacing(20)

        # Level indicators
        self._add_level_indicator(levels_layout, "EXCELLENT", f"<{CO2_LEVEL_EXCELLENT}", "#27ae60")
        self._add_level_indicator(levels_layout, "GOOD", f"<{CO2_LEVEL_GOOD}", "#2ecc71")
        self._add_level_indicator(levels_layout, "MODERATE", f"<{CO2_LEVEL_MODERATE}", "#f39c12")
        self._add_level_indicator(levels_layout, "POOR", f">{CO2_LEVEL_MODERATE}", "#e74c3c")

        layout.addWidget(levels_frame)

        # Chart
        self.series = QLineSeries()
        self.series.setName("CO2")
        self.series.setPen(QPen(QColor(COLOR_CO2), 2))

        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setTitle("CO2 Concentration vs Time")
        self.chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self.chart.setBackgroundBrush(QColor("#1a1a2e"))
        self.chart.setTitleBrush(QColor("#ecf0f1"))
        self.chart.legend().setLabelColor(QColor("#bdc3c7"))

        # X axis (time)
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Time (s)")
        self.axis_x.setRange(0, self.time_window)
        self.axis_x.setLabelsColor(QColor("#bdc3c7"))
        self.axis_x.setTitleBrush(QColor("#bdc3c7"))
        self.axis_x.setGridLineColor(QColor("#34495e"))

        # Y axis (CO2 ppm)
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("CO2 (ppm)")
        self.axis_y.setRange(400, 2500)
        self.axis_y.setLabelsColor(QColor("#bdc3c7"))
        self.axis_y.setTitleBrush(QColor("#bdc3c7"))
        self.axis_y.setGridLineColor(QColor("#34495e"))

        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setStyleSheet("background-color: #1a1a2e; border-radius: 10px;")

        layout.addWidget(self.chart_view)

    def _add_level_indicator(self, layout: QHBoxLayout, name: str, range_text: str, color: str):
        """Add a level indicator to the layout"""
        container = QVBoxLayout()

        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
        """)
        container.addWidget(dot, alignment=Qt.AlignmentFlag.AlignCenter)

        label = QLabel(name)
        label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container.addWidget(label)

        range_label = QLabel(range_text)
        range_label.setStyleSheet("color: #7f8c8d; font-size: 9px;")
        range_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container.addWidget(range_label)

        layout.addLayout(container)

    @Slot(int, bool)
    def update_data(self, co2_ppm: int, connected: bool):
        """Update display with new CO2 data"""
        # Update status
        if connected:
            self.status_label.setText("CONNECTED")
            self.status_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: bold;
                color: {COLOR_CONNECTED};
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(46, 204, 113, 0.2);
            """)
        else:
            self.status_label.setText("DISCONNECTED")
            self.status_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: bold;
                color: {COLOR_DISCONNECTED};
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(231, 76, 60, 0.2);
            """)
            self.co2_label.setText("--- ppm")
            self.level_label.setText("---")
            return

        # Update value label
        self.co2_label.setText(f"{co2_ppm} ppm")

        # Determine level and color
        if co2_ppm < CO2_LEVEL_EXCELLENT:
            level = "EXCELLENT"
            color = "#27ae60"
        elif co2_ppm < CO2_LEVEL_GOOD:
            level = "GOOD"
            color = "#2ecc71"
        elif co2_ppm < CO2_LEVEL_MODERATE:
            level = "MODERATE"
            color = "#f39c12"
        else:
            level = "POOR"
            color = "#e74c3c"

        self.level_label.setText(level)
        self.level_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
        self.co2_label.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {color};")

        # Add point to chart
        current_time = time.time() - self.start_time
        self.series.append(current_time, co2_ppm)

        # Update time window
        x_min = max(0, current_time - self.time_window)
        x_max = current_time
        self.axis_x.setRange(x_min, x_max)

        # Auto-scale Y axis
        self._auto_scale_y(x_min)

        # Remove old points
        self._remove_old_points(x_min)

    def _auto_scale_y(self, min_time: float):
        """Auto-scale Y axis based on visible data"""
        if self.series.count() == 0:
            return

        values = []
        for i in range(self.series.count()):
            point = self.series.at(i)
            if point.x() >= min_time:
                values.append(point.y())

        if not values:
            return

        min_val = min(values)
        max_val = max(values)

        # Add margin
        data_range = max_val - min_val
        margin = max(data_range * 0.15, 100)  # At least 100 ppm margin

        new_min = max(300, min_val - margin)  # CO2 rarely below 300
        new_max = max_val + margin

        self.axis_y.setRange(new_min, new_max)

    def _remove_old_points(self, min_time: float):
        """Remove points outside visible window using binary search"""
        if self.series.count() == 0:
            return

        # Limit max points
        max_points = int(self.time_window * 2)
        if self.series.count() > max_points:
            excess = self.series.count() - max_points
            self.series.removePoints(0, excess)
            return

        # Binary search
        count = self.series.count()
        left, right = 0, count - 1
        points_to_remove = 0

        while left <= right:
            mid = (left + right) // 2
            if self.series.at(mid).x() < min_time:
                points_to_remove = mid + 1
                left = mid + 1
            else:
                right = mid - 1

        if points_to_remove > 0:
            self.series.removePoints(0, points_to_remove)

    def reset(self):
        """Reset chart and display"""
        self.series.clear()
        self.start_time = time.time()
        self.co2_label.setText("--- ppm")
        self.level_label.setText("---")
        self.axis_x.setRange(0, self.time_window)
        self.axis_y.setRange(400, 2500)
