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
from pathlib import Path

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


def run(cmd, check=True, capture=False, sudo=False, cwd=None):
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    print(f"$ {' '.join(cmd)}")
    if capture:
        result = subprocess.run(cmd, check=check, text=True, cwd=cwd,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout)
        return result.stdout
    return subprocess.run(cmd, check=check, cwd=cwd)


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



def patch_sdl2_alooper_pollall():
    """Patch old SDL2 source for NDK r27/r28+.

    The pinned python-for-android release carries SDL2 source that still
    calls ALooper_pollAll(). Newer Android NDK headers mark that API
    obsolete/removed. SDL's upstream fix is the direct replacement with
    ALooper_pollOnce(). This keeps the p4a branch unchanged.
    """
    matches = glob.glob(os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform", "build-*",
        "**", "SDL_androidsensor.c",
    ), recursive=True)

    if not matches:
        return

    old = "ALooper_pollAll(0, NULL, &events, (void **)&source)"
    new = "ALooper_pollOnce(0, NULL, &events, (void **)&source)"

    for path in matches:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        if new in content or old not in content:
            continue

        content = content.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Patched SDL2 ALooper_pollAll -> ALooper_pollOnce in {path}")


def patch_harfbuzz_cast_warnings():
    """Suppress NDK r28 Clang cast diagnostics only in HarfBuzz hb-ft.cc."""
    matches = glob.glob(os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform", "build-*",
        "**", "SDL2_ttf", "external", "harfbuzz", "src", "hb-ft.cc",
    ), recursive=True)
    pragma = (
        "#if defined(__clang__)\n"
        "#pragma clang diagnostic push\n"
        "#pragma clang diagnostic ignored \"-Wcast-function-type-strict\"\n"
        "#endif\n"
    )
    end_pragma = (
        "\n#if defined(__clang__)\n"
        "#pragma clang diagnostic pop\n"
        "#endif\n"
    )
    for path in matches:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            if "-Wcast-function-type-strict" in content:
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(pragma + content + end_pragma)
            print(f"Patched HarfBuzz cast diagnostic in {path}")
        except OSError:
            continue


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


def ensure_p4a_checkout():
    """Ensure the exact p4a branch is cloned before Buildozer starts p4a.

    This is necessary because Buildozer may clone p4a and immediately begin
    compiling it in the same subprocess, leaving no opportunity for a builder
    post-clone source patch. The checkout is still controlled by buildozer.spec.
    """
    spec_path = os.path.join(PROJECT_DIR, "buildozer.spec")
    if not os.path.isfile(spec_path):
        return

    with open(spec_path, encoding="utf-8") as f:
        spec = f.read()

    branch_match = re.search(
        r'^\s*p4a\.branch\s*=\s*(\S+)', spec, re.MULTILINE
    )
    if not branch_match:
        return
    wanted = branch_match.group(1)

    url_match = re.search(
        r'^\s*p4a\.url\s*=\s*(\S+)', spec, re.MULTILINE
    )
    fork_match = re.search(
        r'^\s*p4a\.fork\s*=\s*(\S+)', spec, re.MULTILINE
    )

    if url_match:
        url = url_match.group(1)
    else:
        fork = fork_match.group(1) if fork_match else "kivy"
        url = f"https://github.com/{fork}/python-for-android.git"

    p4a_dir = os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform",
        "python-for-android",
    )
    if os.path.isdir(os.path.join(p4a_dir, ".git")):
        return

    os.makedirs(os.path.dirname(p4a_dir), exist_ok=True)
    banner(f"Pre-cloning python-for-android at pinned branch '{wanted}'")
    try:
        run(["git", "clone", "--branch", wanted, url, p4a_dir])
        print(f"python-for-android cloned at '{wanted}'.")
    except subprocess.CalledProcessError:
        print("WARNING: pre-clone of python-for-android failed; "
              "Buildozer will attempt its normal checkout.")

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


