# movenlink

A lightweight CLI tool to move applications across drives on Windows without breaking them.

It relocates folders and replaces them with symbolic links, so apps continue working as if nothing changed.

---

## Why?

Windows applications often break when moved manually.  
movenlink solves this by using symbolic links to preserve original paths.

---

## Features

- Safe folder relocation (copy → verify → delete → link)
- Reverse operation (restore original location)
- Metadata tracking per folder
- Auto admin elevation via manifest
- PowerShell tab completion for folder paths
- Zero runtime dependencies
- Designed for low-end systems

---

## Project Structure

```
movenlink/
├── main.py                 # Core logic and CLI entry point
├── movenlink.manifest      # Admin elevation manifest (baked into exe)
├── build.bat               # Compiles main.py into movenlink.exe
├── install.bat             # Installs exe to Program Files, adds to PATH, registers tab completion
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

This compiles `main.py` into `dist\movenlink.exe` with the admin manifest baked in.  
Windows will automatically prompt for administrator access every time it runs.

### 4. Install

Right-click `install.bat` → **Run as administrator**.

This will:
- Copy `movenlink.exe` to `C:\Program Files\Movenlink\`
- Add it to the system PATH permanently
- Register PowerShell tab completion in your `$PROFILE`
- Broadcast the PATH change — no reboot needed

Verify the install by opening a new terminal:

```bash
movenlink --help
```

### Uninstall

Right-click `uninstall.bat` → **Run as administrator**.

This removes the exe, cleans it from PATH, and removes the tab completion from your PowerShell profile.

---

## Usage

### Move a folder

```bash
movenlink move "<source>" "<destination>"
```

Moves the folder to the destination and leaves a symbolic link at the original path so everything keeps working.

**Example:**

```bash
movenlink move "C:\Users\me\Games\SteamLibrary" "D:\Games"
```

After this:
- Files live at `D:\Games\SteamLibrary`
- `C:\Users\me\Games\SteamLibrary` is a symlink pointing there
- Apps using the original path continue to work normally

### Reverse a move

```bash
movenlink reverse "<target>"
```

Restores the folder back to its original location and removes the symlink.

**Example:**

```bash
movenlink reverse "D:\Games\SteamLibrary"
```

### Reverse to a custom path

If the original path is lost or you want to restore somewhere else:

```bash
movenlink reverse "<target>" "<restore_path>"
```

**Example:**

```bash
movenlink reverse "D:\Games\SteamLibrary" "C:\Users\me\Games\SteamLibrary"
```

### Help

```bash
movenlink --help
movenlink help
```

---

## Tab Completion

Tab completion works in **PowerShell** and is registered automatically during install.

```powershell
movenlink <Tab>               # completes → move, reverse, help
movenlink move C:\Us<Tab>     # completes → C:\Users\
movenlink move C:\Users\<Tab> # lists all subfolders
movenlink move "D:\My Ga<Tab> # handles paths with spaces, wraps in quotes automatically
```

> **Note:** In `cmd.exe`, folder tab completion works out of the box without any setup — just press Tab on any path argument.

---

## How It Works

```
move:
  1. Copy source folder to destination using robocopy
  2. Verify copy succeeded
  3. Write .linkinfo.json metadata to destination (stores original path)
  4. Delete original folder
  5. Create symbolic link at original path pointing to destination
  6. If symlink creation fails → automatically roll back (restore original folder)

reverse:
  1. Read .linkinfo.json from target to get original path
  2. Remove symbolic link at original path (if present)
  3. Copy files back to original path using robocopy
  4. Verify copy succeeded
  5. Delete metadata file
  6. Delete moved folder
```

---

## Error Handling

| Situation | Behavior |
|---|---|
| Source is already a symlink | Fails — prevents double move |
| Destination already has the folder | Fails with conflict error |
| Symlink creation fails after delete | Auto rollback — files restored to original path |
| Copy back fails during reverse | Aborts — files remain safe at moved location |
| Metadata file is corrupted | Clean error instead of crash |
| Broken symlink passed as source | Rejected immediately with clear error |
| Not enough arguments | Prints usage and exits cleanly |

---

## Testing

Tests live in `test_movenlink.py`. Run them from inside the venv.

### Run all tests

```bash
python test_movenlink.py
```

### List all available tests

```bash
python test_movenlink.py --list
```

### Run a specific test by index

```bash
python test_movenlink.py --test 2
```

### Show timing per test

```bash
python test_movenlink.py --include-time
```

### Combine flags

```bash
python test_movenlink.py --test 2 --include-time
```

### Adding new tests

1. Write a test function in `test_movenlink.py`:

```python
def test_your_case():
    create_files(SRC)           # set up files
    move_app(SRC, DEST)         # run the operation
    return os.path.exists(...)  # return True = PASS, False = FAIL
```

2. Register it in the `TESTS` list:

```python
TESTS = [
    ...
    ("Your Test Name", test_your_case, "One line description of what it checks"),
]
```

It will automatically appear in `--list` and run with all other tests.

### Current test coverage

| # | Test | What it checks |
|---|---|---|
| 0 | Move+Reverse | Move a folder and restore it back cleanly |
| 1 | Manual Reverse | Restore using a manually written metadata file |
| 2 | Invalid Reverse | Folder without metadata should fail safely |
| 3 | Conflict | Fail if destination already has the folder |
| 4 | Link Write | Files written through symlink appear in real folder |
| 5 | Link Delete | Files deleted through symlink disappear from real folder |
| 6 | Link Rename | Files renamed through symlink update in real folder |
| 7 | Nested Folder | Subfolders created through symlink work correctly |
| 8 | Double Move | Moving an already-symlinked folder must fail |
| 9 | Empty Folder | Move and reverse a folder with no files |
| 10 | Corrupt Metadata | Malformed metadata raises a clean error |
| 11 | Reverse No Symlink | Restore works even if symlink was already deleted |
| 12 | Same Location | Moving into own parent directory must fail |
| 13 | Metadata Written | Metadata file exists with correct path after move |
| 14 | Metadata Cleaned | Metadata and destination folder removed after reverse |

---

## Dependencies

**Runtime:** none — all modules used are Python standard library.

**Build only:**

```bash
pip install -r requirements-build.txt
```

```
# requirements-build.txt
pyinstaller
```

---

## Notes

- movenlink is **Windows only** — it relies on `mklink`, `robocopy`, and `rmdir`
- Symlink creation requires **Administrator** privileges — handled automatically via the manifest
- Do not manually delete `.linkinfo.json` from the destination folder — `reverse` needs it to know where to restore
- Files are never deleted before a successful copy is confirmed — operations are safe to interrupt

---

## License

MIT