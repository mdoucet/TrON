import sys
import os
import json
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.lines as mlines

from matplotlib.path import Path
from matplotlib.patches import PathPatch

try:
    from bumps import dream
    import fit_uncertainties
    HAS_BUMPS  = True
except:
    print("No bumps")
    HAS_BUMPS = False


def read_model(model_path, dq=0.027):
    with open(model_path) as fd:
        print('Processing: %s' % model_path)
        code = fd.read()
        # The refl1d model we are reading was auto-generated. We need to replace
        # the data part in case the data file is no longer available.
        code = code.replace('reduced_file = "/SNS/users/m2d/__data.txt"', 'Q = np.arange(0.008, 1., 0.01)')
        code = code.replace('reduced_file =', 'Q = np.arange(0.008, 1., 0.01)\n# reduced_file =')
        code = code.replace('expt_file =', 'expt_file = "%s"\n# ' % model_path.replace('.py', '-expt.json'))
        code = code.replace('err_file =', 'err_file = "%s"\n# ' % model_path.replace('.py', '-err.json'))
        code = code.replace('Q, R, dR, dQ = numpy.loadtxt(reduced_file).T', 'dQ = Q*%s' % dq)
        code = code.replace('Q, R, dR, dQ = np.loadtxt(reduced_file).T', 'dQ = Q*%s' % dq)
        code = code.replace(', data=(R[i_min:i_max], dR[i_min:i_max])', '')
        exec(code, globals())
        print("Read in %s" % model_path)


def plot_sld(run, title, fit_dir=None, show_cl=True, dq=0.027, z_offset=0.0):
    """
        :param ar_dir: Automated-reduction directory
    """
    sld_file = os.path.join(fit_dir, str(run), "__model-profile.dat")
    print(sld_file)
    if not os.path.isfile(sld_file):
        print("Could not find %s" % sld_file)
        return
    pre_sld = np.loadtxt(sld_file).T

    mcmc_file = os.path.join(fit_dir, str(run), "__model-chain.mc")
    mcmc_found = os.path.isfile(mcmc_file)
    if show_cl and not mcmc_found:
        print("MCMC not available: %s" % mcmc_file)
    if show_cl and HAS_BUMPS and mcmc_found:
        # Load the model that was used for fitting
        read_model(os.path.join(fit_dir, str(run), '__model.py'))
        model_path = os.path.join(fit_dir, str(run), '__model')
        state = dream.state.load_state(model_path)
        z_max = pre_sld[0][-1]-pre_sld[0][0]
        print("Z offset = %g;    Z_max = %g" % (pre_sld[0][0], z_max))
        acc_data = fit_uncertainties.load_bumps(model_path, problem, state=state,
                                                trim=10,
                                                z_min=0, #_data[0][0],
                                                z_max=z_max)[0]

        _z, _q = acc_data.quantiles(90)
        _z = np.asarray(_z)+z_offset
        plt.fill_between(_z, _q[0][0], _q[0][1], alpha=0.2)
        #z, sld, dsld = acc_data.mean()
        #plt.fill_between(z[1:], sld[1:]-dsld[1:], sld[1:]+dsld[1:],
        #                alpha=0.2)
    plt.plot(pre_sld[0][-1]-pre_sld[0]+z_offset, pre_sld[1], markersize=4, label=title, linewidth=2, )


def plot_fit(run, title, fit_dir=None, ar_dir=None, scale=1):
    data_file = os.path.join(ar_dir, 'REFL_%s_combined_data_auto.txt' % run)
    _data = np.loadtxt(data_file).T

    fit_file = os.path.join(fit_dir, str(run), "__model-refl.dat")
    _fit = np.loadtxt(fit_file).T

    plt.errorbar(_data[0], _data[1]*scale, yerr=_data[2]*scale, linewidth=1, 
                 markersize=4, marker='.', linestyle='', label=title)

    plt.plot(_fit[0], _fit[4]*scale, linewidth=1, markersize=2, marker='', color='grey', zorder=4)


