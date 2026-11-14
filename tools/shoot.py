#!/usr/bin/env python3
"""Safari screenshots of the Brazos website on one iOS Simulator (run on a macOS runner).

  BASE=https://site shoot.py --names "iPhone 16|iPhone 15" --step 613 --out out/iphone-16
  shoot.py --names "iPhone 16|iPhone 15" --boot-only      boot it, print its udid

--names: device names in order of preference, "|" between them; a trailing * matches a prefix.
--step: front-page scroll step in points (about 0.72 of the screen height, so shots overlap).
"""
import argparse
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
    return subprocess.run(args, check=check, capture_output=True, text=True).stdout


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


def shot(udid, url, path, log):
    """Open the URL, then screenshot until three shots in a row match (loaded and still), at most ~16 s."""
    run("xcrun", "simctl", "openurl", udid, url)
    start = time.time()
    time.sleep(2.5)
    prev, calm = None, 0
    while True:
        run("xcrun", "simctl", "io", udid, "screenshot", "--type=png", path)
        cur = look(path)
        calm = calm + 1 if prev is not None and same(prev, cur) else 0
        prev = cur
        if calm >= 2 or time.time() - start > 16:
            break
        time.sleep(0.5)
    state = "still" if calm >= 2 else "still moving at 16 s"
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

    def url(path, query, hash_):
        return f"{base}{path}?{query + '&' if query else ''}r={next(n)}{hash_}"

    log = open(f"{out}/log.tsv", "w")
    shot(udid, url("/", "y=0", "#front"), f"{out}/00-first-launch.png", log)

    i = 1
    prev, y = None, 0
    while y <= FRONT_MAX_Y:
        path = f"{out}/{i:02d}-front-y{y:05d}.png"
        cur = shot(udid, url("/", f"y={y}", "#front"), path, log)
        if prev is not None and same(prev, cur):  # past the page end: the same view again
            os.remove(path)
            log.write(f"page end before y={y}\n")
            break
        prev, y, i = cur, y + args.step, i + 1

    for name, query, hash_ in DEMO:
        shot(udid, url("/", query, hash_), f"{out}/{i:02d}-{name}.png", log)
        i += 1
    for name, path in LEGAL:
        shot(udid, url(path, "", ""), f"{out}/{i:02d}-{name}.png", log)
        i += 1

    run("xcrun", "simctl", "ui", udid, "appearance", "dark")
    time.sleep(2)
    for name, query, hash_ in DARK:
        shot(udid, url("/", query, hash_), f"{out}/{i:02d}-{name}.png", log)
        i += 1
    log.close()


if __name__ == "__main__":
    main()
