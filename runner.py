import os
import random
import re
import subprocess
import sys

# SAFETY NOTE:
# Runner tries multiple cookie txt files by running script.py.
# It captures stdout+stderr, detects failures like "Failed: No token found in response".
# File routing:
# - success -> moves cookie to plan-specific used folder
# - failure -> moves cookie to link/faild/ (spelling kept from user request)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(REPO_ROOT, "input.txt")
SCRIPT_FILE = os.path.join(REPO_ROOT, "script.py")

# Default cookie folder (must contain .txt files)
COOKIE_FOLDER = os.path.join(REPO_ROOT, "gg")

USED_BASE = os.path.join(REPO_ROOT, "used")  # kept for compatibility
USED_PREMIUM_FOLDER = os.path.join(REPO_ROOT, "premium used")
USED_STANDARE_FOLDER = os.path.join(REPO_ROOT, "standare used")
FAILED_FOLDER = os.path.join(REPO_ROOT, "faild")  # as requested

PACKAGE_ARG = sys.argv[1] if len(sys.argv) > 1 else "standare"

# Allow overriding cookie folder
if len(sys.argv) > 2:
    COOKIE_FOLDER = os.path.join(REPO_ROOT, sys.argv[2])

os.makedirs(USED_BASE, exist_ok=True)
os.makedirs(USED_PREMIUM_FOLDER, exist_ok=True)
os.makedirs(USED_STANDARE_FOLDER, exist_ok=True)
os.makedirs(FAILED_FOLDER, exist_ok=True)


def recycle_cookie_files():
    """Move cookie files back from used/failed folders to gg folder."""
    source_folders = [USED_PREMIUM_FOLDER, USED_STANDARE_FOLDER, FAILED_FOLDER]

    for folder in source_folders:
        if not os.path.isdir(folder):
            continue

        for fname in os.listdir(folder):
            if fname.lower().endswith('.txt'):
                src_path = os.path.join(folder, fname)
                dest_path = os.path.join(COOKIE_FOLDER, fname)

                # Handle duplicate filenames
                if os.path.exists(dest_path):
                    name, ext = os.path.splitext(fname)
                    suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=5))
                    dest_path = os.path.join(COOKIE_FOLDER, f"{name}_{suffix}{ext}")

                try:
                    os.replace(src_path, dest_path)
                except Exception:
                    pass


# Recycle cookie files before starting
recycle_cookie_files()

if not os.path.isdir(COOKIE_FOLDER):
    print(f"Cookie folder not found: {COOKIE_FOLDER}")
    sys.exit(2)

cookie_files = [
    f
    for f in os.listdir(COOKIE_FOLDER)
    if f.lower().endswith('.txt') and os.path.isfile(os.path.join(COOKIE_FOLDER, f))
]

def extract_plan_from_content(txt: str) -> str | None:
    """Extract plan from the cookie text content.

    Expected format seen in files:
      Plan                 : Premium
      Membership Status    : CURRENT_MEMBER

    We only need Premium vs Standard/Standare.
    """
    if not txt:
        return None

    # Normalize whitespace to make parsing robust.
    # Example: "Plan                 : Premium" -> "Plan : Premium"-ish.
    norm = re.sub(r"\s+", " ", txt)

    # Look for: Plan : Premium/Standard/Standare (case-insensitive)
    m = re.search(r"\bPlan\s*:\s*(Premium|Standard|Standare|Basic|Mobile)\b", norm, re.IGNORECASE)
    if not m:
        return None

    return (m.group(1) or '').strip()


def infer_used_folder_from_plan(plan: str | None, fallback_package_arg: str) -> str:
    n = (plan or '').lower()
    if 'premium' in n:
        return USED_PREMIUM_FOLDER
    if 'standare' in n or 'standard' in n:
        return USED_STANDARE_FOLDER

    arg = (fallback_package_arg or '').strip().lower()
    if arg == 'premium':
        return USED_PREMIUM_FOLDER
    return USED_STANDARE_FOLDER



if not cookie_files:
    print(f"No .txt cookie files found in: {COOKIE_FOLDER}")
    sys.exit(3)


def run_script_and_capture(package_arg: str) -> tuple[int, str]:
    """Runs script.py and captures stdout+stderr as text."""
    cmd = [sys.executable, SCRIPT_FILE, package_arg]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
    )
    out = (proc.stdout or '') + (proc.stderr or '')
    return proc.returncode, out


def extract_failure(out_text: str) -> bool:
    # script.py prints: "Failed: No token found in response." on failure
    return 'Failed: No token found in response.' in out_text


def extract_login_url(out_text: str) -> str | None:
    # script.py success prints: "Login URL: https://netflix.com/?nftoken=..."
    m = re.search(r"Login URL:\s*(https?://[^\s\r\n]+)", out_text)
    return m.group(1).strip() if m else None


def move_file(src_path: str, dest_dir: str) -> None:
    base = os.path.basename(src_path)
    dest_path = os.path.join(dest_dir, base)

    if not os.path.exists(dest_path):
        os.replace(src_path, dest_path)
        return

    # If already exists, add suffix
    name, ext = os.path.splitext(base)
    suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=5))
    dest_path = os.path.join(dest_dir, f"{name}_{suffix}{ext}")
    os.replace(src_path, dest_path)


# kept for backward-compat with old logic (filename-based). Not used anymore for routing.
def infer_used_folder_from_filename(fname: str, fallback_package_arg: str) -> str:

    n = (fname or '').lower()
    if 'premium' in n:
        return USED_PREMIUM_FOLDER
    if 'standare' in n or 'standard' in n:
        return USED_STANDARE_FOLDER

    arg = (fallback_package_arg or '').strip().lower()
    if arg == 'premium':
        return USED_PREMIUM_FOLDER
    return USED_STANDARE_FOLDER






max_attempts = min(20, len(cookie_files))
random.shuffle(cookie_files)

last_out = ''
last_rc = 1

attempt = 0

for fname in cookie_files[:max_attempts]:

    attempt += 1
    src_path = os.path.join(COOKIE_FOLDER, fname)

    try:
        with open(src_path, 'r', encoding='utf-8', errors='ignore') as rf:
            content = rf.read().strip()
    except Exception:
        continue

    if not content:
        try:
            move_file(src_path, FAILED_FOLDER)
        except Exception:
            pass
        continue

    with open(INPUT_FILE, 'w', encoding='utf-8') as wf:
        wf.write(content)

    print(f"Attempt {attempt}/{max_attempts}: trying {fname}...", end='\r')
    rc, out = run_script_and_capture(PACKAGE_ARG)
    last_rc = rc
    last_out = out

    failure = extract_failure(out)
    login_url = extract_login_url(out)
    success = (not failure) and bool(login_url)

    if success:
        # Clear the attempt line and print only the URL
        print("\r" + " " * 100 + "\r", end='')
        print(login_url)
        try:
            # Route by the plan extracted from the cookie content ("Plan : Premium" line).
            plan = extract_plan_from_content(content)
            dest_dir = infer_used_folder_from_plan(plan, PACKAGE_ARG)
            move_file(src_path, dest_dir)
        except Exception:
            pass
        sys.exit(0)



    # Failure path (no token)
    try:
        move_file(src_path, FAILED_FOLDER)
    except Exception:
        pass

# All attempts failed
print(last_out)
sys.exit(last_rc)

