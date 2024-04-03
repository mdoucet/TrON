#!/usr/bin/python3
import os
import subprocess

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QFileDialog, QGridLayout, QLabel, QMessageBox, QPushButton, QSpacerItem, QWidget

DATA_FILE_DIRECTIVE = "Click to choose a file to process"
OUTPUT_DIR_DIRECTIVE = os.path.expanduser("~")

from tron.bayesian_analysis import template, fitting_loop, summary_plots


class PathSelector:
    def __init__(self, key, parent, label, directive, select_dir:bool=True, create_file:bool=False):
        self.parent = parent
        self.label = label
        self.directive = directive
        self.key = key
        self.select_dir = select_dir
        self.create_file = create_file
        self.call_back = None

    def attach(self, layout, row_id, call_back=None):
        font = QtGui.QFont()
        font.setItalic(True)
        font.setBold(True)

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
        self.call_back = call_back

        return row_id + 2

    def set_value(self, value):
        self.path_label.setText(value)
        QtCore.QSettings().setValue(f'tr_bayes_{self.key}', value)

    def selection(self):
        if self.select_dir:
            _path = QFileDialog.getExistingDirectory(None, 'Select a folder:',
                                                     self.path_label.text(),
                                                     QFileDialog.ShowDirsOnly)
            if os.path.isdir(_path):
                self.path_label.setText(_path)
                QtCore.QSettings().setValue(f'tr_bayes_{self.key}', _path)            
                if self.call_back is not None:
                    self.call_back(_path)
        else:
            if self.create_file:
                _path, _ = QFileDialog.getSaveFileName(None, 'Save file',
                                                       self.path_label.text(),
                                                       'Settings file (*.*)')
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
        font.setBold(True)

        # Run number
        instructions_run = QLabel(self)
        instructions_run.setText("Select the run number to process.")
        instructions_run.setFont(font)
        layout.addWidget(instructions_run, row_id, 1, 1, 2)

        row_id += 1
        self.run_number_ledit = QtWidgets.QLineEdit()
        self.run_number_ledit.setValidator(QtGui.QIntValidator())
        self.run_number_ledit.returnPressed.connect(self.detect_fit_results)
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
        self.data_dir = PathSelector("input_data", self, "Data directory", 
                                        "Click to directory containing reduced time-resolved data.",
                                        select_dir=True)
        row_id = self.data_dir.attach(layout, row_id, self.data_dir_call_back)

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

        # Select fit direction
        instructions_options = QLabel(self)
        instructions_options.setText("Select the fit order and data range.")
        instructions_options.setFont(font)
        layout.addWidget(instructions_options, row_id, 1, 1, 2)
        row_id += 1

        self.fit_direction = QtWidgets.QCheckBox("Fit forward")
        layout.addWidget(self.fit_direction, row_id, 1)

        row_id += 1
        self.first_time_ledit = QtWidgets.QLineEdit()
        self.first_time_ledit.setValidator(QtGui.QIntValidator())
        layout.addWidget(self.first_time_ledit, row_id, 1)
        self.first_time_label = QLabel(self)
        self.first_time_label.setText("First time index [usually 0]")
        layout.addWidget(self.first_time_label, row_id, 2)
        spacer = QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum,
                             QtWidgets.QSizePolicy.Expanding)

        row_id += 1
        self.last_time_ledit = QtWidgets.QLineEdit()
        self.last_time_ledit.setValidator(QtGui.QIntValidator())
        layout.addWidget(self.last_time_ledit, row_id, 1)
        self.last_time_label = QLabel(self)
        self.last_time_label.setText("Last time index [leave empty or -1 for all]")
        layout.addWidget(self.last_time_label, row_id, 2)
        spacer = QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum,
                             QtWidgets.QSizePolicy.Expanding)
        row_id += 1

        # refl1d model file
        text = (
            "Select a name and location for a new model file.\n"
            + "You can modify this file to adjust fit parameters."
        )
        self.model_file = PathSelector("model_file", self, "Model file to create",
                                       text, select_dir=False, create_file=True)
        row_id = self.model_file.attach(layout, row_id)

        # Output directory
        self.output_dir = PathSelector("output_dir", self, "Output directory", 
                                        "",
                                        select_dir=True)
        row_id = self.output_dir.attach(layout, row_id)


        spacer = QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum,
                             QtWidgets.QSizePolicy.Minimum)
        layout.addItem(spacer, row_id, 1)

        # Process button
        row_id += 1
        self.create_model = QPushButton('Create model')
        self.create_model.setStyleSheet("background-color : orange")
        layout.addWidget(self.create_model, row_id, 1)

        self.perform_fits = QPushButton('Process')
        self.perform_fits.setStyleSheet("background-color : green")
        layout.addWidget(self.perform_fits, row_id, 2)

        self.analyze = QPushButton('Analyze')
        self.analyze.setStyleSheet("background-color : steelblue")
        layout.addWidget(self.analyze, row_id, 3)

        # connections
        row_id += 1
        self.perform_fits.clicked.connect(self.process)
        self.create_model.clicked.connect(self.create_model_file)
        self.analyze.clicked.connect(self.analyze_results)

        # Populate from previous session
        self.read_settings()

    def data_dir_call_back(self, path):
        files = os.listdir(path)
        run_number = self.run_number_ledit.text()
        files = [f for f in files if f.startswith('r%s_t' % run_number) and f .endswith('.txt')]
        self.first_time_ledit.setText('0')
        self.last_time_ledit.setText(str(len(files)))
    
    def detect_fit_results(self):
        run_number = int(self.run_number_ledit.text())
        fit_dir = os.path.join(os.path.expanduser('~'), 'reflectivity_fits')
        if os.path.isdir(fit_dir):
            before = run_number - 100
            after = run_number + 100
            fit_before = ''
            fit_after = ''
            for _dir in os.listdir(fit_dir):
                if os.path.isdir(os.path.join(fit_dir, _dir)):
                    for _run_dir in os.listdir(os.path.join(fit_dir, _dir)):
                        try:
                            raiseit=False
                            _run = int(_run_dir)
                            if _run < run_number and _run > before:
                                before = _run
                                fit_before = os.path.join(fit_dir, _dir, _run_dir, '__model-expt.json')
                                  
                            elif _run > run_number and _run < after:
                                after = _run
                                fit_after = os.path.join(fit_dir, _dir, _run_dir, '__model-expt.json')
                        except:
                            continue

            if os.path.isfile(fit_before):
                self.initial_state_file.set_value(fit_before)
            if os.path.isfile(fit_after):
                self.final_state_file.set_value(fit_after)

    def read_settings(self):
        """
        Read settings from the last session not covered by the PathSelector objects
        """
        _run_number = self.settings.value("tr_bayes_run_number", '')
        self.run_number_ledit.setText(_run_number)
        self.first_time_ledit.setText(self.settings.value("tr_bayes_first_time", '0'))
        self.last_time_ledit.setText(self.settings.value("tr_bayes_last_time", '-1'))

    def save_settings(self):
        self.settings.setValue('tr_bayes_run_number', self.run_number_ledit.text())
        self.settings.setValue('tr_bayes_first_time', self.first_time_ledit.text())
        self.settings.setValue('tr_bayes_last_time', self.last_time_ledit.text())

    def check_inputs(self):
        error = None
        # Check files and output directory
        if not os.path.isdir(self.output_dir.path_label.text()):
            error = "The chosen output directory could not be found"

        if self.first_time_ledit.text() == '':
            self.first_time_ledit.setText('0')
        if self.last_time_ledit.text() == '':
            self.last_time_ledit.setText('-1')

        # Pop up a dialog if there were invalid inputs
        if error:
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

    def create_model_file(self):
        """
            Create a model file based on the initual or final state.
        """
        fit_forward = self.fit_direction.isChecked()
        init_json = self.initial_state_file.path_label.text()
        final_json = self.final_state_file.path_label.text()
        model_path = self.model_file.path_label.text()
        if not os.path.isdir(os.path.dirname(model_path)):
            self.show_dialog("The chosen model file directory could not be found")
            return

        template_str = template.create_model(init_json, final_json, fit_forward=fit_forward)

        with open(model_path, 'w') as fd:
            fd.write(template_str)

    def process(self):
        """
            Execute the fitting loop
        """
        if not self.check_inputs():
            print("Invalid inputs found")
            return

        self.save_settings()

        print("Processing!")
        try:
            fitting_loop.execute_fit(int(self.run_number_ledit.text()), self.data_dir.path_label.text(),
                                    self.model_file.path_label.text(), self.initial_state_file.path_label.text(),
                                    self.final_state_file.path_label.text(),
                                    self.output_dir.path_label.text(),
                                    fit_forward=self.fit_direction.isChecked(),
                                    first_item=int(self.first_time_ledit.text()),
                                    last_item=int(self.last_time_ledit.text()))

            summary_plots.main(int(self.run_number_ledit.text()), self.data_dir.path_label.text(),
                               self.model_file.path_label.text(), self.initial_state_file.path_label.text(),
                               self.final_state_file.path_label.text(),
                               self.output_dir.path_label.text(),
                               first_item=int(self.first_time_ledit.text()),
                               last_item=int(self.last_time_ledit.text()))
        except Exception as exc:
            print(exc)
            self.show_dialog(str(exc))
        print("Completed!")

    def analyze_results(self):
        """
            Run the analysis on the results
        """
        if not self.check_inputs():
            print("Invalid inputs found")
            return

        self.save_settings()

        print("Analyzing!")
        try:
            summary_plots.main(int(self.run_number_ledit.text()), self.data_dir.path_label.text(),
                            self.model_file.path_label.text(), self.initial_state_file.path_label.text(),
                            self.final_state_file.path_label.text(),
                            self.output_dir.path_label.text(),
                            first_item=int(self.first_time_ledit.text()),
                            last_item=int(self.last_time_ledit.text()))
        except Exception as exc:
            print(exc)
            self.show_dialog(str(exc))
        print("Completed!")
