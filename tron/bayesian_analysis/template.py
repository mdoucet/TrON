"""
Create a model from the sample object described by an existing model.
"""
from . import model_utils


def create_model(starting_expt_file, sample_name="sample"):
    """
    Return a refl1d model from the sample object described by an existing model.
    """
    expt = model_utils.expt_from_json_file(
        starting_expt_file, keep_original_ranges=True
    )

    ranges_str = ""
    for layer in expt.sample.layers:
        if not layer.material.rho.fixed:
            ranges_str += (
                f"{sample_name}['{layer.material.name}'].material.rho.range("
                f"{layer.material.rho.bounds[0]}, {layer.material.rho.bounds[1]})\n"
            )
        if not layer.material.irho.fixed:
            ranges_str += (
                f"{sample_name}['{layer.material.name}'].material.irho.range("
                f"{layer.material.irho.bounds[0]}, {layer.material.irho.bounds[1]})\n"
            )
        if not layer.thickness.fixed:
            ranges_str += (
                f"{sample_name}['{layer.material.name}'].thickness.range("
                f"{layer.thickness.bounds[0]}, {layer.thickness.bounds[1]})\n"
            )
        if not layer.interface.fixed:
            ranges_str += (
                f"{sample_name}['{layer.material.name}'].interface.range("
                f"{layer.interface.bounds[0]}, {layer.interface.bounds[1]})\n"
            )

    return _model_template.replace("$ranges", ranges_str)


_model_template = """import sys
import numpy as np
import os

from refl1d.names import QProbe, Parameter, FitProblem
from tron.bayesian_analysis import model_utils


# Parse input arguments ########################################################
# First argument is the data file to use
reduced_file = sys.argv[1]

# Second argument is the starting model [experiment description]
expt_file = sys.argv[2]

# Third argument is the error information used for setting the prior
err_file = sys.argv[3]

# 0.1 was used so far (Jan 2023) with good results
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

sample = expt.sample
$ranges

#probe.intensity.range(0.90, 1.1)

################################################################################
problem = FitProblem(expt)
"""
