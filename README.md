<h1 align="center"> myPGM - Pressure Gauge Monitor </h1>

<div align="center">
<img alt="Demo myPGM UI" src="myPGM/resources/UI_demo.png"> </img>
</div>

**myPGM** is a spectroscopic pressure gauge fitting software for pressure determination in high pressure experiments.

It currently supports the following pressure scales:
- Ruby fluorescence
- Samarium doped strontium borate fluorescence
- Molecular hydrogen vibron
- Cubic boron nitride Raman
- Diamond Raman edge.

**myPGM** supports a simple file management system to process multiple spectra and follow pressure evolution during a typical diamond anvil cell experiment (the external pressure control is set to be membrane pressure for membrane DAC experiments, for now).

This piece of software is still a work in progress so do not hesitate to open issues on this GitHub page or to contact the authors if you notice any bugs.

New versions may come regularly on this page before a first full release, so come back for more features !


## Installation from source

### 1) Get a copy of the code:

```bash
git clone https://github.com/AHilberer/myPGM.git
````
```bash
cd myPGM
```

### 2) (Optional) Set up a virtual environment in the code folder:

```bash
python3 -m venv .venv
```
```bash
source .venv/bin/activate
```

Run the code.

To exit the virtual environment use:

```bash
deactivate
```


### 3) Install the required dependencies:

```bash
python3 -m pip install -r requirements.txt
```

or manually install the required non-native python packages: numpy, pandas, matplotlib, scipy and PyQt5.

### 4) Run as a script:

Start the software using :

```bash
python3 start.py
```

## Executables
Currently not available (WIP)

## Contributors

- __Antoine Hilberer__ - antoine.hilberer@cea.fr
- __Alexis Forestier__
