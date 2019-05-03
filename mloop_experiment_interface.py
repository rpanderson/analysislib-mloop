import lyse
import os
import zmq
import signal
import datetime
import zprocess
import runmanager as rm
from labscript_utils import labconfig
from labscript_utils import shared_drive

# =========================================================================

# Lab configuration
lc = labconfig.LabConfig()
shot_storage = lc.get('DEFAULT', 'experiment_shot_storage')
blacs_port = lc.getint('ports', 'blacs')
blacs_host = lc.get('servers', 'blacs')
mloop_port = lc.getint('ports', 'compiler')
mloop_timeout = lc.getint('DEFAULT', 'server_timeout', fallback=5)

# =========================================================================


def compile_and_run_shot(config):

    # Copy hdf5 file ready for optimisation
    now = datetime.datetime.now()

    # extract relevant information from master config file
    params_to_change = config['params_to_change']
    template_file = config['template_file']
    template_folder = config['template_folder']
    globals_groups = config['globals_groups']
    labscript_file = config['labscript_file']
    globals_values = config['mloop_params']

    # Path to single (template) shot file whose expanded globals to compile with
    template_path = os.path.join(template_folder, template_file)

    # Path to experiment script
    labscript_path = os.path.join(lc.get('DEFAULT', 'labscriptlib'), labscript_file)

    # TODO: Change output_file, sequence_index, run number attribute, mloop session id, in h5 file also
    try:
        shot_output_dir = template_folder
        filename_prefix = now.strftime(config['filename_prefix_format']).format(
            template_basename=os.path.splitext(template_file)[0],
            iter_count=config['iter_count'],
        )
    except KeyError:
        sequence_attrs, shot_output_dir, filename_prefix = rm.new_sequence_details(
            script_path=labscript_path, config=lc, increment_sequence_index=False
        )

    output_file = filename_prefix + '.h5'
    output_path = os.path.join(shot_output_dir, output_file)
    print(output_path)

    # Change optimisation globals in place
    for i in range(len(params_to_change)):
        print(
            '   Changing value of {:}/{:} to {:}'.format(
                globals_groups[i], params_to_change[i], globals_values[i]
            )
        )
        rm.set_value(
            template_path, globals_groups[i], params_to_change[i], globals_values[i]
        )

    # Compile shot and immediately submit to BLACS
    rm.compile_labscript_with_globals_files_async(
        labscript_file=labscript_path,
        globals_files=template_path,
        output_path=output_path,
        stream_port=0,
        done_callback=lambda x: zprocess.zmq_get(
            blacs_port, blacs_host, data=shared_drive.path_to_agnostic(output_path)
        ),
    )


if __name__ == '__main__':

    print('Launching zprocess server for experiment compilation and submission.\n\n')

    # setup port listening with default time out (estimated single shot max time)
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.setsockopt(zmq.LINGER, 0)
    socket.RCVTIMEO = mloop_timeout * 1000
    socket.bind('tcp://0.0.0.0:{}'.format(mloop_port))

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
            print('\nWaiting for compilation request...')
            config = socket.recv_pyobj()
        except zmq.error.Again:
            print('\nTimed out waiting for updated parameters.')
            exit_handler()

        print('Received updated parameters...')
        compile_and_run_shot(config)
        socket.send_pyobj('Experiment parameters recieved', protocol=2)
