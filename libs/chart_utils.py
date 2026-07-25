# 日誌檔 2019.12.25
# -*- coding: UTF-8 -*-
from PyQt5 import QtCore, QtGui, QtChart


def plot_chart(title, series, categories, layout, width=None):
    chart = QtChart.QChart()
    chart.addSeries(series)
    chart.setTitle(title)
    chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

    axis = QtChart.QBarCategoryAxis()
    axis.append(categories)

    axis_y = QtChart.QValueAxis()
    chart.addAxis(axis_y, QtCore.Qt.AlignLeft)
    series.attachAxis(axis_y)

    chart.addAxis(axis, QtCore.Qt.AlignBottom)

    chart.legend().setVisible(True)
    chart.legend().setAlignment(QtCore.Qt.AlignRight)

    chartView = QtChart.QChartView(chart)
    chartView.setRenderHint(QtGui.QPainter.Antialiasing)

    if width is not None:
        chartView.setFixedWidth(width)

    layout.addWidget(chartView)
