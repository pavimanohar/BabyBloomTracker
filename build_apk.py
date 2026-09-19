#!/usr/bin/env python3
"""
build_apk.py — checks requirements, builds BabyBloom.apk with Buildozer,
and installs it straight onto your Samsung Galaxy M34 from WSL.

WHY WI-FI ADB INSTEAD OF USB
WSL2 cannot see USB devices directly (no native USB passthrough), so
this script uses Android's built-in "Wireless debugging" instead — it's
supported on your M34 (Android 16 / One UI 8.5) and needs no extra
Windows-side tooling like usbipd.

ONE-TIME SETUP ON THE PHONE
  1. Settings > Developer options > enable "Wireless debugging".
  2. Tap "Wireless debugging" > "Pair device with pairing code". Note
     the IP:PORT and 6-digit code shown (this pairing port differs from
     the connect port shown on the main Wireless debugging screen).
  3. Phone and WSL host on the same Wi-Fi network.

USAGE
    python3 build_apk.py --pair 192.168.1.23:37251 --pair-code 482913 --connect 192.168.1.23:5555
    python3 build_apk.py --connect 192.168.1.23:5555
    python3 build_apk.py --skip-build --connect 192.168.1.23:5555

Run with -h for all options. Idempotent — re-run any time.
"""

import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys
import time
import re
import urllib.request

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MIN_PYTHON = (3, 9)
MAX_TESTED_PYTHON = (3, 13)

APT_PACKAGES = [
    "git", "zip", "unzip", "openjdk-17-jdk", "autoconf", "libtool",
    "pkg-config", "cmake", "libffi-dev", "libssl-dev", "build-essential",
    "zlib1g-dev", "libncurses-dev", "libncursesw5-dev", "ccache",
    "android-tools-adb", "python3-venv", "python3-pip",
]

PIP_PACKAGES = ["buildozer", "cython==0.29.33"]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def banner(text):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def run(cmd, check=True, capture=False, sudo=False):
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    print(f"$ {' '.join(cmd)}")
    if capture:
        result = subprocess.run(cmd, check=check, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout)
        return result.stdout
    return subprocess.run(cmd, check=check)


def command_exists(name):
    return shutil.which(name) is not None


def in_virtualenv():
    """True if running inside a venv/virtualenv. pip rejects a bare
    --user install in that case (site-packages there are already
    isolated and writable without it)."""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def ensure_running_in_venv():
    """Every 'externally-managed-environment' / '--user install in a
    venv' failure we've hit traces back to one thing: this script (or
    buildozer's own internal pip calls) running under a plain system
    Python instead of the project's venv — almost always because a
    fresh terminal was opened and `source venv/bin/activate` was never
    run. Eliminate that whole class of mistake: create the venv if it
    doesn't exist yet, install this project's requirements into it,
    then transparently re-exec this entire script under that venv's
    Python. After this runs once, everything downstream (including
    buildozer's own bootstrap, which we don't control) is guaranteed
    to be running in a real venv regardless of how this script itself
    was invoked or from which directory."""
    venv_dir = os.path.join(PROJECT_DIR, "venv")
    venv_python = os.path.join(venv_dir, "bin", "python3")
    venv_bin = os.path.join(venv_dir, "bin")

    if not os.path.isfile(venv_python):
        print(f"No venv found at {venv_dir} — creating one now...")
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        except subprocess.CalledProcessError:
            print("WARNING: could not create a venv automatically. Continuing "
                  "with the current Python — you may hit 'externally-managed-"
                  "environment' errors. Create one manually with:\n"
                  f"  python3 -m venv {venv_dir}\n"
                  f"  source {venv_dir}/bin/activate")
            return
        req_file = os.path.join(PROJECT_DIR, "requirements.txt")
        if os.path.isfile(req_file):
            print("Installing this project's requirements into the new venv...")
            subprocess.run([venv_python, "-m", "pip", "install", "-r", req_file])

    # sys.prefix/sys.executable correctness (checked below) only covers
    # OUR OWN process and anything using sys.executable directly. It
    # does NOT affect subprocess calls to a bare command name like
    # "buildozer" or "cython" — those resolve via the PATH environment
    # variable, completely independent of sys.prefix. `source activate`
    # normally handles this by prepending venv/bin to PATH; replicate
    # that here explicitly so every subprocess this script (and
    # anything it calls, including buildozer's own internal tool
    # lookups) launches afterward finds the venv's copies first,
    # instead of some stray leftover elsewhere on PATH.
    current_path = os.environ.get("PATH", "")
    if venv_bin not in current_path.split(os.pathsep):
        os.environ["PATH"] = venv_bin + os.pathsep + current_path
    os.environ["VIRTUAL_ENV"] = venv_dir
    os.environ.pop("PYTHONHOME", None)

    if os.path.abspath(sys.prefix) != os.path.abspath(venv_dir):
        print(f"Not running inside the project venv — relaunching under "
              f"{venv_python} ...\n")
        os.execv(venv_python, [venv_python] + sys.argv)


