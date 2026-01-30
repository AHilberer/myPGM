import numpy as np
import pandas as pd
from copy import deepcopy
from importlib import resources
from scipy.optimize import minimize
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QAbstractListModel, QModelIndex
import csv

class PressureCalculationFailed(Exception):
    pass

def validate_scalar(value, name="Value"):
    if np.iscomplex(value):
        raise PressureCalculationFailed(f"{name} is complex")
    if np.isnan(value) or np.isinf(value):
        raise PressureCalculationFailed(f"{name} is NaN or infinite")
    return True

def load_style(qssfile):
    return resources.files("myPGM.ui").joinpath(qssfile).read_text()

def customparse_file2data(f):
    with open(f, 'r') as file:
        # Skip initial lines to determine the delimiter
        initial_skip = 100  
        for _ in range(initial_skip):
            file.readline()

        # Read a chunk from the middle of the file to determine the delimiter
        chunk_size = 2000
        chunk = file.read(chunk_size)
        file.seek(0)  # Reset file pointer to the beginning

        delimiter = csv.Sniffer().sniff(chunk).delimiter

        count = 0
        data_lines = []
        # Process the file line by line to determine header
        # When it will reach footer, it will be exluded too
        for line in file:
            sp = line.strip().split(delimiter)
            if len(sp) < 2:
                count += 1
            else:
                try:
                    _ = list(map(float, sp))
                    data_lines.append(line)
                except ValueError:
                    count += 1

        #print('delimiter : {}'.format(delimiter))
        #print('count : {}'.format(count))

        # Convert data_lines to a numpy array
        data = np.array([line.strip().split(delimiter) for line in data_lines], 
            dtype=np.float64)

        #print('length: {}'.format(len(data)))
        return data[:, :2] 



if __name__ == '__main__':
    import os
    f1 = os.path.dirname(__file__)+'/resources/various_file_formats/'+'Example_Ruby_3_tab_very_long_header.asc'
    
    print(customparse_file2data(f1))