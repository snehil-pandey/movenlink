# movenlink

Move apps across drives on Windows without breaking them.

movenlink relocates folders to a new drive and leaves a symbolic link at the original path — so apps, games, and tools continue working exactly as before, with no reinstalling, no broken shortcuts, and no registry edits.

---

## Why?

When your system drive fills up, the obvious fix is moving things to another drive. But Windows applications hardcode their install paths deep in the registry, config files, and shortcuts. Move the folder manually and they break instantly.

The usual options are frustrating:
- **Reinstall to the new drive** — tedious, and you lose all your settings
- **Apps & Features → Move** — only works for a handful of Store apps
- **Symlink it yourself** — works perfectly, but the manual steps are error-prone and easy to get wrong

movenlink automates the symlink approach safely. It copies your folder to the destination, verifies the copy, removes the original, and creates a symbolic link in its place — so the app never knows it moved.

Useful for:
- DaVinci Resolve, Adobe, or other large creative tools filling up your C: drive
- Local AI models (Ollama, LM Studio) that default to C: and grow fast
- Steam libraries and game folders
- IDEs, SDKs, and dev tools
- Any folder an app expects to always find at the same path

---

## Features

- Safe move — copy → verify → delete → link, in that order
- Rollback — if anything fails mid-operation, the original is automatically restored
- Reverse — restore a folder to its original location at any time
- Metadata tracking — each moved folder remembers where it came from
- Auto admin elevation — no need to manually run as administrator
- PowerShell tab completion — registered automatically on install
- Zero runtime dependencies — single exe, no installer bloat
- Built for low-end systems with limited SSD space

## How movenlink compares

| Feature | movenlink | Steam Mover | Manual mklink |
|---|---|---|---|
| Rollback on failure | ✅ | ❌ | ❌ |
| Reverse operation | ✅ | ❌ | Manual |
| Metadata tracking | ✅ | ❌ | ❌ |
| Any folder (not just Steam) | ✅ | ❌ | ✅ |
| Single exe, no dependencies | ✅ | ❌ | ✅ |
| Auto admin elevation | ✅ | ❌ | ❌ |
| Test suite | ✅ | ❌ | ❌ |

---

## How It Works

**move:**
1. Copy source folder to destination using robocopy
2. Verify the copy succeeded
3. Write `.linkinfo.json` to destination (stores the original path)
4. Delete the original folder
5. Create a symbolic link at the original path pointing to the destination
6. If the symlink creation fails → automatically roll back and restore the original folder

**reverse:**
1. Read `.linkinfo.json` from the target folder to find the original path
2. Remove the symbolic link at the original path (if present)
3. Copy files back to the original path using robocopy
4. Verify the copy succeeded
5. Delete the metadata file
6. Delete the moved folder

Files are **never deleted before a successful copy is confirmed** — in both directions.

---

## Project Structure

```
movenlink/
├── main.py                 # Core logic and CLI entry point
├── movenlink.manifest      # Admin elevation manifest (baked into exe at build time)
├── build.bat               # Compiles main.py into movenlink.exe
├── install.bat             # Installs exe, adds to PATH, registers tab completion
├── uninstall.bat           # Removes exe, cleans PATH, removes tab completion
├── test_movenlink.py       # Test suite
├── requirements.txt        # Runtime dependencies (none)
└── requirements-build.txt  # Build dependencies (pyinstaller)
```

---

## Installation

### Prerequisites

- Windows 10 or later
- Python 3.8+
- Git

### 1. Clone the repo

```bash
git clone https://github.com/snehil-pandey/movenlink.git
cd movenlink
```

