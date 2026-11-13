# myPGM UI redesign: design spec

Reference for the redesign of the myPGM main window. It goes with:

| File | What it shows |
|---|---|
| `mockup_light.png` | Main window, light theme, everything docked |
| `mockup_dark_plot_undocked.png` | Dark theme, P vs Pm plot undocked into its own window |
| `mockup_light_fit_range_editing.png` | Fit range on and in edit mode (pencil part of the split button active, draggable edges) |
| `mockup_light_settings_menu.png` | Settings menu open (gear button, top right) |
| `mockup_light_table_undocked_samarium.png` | Pressure log undocked; Sm calibration selected (selector colors follow the calibration) |
| `mockup_source.html` | HTML source of the mockup: exact sizes, paddings and colors when a PNG is ambiguous. Holes like `{{t.bg}}` are filled from the palette in its `<script>` block. |

The PNGs are rendered at 2× (1440 × 1010 logical px window).

The mockup is the target for look and layout, not for behavior: everything the app does today (fits, background, spectro calibration, sessions, autosave, column menu, sorting, error bars…) stays as it is.

## 1. Layout

One main window instead of three. From top to bottom:

1. **Top bar** (≈ 56 px, panel color, bottom border)
   - Left: app mark + "myPGM" (bold 15 px) over "Pressure Gauge Monitor · vX.Y.Z" (11 px, muted).
   - Vertical divider, then "Session" (muted) + session name (semibold) + an "Autosaved N s ago" pill.
   - Right: Open, Save, Export CSV (icon + label buttons), theme toggle (icon only), Settings (gear, icon only, opens a menu).
