from mloop.interfaces import Interface
from mloop.controllers import create_controller

import lyse
import time
import threading
import Queue

class LoopInterface(Interface):
    # global lyse; import lyse
    global config_get; import config_get

    # Initialization of the interface, including this method is optional
    def __init__(self):

        # inherit parent class methods
        super().__init__()

        # Retrieve config file parameters from local file or generates and save defaults
        self.cfg_dict = config_get.cfgget()

        # initialise iteration counter
        self.cfg_dict['iter_count'] = 0

    # this is the method called by MLOOP upon each new iteration when it wants to know the cost
    # associated with a given point in the search space
    def get_next_cost_dict(self, params_dict):

        # iterate counter and retrieve new experiment parameters
        self.cfg_dict['iter_count'] += 1
        self.cfg_dict['mloop_params'] = params_dict['params']

        # Only proceed once per execution of the lyse routine
        print('Getting current cost from lyse queue...')
        cost = lyse.routine_storage.my_queue.get()

        # Return cost dictionary to M-LOOP
        print('M-LOOP iteration  {:3d}'.format(self.cfg_dict['iter_count']))
        cost_dict = {
            'cost': float(cost),
            'uncer': float(cost * 0.05),
            'bad': self.cfg_dict["bad"],
        }

        return cost_dict


def optmimus():
    # create M-LOOP optmiser interface with desired parameters
    opt_interface = LoopInterface()

    # retrieve a snapshot of the configuration dictionary
    opt_dict = opt_interface.cfg_dict

    # instantiate experiment controller
    controller = create_controller(opt_interface, **opt_dict)

    # run the optimiser using the constructed interface
    controller.optimize()

    # The results of the optimization will be saved to files and can also be
    # accessed as attributes of the controller.
    print('Optimisation ended.')

    # Format the results
    opt_results = {}
    opt_results['best_params'] = controller.best_params
    opt_results['best_cost'] = controller.best_cost
    opt_results['best_uncer'] = controller.best_uncer
    opt_results['best_index'] = controller.best_index
    return opt_results


# Runs each time analysis routine does
if (
    hasattr(lyse.routine_storage, "counter")
    and lyse.routine_storage.optimisation_thread.is_alive()
):
    lyse.routine_storage.counter += 1
    print("Routine iteration {:3d}".format(lyse.routine_storage.counter))
    lyse.routine_storage.my_queue.put(1.2)
else:
    if not hasattr(lyse.routine_storage, "counter"):
        print("First execution of lyse routine...")
        lyse.routine_storage.my_queue = Queue.Queue()
    else:
        print("Restarting optimisation thread...")
    lyse.routine_storage.counter = 0
    lyse.routine_storage.optimisation_thread = threading.Thread(target=optmimus)
    lyse.routine_storage.optimisation_thread.daemon = True
    lyse.routine_storage.optimisation_thread.start()
    print('Started optimisation thread...')
