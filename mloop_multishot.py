import lyse
import runmanager.remote as rm
import numpy as np
import mloop_config
import sys
import logging
import os
from labscript_utils.setup_logging import LOG_PATH

try:
    from labscript_utils import check_version
except ImportError:
    raise ImportError('Require labscript_utils > 2.1.0')

check_version('lyse', '2.5.0', '4.0')
check_version('zprocess', '2.13.1', '4.0')
check_version('labscript_utils', '2.12.5', '4.0')


def configure_logging(config):
    console_log_level = config['analysislib_console_log_level']
    file_log_level = config['analysislib_file_log_level']
    LOG_FILENAME = 'analysislib_mloop.log'

    global logger
    logger = logging.getLogger('analysislib_mloop')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(filename)s:%(funcName)s:%(lineno)d:%(levelname)s: %(message)s'
    )

    # Set up handlers if not already present from previous runs.
    if not logger.handlers:
        # Set up console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Set up file handler
        full_filename = os.path.join(LOG_PATH, LOG_FILENAME)
        file_handler = logging.FileHandler(full_filename, mode='w')
        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.debug('Logger configured.')


def check_runmanager(config):
    logger.debug('Checking runmanager...')
    msgs = []

    logger.debug('Getting globals.')
    rm_globals = rm.get_globals()
    if not all([x in rm_globals for x in config['mloop_params']]):
        msgs.append('Not all optimisation parameters present in runmanager.')

    logger.debug('Getting run shots state.')
    if not rm.get_run_shots():
        msgs.append('Run shot(s) not selected in runmanager.')

    logger.debug('Checking for errors in globals.')
    if rm.error_in_globals():
        msgs.append('Error in runmanager globals.')

    logger.debug('Checking number of shots.')
    n_shots = rm.n_shots()
    if n_shots > 1 and not config['ignore_bad']:
        msgs.append(
            f'runmanager is set to compile {n_shots:d} shots per request, but your '
            + 'mloop_config has ignore_bad = False. You are advised to (i) remove '
            + 'iterable globals so as to compile one shot per cost or (ii) set '
            + 'ignore_bad = True in your mloop_config and only return one cost with '
            + 'bad = False per sequence.'
        )

    if msgs:
        logger.warning('\n'.join(msgs))
        return False
    else:
        logger.debug('Runmanager ok.')
        return True


def verify_globals(config):
    logger.debug('Verifying globals...')

    # Get the current runmanager globals
    logger.debug('Getting values of globals from runmanager.')
    rm_globals = rm.get_globals()
    current_values = [rm_globals[name] for name in config['mloop_params']]

    # Retrieve the parameter values requested by M-LOOP on this iteration
    logger.debug('Getting requested globals values from lyse.routine_storage.')
    requested_values = lyse.routine_storage.params
    requested_dict = dict(zip(config['mloop_params'], requested_values))

    # Get the parameter values for the shot we just computed the cost for
    logger.debug('Getting lyse dataframe.')
    df = lyse.data()
    shot_values = [df[name].iloc[-1] for name in config['mloop_params']]

    # Verify integrity by cross-checking against what was requested
    if not np.array_equal(current_values, requested_values):
        message = (
            'Cost requested for values different to those in runmanager.\n'
            'Please add an executed shot to lyse with: {requested_dict}'
        ).format(requested_dict=requested_dict)
        logger.error(message)
        return False
    if not np.array_equal(shot_values, requested_values):
        message = (
            'Cost requested for different values to those used to compute cost.\n'
            'Please add an executed shot to lyse with: {requested_dict}'
        ).format(requested_dict=requested_dict)
        logger.error(message)
        return False
    logger.debug('Globals verified.')
    return True


def cost_analysis(cost_key=(None,), maximize=True, x=None):
    """Return a cost dictionary to M-LOOP with at least:
      {'bad': True} or {'cost': float}.
    - Look for the latest cost in the cost_key column of the lyse
    - DataFrame and an uncertainty ('u_' prefix at the lowest level).
    - Report bad shot to M-LOOP if cost is nan or inf.
    - Negate value in DataFrame if maximize = True.
    - Fallback to reporting a constant or fake cost (from x).
    """
    logger.debug('Getting cost...')
    cost_dict = {'bad': False}

    # Retrieve current lyse DataFrame
    logger.debug('Getting lyse dataframe.')
    df = lyse.data()

    # Use the most recent shot
    ix = -1

    # Retrieve cost from specified column
    if len(df) and cost_key in df:
        cost = (df[cost_key].astype(float).values)[ix]
        if np.isnan(cost) or np.isinf(cost):
            cost_dict['bad'] = True
            logger.info('Got bad cost: {cost}'.format(cost=cost))
        else:
            cost_dict['cost'] = (1 - 2 * maximize) * cost
            logger.info('Got cost: {cost}'.format(cost=cost_dict['cost']))
        u_cost_key = cost_key[:-1] + ('u_' + cost_key[-1],)
        if u_cost_key in df:
            cost_dict['uncer'] = df[u_cost_key].iloc[ix]
            logger.info('Got uncertainty: {uncer}'.format(uncer=cost_dict['uncer']))

    # If it doesn't exist, generate a fake cost
    elif x is not None:
        from fake_result import fake_result

        cost_dict['cost'] = (1 - 2 * maximize) * fake_result(x)
        logger.info('Faked cost: {cost}'.format(cost=cost_dict['cost']))

    # Or just use a constant cost (for debugging)
    else:
        cost_dict['cost'] = 1.2
        logger.info('Faked constant cost: {cost}'.format(cost=cost_dict['cost']))

    return cost_dict


if __name__ == '__main__':
    config = mloop_config.get()
    configure_logging(config)

    if not hasattr(lyse.routine_storage, 'queue'):
        logger.info('First execution of lyse routine...')
        try:
            from queue import Queue
        except ImportError:
            # PY2
            from Queue import Queue
        logger.debug('Creating queue.')
        lyse.routine_storage.queue = Queue()
    if (
        hasattr(lyse.routine_storage, 'optimisation')
        and lyse.routine_storage.optimisation.is_alive()
    ):
        cost_dict = cost_analysis(
            cost_key=config['cost_key'] if not config['mock'] else [],
            maximize=config['maximize'],
            x=lyse.routine_storage.params[0] if config['mock'] else None,
        )

        if not cost_dict['bad'] or not config['ignore_bad']:
            if check_runmanager(config):
                if verify_globals(config):
                    logger.debug('Putting cost in queue.')
                    lyse.routine_storage.queue.put(cost_dict)
                else:
                    message = 'NOT putting cost in queue because verify_globals failed.'
                    logger.debug(message)
            else:
                message = 'NOT putting cost in queue because check_runmanager failed.'
                logger.debug(message)
        else:
            message = (
                'NOT putting cost in queue because cost was bad and ignore_bad is True.'
            )
            logger.debug(message)

    elif check_runmanager(config):
        logger.info('(Re)starting optimisation process...')
        import threading
        import mloop_interface

        logger.debug('Starting interface thread...')
        lyse.routine_storage.optimisation = threading.Thread(
            target=mloop_interface.main
        )
        lyse.routine_storage.optimisation.daemon = True
        lyse.routine_storage.optimisation.start()
        logger.debug('Interface thread started.')
    else:
        print(
            '\nNot (re)starting optimisation process.',
            'Please address above warnings before trying again.',
        )
