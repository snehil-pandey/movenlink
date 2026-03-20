# movenlink

A lightweight CLI tool to move applications across drives on Windows without breaking them.

It relocates folders and replaces them with symbolic links, so apps continue working as if nothing changed.

---

## Features

- Safe folder relocation (copy → verify → delete → link)
- Reverse operation (restore original location)
- Metadata tracking per folder
- Auto admin elevation via manifest
- Zero heavy dependencies
- Designed for low-end systems

---

## Why?

Windows applications often break when moved manually.  
movenlink solves this by using symbolic links to preserve original paths.

---

## Project Structure

```
movenlink/
├── main.py                 # Core logic and CLI entry point
├── movenlink.manifest      # Admin elevation manifest (baked into exe)
├── build.bat               # Compiles main.py into movenlink.exe
├── install.bat             # Installs exe to Program Files and adds to PATH
├── uninstall.bat           # Removes exe and cleans PATH
├── test_movenlink.py       # Test suite
└── requirements.txt        # Python dependencies
```

---

## Installation

### Prerequisites

- Windows 10 or later
- Python 3.8+
- Git

### Clone and set up

```bash
git clone https://github.com/snehil-pandey/movenlink.git
cd movenlink
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Build the exe

```bash
build.bat
```

This compiles `main.py` into `dist\movenlink.exe` with the admin manifest baked in.  
Windows will automatically prompt for administrator access every time it runs.

### Install to PATH

Right-click `install.bat` and select **Run as administrator**.

This will:
- Copy `movenlink.exe` to `C:\Program Files\Movenlink\`
- Add it to the system PATH permanently
- Broadcast the PATH change — no reboot needed

Open a new terminal and verify:

```bash
movenlink --help
```

### Uninstall

Right-click `uninstall.bat` and select **Run as administrator**.  
This removes the exe and cleans it from the system PATH.

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
- `C:\Users\me\Games\SteamLibrary` is now a symlink pointing there
- Apps referencing the original path continue to work

### Reverse a move

```bash
movenlink reverse "<target>"
```

Restores the folder back to its original location and removes the symlink.

**Example:**

```bash
movenlink reverse "D:\Games\SteamLibrary"
```

### Reverse with a custom path

If the original path is lost or you want to restore to a different location:

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
  1. Read .linkinfo.json from target folder to get original path
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
| Source is already a symlink | Fails with clear error — prevents double move |
| Destination already has folder | Fails with conflict error |
| symlink creation fails after delete | Auto rollback — files restored to original path |
| Copy back fails during reverse | Aborts — files remain safe at moved location |
| Metadata file is corrupted | Fails with clear error instead of crashing |
| Broken symlink passed as source | Rejected immediately with clear error |
| Not enough arguments | Prints usage and exits cleanly |

---

## Testing

Tests live in `test_movenlink.py`.

### Run all tests

```bash
python test_movenlink.py
```

### Run a specific test by index

First list all available tests:

```bash
python test_movenlink.py --list
```

Then run by index:

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

Open `test_movenlink.py` and:

1. Write a new test function following this pattern:

```python
def test_your_case():
    # set up files or folders
    create_files(SRC)

    # run move or reverse
    move_app(SRC, DEST)

    # assert what should or shouldn't exist
    return os.path.exists(...)  # return True = PASS, False = FAIL
```

2. Register it in the `TESTS` list at the bottom of the test registry section:

```python
TESTS = [
    ...
    ("Your Test Name", test_your_case, "One line description of what it checks"),
]
```

That's it. It will automatically appear in `--list` and run with all other tests.

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

## Requirements

```
pyinstaller
```

Install with:

```bash
pip install -r requirements.txt
```

`requirements.txt`:

```
pyinstaller
```

All other dependencies (`subprocess`, `ctypes`, `json`, etc.) are part of the Python standard library.

---

## Notes

- movenlink only works on **Windows** — it relies on `mklink`, `robocopy`, and `rmdir` which are Windows-only commands
- Symbolic link creation requires **Administrator** privileges — the exe handles this automatically via the manifest
- The `.linkinfo.json` metadata file is hidden in the destination folder after a move — do not delete it manually or `reverse` won't know where to restore
- If something goes wrong mid-operation, your files are never deleted before a successful copy is confirmed

---

## License

MIT