def plot_dyn_data(dynamic_run, initial_state, final_state, first_index=0, last_index=-1, delta_t=30,
                  fit_dir=None, ar_dir=None, dyn_data_dir=None, dyn_fit_dir=None, model_name='__model', scale=1):
    # Reduced data
    pre_data_file = os.path.join(ar_dir, 'REFL_%s_combined_data_auto.txt' % initial_state)
    pre_data = np.loadtxt(pre_data_file).T

    post_data = None
    if final_state is not None:
        post_data_file = os.path.join(ar_dir, 'REFL_%s_combined_data_auto.txt' % final_state)
        post_data = np.loadtxt(post_data_file).T

    # Fit results
    pre_fit = None
    pre_fit_file = os.path.join(fit_dir, str(initial_state), "__model-refl.dat")
    if os.path.isfile(pre_fit_file):
        pre_fit = np.loadtxt(pre_fit_file).T

    post_fit = None
    post_fit_file = os.path.join(fit_dir, str(final_state), "__model-refl.dat")
    if os.path.isfile(post_fit_file):
        post_fit = np.loadtxt(post_fit_file).T

    # Dynamic data
    _file_list = sorted(os.listdir(dyn_data_dir))
    fig, ax = plt.subplots(dpi=150, figsize=(5,8))
    plt.subplots_adjust(left=0.15, right=.95, top=0.98, bottom=0.1)

    #plt.plot(pre_data[0], pre_data[1], linewidth=1, color='darkgreen', label='initial')
    idx = pre_data[2]<pre_data[1]
    plt.errorbar(pre_data[0][idx], pre_data[1][idx], yerr=pre_data[2][idx], linewidth=1, 
                 markersize=2, marker='.', linestyle='',
                 color='darkgreen', label='Pre cycle 1')

    if pre_fit is not None:
        plt.plot(pre_fit[0], pre_fit[4], linewidth=1, markersize=2, marker='', color='black', zorder=400)

    # Get only the files for the run we're interested in
    _good_files = [_f for _f in _file_list if _f.startswith('r%d_t' % dynamic_run)]

    print(len(_good_files))

    scale = 1.
    multiplier = 10
    file_list = []
    for _file in _good_files[first_index:last_index]:
        if _file.startswith('r%d_t' % dynamic_run):
            scale *= 1
            _data = np.loadtxt(os.path.join(dyn_data_dir, _file)).T
            _data_name, _ = os.path.splitext(_file)
            _time = int(_data_name.replace('r%d_t' % dynamic_run, ''))
            _label = '%d < t < %d s' % (_time, _time+delta_t)
 
            # Get fit if it exists
            fit_file = os.path.join(dyn_fit_dir, _data_name, '%s-refl.dat' % model_name)
            #print("Looking for: %s" % fit_file)

            if os.path.isfile(fit_file):
                fit_data = np.loadtxt(fit_file).T
                plt.plot(fit_data[0], fit_data[4]*scale, markersize=2, marker='', linewidth=1, color='black')

            if len(_data)>1:
                idx = _data[2]<_data[1]
                plt.errorbar(_data[0][idx], _data[1][idx]*scale,
                             yerr=_data[2][idx]*scale, linewidth=1,
                             markersize=2, marker='.',  linestyle='', label=_label)

                scale *= multiplier
                file_list.append([_time, _data_name, _data_name])
                #[8010, 'r201289_t008010', '2215784']
            else:
                pass
                #print("%s is empty" % _file)

    final_scale = scale/multiplier
    if post_fit is not None:
        plt.plot(post_fit[0], post_fit[4]*final_scale, linewidth=1, color='darkblue')#, label='final')
    if post_data is not None:
        idx = post_data[2]<post_data[1]
        plt.errorbar(post_data[0][idx], post_data[1][idx]*final_scale, yerr=post_data[2][idx]*final_scale, linewidth=1, 
                     markersize=2, marker='.', linestyle='',
                     color='darkgreen', label='Post cycle 1')

    handles, labels = ax.get_legend_handles_labels()
    plt.legend(handles[::-1], labels[::-1], frameon=False, prop={'size': 7})
    plt.xlabel('Q ($1/\AA$)', fontsize=15)
    plt.ylabel('Reflectivity', fontsize=15)
    plt.yscale('log')
    plt.xscale('log')
    ax.yaxis.labelpad = 1

    plt.show()
    return file_list