def patch_p4a_native_recipes():
    """Install deterministic source patches into the pinned p4a recipes."""
    p4a_root = os.path.join(
        PROJECT_DIR, ".buildozer", "android", "platform",
        "python-for-android", "pythonforandroid", "recipes",
    )

    # SDL2_ttf / HarfBuzz: use p4a's native `patches` mechanism.
    ttf_recipe_dir = os.path.join(p4a_root, "sdl2_ttf")
    ttf_recipe = os.path.join(ttf_recipe_dir, "__init__.py")

    if os.path.isfile(ttf_recipe):
        try:
            patch_dir = os.path.join(ttf_recipe_dir, "patches")
            os.makedirs(patch_dir, exist_ok=True)

            patch_name = "babybloom_harfbuzz_ndk28.patch"
            patch_path = os.path.join(patch_dir, patch_name)

            # Insert the Clang diagnostic suppression at the beginning of
            # hb-ft.cc. A zero-context hunk makes this independent of the
            # exact HarfBuzz line numbers in SDL2_ttf 2.20.2.
            patch_text = """--- a/external/harfbuzz/src/hb-ft.cc
+++ b/external/harfbuzz/src/hb-ft.cc
@@ -0,0 +1,6 @@
+/* BABYBLOOM_NDK28_HARFBUZZ_PATCH */
+#if defined(__clang__)
+#pragma clang diagnostic push
+#pragma clang diagnostic ignored "-Wcast-function-type-strict"
+#endif
+
+"""
            Path(patch_path).write_text(patch_text, encoding="utf-8")

            content = Path(ttf_recipe).read_text(encoding="utf-8")

            # Remove the old dynamically injected HarfBuzz hook, if a
            # previous failed build left it in the pinned checkout.
            cleaned = re.sub(
                r"\n    def prebuild_arch\(self, arch\):.*?"
                r"(?=\nrecipe = LibSDL2TTF\(\))",
                "\n",
                content,
                flags=re.DOTALL,
            )
            cleaned = re.sub(r"^import os\n", "", cleaned, count=1)

            # Add p4a's supported recipe-level patch declaration.
            if "patches/babybloom_harfbuzz_ndk28.patch" not in cleaned:
                target = "    dir_name = 'SDL2_ttf'\n"
                if target not in cleaned:
                    raise RuntimeError("Unexpected sdl2_ttf recipe layout")
                cleaned = cleaned.replace(
                    target,
                    target
                    + "    patches = ['patches/babybloom_harfbuzz_ndk28.patch']\n",
                    1,
                )

            Path(ttf_recipe).write_text(cleaned, encoding="utf-8")
            print("Patched/verified p4a SDL2_ttf HarfBuzz recipe:", ttf_recipe)
            print("Installed HarfBuzz patch:", patch_path)

            # If p4a has already built SDL2_ttf, its .patched marker can
            # cause the new recipe patch to be skipped. Remove only the
            # cached SDL2_ttf build directories; SDK/NDK downloads remain.
            cached_ttf = glob.glob(os.path.join(
                PROJECT_DIR, ".buildozer", "android", "platform",
                "build-*", "**", "sdl2_ttf"
            ), recursive=True)
            for cached in cached_ttf:
                if os.path.isdir(cached):
                    print("Removing stale SDL2_ttf build cache:", cached)
                    shutil.rmtree(cached, ignore_errors=True)

        except OSError as e:
            print(f"WARNING: could not patch SDL2_ttf recipe: {e}")

    # SDL2 / ALooper fix remains unchanged.
    sdl_recipe = os.path.join(
        p4a_root, "sdl2", "__init__.py"
    )
    if os.path.isfile(sdl_recipe):
        try:
            content = Path(sdl_recipe).read_text(encoding="utf-8")

            if not re.search(r"^\s*import\s+os\s*$", content, re.MULTILINE):
                content = "import os\n" + content

            if "BABYBLOOM_NDK28_SDL_LOOPER_PATCH" not in content:
                hook = r'''
    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        path = os.path.join(
            self.get_build_dir(arch.arch),
            "src", "sensor", "android", "SDL_androidsensor.c",
        )
        try:
            with open(path, encoding="utf-8") as f:
                source = f.read()
        except OSError:
            return
        old = "ALooper_pollAll(0, NULL, &events, (void **)&source)"
        new = "ALooper_pollOnce(0, NULL, &events, (void **)&source)"
        if old not in source or new in source:
            return
        source = source.replace(old, new)
        marker = "/* BABYBLOOM_NDK28_SDL_LOOPER_PATCH */\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(marker + source)

'''
                target = "\nrecipe = LibSDL2Recipe()"
                if target not in content:
                    raise RuntimeError("Unexpected sdl2 recipe layout")
                content = content.replace(target, "\n" + hook + target, 1)

            Path(sdl_recipe).write_text(content, encoding="utf-8")
            print(f"Patched/verified p4a SDL2 recipe: {sdl_recipe}")
        except OSError as e:
            print(f"WARNING: could not patch SDL2 recipe: {e}")

    # Kivy 2.3.0 / NDK r28 Clang fix: the generated cgl_gl.c contains
    # one OpenGL function-pointer assignment whose parameter qualifiers
    # are stricter under newer Clang versions. Patch the generated C
    # source immediately before Kivy's native build starts.
    kivy_recipe = os.path.join(
        p4a_root, "kivy", "__init__.py"
    )
    if os.path.isfile(kivy_recipe):
        try:
            content = Path(kivy_recipe).read_text(encoding="utf-8")

            # The generated Kivy hook uses os.walk/os.path. Ensure the
            # p4a Kivy recipe imports os before the hook is installed.
            if not re.search(r"^import os\s*$", content, flags=re.MULTILINE):
                content = "import os\n" + content

            # Remove any previous BabyBloom-generated Kivy hook.
            hook_start = content.find("\n    def prebuild_arch(self, arch):")
            hook_end = content.find("\nrecipe = KivyRecipe()")

            if hook_start != -1 and hook_end != -1:
                existing_hook = content[hook_start:hook_end]
                if "BABYBLOOM_NDK28_KIVY_CGL_GL_PATCH" in existing_hook:
                    content = content[:hook_start] + "\n" + content[hook_end:]

            hook = r'''
    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)

        build_dir = self.get_build_dir(arch.arch)
        marker = "/* BABYBLOOM_NDK28_KIVY_CGL_GL_PATCH */\n"
        pragma = (
            "/* BABYBLOOM_NDK28_KIVY_CGL_GL_PATCH */\n"
            "#if defined(__clang__)\n"
            "#pragma clang diagnostic push\n"
            "#pragma clang diagnostic ignored \"-Wincompatible-function-pointer-types\"\n"
            "#endif\n"
        )

        for root, _dirs, files in os.walk(build_dir):
            if "cgl_gl.c" not in files:
                continue

            path = os.path.join(root, "cgl_gl.c")
            try:
                with open(path, encoding="utf-8") as f:
                    source = f.read()
            except OSError:
                continue

            if marker in source:
                continue

            with open(path, "w", encoding="utf-8") as f:
                f.write(pragma + source)

            print("Patched Kivy cgl_gl.c for NDK r28:", path)

'''
            target = "\nrecipe = KivyRecipe()"
            if target not in content:
                raise RuntimeError("Unexpected Kivy recipe layout")

            content = content.replace(target, "\n" + hook + target, 1)
            Path(kivy_recipe).write_text(content, encoding="utf-8")

            try:
                compile(content, kivy_recipe, "exec")
            except SyntaxError as e:
                raise RuntimeError(
                    f"Generated Kivy recipe is invalid Python: {e}"
                ) from e

            print(f"Patched/verified p4a Kivy recipe: {kivy_recipe}")
        except OSError as e:
            print(f"WARNING: could not patch Kivy recipe: {e}")



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



