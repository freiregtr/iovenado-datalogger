"""
IOVENADO DataLogger - Lidar View

Real-time chart display for TFMINI Lidar distance measurements.
Includes optimized point removal using binary search.
"""

import time

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, Slot

from config.settings import (
    LIDAR_TIME_WINDOW, LIDAR_MIN_CM, LIDAR_MAX_CM,
    COLOR_LIDAR, COLOR_CONNECTED, COLOR_DISCONNECTED
)


class LidarView(QWidget):
    """
    Lidar data display widget with real-time chart.
    Shows distance in cm with signal strength indicator.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.time_window = LIDAR_TIME_WINDOW
        self.start_time = time.time()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()

        title = QLabel("LIDAR - TFMINI 12M")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header.addWidget(title)

        header.addStretch()

        # Current value (large display)
        self.distance_label = QLabel("--- cm")
        self.distance_label.setStyleSheet(f"""
            font-size: 48px;
            font-weight: bold;
            color: {COLOR_LIDAR};
        """)
        header.addWidget(self.distance_label)

        header.addStretch()

        # Signal strength
        strength_container = QVBoxLayout()
        strength_title = QLabel("Signal")
        strength_title.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        strength_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        strength_container.addWidget(strength_title)

        self.strength_label = QLabel("---")
        self.strength_label.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        self.strength_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        strength_container.addWidget(self.strength_label)
        header.addLayout(strength_container)

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

        # Chart
        self.series = QLineSeries()
        self.series.setName("Distance")
        self.series.setPen(QPen(QColor(COLOR_LIDAR), 2))

        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setTitle("Distance vs Time")
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

        # Y axis (distance)
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Distance (cm)")
        self.axis_y.setRange(LIDAR_MIN_CM, LIDAR_MAX_CM)
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

    @Slot(int, int, bool)
    def update_data(self, distance_cm: int, strength: int, connected: bool):
        """Update display with new lidar data"""
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
            self.distance_label.setText("--- cm")
            self.strength_label.setText("---")
            return

        # Update labels
        self.distance_label.setText(f"{distance_cm} cm")
        self.strength_label.setText(f"{strength}")

        # Update color based on distance (closer = more intense)
        if distance_cm < 100:
            self.distance_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #e74c3c;")
        elif distance_cm < 300:
            self.distance_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #f39c12;")
        else:
            self.distance_label.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {COLOR_LIDAR};")

        # Add point to chart
        current_time = time.time() - self.start_time
        self.series.append(current_time, distance_cm)

        # Update time window
        x_min = max(0, current_time - self.time_window)
        x_max = current_time
        self.axis_x.setRange(x_min, x_max)

        # Auto-scale Y axis based on visible data
        self._auto_scale_y(x_min)

        # Remove old points (optimized with binary search)
        self._remove_old_points(x_min)

    def _auto_scale_y(self, min_time: float):
        """Auto-scale Y axis based on visible data"""
        if self.series.count() == 0:
            return

        # Get visible values
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
        margin = max(data_range * 0.15, 50)  # At least 50cm margin

        new_min = max(0, min_val - margin)
        new_max = min(LIDAR_MAX_CM, max_val + margin)

        self.axis_y.setRange(new_min, new_max)

    def _remove_old_points(self, min_time: float):
        """Remove points outside visible window using binary search"""
        if self.series.count() == 0:
            return

        # Limit max points (for 1 Hz over 60s window, we need ~60 points)
        max_points = int(self.time_window * 2)  # 2x margin
        if self.series.count() > max_points:
            excess = self.series.count() - max_points
            self.series.removePoints(0, excess)
            return

        # Binary search for first point in window
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
        self.distance_label.setText("--- cm")
        self.strength_label.setText("---")
        self.axis_x.setRange(0, self.time_window)
        self.axis_y.setRange(LIDAR_MIN_CM, LIDAR_MAX_CM)