def plot_dyn_sld(file_list, initial_state, final_state, delta_t=15,
                 fit_dir=None, dyn_data_dir=None, dyn_fit_dir=None, model_name='__model',
                 model_file=None, show_cl=True, legend_font_size=6):

    fig, ax = plt.subplots(dpi=250, figsize=(5, 4.1))
    plt.subplots_adjust(left=0.15, right=.95, top=0.95, bottom=0.15)

    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']

    # Plot initial state
    i_color = 0
    if initial_state is not None:
        i_color = 1
        plot_sld(initial_state, 'Initial state', fit_dir=fit_dir, show_cl=False)  

    for _file in file_list:
        i_color += 1
        i_color = i_color % len(colors)
        profile_file = os.path.join(dyn_fit_dir, str(_file[2]), '%s-profile.dat' % model_name)
        if not os.path.isfile(profile_file):
            print("Could not find: %s" % profile_file)
            continue
        _data = np.loadtxt(profile_file).T
        
        if HAS_BUMPS and show_cl:
            mc_file = os.path.join(dyn_fit_dir, str(_file[2]), '%s-chain.mc' % model_name)
            if not os.path.isfile(mc_file):
                mc_file = os.path.join(dyn_fit_dir, str(_file[2]), '%s-chain.mc.gz' % model_name)
            if os.path.isfile(mc_file):
                if model_file is None:
                    model_file = os.path.join(dyn_fit_dir, str(_file[2]), '%s.py' % model_name)
                read_model(model_file)
                model_path = os.path.join(dyn_fit_dir, str(_file[2]), model_name)
                print("Model: %s" % model_path)
                state = dream.state.load_state(model_path)
                z_max = _data[0][-1]-_data[0][0]
                print("Z offset = %g;    Z_max = %g" % (_data[0][0], z_max))
                acc_data = fit_uncertainties.load_bumps(model_path, problem, state=state,
                                                        trim=1000,
                                                        z_min=0, #_data[0][0],
                                                        z_max=z_max)[0]

                _z, _q = acc_data.quantiles(90)
                plt.fill_between(_z, _q[0][0], _q[0][1], color=colors[i_color], alpha=0.2)
            else:
                print("MCMC not available: %s" % mc_file)
            
        _label = '%d < t < %d s' % (int(_file[0]), int(_file[0])+delta_t)
        plt.plot(_data[0][-1]-_data[0], _data[1], markersize=4, color=colors[i_color],
                 label=_label, linewidth=1, )

    # Plot final OCP
    if final_state is not None:
        plot_sld(final_state, 'Final state', fit_dir=fit_dir, show_cl=False)           
        
    handles, labels = ax.get_legend_handles_labels()
    #plt.legend(frameon=False, prop={'size': 10})
    plt.legend(handles[::-1], labels[::-1], loc='lower right', frameon=False, fontsize=legend_font_size)
    plt.xlabel('z ($\AA$)', fontsize=14)
    plt.ylabel('SLD ($10^{-6}/\AA^2$)', fontsize=14)
    plt.show()


