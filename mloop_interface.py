import lyse
import config_get
from mloop.interfaces import Interface
from mloop.controllers import create_controller
import zprocess


class LoopInterface(Interface):
    # Initialization of the interface, including this method is optional
    def __init__(self):

        # inherit parent class methods
        super(LoopInterface, self).__init__()

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

        if not self.cfg_dict['mock']:
            # Request next experiment from experiment interface
            from mloop_experiment_interface import compile_and_run_shot
            print('Requesting next shot from experiment interface...')
            compile_and_run_shot(self.cfg_dict)
        else:
            # Store current optimisation parameter so that __main__ can simulate a result
            lyse.routine_storage.x = self.cfg_dict['mloop_params'][0]

        # Only proceed once per execution of the lyse routine
        print('Getting current cost from lyse queue...')
        cost = lyse.routine_storage.queue.get()

        # Return cost dictionary to M-LOOP
        cost_dict = {
            'cost': float(cost),
            # 'uncer': float(0.05),
            'bad': self.cfg_dict['bad'],
        }

        return cost_dict


def optimus():
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
