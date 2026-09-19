# BabyBloom — Pregnancy Care Tracker

A local-first Android app (built with Kivy/KivyMD) for tracking
medications and blood sugar during pregnancy, with a calendar for
appointments/scans and one-tap Excel/PDF export of your sugar log.

## Features

- **Calendar** — month view, add appointments/scans/reminders, see them
  at a glance (bold day = has an entry).
- **Blood sugar log** — Before/After Breakfast, Lunch, Dinner (6 slots).
  Each entry records value (mg/dL), time taken, previous meal time, and
  a fasting toggle. Add more slots later by editing `SUGAR_SLOTS` in
  `db.py` — no other code changes needed.
- **Medications** — add/edit/delete, mark taken, per-day list.
- **Export/Print** — export any date range (or everything) to a
  formatted `.xlsx` or a print-ready `.pdf` table. On Android this opens
  the system share sheet so you can send it straight to a printer app,
  email it to your OB/GYN, or save it to Drive.
- **Pastel "baby" theme** — pink/lavender/mint palette, a procedurally
  generated crescent-moon-and-footprint icon (see note below on
  swapping in real AI-generated art).
- All data stored locally in SQLite (`bloom.db`) — nothing leaves the
  device.

## Project layout

```
BabyBloomTracker/
├── main.py                  # App entry point, navigation, theme wiring
├── db.py                    # SQLite schema + queries
├── theme.py                 # Color palette (edit here to reskin)
├── requirements.txt         # Python deps for the app itself
├── buildozer.spec           # Android packaging config
├── build_apk.py             # Build + deploy script (see below)
├── screens/
│   ├── home_screen.py
│   ├── calendar_screen.py
│   ├── sugar_screen.py
│   ├── medication_screen.py
│   └── export_screen.py
├── utils/
│   └── export_utils.py      # xlsx / pdf generation
└── assets/
    ├── generate_assets.py   # Procedurally draws icon.png / presplash.png
    ├── icon.png
    └── presplash.png
```

## Run on desktop first (fastest way to iterate)

```bash
cd BabyBloomTracker
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

This is the quickest way to try UI changes — no Android build needed
for that.

## Build the .apk and install it on your Samsung M34

Everything is handled by `build_apk.py`. It:

1. Confirms you're on Linux/WSL.
2. Checks your Python version.
3. Checks/installs system packages needed by Buildozer (JDK 17, build
   toolchain, `adb`, etc.) via `apt`.
4. Checks/installs `buildozer` + `cython`.
5. Installs the app's own requirements.
6. Checks free disk space (SDK/NDK download is several GB on first run).
7. Runs `buildozer android debug` (first run also auto-downloads the
   Android SDK/NDK — this can take 20–60+ minutes and needs internet).
8. Connects to your phone over **Wi-Fi ADB** and installs the APK.

### One-time phone setup (Android 16 / One UI 8.5)

1. Developer options are already enabled for you.
2. Settings → Developer options → turn on **Wireless debugging**.
3. Tap **Wireless debugging** → **Pair device with pairing code**. Note
   the `IP:PORT` and 6-digit code shown (this pairing port is different
   from the one used to connect).
4. Make sure the phone and your WSL host's machine are on the **same
   Wi-Fi network**.

### Build + install

```bash
cd BabyBloomTracker

# first time: pair once
python3 build_apk.py --pair 192.168.1.23:37251 --pair-code 482913 \
                      --connect 192.168.1.23:5555

# subsequent runs: pairing usually stays valid, so just:
python3 build_apk.py --connect 192.168.1.23:5555
```

(The `IP:PORT` for `--connect` is shown right on the main "Wireless
debugging" screen on the phone, and can change if the phone reconnects
to Wi-Fi — check it each session if `adb connect` fails.)

Other useful flags:

```bash
python3 build_apk.py --release          # release build instead of debug
python3 build_apk.py --skip-build --connect <ip:port>   # reinstall last APK
python3 build_apk.py --no-install       # just build, don't touch a device
python3 build_apk.py -h                 # full option list
```

### If something goes wrong

- **`adb connect` fails**: re-check the phone is still showing Wireless
  debugging as "on" and re-pair (pairing codes expire after ~a minute
  or two of being generated, and the pairing port itself changes each
  time you open the pairing dialog).
- **Build fails on first run with an SDK/license error**:
  `buildozer.spec` already sets `android.accept_sdk_license = True`;
  if you still get an interactive license prompt, type `y` and re-run.
- **Very slow/large first build**: normal — the Android SDK + NDK are
  multi-GB downloads. Subsequent builds reuse `~/.buildozer` and are
  much faster.
- **Host Python is very new (3.14+)**: `build_apk.py` will warn but
  continue; python-for-android bundles its *own* Python (usually 3.11)
  into the APK, so only the host build tooling is affected. If the
  build fails with odd Cython/setuptools errors, create a Python
  3.11/3.12 venv, install `buildozer`+`cython` in it, and run
  `build_apk.py --skip-checks` from inside that venv.

## About the icon/art

`assets/generate_assets.py` procedurally draws the icon and splash
screen with PIL (a pastel crescent moon cradling a baby footprint and a
heart) — no network or image-generation model required, so it works
fully offline in this build pipeline. If you'd like true AI-generated
artwork instead:

1. Generate a 512×512 PNG with your preferred tool (Midjourney, DALL·E,
   Stable Diffusion, etc.) — try a prompt like *"cute minimal flat icon,
   pregnant mother silhouette with a heart, pastel pink and lavender,
   baby shower style, app icon, no text"*.
2. Save it as `assets/icon.png` (and a 1080×1920 version as
   `assets/presplash.png`).
3. Nothing else changes — `buildozer.spec` already points at these
   exact filenames.

## Extending the app

- **New sugar time slot** (e.g. "Bedtime"): add it to `SUGAR_SLOTS` in
  `db.py`. `sugar_screen.py` renders whatever is in that list.
- **New medication field**: add a column via a migration in
  `db.py`'s `_create_tables` (SQLite `ALTER TABLE ... ADD COLUMN`), then
  surface it in `medication_screen.py`'s dialog.
- **New screen**: create `screens/your_screen.py` following the pattern
  in the existing screens, then register it in `NAV_ITEMS` in `main.py`.
- **Reminders/notifications**: `plyer` (already a dependency) exposes
  `plyer.notification` — wire it up in `medication_screen.py` or a new
  background service if you want scheduled reminders.
