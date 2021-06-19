import os
import json
import configparser
import logging


def get(config_path=None):
    """Creates config file from specified file, or
    creates one locally with default values.
    """

    # Default to local directory and default name
    if not config_path:
        folder = os.path.dirname(__file__)
        config_path = os.path.join(folder, "mloop_config.ini")

    # Instantiate RawConfigParser with case sensitive option names
    config = configparser.RawConfigParser()
    config.optionxform = str

    # Check if file exists and initialise with defaults if it does not
    if os.path.isfile(config_path):
        # Retrieve configuration parameters
        config.read(config_path)
    else:
        print("--- Configuration file not found: generating with default values ---")

        # Shot compilation parameters
        config["COMPILATION"] = {}
        config["COMPILATION"]["mock"] = 'false'

        # Analayis parameters
        config["ANALYSIS"] = {}
        # lyse DataFrame key to optimise
        config["ANALYSIS"]["cost_key"] = '["fake_result", "y"]'
        # Maximize cost_key (negate when reporting cost)
        config["ANALYSIS"]["maximize"] = 'true'
        # Don't report to M-LOOP if a shot is deemed bad
        config["ANALYSIS"]["ignore_bad"] = 'true'
        # Control log level for logging to console from analysislib-mloop. Not to be
        # confused with MLOOP's console_log_level option for its logger.
        config["ANALYSIS"]["analysislib_console_log_level"] = '"INFO"'
        # Control log level for logging to file from analysislib-mloop. Not to be
        # confused with MLOOP's file_log_level option for its logger.
        config["ANALYSIS"]["analysislib_file_log_level"] = '"DEBUG"'

        # M-LOOP parameters
        config["MLOOP"] = {}
        # Parameters mloop varies during optimisation
        config["MLOOP"][
            "mloop_params"
        ] = '{"x": {"min": -5.0, "max": 5.0, "start": -2.0} }'
        # Number of training runs
        config["MLOOP"]["num_training_runs"] = '5'
        # Maximum number of iterations
        config["MLOOP"]["max_num_runs_without_better_params"] = '10'
        # Maximum number of iterations
        config["MLOOP"]["max_num_runs"] = '20'
        # Maximum % move distance from best params
        config["MLOOP"]["trust_region"] = '0.5'
        # Maximum number of iterations
        config["MLOOP"]["cost_has_noise"] = 'true'
        # Force mloop to return a parameter prediction before it is ready
        config["MLOOP"]["no_delay"] = 'false'
        # Display visualisations
        config["MLOOP"]["visualisations"] = 'false'
        # Type of learner to use in optimisation:
        #   [gaussian_process, random, nelder_mead]
        config["MLOOP"]["controller_type"] = '"gaussian_process"'
        # Mute output from MLOOP optimiser
        config["MLOOP"]["console_log_level"] = '"NOTSET"'

        # Write to file
        folder = os.path.dirname(__file__)
        with open(os.path.join(folder, "mloop_config.ini"), "w+") as f:
            config.write(f)

    # iterate over configuration object and store pairs in parameter dictionary
    params = {}
    for sect in config.sections():
        for (key, val) in config.items(sect):
            try:
                params[key] = json.loads(val)
            except json.JSONDecodeError:
                params[key] = val

    # Convert cost_key to tuple
    params["cost_key"] = tuple(params["cost_key"])

    # store number of parameters for passing to controller interface
    params["num_params"] = len(params["mloop_params"])

    # get the names of the parameters, if not explicitly specified by user
    if "param_names" not in params:
        params["param_names"] = list(params["mloop_params"].keys())

    # get min boundaries for specified variables
    params["min_boundary"] = [param["min"] for param in params["mloop_params"].values()]

    # get max boundaries for specified variables
    params["max_boundary"] = [param["max"] for param in params["mloop_params"].values()]

    # starting point for search space, default to half point if not defined
    params["first_params"] = [
        param["start"] for param in params["mloop_params"].values()
    ]

    return params


if __name__ == "__main__":
    print(get())
