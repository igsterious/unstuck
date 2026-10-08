"""Ask a SanDisk Connect wireless stick what it speaks. Read-only: it never writes to the stick.

Run while this PC is on the stick's Wi-Fi, then reconnect to the internet and share probe-report.txt:
    python probe.py                          # direct Wi-Fi, stick at 172.25.63.1
    python probe.py --host 192.168.1.7 --login   # stick joined your home Wi-Fi (user "owner")
"""
import argparse
import datetime
import getpass
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

TIMEOUT = 6
PORTS = [21, 22, 23, 80, 139, 443, 445, 5000, 8000, 8080, 8200, 9000]
ROOTS = ["/", "/files/"]  # "/files/" is the AirStash layout these sticks are built on
SHOW_HEADERS = ["Server", "Content-Type", "Content-Length", "Content-Disposition", "Location",
                "WWW-Authenticate", "DAV", "Allow", "MS-Author-Via", "Accept-Ranges",
                "Access-Control-Allow-Origin"]
PROPFIND_BODY = (b'<?xml version="1.0" encoding="utf-8"?><d:propfind xmlns:d="DAV:"><d:prop>'
                 b'<d:resourcetype/><d:getcontentlength/><d:quota-available-bytes/></d:prop></d:propfind>')

report = []


def say(line=""):
    print(line)
    report.append(line)


def make_opener(host, user, password):
    if password is None:
        return urllib.request.build_opener()
    pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    pm.add_password(None, f"http://{host}/", user, password)
    return urllib.request.build_opener(urllib.request.HTTPDigestAuthHandler(pm),
                                       urllib.request.HTTPBasicAuthHandler(pm))


def call(opener, method, url, headers=None, body=None, limit=2_000_000):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            return r.status, r.headers, r.read(limit)
    except urllib.error.HTTPError as e:
        return e.code, e.headers, (e.read(limit) if e.fp else b"")
    except Exception as e:  # timeouts, refused connections, auth handler errors
        return None, None, f"{type(e).__name__}: {e}".encode()


def show(method, path, status, headers, body, snippet=True):
    say(f"{method} {path} -> {status if status is not None else 'NO ANSWER'}")
    if headers is not None:
        for name in SHOW_HEADERS:
            if headers.get(name):
                say(f"    {name}: {headers.get(name)}")
        if headers.get("Set-Cookie"):
            say("    Set-Cookie: (present)")
    if snippet and body:
        text = body[:300].decode("utf-8", "replace").replace("\r", "").replace("\n", " ")
        say(f"    body: {text}")


def parse_listing(body):
    ns = {"d": "DAV:"}
    root = ET.fromstring(body)
    out = []
    for resp in root.findall("d:response", ns):
        href = (resp.findtext("d:href", default="", namespaces=ns) or "").strip()
        is_dir = resp.find(".//d:collection", ns) is not None
        out.append((href, is_dir))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="172.25.63.1")
    ap.add_argument("--login", action="store_true", help="ask for the stick password (user 'owner')")
    ap.add_argument("--user", default="owner")
    args = ap.parse_args()
    password = getpass.getpass(f"Password for {args.user}: ") if args.login else None
    opener = make_opener(args.host, args.user, password)
    base = f"http://{args.host}"

    say(f"Unstuck probe | {datetime.datetime.now():%Y-%m-%d %H:%M} | host {args.host} | login {'yes' if password else 'no'}")
    say()

    say("== Open TCP ports ==")
    open_ports = []
    for port in PORTS:
        try:
            with socket.create_connection((args.host, port), timeout=1.5):
                open_ports.append(port)
        except OSError:
            pass
    say(f"open: {open_ports or 'none'}")
    if 80 not in open_ports:
        say("Port 80 is closed or unreachable. Is this PC on the stick's Wi-Fi?")
    say()

    say("== Web pages ==")
    for path in ["/", "/myconnect/", "/files/"]:
        show("GET", path, *call(opener, "GET", base + path, limit=4000))
    say()

    say("== WebDAV ==")
    found = None
    for path in ROOTS:
        show("OPTIONS", path, *call(opener, "OPTIONS", base + path), snippet=False)
        status, headers, body = call(opener, "PROPFIND", base + path,
                                     {"Depth": "1", "Content-Type": "application/xml"}, PROPFIND_BODY)
        show("PROPFIND", path, status, headers, body, snippet=status != 207)
        if status == 207 and found is None:
            found = (path, body)
    say()

    if found:
        path, body = found
        say(f"== Listing of {path} (first 25) ==")
        try:
            entries = parse_listing(body)
        except ET.ParseError as e:
            say(f"could not parse XML: {e}")
            entries = []
        for href, is_dir in entries[:25]:
            say(f"  {'DIR ' if is_dir else 'FILE'} {href}")
        say()

        files = [h for h, d in entries if not d]
        sample = next((h for h in files if h.lower().endswith("unstuck.html")), files[0] if files else None)
        if sample:
            say("== How a file is served (first byte only) ==")
            url = urllib.parse.urljoin(base + path, sample).replace(" ", "%20")
            show("GET", sample, *call(opener, "GET", url, {"Range": "bytes=0-0"}), snippet=False)
            if not sample.lower().endswith("unstuck.html"):
                say("(unstuck.html not on the stick yet; copy it over and rerun to check it is served as text/html)")
            say()

    say("== Verdict ==")
    if found:
        say(f"WebDAV root: {found[0]}")
    else:
        say(f"No WebDAV root answered PROPFIND at {ROOTS}. Send this report back for a closer look.")

    out = Path(__file__).with_name("probe-report.txt")
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
