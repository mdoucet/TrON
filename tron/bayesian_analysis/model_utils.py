import os
import json
import numpy as np

import refl1d
from refl1d.names import QProbe, Parameter, SLD, Slab, Experiment

ERR_MIN_ROUGH = 3
ERR_MIN_THICK = 5
ERR_MIN_RHO = 0.2


def print_model(model0, model1):
    print("                   Initial \t            Step")
    for p in model0.keys():
        if p in model1:
            print("%15s %7.3g +- %-7.2g \t %7.3g +- %-7.2g" % (p, model0[p]['best'], model0[p]['std'],
                                                               model1[p]['best'], model1[p]['std']))
        else:
            print("%15s %7.3g +- %-7.2g" % (p, model0[p]['best'], model0[p]['std']))


def sample_from_json_file(model_expt_json_file, model_err_json_file=None,
                          prior_scale=1, set_ranges=False):
    """
        Return the sample object described by the provided json data.

        If model_err_json is provided, it will be used to set the width of
        the prior distribution.
    """
    with open(model_expt_json_file, 'r') as fd:
        expt = json.load(fd)

    err = None
    if model_err_json_file:
        with open(model_err_json_file, 'r') as fd:
            err = json.load(fd)

    return sample_from_json(expt, model_err_json=err,
                            prior_scale=prior_scale, set_ranges=set_ranges)

def sample_from_json(model_expt_json, model_err_json=None, prior_scale=1, set_ranges=False):
    """
        Return the sample object described by the provided json data.

        If model_err_json is provided, it will be used to set the width of
        the prior distribution.
    """
    sample = None
    for layer in model_expt_json['sample']['layers']:
        # dict_keys(['type', 'name', 'thickness', 'interface', 'material', 'magnetism'])

        rho = layer['material']['rho']['value']
        rho_fixed = layer['material']['rho']['fixed']
        rho_limits = layer['material']['rho']['bounds']['limits']
        rho_std = 0

        irho = layer['material']['irho']['value']
        irho_fixed = layer['material']['irho']['fixed']
        irho_limits = layer['material']['irho']['bounds']['limits']
        irho_std = 0

        thickness = layer['thickness']['value']
        thickness_fixed = layer['thickness']['fixed']
        thickness_limits = layer['thickness']['bounds']['limits']
        thickness_std = 0

        interface = layer['interface']['value']
        interface_fixed = layer['interface']['fixed']
        interface_limits = layer['interface']['bounds']['limits']
        interface_std = 0

        if model_err_json:
            if layer['material']['rho']['name'] in model_err_json:
                if prior_scale > 0:
                    rho_std = prior_scale*model_err_json[layer['material']['rho']['name']]['std'] + ERR_MIN_RHO
                else:
                    rho_std = 0
            if layer['material']['irho']['name'] in model_err_json:
                if prior_scale > 0:
                    irho_std = prior_scale*model_err_json[layer['material']['irho']['name']]['std'] + ERR_MIN_RHO
                else:
                    irho_std = 0
            if layer['thickness']['name'] in model_err_json:
                if prior_scale > 0:
                    thickness_std = prior_scale*model_err_json[layer['thickness']['name']]['std'] + ERR_MIN_THICK
                else:
                    thickness_std = 0
            if layer['interface']['name'] in model_err_json:
                if prior_scale > 0:
                    interface_std = prior_scale*model_err_json[layer['interface']['name']]['std'] + ERR_MIN_ROUGH
                else:
                    interface_std = 0

        material = SLD(name=layer['name'], rho=rho, irho=irho)

        slab = Slab(material=material, thickness=thickness, interface=interface)

        # Set the range for each tunable parameter
        if not rho_fixed:
            if rho_std > 0:
                slab.material.rho.dev(rho_std, limits=(rho_limits[0], rho_limits[1]))
            else:
                slab.material.rho.range(rho_limits[0], rho_limits[1])
            slab.material.rho.fixed = not set_ranges
        if not irho_fixed:
            if irho_std > 0:
                slab.material.irho.dev(irho_std, limits=(irho_limits[0], irho_limits[1]))
            else:
                slab.material.irho.range(irho_limits[0], irho_limits[1])
            slab.material.irho.fixed = not set_ranges
        if not thickness_fixed:
            print("Setting thickness")
            if thickness_std > 0:
                print(thickness_std)
                slab.thickness.dev(thickness_std, limits=(thickness_limits[0], thickness_limits[1]))
                print(slab.thickness.distribution.std)
            else:
                slab.thickness.range(thickness_limits[0], thickness_limits[1])
            slab.thickness.fixed = not set_ranges
        if not interface_fixed:
            if interface_std > 0:
                slab.interface.dev(interface_std, limits=(interface_limits[0], interface_limits[1]))
            else:
                slab.interface.range(interface_limits[0], interface_limits[1])
            slab.interface.fixed = not set_ranges

        sample = slab if sample is None else sample | slab
    return sample


