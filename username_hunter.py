#!/usr/bin/env python3
"""
Instagram Username Hunter — continuous research loop.
Runs until --target available names are found (default 70).
Persists state to checked.json so restarts skip already-checked names.

Usage:
  python username_hunter.py
  python username_hunter.py --target 70 --min-len 3 --max-len 6
  python username_hunter.py --dry-run          # no HTTP requests
"""

import argparse
import csv
import itertools
import json
import random
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR        = Path(__file__).parent.resolve()
CHECKED_FILE      = SCRIPT_DIR / "checked.json"
AVAILABLE_CSV     = SCRIPT_DIR / "available_usernames.csv"
DOTTED_CSV        = SCRIPT_DIR / "available_dotted.csv"
PROGRESS_FILE     = SCRIPT_DIR / "progress.txt"
UNCOMMON_WORDS_FILE = SCRIPT_DIR / "uncommon_words.txt"

IG_URL = "https://www.instagram.com/{username}/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 "
    "Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

CONSONANTS = list("bcdfghjklmnprstvwyz")
VOWELS     = list("aeiou")

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


def load_checked() -> set:
    """Load the set of previously checked usernames from disk."""
    if CHECKED_FILE.exists():
        try:
            data = json.loads(CHECKED_FILE.read_text())
            return set(data) if isinstance(data, list) else set()
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def save_checked(checked: set) -> None:
    """Persist the checked set to disk."""
    CHECKED_FILE.write_text(json.dumps(sorted(checked), indent=None))


def ensure_csv_header() -> None:
    """Create CSVs with header rows if they don't exist yet."""
    if not AVAILABLE_CSV.exists():
        with open(AVAILABLE_CSV, "w", newline="") as f:
            csv.writer(f).writerow(["username", "strategy", "timestamp"])
    if not DOTTED_CSV.exists():
        with open(DOTTED_CSV, "w", newline="") as f:
            csv.writer(f).writerow(["username", "word1", "word2", "timestamp"])


def count_csv_rows(path: Path) -> int:
    """Count data rows in a CSV (excluding header)."""
    if not path.exists():
        return 0
    try:
        with open(path, newline="") as f:
            return max(0, sum(1 for _ in f) - 1)  # minus header row
    except Exception:
        return 0


def append_available(username: str, strategy: str) -> None:
    """Append one available plain username to the CSV immediately."""
    with open(AVAILABLE_CSV, "a", newline="") as f:
        csv.writer(f).writerow(
            [username, strategy, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())]
        )


def append_dotted(username: str) -> None:
    """Append one available dotted username to the dotted CSV immediately."""
    parts = username.split(".", 1)
    word1 = parts[0] if parts else ""
    word2 = parts[1] if len(parts) > 1 else ""
    with open(DOTTED_CSV, "a", newline="") as f:
        csv.writer(f).writerow(
            [username, word1, word2, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())]
        )


def write_progress(total_checked: int, available_count: int, target: int,
                   available_dotted: int, strategy: str,
                   last_username: str, start_time: float) -> None:
    """Write a human-readable progress snapshot to progress.txt."""
    elapsed = time.time() - start_time
    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    rate = (total_checked / elapsed * 3600) if elapsed > 0 else 0
    pct  = (available_count / target * 100) if target > 0 else 0

    found_lines = []
    if AVAILABLE_CSV.exists():
        try:
            with open(AVAILABLE_CSV, newline="") as f:
                for row in csv.DictReader(f):
                    found_lines.append(
                        f"  {row['username']:<16} [{row['strategy']}]  {row['timestamp']}"
                    )
        except Exception:
            pass

    dotted_lines = []
    if DOTTED_CSV.exists():
        try:
            with open(DOTTED_CSV, newline="") as f:
                for row in csv.DictReader(f):
                    dotted_lines.append(f"  {row['username']:<24}  {row['timestamp']}")
        except Exception:
            pass

    lines = [
        "=" * 56,
        "  Instagram Username Hunter — Progress Report",
        f"  Updated : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "=" * 56,
        f"  Checked          : {total_checked}",
        f"  Plain available  : {available_count} / {target}  ({pct:.1f}%)",
        f"  Dotted available : {available_dotted}  (no target — collect all)",
        f"  Elapsed          : {elapsed_str}",
        f"  Rate             : ~{rate:.0f} checks/hour",
        f"  Strategy now     : {strategy}",
        f"  Last checked     : {last_username}",
        "-" * 56,
        "  Plain usernames found:",
    ]
    lines += found_lines if found_lines else ["  (none yet)"]
    lines += ["-" * 56, "  Dotted handles found (word.word):"]
    lines += dotted_lines if dotted_lines else ["  (none yet)"]
    lines.append("=" * 56)

    PROGRESS_FILE.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Candidate generators
