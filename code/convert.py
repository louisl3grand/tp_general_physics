import numpy as np
import h5py
from spectral_cube import SpectralCube

#path
path     = '/data/glx-calcul1/data1/amarchal/HI4PI/data/'
filename = 'CAR_G07.fits'

#load hyperspectral cube
cube = SpectralCube.read(path + filename, format='fits')

out = np.zeros((len(cube), len(cube[0]), len(cube[0])))
for i in range(len(cube)):
    out[i] = cube[i].value

#write in h5 format
with h5py.File('data.h5', 'w') as hf:
    hf.create_dataset('temperature', data=out)
    hf.create_dataset('velocity', data=cube.spectral_axis)
