import os
import sys
import subprocess
import ctypes
import json

TRACK_FILE = ".linkinfo.json"


# -------------------------
# Optional Autocomplete
# -------------------------
try:
    import readline
except ImportError:
    readline = None


def path_completer(text, state):
    if not text:
        text = "."

    dirname = os.path.dirname(text) or "."

    try:
        entries = os.listdir(dirname)
    except Exception:
        return None

    matches = []
    for entry in entries:
        full = os.path.join(dirname, entry)
        if full.lower().startswith(text.lower()):
            matches.append(full + (os.sep if os.path.isdir(full) else ""))

    return matches[state] if state < len(matches) else None


def enable_autocomplete():
    if readline:
        readline.set_completer(path_completer)
        readline.parse_and_bind("tab: complete")


# -------------------------
# Utils
# -------------------------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True)
    if result.returncode >= 8:
        print("ERROR: Command failed")
        print(cmd)
        sys.exit(1)


def ensure_exists(path, label="Path"):
    if not os.path.exists(path):
        print(f"ERROR: {label} does not exist: {path}")
        sys.exit(1)


def write_metadata(path, data):
    track_path = os.path.join(path, TRACK_FILE)

    # remove stale file if exists
    if os.path.exists(track_path):
        try:
            os.remove(track_path)
        except:
            pass

    with open(track_path, "w") as f:
        json.dump(data, f)

    # hide only if not testing
    if not os.environ.get("MOVENLINK_TEST"):
        subprocess.run(f'attrib +h "{track_path}"', shell=True)


def read_metadata(path):
    file = os.path.join(path, TRACK_FILE)
    if not os.path.exists(file):
        return None
    with open(file) as f:
        return json.load(f)


# -------------------------
# Move
# -------------------------
def move_app(source, destination):
    if not is_admin():
        print("ERROR: Run as Administrator")
        sys.exit(1)

    ensure_exists(source, "Source")

    source = os.path.abspath(source)
    destination = os.path.abspath(destination)

    folder = os.path.basename(source.rstrip("\\/"))
    final_dest = os.path.join(destination, folder)

    print("\nMoving:")
    print(f"  FROM: {source}")
    print(f"  TO:   {final_dest}")

    if os.path.exists(final_dest):
        print("ERROR: Destination already contains this folder")
        sys.exit(1)

    os.makedirs(destination, exist_ok=True)

    # copy excluding metadata
    run_cmd(f'robocopy "{source}" "{final_dest}" /E /XF {TRACK_FILE}')

    if not os.path.exists(final_dest):
        print("ERROR: Copy failed")
        sys.exit(1)

    # remove original
    run_cmd(f'rmdir /S /Q "{source}"')

    print("Creating symbolic link...")
    run_cmd(f'mklink /D "{source}" "{final_dest}"')

    # write metadata
    write_metadata(final_dest, {
        "original_path": source
    })

    print("Done.\n")


# -------------------------
# Reverse
# -------------------------
def reverse_app(target_path, final=None):
    if not is_admin():
        print("ERROR: Run as Administrator")
        sys.exit(1)

    target_path = os.path.abspath(target_path)
    ensure_exists(target_path, "Target")

    metadata = read_metadata(target_path)

    if metadata is None and final is None:
        print("ERROR: Not a managed folder. Provide original path manually.")
        sys.exit(1)

    original_path = final if final else metadata["original_path"]

    print("\nRestoring:")
    print(f"  FROM: {target_path}")
    print(f"  TO:   {original_path}")

    # remove symlink
    if os.path.exists(original_path):
        if os.path.islink(original_path):
            run_cmd(f'rmdir "{original_path}"')
        else:
            print("ERROR: Target exists and is not a symlink")
            sys.exit(1)

    # copy back excluding metadata
    run_cmd(f'robocopy "{target_path}" "{original_path}" /E /XF {TRACK_FILE}')

    # remove metadata first
    track_path = os.path.join(target_path, TRACK_FILE)
    if os.path.exists(track_path):
        try:
            os.remove(track_path)
        except:
            pass

    # remove only this folder
    if os.path.exists(target_path):
        run_cmd(f'rmdir /S /Q "{target_path}"')

    print("Done.\n")


# -------------------------
# Help / Explain
# -------------------------
def show_help():
    print("""
movenlink - Lightweight App Relocation Tool

Commands:
  movenlink move <source> <destination>
  movenlink reverse <target_path> [original_path]
  movenlink explain <command>
  movenlink help

Examples:
  movenlink move "C:\\Program Files\\App" "D:\\Apps"
  movenlink reverse "D:\\Apps\\App"

Notes:
  - Requires Administrator privileges
  - Uses symbolic links (mklink)
  - Metadata is stored per app
""")


def explain_move():
    print("""
EXPLAIN: move

1. Copies files to destination
2. Verifies copy
3. Deletes original folder
4. Creates symbolic link
5. Stores metadata

Metadata is NOT copied with files.
""")


def explain_reverse():
    print("""
EXPLAIN: reverse

1. Reads metadata
2. Removes symbolic link
3. Copies files back (excluding metadata)
4. Deletes relocated folder

Only works on managed folders.
""")


# -------------------------
# CLI
# -------------------------
def main():
    enable_autocomplete()

    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "move":
        if len(sys.argv) < 4:
            print("\nInteractive mode")
            src = input("Source path: ")
            dst = input("Destination path: ")
        else:
            src, dst = sys.argv[2], sys.argv[3]

        move_app(src, dst)

    elif cmd == "reverse":
        if len(sys.argv) < 3:
            print("\nInteractive mode")
            target = input("Target path: ")
            final = input("Original path (optional): ")
        else:
            target = sys.argv[2]
            final = sys.argv[3] if len(sys.argv) > 3 else None

        reverse_app(target, final if final else None)

    elif cmd == "help":
        show_help()

    elif cmd == "explain":
        if len(sys.argv) < 3:
            print("Usage: movenlink explain <move|reverse>")
            sys.exit(1)

        topic = sys.argv[2].lower()

        if topic == "move":
            explain_move()
        elif topic == "reverse":
            explain_reverse()
        else:
            print("Unknown topic")

    else:
        print("ERROR: Invalid command")


if __name__ == "__main__":
    main()