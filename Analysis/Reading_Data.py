# This is an example file of how to read data

# First import libraries
from scipy.io import loadmat

# load the files
file_path = "/data/example.mat"

# load the mat file, which is essentially a dictionary
mat = loadmat(file_path)

# Extract the data fields
neural_time_stamp = mat['nsp_time']
eeg_data = mat['eeg'] # this is a numpy array
go_cues = mat['go_timestamp']
trial_end = mat['trial_end_timestamp']
label = mat['cue'] 

# Visualize your data
# ...
