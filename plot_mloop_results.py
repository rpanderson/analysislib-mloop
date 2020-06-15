import lyse
import numpy as np
import matplotlib.pyplot as plt
import mloop_config
from fake_result import fake_result

try:
    df = lyse.data()
    config = mloop_config.get()
    x = list(config['mloop_params'])[0]
    y = config['cost_key']
    try:
        # Try to use the most recent mloop_session ID
        gb = df.groupby('mloop_session')
        mloop_session = list(gb.groups.keys())[-1]
        subdf = gb.get_group(mloop_session)
    except Exception:
        # Fallback to the entire lyse DataFrame
        subdf = df
        mloop_session = None
    subdf.plot(x=x, y=y, kind='scatter')
    x_p = np.linspace(df[x].min(), df[x].max(), 200)
    plt.plot(x_p, fake_result(x_p, s=0))
    plt.axis(ymin=0, ymax=1.1)
    plt.title('M-LOOP session: {:}'.format(mloop_session))
    plt.show()
except Exception:
    pass
