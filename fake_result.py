import lyse
import numpy as np

def lorentzian(x, s=0.01):
    return 1 / (1 + x ** 2) + s * np.random.randn()

def sinc2(x, s=0.01):
    return np.sinc(x) ** 2 + s * np.random.randn()

if __name__ == '__main__':
    run = lyse.Run(lyse.path)
    run_globals = run.get_globals()
    y = sinc2(run_globals['x'])
    run.save_result('y', y)