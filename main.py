import os
import sys
import subprocess
import ctypes
import json

TRACK_FILE = ".linkinfo.json"


# -------------------------
# Exceptions
# -------------------------
class MovenlinkError(Exception):
    pass


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
        raise MovenlinkError(f"Command failed: {cmd}")


def ensure_exists(path, label="Path"):
    if not (os.path.exists(path) or os.path.islink(path)):
        raise MovenlinkError(f"{label} does not exist: {path}")


def write_metadata(path, data):
    track_path = os.path.join(path, TRACK_FILE)

    if os.path.exists(track_path):
        os.remove(track_path)

    with open(track_path, "w") as f:
        json.dump(data, f)

    if not os.environ.get("MOVENLINK_TEST"):
        subprocess.run(f'attrib +h "{track_path}"', shell=True)


def read_metadata(path):
    file = os.path.join(path, TRACK_FILE)
    if not os.path.exists(file):
        return None
    with open(file) as f:
        return json.load(f)


# -------------------------
# Core Logic
# -------------------------
def move_app(source, destination):
    if not is_admin():
        raise MovenlinkError("Run as Administrator")

    ensure_exists(source, "Source")

    source = os.path.abspath(source)
    destination = os.path.abspath(destination)

    folder = os.path.basename(source.rstrip("\\/"))
    final_dest = os.path.join(destination, folder)

    if os.path.exists(final_dest):
        raise MovenlinkError("Destination already contains this folder")

    os.makedirs(destination, exist_ok=True)

    # Copy
    run_cmd(f'robocopy "{source}" "{final_dest}" /E /XF {TRACK_FILE}')

    if not os.path.exists(final_dest):
        raise MovenlinkError("Copy failed")

    # Delete original folder
    run_cmd(f'rmdir /S /Q "{source}"')

    # Create symlink EXACTLY at original path
    run_cmd(f'mklink /D "{source}" "{final_dest}"')

    # Save metadata in destination
    write_metadata(final_dest, {"original_path": source})


def reverse_app(target_path, final=None):
    if not is_admin():
        raise MovenlinkError("Run as Administrator")

    target_path = os.path.abspath(target_path)
    ensure_exists(target_path, "Target")

    metadata = read_metadata(target_path)

    if metadata is None and final is None:
        raise MovenlinkError("Not a managed folder")

    original_path = final if final else metadata["original_path"]

    # Remove symlink if exists
    if os.path.exists(original_path):
        if os.path.islink(original_path):
            run_cmd(f'rmdir "{original_path}"')
        else:
            raise MovenlinkError("Target exists and is not a symlink")

    # Copy back
    run_cmd(f'robocopy "{target_path}" "{original_path}" /E /XF {TRACK_FILE}')

    # Remove metadata
    track_path = os.path.join(target_path, TRACK_FILE)
    if os.path.exists(track_path):
        os.remove(track_path)

    # Delete moved folder
    if os.path.exists(target_path):
        run_cmd(f'rmdir /S /Q "{target_path}"')


# -------------------------
# CLI
# -------------------------
def main():
    try:
        if len(sys.argv) < 2:
            print("Use: move | reverse")
            return

        cmd = sys.argv[1]

        if cmd == "move":
            move_app(sys.argv[2], sys.argv[3])
            print("Done")

        elif cmd == "reverse":
            final = sys.argv[3] if len(sys.argv) > 3 else None
            reverse_app(sys.argv[2], final)
            print("Done")

        else:
            print("Unknown command")

    except MovenlinkError as e:
        print("ERROR:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()