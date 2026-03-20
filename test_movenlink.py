import os
import shutil
import random
import string
import json
import importlib.util

# -------------------------
# Dynamically load main.py
# -------------------------
spec = importlib.util.spec_from_file_location("movenlink", "main.py")
movenlink = importlib.util.module_from_spec(spec)
spec.loader.exec_module(movenlink)

move_app = movenlink.move_app
reverse_app = movenlink.reverse_app
TRACK_FILE = movenlink.TRACK_FILE


# -------------------------
# Config
# -------------------------
BASE_DIR = os.path.abspath("test_env")
SRC_DIR = os.path.join(BASE_DIR, "original")
DEST_DIR = os.path.join(BASE_DIR, "destination")
MANUAL_DIR = os.path.join(BASE_DIR, "manual_dest")

TEST_RESULTS = []


# -------------------------
# Helpers
# -------------------------
def rand_text(n=20):
    return ''.join(random.choices(string.ascii_letters, k=n))


def create_files(folder, count=5):
    os.makedirs(folder, exist_ok=True)
    files = []

    for i in range(count):
        path = os.path.join(folder, f"file_{i}.txt")
        content = rand_text()

        with open(path, "w") as f:
            f.write(content)

        files.append((path, content))

    return files


def verify_files(folder, files):
    for original_path, content in files:
        filename = os.path.basename(original_path)
        new_path = os.path.join(folder, filename)

        if not os.path.exists(new_path):
            return False

        with open(new_path) as f:
            if f.read() != content:
                return False

    return True


def record(name, passed):
    TEST_RESULTS.append((name, passed))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}")


# -------------------------
# Setup / Cleanup
# -------------------------
def setup():
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    os.makedirs(BASE_DIR)


def cleanup():
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)


# -------------------------
# TEST 1: Move + Reverse
# -------------------------
def test_move_and_reverse():
    try:
        files = create_files(SRC_DIR)

        move_app(SRC_DIR, DEST_DIR)

        moved_path = os.path.join(DEST_DIR, "original")

        cond1 = os.path.exists(moved_path)
        cond2 = verify_files(moved_path, files)

        reverse_app(moved_path)

        cond3 = os.path.exists(SRC_DIR)
        cond4 = verify_files(SRC_DIR, files)

        record("Move and Reverse", cond1 and cond2 and cond3 and cond4)

    except Exception as e:
        print(e)
        record("Move and Reverse", False)


# -------------------------
# TEST 2: Manual Metadata Reverse
# -------------------------
def test_manual_metadata_reverse():
    try:
        files = create_files(SRC_DIR)

        shutil.copytree(SRC_DIR, MANUAL_DIR)
        shutil.rmtree(SRC_DIR)

        meta = {"original_path": SRC_DIR}

        with open(os.path.join(MANUAL_DIR, TRACK_FILE), "w") as f:
            json.dump(meta, f)

        reverse_app(MANUAL_DIR)

        cond1 = os.path.exists(SRC_DIR)
        cond2 = verify_files(SRC_DIR, files)

        record("Manual Metadata Reverse", cond1 and cond2)

    except Exception as e:
        print(e)
        record("Manual Metadata Reverse", False)


# -------------------------
# TEST 3: Invalid Reverse
# -------------------------
def test_invalid_reverse():
    try:
        os.makedirs(MANUAL_DIR, exist_ok=True)

        try:
            reverse_app(MANUAL_DIR)
            record("Invalid Reverse", False)
        except SystemExit:
            record("Invalid Reverse", True)

    except Exception as e:
        print(e)
        record("Invalid Reverse", False)


# -------------------------
# TEST 4: Destination Conflict
# -------------------------
def test_destination_conflict():
    try:
        create_files(SRC_DIR)
        os.makedirs(os.path.join(DEST_DIR, "original"), exist_ok=True)

        try:
            move_app(SRC_DIR, DEST_DIR)
            record("Destination Conflict", True)
        except:
            record("Destination Conflict", False)

    except Exception as e:
        print(e)
        record("Destination Conflict", False)


# -------------------------
# TEST 5: Integrity Check
# -------------------------
def test_integrity():
    try:
        files = create_files(SRC_DIR)

        move_app(SRC_DIR, DEST_DIR)

        moved_path = os.path.join(DEST_DIR, "original")

        cond = verify_files(moved_path, files)

        record("Integrity Check", cond)

    except Exception as e:
        print(e)
        record("Integrity Check", False)


# -------------------------
# RUN ALL TESTS
# -------------------------
def run_tests():
    setup()

    test_move_and_reverse()
    test_manual_metadata_reverse()
    test_invalid_reverse()
    test_destination_conflict()
    test_integrity()

    print("\n--- RESULTS ---")
    passed = sum(1 for _, r in TEST_RESULTS if r)
    total = len(TEST_RESULTS)

    for name, result in TEST_RESULTS:
        print(f"{name}: {'PASS' if result else 'FAIL'}")

    print(f"\nSummary: {passed}/{total} tests passed")

    cleanup()


if __name__ == "__main__":
    run_tests()