def trend_data(file_list, initial_state, final_state, label='',
                 fit_dir=None, dyn_data_dir=None, dyn_fit_dir=None, model_name='__model',
                 model_file=None, newplot=True, plot_chi2=True, add_plot=0):
    """
        sei_thick.append(item['sei thickness'][which])
    sei_dthick.append(item['sei thickness']['std'])
    """
    # Get the varying parameters, which are assumed to be the same for all data sets
    par_file = os.path.join(dyn_fit_dir, str(file_list[0][2]), '%s.par' % model_name)
    if not os.path.isfile(par_file):
        par_file = os.path.join(dyn_fit_dir, str(file_list[-1][2]), '%s.par' % model_name)

    trend_data = dict()
    trend_err = dict()
    chi2 = []
    nlprior = []
    timestamp = []

    with open(par_file, 'r') as fd:
        for line in fd.readlines():
            par = ' '.join(line.split(' ')[0:2])
            if 'intensity' not in par:
                trend_data[par] = []
                trend_err[par] = []
                
    # Go through each file and retrieve the parameters
    # 'which' defines the value to select. It can either be 'mean' of 'best'.
    which = 'mean'
    for _file in file_list:
        err_file = os.path.join(dyn_fit_dir, str(_file[2]), '%s.err' % model_name)
        err_json = os.path.join(dyn_fit_dir, str(_file[2]), '%s-err.json' % model_name)
        bayes_json = os.path.join(dyn_fit_dir, str(_file[2]), '%s-bayes.dat' % model_name)

        if os.path.isfile(err_json):
            with open(bayes_json) as fd:
                for l in fd.readlines():
                    if l.startswith('NLL'):
                        toks = l.split(':')
                        _nll = float(toks[1])
                    if l.startswith('NLPrior'):
                        toks = l.split(':')
                        _nlprior = float(toks[1])
                    if l.startswith('Points'):
                        toks = l.split(':')
                        _npts = float(toks[1])
                chi2.append(_nll/_npts)
                nlprior.append(_nlprior/_npts)

            with open(err_json) as fd:
                m = json.load(fd)
                for par in trend_data.keys():
                    trend_data[par].append(m[par][which])
                    trend_err[par].append(m[par]['std'])

            timestamp.append(float(_file[0]))

    # Read initial and final states
    steady_values = dict()
    steady_err = dict()
    steady_times = dict()

    initial_file = os.path.join(fit_dir, str(initial_state), '__model-expt.json')
    if os.path.isfile(initial_file):
        with open(initial_file) as fd:
            m = json.load(fd)
            for par in trend_data.keys():
                for layer in m['sample']['layers']:
                    #print(layer)
                    rho = layer['material']['rho']
                    irho = layer['material']['irho']
                    thickness = layer['thickness']
                    interface = layer['interface']
                    for p in [rho, irho, thickness, interface]:
                        if p['name'] == par:
                            steady_values[par] = [p['value'], ]
                            steady_times[par] = [timestamp[0]-50, ]
                            print(par, p['value'])

    
    final_file = os.path.join(fit_dir, str(final_state), '__model-expt.json')
    if os.path.isfile(final_file):
        with open(final_file) as fd:
            m = json.load(fd)
            for par in trend_data.keys():
                for layer in m['sample']['layers']:
                    #print(layer)
                    rho = layer['material']['rho']
                    irho = layer['material']['irho']
                    thickness = layer['thickness']
                    interface = layer['interface']
                    for p in [rho, irho, thickness, interface]:
                        if p['name'] == par:
                            if p['name'] in steady_values:
                                steady_values[par].append(p['value'])
                                steady_times[par].append(timestamp[-1]+50)
                            else:
                                steady_values[par] = [p['value'], ]
                                steady_times[par] = [timestamp[-1]+50, ]
                        


    # Plot trend data
    n_tot = len(trend_data.keys()) + add_plot
    if plot_chi2:
        n_tot += 1

    if newplot:
        ysize = len(trend_data.keys()) * 2 + 6
        fig, axs = plt.subplots(n_tot,1, dpi=100, figsize=(6,ysize), sharex=True)
        plt.subplots_adjust(left=0.15, right=.95, top=0.98, bottom=0.1)

    n_current = 1
    for i, par in enumerate(trend_data.keys()):
        ax = plt.subplot(n_tot, 1, i+1)
        plt.errorbar(timestamp, trend_data[par], yerr=trend_err[par], label=par, marker='.', markersize=8, linestyle='--')
        #plt.xlabel('seconds')
        
        if par in steady_values:
            plt.plot(steady_times[par], steady_values[par], linestyle='', marker='*', markersize=10)
        
        plt.ylabel(par)
        #plt.legend(frameon=False)

    if plot_chi2:
        ax = plt.subplot(n_tot, 1, n_tot)
        plt.plot(timestamp, chi2, label='$\chi^2$')
        plt.plot(timestamp, nlprior, label='prior', linestyle='--')
        plt.ylabel('$\chi^2$')
        plt.legend(frameon=False)

    plt.xlabel("Time (seconds)")

    with open(os.path.join(dyn_fit_dir, 'trend-%s.json' % model_name), 'w') as fp:
        json.dump([timestamp, trend_data, trend_err, chi2], fp)
    return trend_data, trend_err
        

