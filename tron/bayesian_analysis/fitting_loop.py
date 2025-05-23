"""
Fitting loop for time-resolved data sets.
"""

import os
import time
import json
import subprocess
import shutil

from . import model_utils


class FittingLoop:
    """
    Class representing a fitting loop for time-resolved data sets.
    """

    def __init__(
        self,
        dyn_data_dir,
        results_dir,
        model_dir=None,
        model_name="__model",
        initial_err_file=None,
        initial_expt_file=None,
        final_err_file=None,
        final_expt_file=None,
    ):
        """
        Initialize the FittingLoop object.

        Parameters
        ----------
        dyn_data_dir : str
            Directory where the dynamic data is stored.
        results_dir : str
            Directory where the results will be stored.
        model_dir : str, optional
            Directory where the model is stored.
        model_name : str, optional
            Name of the model file.
        initial_err_file : str, optional
            File path of the initial error file.
        initial_expt_file : str, optional
            File path of the initial experiment file.
        final_err_file : str, optional
            File path of the final error file.
        final_expt_file : str, optional
            File path of the final experiment file.

        """
        self.fit_forward = True
        self.dyn_file_list = []
        self.model_dir = model_dir
        self.model_name = model_name
        self.dyn_data_dir = dyn_data_dir
        self.results_dir = results_dir
        self.initial_err_file = initial_err_file
        self.initial_expt_file = initial_expt_file
        self.final_err_file = final_err_file
        self.final_expt_file = final_expt_file
        self.last_output = ""

    def save(self, file_path):
        """
        Save all the settings to a file.

        Parameters
        ----------
        file_path : str
            File path to save the settings.

        """
        meta_data = dict(
            model_dir=self.model_dir,
            model_name=self.model_name,
            dyn_data_dir=self.dyn_data_dir,
            results_dir=self.results_dir,
            initial_err_file=self.initial_err_file,
            initial_expt_file=self.initial_expt_file,
            final_err_file=self.final_err_file,
            final_expt_file=self.final_expt_file,
            dyn_file_list=self.dyn_file_list,
            fit_forward=self.fit_forward,
        )
        with open(file_path, "w") as fd:
            json.dump(meta_data, fd)

    def load(self, file_path):
        """
        Load settings from a file.

        Parameters
        ----------
        file_path : str
            File path to load the settings from.

        """
        with open(file_path, "r") as fd:
            meta_data = json.load(fd)
        self.model_dir = meta_data["model_dir"]
        self.model_name = meta_data["model_name"]
        self.dyn_data_dir = meta_data["dyn_data_dir"]
        self.results_dir = meta_data["results_dir"]
        self.initial_err_file = meta_data["initial_err_file"]
        self.initial_expt_file = meta_data["initial_expt_file"]
        self.final_err_file = meta_data["final_err_file"]
        self.final_expt_file = meta_data["final_expt_file"]
        self.fit_forward = meta_data["fit_forward"]
        self.dyn_file_list = meta_data["dyn_file_list"]

    def __str__(self):
        """
        Return a string representation of the FittingLoop object.

        Returns
        -------
        str
            String representation of the FittingLoop object.

        """
        return (
            f"Model: {os.path.join(self.model_dir, self.model_name)}\n"
            f"Data: {self.dyn_data_dir}\n"
            f"Results: {self.results_dir}\n"
            f"Initial state: {self.initial_expt_file}\n"
            f"Final state: {self.final_expt_file}"
        )

    def print_initial_final(self):
        """
        Print the initial and final models.
        """
        print(self)
        with open(self.initial_err_file, "r") as fd:
            initial_model = json.load(fd)
        with open(self.final_err_file, "r") as fd:
            final_model = json.load(fd)
        model_utils.print_model(initial_model, final_model)

    def fit(self, dyn_file_list, fit_forward=True):
        """
        Execute the fitting loop.

        Parameters
        ----------
        dyn_file_list : list
            List of time-resolved data sets, ordered in increasing times.
        fit_forward : bool, optional
            Flag indicating whether to fit forward in time (default: True).

        """
        self.fit_forward = fit_forward
        self.dyn_file_list = dyn_file_list

        # Clean results directory so we don't mix up results
        if os.path.isdir(self.results_dir):
            shutil.rmtree(self.results_dir)
        os.mkdir(self.results_dir)

        # Save parameters so we know what we did
        self.save(os.path.join(self.results_dir, "fit_parameters.json"))

        # If we are fitting starting from the final state, get an iterator reversing the file order
        _ordered_files = dyn_file_list if self.fit_forward else reversed(dyn_file_list)

        if self.fit_forward:
            starting_expt = self.initial_expt_file
            starting_err = self.initial_err_file
        else:
            starting_expt = self.final_expt_file
            starting_err = self.final_err_file

        # Initialize our time series of models
        with open(starting_err, "r") as fd:
            initial_model = json.load(fd)
        time_series = [initial_model]

        t0 = time.time()
        t1 = time.time()
        for _file in _ordered_files:
            print(f"Fitting {_file}")
            _base_name, _ = os.path.splitext(_file)
            data_to_fit = os.path.join(self.dyn_data_dir, _file)
            command = [
                "python",
                "-m",
                "refl1d.main",
                "--fit=dream",
                "--steps=1000",
                "--burn=1000",
                "--batch",
                "--overwrite",
                f"--store={os.path.join(self.results_dir, _base_name)}",
                os.path.join(self.model_dir, f"{self.model_name}.py"),
                data_to_fit,
                starting_expt,
                starting_err,
            ]

            self.last_output = subprocess.run(command, capture_output=True, text=True)

            # Update the starting model with the fit we just did
            _model = os.path.join(
                self.results_dir, _base_name, f"{self.model_name}-expt.json"
            )
            _err = os.path.join(
                self.results_dir, _base_name, f"{self.model_name}-err.json"
            )
            starting_model = _model
            starting_err = _err

            print(starting_model)

            with open(os.path.join(_err), "r") as fd:
                updated_model = json.load(fd)
                time_series.append(updated_model)

            model_utils.print_model(time_series[-2], time_series[-1])

            total_time = (time.time() - t0) / 60
            item_time = time.time() - t1
            t1 = time.time()
            print("    Completed: %g s [total=%g m]" % (item_time, total_time))


