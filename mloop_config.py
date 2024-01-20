import os
import json
import configparser
import tomli
import logging
from collections import namedtuple


MloopParam = namedtuple("MloopParam", ["name", "min", "max", "start"])
RunmanagerGlobal = namedtuple("RunmanagerGlobal", ["name", "expr", "args"])

def is_global_active(config, group, name, category):
    """
    We check to see if the requeted global has been activated or not
    """

    if group in config["MLOOP"]["groups"]:
        if config[category][group][name].get("enable", True):
            return True
    
    return False

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
    if config_path:
        with open(config_path, "rb") as f:
            config = tomli.load(f)
    else:
        raise RuntimeError("Unknown configuration file type. Supports only .toml.")


    to_flatten = ["COMPILATION", "ANALYSIS", "MLOOP"]
    # iterate over configuration object and store pairs in parameter dictionary
    params = {}
    for sect in to_flatten:
        for (key, val) in config[sect].items():
            params[key] = val

    # Convert cost_key to tuple
    params["cost_key"] = tuple(params["cost_key"])

    param_dict = {}
    global_list = []

    for group in config.get("MLOOP_PARAMS", {}):
        for name, param in config["MLOOP_PARAMS"][group].items():
            if is_global_active(config, group, name, "MLOOP_PARAMS"):
                param_dict[name] = MloopParam(
                    name=name,
                    min=param["min"],
                    max=param["max"],
                    start=param["start"]
                )

                if "global_name" in param:
                    global_list.append(
                        RunmanagerGlobal(
                            name=param["global_name"],
                            expr=None,
                            args=[name]
                        )
                    )

    for group in config.get("RUNMANAGER_GLOBALS", {}):
        for name, param in config["RUNMANAGER_GLOBALS"][group].items():
            if is_global_active(config, group, name, "RUNMANAGER_GLOBALS"):

                global_list.append(
                    RunmanagerGlobal(
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
