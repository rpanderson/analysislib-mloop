import lyse
import config_get
from mloop.interfaces import Interface
from mloop.controllers import create_controller
import zprocess
from runmanager.remote import set_globals, engage


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
            print('Requesting next shot from experiment interface...')
            globals_dict = dict(
                zip(self.cfg_dict['params_to_change'], self.cfg_dict['mloop_params'])
            )
            set_globals(globals_dict)
            set_globals_mloop(mloop_iteration=self.cfg_dict['iter_count'])
            engage()
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
    opt_interface.daemon = True

    # retrieve a snapshot of the configuration dictionary
    opt_dict = opt_interface.cfg_dict

    # instantiate experiment controller
    controller = create_controller(opt_interface, **opt_dict)

    # Define the M-LOOP session ID and initialise the mloop_iteration
    set_globals_mloop(controller.start_datetime.strftime('%Y%m%dT%H%M%S'), 0)

    # run the optimiser using the constructed interface
    controller.optimize()

    # The results of the optimization will be saved to files and can also be
    # accessed as attributes of the controller.
    print('Optimisation ended.')

    # Set the M-LOOP session and index to None if they exist
    set_globals_mloop()

    # Set the optimisation parameters to their best results
    print('Setting best params in runmanager.')
    globals_dict = dict(
        zip(opt_dict['params_to_change'], controller.best_params)
    )
    set_globals(globals_dict)

    # Format the results
    opt_results = {}
    opt_results['best_params'] = controller.best_params
    opt_results['best_cost'] = controller.best_cost
    opt_results['best_uncer'] = controller.best_uncer
    opt_results['best_index'] = controller.best_index
    return opt_results
