import os
import sys
import json
import configparser as cfg

# creates config file from specified file or creates one locally with
# default values
def cfgget(cfgfile=None):

    # default to local directory and default name
    if cfgfile == None:
        folder = os.path.dirname(__file__)
        cfgfile = os.path.join(folder, "mloop_config.ini")

    # instantiate parser object and don't be case insensitive
    config = cfg.RawConfigParser()
    config.optionxform = str

    # check if file exists and initialise with defaults if it does not
    if os.path.isfile(cfgfile):
        # retrieve configuration parameters
        config.read(cfgfile)
    else:
        print("--- Configuration file not found: generating with default values ---")

        # Shot compilation parameters
        config["COMPILATION"] = {}
        config["COMPILATION"]["mock"] = 'false'
        config["COMPILATION"]["labscript_file"] = '"mloop_test.py"'
        config["COMPILATION"]["template_folder"] = '"C:\\\\Experiments\\\\example_experiment\\\\mloop_test"'
        config["COMPILATION"]["template_file"] = '"template.h5"'

        # Analayis parameters
        config["ANALYSIS"] = {}
        # lyse DataFrame key to optimise
        config["ANALYSIS"]["opt_param"] = '["fake_result", "y"]'
        # ignore nans in cost_analysis function
        config["ANALYSIS"]["ignore_nans"] = 'false'

        # M-LOOP parameters
        config["MLOOP"] = {}
        # parameters mloop varies during optimisation
        config["MLOOP"]["mloop_params"] = '{"x": {"min": -5.0, "max": 5.0, "start": -2.0, "group": "some_group"} }'
        # number of training runs
        config["MLOOP"]["num_training_runs"] = '5'
        # maximum number of iterations
        config["MLOOP"]["max_num_runs_without_better_params"] = '10'
        # maximum number of iterations
        config["MLOOP"]["max_num_runs"] = '20'
        # maximum number of iterations
        config["MLOOP"]["uncer"] = '0.0'
        # maximum % move distance from best params
        config["MLOOP"]["trust_region"] = '0.5'
        # trust data or not flag
        config["MLOOP"]["bad"] = 'false'
        # maximum number of iterations
        config["MLOOP"]["cost_has_noise"] = 'true'
        # force mloop to return a parameter prediction before it is ready
        config["MLOOP"]["no_delay"] = 'false'
        # display visualisations (may not work without tweaking in our
        # environment)
        config["MLOOP"]["visualisations"] = 'false'
        # type of learner to use in optimisation: [gaussian_process, random, nelder_mead]
        config["MLOOP"]["controller_type"] = '"gaussian_process"'
        # mute output from MLOOP optimiser
        config["MLOOP"]["console_log_level"] = '"NOTSET"'

        # write to file
        folder = os.path.dirname(__file__)
        with open(os.path.join(folder, "mloop_config.ini"), "w+") as cfile:
            config.write(cfile)

    # iterate over configuration object and store pairs in parameter dictionary
    params = dict((key, json.loads(val))
                  for sect in config.sections() for (key, val) in config.items(sect))

    # modify params to match mloop expectations - not crazy about this but it has to happen somewhere
    params["params_to_change"] = list(params["mloop_params"].keys())

    # store number of parameters for passing to controller interface
    params["num_params"] = len(params["params_to_change"])

    # get min boundaries for specified variables
    params["min_boundary"] = [params["mloop_params"][key]["min"] for key in params["params_to_change"]]

    # get max boundaries for specified variables
    params["max_boundary"] = [params["mloop_params"][key]["max"] for key in params["params_to_change"]]

    # starting point for search space, default to half point if not defined
    params["first_params"] = [params["mloop_params"][key]["start"] for key in params["params_to_change"]]

    # get group name of each global
    params["globals_groups"] = [params["mloop_params"][key]["group"] for key in params["params_to_change"]]

    return params

if __name__ == "__main__":
    print(cfgget())
