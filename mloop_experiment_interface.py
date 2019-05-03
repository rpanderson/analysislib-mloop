import lyse
import os
import zmq
import h5py
import time
import signal
import datetime
import zprocess
import numpy as np
import runmanager as rm
import labscript_utils.labconfig as labconfig
import labscript_utils.shared_drive as shared_drive

#=========================================================================

# Lab configuration
lc = labconfig.LabConfig()

# Path to experiment shot storage
experiment_shot_storage = lc.get('DEFAULT', 'experiment_shot_storage')

# server wait time
server_timeout = int(lc.get('DEFAULT', 'server_timeout'))

# Ports
BLACS_port = int(lc.get('ports', 'blacs'))
BLACS_hostname = lc.get('servers', 'blacs')
mloop_experiment_port = int(lc.get('ports', 'mloop-experiment'))

#=========================================================================

# mloop experiment headless run manager
def mloop_run_experiment(config_dict):

    # Copy hdf5 file ready for optimization
    now = datetime.datetime.now()

    # extract relevant information from master config file
    params_to_change = config_dict["params_to_change"]
    template_file = config_dict["template_file"]
    template_folder = config_dict["template_folder"]
    globals_groups = config_dict["globals_groups"]
    labscript_file = config_dict["labscript_file"]
    globals_values = config_dict["mloop_params"]

    # Setup paths
    template_path = os.path.join(template_folder, template_file)

    labscriptlib_path = lc.get('DEFAULT', 'labscriptlib')
    labscript_path = os.path.join(labscriptlib_path, labscript_file)

    # TODO: Change output_file, sequence_index, run number attribute, mloop session id, in h5 file also
    output_file = template_file.replace('.h5', '_{}_mloop{:05d}.h5'.format(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"), config_dict["iter_count"]))
    output_path = os.path.join(template_folder, output_file)

    # Change optimisation globals in place
    for i in range(len(params_to_change)):
        print('Changing value of {:}/{:} to {:}'.format(globals_groups[i], params_to_change[i], globals_values[i]))
        rm.set_value(template_path, globals_groups[i], params_to_change[i], globals_values[i])

    # Run shot of the experiment via BLACS
    rm.compile_labscript_with_globals_files_async(labscript_path, template_path, output_path,
                                                  0,
                                                  # lambda x: print('Experiment submitted! (Not.)'))
                                                  lambda x: zprocess.zmq_get(BLACS_port, BLACS_hostname,
                                                                             data=shared_drive.path_to_agnostic(output_path)))

if __name__ == "__main__":

    print("Opening ZProcess Server for Experiment\n")

    # setup port listening with default time out (estimated single shot max time)
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.setsockopt(zmq.LINGER, 0)
    socket.RCVTIMEO = server_timeout*1000
    socket.bind("tcp://0.0.0.0:{}".format(mloop_experiment_port))
    
    def exit_handler(*args, **kwargs):
        # close socket 
        socket.close()
        # terminate context
        context.term()
        #  This closes the socket but the process still hangs?
        exit()

    signal.signal(signal.SIGTERM, exit_handler)
    signal.signal(signal.SIGINT, exit_handler)

    while True:
        try:
            # recieve configuration dictionary with updated parameters and block
            # until recieved or timeout
            config_dict = socket.recv_pyobj()
        except zmq.error.Again:
            print('\nExperiment interface timed out!')
            exit_handler()

        print("\nRunning new experiment with specified parameters")
        mloop_run_experiment(config_dict)
        socket.send_pyobj("Experiment parameters recieved", protocol=2)
