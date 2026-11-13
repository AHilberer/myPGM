# Changelog

All notable changes to myPGM are listed here. Versions follow [semantic versioning](https://semver.org).

## [Unreleased]

### Added
- **Save session** writes to the session's own file (shown in the window title) and only asks for a
  file the first time; **Save session as...** always asks. Keyboard shortcuts: Ctrl+O, Ctrl+S,
  Ctrl+Shift+S and Ctrl+Q (Cmd on macOS).
- The theme, font size and the folders last used in file dialogs are remembered between launches
  (in `~/.config/myPGM/myPGM.ini`, or `%APPDATA%\myPGM\myPGM.ini` on Windows). Reference positions
  (λ0, ν0) are not, on purpose: they are measured for each experiment.

### Changed
- The fit error dialog gives the reason (e.g. too few points in the fit range); it was only in the log.
- Error dialogs, the Pm dialog and the file dialog open over the main window (they could open
  behind it).
- Session files are about 2.3x smaller: compact JSON, without the fitted curve (rebuilt when the
  session is opened). Older sessions still open, and new ones open in myPGM 1.0.

### Fixed
- Exporting the table to a file that cannot be written (no permission, file open elsewhere) gave an
  unexpected error; it is now reported. The `.csv` extension was not added when `.csv` appeared
  elsewhere in the path, and was added again to a name ending in `.CSV`.
- A failed fit left the spectrum with the toolbox calibration but its previous position, so a
  point already in the PvPm table could show a wrong pressure; a failed fit now changes nothing.
- A fit range with too few points for the model gave an "Unexpected error" instead of the fit error.
- Manual Bg with a single click subtracted the previous manual background a second time.
- "Add fit to table" ignored T, x0 and T0 edited in the pressure toolbox after the fit, so the table
  point did not have the pressure shown in the toolbox. They are now used; if the calibration,
  position or pressure was changed in the toolbox, the fit is not added and a message explains why.
- A session backup that could not be loaded was offered for recovery at every start; it is now
  kept aside as `.discarded.json`, like a declined backup.
- Auto Bg left out the last point of the spectrum: after the last but one anchor the background
  stayed flat, so a sloped baseline was only partly removed at the high-x end.
- Spectra stored with x decreasing: Auto Bg used the upper hull (making the spectrum negative), and
  the Raman edge and the derivative plot followed the file order instead of increasing x.
- Spectrum files with a row of more values than the others (e.g. a numeric header line) could not
  be loaded.
- A single-column spectrometer calibration file with decimal commas (`690,01`) was read as two
  columns, giving a flat x axis (690, 690, ...) without any error.
- Opening a session did not update the spectrometer calibration file name shown next to "Use";
  sessions now store it.
- A spectrum with no positive intensity was turned upside down by the normalisation, and an
  all-zero spectrum loaded as NaN; the latter is now refused with a clear message.
- The automatic backup could read the file order while Move up/down was changing it.

### Development
- Fit models declare their number of peaks and parameters per peak (checked against the fit
  function), instead of guessing them from the number of arguments.
- Each window works on its own copies of the calibrations: editing x0 or T0 no longer changes the
  module-level calibration objects (which leaked between tests).
- The automatic backup (file, lock, background writing, scan for orphans) moved from the presenter
  to `myPGM/session_backup.py`.

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
