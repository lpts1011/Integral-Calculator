# Packaging

The desktop application uses PySide6, Qt WebEngine, and a fully local MathLive
bundle. It does not download editor code or fonts while running.

## Offline Math Editor Assets

The repository already contains the pinned MathLive bundle. To restore or
refresh that exact bundle from its npm package, run:

```bash
./scripts/vendor_mathlive.sh
```

The vendor script verifies MathLive `0.110.0`, writes the JavaScript checksum,
copies the required fonts, and preserves the license under
`THIRD_PARTY_NOTICES`. Both desktop build scripts bundle
`math_editor/resources` into the application.

## macOS `.app`

Build the local macOS desktop app from this folder:

```bash
./build_macos_app.sh
```

The script verifies that the selected Python contains PySide6, Qt WebEngine,
and PyInstaller before it can replace an installed app. When the dependencies
are in a specific environment, select it explicitly:

```bash
PYTHON_BIN=/path/to/environment/bin/python3 ./build_macos_app.sh
```

The build output is:

```text
dist/Integral_Calculator_Python.app
```

On macOS, Desktop folders managed by a file provider can immediately attach
Finder metadata that prevents code signing. The build script therefore signs a
metadata-free staging copy, installs the verified app at:

```text
~/Applications/Integral_Calculator_Python.app
```

and creates this clickable launcher beside the Python entry point:

```text
Main/Integral_Calculator_Python.app
```

The local launcher is a symbolic link to the complete signed app in
`~/Applications`. Set `INTEGRAL_CALCULATOR_APP_PATH` before building to choose a
different stable installation path.

If PyInstaller is missing, install it first:

```bash
python3 -m pip install --user pyinstaller
```

The app is ad-hoc signed for local macOS use. For public distribution outside
your own Mac, use an Apple Developer ID certificate and notarization.

## Public macOS `.dmg`

The recommended public distribution is a Developer ID-signed and Apple-notarized
disk image. This is a formal macOS release channel outside the Mac App Store and
does not require users to bypass Gatekeeper.

Prerequisites:

- Active Apple Developer Program membership.
- A `Developer ID Application` certificate installed in the login keychain.
- Notarization credentials saved in the keychain by `notarytool`.

Save the notarization credentials once. Use an app-specific Apple ID password;
never put that password in this repository or in a build script.

```bash
xcrun notarytool store-credentials "integral-calculator-notary" \
  --apple-id "YOUR_APPLE_ID" \
  --team-id "YOUR_TEAM_ID" \
  --password "YOUR_APP_SPECIFIC_PASSWORD"
```

Then create a formal release:

```bash
APP_VERSION=6.1 \
DEVELOPER_ID_APPLICATION="Developer ID Application: YOUR NAME (TEAM_ID)" \
NOTARY_PROFILE="integral-calculator-notary" \
./build_macos_release.sh
```

The release script deliberately refuses to run without both the Developer ID
certificate and the notarization keychain profile. It performs all of these
steps before producing an artifact:

1. Builds the current PySide6 application with the requested version.
2. Signs it with Hardened Runtime and the Qt WebEngine JIT entitlements.
3. Verifies the complete application signature.
4. Creates a compressed DMG containing `Integral Calculator.app` and an
   `Applications` shortcut.
5. Signs the DMG, submits it to Apple's notary service, and waits for approval.
6. Staples and validates the notarization ticket.
7. Runs Gatekeeper assessment and prints the final SHA-256 checksum.

The finished disk image is written to `Main/release/`. The current build
environment produces an Apple-silicon `arm64` application; an Intel or
Universal 2 release requires a compatible Python and dependency build.

## Mac App Store

A Mac App Store edition is possible, but it is a separate second-stage release
target. Apple requires App Sandbox, App Store Connect metadata, review, and
App Store-managed updates. Qt WebEngine helper processes and JIT execution also
need dedicated sandbox entitlements and full regression testing. Keep the
Developer ID DMG target independent so App Store restrictions cannot change the
behavior of the direct-download edition.

## Windows `.exe`

PyInstaller is not a cross-compiler, so build the Windows version on a Windows
computer.

From this folder on Windows, run:

```bat
build_windows_app.bat
```

The generated executable is:

```text
dist\Integral_Calculator_Python\Integral_Calculator_Python.exe
```

Keep the whole `dist\Integral_Calculator_Python` folder together when moving the
program to another Windows computer, because the `.exe` uses the DLLs and
Python packages beside it.

You can also build it from GitHub Actions from the repository root. Run the `Build Windows EXE` workflow, then download the
`Integral-Calculator-Windows` artifact.

## Runtime Stack

The production entry point is the PySide6 application. Matplotlib uses QtAgg,
and every mathematical expression field is rendered by the bundled MathLive
editor through Qt WebEngine. The retired Tkinter reference implementation has
been removed. Packaging still explicitly excludes Tk so it cannot return as an
accidental runtime dependency.

## Packaged runtime verification

The arm64 application requires macOS 13 or newer. Its Info.plist version and
minimum OS are set by `macos_app.spec`. Verify the actual installed runtime,
including its numerical engine, symbolic worker, and offline editor:

```sh
~/Applications/Integral_Calculator_Python.app/Contents/MacOS/Integral_Calculator_Python \
  --self-test --self-test-output /tmp/integral-runtime-check.json
```

The same flags work with `python Integral_Calculator.py`. This test runs offscreen
and records checks in the requested JSON file; it exits with a nonzero status if
a check fails. The public v5 ZIP is ad-hoc signed and not Apple-notarized; the
Developer ID/notarization build path above requires the user's own credentials.
Windows packaging uses installed platform-compatible NumPy rather than copying
macOS native extensions.
