import lyse
import numpy as np
import mloop_config

try:
    from labscript_utils import check_version
except ImportError:
    raise ImportError('Require labscript_utils > 2.1.0')

check_version('lyse', '2.5.0', '3.0')
check_version('zprocess', '2.13.1', '3.0')
check_version('labscript_utils', '2.12.5', '3.0')


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
            x=lyse.routine_storage.x if config['mock'] else None,
        )
        if not cost_dict['bad'] or not config['ignore_bad']:
            lyse.routine_storage.queue.put(cost_dict)
    else:
        print('(Re)starting optimisation process...')
        import threading
        import mloop_interface

        lyse.routine_storage.optimisation = threading.Thread(
            target=mloop_interface.main
        )
        lyse.routine_storage.optimisation.daemon = True
        lyse.routine_storage.optimisation.start()
