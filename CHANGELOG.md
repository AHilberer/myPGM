# Changelog

All notable changes to myPGM are listed here. Versions follow [semantic versioning](https://semver.org).

## [1.0.0] - 2026-10-18

First stable release. Compared with the previous `main` branch, it fixes several fitting and stability
problems, adds fit uncertainties, a session safety net and a clearer pressure table, and comes with an
automated test suite.

### Added
- **Fit uncertainty**: σx and σP (statistical precision of the fit) in the fitted pressure title
  (`P ± σP`), in the PvPm table and CSV export, and as error bars in the PvPm plot.
- **Unsaved work protection**: closing with unsaved changes asks Save / Discard / Cancel.
- **Automatic session backup** every 30 s in the user folder, one per myPGM window; after a crash the
  backup is offered for recovery at the next start.
- **Log file** in the user folder (e.g. `~/Library/Application Support/myPGM/mypgm.log` on macOS),
  with every error shown in the app; `--debug` adds files loaded, fit results and sessions.
- **`--demo`** opens a ready example session: three ruby spectra and the H2 vibron spectrum fitted and
  added to the table with membrane pressures of 8, 15, 24 and 27 bar.
- **`mypgm` command** after `pip install -e .`; dependencies and Python ≥ 3.10 declared in `pyproject.toml`.
- **PvPm table**: units in the headers, `P ± σP`, unit in each x cell, a `#` column giving the order
  points were added, sorting by any column, a colour dot per calibration (as in the plot), file path
  on hover, and a right-click header menu to show or hide columns (T, x0, T0 and σx hidden by default;
  T shown and highlighted when a point is not at 298 K).
- Short calibration names (e.g. "Sm Datchi 1997", "H2 vibron") in the table and plot legend.
- An example script comparing the ruby and samarium scales: `examples/plot_calibrations.py`.

### Changed
- The example spectra are only loaded with `--demo` (they were loaded at every start).
- The CSV export is built from the data: every column at full precision, ASCII headers with units,
  plus the x unit, fit model and file path (it used to copy the rounded display text).
- Deleting a file that has a point in the PvPm table keeps the point (as a table-only entry).
- The manual background stays flat beyond the first and last clicked points.
- Voigt fits start from the measured peak height: Single Voigt, the H2 default model, now converges
  on the H2 vibron (it did not on the example spectrum).
- The font size setting applies to the whole application, including plots and the PvPm table, and is
  consistent at startup.
- The theme applies to every window and dialog.
- "Load latest" picks the newest `.asc` or `.txt` file, and does not load the same file twice.
- The Pm dialog starts from the last Pm.
- The PvPm plot joins points in the table order; "Display lines" moved to the plot's right-click menu.
- The x0 field is greyed out (and blank in the table) for calibrations that do not use it (H2 vibron).
- The PvPm windows open next to the main window, inside the screen (they could open off-screen).
- A repeated unexpected error is shown once, the repeats being counted in the log.

### Fixed
- Errors that closed the application: unreadable files, fits failing to find enough peaks, clicks
  outside the plot area, duplicate manual background points, corrupted session files (which also
  emptied the current session).
- Single-peak fits started from the smallest peak (R2 instead of R1 on ruby), and peak widths were
  mismatched in the initial guess.
- A fit could silently use the calibration's default x0/T0 instead of the values in the toolbox.
- Processing steps undid each other: smoothing dropped the alternative spectrometer calibration, a
  second automatic background was lost when smoothing, and Reset Bg dropped the smoothing.
- Switching "Fit range" off kept using the previous range.
- Two spectra loaded within the same millisecond overwrote each other.
- Sorting the PvPm table by P or x raised an error for each comparison.
- The spectrum axis units could come from the previously selected spectrum (e.g. cm⁻¹ on a ruby
  spectrum).
- The font size window wiped the theme, and the T field turned orange at 298 K in light mode.
- On Linux under Wayland, the terminal filled with "Wayland does not support
  QWindow::requestActivate()" warnings; these harmless Qt messages are now muted.

### Known limitations
- σx and σP are the statistical precision of the fit only: they do not include the uncertainty on x0,
  T, the calibration itself or the choice of fit model.
- The Raman edge model needs a fit range around the edge: on the whole spectrum it can pick an
  unrelated feature.
- Settings (λ0, theme, font size, folders) are not remembered between launches.
- Tested on macOS and Linux (AlmaLinux, Wayland); Windows has not been tested yet.
- No standalone executables yet.

### Development
- pytest suite (245 tests: calibrations, file parser, fits on the example spectra, processing, sessions,
  GUI workflows), run on GitHub Actions for Python 3.10 and 3.13 and with the oldest supported
  dependency versions.
- Dead code, duplicated code and unused imports removed; `print` replaced by logging.

## [0.1] - 2025-04-09

Pre-release.