def save_parameters():
    # Write human-readable output

    _header = ['Time (sec)', 'Layer 1 rho', 'Layer 1 thickness', 'Layer 1 interface',
               'Layer 2 rho', 'Layer 2 thickness', 'Layer 2 interface', 'THF interface', 'chi2']

    with open(os.path.join(project_dir, 'results-table-193673.md'), 'w') as fd:

        header = '| ' + '|'.join(_header) + '|\n'
        header += '| ' + '|'.join(len(_header)*['---']) + '|\n'
        fd.write(header)

        for i, _time in enumerate(timestamp):
            entry = '| %g ' % (60.0*timestamp[i])
            entry += '| %4.2f ± %4.2f' % (oxide_rho[i], oxide_drho[i])
            entry += '| %4.1f ± %4.1f' % (oxide_thick[i], oxide_dthick[i])
            entry += '| %4.1f ± %4.1f' % (oxide_sigma[i], oxide_dsigma[i])
            entry += '| %4.2f ± %4.2f' % (sei_rho[i], sei_drho[i])
            entry += '| %4.1f ± %4.1f' % (sei_thick[i], sei_dthick[i])
            entry += '| %4.1f ± %4.1f' % (sei_sigma[i], sei_dsigma[i])
            entry += '| %4.1f ± %4.1f' % (solvent_sigma[i], solvent_dsigma[i])
            entry += '| %g |\n' % chi2[i]
            fd.write(entry)

    # Save trend data
    trend_data = [60.0*np.asarray(timestamp), oxide_rho, oxide_drho, oxide_thick, oxide_dthick, oxide_sigma, oxide_dsigma,
                  sei_rho, sei_drho, sei_thick, sei_dthick, sei_sigma, sei_dsigma, solvent_sigma, solvent_dsigma]
    trend_data = np.asarray(trend_data).T

    np.savetxt(os.path.join(project_dir, "results-table-193673.txt"), trend_data)

def write_md_table(trend_data_file):
    """
        The trend data file is saved as:
            data[0] is the array of times
            data[1] is a dict of parameter values
            data[2] is the corresponding dict of uncertainties
    """
    with open(trend_data_file) as fd:
        data = json.load(fd)

        output_file = trend_data_file.replace('.json', '-table.md')
        with open(output_file, 'w') as output:
            # Write header
            headers = data[1].keys()
            header = '| Time | ' + '|'.join(headers) + '| chi2 |\n'
            header += '| ' + '|'.join((len(headers)+2)*['---']) + '|\n'
            output.write(header)

            for i in range(len(data[0])):
                entry = '| %g ' % (data[0][i])
                for k in data[1].keys():
                    entry += '| %4.2f ± %4.2f ' % (data[1][k][i], data[2][k][i])
                entry += '| %g |\n' % data[3][i]
                output.write(entry)

def detect_changes(dynamic_run, dyn_data_dir, first=0, last=-1, out_array=None):

    compiled_array = []
    compiled_times = []

    _file_list = sorted(os.listdir(dyn_data_dir))

    # Get only the files for the run we're interested in
    _good_files = [_f for _f in _file_list if _f.startswith('r%d_t' % dynamic_run)]

    print(len(_good_files))
    chi2 = []
    asym = []
    t = []
    skipped = 0
    previous = None
    
    min_q = 0.0154
    for _file in _good_files[first:last]:
        if _file.startswith('r%d_t' % dynamic_run):
            _data = np.loadtxt(os.path.join(dyn_data_dir, _file)).T
            if len(_data) == 0:
                continue
            idx = _data[0] >= min_q
            _data_name, _ = os.path.splitext(_file)
            _time = int(_data_name.replace('r%d_t' % dynamic_run, ''))
            compiled_array.append([_data[0][idx], _data[1][idx], _data[2][idx]])
            compiled_times.append(_time)

            if previous is not None:
                if len(_data[1]) == len(previous):
                    delta = np.mean((_data[1]-previous)**2/(_data[2]**2+previous_err**2))
                    chi2.append(delta)
                    _asym = np.mean((_data[1]-previous)/(_data[1]+previous))
                    asym.append(_asym)
                    t.append(_time)
                    
                elif True:
                    old_r = []
                    old_err = []
                    new_r = []
                    new_err = []
                    
                    for i, q in enumerate(_data[0]):
                        idx = np.argwhere(previous_q == q)
                        #print(idx)
                        if len(idx) > 0:
                            new_r.append(_data[1][i])
                            new_err.append(_data[2][i])
                            old_r.append(previous[idx[0][0]])
                            old_err.append(previous_err[idx[0][0]])

                    old_r = np.asarray(old_r)
                    old_err = np.asarray(old_err)
                    new_r = np.asarray(new_r)
                    new_err = np.asarray(new_err)

                    delta = np.mean((new_r - old_r)**2 / (new_err**2 + old_err**2))
                    #delta = np.mean((new_r - old_r)**2 / (new_err**2))
                    chi2.append(delta)
                    _asym = np.mean((new_r-old_r)/(new_r+old_r))
                    asym.append(_asym)
                    t.append(_time)
                
                previous_q = _data[0]
                previous = _data[1]
                previous_err = _data[2]

                        
                    #print("Unequal length: %s" % _file)
            else:
                print("Ref %s" % _file)
                previous_q = _data[0]
                previous = _data[1]
                previous_err = _data[2]

    if out_array:
        #np.save(out_array, np.asarray(compiled_array))
        #np.save(out_array+'_times', np.asarray(compiled_times))
        np.savetxt(out_array+'_chi2.txt', t)
        np.savetxt(out_array+'_times.txt', t)
    print("Skipped: %s" % skipped)
    fig = plt.figure(dpi=100, figsize=[8,4])
    plt.plot(t, chi2, markersize=10, marker='.', linestyle='--', label='$\chi^2$')
    #plt.plot(t, 10*np.asarray(asym), label='Asym [x10]')
    #plt.legend(frameon=False)
    plt.ylabel('$\chi^2$')
    plt.xlabel('Time (sec)')
    return t, chi2


