import os
import time
import json
import subprocess
import shutil

import model_utils


class FittingLoop():
    
    def __init__(self, dyn_data_dir, results_dir, model_dir=None, model_name='__model',
                 initial_err_file=None, initial_expt_file=None,
                 final_err_file=None, final_expt_file=None,
                ):
        
        # For from early times onward. False goes back in time
        self.fit_forward = True
        self.dyn_file_list = []
        self.model_dir = model_dir
        self.model_name = model_name

        # Directory where that dynamic data is
        self.dyn_data_dir = dyn_data_dir
        
        # Directory where we store the results
        self.results_dir = results_dir

        # Initial and final states. Initial is before dynamic data, and
        # final is after.
        self.initial_err_file = initial_err_file
        self.initial_expt_file = initial_expt_file
        self.final_err_file = final_err_file
        self.final_expt_file = final_expt_file

        self.last_output = ''

    def save(self, file_path):
        """
            Save all the settings to file
        """
        meta_data = dict(model_dir=self.model_dir, model_name=self.model_name,
                         dyn_data_dir=self.dyn_data_dir, results_dir=self.results_dir,
                         initial_err_file=self.initial_err_file,
                         initial_expt_file=self.initial_expt_file,
                         final_err_file=self.final_err_file,
                         final_expt_file=self.final_expt_file,
                         dyn_file_list=self.dyn_file_list,
                         fit_forward=self.fit_forward)
        with open(file_path, 'w') as fd:
            json.dump(meta_data, fd)
    
    def load(self, file_path):
        """
            Load settings from file
        """
        with open(file_path, 'r') as fd:
            meta_data = json.load(fd)
        self.model_dir = meta_data['model_dir']
        self.model_name = meta_data['model_name']
        self.dyn_data_dir = meta_data['dyn_data_dir']
        self.results_dir = meta_data['results_dir']
        self.initial_err_file = meta_data['initial_err_file']
        self.initial_expt_file = meta_data['initial_expt_file']
        self.final_err_file = meta_data['final_err_file']
        self.final_expt_file = meta_data['final_expt_file']
        self.fit_forward = meta_data['fit_forward']
        self.dyn_file_list = meta_data['dyn_file_list']

    def __str__(self):
        print("Model: %s" % os.path.join(self.model_dir, self.model_name))
        print("Data: %s" % self.dyn_data_dir)
        print("Results: %s" % self.results_dir)
        print("Initial state: %s" % self.initial_expt_file)
        print("Final state: %s" % self.final_expt_file)
        
    def print_initial_final(self):
        with open(self.initial_err_file, 'r') as fd:
            initial_model = json.load(fd)
        with open(self.final_err_file, 'r') as fd:
            final_model = json.load(fd)
        model_utils.print_model(initial_model, final_model)

    def fit(self, dyn_file_list, fit_forward=True):
        """
            Execute the fitting loop.

            :param dyn_file_list: list of time-resolved data sets, ordered in increasing times
        """
        self.fit_forward = fit_forward
        self.dyn_file_list = dyn_file_list

        # Clean results directory so we don't mix up results
        if os.path.isdir(self.results_dir):
            shutil.rmtree(self.results_dir)
        os.mkdir(self.results_dir)

        # Save parameters so we know what we did
        self.save(os.path.join(self.results_dir, 'fit_parameters.json'))

        # If we are fitting starting from the final state, get an iterator reversing the file order
        _ordered_files = dyn_file_list if self.fit_forward else reversed(dyn_file_list)

        if self.fit_forward:
            starting_expt = self.initial_expt_file
            starting_err = self.initial_err_file
        else:
            starting_expt = self.final_expt_file
            starting_err = self.final_err_file
        
        # Initialize our time series of models
        with open(starting_err, 'r') as fd:
            initial_model = json.load(fd)
        time_series = [initial_model]

        t0 = time.time()
        t1 = time.time()
        for _file in _ordered_files:
            print("Fitting %s" % _file)
            _base_name, _ = os.path.splitext(_file)
            data_to_fit = os.path.join(self.dyn_data_dir, _file)
            command = ['refl1d_cli.py', '--fit=dream', '--steps=1000', '--burn=1000', '--batch', '--overwrite',
                       '--store=%s' % os.path.join(self.results_dir, _base_name), 
                       os.path.join(self.model_dir, '%s.py' % self.model_name),
                       data_to_fit, starting_expt, starting_err]

            self.last_output = subprocess.run(command, capture_output=True, text=True)

            # Update the starting model with the fit we just did
            _model = os.path.join(self.results_dir, _base_name, '%s-expt.json' % self.model_name)
            _err = os.path.join(self.results_dir, _base_name, '%s-err.json' % self.model_name)
            starting_model = _model
            starting_err = _err

            print(starting_model)

            with open(os.path.join(_err), 'r') as fd:
                updated_model = json.load(fd)
                time_series.append(updated_model)

            model_utils.print_model(time_series[-2], time_series[-1])

            total_time = (time.time()-t0)/60
            item_time = time.time()-t1
            t1 = time.time()
            print("    Completed: %g s [total=%g m]" % (item_time, total_time))
