"""Compare the ruby and samarium borate pressure scales shipped with myPGM.

Needs matplotlib (not a myPGM dependency):
    python -m pip install matplotlib
    python examples/plot_calibrations.py
"""
import matplotlib.pyplot as plt
import numpy as np

from myPGM.calibrations import (Pruby2020, PrubyMao1986, PrubyMao1986_DatchiF,
                                PrubyHolzapfel2005, PrubyDO2007,
                                PsamDatchi1997, PsamRashchenko2015)

fig, ax = plt.subplots(2, figsize=(7,9), sharex=True)
ax[0].set_xlabel('wavelength (nm)')
ax[0].set_ylabel('P (GPa)')

ax[1].set_xlabel('wavelength (nm)')
ax[1].set_ylabel('P - Pruby2020 (GPa)')

ll = np.linspace(694.28, 720, 100)
l0 = 694.28

T1 = 298
T0 = 298

ruby2020 = Pruby2020(ll, T1, l0, T0)

ax[0].plot(ll, ruby2020, c='k', label='ruby 2020')
ax[0].plot(ll, PrubyMao1986(ll, T1, l0, T0), c='r', label='Mao 1986')
ax[0].plot(ll, PrubyMao1986_DatchiF(ll, T1, l0, T0), c='pink', linestyle='dashed', label='Mao 1986 Datchi Form')
ax[0].plot(ll, PrubyHolzapfel2005(ll, T1, l0, T0), c='green', label='Holzapfel 2005')
ax[0].plot(ll, PrubyDO2007(ll, T1, l0, T0), c='gold', label='Dorogokupets-Oganov 2007')

# differences
ax[1].plot(ll, ruby2020-ruby2020, c='k')
ax[1].plot(ll, PrubyMao1986(ll, T1, l0, T0) - ruby2020, c='r')
ax[1].plot(ll, PrubyMao1986_DatchiF(ll, T1, l0, T0) - ruby2020, c='pink', linestyle='dashed')
ax[1].plot(ll, PrubyHolzapfel2005(ll, T1, l0, T0) - ruby2020, c='green')
ax[1].plot(ll, PrubyDO2007(ll, T1, l0, T0) - ruby2020, c='gold')

ax[0].legend()

plt.show()

fig, ax = plt.subplots()
ax.set_title('Samarium Borate')
ax.set_xlabel('wavelength (nm)')
ax.set_ylabel('P (GPa)')

ll = np.linspace(685.41, 700, 100)
l0 = 685.41

T1 = 298
T0 = 298

ax.plot(ll, PsamDatchi1997(ll, T1, l0, T0), c='k', label='Datchi 1997')
ax.plot(ll, PsamRashchenko2015(ll, T1, l0, T0), c='r', label='Rashchenko 2015')

ax.legend()

plt.show()
