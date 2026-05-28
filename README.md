# Ids

A slow, resumable Instagram username availability checker designed to favor
accurate results over speed.

## Termux setup

```bash
pkg update
pkg install python
python -m pip install -r requirements.txt
```

## Recommended usage

1. Optional but recommended: create a saved Instagram session. Logged-in checks
   use the profile-info endpoint, which is less noisy than anonymous signup
   attempts.

   ```bash
   python login.py
   ```

2. Run the hunter with conservative timing. Instagram returns HTTP `429` when
   you are being rate limited; the script now treats that as **unknown**, waits,
   and does not save that username as checked.

   ```bash
   python username_hunter.py --target 20 --min-delay 90 --max-delay 180
   ```

3. If you already hit a lot of `429` responses in Termux, stop the script and
   wait before trying again. Continuing immediately usually produces more 429s
   and less reliable results.

## Notes about accuracy

* A username availability result is only a point-in-time check. Instagram can
  change availability or reserve names at any time.
* For best accuracy, use `login.py` first and keep delays high.
* The script intentionally does not try to bypass Instagram rate limits. It
  respects `Retry-After` when Instagram sends it and backs off with jitter.
