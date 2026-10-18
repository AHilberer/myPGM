<h1 align="center"> myPGM - Pressure Gauge Monitor </h1>

<div align="center">
<img alt="Demo myPGM UI" src="myPGM/resources/UI_demo.png"> </img>
</div>

<br>

**myPGM** is a desktop application for fitting spectroscopic pressure gauges and estimating pressure in high-pressure experiments.

It currently supports the following pressure scales:
- Ruby fluorescence
- Samarium doped strontium borate fluorescence
- Molecular hydrogen vibron
- Cubic boron nitride Raman
- Diamond Raman edge.

**myPGM** also provides a simple workflow to process multiple spectra and track pressure evolution during a typical diamond anvil cell experiment. The external pressure control is currently intended for membrane pressure in membrane DAC setups.

# Main features

- Load and organize several spectra in the same session, including quick access to the latest file from a selected acquisition folder.
- Fit pressure markers with several line-shape models, including single or double peak profiles and Raman edge fitting depending on the selected calibration.
- Switch between supported calibrations directly from the interface and adjust pressure, reference position and temperature parameters interactively.
- Apply basic spectrum preprocessing before fitting, including smoothing, automatic background subtraction and manual background definition.
- Use an optional spectrometer calibration file to recalculate the spectral axis when needed.
- Switch to a dark mode interface for light-sensitive environments, for example during low-light instrument operation.
- Store fitted points in a dedicated pressure table, visualize pressure evolution in a P vs Pm plot, and export the table to CSV.
- Show the fit uncertainty on the peak position (σx) and pressure (σP) in the plot title, the table and as error bars. This is the statistical precision of the fit only: it does not include the uncertainty on x0, T, the calibration itself or the choice of fit model. Raman edge positions have no fit uncertainty.
- Save and reload complete working sessions, including loaded spectra, fit results, table entries and spectrometer calibration state.

**myPGM** is still a work in progress, so please open an issue or contact the authors if you notice a bug or unexpected behavior.

# Quick start

Once the application is running, a typical workflow is:

1. Load one or several spectra.
2. Select the appropriate calibration and fit model.
3. Apply smoothing or background subtraction if needed.
4. Run the fit and inspect the extracted pressure.
5. Add selected results to the table to follow pressure evolution during the experiment.

# Installation from source

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

Later, to exit the virtual environment use:

```bash
deactivate
```


### 3) Install myPGM and its dependencies:

myPGM requires Python 3.10 or newer.

```bash
python3 -m pip install -e .
```

This also installs the `mypgm` command. (Alternatively, `python3 -m pip install -r requirements.txt` installs only the dependencies.)

### 4) Run the application:

```bash
mypgm
```

or, from the code folder, `python3 run.py` or `python3 -m myPGM`.

To start with the bundled example spectra loaded, add `--demo`:

```bash
mypgm --demo
```

# Log file

myPGM writes warnings and errors, including every error message shown in the app, to the terminal and to a log file in your user folder (the file is limited to 1 MB, with the last 3 files kept):

- macOS: `~/Library/Application Support/myPGM/mypgm.log`
- Windows: `%APPDATA%\myPGM\mypgm.log`
- Linux: `~/.local/share/myPGM/mypgm.log`

The exact path is printed at startup and shown in the dialog that appears if an unexpected error occurs. Please attach this file when reporting a bug.

For more detailed messages (files loaded, fit results, sessions saved and loaded), start the app with `--debug`:

```bash
mypgm --debug
```

# Running the tests

The test suite covers the pressure calibrations, the file parser, the fits on the bundled example spectra and the main GUI workflows (run headless, no window opens):

```bash
python3 -m pip install -e ".[test]"
python3 -m pytest
```

A test marked `xfail` describes a known bug that is not fixed yet. The tests also run on GitHub for every push and pull request.

# Executables
Currently not available (WIP)

# Contributors

- __Antoine Hilberer__ - antoine.hilberer@cea.fr
- __Alexis Forestier__ - alexis.forestier@cea.fr