def pip_install(args):
    """pip install, adding --user (+ --break-system-packages for PEP 668
    "externally managed" systems) only when NOT already in a venv."""
    cmd = [sys.executable, "-m", "pip", "install"]
    if not in_virtualenv():
        cmd += ["--user", "--break-system-packages"]
    cmd += args
    run(cmd)


# --------------------------------------------------------------------------
# recipe patches — narrow, well-understood fixes only
# --------------------------------------------------------------------------

def _fetch_url_with_deadline(url, dest_path, connect_timeout=15, max_total_seconds=45):
    """Like urlretrieve, but enforces a hard wall-clock budget for the
    whole download — not just a per-socket-operation timeout. A slow
    connection that trickles a few bytes every few seconds can stay
    "alive" indefinitely under a plain timeout= parameter (each
    individual read() call resets the clock), which is exactly what let
    a stalled Savannah download hang well past the intended timeout.
    This aborts the moment total elapsed time exceeds the budget,
    regardless of whether data is still (slowly) arriving."""
    start = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=connect_timeout) as resp:
        with open(dest_path, "wb") as out:
            while True:
                if time.time() - start > max_total_seconds:
                    raise TimeoutError(
                        f"exceeded {max_total_seconds}s total download budget")
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)


def summarize_build_output(output):
    """Prints a compact summary of what buildozer's output actually
    shows happened: the full recipe build order (if it got that far),
    which requirements install via pip with no dedicated recipe, which
    recipes were confirmed already-built (skipped), which recipes
    reached their "Building" step this run, and finally the tail of
    the raw output — since whatever caused the failure is almost
    always in the last ~30 lines, wherever the regexes above don't
    catch it."""
    banner("Build summary")

    order_match = re.search(r"Recipe build order is (\[[^\]]*\])", output)
    if order_match:
        print(f"Full recipe build order: {order_match.group(1)}")

    pip_only_match = re.search(r"requirements \(([^)]*)\) were not found as recipes", output)
    if pip_only_match:
        print(f"Installed via pip directly (no dedicated recipe): {pip_only_match.group(1)}")

    already_built = sorted(set(re.findall(
        r"\[INFO\]:\s+(\S+) said it is already built, skipping", output)))
    building_started = sorted(set(re.findall(
        r"\[INFO\]:\s+Building (\S+) for \S+", output)))
    downloading = sorted(set(re.findall(
        r"\[INFO\]:\s+Downloading (\S+)\b", output)))

    if already_built:
        print(f"Confirmed already built (skipped this run): {', '.join(already_built)}")
    if building_started:
        print(f"Reached the 'Building' step this run: {', '.join(building_started)}")
    if downloading:
        print(f"Download step ran this run for: {', '.join(downloading)}")
    if not (already_built or building_started or downloading):
        print("(Build didn't get far enough this run to report per-recipe status —"
              " see the tail below for what actually happened.)")

    print("\nLast 30 lines of buildozer output (the actual failure is almost always here):")
    for line in output.splitlines()[-30:]:
        print("  " + line)
    print()