### 2. Set up environment

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements-build.txt
```

### 3. Build the exe

```bash
build.bat
```

Compiles `main.py` into `dist\movenlink.exe` with the admin manifest baked in. Windows will automatically prompt for administrator access every time it runs — no manual "run as administrator" needed.

### 4. Install

Right-click `install.bat` → **Run as administrator**

This will:
- Copy `movenlink.exe` to `C:\Program Files\Movenlink\`
- Add it to the system PATH permanently via registry
- Register PowerShell tab completion in your `$PROFILE`
- Broadcast the PATH change so new terminals pick it up immediately — no reboot needed

Verify:

```bash
movenlink --help
```

### Uninstall

Right-click `uninstall.bat` → **Run as administrator**

Removes the exe, cleans PATH, and removes the tab completion block from your PowerShell profile.

---

## Usage

### Move a folder

```bash
movenlink move "<source>" "<destination>"
```

**Example — move DaVinci Resolve to D: drive:**

```bash
movenlink move "C:\Program Files\DaVinci Resolve" "D:\Apps"
```

After this:
- Files live at `D:\Apps\DaVinci Resolve`
- `C:\Program Files\DaVinci Resolve` is a symlink pointing there
- DaVinci Resolve launches and works exactly as before

### Reverse a move

```bash
movenlink reverse "<target>"
```

**Example:**

```bash
movenlink reverse "D:\Apps\DaVinci Resolve"
```

Reads the saved metadata, copies everything back to the original path, removes the symlink, and deletes the moved folder.

### Reverse to a different path

If the original path no longer exists or you want to restore somewhere else:

```bash
movenlink reverse "<target>" "<restore_path>"
```

**Example:**

```bash
movenlink reverse "D:\Apps\DaVinci Resolve" "C:\Program Files\DaVinci Resolve"
```

### Help

```bash
movenlink --help
```

---

## Tab Completion

Registered automatically during install. Works in PowerShell.

```powershell
movenlink <Tab>                # → move, reverse, help
movenlink move C:\Us<Tab>      # → C:\Users\
movenlink move C:\Users\<Tab>  # → lists all subfolders
movenlink move "D:\My Ga<Tab>  # → handles spaces, wraps result in quotes
```

In `cmd.exe`, folder tab completion works out of the box on any argument without any setup.

---

## Error Handling

| Situation | Behavior |
|---|---|
| Source is already a symlink | Fails — prevents double move |
| Destination already has the folder | Fails with a conflict error |
| Symlink creation fails after delete | Auto rollback — original folder restored |
| Copy back fails during reverse | Aborts — files stay safe at moved location |
| Metadata file is corrupted | Clean error — no crash |
| Broken symlink passed as source | Rejected immediately with a clear message |
| Missing arguments | Prints usage and exits cleanly |

---

## Testing

Tests are in `test_movenlink.py` and run inside the venv.

```bash
# Run all tests
python test_movenlink.py

# List all tests with descriptions
python test_movenlink.py --list

# Run a single test by index
python test_movenlink.py --test 4

# Show time taken per test
python test_movenlink.py --include-time
```

### Adding a test

1. Write the function:

```python
def test_your_case():
    create_files(SRC)           # create test files
    move_app(SRC, DEST)         # run the operation
    return os.path.exists(...)  # True = PASS, False = FAIL
```

2. Register it:

```python
TESTS = [
    ...
    ("Your Test Name", test_your_case, "What this test checks"),
]
```

It will appear in `--list` and run automatically with all other tests.

### Test coverage

| # | Test | What it checks |
|---|---|---|
| 0 | Move+Reverse | Full move and restore cycle |
| 1 | Manual Reverse | Restore using a hand-written metadata file |
| 2 | Invalid Reverse | Folder with no metadata should fail cleanly |
| 3 | Conflict | Fail if destination already has the folder |
| 4 | Link Write | Files written via symlink appear in real folder |
| 5 | Link Delete | Files deleted via symlink disappear from real folder |
| 6 | Link Rename | Files renamed via symlink update in real folder |
| 7 | Nested Folder | Subfolders created via symlink work correctly |
| 8 | Double Move | Moving an already-symlinked folder must fail |
| 9 | Empty Folder | Move and reverse a folder with no files |
| 10 | Corrupt Metadata | Malformed metadata raises a clean error |
| 11 | Reverse No Symlink | Restore works even if symlink was already deleted |
| 12 | Same Location | Moving into own parent directory must fail |
| 13 | Metadata Written | Metadata exists with correct path after move |
| 14 | Metadata Cleaned | Metadata and destination removed after reverse |

---

## Dependencies

No runtime dependencies. Everything used — `os`, `sys`, `subprocess`, `ctypes`, `json` — is Python standard library.

Build only:

```bash
pip install -r requirements-build.txt  # pyinstaller
```

---

## Notes

- **Windows only** — relies on `mklink`, `robocopy`, and `rmdir`
- **Do not delete `.linkinfo.json`** from the destination folder manually — `reverse` needs it to know where to restore
- The metadata file is hidden automatically after a move (unless running in test mode)
- Operations are safe to fail — files are never in an unrecoverable state

---

## License

MIT
