import os
import shutil
import time
import argparse
import random
import string

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


def record(name, ok, t=None, detailed=False):
    results.append((name, ok, t))
    if detailed:
        msg = f"{name}: {'PASS' if ok else 'FAIL'}"
        if t is not None:
            msg += f" ({t:.4f}s)"
        print(msg)


# -------------------------
# Tests
# -------------------------
def test_move_reverse(detailed, timing):
    t0 = time.time()

    data = create_files(SRC)
    move_app(SRC, DEST)

    moved = os.path.join(DEST, "original")
    ok = verify(moved, data)

    reverse_app(moved)
    ok = ok and verify(SRC, data)

    t1 = time.time()
    record("Move+Reverse", ok, t1 - t0 if timing else None, detailed)


def test_manual_reverse(detailed, timing):
    t0 = time.time()

    data = create_files(SRC)
    shutil.copytree(SRC, MANUAL)
    shutil.rmtree(SRC)

    with open(os.path.join(MANUAL, ".linkinfo.json"), "w") as f:
        f.write(f'{{"original_path": "{SRC}"}}')

    reverse_app(MANUAL)
    ok = verify(SRC, data)

    t1 = time.time()
    record("Manual Reverse", ok, t1 - t0 if timing else None, detailed)


def test_invalid_reverse(detailed, timing):
    t0 = time.time()

    os.makedirs(MANUAL, exist_ok=True)

    try:
        reverse_app(MANUAL)
        ok = False
    except MovenlinkError:
        ok = True

    t1 = time.time()
    record("Invalid Reverse", ok, t1 - t0 if timing else None, detailed)


def test_conflict(detailed, timing):
    t0 = time.time()

    create_files(SRC)
    os.makedirs(os.path.join(DEST, "original"), exist_ok=True)

    try:
        move_app(SRC, DEST)
        ok = False
    except MovenlinkError:
        ok = True

    t1 = time.time()
    record("Conflict", ok, t1 - t0 if timing else None, detailed)


# -------------------------
# Runner
# -------------------------
def run(detailed=False, timing=False):
    os.environ["MOVENLINK_TEST"] = "1"

    if os.path.exists(BASE):
        shutil.rmtree(BASE)
    os.makedirs(BASE)

    test_move_reverse(detailed, timing)
    test_manual_reverse(detailed, timing)
    test_invalid_reverse(detailed, timing)
    test_conflict(detailed, timing)

    print("\nSummary:")
    passed = sum(1 for r in results if r[1])
    total = len(results)

    for name, ok, _ in results:
        print(f"{name}: {'PASS' if ok else 'FAIL'}")

    print(f"\n{passed}/{total} passed")

    shutil.rmtree(BASE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--detailed", action="store_true")
    parser.add_argument("--include-time", action="store_true")

    args = parser.parse_args()

    run(args.detailed, args.include_time)