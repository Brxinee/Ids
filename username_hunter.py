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
import os
import random
import re
import string
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
CHECKED_FILE = SCRIPT_DIR / "checked.json"
AVAILABLE_CSV = SCRIPT_DIR / "available_usernames.csv"
DOTTED_CSV = SCRIPT_DIR / "available_dotted.csv"
PROGRESS_FILE = SCRIPT_DIR / "progress.txt"
UNCOMMON_WORDS_FILE = SCRIPT_DIR / "uncommon_words.txt"
DICT_FILE = Path("/usr/share/dict/words")

# Instagram profile URL — a 404 means the name is free (no scraping of
# private data; we only read the HTTP status code of the public profile page).
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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 "
    "Firefox/125.0",
]

# Consonants / vowels for CVCV generation
CONSONANTS = list("bcdfghjklmnprstvwyz")
VOWELS = list("aeiou")

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
    """Persist the checked set to disk (full rewrite — fast enough for <1 M entries)."""
    CHECKED_FILE.write_text(json.dumps(sorted(checked), indent=None))


def ensure_csv_header() -> None:
    """Create CSVs with header rows if they don't exist yet."""
    if not AVAILABLE_CSV.exists():
        with open(AVAILABLE_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "strategy", "timestamp"])
    if not DOTTED_CSV.exists():
        with open(DOTTED_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "word1", "word2", "timestamp"])


def append_available(username: str, strategy: str) -> None:
    """Append one available plain username to the CSV immediately."""
    with open(AVAILABLE_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([username, strategy, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())])


def append_dotted(username: str) -> None:
    """Append one available dotted username to the dotted CSV immediately."""
    parts = username.split(".", 1)
    word1 = parts[0] if len(parts) > 0 else ""
    word2 = parts[1] if len(parts) > 1 else ""
    with open(DOTTED_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([username, word1, word2, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())])


