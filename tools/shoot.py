#!/usr/bin/env python3
"""Safari screenshots of the Brazos website on one iOS Simulator (run on a macOS runner).

  BASE=https://site shoot.py --names "iPhone 16|iPhone 15" --step 613 --out out/iphone-16
  shoot.py --names "iPhone 16|iPhone 15" --boot-only      boot it, print its udid

--names: device names in order of preference, "|" between them; a trailing * matches a prefix.
--step: front-page scroll step in points (about 0.72 of the screen height, so shots overlap).
"""
import argparse
import glob
import itertools
import json
import os
import re
import subprocess
import time

FRONT_MAX_Y = 14000  # the front page is about 11,800 px tall on a phone

DEMO = [  # (file name, extra query, hash)
    ("app-home", "", "#app"),
    ("app-discover", "", "#app-discover"),
    ("app-customer-myjobs", "", "#app-customer-myjobs"),
    ("app-inbox", "", "#app-inbox"),
    ("app-chat-t1", "", "#app-chat-t1"),
    ("app-profile", "", "#app-profile"),
    ("app-notifications", "", "#app-notifications"),
    ("app-worker", "", "#app-worker"),
    ("app-worker-map", "", "#app-worker-map"),
    ("app-earnings", "", "#app-earnings"),
    ("app-job-j1", "", "#app-job-j1"),
    ("app-person-sam", "", "#app-person-sam"),
    ("app-details-m1", "", "#app-details-m1"),
    ("app-bid-m1", "", "#app-bid-m1"),
    ("show-mode", "show=mode", "#app-customer"),
    ("show-create", "show=create", "#app-customer"),
    ("app-dark", "", "#app-dark"),
    ("app-chat-t1-dark", "", "#app-chat-t1-dark"),
    ("app-profile-dark", "", "#app-profile-dark"),
]
LEGAL = [("privacy", "/privacy"), ("terms", "/terms"), ("support", "/support"), ("404", "/does-not-exist")]
DARK = [("dark-front-y00000", "y=0", "#front"), ("dark-app-home", "", "#app"), ("dark-app-chat-t1", "", "#app-chat-t1")]