def patch_hidapi_receiver_flags():
    """Android 14+ hard-requires an explicit RECEIVER_EXPORTED /
    RECEIVER_NOT_EXPORTED flag on every dynamically-registered
    BroadcastReceiver. This is enforced by the device's own OS version
    here (confirmed: lowering this project's targetSdkVersion to 33 did
    NOT avoid the crash on this Android 16 device — the enforcement
    isn't gated on the app's target API in this case). SDL2's bundled
    HIDDeviceManager.java (part of its Android game-controller/HID
    support, which SDL2 initializes automatically even though this app
    never uses a controller) predates this requirement and crashes the
    app immediately on launch with "hid_init threw an exception".

    Patches both registerReceiver() calls (USB and Bluetooth device
    broadcasts) to add the flag, guarded by an SDK_INT check so it
    stays correct on this project's minSdk (24) too.
    """
    matches = glob.glob(os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform", "build-*",
        "**", "HIDDeviceManager.java",
    ), recursive=True)
    if not matches:
        return  # dist not generated yet this run — nothing to patch yet

    def patched(content, field_name):
        pattern = re.compile(
            r'([ \t]*)mContext\.registerReceiver\(' + field_name + r', filter\);'
        )
        def _sub(m):
            indent = m.group(1)
            return (
                f'{indent}if (android.os.Build.VERSION.SDK_INT >= 33) {{\n'
                f'{indent}    mContext.registerReceiver({field_name}, filter, '
                f'android.content.Context.RECEIVER_NOT_EXPORTED);\n'
                f'{indent}}} else {{\n'
                f'{indent}    mContext.registerReceiver({field_name}, filter);\n'
                f'{indent}}}'
            )
        return pattern.subn(_sub, content)

    for path in matches:
        with open(path) as f:
            content = f.read()
        if "RECEIVER_NOT_EXPORTED" in content:
            continue  # already patched from a previous run

        content, n1 = patched(content, "mUsbBroadcast")
        content, n2 = patched(content, "mBluetoothBroadcast")
        if n1 or n2:
            with open(path, "w") as f:
                f.write(content)
            print(f"Patched {n1 + n2} receiver registration(s) in {path}")


def remove_broken_reportlab_recipe():
    """Some python-for-android checkouts ship a reportlab recipe that
    fails to build. Deleting the recipe folder from p4a's local clone is
    a standard, supported p4a technique: any requirement with no
    matching recipe is instead installed via pip (cross-compiled for the
    target) automatically. This is safe and reversible — p4a re-clones
    fresh if you ever delete .buildozer entirely."""
    rl_recipe_dir = os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform",
        "python-for-android", "pythonforandroid", "recipes", "reportlab",
    )
    if os.path.exists(rl_recipe_dir):
        print("Removing bundled reportlab p4a recipe so pip installs it directly...")
        shutil.rmtree(rl_recipe_dir)