# ---------------------------------------------------------------------------


def fresh_uncommon_generator(min_len: int, max_len: int):
    """
    Infinite generator over uncommon_words.txt — reshuffles on each full cycle.
    This is the primary strategy: covers all 16k+ words before repeating.
    """
    while True:
        if not UNCOMMON_WORDS_FILE.exists():
            yield "rune"
            continue
        raw = UNCOMMON_WORDS_FILE.read_text().splitlines()
        random.shuffle(raw)
        for w in raw:
            w = w.strip().lower()
            if w and min_len <= len(w) <= max_len and w.isalpha():
                yield w


def cvcv_generator(min_len: int, max_len: int):
    """Yield randomly generated pronounceable strings (CVCV / VCVC patterns)."""
    patterns = {
        3: ["cvc", "vcv", "cvv", "vcc"],
        4: ["cvcv", "vcvc", "cvvc", "vccv"],
        5: ["cvcvc", "vcvcv", "cvccv", "vccvc"],
        6: ["cvcvcv", "vcvcvc", "cvccvc", "vccvcv"],
    }
    pool = []
    for length in range(min_len, max_len + 1):
        pool.extend(patterns.get(length, []))

    while True:
        pattern = random.choice(pool)
        word = "".join(
            random.choice(CONSONANTS) if ch == "c" else random.choice(VOWELS)
            for ch in pattern
        )
        yield word


COMMON_SHORT = [
    "cat", "dog", "fox", "bee", "ant", "owl", "bat", "elk", "emu", "yak",
    "cod", "eel", "jay", "ram", "gnu", "mew", "koi", "dab", "doe",
    "box", "cup", "pen", "bag", "hat", "cap", "map", "key", "jar", "pot",
    "pin", "rod", "bar", "log", "arc", "hub", "lab", "pub", "spa", "gym",
    "dye", "ore", "tar", "wax", "tin", "gel", "gas", "oil", "fat", "ash",
    "mud", "ice", "fog", "mist", "frost", "flame", "smoke", "ember",
    "lake", "pond", "reef", "cave", "dune", "peak", "vale", "glen",
    "rift", "cove", "isle", "moor", "mire", "dell", "ford",
]


def common_words_generator(min_len: int, max_len: int):
    """Yield common short English words (covers ban-released handles)."""
    pool = [w for w in COMMON_SHORT if min_len <= len(w) <= max_len]
    while True:
        random.shuffle(pool)
        yield from pool


