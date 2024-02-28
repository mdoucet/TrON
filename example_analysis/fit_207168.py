import sys
import os
import numpy as np
import json
import subprocess
import time

sys.path.append(os.path.expanduser('~/git/TrON/bayesian_analysis'))
import importlib
import model_utils
importlib.reload(model_utils)
import fitting_loop
importlib.reload(fitting_loop)

# Data analysis directory
project_dir = os.path.expanduser('~/git/TrON/example_analysis')

# Upper-level data directory for the time-resolved data
data_dir = os.path.join(project_dir, 'data')

# Directory where we store dynamic fit results
dyn_model_dir = os.path.join(project_dir, 'dyn-fitting')


# Initial data set and model (starting point)
initial_data_file = os.path.join(data_dir, 'REFL_207161_combined_data_auto.txt')
initial_data = np.loadtxt(initial_data_file).T

final_data_file = os.path.join(data_dir, 'REFL_207169_combined_data_auto.txt')
final_data = np.loadtxt(final_data_file).T

initial_err_file = os.path.join(dyn_model_dir, '207161', '__model-err.json')
initial_expt_file = os.path.join(dyn_model_dir, '207161', '__model-expt.json')

final_err_file = os.path.join(dyn_model_dir, '207169', '__model-err.json')
final_expt_file = os.path.join(dyn_model_dir, '207169', '__model-expt.json')

dynamic_run = 207168

# Create top-level directory for the dynamic fits
if not os.path.exists(os.path.join(dyn_model_dir, '%s-dyn' % dynamic_run)):
    os.makedirs(os.path.join(dyn_model_dir, '%s-dyn' % dynamic_run))

store_basename = os.path.join(dyn_model_dir, '%s-dyn/results-30s-bck' % dynamic_run)

results_dir = os.path.join(dyn_model_dir, store_basename)


loop = fitting_loop.FittingLoop(data_dir, results_dir=results_dir, model_dir=project_dir, model_name='model-loop-207168',
                                initial_err_file=initial_err_file, initial_expt_file=initial_expt_file,
                                final_err_file=final_err_file, final_expt_file=final_expt_file,
                )

try:
    print(loop)
    loop.print_initial_final()
except:
    print(loop.last_output)

PROCESS_ALL_DATA = True

first = 0
last = -1

if PROCESS_ALL_DATA:
    _file_list = sorted(os.listdir(data_dir))
    # Get only the files for the run we're interested in
    _good_files = [_f for _f in _file_list if _f.startswith('r%d_t' % dynamic_run)]
    #_good_files = _good_files[first:last]

try:
    print(_good_files)
    loop.fit(_good_files, fit_forward=False)
except:
    raise
    print(loop.last_output)
