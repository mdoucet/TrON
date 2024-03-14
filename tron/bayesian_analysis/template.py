"""
    Create a model from the sample object described by an existing model.
"""
import json


def create_model(initial_expt_file, final_expt_file, fit_forward=False):
    """
        Return a refl1d model from the sample object described by an existing model.
    """
    if fit_forward:
        ranges = template_ranges_from_json(json.load(open(initial_expt_file)))
    else:
        ranges = template_ranges_from_json(json.load(open(final_expt_file)))
    
    return _model_template.replace("$ranges", ranges)


def template_ranges_from_json(model_expt_json, sample_name='sample'):
    """
        Return the sample object described by the provided json data.
    """
    ranges_str = ""

    for layer in model_expt_json['sample']['layers']:
        # dict_keys(['type', 'name', 'thickness', 'interface', 'material', 'magnetism'])

        rho = layer['material']['rho']['value']
        rho_fixed = layer['material']['rho']['fixed']
        rho_limits = layer['material']['rho']['bounds']['limits']

        irho = layer['material']['irho']['value']
        irho_fixed = layer['material']['irho']['fixed']
        irho_limits = layer['material']['irho']['bounds']['limits']

        thickness = layer['thickness']['value']
        thickness_fixed = layer['thickness']['fixed']
        thickness_limits = layer['thickness']['bounds']['limits']

        interface = layer['interface']['value']
        interface_fixed = layer['interface']['fixed']
        interface_limits = layer['interface']['bounds']['limits']

        if not rho_fixed:
            ranges_str += f"{sample_name}['{layer['material']['name']}'].material.rho.range({rho_limits[0]}, {rho_limits[1]})\n"
        if not irho_fixed:
            ranges_str += f"{sample_name}['{layer['material']['name']}'].material.irho.range({irho_limits[0]}, {irho_limits[1]})\n"
        if not thickness_fixed:
            ranges_str += f"{sample_name}['{layer['material']['name']}'].thickness.range({thickness_limits[0]}, {thickness_limits[1]})\n"
        if not interface_fixed:
            ranges_str += f"{sample_name}['{layer['material']['name']}'].interface.range({interface_limits[0]}, {interface_limits[1]})\n"
        ranges_str += "\n"

    return ranges_str

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
