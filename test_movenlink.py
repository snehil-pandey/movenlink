import os
import sys
import shutil
import time
import argparse
import random
import string
import json

from main import move_app, reverse_app, MovenlinkError

BASE = "test_env"
SRC = os.path.join(BASE, "original")
DEST = os.path.join(BASE, "destination")
MANUAL = os.path.join(BASE, "manual")

results = []


# -------------------------
# Helpers
# -------------------------
def rand():
    return ''.join(random.choices(string.ascii_letters, k=10))


def create_files(path):
    os.makedirs(path, exist_ok=True)
    data = {}
    for i in range(5):
        f = os.path.join(path, f"f{i}.txt")
        content = rand()
        with open(f, "w") as file:
            file.write(content)
        data[f] = content
    return data


def verify(path, data):
    for f, content in data.items():
        name = os.path.basename(f)
        new = os.path.join(path, name)
        if not os.path.exists(new):
            return False
        if open(new).read() != content:
            return False
    return True


def get_dest_path():
    return os.path.join(DEST, os.path.basename(SRC))


# -------------------------
# Tests
# -------------------------

def test_move_reverse():
    data = create_files(SRC)

    move_app(SRC, DEST)

    moved = get_dest_path()

    # FIX: check move result before proceeding to reverse
    if not verify(moved, data):
        return False

    reverse_app(moved)
    return verify(SRC, data)


def test_manual_reverse():
    data = create_files(SRC)

    shutil.copytree(SRC, MANUAL)
    shutil.rmtree(SRC)

    with open(os.path.join(MANUAL, ".linkinfo.json"), "w") as f:
        json.dump({"original_path": SRC}, f)

    reverse_app(MANUAL)
    return verify(SRC, data)


def test_invalid_reverse():
    os.makedirs(MANUAL, exist_ok=True)
    try:
        reverse_app(MANUAL)
        return False
    except MovenlinkError:
        return True


def test_conflict():
    create_files(SRC)
    os.makedirs(get_dest_path(), exist_ok=True)

    try:
        move_app(SRC, DEST)
        return False
    except MovenlinkError:
        return True


def test_link_write():
    # FIX: create files before moving
    create_files(SRC)
    move_app(SRC, DEST)

    link_path = SRC
    real_path = get_dest_path()

    new_file = os.path.join(link_path, "new_file.txt")
    content = rand()

    with open(new_file, "w") as f:
        f.write(content)

    real_file = os.path.join(real_path, "new_file.txt")

    return os.path.exists(real_file) and open(real_file).read() == content


def test_link_delete():
    create_files(SRC)
    move_app(SRC, DEST)

    link_path = SRC
    real_path = get_dest_path()

    file_name = "f0.txt"
    os.remove(os.path.join(link_path, file_name))

    return not os.path.exists(os.path.join(real_path, file_name))


def test_link_rename():
    create_files(SRC)
    move_app(SRC, DEST)

    link_path = SRC
    real_path = get_dest_path()

    os.rename(
        os.path.join(link_path, "f1.txt"),
        os.path.join(link_path, "renamed.txt")
    )

    return os.path.exists(os.path.join(real_path, "renamed.txt"))


def test_nested_structure():
    # FIX: create files before moving
    create_files(SRC)
    move_app(SRC, DEST)

    link_path = SRC
    real_path = get_dest_path()

    nested_link = os.path.join(link_path, "subfolder")
    nested_real = os.path.join(real_path, "subfolder")

    try:
        os.makedirs(nested_link, exist_ok=True)
    except Exception:
        return False

    if not os.path.exists(nested_real):
        return False

    file_path = os.path.join(nested_link, "deep.txt")
    content = rand()

    try:
        with open(file_path, "w") as f:
            f.write(content)
    except Exception:
        return False

    real_file = os.path.join(nested_real, "deep.txt")

    return os.path.exists(real_file) and open(real_file).read() == content


# -------------------------
# Test Registry
# -------------------------
TESTS = [
    ("Move+Reverse", test_move_reverse, "Move a folder and bring it back like nothing changed"),
    ("Manual Reverse", test_manual_reverse, "Use saved info file to restore folder to original place"),
    ("Invalid Reverse", test_invalid_reverse, "Try restoring wrong folder and expect it to fail safely"),
    ("Conflict", test_conflict, "Stop if same folder already exists in destination"),
    ("Link Write", test_link_write, "Create file in shortcut folder and check it appears in real folder"),
    ("Link Delete", test_link_delete, "Delete file from shortcut and check it disappears in real folder"),
    ("Link Rename", test_link_rename, "Rename file in shortcut and check it updates in real folder"),
    ("Nested Folder", test_nested_structure, "Create folder inside shortcut and verify it works properly"),
]


# -------------------------
# Runner
# -------------------------
def run(selected=None, timing=False):
    os.environ["MOVENLINK_TEST"] = "1"

    if os.path.exists(BASE):
        shutil.rmtree(BASE)
    os.makedirs(BASE)

    selected_tests = TESTS if selected is None else [TESTS[selected]]

    results.clear()

    for name, func, desc in selected_tests:
        t0 = time.time()

        print(f"\n{'='*60}")
        print(f"  Running: {name}")
        print(f"{'='*60}")
        try:
            ok = func()
        except Exception as e:
            print(f"[DEBUG] {name} failed:", e)
            ok = False

        t = time.time() - t0
        # FIX: always store t so --detailed can show it when --include-time is set
        results.append((name, ok, t, desc))

        # FIX: use try/finally to ensure cleanup always runs
        try:
            shutil.rmtree(BASE)
            os.makedirs(BASE)
        except Exception as e:
            print(f"[DEBUG] Cleanup failed after {name}:", e)

    passed = sum(1 for r in results if r[1])
    total = len(results)

    # -------------------------
    # Output
    # -------------------------

    # Table — always shown, time column added with --include-time
    if timing:
        print("\n+----------------------+--------+-----------+")
        print("| Test                 | Result | Time      |")
        print("+----------------------+--------+-----------+")
        for name, ok, t, _ in results:
            print(f"| {name:<20} | {'PASS' if ok else 'FAIL':<6} | {t:.4f}s   |")
        print("+----------------------+--------+-----------+")
    else:
        print("\n+----------------------+--------+")
        print("| Test                 | Result |")
        print("+----------------------+--------+")
        for name, ok, t, _ in results:
            print(f"| {name:<20} | {'PASS' if ok else 'FAIL':<6} |")
        print("+----------------------+--------+")

    print(f"\n{passed}/{total} passed")

    try:
        shutil.rmtree(BASE)
    except Exception as e:
        print(f"[DEBUG] Final cleanup failed:", e)


# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Movenlink Test Suite")

    parser.add_argument("--include-time", action="store_true", help="Show how long each test took")
    parser.add_argument("--test",         type=int,            help="Run a single test by index (see --list)")
    parser.add_argument("--list",         action="store_true", help="List all available tests and exit")

    args = parser.parse_args()

    # --list: print all tests and exit
    if args.list:
        print("\nAvailable tests:\n")
        for i, (name, _, desc) in enumerate(TESTS):
            print(f"  [{i}] {name}: {desc}")
        print()
        exit(0)

    # --test: validate index
    if args.test is not None:
        if args.test < 0 or args.test >= len(TESTS):
            print(f"Invalid test index. Use --list to see available tests (0 to {len(TESTS) - 1}).")
            exit(1)

    run(
        selected=args.test,
        timing=args.include_time,
    )