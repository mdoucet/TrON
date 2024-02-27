"""
refl1d_cli.py --fit=dream --steps=100 --burn=100 --store=results model-loop.py

Use --batch is you dont' want to see the output and pop up the plots.
"""
import sys
import numpy as np
import os

from refl1d.names import QProbe, Parameter, FitProblem
sys.path.append(os.path.expanduser('~/git/analysis_playground/bayesian-fitting'))
import model_utils

import warnings
import matplotlib.cbook
warnings.filterwarnings("ignore",category=matplotlib.cbook.mplDeprecation)
warnings.simplefilter('ignore', UserWarning)

# Parse input arguments ########################################################
# First argument is the data file to use
reduced_file = sys.argv[1]

# Second argument is the starting model [experiment description]
expt_file = sys.argv[2]

# Third argument is the error information used for setting the prior
err_file = sys.argv[3]

# 0.1 was used so far (Jan 2023) with good results
#prior_scale = 0.1
prior_scale = 1

# Load data ####################################################################
q_min = 0.0
q_max = 0.4

try:
    Q, R, dR, dQ = np.loadtxt(reduced_file).T
except:
    Q, R, dR = np.loadtxt(reduced_file).T
    dQ = 0.028*Q

i_min = np.min([i for i in range(len(Q)) if Q[i]>q_min])
i_max = np.max([i for i in range(len(Q)) if Q[i]<q_max])+1

# SNS data is FWHM
dQ_std = dQ/2.35
probe = QProbe(Q[i_min:i_max], dQ_std[i_min:i_max], data=(R[i_min:i_max], dR[i_min:i_max]))

# Experiment ###################################################################
expt = model_utils.expt_from_json_file(expt_file, probe=probe,
                                       model_err_json_file=err_file,
                                       prior_scale=prior_scale, set_ranges=False)

#sample['material'].thickness = constraint_thickness(sample['material'].thickness)

#expt.sample['Ti'].interface.range(1.0, 35.0)
expt.sample['Ti'].material.rho.range(-2.0, 0)


#expt.sample['Cu'].interface.range(5.0, 22.0)
#expt.sample['Cu'].thickness.range(expt.sample['Cu'].thickness.value*0.97, expt.sample['Cu'].thickness.value*1.03)


expt.sample['material'].thickness.range(expt.sample['material'].thickness.value-5, expt.sample['material'].thickness.value+5)
expt.sample['material'].material.rho.range(-1.0, 5.5) # Cu-K was 4.0
#expt.sample['material'].material.irho.range(0.0, 0.3)
#expt.sample['material'].interface.range(1.0, 22.0)
expt.sample['material'].interface.range(5, expt.sample['material'].thickness.value/2+5)


expt.sample['SEI'].thickness.range(55.0, 300.0)
expt.sample['SEI'].material.rho.range(3, 6.3)
#expt.sample['SEI'].material.irho.range(0.0, 0.3)
expt.sample['SEI'].interface.range(8.0, 25.0)

neigh_thick = min(expt.sample['material'].thickness.value, expt.sample['SEI'].thickness.value)

#expt.sample['SEI'].interface.range(5, expt.sample['material'].thickness.value/2+5)
#expt.sample['SEI'].interface.range(5, neigh_thick+5)

def thf_rough(thick):
    return thick/2.0

expt.sample['THF'].interface.range(15.0, 150.0)
#expt.sample['THF'].interface.range(5, expt.sample['SEI'].thickness.value/2+5)
#expt.sample['THF'].interface = thf_rough(expt.sample['SEI'].thickness)

#probe.intensity.range(0.95, 1.8)

################################################################################
problem = FitProblem(expt)
