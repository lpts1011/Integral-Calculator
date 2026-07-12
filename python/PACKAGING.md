# Packaging

## macOS `.app`

Build the local macOS desktop app from this folder:

```bash
./build_macos_app.sh
```

The generated app is:

```text
dist/Integral Calculator.app
```

If PyInstaller is missing, install it first:

```bash
python3 -m pip install --user pyinstaller
```

The app is ad-hoc signed for local macOS use. For public distribution outside
your own Mac, use an Apple Developer ID certificate and notarization.

## Windows `.exe`

PyInstaller is not a cross-compiler, so build the Windows version on a Windows
computer.

From this folder on Windows, run:

```bat
build_windows_app.bat
```

The generated executable is:

```text
dist\Integral Calculator\Integral Calculator.exe
```

Keep the whole `dist\Integral Calculator` folder together when moving the
program to another Windows computer, because the `.exe` uses the DLLs and
Python packages beside it.

You can also build it from GitHub Actions after pushing this folder as a
repository. Run the `Build Windows EXE` workflow, then download the
`Integral-Calculator-Windows` artifact.

## Web Version

The current app is a Tkinter desktop application, so a real web version would
need a separate web interface. The math/parser/integration modules are already
split out, which means they can be reused behind a Flask/FastAPI backend or
ported into a browser frontend later.
