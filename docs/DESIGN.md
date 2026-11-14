# myPGM interface: design spec

How the myPGM window is laid out and styled, and the rules behind it: theme tokens, calibration
colours, density, dialogs, the Settings window and the startup screen. The code cites it by
section ("DESIGN.md §3"). It started as the spec of the 2.0 redesign; the mockups it was drawn
from were removed once the app matched them (they are in the git history, up to version 2.0.0).
The app is now the reference for anything this file leaves open.

## 1. Layout

One main window instead of three. From top to bottom:

1. **Top bar** (48 px, panel color, bottom border; 24 px app icon, 34 px buttons)
   - Left: the app icon (`resources/icons/AppIcon*.png`) + "myPGM" (bold 15 px) over "Pressure Gauge Monitor · vX.Y.Z" (11 px, muted).
   - Vertical divider, then "Session" (muted) + session name (semibold) + an "Autosaved N s ago" pill.
   - Right: two panel toggles (icon only, 34 px: table icon = Pressure log, scatter icon = P vs Pm; pressed = `acs` background, `ac` border, `act` icon), a divider, then Open, Save, Export CSV (icon + label buttons), theme toggle (icon only), Settings (gear, icon only, opens the Settings window, §4).
2. **Workspace**: three columns in a horizontal splitter
   - **Spectra sidebar** (≈ 240 px): header "SPECTRA" + "+" add button; an acquisition-folder box (folder name or "No acquisition folder", "Select…" link, full-width primary **Load latest** button); the file list; at the bottom move up / move down / delete icon buttons.
   - **Center** (takes the extra width):
     - **Fitted pressure card**: label "FITTED PRESSURE"; the value in large mono (40 px, semibold) + "GPa" (16 px semibold), no uncertainty shown (see §5); a row of pills: calibration (with its colored dot), fit model, "λ 696.224 nm", file name. On the right, vertically centered in the card: "Membrane pressure Pm" field (mono, "bar" suffix) and the primary **Add fit to log** button (today's `add_fitted_button`). When no spectrum is fitted the value shows "—" and the button is disabled. The card is kept compact (≈ 110 px tall, 10 px top and bottom padding) so the spectrum gets the height.
     - **Spectrum card**: one toolbar row (Fit [accent-soft, primary] · Click-to-fit · Fit range split button [see below] | Background: segmented Auto / Manual / None | Smoothing − n +), a small legend row (Data · Fit · Fit range, then on the right χ²ᵣ, a divider and a **dI/dλ** pill toggle), then the pyqtgraph plot. The derivative toggle lives in the legend row so the toolbar fits on one line and the option stays visible: a 28 px pill with a split-plot icon, neutral when off, accent border + accent-soft background when on. On, the derivative plot appears under the spectrum in the same card (dashed separator, ~1/3 of the spectrum height, same x axis, zero line, dashed marker at the fitted peak/edge): this is today's `Derivative_button` / `deriv_widget` in the plot splitter, restyled. The fit range is a light accent band with accent edges; the fitted peak gets a dashed vertical marker and a small label "R1 · 696.224 nm / P 5.319 GPa". The plot title text is gone (the pressure is in the card above).
     - **Fit range split button**, two joined buttons sharing one border:
       - left part "Fit range" toggles the use of a fit range (today's `fit_range_enable_button`); on = accent border and accent text, off = neutral, and the band disappears from the plot;
       - right part, a pencil icon (32 × 32, tooltip "Edit fit range"), toggles editing (today's `fit_range_edit_button`, keep both attribute names); it is disabled while the fit range is off and turning the range off also ends editing;
       - while editing, the pencil part is solid accent with `onac` icon, the band edges get 2 px lines and grab handles (12 × 36 px accent pills with two grip lines) at mid height, and a small accent label at the top of the band shows "Drag the edges · 691.0 – 700.5 nm" with the live bounds. Keep the existing `ResizeOnlyLinearRegion` (`fit_range_selector`); only its look changes.
   - **Inspector** (≈ 300 px), three cards:
     - "PRESSURE GAUGE": Calibration selector (solid calibration color, see §3), "T correction · Datchi 2007" caption, Fit model selector (tinted calibration color).
     - "PARAMETERS" ("λ ⇄ P linked" on the right): 2 × 2 grid λ, λ₀, T, T₀ (mono inputs; the fitted one has an accent border and a small "fit" suffix), then a highlighted P (GPa) row (accent-soft background, 18 px semibold mono).
       Below it, a full-width secondary **Add point to log** button (accent border and text). It adds a point from the λ / T / P values alone, with no spectrum or fit (today's `PToolbox_toTable_button` → `add_current_PToolbox_to_table`). It opens a small modal: title "Add point to log", a summary line "<calibration> · λ … nm · T … K → P … GPa", a focused "Membrane pressure Pm" field prefilled with the last Pm (bar suffix), Cancel / **Add to log** (Enter confirms, Esc cancels). Same idea as today's `prompt_fit_pm`; there is no Pm field in the inspector.
     - "SPECTROMETER": file name or "No calibration file" + "Load…" button; "Use spectrometer calibration" checkbox.
3. **Bottom dock area**: "PRESSURE LOG" (wide) and "P VS PM" side by side, each in a `QDockWidget`.
   - Each header has an undock button (arrow-out-of-box icon). Undocked, it becomes a floating window with a compact title bar (grip, title, "myPGM", dock-back button); its place in the main window shows a dashed placeholder "<Name> is open in a separate window [Dock back]" (with real `QDockWidget`s the native float/dock behavior is fine: the placeholder is optional).
   - Pressure log header: count pill ("4 points"), then Columns, Remove selected, Clear, undock, close (×).
   - **Bottom area sizing (docked).** The bottom area never pushes the workspace off screen: it has its own height, set by a horizontal splitter handle between the workspace and the panels (4 px gap, row-resize cursor). Default ≈ 28 % of the window height (280 px at 1010 px), min 160 px, max 50 %; the user's height is remembered. Inside it, the docked panels share the full height: the table scrolls inside its card with a sticky header row (the newest/current row is scrolled into view when a point is added), and the P vs Pm plot stretches to the card height. Width split: log ≈ 70 %, plot ≈ 30 %, adjustable with a vertical splitter between them; if one is hidden or floating, the other takes the full width. Floating windows keep their own size and do not affect the bottom area.
   - **Optional panels**: both panels can be hidden with their top-bar toggle or the × (muted, borderless 30 px icon button, tooltip "Hide …") at the right of their header, docked or floating. The top-bar toggle shows them again where they were (docked or floating). When one is hidden the other takes the whole width; when both are hidden the bottom area disappears and the workspace takes the full height. Hiding never deletes logged points. Visibility is saved with the dock layout (`saveState()`).
   - P vs Pm header: legend dots per calibration, then undock, close (×).
   - The row of the current point is highlighted (`--sel`); the current point in the plot gets a ring.

Spacing: **4 px** between panels and around the window edge (`theme.GAP`); 14 px inside panels; 8–12 px between controls. Panels have 12 px radius, 1 px border and, in light theme only, a soft shadow (`0 1px 2px rgba(16,24,40,.07), 0 2px 6px rgba(16,24,40,.06)`; in QSS a shadow needs `QGraphicsDropShadowEffect`; if that is costly, a slightly darker border is fine).

Section titles: 12 px, semibold, uppercase, letter-spacing 0.06em, muted color.

**Window width never depends on content.** Qt widens a window to its layout's minimum width, which pushed the window off the screen (macOS: off its right edge) when a long file name or a fit appeared. Text that varies is shortened with "…" (pills, session name, hints) or cut at the edge (P vs Pm legend, full text in the tooltip); the file pill gives way first, the model and position pills stay whole. One-line bars collapse in order when narrow (`widgets.Collapser`): fit toolbar "Background"/"Smoothing" labels, then Click-to-fit and Fit range as icons; top bar app name, "Session", then Export CSV / Open / Save as icons. A fitted pressure of 10 000 GPa or more (a fit gone wrong) is shown in scientific notation. If the window still grows, it is moved back inside the screen (only for a resize to its minimum size, never for one by the user). `tests/test_resizing.py` checks this.

## 2. Theme tokens

| Token | Use | Light | Dark |
|---|---|---|---|
| `bg` | window background (between panels) | `#E8EBF0` | `#0C0F14` |
| `sf` | panels, buttons | `#FFFFFF` | `#141820` |
| `sf2` | inputs, pills, segmented background | `#EEF1F5` | `#1B2029` |
| `hd` | panel header strips, table header | `#F7F8FA` | `#171C24` |
| `bd` | borders, dividers | `#CDD3DC` | `#272D38` |
| `tx` | text | `#121519` | `#E5E8EE` |
| `mu` | secondary text, axis labels | `#545B69` | `#98A1B1` |
| `ac` | accent: primary buttons, focus, fit-range edges | `#2450D6` | `#7B97FF` |
| `acs` | accent soft (9 % / 15 % of `ac`) | `rgba(36,80,214,.09)` | `rgba(123,151,255,.15)` |
| `act` | text on `acs` | `#1D3FAE` | `#AFC0FF` |
| `onac` | text on `ac` | `#FFFFFF` | `#0C0F14` |
| `sel` | selected / current table row | `rgba(36,80,214,.07)` | `rgba(123,151,255,.11)` |
| `dot` | raw data points | `#9AA1AD` | `#5D6676` |
| `grid` | plot grid | `#E6E9EE` | `#1E232C` |

Fonts: **Inter** (UI text, 13 px base, 400/500/600/700) and **JetBrains Mono** (every number: pressures, λ, Pm, table values, axis ticks). Both are SIL OFL; ship the `.ttf` files in `myPGM/resources/fonts/` (from fonts.google.com or the projects' GitHub releases) and load them with `QFontDatabase.addApplicationFont`; fall back to the system font if loading fails.

Icons: stroke icons (Lucide style, 1.8 px stroke, 16 px in buttons, 15 px in small buttons), drawn in the current text color so they follow the theme. Lucide is ISC-licensed.

Controls: buttons 30–40 px high, 7–8 px radius; primary = `ac` background, `onac` text, semibold; secondary = `sf` background, `bd` border; icon-only buttons are square (30 or 34 px) and need a tooltip.

## 3. Calibration colors

Each calibration family has one color, used everywhere the calibration appears: file-list dot, pill in the fitted-pressure card, table "Calibration" column dot, P vs Pm markers and legend, and the calibration selector (the fit model selector is colored by kind of model, see below).

| Family | Light (solid / text on tint) | Dark (solid / text on tint) |
|---|---|---|
| Ruby | `#C42B3B` / `#9E1C2B` | `#F2697A` / `#F7A8B2` |
| Samarium (SrB₄O₇:Sm²⁺) | `#6B3FC4` / `#552FA3` | `#B79CF5` / `#CDBBF8` |
| H₂ vibron | `#985A0A` / `#7E4A07` | `#E0A458` / `#EDC28A` |
| Diamond Raman edge | `#0B6E60` / `#085A4E` | `#4CC7B4` / `#8ADBCE` |
| cBN | pick a fifth hue with the same lightness, e.g. `#2F6FA8` / `#8DBDE6` | |

- **Calibration selector**: background = solid color, text = white (light) or `#12151B` (dark), semibold, custom chevron. Its list is neutral like the fit model list (regular weight, `acs` selection), each item with a dot in its family's color, all calibrations visible without scrolling.
- **Fit model selector**: colored by the kind of model, not by the calibration (as before the redesign): Double models red, Single models green, Raman edge grey (`theme.MODEL_COLORS`, light and dark variants). Background = that color at 10 % (light) / 16 % (dark), 1 px border at 45 % / 55 %, text = its "text on tint" color, semibold; each item of the list has a dot in its kind's color.
- Today `HPCalibration.color` holds one named color per calibration (`firebrick`, `crimson`…). Either replace it by a family key mapped to the table above, or keep per-calibration shades but make sure each has a light and a dark variant with ≥ 4.5:1 contrast for the selector text.

## 3b. Dialogs and popups

All popups follow the theme; none uses the platform's message box.

- **Messages** (`dialogs.MessageDialog`: errors, fit failure, unsaved changes, clearing the log): `sf` background like the Add point dialog, a 36 px circle with a Lucide icon (errors: `circle-alert` in `err` on `bad`; questions: `circle-help` in `ac` on `info`), a title (15 px semibold), the text (wrapped at 360 px, selectable), buttons on the right with the default one primary and focused; a destructive choice (Discard) sits on the left. Esc gives the safe choice (OK / Cancel).
- **Additional pressure toolbox** window: the two cards side by side at their natural height; a taller window leaves the space below them.
- **Menus** (menu bar on Windows / Linux, log header, P vs Pm plot): `sf`, 1 px `bd` border, items with a 6 px radius and an `acs` hover. The plot's X / Y axis forms (pyqtgraph) are not capped at 200 px so the labels fit.
- **Export…** (pyqtgraph, P vs Pm plot menu): `sf` background, field labels, list heights for their few items, Export primary, no "params" heading over the options, the exported area outlined in `ac`.

## 4. Settings window (gear button)

The gear button opens a separate **Settings** window (a non-modal `QDialog`, 820 × 600, resizable, one instance). It replaces the old menu-bar entries (Theme, Font size, Toggle additional PToolbox). On macOS it is also reachable with ⌘ , and from the app menu.

Layout: header strip ("Settings · myPGM"), a left list of sections (188 px, `hd` background, selected item `acs` background + `act` text), the section content on the right (20 × 24 px padding, rows separated by 1 px `bd` lines: title 13 px medium + 12 px muted description on the left, control on the right), and a footer: "Restore defaults" (text button, left), **Cancel** and **Save** (primary). Save applies and writes the values to `QSettings`; Cancel discards.

Sections and settings:

- **General**: Theme (segmented Light / Dark / System; same state as the top-bar toggle) · Interface font size (stepper, px; replaces `FontSizeWindow`) · Additional pressure toolbox (checkbox; replaces the menu toggle).
- **Session**: Autosave (checkbox, on by default) · **Autosave every** N (number field + seconds / minutes; default 30 s; replaces the hard-coded `AUTOSAVE_INTERVAL_MS`, applied to `autosave_timer` without restarting the app; disabled when Autosave is off; minimum 5 s) · Offer to recover an unsaved session at startup (checkbox).
- **Fitting** (new, can come later): Default calibration · Default fit model · Fit automatically after "Load latest".
- **Pressure log**: visible columns as a 3-column grid of checkboxes, in the order of `PvPmTable.COLUMNS` (Pm, P, σP (fit), x, σx (fit), T, x0, T0, calibration, file), defaults from that list; the two fit uncertainties are off by default. Same state as the right-click header menu.
- **Logging**: Debug logging (checkbox, same effect as `--debug`) · Open log folder (button).
- **About**: app mark, name and version, "Source on GitHub" and "Report an issue" links.

## 4b. Startup (empty state)

What the window shows when no spectrum is loaded. Same layout as the main window, so nothing jumps when the first file arrives:

- **Center**: one card replaces the fitted pressure card and the spectrum. A large dashed drop zone (whole card accepts drops) with a small spectrum glyph in the calibration color, "Drop spectrum files here", one line on accepted files ("Text or ASC spectra…", matching the file dialog filter `*.txt *.asc`), and three buttons: **Add spectra…** (primary), Select acquisition folder…, Open session…. Under it: a hint that λ can be entered in Parameters to get a pressure without a spectrum, and an "Explore the demo session" link (same as `mypgm --demo`).
- **Spectra sidebar**: the list is replaced by a dashed "No spectra yet / Drop .asc or .txt files here" box; the folder box and Load latest stay.
- **Inspector**: fully usable (manual conversion and "Add point to log" work without a spectrum); λ starts at λ₀, so P = 0.000.
- **Pressure log**: header count "No points"; one centered row "No points yet. Fit a spectrum and use Add fit to log, or Add point to log in Parameters." P vs Pm: legend hidden, centered "Logged points appear here, P against Pm."
- **Top bar**: the autosave pill reads "Not saved yet" with a muted dot.
- **Recovery**: when a backup of an unsaved session is found, a banner under the top bar replaces today's `ask_recover_session` message box: "myPGM did not close normally last time. A backup of the unsaved session from <when> was found." with **Recover session** (primary) and Discard. It can be ignored; it disappears once the user loads anything else or clicks one of the buttons.

## 5. Density

- File list: one line per file, 30 px rows: dot · name (ellipsized) · fitted P (mono, muted; accent when selected) or "—". The calibration and model go in the tooltip. Selected row: `acs` background + 1 px `ac` border, semibold name.
- Pressure log: ≈ 26 px rows, 12.5 px text, mono numbers right-aligned; header row on `hd`, 10.5 px uppercase muted. Default columns: #, Pm (bar), P (GPa), x, calibration, file.

**Fit uncertainties.** The fit uncertainties are purely numerical and of little practical use, so they are computed and saved but not shown by default: no "± σ" next to the big pressure, in the pills, in the peak label or in the P column (P shows the value alone, today it shows "P ± σ"). They are available as optional table columns **σP (fit)** (new, split out of the P column) and **σx (fit)** (existing), both off by default, toggled from the header menu or Settings › Pressure log, and exported to CSV when shown.

## 6. pyqtgraph

- Background `sf`; axes and tick labels `mu` (tick labels in JetBrains Mono 11 px); grid `grid`, no frame.
- Data: small round points in `dot`; fit line 2 px in the calibration color; fit range band `acs` with 1 px `ac` edges.
- P vs Pm: markers 10 px in the calibration color, thin connecting line at 60 % opacity, current point ringed. Both axes titled: "Pm (bar)" and "P (GPa)".