def ensure_p4a_branch():
    """Buildozer only clones python-for-android once. If buildozer.spec's
    p4a.branch is set (or changed) AFTER that initial clone already
    happened, it does NOT retroactively switch the existing checkout —
    the build silently keeps using whatever was originally cloned
    (often the latest/master branch, which can be far newer than
    intended, e.g. targeting a much newer CPython than the pinned
    branch would). This forces the checkout onto the exact branch/tag
    buildozer.spec specifies, every run, so the pin actually takes
    effect regardless of build history."""
    spec_path = os.path.join(PROJECT_DIR, "buildozer.spec")
    if not os.path.isfile(spec_path):
        return
    with open(spec_path) as f:
        spec_content = f.read()
    branch_match = re.search(r'^\s*p4a\.branch\s*=\s*(\S+)', spec_content, re.MULTILINE)
    if not branch_match:
        return
    wanted = branch_match.group(1)

    p4a_dir = os.path.join(PROJECT_DIR, ".buildozer", "android", "platform", "python-for-android")
    if not os.path.isdir(os.path.join(p4a_dir, ".git")):
        return  # not cloned yet — buildozer will clone at the right branch itself

    try:
        current_commit = subprocess.run(
            ["git", "-C", p4a_dir, "rev-parse", "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return

    target_commit = subprocess.run(
        ["git", "-C", p4a_dir, "rev-parse", wanted],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    ).stdout.strip()

    if target_commit and current_commit == target_commit:
        return  # already on the right commit, nothing to do

    banner(f"python-for-android checkout is not on the pinned '{wanted}' "
           f"(buildozer only clones p4a once, so a p4a.branch change "
           f"doesn't retroactively apply to an existing checkout) — "
           f"fixing this now.")
    try:
        run(["git", "-C", p4a_dir, "fetch", "--all", "--tags"])
        run(["git", "-C", p4a_dir, "checkout", "-f", wanted])
        print(f"python-for-android now checked out at '{wanted}'.")
    except subprocess.CalledProcessError:
        print(f"WARNING: could not switch python-for-android to '{wanted}' "
              f"automatically. Fix manually with:\n"
              f"  rm -rf {p4a_dir}\n"
              f"(buildozer will re-clone it fresh, at the correct branch, "
              f"on the next run).")


def precache_freetype(timeout=25, attempts=2, local_file=None):
    """FreeType's official download host (GNU Savannah) is frequently
    slow, unresponsive, or unreachable from some networks.

    Earlier version of this fix redirected the recipe's own `url =`
    line to a local file:// path — the download itself then succeeded,
    but p4a's later unpack() step looks for the file at a fixed path,
    `packages/<recipe>/<filename>`, regardless of what URL was used to
    fetch it, so that approach downloaded successfully but to the
    wrong place. Confirmed empirically: every OTHER recipe in the same
    build correctly shows "X download already cached, skipping" using
    nothing but a plain file + `.mark-<filename>` marker sitting
    directly in `packages/<recipe>/` — so that's the actual, simpler,
    already-working convention this now follows instead.
    """
    recipe_matches = glob.glob(os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform", "python-for-android",
        "pythonforandroid", "recipes", "freetype", "__init__.py",
    ))
    if not recipe_matches:
        return  # p4a not cloned yet on this run — nothing to pre-fetch yet

    with open(recipe_matches[0]) as f:
        recipe_source = f.read()

    url_match = re.search(r'url\s*=\s*["\']([^"\']+)["\']', recipe_source)
    if not url_match:
        return
    raw_url = url_match.group(1)

    # p4a recipes commonly store the URL as a template with the version
    # substituted in at use-time (e.g. ".../freetype-{version}.tar.gz").
    # Reading the raw attribute without resolving it produces a broken
    # filename/URL (literally containing "{version}").
    primary_url = raw_url
    if "{version}" in raw_url:
        version_match = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']',
                                   recipe_source, re.MULTILINE)
        if version_match:
            primary_url = raw_url.format(version=version_match.group(1))
    filename = os.path.basename(primary_url)

    # Our own stable cache, independent of anything buildozer sweeps.
    cache_dir = os.path.join(PROJECT_DIR, ".build_apk_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cached_tar = os.path.join(cache_dir, filename)

    def have_valid(path):
        return os.path.isfile(path) and os.path.getsize(path) > 500_000

    if not have_valid(cached_tar) and local_file:
        if not os.path.isfile(local_file):
            print(f"ERROR: --freetype-file path does not exist: {local_file}")
        elif os.path.getsize(local_file) <= 500_000:
            print(f"ERROR: --freetype-file looks too small to be a real tarball: {local_file}")
        else:
            banner(f"Using local FreeType file: {local_file}")
            shutil.copyfile(local_file, cached_tar)

    if not have_valid(cached_tar):
        # SourceForge first — confirmed reachable on this network. Savannah
        # (and its dedicated mirror subdomain) go last as a fallback only,
        # since they've been unreliable here.
        mirrors = []
        version_match = re.search(r"freetype-([\d.]+)\.tar\.gz", filename)
        if version_match:
            version = version_match.group(1)
            mirrors.append(f"https://downloads.sourceforge.net/freetype/{filename}")
            mirrors.append(
                f"https://sourceforge.net/projects/freetype/files/freetype2/"
                f"{version}/{filename}/download"
            )
        mirrors.append(primary_url)
        if version_match:
            mirrors.append(f"https://download-mirror.savannah.gnu.org/releases/freetype/{filename}")

        for url in mirrors:
            if have_valid(cached_tar):
                break
            for attempt in range(1, attempts + 1):
                try:
                    banner(f"Pre-fetching FreeType from {url} (attempt {attempt}/{attempts})")
                    _fetch_url_with_deadline(url, cached_tar, connect_timeout=timeout,
                                              max_total_seconds=45)
                    if have_valid(cached_tar):
                        break
                    print("  downloaded file looks too small — treating as failed")
                    if os.path.isfile(cached_tar):
                        os.remove(cached_tar)
                except Exception as e:
                    print(f"  attempt failed: {e}")
                    if os.path.isfile(cached_tar):
                        os.remove(cached_tar)

    if not have_valid(cached_tar):
        print("WARNING: could not pre-fetch FreeType from any mirror on this "
              "network. Download it manually from any network that works "
              "(e.g. https://sourceforge.net/projects/freetype/files/freetype2/), "
              "then re-run with:\n"
              f"  python3 build_apk.py --freetype-file /path/to/{filename} ...\n"
              "buildozer will otherwise attempt its own (network) download, "
              "which may hang — Ctrl+C if it does.")
        return

    # Place a plain copy (not a symlink — some tools/hash-checks don't
    # follow those reliably) directly where p4a's unpack() expects it,
    # for every arch this project targets, with the matching marker.
    for pkg_dir in glob.glob(os.path.join(
            PROJECT_DIR, ".buildozer", "android", "platform", "build-*",
            "packages", "freetype")):
        dest_tar = os.path.join(pkg_dir, filename)
        dest_mark = os.path.join(pkg_dir, f".mark-{filename}")
        if have_valid(dest_tar) and os.path.isfile(dest_mark):
            continue  # already in place from a previous run
        os.makedirs(pkg_dir, exist_ok=True)
        shutil.copyfile(cached_tar, dest_tar)
        with open(dest_mark, "w"):
            pass
        print(f"Placed FreeType tarball + marker at {pkg_dir}")


def find_hostpython3():
    """Locate buildozer's internal build-time host Python (used only to
    run setup.py for recipes needing native compilation, e.g. Pillow)."""
    matches = glob.glob(os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform", "build-*",
        "build", "other_builds", "hostpython3", "desktop", "hostpython3",
        "native-build", "python3",
    ))
    return matches[0] if matches else None