def find_android_build_tool(name):
    """Locate an Android SDK build-tool executable, preferring the newest version."""
    candidates = []

    for root_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(root_var)
        if root:
            candidates.extend(glob.glob(os.path.join(root, "build-tools", "*", name)))

    # Buildozer may keep the SDK under the project directory or under the
    # user's shared ~/.buildozer directory. Check both locations.
    sdk_roots = [
        os.path.join(PROJECT_DIR, ".buildozer", "android", "platform", "android-sdk"),
        os.path.join(os.path.expanduser("~"), ".buildozer", "android", "platform", "android-sdk"),
    ]
    for sdk_root in sdk_roots:
        candidates.extend(glob.glob(os.path.join(
            sdk_root, "build-tools", "*", name
        )))

    # Remove duplicates and retain executable files.
    candidates = [p for p in dict.fromkeys(candidates) if os.path.isfile(p) and os.access(p, os.X_OK)]
    if candidates:
        candidates.sort(key=lambda p: p.split(os.sep)[-2], reverse=True)
        return candidates[0]

    return shutil.which(name)


def sign_release_apk(apk_path):
    """16 KB-align and sign an APK with the standard Android debug key.

    The AAB->APK Gradle path currently produces an unsigned release APK.
    Android will reject that APK with INSTALL_PARSE_FAILED_NO_CERTIFICATES.
    Keep signing local and deterministic by using the standard debug keystore.
    """
    banner("Signing release APK")

    zipalign = find_android_build_tool("zipalign")
    apksigner = find_android_build_tool("apksigner")
    if not zipalign:
        raise RuntimeError("zipalign was not found in the Android SDK/build-tools.")
    if not apksigner:
        raise RuntimeError("apksigner was not found in the Android SDK/build-tools.")

    android_dir = os.path.expanduser("~/.android")
    os.makedirs(android_dir, exist_ok=True)
    keystore = os.path.join(android_dir, "debug.keystore")

    if not os.path.isfile(keystore):
        keytool = shutil.which("keytool")
        if not keytool:
            java_home = os.environ.get("JAVA_HOME")
            if java_home:
                candidate = os.path.join(java_home, "bin", "keytool")
                if os.path.isfile(candidate):
                    keytool = candidate
        if not keytool:
            raise RuntimeError("keytool was not found; cannot create the debug keystore.")

        print(f"Creating Android debug keystore: {keystore}")
        run([
            keytool, "-genkeypair",
            "-keystore", keystore,
            "-storepass", "android",
            "-keypass", "android",
            "-alias", "androiddebugkey",
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-dname", "CN=Android Debug,O=Android,C=US",
        ], check=True)

    apk_path = os.path.abspath(apk_path)
    apk_dir = os.path.dirname(apk_path)
    stem = os.path.splitext(os.path.basename(apk_path))[0]
    aligned_path = os.path.join(apk_dir, stem + "-aligned.apk")

    # zipalign must happen before signing. Use -P 16 so the final APK is
    # packaged appropriately for 16 KB page-size devices.
    if os.path.exists(aligned_path):
        os.remove(aligned_path)
    run([zipalign, "-P", "16", "-f", "4", apk_path, aligned_path], check=True)

    # Sign the aligned APK. The final artifact replaces the unsigned APK.
    run([
        apksigner, "sign",
        "--ks", keystore,
        "--ks-pass", "pass:android",
        "--key-pass", "pass:android",
        "--ks-key-alias", "androiddebugkey",
        "--out", apk_path,
        aligned_path,
    ], check=True)

    if os.path.exists(aligned_path):
        os.remove(aligned_path)

    # Verify the signature before returning the APK.
    run([apksigner, "verify", "--verbose", apk_path], check=True)
    print(f"Signed APK: {apk_path}")
    return apk_path


