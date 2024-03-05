#!/usr/bin/python3
import sys

from ui.bayesian_ui import BayesianModel

from qtpy import QtCore
from qtpy.QtWidgets import QApplication, QGridLayout, QTabWidget, QWidget


class FittingInterface(QTabWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.setWindowTitle('Time-resolved analysis')
        layout = QGridLayout()
        self.setLayout(layout)

        self.settings = QtCore.QSettings()

        # Bayesian analysis tab
        tab_id = 0
        self.time_60Hz_tab = BayesianModel()
        self.addTab(self.time_60Hz_tab, "Bayesian analysis")
        self.setTabText(tab_id, "Bayesian analysis")


if __name__ == '__main__':
    app = QApplication([])
    window = FittingInterface()
    window.show()
    sys.exit(app.exec_())