def patch_hostpython_setuptools():
    """Known python-for-android issue on Python 3.12+ hosts: the internal
    host Python it builds for running setup.py bootstraps pip via
    ensurepip, which no longer bundles setuptools on Python 3.12+. Any
    recipe that shells out to `setup.py build_ext` directly (Pillow is
    the common one) then fails with
    'ModuleNotFoundError: No module named setuptools'. Fix: install
    setuptools into that specific interpreter."""
    hostpy = find_hostpython3()
    if not hostpy or not os.path.isfile(hostpy):
        return False
    banner("Patching buildozer's internal host Python with setuptools "
           "(known python-for-android issue on Python 3.12+ hosts)")
    try:
        run([hostpy, "-m", "ensurepip", "--upgrade"])
        run([hostpy, "-m", "pip", "install", "--upgrade", "setuptools", "wheel"])
        return True
    except subprocess.CalledProcessError:
        print("WARNING: could not patch host Python automatically. Manually run:\n"
              f'  "{hostpy}" -m ensurepip --upgrade\n'
              f'  "{hostpy}" -m pip install --upgrade setuptools wheel')
        return False


# --------------------------------------------------------------------------
# requirement checks
# --------------------------------------------------------------------------

def check_environment():
    banner("1/7  Checking environment (WSL / Linux)")
    is_linux = platform.system() == "Linux"
    is_wsl = "microsoft" in platform.uname().release.lower() if is_linux else False
    print(f"System: {platform.system()}  Release: {platform.uname().release}")
    print(f"Detected WSL: {is_wsl}")
    if not is_linux:
        print("ERROR: Buildozer/python-for-android only builds on Linux (or macOS).")
        return False
    return True


