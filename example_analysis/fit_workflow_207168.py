import sys
import os
import numpy as np
import json
import subprocess
import time

import importlib
from tron.bayesian_analysis import model_utils, fitting_loop


# Data analysis directory
project_dir = os.path.expanduser('~/git/TrON/example_analysis')

# Upper-level data directory for the time-resolved data
data_dir = os.path.join(project_dir, 'data')

# Directory where we store dynamic fit results
dyn_model_dir = os.path.join(project_dir, 'dyn-fitting')


# Initial data set and model (starting point)
initial_err_file = os.path.join(dyn_model_dir, '207161', '__model-err.json')
initial_expt_file = os.path.join(dyn_model_dir, '207161', '__model-expt.json')

final_err_file = os.path.join(dyn_model_dir, '207169', '__model-err.json')
final_expt_file = os.path.join(dyn_model_dir, '207169', '__model-expt.json')

dynamic_run = 207168

# Create top-level directory for the dynamic fits
if not os.path.exists(os.path.join(dyn_model_dir, f'{dynamic_run}-dyn')):
    os.makedirs(os.path.join(dyn_model_dir, f'{dynamic_run}-dyn'))

store_basename = os.path.join(
    dyn_model_dir, f'{dynamic_run}-dyn/results-30s-bck'
)

results_dir = os.path.join(dyn_model_dir, store_basename)

loop = fitting_loop.FittingLoop(data_dir, results_dir=results_dir, model_dir=project_dir, model_name='model-loop-207168',
                                initial_err_file=initial_err_file, initial_expt_file=initial_expt_file,
                                final_err_file=final_err_file, final_expt_file=final_expt_file,
                )

print(loop)
loop.print_initial_final()

_file_list = sorted(os.listdir(data_dir))
_good_files = [_f for _f in _file_list if _f.startswith('r%d_t' % dynamic_run)]

loop.fit(_good_files, fit_forward=False)
