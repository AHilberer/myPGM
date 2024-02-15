# PGM - Pressure Gauge Monitor
 
PGM - Pressure Gauge Monitor is a spectral pressure gauge fitting software for pressure determination in high pressure experiments. It currently supports ruby, samarium doped strontium borate, and diamond Raman edges scales.

## Installation
### 1) Get a copy of the code:

`$ git clone https://github.com/AHilberer/PGM.git`

`$ cd PGM`

### 2) (Optional) Set up a virtual environment in the code folder:

`$ python3 -m venv .venv`

`$ source .venv/bin/activate`

### 3) Install the required dependencies:

`$ python3 -m pip install -r requirements.txt `

or manually install the required non-native python packages: numpy, pandas, matplotlib, scipy and PyQt5.

### 4) Run as a script:

`$ python3 PGMonline/PGM_online.py`
or
`$ python3 PGMonline/PGM_offline.py`

If you are using a virtual environment use

`$ deactivate`

to quit it.

## Contributors

[<img src="https://github.com/{{ AHilberer }}.png" width="60px;"/><br /><sub><ahref="https://github.com/{{ AHilberer }}">{{ AHilberer }}</a></sub>](https://github.com/{{ AHilberer }}/{{ PGM }}