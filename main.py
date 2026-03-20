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


def get_exe_name():
    """Returns the name of the executable or script for use in usage messages."""
    return os.path.basename(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])


def run_cmd(cmd, is_robocopy=False):
    """
    Run a shell command and raise MovenlinkError on failure.
    Robocopy uses exit codes 0-7 for success (bitmask), 8+ for failure.
    All other commands use 0 for success, non-zero for failure.
    """
    result = subprocess.run(cmd, shell=True)
    if is_robocopy:
        if result.returncode >= 8:
            raise MovenlinkError(f"Robocopy failed (code {result.returncode}): {cmd}")
    else:
        if result.returncode != 0:
            raise MovenlinkError(f"Command failed (code {result.returncode}): {cmd}")


def ensure_exists(path, label="Path"):
    """
    Check path exists. Rejects broken symlinks explicitly instead of
    letting them pass through to cause confusing downstream errors.
    """
    if os.path.islink(path) and not os.path.exists(path):
        raise MovenlinkError(f"{label} is a broken symlink: {path}")
    if not os.path.exists(path):
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
    """
    Returns metadata dict or None if file missing.
    Raises MovenlinkError on malformed JSON instead of crashing.
    """
    file = os.path.join(path, TRACK_FILE)
    if not os.path.exists(file):
        return None
    try:
        with open(file) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise MovenlinkError(f"Metadata file is corrupted: {e}")


# -------------------------
# Tab Completion
# -------------------------

# PowerShell completer script — registered into the user's PowerShell profile
# so that tab completion works for movenlink in any PowerShell session.
#
# How it works:
#   - Arg 1 (move/reverse/help) completes from the fixed command list
#   - Arg 2+ completes folder paths from the filesystem, filtered by what
#     the user has typed so far (prefix match, directories only)

POWERSHELL_COMPLETER = r"""
# movenlink tab completion for PowerShell
Register-ArgumentCompleter -Native -CommandName movenlink -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $tokens = $commandAst.CommandElements
    $count  = $tokens.Count

    # First argument: complete subcommands
    if ($count -le 2) {
        @('move', 'reverse', 'help') | Where-Object { $_ -like "$wordToComplete*" } |
            ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
        return
    }

    # Second argument onwards: complete folder paths
    $prefix = $wordToComplete -replace '"', ''

    # Resolve base directory and partial name from what user typed
    if ($prefix -eq '' -or $prefix -match '^[A-Za-z]:\\?$') {
        $baseDir  = if ($prefix -eq '') { (Get-Location).Path } else { $prefix }
        $partial  = ''
    } else {
        $baseDir  = Split-Path $prefix -Parent
        $partial  = Split-Path $prefix -Leaf
        if (-not $baseDir) { $baseDir = (Get-Location).Path }
    }

    if (-not (Test-Path $baseDir)) { return }

    Get-ChildItem -LiteralPath $baseDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "$partial*" } |
        ForEach-Object {
            $full = Join-Path $baseDir $_.Name
            # Wrap in quotes if path has spaces
            $completion = if ($full -match ' ') { '"' + $full + '"' } else { $full }
            [System.Management.Automation.CompletionResult]::new(
                $completion, $_.Name, 'ParameterValue', $full
            )
        }
}
"""


def install_completion():
    """
    Appends the PowerShell completer block to the current user's PowerShell profile.
    Skips if already installed. Called automatically by install.bat.
    """
    profile_cmd = 'powershell -NoProfile -Command "$PROFILE"'
    result = subprocess.run(profile_cmd, shell=True, capture_output=True, text=True)
    profile_path = result.stdout.strip()

    if not profile_path:
        print("Could not determine PowerShell profile path.")
        return False

    # Create profile file and parent dirs if they don't exist
    os.makedirs(os.path.dirname(profile_path), exist_ok=True)

    existing = ""
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            existing = f.read()

    # Don't add twice
    if "# movenlink tab completion" in existing:
        print("Tab completion already installed.")
        return True

    with open(profile_path, "a", encoding="utf-8") as f:
        f.write("\n" + POWERSHELL_COMPLETER)

    print(f"Tab completion installed to: {profile_path}")
    print("Restart PowerShell or run: . $PROFILE")
    return True