def package_data(dynamic_run, dyn_data_dir, first=0, last=-1, qmin=0, qmax=1, max_len=None, out_array=None):

    compiled_array = []
    compiled_times = []
    data_array = []
    
    _file_list = sorted(os.listdir(dyn_data_dir))

    # Get only the files for the run we're interested in
    _good_files = [_f for _f in _file_list if _f.startswith('r%d_t' % dynamic_run)]

    print(len(_good_files))
    asym = []
    t = []
    skipped = 0
    previous = None
    
    min_q = qmin
    max_q = qmax

    for i, _file in enumerate(_good_files[first:last]):
        if _file.startswith('r%d_t' % dynamic_run):
            print(_file)
            _data = np.loadtxt(os.path.join(dyn_data_dir, _file)).T
            if np.min(_data[0]) > min_q:
                min_q = np.min(_data[0])
            if np.max(_data[0]) < max_q:
                max_q = np.max(_data[0])

            _data_name, _ = os.path.splitext(_file)
            _time = int(_data_name.replace('r%d_t' % dynamic_run, ''))
            data_array.append([_data_name, _time, _data])

    for i, _data in enumerate(data_array):
        idx = (_data[2][0] >= min_q) & (_data[2][0] < max_q)
        if max_len is not None and len(_data[2][0][idx]) > max_len:
            data2 = _data[2][0][idx]
            print(data2[-max_len:])
            compiled_array.append([data2[-max_len:], _data[2][1][idx][-max_len:], _data[2][2][idx][-max_len:]])
            compiled_times.append(_data[1])
        else:
            compiled_array.append([_data[2][0][idx], _data[2][1][idx], _data[2][2][idx]])
            compiled_times.append(_data[1])

    compiled_array = np.asarray(compiled_array)
    compiled_times = np.asarray(compiled_times)
    print(compiled_array.shape)
    print(np.max(compiled_array[0][0]))
    if out_array:
        np.save(out_array, compiled_array)
        np.save(out_array+'_times',compiled_times )
    return compiled_times, compiled_array

def package_json_data(dynamic_run, dyn_data_dir, out_array=None):

    compiled_array = []
    compiled_times = []
    data_array = []
    
    _file_list = sorted(os.listdir(dyn_data_dir))

    # Get only the files for the run we're interested in
    _good_files = [_f for _f in _file_list if _f.startswith('r%d_t' % dynamic_run)]

    for i, _file in enumerate(_good_files):
        if _file.startswith('r%d_t' % dynamic_run):
            
            _data = np.loadtxt(os.path.join(dyn_data_dir, _file)).T
            print(i, _file, len(_data[0]))
            _data_name, _ = os.path.splitext(_file)
            _time = int(_data_name.replace('r%d_t' % dynamic_run, ''))
            compiled_array.append(_data.tolist())
            compiled_times.append(_time)

    if out_array:
        with open(out_array, 'w') as fp:
            json.dump(dict(times=compiled_times, data=compiled_array), fp)
        
    return compiled_times, compiled_array
