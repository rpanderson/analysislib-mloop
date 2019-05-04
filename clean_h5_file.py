import os
import h5py
from shutil import copyfile

def clean_h5_file(h5file, new_h5_file, repeat_number=0):
    if os.path.exists(new_h5_file):
        copyfile(new_h5_file, new_h5_file + '.bak')
    with h5py.File(h5file, 'r') as old_file:
        with h5py.File(new_h5_file, 'w') as new_file:
            groups_to_copy = [
                'devices',
                'calibrations',
                'script',
                'globals',
                'connection table',
                'labscriptlib',
                'waits',
                'time_markers',
            ]
            for group in groups_to_copy:
                if group in old_file:
                    new_file.copy(old_file[group], group)
            for name in old_file.attrs:
                new_file.attrs[name] = old_file.attrs[name]
            new_file.attrs['run repeat'] = repeat_number
    return new_h5_file