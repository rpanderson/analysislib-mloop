import os
import json
import configparser
import tomli
import logging
from collections import namedtuple


MloopParam = namedtuple("MloopParam", ["name", "min", "max", "start"])
RunmanagerGlobal = namedtuple("RunmanagerGlobal", ["name", "expr", "args"])


def prepare_globals(global_list, params_val_dict):
    globals_to_set = {}
    for g in global_list:
        target = g.name
        args = [ params_val_dict[arg] for arg in g.args ]

        assert args

        if g.expr:
            val = eval(g.expr)(*args)
        else:
            val = args[0]

        globals_to_set[target] = val

    return globals_to_set


def get(config_paths=None):
    """Creates config file from specified file, or
    creates one locally with default values.
    """

    # Default to local directory and default name
    if not config_paths:
        config_paths = []
        folder = os.path.dirname(__file__)
        config_paths.append(os.path.join(folder, "mloop_config.toml"))
        config_paths.append(os.path.join(folder, "mloop_config.ini"))

    config_path = ""
    for path in config_paths:
        if os.path.isfile(path):
            print(path)
            config_path = path
            break

    config = None
    config_type = None
    if config_path:
        if config_path.lower().endswith(".ini"):
            config_type = "ini"
            config.read(config_path)

            # Instantiate RawConfigParser with case sensitive option names
            config = configparser.RawConfigParser()
            config.optionxform = str

            # Retrieve configuration parameters
            config.read(config_path)
        elif config_path.lower().endswith(".toml"):
            config_type = "toml"
            with open(config_path, "rb") as f:
                config = tomli.load(f)
        else:
            raise TypeError("Unknown configuration file type. Supports only .ini or .toml.")

    else:
        print("--- Configuration file not found: generating with default values ---")
        config_type = "ini"

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

    to_flatten = ["COMPILATION", "ANALYSIS", "MLOOP"]
    # iterate over configuration object and store pairs in parameter dictionary
    params = {}
    for sect in to_flatten:
        for (key, val) in config[sect].items():
            # only parse json in ini file, not in toml file
            if config_type == "ini":
                try:
                    params[key] = json.loads(val)
                except json.JSONDecodeError:
                    params[key] = val
            else:
                params[key] = val

    # Convert cost_key to tuple
    params["cost_key"] = tuple(params["cost_key"])

    param_dict = {}
    global_list = []

    if config_type == "ini":
        for name, param in config["MLOOP"]["mloop_params"].items():
            param_dict[name] = \
                    MloopParam(
                            name=name,
                            min=param["min"],
                            max=param["max"],
                            start=param["start"]
                            )
            global_list.append(RunmanagerGlobal(
                            name=param["global_name"],
                            expr=None,
                            args=[name]
                            )
                )

    elif config_type == "toml":
        for name, param in config["MLOOP_PARAMS"].items():
            if ("enable" in param) and param["enable"]: 
                param_dict[name] = \
                        MloopParam(
                                name=name,
                                min=param["min"],
                                max=param["max"],
                                start=param["start"]
                                )

                if "global_name" in param:
                    global_list.append(RunmanagerGlobal(
                                    name=param["global_name"],
                                    expr=None,
                                    args=[name]
                                    )
                    )

        if "RUNMANAGER_GLOBALS" in config:
            if ("enable" in param) and param["enable"]:
                for name, param in config["RUNMANAGER_GLOBALS"].items():
                    global_list.append(RunmanagerGlobal(
                                    name=name,
                                    expr=param.get('expr', None),
                                    args=param['args']
                                    )
                    )

        # check if all mloop params can be mapped to at least one global
        for ml_name in param_dict.keys():
            if not any([ (ml_name in g.args) for g in global_list ]):
                raise KeyError(f"Parameter {ml_name} in MLOOP_PARAMS doesn't have a Runmanager global mapped to it.")

        # check if all args of any global has been defined in mloop params
        for g in global_list:
            for a in g.args:
                if a not in param_dict:
                    raise KeyError(f"Argument {a} of global {g.name} doesn't exist.")

        params['mloop_params'] = param_dict
        params['runmanager_globals'] = global_list

        params['num_params'] = len(params['mloop_params'].values())
        params['min_boundary'] = [p.min for p in params['mloop_params'].values()]
        params['max_boundary'] = [p.max for p in params['mloop_params'].values()]
        params['first_params'] = [p.start for p in params['mloop_params'].values()]
        

        
    return params


if __name__ == "__main__":
    print(get())
