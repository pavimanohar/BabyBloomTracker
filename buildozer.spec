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

# api 33 (not 34): Android 14+ hard-enforces an "exported/not-exported"
# flag on every dynamically-registered BroadcastReceiver ONLY for apps
# targeting API 34+. SDL2's bundled Java HIDAPI (joystick/controller
# support, initialized automatically even though this app never uses
# it) hasn't been updated for that requirement upstream in this
# python-for-android version, and crashes immediately on launch when
# targeting 34. Targeting 33 keeps that check as a non-fatal warning
# instead — the app still installs and runs fine on Android 16 / One
# UI 8.5, since Android is backward compatible with older-targeting
# apps. (33 is already downloaded locally too, so this needs no new
# SDK platform fetch.)
android.api = 33
android.minapi = 24
android.ndk = 25b
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
