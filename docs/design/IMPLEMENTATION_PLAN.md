# UI redesign: implementation plan for Claude Code

Work on the `antoine_dev` branch, one step at a time: each step is reviewed, tested and committed before the next one. The target is described in `docs/design/DESIGN.md` and the `mockup_*.png` captures.

## Ground rules (give these to Claude Code with every step)

- PyQt5 + pyqtgraph stay; no new runtime dependency unless agreed.
- Do not change fitting, calibrations maths, the data model or session files. Touch `presenter.py` only for wiring.
- Keep the widget attribute names that `presenter.py` and `tests/test_gui.py` use (e.g. `fit_button`, `fit_model_combo`, `PvPmTableWindow`, `PvPmPlotWindow`…). If one must change, update the tests in the same commit and say why.
- `python3 -m pytest` passes at the end of every step.
- Visual check at the end of every step: start the app headless on the demo session, grab the window and compare it with the mockup, e.g.
  ```bash
  QT_QPA_PLATFORM=offscreen python3 - <<'EOF'
  # build the app the way `mypgm --demo` does, process events, then:
  # window.resize(1440, 1010); window.grab().save("/tmp/step.png")
  EOF
  ```
  then open `/tmp/step.png` and list the visible differences with `docs/design/mockup_light.png` (and the dark one for theme steps). Fix what belongs to the current step; note the rest for later steps.

## Steps

1. **Theme system**
   - Replace `light-mode.qss` / `dark-mode.qss` by one QSS template filled from a Python token dict (`myPGM/ui/theme.py`: `LIGHT`, `DARK`, `CALIB_COLORS`, `apply_theme(app, dark)`), tokens from DESIGN.md §2–3.
   - Bundle Inter and JetBrains Mono in `myPGM/resources/fonts/` (OFL license files included) and load them at startup; numbers use the mono font.
   - Apply tokens to pyqtgraph (DESIGN.md §6) in the main plot, derivative plot and P vs Pm plot.
   - Outcome: same layout as today, new colors and fonts, light/dark toggle still works.
2. **Main layout**
   - Top bar (DESIGN.md §1.1) as a toolbar or a custom header widget; the theme toggle replaces the Theme menu.
   - Workspace as a horizontal `QSplitter`: spectra sidebar | center | inspector, 8 px spacing and margins.
   - Move the PressureToolbox content into the inspector cards (Pressure gauge, Parameters, Spectrometer).
3. **Docks**
   - Turn `HPTableWindow` and `PvPmPlotWindow` into `QDockWidget`s in the bottom area, side by side, with an undock button in their headers; floating docks get the compact title bar.
   - Save and restore dock layout and window geometry with `saveState()` / `restoreState()` in `QSettings`. Replace `_arrange_windows` accordingly.
   - The "P vs Pm" button that toggled the separate windows becomes unnecessary (docks can be closed/reopened from the Settings menu or a View submenu).
4. **Center panel**
   - Fitted pressure card (big value, σ, pills, Pm field + Add to log). It replaces the plot title and the "Add fit to table" / "Add to table" buttons (keep one code path).
   - Fit toolbar: Fit / Click-to-fit / Fit range (+ edit); Background as an exclusive `QButtonGroup` of checkable buttons (Auto / Manual / None); Smoothing stepper; Derivative checkbox; legend row.
5. **Density and colors**
   - File list: `QStyledItemDelegate` for one-line 30 px rows (dot, name, fitted P), tooltip with calibration and model.
   - Pressure log: 26 px rows, mono numbers, highlighted current row, header strip style.
   - Calibration-colored selectors: dynamic property on the combos (e.g. `setProperty("calib", "ruby")`) used by the QSS, re-polished (`style().unpolish(w); style().polish(w)`) on each calibration change. Same family color for dots, table, P vs Pm markers.
6. **Settings menu**
   - `QToolButton` with gear icon, `InstantPopup`, `QMenu` with the entries of DESIGN.md §4; Font size and additional PToolbox go into a Preferences dialog.
   - Icons: Lucide SVGs in `myPGM/resources/icons/ui/`, recolored to the current text color when the theme changes (replace `stroke="currentColor"` before loading into a `QIcon`, or render with `QSvgRenderer`).
7. **Polish and docs**
   - Compare light and dark against all four mockups; fix spacing, alignment, focus states, tooltips on icon-only buttons, keyboard navigation.
   - Update the README screenshot (`docs/myPGM_screenshot.png`) and CHANGELOG.

## Prompts to paste

Start (in plan mode):

> Read `docs/design/DESIGN.md`, `docs/design/IMPLEMENTATION_PLAN.md` and look at the four `docs/design/mockup_*.png`. Then read `myPGM/ui/*.py`, the two `.qss` files, `presenter.py` and `tests/test_gui.py`. Propose a detailed plan for **step 1 only**, following the ground rules. List the files you will create or change and how you will check the result visually.

Each following step:

> Step 1 is committed. Now plan and implement **step N** of `docs/design/IMPLEMENTATION_PLAN.md`, following the ground rules. When done: run the tests, render the demo window headless, compare it with the mockups, fix the differences that belong to this step, then summarize what changed and what still differs.
