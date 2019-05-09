import lyse
import numpy as np


def lorentzian(x, s=0.01):
    return 1 / (1 + x ** 2) + s * np.random.randn()


def sinc2(x, s=0.01):
    return np.sinc(x) ** 2 + s * np.random.randn()


def fake_result(*args, **kwargs):
    return sinc2(*args, **kwargs)


if __name__ == '__main__':
    run = lyse.Run(lyse.path)
    run_globals = run.get_globals()
    y = fake_result(run_globals['x'])
    # Give a nan result occasionally to test bad shots
    # Ensure ignore_bad = false in mloop_config.ini.
    if np.random.rand() < 0.9:
        run.save_result('y', y)
        run.save_result('u_y', 0.01)
