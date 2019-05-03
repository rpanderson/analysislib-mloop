import lyse
import numpy as np

def lorentzian(x, s=0.05):
    return 1 / (1 + x ** 2) + s * np.random.randn()

if __name__ == '__main__':
    # Runs each time this analysis routine does
    if not hasattr(lyse.routine_storage, "queue"):
        print("First execution of lyse routine...")
        import Queue
        lyse.routine_storage.queue = Queue.Queue()
    if (
        hasattr(lyse.routine_storage, "optimisation")
        and lyse.routine_storage.optimisation.is_alive()
    ):
        lyse.routine_storage.queue.put(-lorentzian(lyse.routine_storage.x))
    else:
        print("(Re)starting optimisation process...")
        import threading
        from mloop_interface import optimus
        lyse.routine_storage.optimisation = threading.Thread(target=optimus)
        lyse.routine_storage.optimisation.daemon = True
        lyse.routine_storage.optimisation.start()