def verify_16kb_apk_alignment(apk_path):
    """Verify the final APK is packaged for 16 KB page-size devices.

    Android recommends zipalign -P 16 for APK packaging. NDK r28c builds
    native ELF shared libraries with 16 KB alignment by default, but this
    check also scans the APK's .so files with llvm-readelf when available.
    """
    banner("Verifying 16 KB page-size alignment")
    zipalign = find_android_build_tool("zipalign")
    if zipalign:
        result = subprocess.run(
            [zipalign, "-c", "-P", "16", "-v", "4", apk_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            raise RuntimeError("APK zip alignment check failed for 16 KB page size.")
    else:
        print("WARNING: zipalign not found; skipping APK zip-alignment check.")

    ndk_root = os.path.join(PROJECT_DIR, ".buildozer", "android", "platform")
    readelf_candidates = glob.glob(
        os.path.join(ndk_root, "android-ndk-r28c", "toolchains", "llvm",
                     "prebuilt", "linux-x86_64", "bin", "llvm-readelf")
    )
    readelf = readelf_candidates[0] if readelf_candidates else shutil.which("llvm-readelf")
    if not readelf:
        print("WARNING: llvm-readelf not found; ELF LOAD alignment was not checked automatically.")
        return

    import zipfile
    failures = []
    with zipfile.ZipFile(apk_path) as zf:
        for name in zf.namelist():
            if not (name.startswith("lib/") and name.endswith(".so")):
                continue
            data = zf.read(name)
            temp_path = os.path.join(PROJECT_DIR, ".build_apk_cache", os.path.basename(name))
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "wb") as fh:
                fh.write(data)
            out = subprocess.run([readelf, "-Wl", temp_path],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, check=False).stdout
            loads = []
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 8 and parts[0] == "LOAD":
                    try:
                        loads.append(int(parts[-1], 16))
                    except ValueError:
                        pass
            if loads and any(align % 0x4000 for align in loads):
                failures.append((name, loads))
            try:
                os.remove(temp_path)
            except OSError:
                pass

    if failures:
        for name, loads in failures:
            print(f"UNALIGNED: {name} LOAD alignments={loads}")
        raise RuntimeError("One or more native libraries are not ELF 16 KB aligned.")
    print("16 KB ELF alignment check passed for packaged native libraries.")


def _ensure_16kb_clean_build_state():
    """Remove stale native build artifacts when the configured NDK changes.

    Buildozer/p4a caches recipe outputs, so merely changing the NDK version
    is not enough: old SDL2/Python/FreeType/OpenSSL .so files can otherwise
    survive into the next APK. Only the native build/output caches are
    removed; the downloaded SDK/NDK and source project remain intact.
    """
    marker = os.path.join(PROJECT_DIR, ".build_apk_cache", "ndk-version")
    current = "28c"
    previous = None
    if os.path.isfile(marker):
        try:
            previous = open(marker).read().strip()
        except OSError:
            pass
    if previous == current:
        return
    platform_dir = os.path.join(PROJECT_DIR, ".buildozer", "android", "platform")
    for name in ("build-arm64-v8a", "build_other_builds", "build-other", "dists"):
        path = os.path.join(platform_dir, name)
        if os.path.exists(path):
            print(f"Removing stale native build cache: {path}")
            shutil.rmtree(path, ignore_errors=True)
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "w") as fh:
        fh.write(current)

