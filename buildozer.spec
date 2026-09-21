[app]
title = BabyBloom
package.name = babybloom
package.domain = org.babybloom

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0.0

# python-for-android recipe names. sqlite3 ships with python-for-android's
# python build automatically, no separate recipe needed.
requirements = python3,kivy==2.3.0,kivymd==1.2.0,openpyxl,reportlab,pillow,plyer,sqlite3

icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png

orientation = portrait
fullscreen = 0

# Exports are written to the app's own storage (user_data_dir), which
# needs no runtime permission on modern Android. These two are kept so
# a future "export to Downloads/shared storage" feature works too.
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET

# Samsung Galaxy M34 is arm64 (Exynos 1280). Building only arm64-v8a
# keeps build times down; add armeabi-v7a too if you need older devices.
android.archs = arm64-v8a

# Was briefly considered as the fix for the RECEIVER_EXPORTED crash
# (theory: Android 14+'s hard enforcement was gated on this app's own
# targetSdkVersion). Confirmed wrong: the crash persisted at 33 too, on
# this Android 16 device — the OS enforces it regardless of what we
# target here. Staying on 33 for now anyway (already built/cached, no
# functional downside) while the real fix — patch_hidapi_receiver_flags()
# in build_apk.py, which patches SDL2's own Java source directly — gets
# verified in isolation. Bump back to 34 later as a separate, unrelated
# change once that's confirmed.
android.api = 33
android.minapi = 24
android.ndk = 28c
android.accept_sdk_license = True

android.allow_backup = True
android.logcat_filters = *:S python:D

# Pins python-for-android to a release predating Python 3.12+/Cython 3.x
# requirements, keeping it compatible with the Kivy 2.3.0 / Cython
# 0.29.33 combo this project uses. IMPORTANT: buildozer only clones
# python-for-android once — if .buildozer/android/platform/python-for-android
# already exists from before this line was added, changing it here does
# NOT retroactively switch that existing checkout. build_apk.py handles
# this automatically (see ensure_p4a_branch()), but if building manually
# without it, you'd need to `rm -rf` that directory once for this to
# take effect.
p4a.branch = release-2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