2. **Workspace**: three columns in a horizontal splitter
   - **Spectra sidebar** (≈ 240 px): header "SPECTRA" + "+" add button; an acquisition-folder box (folder name or "No acquisition folder", "Select…" link, full-width primary **Load latest** button); the file list; at the bottom move up / move down / delete icon buttons.
   - **Center** (takes the extra width):
     - **Fitted pressure card**: label "FITTED PRESSURE"; the value in very large mono (52 px, semibold) + "GPa" (20 px semibold) + "± σ" (16 px mono, muted); a row of pills: calibration (with its colored dot), fit model, "λ 696.224 nm · σ 0.002", file name. On the right: "Membrane pressure Pm" field (mono, "bar" suffix) and the primary **Add to log** button.
     - **Spectrum card**: one toolbar row (Fit [accent-soft, primary] · Click-to-fit · Fit range split button [see below] | Background: segmented Auto / Manual / None | Smoothing − n + | Derivative checkbox), a small legend row (Data · Fit · Fit range, χ²ᵣ on the right), then the pyqtgraph plot. The fit range is a light accent band with accent edges; the fitted peak gets a dashed vertical marker and a small label "R1 · 696.224 nm / P 5.319 ± 0.003". The plot title text is gone (the pressure is in the card above).
     - **Fit range split button** (`mockup_light_fit_range_editing.png`), two joined buttons sharing one border:
       - left part "Fit range" toggles the use of a fit range (today's `fit_range_enable_button`); on = accent border and accent text, off = neutral, and the band disappears from the plot;
       - right part, a pencil icon (32 × 32, tooltip "Edit fit range"), toggles editing (today's `fit_range_edit_button`, keep both attribute names); it is disabled while the fit range is off and turning the range off also ends editing;
       - while editing, the pencil part is solid accent with `onac` icon, the band edges get 2 px lines and grab handles (12 × 36 px accent pills with two grip lines) at mid height, and a small accent label at the top of the band shows "Drag the edges · 691.0 – 700.5 nm" with the live bounds. Keep the existing `ResizeOnlyLinearRegion` (`fit_range_selector`); only its look changes.
   - **Inspector** (≈ 300 px), three cards:
     - "PRESSURE GAUGE": Calibration selector (solid calibration color, see §3), "T correction · Datchi 2007" caption, Fit model selector (tinted calibration color).
     - "PARAMETERS" ("λ ⇄ P linked" on the right): 2 × 2 grid λ, λ₀, T, T₀ (mono inputs; the fitted one has an accent border and a small "fit" suffix), then a highlighted P (GPa) row (accent-soft background, 18 px semibold mono).
     - "SPECTROMETER": file name or "No calibration file" + "Load…" button; "Use spectrometer calibration" checkbox.
3. **Bottom dock area**: "PRESSURE LOG" (wide) and "P VS PM" side by side, each in a `QDockWidget`.
   - Each header has an undock button (arrow-out-of-box icon). Undocked, it becomes a floating window with a compact title bar (grip, title, "myPGM", dock-back button); its place in the main window shows a dashed placeholder "<Name> is open in a separate window [Dock back]" (with real `QDockWidget`s the native float/dock behavior is fine: the placeholder is optional).
   - Pressure log header: count pill ("4 points"), then Columns, Remove selected, Clear, undock.
   - P vs Pm header: legend dots per calibration, then undock.
   - The row of the current point is highlighted (`--sel`); the current point in the plot gets a ring.

Spacing: **8 px** between panels and around the window edge; 14 px inside panels; 8–12 px between controls. Panels have 12 px radius, 1 px border and, in light theme only, a soft shadow (`0 1px 2px rgba(16,24,40,.07), 0 2px 6px rgba(16,24,40,.06)`; in QSS a shadow needs `QGraphicsDropShadowEffect`; if that is costly, a slightly darker border is fine).

Section titles: 12 px, semibold, uppercase, letter-spacing 0.06em, muted color.

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

Each calibration family has one color, used everywhere the calibration appears: file-list dot, pill in the fitted-pressure card, table "Calibration" column dot, P vs Pm markers and legend, and the two selectors.

| Family | Light (solid / text on tint) | Dark (solid / text on tint) |
|---|---|---|
| Ruby | `#C42B3B` / `#9E1C2B` | `#F2697A` / `#F7A8B2` |
| Samarium (SrB₄O₇:Sm²⁺) | `#6B3FC4` / `#552FA3` | `#B79CF5` / `#CDBBF8` |
| H₂ vibron | `#985A0A` / `#7E4A07` | `#E0A458` / `#EDC28A` |
| Diamond Raman edge | `#0B6E60` / `#085A4E` | `#4CC7B4` / `#8ADBCE` |
| cBN (not in mockup) | pick a fifth hue with the same lightness, e.g. `#2F6FA8` / `#8DBDE6` | |

- **Calibration selector**: background = solid color, text = white (light) or `#12151B` (dark), semibold, custom chevron.
- **Fit model selector**: background = solid color at 10 % (light) / 16 % (dark), 1 px border at 45 % / 55 %, text = "text on tint" color, semibold.
- Today `HPCalibration.color` holds one named color per calibration (`firebrick`, `crimson`…). Either replace it by a family key mapped to the table above, or keep per-calibration shades but make sure each has a light and a dark variant with ≥ 4.5:1 contrast for the selector text.

## 4. Settings menu (gear button)

A drop-down menu under the gear button, 280 px wide:

- SETTINGS (section label)
- Preferences… (⌘ ,)
- Default calibration & fit model… (new feature: optional, can come later)
- Spectrometer calibration… (same action as "Load…" in the inspector)
- Table columns… (same choices as the existing right-click menu on the table headers)
- ───
- Autosave every 30 s (checkable)
- Debug logging (checkable)
- Open log folder
- ───
- Report an issue
- About myPGM (version on the right)

The existing menu-bar entries move here or into the top bar: Theme → theme toggle button; "Font size" and "Toggle additional PToolbox" → Preferences…; Files → Open / Save in the top bar (keep the keyboard shortcuts and "Save session as…"). On macOS the native menu bar can keep mirroring these actions.

## 5. Density

- File list: one line per file, 30 px rows: dot · name (ellipsized) · fitted P (mono, muted; accent when selected) or "—". The calibration and model go in the tooltip. Selected row: `acs` background + 1 px `ac` border, semibold name.
- Pressure log: ≈ 26 px rows, 12.5 px text, mono numbers right-aligned; header row on `hd`, 10.5 px uppercase muted.

## 6. pyqtgraph

- Background `sf`; axes and tick labels `mu` (tick labels in JetBrains Mono 11 px); grid `grid`, no frame.
- Data: small round points in `dot`; fit line 2 px in the calibration color; fit range band `acs` with 1 px `ac` edges.
- P vs Pm: markers 10 px in the calibration color, thin connecting line at 60 % opacity, current point ringed.
