import lyse
import runmanager.remote as rm
import numpy as np
import mloop_config

try:
    from labscript_utils import check_version
except ImportError:
    raise ImportError('Require labscript_utils > 2.1.0')

check_version('lyse', '2.5.0', '3.0')
check_version('zprocess', '2.13.1', '3.0')
check_version('labscript_utils', '2.12.5', '3.0')


def check_runmanager(config):
    msgs = ['WARNING(s):']
    rm_globals = rm.get_globals()
    if not all([x in rm_globals for x in config['mloop_params']]):
        msgs.append('Not all optimisation parameters present in runmanager.')
    if not rm.get_run_shots():
        msgs.append('Run shot(s) not selected in runmanager.')
    if rm.error_in_globals():
        msgs.append('Error in runmanager globals.')
    n_shots = rm.n_shots()
    if n_shots > 1 and not config['ignore_bad']:
        msgs.append(
            f'runmanager is set to compile {n_shots:d} shots per request, but your '
            + 'mloop_config has ignore_bad = False. You are advised to (i) remove '
            + 'iterable globals so as to compile one shot per cost or (ii) set '
            + 'ignore_bad = True in your mloop_config and only return one cost with '
            + 'bad = False per sequence.'
        )
    if len(msgs) > 1:
        print('\n'.join(msgs))
    return len(msgs) <= 1


def verify_globals(config):
    # Get the current runmanager globals
    rm_globals = rm.get_globals()
    current_values = [rm_globals[name] for name in config['mloop_params']]

    # Retrieve the parameter values requested by M-LOOP on this iteration
    requested_values = lyse.routine_storage.params
    requested_dict = dict(zip(config['mloop_params'], requested_values))

    # Get the parameter values for the shot we just computed the cost for
    df = lyse.data()
    shot_values = [df[name].iloc[-1] for name in config['mloop_params']]

    # Verify integrity by cross-checking against what was requested
    if not np.array_equal(current_values, requested_values):
        print('Cost requested for different values to those in runmanager.')
        print('Please add an executed shot to lyse with: ', requested_dict)
        return False
    if not np.array_equal(shot_values, requested_values):
        print('Cost requested for different values to those used to compute cost.')
        print('Please add an executed shot to lyse with: ', requested_dict)
        return False
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
    cost_dict = {'bad': False}

    # Retrieve current lyse DataFrame
    df = lyse.data()

    # Use the most recent shot
    ix = -1

    # Retrieve cost from specified column
    if len(df) and cost_key in df:
        cost = (df[cost_key].astype(float).values)[ix]
        if np.isnan(cost) or np.isinf(cost):
            cost_dict['bad'] = True
        else:
            cost_dict['cost'] = (1 - 2 * maximize) * cost
        u_cost_key = cost_key[:-1] + ('u_' + cost_key[-1],)
        if u_cost_key in df:
            cost_dict['uncer'] = df[u_cost_key].iloc[ix]

    # If it doesn't exist, generate a fake cost
    elif x is not None:
        from fake_result import fake_result

        cost_dict['cost'] = (1 - 2 * maximize) * fake_result(x)

    # Or just use a constant cost (for debugging)
    else:
        cost_dict['cost'] = 1.2

    return cost_dict


if __name__ == '__main__':
    config = mloop_config.get()
    if not hasattr(lyse.routine_storage, 'queue'):
        print('First execution of lyse routine...')
        try:
            from queue import Queue
        except ImportError:
            # PY2
            from Queue import Queue
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
        if (
            (not cost_dict['bad'] or not config['ignore_bad']) and
            check_runmanager(config) and
            verify_globals(config)
        ):
            lyse.routine_storage.queue.put(cost_dict)
    elif check_runmanager(config):
        print('(Re)starting optimisation process...')
        import threading
        import mloop_interface

        lyse.routine_storage.optimisation = threading.Thread(
            target=mloop_interface.main
        )
        lyse.routine_storage.optimisation.daemon = True
        lyse.routine_storage.optimisation.start()
    else:
        print(
            '\nNot (re)starting optimisation process.',
            'Please address above warnings before trying again.',
        )
