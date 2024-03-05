#!/usr/bin/python3
import os
import subprocess

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QFileDialog, QGridLayout, QLabel, QMessageBox, QPushButton, QSpacerItem, QWidget

DATA_FILE_DIRECTIVE = "Click to choose a file to process"
OUTPUT_DIR_DIRECTIVE = os.path.expanduser("~")


class PathSelector:
    def __init__(self, key, parent, label, directive, select_dir:bool=True):
        self.parent = parent
        self.label = label
        self.directive = directive
        self.key = key
        self.select_dir = select_dir

    def attach(self, layout, row_id):
        font = QtGui.QFont()
        font.setItalic(True)

        instructions = QLabel(self.parent)
        instructions.setText(self.directive)
        instructions.setFont(font)
        layout.addWidget(instructions, row_id, 1, 1, 2)

        row_id += 1
        self.choose_path = QPushButton(self.label)
        layout.addWidget(self.choose_path, row_id, 1)

        self.path_label = QLabel(self.parent)
        layout.addWidget(self.path_label, row_id, 2)

        # Fill in default value if available
        _path = QtCore.QSettings().value(f'tr_bayes_{self.key}', '')
        if len(_path.strip()) == 0:
            _path = ''
        self.path_label.setText(_path)
        self.choose_path.clicked.connect(self.selection)

        spacer = QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum,
                             QtWidgets.QSizePolicy.Expanding)
        layout.addItem(spacer, row_id+1, 1)

        return row_id + 2

    def selection(self):
        if self.select_dir:
            _path = QFileDialog.getExistingDirectory(None, 'Select a folder:',
                                                     self.path_label.text(),
                                                     QFileDialog.ShowDirsOnly)
            if os.path.isdir(_path) or len(_path.strip()) == 0:
                self.path_label.setText(_path)
                QtCore.QSettings().setValue(f'tr_bayes_{self.key}', _path)
        else:
            _path, _ = QFileDialog.getOpenFileName(None, 'Open file',
                                                   self.path_label.text(),
                                                   'Settings file (*.*)')
            if os.path.isfile(_path) or len(_path.strip()) == 0:
                self.path_label.setText(_path)
                QtCore.QSettings().setValue(f'tr_bayes_{self.key}', _path)
    

class BayesianModel(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.setWindowTitle('Quick reduce')
        layout = QGridLayout()
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
        self.setLayout(layout)

        self.settings = QtCore.QSettings()

        row_id = 1
        font = QtGui.QFont()
        font.setItalic(True)

        # Run number
        instructions_run = QLabel(self)
        instructions_run.setText("Select the run number to process.")
        instructions_run.setFont(font)
        layout.addWidget(instructions_run, row_id, 1, 1, 2)

        row_id += 1
        self.run_number_ledit = QtWidgets.QLineEdit()
        self.run_number_ledit.setValidator(QtGui.QIntValidator())
        layout.addWidget(self.run_number_ledit, row_id, 1)
        self.run_number_label = QLabel(self)
        self.run_number_label.setText("Run number")
        layout.addWidget(self.run_number_label, row_id, 2)
        spacer = QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum,
                             QtWidgets.QSizePolicy.Expanding)
        row_id += 1
        layout.addItem(spacer, row_id, 1)

        # Time-resolved data directory
        row_id += 1
        self.td_data_dir = PathSelector("input_data", self, "Data directory", 
                                        "Click to directory containing reduced time-resolved data.",
                                        select_dir=True)
        row_id = self.td_data_dir.attach(layout, row_id)

        # Initial state fit results
        text = (
            "Select the initial state fit results.\n"
            + "Leave empty when the initial state is not known.\n"
            + "Example: reflectivity_fits/IPTS-29196/201282/__model_expt.json"

        )
        self.initial_state_file = PathSelector("initial_state", self, "Initial state",
                                               text, select_dir=False)
        row_id = self.initial_state_file.attach(layout, row_id)

        # Final state fit results
        text = (
            "Select the final state fit results.\n"
            + "Leave empty when the initial state is not known."
        )
        self.final_state_file = PathSelector("final_state", self, "Final state",
                                             text, select_dir=False)
        row_id = self.final_state_file.attach(layout, row_id)

        # Output directory
        self.output_dir = PathSelector("output_dir", self, "Output directory", 
                                        "Click to choose an output directory.",
                                        select_dir=True)
        row_id = self.output_dir.attach(layout, row_id)


        spacer = QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum,
                             QtWidgets.QSizePolicy.Minimum)
        layout.addItem(spacer, row_id, 1)

        # Process button
        row_id += 1
        self.perform_reduction = QPushButton('Process')
        self.perform_reduction.setStyleSheet("background-color : green")
        layout.addWidget(self.perform_reduction, row_id, 1)

        # connections
        row_id += 1
        self.perform_reduction.clicked.connect(self.reduce)

        # Populate from previous session
        self.read_settings()

    def read_settings(self):
        """
        Read settings from the last session not covered by the PathSelector objects
        """
        _run_number = self.settings.value("tr_bayes_run_number", '')
        self.run_number_ledit.setText(_run_number)

    def save_settings(self):
        self.settings.setValue('tr_bayes_run_number', self.run_number_ledit.text())

    def check_inputs(self):
        error = None
        # Check files and output directory
        if not os.path.isdir(self.output_dir.path_label.text()):
            error = "The chosen output directory could not be found"

        try:
            int(self.run_number_ledit.text())
        except Exception:
            error = "Check your run number"
        # Pop up a dialog if there were invalid inputs
        if error:
            print('test')
            self.show_dialog(error)
            return False
        return True

    def show_dialog(self, text):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setText(text)
        msgBox.setWindowTitle("Invalid inputs")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec()

    def reduce(self):
        if not self.check_inputs():
            print("Invalid inputs found")
            return

        self.save_settings()

        print("Processing!")

        #subprocess.run(['nsd-conda-wrap.sh', 'refl1d', 'scripts/quick_reduce.py',
        #                self.run_number_ledit.text(), self.db_run_number_ledit.text(),
        #                self.peak_pixel_ledit.text(), self.db_peak_pixel_ledit.text(), self.output_dir_label.text()])