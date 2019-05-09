import lyse
from runmanager.remote import set_globals, engage
import mloop_config
from mloop.interfaces import Interface
from mloop.controllers import create_controller
import time


def set_globals_mloop(mloop_session=None, mloop_iteration=None):
    """Set globals named 'mloop_session' and 'mloop_iteration'
    based on the current . Defaults are None, which will ideally
    remain that way unless there is an active optimisation underway.
    """
    if mloop_iteration and mloop_session is None:
        globals = {'mloop_iteration': mloop_iteration}
    else:
        globals = {'mloop_session': mloop_session, 'mloop_iteration': mloop_iteration}
    try:
        set_globals(globals)
    except ValueError:
        pass


class LoopInterface(Interface):
    def __init__(self):
        super(LoopInterface, self).__init__()

        # Retrieve configuration from file or generate from defaults
        self.config = mloop_config.get()
        self.num_in_costs = 0

    # Method called by M-LOOP upon each new iteration to determine the cost
    # associated with a given point in the search space
    def get_next_cost_dict(self, params_dict):
        self.num_in_costs += 1
        if not self.config['mock']:
            print('Requesting next shot from experiment interface...')
            globals_dict = dict(zip(self.config['mloop_params'], params_dict['params']))
            set_globals(globals_dict)
            print('Run: {:d}'.format(self.num_in_costs))
            set_globals_mloop(mloop_iteration=self.num_in_costs)
            time.sleep(0.05)
            engage()
        else:
            # Store a current parameter so that mloop_multishot.py can fake a cost
            lyse.routine_storage.x = params_dict['params'][0]

        # Only proceed once per execution of the mloop_multishot.py routine
        print('Getting current cost from lyse queue...')
        return lyse.routine_storage.queue.get()


def main():
    # Create M-LOOP optmiser interface with desired parameters
    interface = LoopInterface()
    # interface.daemon = True

    # Instantiate experiment controller
    controller = create_controller(interface, **interface.config)

    # Define the M-LOOP session ID and initialise the mloop_iteration
    set_globals_mloop(controller.start_datetime.strftime('%Y%m%dT%H%M%S'), 0)

    # Run the optimiser using the constructed interface
    controller.optimize()

    # Reset the M-LOOP session and index to None
    print('Optimisation ended.')
    set_globals_mloop()

    # Set the optimisation globals to their best results
    print('Setting best parameters in runmanager.')
    globals_dict = dict(zip(interface.config['mloop_params'], controller.best_params))
    set_globals(globals_dict)

    # Return the results in a dictionary
    opt_results = {}
    opt_results['best_params'] = controller.best_params
    opt_results['best_cost'] = controller.best_cost
    opt_results['best_uncer'] = controller.best_uncer
    opt_results['best_index'] = controller.best_index
    return opt_results
