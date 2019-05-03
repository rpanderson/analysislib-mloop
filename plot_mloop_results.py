import lyse
import numpy as np
import matplotlib.pyplot as plt

def lorentzian(x, s=0.05):
    return 1 / (1 + x ** 2) + s * np.random.randn()

def sinc2(x, s=0.01):
    return np.sinc(x)**2 + s * np.random.randn()

try:
    df = lyse.data()
    df.plot(x='x', y=('fake_result', 'y'), kind='scatter')
    x_p = np.linspace(df.x.min(), df.x.max(), 100)
    plt.plot(x_p, sinc2(x_p, s=0))
    plt.axis(ymin=0, ymax=1.1)
    plt.show()
except:
    pass