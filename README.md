# brazos-site-check

Screenshots of the Brazos website in Safari on iOS Simulators (the same Safari as a real iPhone), on a free GitHub Mac.

One run of `.github/workflows/ios-safari.yml` gives one artifact, `ios-safari-<label>`:

- `iphone-se/`, `iphone-16/`, `iphone-16-pro-max/`, `ipad/`: the front page from top to bottom, every demo screen, the legal pages and the 404 page in a light system, then the front page, demo Home and a chat in a dark system. `log.tsv` lists each URL; `device.txt` names the simulator and iOS version.
- `maestro/`: taps through the site on the iPhone (Get the app, a FAQ answer, the demo tabs, Create, a chat with the keyboard open, Dark, exit), a screenshot after each step, plus `scroll.mp4` (the front page swiped top to bottom) and `interact.mp4`.

## Check the live site

```bash
gh workflow run ios-safari.yml -R mahmudur-2/brazos-site-check -f label=live
gh run list -R mahmudur-2/brazos-site-check -w ios-safari.yml -L 1      # the run id
gh run watch <run-id> -R mahmudur-2/brazos-site-check
gh run download <run-id> -R mahmudur-2/brazos-site-check -D "C:\Users\mdmah\runs\web-live\shots\ios-sim\live"
```

## Check a new build before it goes live

The repo is public: whatever is pushed to `dist/` can be read by anyone.

```bash
cd C:/Users/mdmah/runs/brazos-site-check
rm -rf dist && cp -r C:/Users/mdmah/runs/web-live/dist dist
git add dist && git commit -m "dist: <what changed>" && git push origin main
gh workflow run ios-safari.yml -R mahmudur-2/brazos-site-check -f base=local -f label=<name>
gh run list -R mahmudur-2/brazos-site-check -w ios-safari.yml -L 1      # the run id
gh run watch <run-id> -R mahmudur-2/brazos-site-check
gh run download <run-id> -R mahmudur-2/brazos-site-check -D "C:\Users\mdmah\runs\web-live\shots\ios-sim\<name>"
```

With `base=local` each Mac serves `dist/` with `serve.mjs` (it follows the Cloudflare rules: `/privacy` → `privacy.html`, the 404 page, `_headers`) at `http://localhost:8790`.

## Files

- `tools/shoot.py`: boots one simulator, opens each URL in Safari and screenshots it once the screen stops changing.
- `tools/record.sh`: records the simulator screen between two screenshots a Maestro flow takes.
- `tools/sheet.py`: `python tools/sheet.py <download dir>` makes one contact sheet per device, `sheet-<device>.png`, in that folder (needs Pillow).
- `tools/site.sh`: picks the site (the live origin, or `dist/` served on the Mac).
- `flows/`: the Maestro flows.
- `serve.mjs`: the static server for `base=local`.