def build_apk(release=True, freetype_file=None):
    banner("7/7  Building the APK with Buildozer (first run downloads the "
           "Android SDK/NDK — can take a long time)")
    target = "release" if release else "debug"
    os.chdir(PROJECT_DIR)

    # Only has an effect once p4a has been cloned into .buildozer — a
    # first-ever run won't have it yet, which is fine, it gets applied
    # on the retry after p4a is cloned during that same first run.
    ensure_p4a_checkout()
    ensure_p4a_branch()
    patch_p4a_native_recipes()
    remove_broken_reportlab_recipe()
    patch_hidapi_receiver_flags()
    patch_sdl2_alooper_pollall()
    patch_harfbuzz_cast_warnings()
    _ensure_16kb_clean_build_state()

    transient_retries_left = MAX_TRANSIENT_RETRIES
    setuptools_patch_tried = False

    while True:
        ensure_p4a_checkout()
        ensure_p4a_branch()
        patch_p4a_native_recipes()
        remove_broken_reportlab_recipe()
        patch_hidapi_receiver_flags()
        patch_sdl2_alooper_pollall()
        patch_harfbuzz_cast_warnings()
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
    os.makedirs(bin_dir, exist_ok=True)

    # Some p4a/Gradle combinations finish successfully with an Android App
    # Bundle (.aab) instead of an installable APK.  Do not treat that as a
    # failed build: ask the generated Gradle project to assemble the APK.
    apks = [f for f in os.listdir(bin_dir) if f.endswith(".apk")]
    # Ignore stale APKs from earlier failed packaging/signing attempts.
    # The presence of an APK in bin/ must not prevent us from processing the
    # freshly generated AAB.
    aabs = [f for f in os.listdir(bin_dir) if f.endswith(".aab")]
    apks = [f for f in os.listdir(bin_dir) if f.endswith(".apk")]

    if aabs:
        if aabs:
            aabs.sort(key=lambda f: os.path.getmtime(os.path.join(bin_dir, f)), reverse=True)
            aab_path = os.path.join(bin_dir, aabs[0])
            print(f"Buildozer produced AAB: {aab_path}")

            dist_matches = glob.glob(os.path.join(
                PROJECT_DIR, ".buildozer", "android", "platform",
                "build-*", "dists", "*"
            ))
            dist_matches = [p for p in dist_matches if os.path.isdir(p)]
            if not dist_matches:
                print("ERROR: AAB was produced, but the generated Gradle project was not found.")
                return None

            dist_matches.sort(key=os.path.getmtime, reverse=True)
            dist_dir = dist_matches[0]
            gradlew = os.path.join(dist_dir, "gradlew")
            if not os.path.isfile(gradlew):
                print(f"ERROR: Gradle wrapper not found in {dist_dir}")
                return None

            print("AAB detected. Assembling the installable release APK from the same Gradle project...")
            print(f"Gradle project directory: {dist_dir}")
            run([gradlew, "assembleRelease"], check=True, cwd=dist_dir)

            gradle_apks = glob.glob(os.path.join(
                dist_dir, "build", "outputs", "apk", "release", "*.apk"
            ))
            if not gradle_apks:
                # Some Android Gradle Plugin versions put the APK one level
                # deeper or use a different release output directory.
                gradle_apks = glob.glob(os.path.join(
                    dist_dir, "build", "outputs", "apk", "**", "*.apk"
                ), recursive=True)

            if not gradle_apks:
                print("ERROR: Gradle assembleRelease completed but no APK was found.")
                return None

            gradle_apks.sort(key=os.path.getmtime, reverse=True)
            generated_apk = gradle_apks[0]
            apk_name = os.path.basename(generated_apk)
            # Keep the final filename stable and remove any explicit Gradle
            # "unsigned" suffix from the installable artifact.
            apk_name = re.sub(r"-unsigned(?=\.apk$)", "", apk_name)
            apk_path = os.path.join(bin_dir, apk_name)
            shutil.copy2(generated_apk, apk_path)
            print(f"Converted/generated APK: {apk_path}")

            # Gradle's release APK is unsigned in this configuration.
            # Align first, then sign, so adb can install the final artifact.
            sign_release_apk(apk_path)
            apks = [os.path.basename(apk_path)]

    # Always process the newest APK in bin/. This is important when an
    # unsigned APK from a previous run is still present: it must never be
    # returned as the final artifact.
    apks = [f for f in os.listdir(bin_dir) if f.endswith(".apk")]
    if not apks:
        print("ERROR: build finished but no APK was produced in bin/.")
        return None

    apks.sort(key=lambda f: os.path.getmtime(os.path.join(bin_dir, f)), reverse=True)
    apk_path = os.path.join(bin_dir, apks[0])

    # A final APK must always be signed. Do not depend on the filename
    # containing '-unsigned' because Gradle/p4a may emit different names.
    print(f"Signing final APK artifact: {apk_path}")
    sign_release_apk(apk_path)

    print(f"Built: {apk_path}")
    verify_16kb_apk_alignment(apk_path)
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
    parser.add_argument("--release", action="store_true", dest="release", default=True,
                         help="Build a non-debuggable release APK (default).")
    parser.add_argument("--debug", action="store_false", dest="release",
                         help="Build a debuggable APK for development/testing.")
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