def check_python_version():
    banner("2/7  Checking Python version")
    v = sys.version_info
    print(f"Running Python {v.major}.{v.minor}.{v.micro}  (in venv: {in_virtualenv()})")
    if (v.major, v.minor) < MIN_PYTHON:
        print(f"ERROR: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.")
        return False
    if (v.major, v.minor) > MAX_TESTED_PYTHON:
        print(f"WARNING: Python {v.major}.{v.minor} is newer than buildozer/"
              f"python-for-android have been validated against.")
    return True


def check_apt_packages():
    banner("3/7  Checking system (apt) packages")
    if not command_exists("apt-get"):
        print("apt-get not found — install these manually with your package manager:")
        print("  " + ", ".join(APT_PACKAGES))
        return True

    missing = []
    for pkg in APT_PACKAGES:
        result = subprocess.run(["dpkg", "-s", pkg], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            missing.append(pkg)

    if not missing:
        print("All required system packages already installed.")
        return True

    print(f"Missing packages: {', '.join(missing)}")
    try:
        run(["apt-get", "update"], sudo=True)
        run(["apt-get", "install", "-y"] + missing, sudo=True)
    except subprocess.CalledProcessError:
        print("ERROR: apt-get install failed.")
        return False
    return True


def check_java():
    banner("4/7  Checking Java (JDK 17)")
    if command_exists("javac"):
        out = subprocess.run(["javac", "-version"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True).stdout
        print(f"Found: {out.strip()}")
        return True
    print("javac not found — run: sudo apt install openjdk-17-jdk")
    return False


def check_pip_packages():
    banner("5/7  Checking Python build tools (buildozer, cython)")
    ok = True
    for pkg in PIP_PACKAGES:
        name = pkg.split("==")[0]
        result = subprocess.run([sys.executable, "-m", "pip", "show", name],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            print(f"{name}: already installed.")
            continue
        print(f"{name}: not found, installing...")
        try:
            pip_install([pkg])
        except subprocess.CalledProcessError:
            print(f"ERROR: failed to pip install {pkg}")
            ok = False

    venv_bin = os.path.join(PROJECT_DIR, "venv", "bin")
    buildozer_found = shutil.which("buildozer")
    buildozer_is_ours = (
        buildozer_found
        and os.path.commonpath([os.path.abspath(buildozer_found), venv_bin]) == venv_bin
    )
    if buildozer_is_ours:
        return ok
    if buildozer_found and not buildozer_is_ours:
        print(f"NOTE: found a 'buildozer' on PATH at {buildozer_found}, but it's "
              f"not this project's venv copy — installing our own into the venv "
              f"so it takes priority (PATH already puts {venv_bin} first).")
        try:
            pip_install(["buildozer"])
        except subprocess.CalledProcessError:
            print("ERROR: failed to pip install buildozer into the venv")
            return False
        return ok

    if in_virtualenv():
        print("NOTE: 'buildozer' isn't on PATH even though a venv is active. "
              "Confirm the venv is activated in this shell and re-run.")
        return False

    user_base = subprocess.run([sys.executable, "-m", "site", "--user-base"],
                                stdout=subprocess.PIPE, text=True).stdout.strip()
    bin_dir = os.path.join(user_base, "bin")
    print(f"NOTE: 'buildozer' isn't on PATH yet. Add to ~/.bashrc:\n"
          f'  export PATH="{bin_dir}:$PATH"\nthen open a new shell and re-run.')
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    return command_exists("buildozer")


def check_app_dependencies():
    banner("6/7  Checking the app's own Python requirements")
    req_file = os.path.join(PROJECT_DIR, "requirements.txt")
    if not os.path.isfile(req_file):
        print("requirements.txt not found — skipping.")
        return True
    try:
        pip_install(["-r", req_file])
    except subprocess.CalledProcessError:
        print("ERROR: failed installing app requirements.")
        return False
    return True


def check_disk_space(min_gb=10):
    banner("Checking free disk space (Android SDK/NDK need real room)")
    _, _, free = shutil.disk_usage(PROJECT_DIR)
    free_gb = free / (1024 ** 3)
    print(f"Free space: {free_gb:.1f} GB (recommend at least {min_gb} GB).")
    if free_gb < min_gb:
        print("WARNING: low disk space. First build may fail partway through the SDK/NDK download.")
    return True


# --------------------------------------------------------------------------
# build + deploy
# --------------------------------------------------------------------------

TRANSIENT_NETWORK_MARKERS = [
    "502", "503", "504", "bad gateway", "gateway time-out",
    "connection reset", "read timed out", "urlopen error",
    "temporary failure in name resolution", "could not resolve host",
]

MAX_TRANSIENT_RETRIES = 3
TRANSIENT_RETRY_DELAY_SEC = 20


def run_buildozer_streamed(target):
    """Runs buildozer while still printing output live (so you can watch
    progress), but also captures it so we can detect known transient
    failures and retry automatically."""
    cmd = ["buildozer", "-v", "android", target]
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
    lines = []
    for line in proc.stdout:
        print(line, end="")
        lines.append(line)
    proc.wait()
    return proc.returncode, "".join(lines)


def build_apk(release=False, freetype_file=None):
    banner("7/7  Building the APK with Buildozer (first run downloads the "
           "Android SDK/NDK — can take a long time)")
    target = "release" if release else "debug"
    os.chdir(PROJECT_DIR)

    # Only has an effect once p4a has been cloned into .buildozer — a
    # first-ever run won't have it yet, which is fine, it gets applied
    # on the retry after p4a is cloned during that same first run.
    ensure_p4a_branch()
    remove_broken_reportlab_recipe()
    patch_hidapi_receiver_flags()

    transient_retries_left = MAX_TRANSIENT_RETRIES
    setuptools_patch_tried = False

    while True:
        ensure_p4a_branch()
        remove_broken_reportlab_recipe()
        patch_hidapi_receiver_flags()
        precache_freetype(local_file=freetype_file)
        returncode, output = run_buildozer_streamed(target)
        if returncode == 0:
            break

        lower_output = output.lower()

        # Case 1: known Python 3.12+ hostpython/setuptools issue — patch
        # once and retry immediately (doesn't count against the network
        # retry budget, since it's not transient).
        if (not setuptools_patch_tried
                and "no module named 'setuptools'" in lower_output
                and find_hostpython3() is not None):
            setuptools_patch_tried = True
            if patch_hostpython_setuptools():
                print("Retrying build now that host Python has setuptools...")
                continue

        # Case 2: looks like a transient network/mirror failure (e.g. the
        # freetype download from GNU/Savannah occasionally 502s) — retry
        # a few times with a short backoff, since already-downloaded
        # files stay cached and only the failed step re-runs.
        if (transient_retries_left > 0
                and any(marker in lower_output for marker in TRANSIENT_NETWORK_MARKERS)):
            transient_retries_left -= 1
            print(f"\nDetected what looks like a transient network error. "
                  f"Retrying in {TRANSIENT_RETRY_DELAY_SEC}s "
                  f"({transient_retries_left} retries left)...")
            time.sleep(TRANSIENT_RETRY_DELAY_SEC)
            continue

        print("ERROR: buildozer build failed.")
        summarize_build_output(output)
        raise subprocess.CalledProcessError(returncode, "buildozer", output=output)

    bin_dir = os.path.join(PROJECT_DIR, "bin")
    apks = [f for f in os.listdir(bin_dir) if f.endswith(".apk")] if os.path.isdir(bin_dir) else []
    if not apks:
        print("ERROR: build finished but no .apk found in bin/.")
        return None
    apks.sort(key=lambda f: os.path.getmtime(os.path.join(bin_dir, f)), reverse=True)
    apk_path = os.path.join(bin_dir, apks[0])
    print(f"Built: {apk_path}")
    return apk_path


def adb_pair(pair_address, code):
    banner(f"Pairing with device at {pair_address}")
    run(["adb", "pair", pair_address, code])


def adb_connect(address, retries=3):
    banner(f"Connecting to device at {address}")
    for attempt in range(1, retries + 1):
        out = run(["adb", "connect", address], capture=True)
        if "connected" in out.lower() and "failed" not in out.lower():
            return True
        print(f"Attempt {attempt}/{retries} failed, retrying in 2s...")
        time.sleep(2)
    return False


def adb_install(apk_path, serial=None):
    banner(f"Installing {os.path.basename(apk_path)} on device")
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += ["install", "-r", apk_path]
    run(cmd)
    print("\nInstalled. Launch 'BabyBloom' from the app drawer on your M34.")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Check requirements, build BabyBloom.apk, and install it "
                     "on a Samsung M34 (or any Android device) over Wi-Fi ADB.",
    )
    parser.add_argument("--pair", metavar="IP:PORT")
    parser.add_argument("--pair-code", metavar="CODE")
    parser.add_argument("--connect", metavar="IP:PORT")
    parser.add_argument("--serial", metavar="SERIAL")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--freetype-file", metavar="PATH",
                         help="Path to an already-downloaded freetype tarball "
                              "(freetype-X.Y.Z.tar.gz) to use instead of "
                              "fetching it from the network. Useful if every "
                              "mirror is unreachable from this network — "
                              "download it once via any other connection "
                              "(phone hotspot, VPN, etc.) and point this at it.")
    parser.add_argument("--skip-checks", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--no-install", action="store_true")
    args = parser.parse_args()

    if not args.skip_checks:
        steps = [
            check_environment,
            check_python_version,
            check_apt_packages,
            check_java,
            check_pip_packages,
            check_app_dependencies,
            check_disk_space,
        ]
        for step in steps:
            if not step():
                print(f"\nStopping: requirement check '{step.__name__}' failed. "
                      f"Fix the issue above and re-run.")
                sys.exit(1)

    apk_path = None
    if not args.skip_build:
        apk_path = build_apk(release=args.release, freetype_file=args.freetype_file)
        if not apk_path:
            sys.exit(1)
    else:
        bin_dir = os.path.join(PROJECT_DIR, "bin")
        apks = [f for f in os.listdir(bin_dir) if f.endswith(".apk")] if os.path.isdir(bin_dir) else []
        if apks:
            apks.sort(key=lambda f: os.path.getmtime(os.path.join(bin_dir, f)), reverse=True)
            apk_path = os.path.join(bin_dir, apks[0])
            print(f"Using existing APK: {apk_path}")
        else:
            print("ERROR: --skip-build given but no APK found in bin/.")
            sys.exit(1)

    if args.no_install:
        banner(f"Done. APK is at: {apk_path}")
        return

    if not command_exists("adb"):
        print("ERROR: adb not found. `sudo apt install android-tools-adb`.")
        sys.exit(1)

    if args.pair:
        if not args.pair_code:
            print("ERROR: --pair requires --pair-code.")
            sys.exit(1)
        adb_pair(args.pair, args.pair_code)

    if args.connect:
        if not adb_connect(args.connect):
            print("ERROR: could not connect to the device. Checklist:\n"
                  "  - Phone and WSL host on the same Wi-Fi network\n"
                  "  - Wireless debugging is still toggled ON on the phone\n"
                  "  - You used the CONNECT address, not the pairing address\n"
                  "  - Re-pair with --pair / --pair-code (pairing codes expire quickly)")
            sys.exit(1)
        adb_install(apk_path, serial=args.connect)
    elif args.serial:
        adb_install(apk_path, serial=args.serial)
    else:
        print(f"No --connect/--pair/--serial given.\nAPK is ready at: {apk_path}\n"
              "Install manually later with:\n  adb connect <PHONE_IP>:<PORT>\n"
              f"  adb install -r {apk_path}")


if __name__ == "__main__":
    ensure_running_in_venv()
    main()
