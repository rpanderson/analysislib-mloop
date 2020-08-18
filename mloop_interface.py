import lyse
from runmanager.remote import set_globals, engage
import mloop_config
from mloop.interfaces import Interface
from mloop.controllers import create_controller
import logging


logger = logging.getLogger('analysislib_mloop')


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
        logger.debug('mloop_iteration and/or mloop_session set.')
    except ValueError:
        logger.debug('Failed to set mloop_iteration and/or mloop_session.')


class LoopInterface(Interface):
    def __init__(self):
        # Retrieve configuration from file or generate from defaults
        self.config = mloop_config.get()

        # Pass config arguments to parent class's __init__() so that any
        # relevant specified options are applied appropriately.
        super(LoopInterface, self).__init__(**self.config)

        self.num_in_costs = 0

    # Method called by M-LOOP upon each new iteration to determine the cost
    # associated with a given point in the search space
    def get_next_cost_dict(self, params_dict):
        self.num_in_costs += 1
        # Store current parameters to later verify reported cost corresponds to these
        # or so mloop_multishot.py can fake a cost if mock = True
        logger.debug('Storing requested parameters in lyse.routine_storage.')
        lyse.routine_storage.params = params_dict['params']

        if not self.config['mock']:
            logger.info('Requesting next shot from experiment interface...')
            globals_dict = dict(zip(self.config['mloop_params'], params_dict['params']))
            logger.debug('Setting optimization parameter values.')
            set_globals(globals_dict)
            logger.debug('Setting mloop_iteration...')
            set_globals_mloop(mloop_iteration=self.num_in_costs)
            logger.debug('Calling engage().')
            engage()

        # Only proceed once per execution of the mloop_multishot.py routine
        logger.info('Waiting for next cost from lyse queue...')
        cost_dict = lyse.routine_storage.queue.get()
        logger.debug('Got cost_dict from lyse queue: {cost}'.format(cost=cost_dict))
        return cost_dict


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
    logger.info('Optimisation ended.')
    set_globals_mloop()

    # Set the optimisation globals to their best results
    logger.info('Setting best parameters in runmanager.')
    globals_dict = dict(zip(interface.config['mloop_params'], controller.best_params))
    set_globals(globals_dict)

    # Return the results in a dictionary
    opt_results = {}
    opt_results['best_params'] = controller.best_params
    opt_results['best_cost'] = controller.best_cost
    opt_results['best_uncer'] = controller.best_uncer
    opt_results['best_index'] = controller.best_index
    return opt_results
