from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import leastsq
from scipy.optimize import curve_fit
from scipy import asarray as ar,exp
from astropy import constants as const
from astropy.io import fits
from astropy import units as u
from astropy import wcs
from astropy.wcs import WCS


plt.ion()

cm = plt.get_cmap('inferno')
cm.set_bad(color='black')
imkw = dict(origin='lower', interpolation='none', cmap=cm)

def gauss(x, a, x0, sigma):
    return a*exp(-(x-x0)**2/(2*sigma**2))


def mean2vel(CRVAL, CDELT, CRPIX, mean):
    ### transform teh pixel indexes (mean) into the velocity in km/s
    vel = [(CRVAL + CDELT * (mean[i] - CRPIX)) for i in range(len(mean))] #VLSR [km.s-1]
    return vel

# def plot_map(image, nb_fig, xtitle, xlabel, ylabel, vmin, vmax, cbar_label, wcs, imkw):
#     return fig

# To download the data cube from HI4PI >> wget http://cdsarc.u-strasbg.fr/ftp/J/A+A/594/A116/CUBES/GAL/CAR/CAR_G07.fits

# Constant values
mh    = 1.6737236e-27 # kg
mu    = 1.25 * mh
k     = 1.38064852e-23 # J.K-1 --> m2.kg.s-2.K-1
G     = const.G.value # m3.kg-1.s-2
M_sun = const.M_sun.value # kg

# Convertion tools
kpc2m  = u.kpc.to(u.m)
pc2cm  = u.pc.to(u.cm)

# HI4PI channel separation
dv = 1.29 #km.s-1

# hdu_list_data = fits.open("/data/amarchal/HI4PI/CAR/CAR_G07.fits")
hdu_list_data = fits.open("../CAR_G07.fits")
hdu_data = hdu_list_data[0]

cube = hdu_data.data
CDELT = hdu_data.header['CDELT3'] * 1.e-3 #km.s-1
CRVAL = hdu_data.header['CRVAL3'] * 1.e-3 #km.s-1
CRPIX = hdu_data.header['CRPIX3']
reso = np.abs(CDELT)

#Plot total integrated density map
w = wcs.WCS(naxis=2)
w.wcs.crpix = [hdu_data.header['CRPIX1'], hdu_data.header['CRPIX2']]
w.wcs.cdelt = np.array([hdu_data.header['CDELT1'], hdu_data.header['CDELT2']])
w.wcs.crval = [hdu_data.header['CRVAL1'], hdu_data.header['CRVAL2']]
w.wcs.ctype = [hdu_data.header['CTYPE1'], hdu_data.header['CTYPE2']]


wcs = WCS(hdu_data.header)
wcs2d = wcs.dropaxs(2)
plt.subplot(projection=wcs)

fig = plt.figure(0, figsize=(7, 7))
ax = fig.add_axes([0.1,0.1,0.78,0.8], projection=w)
ax.set_title("")
ax.set_xlabel("LON [degree]")
ax.set_ylabel("LAT [degree]")
img = ax.imshow(np.sum(cube,axis=0)*dv, aspect='auto', **imkw)
colorbar_ax = fig.add_axes([0.89, 0.1, 0.02, 0.8])
cbar = fig.colorbar(img, cax=colorbar_ax)
cbar.set_label("$NHI/ \, [1.83 \, 10^{18} \, cm^{-2}]$")

rms = 43.e-3 # K

velocity = np.array(mean2vel(CRVAL, CDELT, CRPIX, np.arange(cube.shape[0])))
idx = np.where((velocity < -185.) & (velocity > -225.))[0]

# hvc = subcube[:, 146:155, 175:199]
hvc = cube[idx, 144:158, 172:202]
clean_hvc = np.copy(hvc)
clean_hvc[np.where(hvc < 3. * rms)] = 0.

sum_clean_hvc = np.sum(clean_hvc, axis=0)

fig = plt.figure(1, figsize=(7, 7))
ax = fig.add_axes([0.1,0.1,0.78,0.8], projection=w)
ax.set_title("")
ax.set_xlabel("LON [degree]")
ax.set_ylabel("LAT [degree]")
img = ax.imshow(np.sum(cube[idx,:,:]*dv,axis=0), aspect='auto', **imkw)
colorbar_ax = fig.add_axes([0.89, 0.1, 0.02, 0.8])
cbar = fig.colorbar(img, cax=colorbar_ax)
cbar.set_label("$NHI/ \, [1.83 \, 10^{18} \, cm^{-2}]$")

fig = plt.figure(2)
ax1 = fig.add_subplot(111)
ax1.imshow(sum_clean_hvc, interpolation = 'none')
plt.show()

spectra = np.mean(clean_hvc, axis=(1,2))
vel_spectra = velocity[idx]

# http://stackoverflow.com/questions/10143905/python-two-curve-gaussian-fitting-with-non-linear-least-squares
x      = vel_spectra
y_real = spectra

n     = len(x)
mean  = np.sum(x * y_real) / np.sum(y_real)
sigma = np.sqrt(np.sum((x - mean)**2 * y_real) / np.sum(y_real))

popt, pcov = curve_fit(gauss, x, y_real, p0 = [1, mean, sigma])

fig = plt.figure(3, figsize=(16,9))
ax1 = fig.add_subplot(111)
ax1.plot(x, spectra, '.b', markersize=8)
ax1.plot(x, gauss(x,*popt), color='r')

theta = np.radians(15. * (51-29)/266.)

NHI = 1.82243e18 * np.sum(spectra) * dv # in cm-2
density_surf = NHI * mh * pc2cm**2 / M_sun # Msun.pc-2
dispersion = popt[2] * 1.e3 # m/s
Tk  = mh * dispersion**2 / k # K

d    = np.arange(1000) + 1 # kpc

b    = 41 # deg
z    = d * np.sin(np.radians(b))

nHI  = (NHI/1.e-4) / theta / (d * kpc2m) *1.e-6 # cm-3
Ps_k = (nHI * Tk) - ((mu**2 * G * (NHI/1.e-4)**2 * np.pi / 15. / k)*1.e-6)# K.cm-3

def P_k_Wolfire(z):
    return 2250. * (1. + (z**2 / 19.6))**(-1.35)

Ps_k_theory = P_k_Wolfire(z)

fig = plt.figure(4, figsize=(16,9))
ax1 = fig.add_subplot(111)
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.set_xlabel('$z (kpc)$', fontsize=18)
ax1.set_ylabel('$P_s.k^{-1} (K.cm^{-3})$', fontsize=18)
ax1.plot(z, Ps_k, color='r', linewidth=2., label='HVC stability')
ax1.plot(z, Ps_k_theory, color='b', linewidth=2., label='HIM (Wolfire et al. 1995)')
legend = ax1.legend(loc=1, shadow=True)
frame = legend.get_frame()
frame.set_facecolor('0.90')
for label in legend.get_texts():
    label.set_fontsize('large')
for label in legend.get_lines():
    label.set_linewidth(1.5)
plt.show()

