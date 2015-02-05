#!/usr/bin/env python
import numpy as np
import naima
import astropy.units as u
from astropy.constants import m_e,c
from astropy.io import ascii

## Read data

xray = ascii.read('CrabNebula_Fake_Xray.dat')
vhe = ascii.read('CrabNebula_HESS_2006_ipac.dat')

## Model definition

from naima.models import InverseCompton, Synchrotron, ExponentialCutoffPowerLaw

def ElectronIC(pars,data):

    # Match parameters to ECPL properties, and give them the appropriate units
    amplitude = pars[0] / u.eV
    alpha = pars[1]
    e_cutoff = (10**pars[2]) * u.TeV
    B = pars[3] * u.uG

    # Initialize instances of the particle distribution and radiative models
    ECPL = ExponentialCutoffPowerLaw(amplitude,10.*u.TeV, alpha, e_cutoff)
    IC = InverseCompton(ECPL, seed_photon_fields=['CMB'])
    SYN = Synchrotron(ECPL, B=B)

    # compute flux at the energies given in data['energy'], and convert to units
    # of flux data
    # Data contains the merged X-ray and VHE spectrum:
    # Select xray and vhe bands and only compute Sync and IC for these bands,
    # respectively
    model = np.zeros_like(data['flux'])

    xray_idx = np.where(data['energy'] < 1*u.MeV)
    model[xray_idx] = SYN.flux(data['energy'][xray_idx],
                               2.0*u.kpc).to(data['flux'].unit)

    vhe_idx = np.where(data['energy'] >= 1*u.MeV)
    model[vhe_idx] = IC.flux(data['energy'][vhe_idx],
                             2.0*u.kpc).to(data['flux'].unit)

    # An alternative, slower approach, is to compute both models for all the
    # energy range:
    # model = (IC.flux(data,distance=2.0*u.kpc).to(data['flux'].unit) +
    #          SYN.flux(data,distance=2.0*u.kpc).to(data['flux'].unit))

    # The electron particle distribution (nelec) is saved in units or particles
    # per unit lorentz factor (E/mc2).  We define a mec2 unit and give nelec and
    # elec_energy the corresponding units.
    mec2 = u.Unit(m_e*c**2)
    nelec = IC._nelec * (1/mec2)
    elec_energy = IC._gam * mec2

    # The first array returned will be compared to the observed spectrum for
    # fitting. All subsequent objects will be stores in the sampler metadata
    # blobs.
    return model, (elec_energy,nelec), IC.We

## Prior definition

def lnprior(pars):
	"""
	Return probability of parameter values according to prior knowledge.
	Parameter limits should be done here through uniform prior ditributions
	"""

	logprob = naima.uniform_prior(pars[0],0.,np.inf) \
                + naima.uniform_prior(pars[1],-1,5) \
                + naima.uniform_prior(pars[3],0,np.inf)

	return logprob

if __name__=='__main__':

## Set initial parameters and labels

    # Estimate initial magnetic field and get value in uG
    B0 = naima.estimate_B(xray, vhe).to('uG').value

    p0=np.array((4.9,3.3,np.log10(48.0),B0))
    labels=['norm','index','log10(cutoff)','B']

## Run sampler

    sampler,pos = naima.run_sampler(data_table=[xray,vhe], p0=p0, labels=labels, model=ElectronIC,
            prior=lnprior, nwalkers=50, nburn=50, nrun=10, threads=4, data_sed=False)

## Save sampler
    from astropy.extern import six
    from six.moves import cPickle
    sampler.pool=None
    cPickle.dump(sampler,open('CrabNebula_SynIC_sampler.pickle','wb'))

## Diagnostic plots

    naima.save_diagnostic_plots('CrabNebula_SynIC',sampler,sed=True)
    naima.save_results_table('CrabNebula_SynIC',sampler)