def execute_fit(
    dynamic_run,
    data_dir,
    model_file,
    initial_expt_file,
    final_expt_file,
    results_dir,
    first_item=0,
    last_item=-1,
    fit_forward=True,
):
    """
    Execute the fitting loop.

    Parameters
    ----------
    dynamic_run : int
        Run number of the dynamic data.
    data_dir : str
        Directory where the dynamic data is stored.
    model_file : str
        File path of the model.
    initial_expt_file : str
        File path of the initial refl1d json experiment file.
    final_expt_file : str
        File path of the final refl1d json experiment file.
    results_dir : str
        Directory where the results will be stored.
    first_item : int, optional
        Index of the first data file to use (default: 0).
    last_item : int, optional
        Index of the last data file to use (default: -1, which means all files until the end).
    fit_forward : bool, optional
        Flag indicating whether to fit forward in time (default: True).

    """
    model_dir, model_name = os.path.split(model_file)

    # Initial data set and model (starting point)
    if initial_expt_file is not None:
        if "expt" not in initial_expt_file:
            raise ValueError(
                "The initial experiment file must be a refl1d json experiment file."
            )
        else:
            initial_err_file = initial_expt_file.replace("1-expt", "err")
            if not os.path.exists(initial_err_file):
                raise ValueError(f"Error file {initial_err_file} does not exist.")

    if final_expt_file is not None:
        if "expt" not in final_expt_file:
            raise ValueError(
                "The final experiment file must be a refl1d json experiment file."
            )
        else:
            final_err_file = final_expt_file.replace("1-expt", "err")
            if not os.path.exists(final_err_file):
                raise ValueError(f"Error file {final_err_file} does not exist.")

    # Create top-level directory for the dynamic fits
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    model_name = model_name.replace(".py", "")
    loop = FittingLoop(
        data_dir,
        results_dir=results_dir,
        model_dir=model_dir,
        model_name=model_name,
        initial_err_file=initial_err_file,
        initial_expt_file=initial_expt_file,
        final_err_file=final_err_file,
        final_expt_file=final_expt_file,
    )

    loop.print_initial_final()

    _good_files = [
        _f
        for _f in sorted(os.listdir(data_dir))
        if _f.startswith("r%d_t" % dynamic_run)
    ]

    try:
        loop.fit(_good_files[first_item:last_item], fit_forward=fit_forward)
    except Exception as e:
        print(f"Error: {e}")
        print(loop.last_output)


if __name__ == "__main__":
    # Main execution block for running the fitting loop from the command line.
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Fitting loop for time-resolved data sets."
    )
    parser.add_argument("dynamic_run", type=int, help="Run number of the dynamic data.")
    parser.add_argument(
        "data_dir", type=str, help="Directory where the dynamic data is stored."
    )
    parser.add_argument("model_file", type=str, help="File path of the model.")
    parser.add_argument(
        "initial_expt_file",
        type=str,
        help="File path of the initial refl1d json experiment file.",
    )
    parser.add_argument(
        "final_expt_file",
        type=str,
        help="File path of the final refl1d json experiment file.",
    )
    parser.add_argument(
        "results_dir", type=str, help="Directory where the results will be stored."
    )

    args = parser.parse_args()

    execute_fit(
        args.dynamic_run,
        args.data_dir,
        args.model_file,
        args.initial_expt_file,
        args.final_expt_file,
        args.results_dir,
    )