def write_progress(total_checked: int, available_count: int, target: int,
                   available_dotted: int, strategy: str,
                   last_username: str, start_time: float) -> None:
    """Write a human-readable progress snapshot to progress.txt."""
    elapsed = time.time() - start_time
    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    rate = (total_checked / elapsed * 3600) if elapsed > 0 else 0
    pct = (available_count / target * 100) if target > 0 else 0

    # Read available CSV for the list of plain finds so far
    found_lines = []
    if AVAILABLE_CSV.exists():
        try:
            with open(AVAILABLE_CSV, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    found_lines.append(f"  {row['username']:<14} [{row['strategy']}]  {row['timestamp']}")
        except Exception:
            pass

    # Read dotted CSV for the list of dotted finds so far
    dotted_lines = []
    if DOTTED_CSV.exists():
        try:
            with open(DOTTED_CSV, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    dotted_lines.append(f"  {row['username']:<20}  {row['timestamp']}")
        except Exception:
            pass

    lines = [
        "=" * 54,
        f"  Instagram Username Hunter — Progress Report",
        f"  Updated : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "=" * 54,
        f"  Checked         : {total_checked}",
        f"  Plain available : {available_count} / {target}  ({pct:.1f}%)",
        f"  Dotted available: {available_dotted}  (no target — collect all)",
        f"  Elapsed         : {elapsed_str}",
        f"  Rate            : ~{rate:.0f} checks/hour",
        f"  Strategy now    : {strategy}",
        f"  Last checked    : {last_username}",
        "-" * 54,
        f"  Plain usernames found:",
    ]
    if found_lines:
        lines.extend(found_lines)
    else:
        lines.append("  (none yet)")

    lines.append("-" * 54)
    lines.append(f"  Dotted handles found (word.word):")
    if dotted_lines:
        lines.extend(dotted_lines)
    else:
        lines.append("  (none yet)")

    lines.append("=" * 54)
    PROGRESS_FILE.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Candidate generators
# ---------------------------------------------------------------------------


def load_uncommon_words(min_len: int, max_len: int):
    """Yield words from uncommon_words.txt."""
    if not UNCOMMON_WORDS_FILE.exists():
        return
    words = UNCOMMON_WORDS_FILE.read_text().splitlines()
    random.shuffle(words)
    for w in words:
        w = w.strip().lower()
        if w and min_len <= len(w) <= max_len and w.isalpha():
            yield w


def load_dict_words(min_len: int, max_len: int):
    """Yield words from the system dictionary."""
    if not DICT_FILE.exists():
        return
    words = DICT_FILE.read_text().splitlines()
    random.shuffle(words)
    for w in words:
        w = w.strip().lower()
        if (w and min_len <= len(w) <= max_len and w.isalpha()
                and re.match(r"^[a-z]+$", w)):
            yield w


def cvcv_generator(min_len: int, max_len: int):
    """Yield randomly generated pronounceable strings (CVCV / VCVC patterns)."""
    patterns_3 = ["cvc", "vcv", "cvv", "vcc"]
    patterns_4 = ["cvcv", "vcvc", "cvvc", "vccv"]
    patterns_5 = ["cvcvc", "vcvcv", "cvccv", "vccvc"]
    patterns_6 = ["cvcvcv", "vcvcvc", "cvccvc", "vccvcv"]

    pool = []
    for length in range(min_len, max_len + 1):
        if length == 3:
            pool.extend(patterns_3)
        elif length == 4:
            pool.extend(patterns_4)
        elif length == 5:
            pool.extend(patterns_5)
        elif length == 6:
            pool.extend(patterns_6)

    while True:
        pattern = random.choice(pool)
        word = ""
        for ch in pattern:
            if ch == "c":
                word += random.choice(CONSONANTS)
            else:
                word += random.choice(VOWELS)
        if min_len <= len(word) <= max_len:
            yield word


COMMON_SHORT = [
    "cat", "dog", "fox", "bee", "ant", "owl", "bat", "elk", "emu", "yak",
    "cod", "eel", "jay", "ram", "gnu", "mew", "koi", "dab", "tit", "doe",
    "box", "cup", "pen", "bag", "hat", "cap", "map", "key", "jar", "pot",
    "pin", "rod", "bar", "log", "arc", "hub", "lab", "pub", "spa", "gym",
    "dye", "ore", "tar", "wax", "tin", "gel", "gas", "oil", "fat", "ash",
    "mud", "ice", "fog", "mist", "frost", "flame", "smoke", "ember",
    "lake", "pond", "reef", "cave", "dune", "peak", "vale", "glen",
    "rift", "cove", "isle", "moor", "mire", "dell", "ford",
]


def common_words_generator(min_len: int, max_len: int):
    """Yield common short English words (low hit rate but covers ban-released handles)."""
    pool = [w for w in COMMON_SHORT if min_len <= len(w) <= max_len]
    random.shuffle(pool)
    while True:
        random.shuffle(pool)
        yield from pool


FOREIGN_WORDS = [
    # Japanese romaji
    "kage", "kami", "kaze", "hana", "yuki", "tsuru", "sora", "mizu",
    "tora", "kiri", "kumo", "hoshi", "tsuki", "nami", "shiro", "kuro",
    "aka", "ao", "ki", "midori", "neko", "inu", "tori", "uma", "kame",
    "sakura", "momiji", "fuji", "asahi", "yuhi", "izumi", "kawaii",
    "dojo", "sensei", "ninja", "katana", "tanto", "kunai", "shoji",
    "torii", "pagoda", "zen", "koan", "zazen", "musha", "bushi",
    # Latin
    "lumen", "nova", "vita", "aura", "luna", "terra", "ignis", "aqua",
    "ventus", "caelum", "silva", "mons", "flos", "pax", "lux", "fides",
    "spes", "amor", "veritas", "fortis", "felix", "bonus", "malus",
    "magnus", "parvus", "altus", "sacer", "sanctus", "divus",
    "anima", "animus", "umbra", "nox", "dies", "hora", "tempus",
    "locus", "via", "iter", "caput", "manus", "oculus", "auris",
    "nauta", "miles", "rex", "dux", "dominus", "servus",
    # Greek romaji
    "helix", "crypt", "glyph", "rune", "mythos", "logos", "chaos",
    "cosmos", "kairos", "telos", "ethos", "pathos", "hubris", "nemesis",
    "aether", "kronos", "tyche", "moira", "arche", "polis", "demos",
    "daimon", "psyche", "pneuma", "soma", "bios", "zoe", "nomos",
    "aletheia", "physis", "techne", "poiesis",
    # Sanskrit romaji
    "bodhi", "dharma", "karma", "prana", "atman", "brahma", "vishnu",
    "shiva", "indra", "surya", "soma", "agni", "vayu", "varuna",
    "mitra", "lotus", "chakra", "tantra", "mantra", "sutra", "veda",
    "deva", "asura", "naga", "yogi", "sadhu", "rishi", "siddhi",
    # Norse / Celtic
    "rune", "runic", "druid", "ogham", "veda", "fjord", "fjell",
    "stave", "wyrd", "norns", "aesir", "vanir", "odin", "thor",
    "freyr", "frigg", "skald", "thane", "jarl",
]


def foreign_words_generator(min_len: int, max_len: int):
    """Yield romanized foreign-language short words."""
    pool = list({w for w in FOREIGN_WORDS if min_len <= len(w) <= max_len and w.isalpha()})
    random.shuffle(pool)
    while True:
        random.shuffle(pool)
        yield from pool


def dotted_generator():
    """
    Yield 'word1.word2' dotted handles forever from the rare word pool.
    Pairs are generated randomly from the uncommon_words.txt list.
    Produces millions of combinations — essentially infinite.
    Targets short + rare combos: both words 3–4 chars for clean handles.
    """
    def load_pool() -> list:
        if not UNCOMMON_WORDS_FILE.exists():
            return ["rune", "vale", "ash", "sol", "ori", "fen", "koa", "nox"]
        raw = UNCOMMON_WORDS_FILE.read_text().splitlines()
        # Prefer short words (3-4 chars) for clean dotted handles
        short = [w.strip().lower() for w in raw
                 if w.strip() and 3 <= len(w.strip()) <= 4 and w.strip().isalpha()]
        medium = [w.strip().lower() for w in raw
                  if w.strip() and 5 <= len(w.strip()) <= 6 and w.strip().isalpha()]
        # Mostly short pairs; occasionally medium
        pool = short * 3 + medium
        return pool if pool else ["rune", "vale", "ash", "sol"]

    pool = load_pool()
    random.shuffle(pool)

    while True:
        # Refresh pool occasionally to pick up any new words added
        if random.random() < 0.001:
            pool = load_pool()
            random.shuffle(pool)

        w1 = random.choice(pool)
        w2 = random.choice(pool)
        if w1 != w2:
            username = f"{w1}.{w2}"
            # Instagram max username length is 30; dotted handles: keep total <= 22
            if len(username) <= 22:
                yield username


# ---------------------------------------------------------------------------
# Infinite round-robin generator
# ---------------------------------------------------------------------------


STRATEGY_NAMES = [
    "uncommon_words",
    "dict_words",
    "cvcv",
    "common_words",
    "foreign_words",
    "dotted_words",
]


def infinite_candidate_generator(min_len: int, max_len: int):
    """
    Yields (username, strategy) tuples forever.
    Rotates through strategies every SWITCH_EVERY checks.
    Dotted strategy rotates in every 6th slot (every ~120 checks).
    """
    SWITCH_EVERY = 20

    # These generators are stateful; build them once
    dict_gen = load_dict_words(min_len, max_len)  # generator — exhausts eventually
    cvcv_gen = cvcv_generator(min_len, max_len)   # infinite
    common_gen = common_words_generator(min_len, max_len)  # infinite cycle
    foreign_gen = foreign_words_generator(min_len, max_len)  # infinite cycle
    dotted_gen = dotted_generator()               # infinite

    # Rebuild uncommon with fresh shuffle on each cycle
    def fresh_uncommon():
        while True:
            words = []
            if UNCOMMON_WORDS_FILE.exists():
                raw = UNCOMMON_WORDS_FILE.read_text().splitlines()
                random.shuffle(raw)
                words = [w.strip().lower() for w in raw
                         if w.strip() and min_len <= len(w.strip()) <= max_len
                         and w.strip().isalpha()]
            if not words:
                words = ["rune"]  # fallback — should never be empty
            yield from words

    uncommon_inf = fresh_uncommon()

    generators = {
        "uncommon_words": uncommon_inf,
        "dict_words":     dict_gen,
        "cvcv":           cvcv_gen,
        "common_words":   common_gen,
        "foreign_words":  foreign_gen,
        "dotted_words":   dotted_gen,
    }

    strategy_cycle = itertools.cycle(STRATEGY_NAMES)
    current_strategy = next(strategy_cycle)
    count_in_strategy = 0

    while True:
        gen = generators[current_strategy]
        try:
            candidate = next(gen)
        except StopIteration:
            # This strategy is exhausted — skip to next
            current_strategy = next(strategy_cycle)
            count_in_strategy = 0
            continue

        # Validate: plain strategies must be alpha; dotted strategy allows one dot
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


def check_instagram(username: str, session: requests.Session) -> bool:
    """
    Returns True if the username appears to be available.

    Instagram now serves HTTP 200 for everything (even non-existent profiles)
    because they use a client-side JS app. We therefore check the response
    body for the phrases Instagram injects for missing profiles, in addition
    to the legacy HTTP 404 signal.

    Detection order:
      1. HTTP 404                          → available
      2. Body contains not-found markers   → available
      3. HTTP 429                          → sleep 60 s, retry
      4. Anything else (200 with profile)  → taken
    """
    url = IG_URL.format(username=username)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    # Phrases Instagram embeds in the HTML when a profile doesn't exist
    NOT_FOUND_MARKERS = [
        "Sorry, this page isn't available",
        "sorry, this page isn't available",
        "Page Not Found",
        "page isn't available",
        "isn’t available",          # curly apostrophe version
        '"user_not_found"',
        '"username_not_found"',
        '"UserNotFound"',
        '"errorCode":100',
    ]

    for attempt in range(4):
        try:
            resp = session.get(url, headers=headers, timeout=15, allow_redirects=True)

            if resp.status_code == 404:
                return True

            if resp.status_code == 429:
                wait = 60 + random.uniform(0, 15)
                print(f"\n  [RATE LIMITED] Sleeping {wait:.0f}s …", flush=True)
                time.sleep(wait)
                continue

            if resp.status_code == 200:
                body = resp.text
                # Check body for not-found signals
                for marker in NOT_FOUND_MARKERS:
                    if marker in body:
                        return True
                # 200 with none of the markers → profile exists → taken
                return False

            # Any other status (5xx etc.) → treat as taken / retry
            if attempt < 3:
                time.sleep(2 ** attempt)

        except requests.exceptions.ConnectionError:
            if attempt < 3:
                time.sleep(2 ** attempt)
        except requests.exceptions.Timeout:
            if attempt < 3:
                time.sleep(2 ** attempt)
        except KeyboardInterrupt:
            raise

    return False  # treat persistent errors as "taken" (conservative)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram username hunter — continuous loop")
    parser.add_argument("--target",     type=int, default=70,  help="Stop after finding this many plain available names (default: 70)")
    parser.add_argument("--min-len",    type=int, default=3,   help="Minimum username length (default: 3)")
    parser.add_argument("--max-len",    type=int, default=6,   help="Maximum username length (default: 6)")
    parser.add_argument("--dry-run",    action="store_true",   help="Generate candidates without hitting Instagram")
    parser.add_argument("--no-dotted",  action="store_true",   help="Disable the dotted handle strategy")
    args = parser.parse_args()

    ensure_csv_header()
    checked: set = load_checked()
    available_count = 0         # plain usernames found
    available_dotted = 0        # dotted handles found (no limit — collect all)
    total_checked = len(checked)

    print(f"Instagram Username Hunter")
    print(f"  Target (plain): {args.target} available")
    print(f"  Dotted handles: unlimited — collect all found")
    print(f"  Length        : {args.min_len}–{args.max_len} chars")
    print(f"  Dry-run       : {args.dry_run}")
    print(f"  Dotted mode   : {'OFF' if args.no_dotted else 'ON'}")
    print(f"  Resuming      : {total_checked} previously checked")
    print(f"  State file    : {CHECKED_FILE}")
    print(f"  CSV (plain)   : {AVAILABLE_CSV}")
    print(f"  CSV (dotted)  : {DOTTED_CSV}")
    print()

    session = requests.Session()
    start_time = time.time()

    # Save checked state every N checks to avoid constant disk writes
    SAVE_INTERVAL = 50
    checks_since_save = 0
    last_username = ""

    # Build effective strategy list (optionally exclude dotted)
    active_strategies = [s for s in STRATEGY_NAMES
                         if not (args.no_dotted and s == "dotted_words")]

    try:
        for username, strategy in infinite_candidate_generator(args.min_len, args.max_len):

            # Skip dotted if disabled
            if args.no_dotted and strategy == "dotted_words":
                continue

            # Skip already-checked
            if username in checked:
                continue

            # Mark as checked immediately (before the HTTP call so restarts
            # don't repeat a username stuck mid-request)
            checked.add(username)
            total_checked += 1
            checks_since_save += 1
            last_username = username

            is_dotted = strategy == "dotted_words"

            if args.dry_run:
                # Simulate: plain 1-in-30, dotted 1-in-8 (higher availability)
                chance = (1 / 8) if is_dotted else (1 / 30)
                is_available = random.random() < chance
                time.sleep(0.01)
            else:
                # Real delay: 2–5 s
                time.sleep(random.uniform(2, 5))
                is_available = check_instagram(username, session)

            status_char = "✓" if is_available else "✗"
            status_word = "AVAILABLE" if is_available else "TAKEN"

            # Display counter depends on type
            plain_disp = available_count + (1 if (is_available and not is_dotted) else 0)
            dot_disp   = available_dotted + (1 if (is_available and is_dotted) else 0)

            print(
                f"[{total_checked} chk | {plain_disp} plain | {dot_disp} dotted"
                f" | {strategy}] "
                f"{username} → {status_word} {status_char}",
                flush=True,
            )

            if is_available:
                if is_dotted:
                    available_dotted += 1
                    append_dotted(username)
                    print(f"  🔵 Dotted handle: {username}", flush=True)
                else:
                    available_count += 1
                    append_available(username, strategy)
                    print(f"  🟢 Plain handle : {username}", flush=True)

                write_progress(total_checked, available_count, args.target,
                               available_dotted, strategy, last_username, start_time)

            # Periodic state save + progress report
            if checks_since_save >= SAVE_INTERVAL:
                save_checked(checked)
                write_progress(total_checked, available_count, args.target,
                               available_dotted, strategy, last_username, start_time)
                checks_since_save = 0

            # Only plain usernames count toward the target
            if available_count >= args.target:
                print(
                    f"\n🎯 Target reached: {available_count} plain usernames found "
                    f"+ {available_dotted} dotted handles after {total_checked} checks."
                )
                break

    except KeyboardInterrupt:
        print(
            f"\n⚡ Interrupted. {available_count} plain + {available_dotted} dotted "
            f"found, {total_checked} checked total."
        )

    finally:
        save_checked(checked)
        write_progress(total_checked, available_count, args.target,
                       available_dotted, "", last_username, start_time)
        print(f"State saved      → {CHECKED_FILE}")
        print(f"Results (plain)  → {AVAILABLE_CSV}")
        print(f"Results (dotted) → {DOTTED_CSV}")
        print(f"Progress         → {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