def expt_from_json_file(model_expt_json_file, q=None, q_resolution=0.025, probe=None,
                        model_err_json_file=None, prior_scale=1, set_ranges=False):
    """
        Return the experiment object described by the provided json data.

        If model_err_json is provided, it will be used to set the width of
        the prior distribution.
    """
    with open(model_expt_json_file, 'r') as fd:
        expt = json.load(fd)

    err = None
    if model_err_json_file:
        with open(model_err_json_file, 'r') as fd:
            err = json.load(fd)

    return expt_from_json(expt, q=q, q_resolution=q_resolution, probe=probe,
                          model_err_json=err, prior_scale=prior_scale,
                          set_ranges=set_ranges)


def expt_from_json(model_expt_json, q=None, q_resolution=0.025, probe=None,
                   model_err_json=None, prior_scale=1, set_ranges=False):
    """
        Return the experiment object described by the provided json data.

        If model_err_json is provided, it will be used to set the width of
        the prior distribution.
    """
    if q is None:
        q = np.linspace(0.005, 0.2, 100)

    # The QProbe object represents the beam
    if probe is None:
        zeros = np.zeros(len(q))
        dq = q_resolution * q
        probe = QProbe(q, dq, data=(zeros, zeros))

    sample = sample_from_json(model_expt_json,
                              model_err_json=model_err_json,
                              prior_scale=prior_scale, set_ranges=set_ranges)

    intensity = model_expt_json['probe']['intensity']['value']
    intensity_fixed = model_expt_json['probe']['intensity']['fixed']
    intensity_limits = model_expt_json['probe']['intensity']['bounds']['limits']
    intensity_std = 0

    background = model_expt_json['probe']['background']['value']
    background_fixed = model_expt_json['probe']['background']['fixed']
    background_limits = model_expt_json['probe']['background']['bounds']['limits']
    background_std = 0

    if model_err_json:
        if model_expt_json['probe']['intensity']['name'] in model_err_json:
            intensity_std = model_err_json[model_expt_json['probe']['intensity']['name']]['std']
        if model_expt_json['probe']['background']['name'] in model_err_json:
            background_std = model_err_json[model_expt_json['probe']['background']['name']]['std']

    probe.intensity = Parameter(value=intensity,
                                center=intensity, width=intensity_std,
                                name=model_expt_json['probe']['intensity']['name'])

    probe.background = Parameter(value=background,
                                 center=background, width=background_std,
                                 name=model_expt_json['probe']['background']['name'])
    if set_ranges:
        if not background_fixed:
            probe.intensity.range(background_limits[0], background_limits[1])
        if not intensity_fixed:
            probe.background.range(intensity_limits[0], intensity_limits[1])

    return Experiment(probe=probe, sample=sample)


def calculate_reflectivity(model_expt_json_file, q, q_resolution=0.025):
    """
        Reflectivity calculation using refl1d
    """
    expt = expt_from_json_file(model_expt_json_file, q, q_resolution=q_resolution)
    _, r = expt.reflectivity()
    return r
