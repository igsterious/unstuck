# Unstuck

A replacement for the discontinued SanDisk Connect Drive app. It's one HTML file that lives **on the stick itself**.
The stick runs a WebDAV server (AirStash technology). A page served from the stick can talk to that server directly,
so this works in any browser (Chrome on Android, Edge on Windows) with nothing to install.

It can browse, filter and sort; view photos, video and audio (swipe between photos); download; upload (multiple files,
with a progress bar, or drag and drop on the PC); create folders; rename; and delete. It also shows free space when
the stick reports it.

## 1. Probe the stick (once, ~1 min)

The stick's exact paths aren't documented. This script asks the stick directly and never writes anything to it.

1. Turn the stick on and connect the **PC** to its Wi‑Fi (`SanDisk…`).
2. `python probe.py`
3. Reconnect to your normal Wi‑Fi. `probe-report.txt` now says where the file share lives
   (the AirStash layout is `/files/`).

If the stick has joined your home Wi‑Fi, use its LAN address instead: `python probe.py --host 192.168.x.y --login`
(user `owner`, your stick password).

## 2. Put the app on the stick

Plug the stick into the PC over USB and copy `unstuck.html` to its top level.

## 3. Use it

1. Phone: join the stick's Wi‑Fi.
2. In Chrome, open `http://172.25.63.1/files/unstuck.html`, **typing the `http://`**. Without it, Chrome tries
   HTTPS, and the stick only has plain HTTP (port 80).
3. Chrome menu → **Add to Home screen**. From then on it behaves like an app icon.

The PC uses the same address in Edge.

**If it doesn't load on the Pixel:** Android may route traffic over mobile data because the stick's Wi‑Fi has no
internet. Turn mobile data off while you use the stick.

**Settings** (sliders icon): override the WebDAV root, show hidden files, photo thumbnails, and a link to the stick's
own settings page (`/myconnect/`).

## Limits

- Plain HTTP, so there are no wake locks or share-sheet integration. Keep the screen on during long uploads.
- Chrome can't play every video codec, so use Download for anything it won't play.
- Creating folders over Wi‑Fi reportedly failed on some AirStash firmware. If it fails, the app shows the error.
- If the stick serves `.html` files as downloads instead of pages, this approach won't work. Rerun the probe with
  `unstuck.html` on the stick: it reports the Content-Type the stick uses. The fallback would be a native Android app.