FOREIGN_WORDS = [
    # Japanese
    "kage", "kami", "kaze", "hana", "yuki", "sora", "mizu", "tora", "kiri",
    "kumo", "nami", "shiro", "kuro", "neko", "inu", "tori", "uma", "kame",
    "fuji", "asahi", "dojo", "ninja", "tanto", "shoji", "zen", "musha", "bushi",
    # Latin
    "lumen", "nova", "vita", "aura", "luna", "terra", "ignis", "aqua",
    "silva", "mons", "flos", "pax", "lux", "fides", "spes", "amor",
    "anima", "animus", "umbra", "nox", "via", "rex", "dux",
    # Greek
    "helix", "glyph", "rune", "logos", "chaos", "cosmos", "ethos",
    "pathos", "aether", "psyche", "soma", "bios", "demos", "polis",
    # Sanskrit
    "bodhi", "karma", "prana", "atman", "brahma", "surya", "agni",
    "lotus", "chakra", "mantra", "sutra", "veda", "deva", "naga", "yogi",
    # Norse / Celtic
    "rune", "druid", "fjord", "wyrd", "odin", "thor", "freyr", "skald",
]


def foreign_words_generator(min_len: int, max_len: int):
    """Yield romanized foreign-language short words."""
    pool = list({w for w in FOREIGN_WORDS if min_len <= len(w) <= max_len and w.isalpha()})
    while True:
        random.shuffle(pool)
        yield from pool


def dotted_generator():
    """
    Yield 'word1.word2' dotted handles forever.
    Prefers short 3-4 char words for clean handles like 'sol.kira', 'fen.nova'.
    Combination space is billions — essentially infinite, no repeats for ages.
    """
    def build_pool():
        if not UNCOMMON_WORDS_FILE.exists():
            return ["rune", "vale", "ash", "sol", "ori", "fen", "koa", "nox"]
        raw = UNCOMMON_WORDS_FILE.read_text().splitlines()
        short  = [w.strip().lower() for w in raw
                  if w.strip() and 3 <= len(w.strip()) <= 4 and w.strip().isalpha()]
        medium = [w.strip().lower() for w in raw
                  if w.strip() and 5 <= len(w.strip()) <= 6 and w.strip().isalpha()]
        pool = short * 3 + medium  # weight toward short words
        return pool if pool else ["rune", "vale", "ash", "sol"]

    pool = build_pool()
    random.shuffle(pool)
    checks = 0

    while True:
        checks += 1
        # Refresh pool every ~5000 yields
        if checks % 5000 == 0:
            pool = build_pool()
            random.shuffle(pool)

        w1 = random.choice(pool)
        w2 = random.choice(pool)
        if w1 != w2:
            username = f"{w1}.{w2}"
            if len(username) <= 24:   # Instagram max is 30; keep clean
                yield username


# ---------------------------------------------------------------------------
# Infinite round-robin generator
# ---------------------------------------------------------------------------

STRATEGY_NAMES = [
    "uncommon_words",
    "cvcv",
    "common_words",
    "foreign_words",
    "dotted_words",
]


def infinite_candidate_generator(min_len: int, max_len: int, skip_dotted: bool = False):
    """
    Yields (username, strategy) tuples forever.
    Rotates through strategies every SWITCH_EVERY candidates.
    """
    SWITCH_EVERY = 20

    generators = {
        "uncommon_words": fresh_uncommon_generator(min_len, max_len),
        "cvcv":           cvcv_generator(min_len, max_len),
        "common_words":   common_words_generator(min_len, max_len),
        "foreign_words":  foreign_words_generator(min_len, max_len),
        "dotted_words":   dotted_generator(),
    }

    active = [s for s in STRATEGY_NAMES if not (skip_dotted and s == "dotted_words")]
    strategy_cycle = itertools.cycle(active)
    current_strategy = next(strategy_cycle)
    count_in_strategy = 0

    while True:
        gen = generators[current_strategy]
        try:
            candidate = next(gen)
        except StopIteration:
            current_strategy = next(strategy_cycle)
            count_in_strategy = 0
            continue

        # Validate candidate
        if current_strategy == "dotted_words":
            parts = candidate.split(".")
            if len(parts) != 2 or not all(p.isalpha() and p for p in parts):
                continue
        else:
            if not candidate or not candidate.isalpha():
                continue

        yield candidate, current_strategy

        count_in_strategy += 1
        if count_in_strategy >= SWITCH_EVERY:
            current_strategy = next(strategy_cycle)
            count_in_strategy = 0