def uninstall_completion():
    """
    Removes the movenlink completer block from the PowerShell profile.
    Called automatically by uninstall.bat.
    """
    profile_cmd = 'powershell -NoProfile -Command "$PROFILE"'
    result = subprocess.run(profile_cmd, shell=True, capture_output=True, text=True)
    profile_path = result.stdout.strip()

    if not profile_path or not os.path.exists(profile_path):
        return

    with open(profile_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "# movenlink tab completion" not in content:
        return

    # Strip the completer block out
    lines = content.splitlines(keepends=True)
    out = []
    skip = False
    for line in lines:
        if "# movenlink tab completion" in line:
            skip = True
        if skip and line.strip() == "}":
            skip = False
            continue
        if not skip:
            out.append(line)

    with open(profile_path, "w", encoding="utf-8") as f:
        f.writelines(out)

    print("Tab completion removed from PowerShell profile.")


# -------------------------
# Core Logic
# -------------------------
def move_app(source, destination):
    if not is_admin():
        raise MovenlinkError("Run as Administrator")

    ensure_exists(source, "Source")

    source = os.path.abspath(source)
    destination = os.path.abspath(destination)

    # Prevent moving an already symlinked (already moved) folder
    if os.path.islink(source):
        raise MovenlinkError("Source is already a symlink — folder may have already been moved")

    folder = os.path.basename(source.rstrip("\\/"))
    final_dest = os.path.join(destination, folder)

    if os.path.exists(final_dest):
        raise MovenlinkError("Destination already contains this folder")

    os.makedirs(destination, exist_ok=True)

    # Copy to destination
    run_cmd(f'robocopy "{source}" "{final_dest}" /E /XF {TRACK_FILE}', is_robocopy=True)

    if not os.path.exists(final_dest):
        raise MovenlinkError("Copy failed — destination folder not found after robocopy")

    # Write metadata before touching the original, so we can recover
    write_metadata(final_dest, {"original_path": source})

    # Delete original folder
    run_cmd(f'rmdir /S /Q "{source}"')

    # Create symlink at original path
    # If mklink fails, roll back by restoring the original folder
    try:
        run_cmd(f'mklink /D "{source}" "{final_dest}"')
    except MovenlinkError:
        try:
            run_cmd(f'robocopy "{final_dest}" "{source}" /E /XF {TRACK_FILE}', is_robocopy=True)
            run_cmd(f'rmdir /S /Q "{final_dest}"')
        except MovenlinkError:
            pass  # best-effort rollback, data is still safe in final_dest
        raise MovenlinkError(
            f"Failed to create symlink at '{source}'. "
            f"Files are safe at '{final_dest}'. Run as Administrator and try again."
        )


def reverse_app(target_path, final=None):
    if not is_admin():
        raise MovenlinkError("Run as Administrator")

    target_path = os.path.abspath(target_path)
    ensure_exists(target_path, "Target")

    metadata = read_metadata(target_path)

    if metadata is None and final is None:
        raise MovenlinkError("Not a managed folder — no metadata found")

    original_path = final if final else metadata["original_path"]

    # Remove symlink at original path if it exists
    if os.path.islink(original_path):
        run_cmd(f'rmdir "{original_path}"')
    elif os.path.exists(original_path):
        raise MovenlinkError(f"Target path exists and is not a symlink: '{original_path}'")

    # Copy back first, verify, THEN delete source
    run_cmd(f'robocopy "{target_path}" "{original_path}" /E /XF {TRACK_FILE}', is_robocopy=True)

    if not os.path.exists(original_path):
        raise MovenlinkError(
            f"Copy back failed — original path not restored. "
            f"Files are still safe at '{target_path}'"
        )

    # Remove metadata file from destination
    track_path = os.path.join(target_path, TRACK_FILE)
    if os.path.exists(track_path):
        os.remove(track_path)

    # Only delete moved folder after confirming copy succeeded
    run_cmd(f'rmdir /S /Q "{target_path}"')


# -------------------------
# CLI
# -------------------------
def print_usage():
    exe = get_exe_name()
    print(f"Usage:")
    print(f"  {exe} move    <source> <destination>")
    print(f"  {exe} reverse <target> [original_path]")
    print()
    print(f"Examples:")
    print(f'  {exe} move    "C:\\Users\\me\\Games" "D:\\Games"')
    print(f'  {exe} reverse "D:\\Games\\Games"')


def main():
    try:
        if len(sys.argv) < 2:
            print_usage()
            sys.exit(0)

        cmd = sys.argv[1]

        if cmd in ("-h", "--help", "help"):
            print_usage()
            sys.exit(0)

        elif cmd == "move":
            if len(sys.argv) < 4:
                exe = get_exe_name()
                print(f"Usage: {exe} move <source> <destination>")
                sys.exit(1)
            move_app(sys.argv[2], sys.argv[3])
            print("Done")

        elif cmd == "reverse":
            if len(sys.argv) < 3:
                exe = get_exe_name()
                print(f"Usage: {exe} reverse <target> [original_path]")
                sys.exit(1)
            final = sys.argv[3] if len(sys.argv) > 3 else None
            reverse_app(sys.argv[2], final)
            print("Done")

        # Internal commands called by install.bat / uninstall.bat
        elif cmd == "__install_completion__":
            install_completion()

        elif cmd == "__uninstall_completion__":
            uninstall_completion()

        else:
            print(f"Unknown command: '{cmd}'")
            print_usage()
            sys.exit(1)

    except MovenlinkError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()