def run(*args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode:
        raise SystemExit(f"{' '.join(args)} exited {p.returncode}: {p.stderr.strip()}")
    return p.stdout


def retry(*args, tries=4):
    """simctl openurl/launch can time out (exit 60) while a fresh simulator is still settling."""
    for i in range(tries):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0:
            return
        print(f"{args[2]} exited {p.returncode}, try {i + 1}: {p.stderr.strip()}", flush=True)
        time.sleep(10)
    raise SystemExit(f"{' '.join(args)} failed {tries} times")


def pick(names):
    """The first wanted device on the newest iOS runtime that has one."""
    devices = json.loads(run("xcrun", "simctl", "list", "devices", "available", "--json"))["devices"]

    def version(key):
        m = re.search(r"\.iOS-([\d-]+)$", key)
        return tuple(map(int, m.group(1).split("-"))) if m else None

    for runtime in sorted((k for k in devices if version(k)), key=version, reverse=True):
        for name in names.split("|"):
            for d in devices[runtime]:
                if d["name"] == name or (name.endswith("*") and d["name"].startswith(name[:-1])):
                    return d, runtime
    raise SystemExit(f"no available simulator named {names}")


def boot(names):
    device, runtime = pick(names)
    udid = device["udid"]
    # No Mac keyboard attached, so tapping a field opens the on-screen keyboard as on a phone.
    run("defaults", "write", "com.apple.iphonesimulator", "ConnectHardwareKeyboard", "-bool", "false")
    if device["state"] != "Booted":
        run("xcrun", "simctl", "boot", udid)
    run("xcrun", "simctl", "bootstatus", udid, "-b")
    run("xcrun", "simctl", "status_bar", udid, "override", "--time", "9:41", "--batteryState", "charged",
        "--batteryLevel", "100", "--cellularBars", "4", check=False)
    run("xcrun", "simctl", "ui", udid, "appearance", "light")
    retry("xcrun", "simctl", "launch", udid, "com.apple.mobilesafari")
    time.sleep(5)
    return device, runtime


def look(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.convert("L").resize((160, round(160 * im.height / im.width)))


def same(a, b):
    """Under 0.3% of a 160 px wide grey copy changed: a blinking dot passes, a scroll or new screen does not."""
    from PIL import ImageChops
    if a.size != b.size:
        return False
    changed = ImageChops.difference(a, b).point(lambda v: 255 if v > 12 else 0).histogram()[255]
    return changed / (a.size[0] * a.size[1]) < 0.003


def blank(img):
    """Still loading: one flat colour between the status bar and Safari's bottom bar."""
    w, h = img.size
    body = img.crop((0, h // 10, w, h * 85 // 100))
    hist = body.histogram()
    top = max(range(256), key=hist.__getitem__)
    return sum(hist[max(0, top - 6):top + 7]) / (body.size[0] * body.size[1]) > 0.985


TAB_DIRS = []


def close_tabs(udid):
    """Quit Safari and drop its saved tabs, so the next openurl opens Safari with that one tab.
    (Each openurl adds a tab: dozens of them slowed Safari to a minute a page and filled the iPad tab bar.)"""
    run("xcrun", "simctl", "terminate", udid, "com.apple.mobilesafari", check=False)
    if not TAB_DIRS:
        root = os.path.expanduser(f"~/Library/Developer/CoreSimulator/Devices/{udid}/data")
        TAB_DIRS.extend(sorted({os.path.dirname(p) for p in glob.glob(f"{root}/**/SafariTabs.db", recursive=True)}))
        print("Safari tabs live in", TAB_DIRS or "(not found)", flush=True)
    for d in TAB_DIRS:
        for p in glob.glob(f"{d}/SafariTabs.db*"):
            os.remove(p)


def shot(udid, url, path, log, last):
    """Open the URL in a fresh Safari with one tab, then screenshot until the page is not blank, differs from the
    last screen (`last`), and three shots in a row match. A page that keeps moving is taken at 20 s;
    a blank one, or one still showing the last screen, is waited for up to 45 s."""
    close_tabs(udid)
    retry("xcrun", "simctl", "openurl", udid, url)
    start = time.time()
    time.sleep(2.5)
    prev, calm = None, 0
    while True:
        run("xcrun", "simctl", "io", udid, "screenshot", "--type=png", path)
        cur = look(path)
        calm = calm + 1 if prev is not None and same(prev, cur) else 0
        prev = cur
        waited = time.time() - start
        new = not blank(cur) and not (last is not None and same(last, cur))
        if (new and (calm >= 2 or waited > 20)) or waited > 45:
            break
        time.sleep(0.5)
    state = ("BLANK" if blank(cur) else "same as the last screen" if last is not None and same(last, cur)
             else "still" if calm >= 2 else "still moving")
    log.write(f"{os.path.basename(path)}\t{time.time() - start:.1f}s\t{state}\t{url}\n")
    log.flush()
    print(os.path.basename(path), state, flush=True)
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", required=True)
    ap.add_argument("--step", type=int)
    ap.add_argument("--out")
    ap.add_argument("--boot-only", action="store_true")
    args = ap.parse_args()

    device, runtime = boot(args.names)
    udid = device["udid"]
    if args.boot_only:
        print(udid)
        return

    base = os.environ["BASE"].rstrip("/")
    out = args.out
    os.makedirs(out, exist_ok=True)
    with open(f"{out}/device.txt", "w") as f:
        f.write(f"{device['name']}\t{runtime.rsplit('.', 1)[-1]}\t{udid}\t{base}\n")
    n = itertools.count(1)  # r=<n> makes every URL new, so Safari loads it fresh even when only the hash differs
    log = open(f"{out}/log.tsv", "w")
    last = None

    def take(name, path, query, hash_):
        nonlocal last
        url = f"{base}{path}?{query + '&' if query else ''}r={next(n)}{hash_}"
        prev, last = last, shot(udid, url, f"{out}/{name}.png", log, last)
        return prev

    # Safari's first launches show its start page and a one-time tip; these two shots take them.
    take("00a-first-launch", "/", "y=0", "#front")
    take("00b-second-launch", "/support", "", "")

    i, y = 1, 0
    while y <= FRONT_MAX_Y:
        name = f"{i:02d}-front-y{y:05d}"
        prev = take(name, "/", f"y={y}", "#front")
        if i > 1 and same(prev, last):  # past the page end: the same view again
            os.remove(f"{out}/{name}.png")
            log.write(f"page end before y={y}\n")
            break
        y, i = y + args.step, i + 1

    for name, query, hash_ in DEMO:
        take(f"{i:02d}-{name}", "/", query, hash_)
        i += 1
    for name, path in LEGAL:
        take(f"{i:02d}-{name}", path, "", "")
        i += 1

    run("xcrun", "simctl", "ui", udid, "appearance", "dark")
    time.sleep(2)
    for name, query, hash_ in DARK:
        take(f"{i:02d}-{name}", "/", query, hash_)
        i += 1
    log.close()


if __name__ == "__main__":
    main()