# ---------------------------------------------------------------------------
# Instagram availability check
# ---------------------------------------------------------------------------

# Instagram JSON API endpoint — returns 404 when user doesn’t exist, 200 with
# user data when they do. Much more reliable than HTML body scraping.
IG_API_URL = "https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"

# Fallback: phrases in HTML body that indicate a missing profile.
NOT_FOUND_MARKERS = [
    "Sorry, this page isn’t available",   # curly apostrophe U+2019 (real HTML)
    "Sorry, this page isn’t available",        # straight apostrophe fallback
    "Page Not Found",
    "page isn’t available",
    "page isn’t available",
    ‘"user_not_found"’,
    ‘"username_not_found"’,
    ‘"UserNotFound"’,
    ‘"errorCode":100’,
    "The link you followed may be broken",
    ‘"data":{"user":null}’,                    # JSON API: user field is null
]

# Phrases that confirm a profile EXISTS (body-check fallback).
TAKEN_MARKERS = [
    ‘"ProfilePage"’,
    ‘"GraphUser"’,
    ‘"is_private"’,
    ‘"edge_followed_by"’,
]


def check_instagram(username: str, session: requests.Session) -> bool:
    """
    Returns True if the username appears to be available.

    Detection strategy (in order):
      1. JSON API  → 404              : available
      2. JSON API  → 200, user=null   : available
      3. JSON API  → 200, user data   : taken
      4. HTML page → 404              : available
      5. HTML page → NOT_FOUND_MARKERS: available
      6. HTML page → TAKEN_MARKERS    : taken
      7. HTTP 429                     : sleep 65 s, retry
      8. Persistent failure           : treat as taken (safe default)
    """
    api_url     = IG_API_URL.format(username=username)
    profile_url = IG_URL.format(username=username)

    api_headers = {
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "x-ig-app-id":     "936619743392459",
        "Referer":         "https://www.instagram.com/",
        "X-Requested-With":"XMLHttpRequest",
    }
    html_headers = {
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
        "Referer":         "https://www.google.com/",
        "Cache-Control":   "no-cache",
    }

    for attempt in range(4):
        try:
            # ── Primary: JSON API ──────────────────────────────────────────
            resp = session.get(api_url, headers=api_headers, timeout=15,
                               allow_redirects=True)

            if resp.status_code == 404:
                return True                          # clear "not found"

            if resp.status_code == 429:
                wait = 65 + random.uniform(0, 20)
                print(f"\n  [RATE LIMITED] Sleeping {wait:.0f}s …", flush=True)
                time.sleep(wait)
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    user = data.get("data", {}).get("user")
                    if user is None:
                        return True                  # API says user = null
                    return False                     # user object present = taken
                except Exception:
                    pass                             # bad JSON → fall to HTML

            # ── Fallback: HTML profile page ────────────────────────────────
            resp2 = session.get(profile_url, headers=html_headers, timeout=15,
                                allow_redirects=True)

            if resp2.status_code == 404:
                return True

            if resp2.status_code == 200:
                body = resp2.text
                for marker in NOT_FOUND_MARKERS:
                    if marker in body:
                        return True
                for marker in TAKEN_MARKERS:
                    if marker in body:
                        return False
                # Could not determine — treat as taken (safe)
                return False

            if attempt < 3:
                time.sleep(2 ** (attempt + 1))

        except requests.exceptions.ConnectionError:
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
        except requests.exceptions.Timeout:
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
        except KeyboardInterrupt:
            raise
        except Exception:
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))

    return False  # persistent failure → treat as taken


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram username hunter — continuous loop")
    parser.add_argument("--target",    type=int,  default=70,    help="Stop after N plain available names (default 70)")
    parser.add_argument("--min-len",   type=int,  default=3,     help="Minimum username length (default 3)")
    parser.add_argument("--max-len",   type=int,  default=6,     help="Maximum username length (default 6)")
    parser.add_argument("--dry-run",   action="store_true",      help="Simulate without hitting Instagram")
    parser.add_argument("--no-dotted", action="store_true",      help="Disable dotted handle strategy")
    args = parser.parse_args()

    ensure_csv_header()

    # Resume state
    checked = load_checked()
    total_checked = len(checked)

    # BUG FIX: read counts from existing CSVs so resume shows correct numbers
    available_count   = count_csv_rows(AVAILABLE_CSV)
    available_dotted  = count_csv_rows(DOTTED_CSV)

    print("=" * 56)
    print("  Instagram Username Hunter")
    print("=" * 56)
    print(f"  Target (plain)   : {args.target}")
    print(f"  Dotted strategy  : {'OFF' if args.no_dotted else 'ON — collect all'}")
    print(f"  Length range     : {args.min_len}–{args.max_len} chars")
    print(f"  Dry-run mode     : {args.dry_run}")
    print(f"  Resuming from    : {total_checked} previously checked")
    print(f"  Plain found so far : {available_count}")
    print(f"  Dotted found so far: {available_dotted}")
    print(f"  Word pool size   : {sum(1 for _ in open(UNCOMMON_WORDS_FILE)) if UNCOMMON_WORDS_FILE.exists() else 0} words")
    print("=" * 56)
    print()

    session = requests.Session()
    start_time = time.time()
    SAVE_INTERVAL = 50
    checks_since_save = 0
    last_username = ""

    try:
        for username, strategy in infinite_candidate_generator(
            args.min_len, args.max_len, skip_dotted=args.no_dotted
        ):
            # Skip already-checked
            if username in checked:
                continue

            checked.add(username)
            total_checked += 1
            checks_since_save += 1
            last_username = username

            is_dotted = strategy == "dotted_words"

            if args.dry_run:
                chance = (1 / 8) if is_dotted else (1 / 30)
                is_available = random.random() < chance
                time.sleep(0.01)
            else:
                time.sleep(random.uniform(2, 5))
                is_available = check_instagram(username, session)

            status_char = "✓" if is_available else "✗"
            status_word = "AVAILABLE" if is_available else "TAKEN"

            plain_disp = available_count  + (1 if (is_available and not is_dotted) else 0)
            dot_disp   = available_dotted + (1 if (is_available and is_dotted)     else 0)

            print(
                f"[{total_checked} chk | {plain_disp} plain | {dot_disp} dotted"
                f" | {strategy}] {username} → {status_word} {status_char}",
                flush=True,
            )

            if is_available:
                if is_dotted:
                    available_dotted += 1
                    append_dotted(username)
                    print(f"  🔵 Dotted  → {username}", flush=True)
                else:
                    available_count += 1
                    append_available(username, strategy)
                    print(f"  🟢 Plain   → {username}", flush=True)

                write_progress(total_checked, available_count, args.target,
                               available_dotted, strategy, last_username, start_time)

            if checks_since_save >= SAVE_INTERVAL:
                save_checked(checked)
                write_progress(total_checked, available_count, args.target,
                               available_dotted, strategy, last_username, start_time)
                checks_since_save = 0

            if available_count >= args.target:
                print(
                    f"\n🎯 Target reached: {available_count} plain + "
                    f"{available_dotted} dotted after {total_checked} checks."
                )
                break

    except KeyboardInterrupt:
        print(
            f"\n⚡ Stopped. {available_count} plain + {available_dotted} dotted "
            f"found. {total_checked} total checked."
        )

    finally:
        save_checked(checked)
        write_progress(total_checked, available_count, args.target,
                       available_dotted, "", last_username, start_time)
        print(f"\n  State   → {CHECKED_FILE}")
        print(f"  Plain   → {AVAILABLE_CSV}")
        print(f"  Dotted  → {DOTTED_CSV}")
        print(f"  Progress→ {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
