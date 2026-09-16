BOT_TOKEN   = "8578966664:AAFu5H6RTjVGgDtUYZSd3y-yL92kgHlIj1c"

OWNER_ID    = 8928103975

GRANTED_IDS = set()

# ── PERSISTENT STORAGE (Render Disk mounted at /var/data) ──
DATA_DIR    = os.environ.get("LOQI_DATA_DIR", "/var/data")
os.makedirs(DATA_DIR, exist_ok=True)

COOKIE_OUT  = os.path.join(DATA_DIR, "cookies.txt")
PROXY_OUT   = os.path.join(DATA_DIR, "proxyhub.txt")

# ── COOKIE SETTINGS ──────────────────────────────────
COOKIE_WORKERS   = 200        # was 6000 — cloud-safe
COOKIE_MAX       = 20_000     # max per run

# ── PROXY SETTINGS ───────────────────────────────────
PROXY_ALIVE_CAP  = 2_000      # stop after this many alive
PROXY_TOTAL_CAP  = 2_000      # file output cap
PROXY_RAW_CAP    = 20_000     # raw scrape ceiling
PROXY_WORKERS    = 100        # was 1500 — cloud-safe
PROXY_TIMEOUT    = 2          # per-proxy check timeout (tight)
CONNECT_TIMEOUT  = 1          # connect phase timeout

# ── BOT SETTINGS ─────────────────────────────────────
NOTIFY_ON_START     = True
STATE_FILE          = os.path.join(DATA_DIR, "loqi_state.json")
LOG_FILE            = os.path.join(DATA_DIR, "loqi_activity.log")

USER_DAILY_QUOTA    = 2_000
USER_COOLDOWN_SEC   = 15
OWNER_DAILY_QUOTA   = 999_999

FLOOD_WINDOW_SEC    = 5
FLOOD_MAX_MSGS      = 15

FILE_TTL_SEC        = 600

PROGRESS_REFRESH_SEC = 0.4
SPINNER_FRAMES       = ["◐","◓","◑","◒"]

USER_QUOTA_OVERRIDE : dict = {}




import os, sys, re, json, time, random, threading, traceback
import datetime, tempfile, itertools, socket
from typing import Optional, List, Dict, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter

# tighten global socket default
socket.setdefaulttimeout(8)

# suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SOCKS support (PySocks) — required for socks4/socks5 proxy checks
try:
    import socks  # noqa: F401
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    print("[!] PySocks not installed — socks4/socks5 checks will fail silently")


VERSION    = "4.0.1"
AUTHOR_1   = "@LOQIXXV"
AUTHOR_2   = "@LOQIXXVV"
BUILD_DATE = "2026"




PENDING_USERS : Dict[int, dict] = {}
BANNED_IDS    : set             = set()
USER_USAGE    : Dict[int, dict] = {}
FLOOD_TRACK   : Dict[int, list] = {}
MUTED_UNTIL   : Dict[int, float] = {}




BASE_URL     = f"https://api.telegram.org/bot{BOT_TOKEN}"
POLL_TIMEOUT = 30
_offset: int = 0
_api_sess: Optional[requests.Session] = None
_api_pool   = HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=2)


def _sess() -> requests.Session:
    global _api_sess
    if _api_sess is None:
        _api_sess = requests.Session()
        _api_sess.mount("https://", _api_pool)
        _api_sess.mount("http://",  _api_pool)
    return _api_sess


def tg(method: str, **kw) -> dict:
    try:
        r = _sess().post(f"{BASE_URL}/{method}", json=kw, timeout=12)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tg_multipart(method: str, data: dict, files: dict) -> dict:
    try:
        r = _sess().post(f"{BASE_URL}/{method}", data=data, files=files, timeout=120)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_updates() -> List[dict]:
    global _offset
    res = tg("getUpdates", offset=_offset, timeout=POLL_TIMEOUT,
             allowed_updates=["message", "callback_query"])
    if not res.get("ok"):
        return []
    upds = res.get("result", [])
    if upds:
        _offset = upds[-1]["update_id"] + 1
    return upds




# ── shared cookie HTTP pool ──
_cookie_pool = HTTPAdapter(
    pool_connections=128,
    pool_maxsize=COOKIE_WORKERS,
    pool_block=False,
    max_retries=0,
)
_cookie_sess: Optional[requests.Session] = None
_cookie_sess_lock = threading.Lock()


def _cookie_session() -> requests.Session:
    global _cookie_sess
    if _cookie_sess is None:
        with _cookie_sess_lock:
            if _cookie_sess is None:
                s = requests.Session()
                s.mount("https://", _cookie_pool)
                s.mount("http://",  _cookie_pool)
                _cookie_sess = s
    return _cookie_sess


# ── shared proxy-check HTTP pool ──
_proxy_pool = HTTPAdapter(
    pool_connections=256,
    pool_maxsize=PROXY_WORKERS,
    pool_block=False,
    max_retries=0,
)
_proxy_src_sess: Optional[requests.Session] = None
_proxy_src_lock = threading.Lock()


def _proxy_src_session() -> requests.Session:
    global _proxy_src_sess
    if _proxy_src_sess is None:
        with _proxy_src_lock:
            if _proxy_src_sess is None:
                s = requests.Session()
                s.mount("https://", _proxy_pool)
                s.mount("http://",  _proxy_pool)
                _proxy_src_sess = s
    return _proxy_src_sess




def rkb(*rows, resize: bool = True, one_time: bool = False) -> dict:
    return {
        "keyboard"          : [[{"text": t} for t in row] for row in rows],
        "resize_keyboard"   : resize,
        "one_time_keyboard" : one_time,
    }


def rkb_remove() -> dict:
    return {"remove_keyboard": True}




KB_USER_MAIN = rkb(
    ["◈ GENERATE PROXY",   "◇ COOKIE GEN"],
    ["◈ MY QUOTA",         "◇ MY PROFILE"],
    ["◈ ABOUT"],
)

KB_USER_COOKIE = rkb(
    ["◈ GEN x100",   "◇ GEN x500"],
    ["◈ GEN x1000",  "◇ GEN x2000"],
    ["◈◈ MAIN MENU"],
)

KB_MAIN = rkb(
    ["◈ GENERATE PROXY",   "◇ COOKIE GEN"],
    ["◈ ADMIN PANEL",      "◇ USER MANAGER"],
    ["◈ MY ACCESS",        "◇ ABOUT"],
)

KB_ADMIN = rkb(
    ["◈ LIST USERS",   "◇ PENDING"],
    ["◈ BROADCAST",    "◇ BAN USER"],
    ["◈ UNBAN USER",   "◇ RESET QUOTA"],
    ["◈ GRANT USER",   "◇ REVOKE USER"],
    ["◈◈ MAIN MENU"],
)

KB_USER_MGR = rkb(
    ["◈ VIEW USER",    "◇ GRANT USER"],
    ["◈ BAN USER",     "◇ UNBAN USER"],
    ["◈ RESET QUOTA",  "◇ USER STATS"],
    ["◈◈ MAIN MENU"],
)

KB_PROXY = rkb(
    ["◈ QUICK GEN",      "◇ HTTP ONLY"],
    ["◈ SOCKS4",         "◇ SOCKS5"],
    ["◈ HTTPS ONLY",     "◇ ALL TYPES"],
    ["◈◈ MAIN MENU"],
)

KB_COOKIE = rkb(
    ["◈ GEN x100",   "◇ GEN x500"],
    ["◈ GEN x1000",  "◇ GEN x2000"],
    ["◈ GEN x5000",  "◇ GEN x10000"],
    ["◈ GEN x20000", "◇ MAIN MENU"],
    ["◈◈ MAIN MENU"],
)

KB_STOP = rkb(
    ["◈ STOP TASK"],
    ["◈◈ MAIN MENU"],
)

KB_BACK = rkb(["◈◈ MAIN MENU"])




def send(cid: int, text: str, kb=None, parse_mode: str = "HTML") -> dict:
    kw: dict = {
        "chat_id"                  : cid,
        "text"                     : text,
        "parse_mode"               : parse_mode,
        "disable_web_page_preview" : True,
    }
    if kb is not None:
        kw["reply_markup"] = kb
    return tg("sendMessage", **kw)


def send_doc(cid: int, path: str, caption: str = "") -> dict:
    with open(path, "rb") as fh:
        return tg_multipart(
            "sendDocument",
            data={"chat_id": cid, "caption": caption, "parse_mode": "HTML"},
            files={"document": (os.path.basename(path), fh, "text/plain")},
        )




LOGO = (
    "◈◈◈ L O Q I   S Y S T E M ◈◈◈\n"
    f"◇ v{VERSION}  //  {AUTHOR_1}\n"
    "◈ PROXY GEN + COOKIE GEN"
)

DENY = (
    "◈◈◈ A C C E S S   D E N I E D ◈◈◈\n"
    "◇ NO CLEARANCE FOR NODE\n"
    f"◈ CONTACT  {AUTHOR_2}"
)


def _box(title: str, lines: List[str]) -> str:
    out = [f"◈◈ {title} ◈◈", "──────────────────"]
    out += [f"  {l}" for l in lines]
    return "\n".join(out)


def _bar(v: int, t: int, w: int = 16) -> str:
    if t == 0:
        return "░" * w
    f = int(w * v / max(t, 1))
    return "█" * f + "░" * (w - f)




def is_granted(uid: int) -> bool:
    return uid == OWNER_ID or uid in GRANTED_IDS


def is_owner(uid: int) -> bool:
    return uid == OWNER_ID


def is_banned(uid: int) -> bool:
    return uid in BANNED_IDS




def load_state():
    global GRANTED_IDS, BANNED_IDS, PENDING_USERS, USER_USAGE
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        GRANTED_IDS   = set(d.get("granted", []))
        BANNED_IDS    = set(d.get("banned", []))
        PENDING_USERS = {int(k): v for k, v in d.get("pending", {}).items()}
        USER_USAGE    = {int(k): v for k, v in d.get("usage", {}).items()}
        print(f"  [+] STATE LOADED  //  granted={len(GRANTED_IDS)} "
              f"banned={len(BANNED_IDS)} pending={len(PENDING_USERS)}")
    except Exception as e:
        print(f"  [!] STATE LOAD FAIL: {e}")


def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "granted": list(GRANTED_IDS),
                "banned" : list(BANNED_IDS),
                "pending": {str(k): v for k, v in PENDING_USERS.items()},
                "usage"  : {str(k): v for k, v in USER_USAGE.items()},
            }, f, indent=2)
    except Exception as e:
        print(f"  [!] STATE SAVE FAIL: {e}")


def log_activity(uid: int, action: str, extra: str = ""):
    try:
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] uid={uid} action={action} {extra}\n")
    except Exception:
        pass




def get_quota(uid: int) -> int:
    if is_owner(uid):
        return OWNER_DAILY_QUOTA
    if uid in USER_QUOTA_OVERRIDE:
        return USER_QUOTA_OVERRIDE[uid]
    return USER_DAILY_QUOTA


def quota_left(uid: int) -> int:
    now = time.time()
    u   = USER_USAGE.get(uid)
    if not u or now >= u.get("reset_ts", 0):
        return get_quota(uid)
    return max(0, get_quota(uid) - u.get("count", 0))


def quota_consume(uid: int, amount: int):
    now = time.time()
    u   = USER_USAGE.get(uid) or {"count": 0, "reset_ts": now + 86400, "last_run": 0}
    if now >= u.get("reset_ts", 0):
        u = {"count": 0, "reset_ts": now + 86400, "last_run": 0}
    u["count"]    += amount
    u["last_run"]  = now
    USER_USAGE[uid] = u
    save_state()


def cooldown_remaining(uid: int) -> int:
    u = USER_USAGE.get(uid)
    if not u:
        return 0
    delta = USER_COOLDOWN_SEC - (time.time() - u.get("last_run", 0))
    return max(0, int(delta))


def flood_check(uid: int) -> bool:
    if is_owner(uid):
        return False
    if MUTED_UNTIL.get(uid, 0) > time.time():
        return True
    now    = time.time()
    bucket = FLOOD_TRACK.setdefault(uid, [])
    bucket[:] = [t for t in bucket if now - t < FLOOD_WINDOW_SEC]
    bucket.append(now)
    if len(bucket) > FLOOD_MAX_MSGS:
        MUTED_UNTIL[uid] = now + 30
        log_activity(uid, "FLOOD_MUTE", "30s")
        return True
    return False


def schedule_delete(path: str, delay: int = FILE_TTL_SEC):
    def _rm():
        time.sleep(delay)
        try:
            os.remove(path)
        except Exception:
            pass
    threading.Thread(target=_rm, daemon=True).start()




_state: Dict[int, Dict[str, Any]] = {}
_state_lock = threading.Lock()


def _set(cid: int, k: str, v: Any):
    with _state_lock:
        _state.setdefault(cid, {})[k] = v


def _get(cid: int, k: str) -> Any:
    with _state_lock:
        return _state.get(cid, {}).get(k)


def _del(cid: int, k: str):
    with _state_lock:
        _state.get(cid, {}).pop(k, None)


_user_menu: Dict[int, str] = {}


def set_menu(uid: int, name: str):
    _user_menu[uid] = name


def get_menu(uid: int) -> str:
    return _user_menu.get(uid, "main")




# ═══════════════════════════════════════════════════
#  PROXY GEN
# ═══════════════════════════════════════════════════

IP_RE = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:\s]+(\d{2,5})')

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "curl/8.7.1", "python-httpx/0.27.0",
]

SOURCES = [
    ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",    "HTTP"),
    ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",  "SOCKS4"),
    ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",  "SOCKS5"),
    ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",    "HTTP"),
    ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",  "SOCKS4"),
    ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",  "SOCKS5"),
    ("https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt","HTTP"),
    ("https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",    "SOCKS5"),
    ("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",     "HTTP"),
    ("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",    "HTTPS"),
    ("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",   "SOCKS4"),
    ("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",   "SOCKS5"),
    ("https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",       "HTTP"),
    ("https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",     "SOCKS5"),
    ("https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",         "HTTP"),
    ("https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",       "SOCKS5"),
    ("https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt","HTTP"),
    ("https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt", "HTTP"),
    ("https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt","SOCKS5"),
    ("https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000&simplified=true",   "HTTP"),
    ("https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks4&timeout=10000&simplified=true", "SOCKS4"),
    ("https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=10000&simplified=true", "SOCKS5"),
    ("https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt", "HTTP"),
    ("https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt",    "HTTP"),
    ("https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",  "SOCKS5"),
    ("https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt", "HTTPS"),
    ("https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt","SOCKS5"),
    ("https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http", "HTTP"),
    ("https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=socks5","SOCKS5"),
]

JUDGE = "http://httpbin.org/ip"

ANON_HDRS = {
    "x-forwarded-for", "x-real-ip", "via", "forwarded",
    "x-proxy-id", "proxy-connection", "x-forwarded-host",
    "x-client-ip", "client-ip", "true-client-ip",
    "cf-connecting-ip", "x-originating-ip",
}


def _ua() -> str:
    return random.choice(UA_POOL)


def _valid_ip(ip: str) -> bool:
    s = ip.split(".")
    return len(s) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in s)


def _valid_port(v) -> bool:
    try:
        return 1 <= int(v) <= 65535
    except (ValueError, TypeError):
        return False


def _parse(text: str, ptype: str) -> List[Tuple[str, int, str]]:
    out = []
    for m in IP_RE.finditer(text):
        ip, port = m.group(1), int(m.group(2))
        if _valid_ip(ip) and _valid_port(port):
            out.append((ip, port, ptype))
    return out


def _fetch_src(url: str, ptype: str) -> List[Tuple[str, int, str]]:
    try:
        r = _proxy_src_session().get(
            url,
            headers={"User-Agent": _ua()},
            timeout=12,
            verify=False,
        )
        return _parse(r.text, ptype)
    except Exception:
        return []


def _own_ip() -> str:
    for url in ["https://api.ipify.org", "http://httpbin.org/ip"]:
        try:
            r = requests.get(url, timeout=4, verify=False)
            m = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', r.text)
            if m:
                return m.group(0)
        except Exception:
            pass
    return ""


def _check_one(ip: str, port: int, ptype: str, my_ip: str) -> Optional[dict]:
    """Test a single proxy. SOCKS requires PySocks installed."""
    if ptype in ("SOCKS4", "SOCKS5") and not SOCKS_AVAILABLE:
        return None

    purl = f"{ptype.lower()}://{ip}:{port}"
    prx  = {"http": purl, "https": purl}
    t0   = time.monotonic()
    try:
        r   = requests.get(
            JUDGE,
            proxies=prx,
            timeout=(CONNECT_TIMEOUT, PROXY_TIMEOUT),
            headers={"User-Agent": _ua()},
            verify=False,
        )
        ms   = int((time.monotonic() - t0) * 1000)
        hdrs = {k.lower() for k in r.headers}
        if my_ip and my_ip in r.text:
            anon = "Transparent"
        elif any(h in hdrs for h in ANON_HDRS):
            anon = "Anonymous"
        else:
            anon = "Elite"
        return {"ip": ip, "port": port, "type": ptype, "latency": ms, "anon": anon}
    except Exception:
        return None


def scrape_sources(
    type_filter: Optional[str] = None,
    raw_cap: int = PROXY_RAW_CAP,
) -> List[Tuple[str, int, str]]:
    srcs = SOURCES if not type_filter else [
        (u, t) for u, t in SOURCES if t == type_filter.upper()
    ]
    seen, out = set(), []
    with ThreadPoolExecutor(max_workers=64) as ex:
        futs = {ex.submit(_fetch_src, url, pt): i
                for i, (url, pt) in enumerate(srcs)}
        for fut in as_completed(futs):
            for ip, port, pt in fut.result():
                k = f"{ip}:{port}"
                if k not in seen:
                    seen.add(k)
                    out.append((ip, port, pt))
                    if len(out) >= raw_cap:
                        ex.shutdown(wait=False, cancel_futures=True)
                        return out
    return out


def check_proxies(
    lst: List[Tuple[str, int, str]],
    cap: int = PROXY_ALIVE_CAP,
    prog=None,
    stop_evt: threading.Event = None,
) -> List[dict]:
    my_ip   = _own_ip()
    total   = min(len(lst), PROXY_RAW_CAP)
    done    = [0]
    alive_n = [0]
    lock    = threading.Lock()
    stop    = stop_evt or threading.Event()
    results : List[Optional[dict]] = []

    def _w(item):
        if stop.is_set():
            return
        ip, port, ptype = item
        res = _check_one(ip, port, ptype, my_ip)
        with lock:
            done[0] += 1
            if res is not None:
                alive_n[0] += 1
                results.append({**res, "alive": True})
                if alive_n[0] >= cap:
                    stop.set()
            if prog and (done[0] % 20 == 0 or stop.is_set()):
                prog(done[0], total, alive_n[0])

    with ThreadPoolExecutor(max_workers=PROXY_WORKERS) as ex:
        futs = [ex.submit(_w, item) for item in lst[:total]]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception:
                pass
            if stop.is_set():
                break

    return results[:cap]


def _write_proxy_file(lst: list) -> str:
    with open(PROXY_OUT, "w", encoding="utf-8") as f:
        for item in lst:
            if isinstance(item, dict):
                f.write(f"{item['ip']}:{item['port']}\n")
            else:
                ip, port, _ = item
                f.write(f"{ip}:{port}\n")
    return PROXY_OUT


PROXY_TYPE_MAP = {
    "◈ QUICK GEN"  : None,
    "◈ ALL TYPES"  : None,
    "◇ ALL TYPES"  : None,
    "◇ HTTP ONLY"  : "HTTP",
    "◈ HTTP ONLY"  : "HTTP",
    "◈ HTTPS ONLY" : "HTTPS",
    "◇ HTTPS ONLY" : "HTTPS",
    "◈ SOCKS4"     : "SOCKS4",
    "◇ SOCKS4"     : "SOCKS4",
    "◇ SOCKS5"     : "SOCKS5",
    "◈ SOCKS5"     : "SOCKS5",
}


def start_proxy_task(cid: int, uid: int, mode: str):
    if _get(cid, "proxy_thread") and _get(cid, "proxy_thread").is_alive():
        send(cid, "◈ PROXY TASK RUNNING\n◇ STOP IT FIRST", kb=KB_STOP)
        return

    ptype = PROXY_TYPE_MAP.get(mode, None)
    label = (ptype or "ALL").upper()

    if ptype in ("SOCKS4", "SOCKS5") and not SOCKS_AVAILABLE:
        send(cid,
             "◈ SOCKS UNAVAILABLE\n"
             "◇ PySocks not installed on host\n"
             "◈ add 'PySocks' to requirements.txt",
             kb=_main_kb(uid))
        return

    stop = threading.Event()
    _set(cid, "stop", stop)

    inline_cancel = {
        "inline_keyboard": [[
            {"text": "◈ CANCEL GEN", "callback_data": f"cancelgen:{uid}"}
        ]]
    }

    pm = tg("sendMessage",
            chat_id=cid,
            text=(
                f"◈ PROXY GEN  //  BOOT\n"
                f"◇ TYPE   : {label}\n"
                f"◈ TARGET : {PROXY_TOTAL_CAP:,}\n"
                f"◇ WORKERS: {PROXY_WORKERS}\n"
                f"◈ SCANNING SOURCES..."
            ),
            parse_mode="HTML",
            reply_markup=inline_cancel)

    msg_id = pm.get("result", {}).get("message_id") if pm.get("ok") else None
    spin   = itertools.cycle(SPINNER_FRAMES)

    def _edit(text: str):
        if msg_id:
            tg("editMessageText",
               chat_id=cid, message_id=msg_id,
               text=text,
               parse_mode="HTML",
               reply_markup=inline_cancel)

    def run():
        last_edit = [0.0]
        t0        = time.time()

        scrape_done = threading.Event()

        def _spin_scrape():
            while not scrape_done.is_set() and not stop.is_set():
                s = next(spin)
                _edit(
                    f"◈ PROXY GEN  //  {s}\n"
                    f"◇ TYPE   : {label}\n"
                    f"◈ SCRAPING SOURCES..."
                )
                time.sleep(0.5)

        sp = threading.Thread(target=_spin_scrape, daemon=True)
        sp.start()

        proxy_list = scrape_sources(type_filter=ptype)

        scrape_done.set()
        sp.join(timeout=1)

        if stop.is_set():
            send(cid, "◈ STOPPED", kb=_main_kb(uid))
            _del(cid, "proxy_thread"); _del(cid, "stop")
            return

        raw_count = len(proxy_list)
        _edit(
            f"◈ PROXY GEN  //  VALIDATE\n"
            f"◇ RAW : {raw_count:,} found\n"
            f"◈ CHECKING {min(raw_count, PROXY_TOTAL_CAP):,} proxies...\n"
            f"◇ WORKERS: {PROXY_WORKERS}"
        )

        def cp(done, total, alive):
            if stop.is_set():
                return
            now = time.time()
            if now - last_edit[0] < PROGRESS_REFRESH_SEC:
                return
            last_edit[0] = now
            s   = next(spin)
            bar = _bar(alive, PROXY_ALIVE_CAP, w=18)
            pct = int(alive * 100 / max(PROXY_ALIVE_CAP, 1))
            elapsed = now - t0
            rate    = done / elapsed if elapsed > 0 else 0
            _edit(
                f"◈ PROXY GEN  //  {s}  {label}\n"
                f"◇ ALIVE   : [{bar}] {pct}%\n"
                f"──────────────────\n"
                f"◈ ALIVE   : {alive:,}/{PROXY_ALIVE_CAP:,}\n"
                f"◇ CHECKED : {done:,}/{total:,}\n"
                f"──────────────────\n"
                f"◈ RATE    : ~{rate:0.0f}/s\n"
                f"◇ ELAPSED : {elapsed:0.1f}s"
            )

        checked = check_proxies(proxy_list, cap=PROXY_ALIVE_CAP, prog=cp, stop_evt=stop)

        path    = _write_proxy_file(checked)
        elapsed = round(time.time() - t0, 1)

        cap_txt = (
            f"◈ LOQI  //  {AUTHOR_2}\n"
            f"◇ TYPE    : {label}\n"
            f"◈ ALIVE   : {len(checked):,}\n"
            f"◇ ELAPSED : {elapsed}s\n"
            f"◈ FILE    : proxyhub.txt"
        )
        send_doc(cid, path, caption=cap_txt)
        schedule_delete(path)

        send(cid,
             _box("◈ PROXY GEN COMPLETE", [
                 f"◇ TYPE    : {label}",
                 f"◈ ALIVE   : {len(checked):,}",
                 f"◇ ELAPSED : {elapsed}s",
                 "◈ FILE    : proxyhub.txt  //  SENT",
             ]),
             kb=_main_kb(uid))

        _del(cid, "proxy_thread"); _del(cid, "stop")

    t = threading.Thread(target=run, daemon=True)
    _set(cid, "proxy_thread", t)
    t.start()


def generate_proxy_quick(cid: int, uid: int):
    start_proxy_task(cid, uid, "◈ QUICK GEN")




# ═══════════════════════════════════════════════════
#  COOKIE GEN — DATADOME/GARENA
# ═══════════════════════════════════════════════════

COOKIE_URL = "https://datadome.garena.com/js/"

COOKIE_PAYLOAD = (
    'jspl=QGQ0BVgjckhG9XFf_olrvPEwB5AKErtjUd6f_dtbCw6uU4mUnl4Ca5uJY9K_OWQfTtT2EcX852pDG2IId4gG5U65OppS7iwx7RfQ1zzKRMro56Xwcuu9Q_K16c69frRlWlLQd-n0p6XgiRXwusJv0AzdM9tBXrKAChlwUPvgd1086UwD5VEdfQXn-_xJN7-6-7Fs2LBt0A7vW4CPF6iCHCIKFJHbFFo8uTxvSdJL69AHKqqrRJ8oQCkfO_GrZiTFCXZAbGwdCqzkFEGFeBGH0RVAG_q7wmiKlII3zlcqZcRgoP2awfU6RjhvIeJToH5rTrby8SGuCZXLAGCG2tcCxraVYDQEL63p5anIGBrdTwdGVE6yL8B4vXNXLTIO0iq0AWjCksq599tQ38RAgo0tMl6cix0pOUwpigTNKY-4eIEEaQ2Cn_Nr9eXTrqRWZOaszlStMIE8M73ErsI_6dLXI5tcohL1NA0k6dPyVhurkMtYjUodgDN0EluJufLMKvH_D6-JT9xIebqCZ2zPv2eOO5wcMC1TyHFjR3NGwpJvD-YghfQUxdmFd3Xcjc41Rcp21CZ2HVsFZME-B8ppZ7AyU3Mn-ETydYWauETEamzkZynKSMKQTys-SrbONsKCbmQiGUxDumBKsPR8ODY87U_QKs3icJeXPheiBv-0w40kMiBU7KLYOrH0wCcGPO4pWS5bl9ju2KF3nMwD5V5AajCqdotm-JU7qAZxJiPAtU9xZmqr-mDQELX56jokfmqkX8v_4YZeAdx0VU96Rpj_-qdvhKpzm9OYZeJI-4VVLhXN200cEumhRfyVp5HZ3pUdUYxgp0ryCydj31kG8dLTDCKTIhMtsUo3bSypcbsE-xdz-P-gUNUYXcTN7uuekhuKwNIeEcTcLdw6udGartLTkTt4SmWxncPDzKwLh6qdhdRVAJIhlbeFY_OeIF4TkCPbGEv9xlN3MJFZccX097QLDT9niyMzxACRar3aPJDzZlaoyyr0asFkNu65-Hfj_XLYlSYET7vC-Sqgzo5016flXcuzKZvMfJp9Jk78GRUtYtVPHEJzMdU0SMcKTp8joR8Y_mmyHIOnoGer4TatyOfNCRF8XOJNdMwp3qSknYp_yfBSUa1Ij3WPtX9lg5kl50YJgNQPovYyCJU_Dwjty_KirEFgbUoOT7yr7w5pJc7yBC2n3wfTxiwmp-RsBwZXlk19UYDiGwWTMA5EfglURLVraue7Df36AEQV5QqBVupNtGpZFwPC5K9YJDG5DIlIMNfIL4X8chGhxCMV6nem-otHDi9JUkcVbTttqrJyXQ50FNfRwUt_ScqwsXVEBD26I-AD6xsdkqmCx60ehJMXiSywNE_Mjt9zG4TUoHKY95gpcXDSvcSVJ6W-rCAQ3M0vcgu5wcdEb1SXmBzUJf_rSJxZoFNPdZjgrQqVBByJKy2V7x4ywPpPPf83z0Y6B7gkW6RS7fUlT47SSjvtkXGYoRLn9zDcOtvX1TxxUXrDjw4H9T5n7zOy5Eao7BQ9fcDgZ1pyYH6soR9Ug2MsOX5cHCH5LMC7qZtDW0aFKLD76LNMcZfWxn_tiadU3JynnXwkZ8B70leGLWoe9azUJY0F_xgD6tgCKf1xxJQAtcuUU1PTHG_kIFhD_UrZiq4DKhIMZgvkSgwEvpYmHOnpRZMoqOn2T81bwz1jhDq3H0YJClW2y0Bzk_cvMEZOb05kS3cHr0fcVGnLkqxGWWsT9YVRbNueDhbZIoPfdiOpqn9ZTOpxKFxwEuEeKaPSfb6A7PUAHREieN9hpCdlmZwygPw3sHpK0jdD-hKUTiG3d-xOr2Tc9-QVtSy_mdR_rSdMDvXEJsVZJ33f6SaKsnsElaLd2vB8YZfUaTksujLUBqgxd4gSKUdcEZ-_-8huvk9MJFsw37KqHYVCCmdHzJe_KjC6GZx4UGskD1amFPKYTp7Q4H9U-RIflTDX3K8Pxced7Kx4W-7tDt8V5wj6ggRDK_wAZ_8fxpjrH7PhEyTTeJxB_bJ2Sigbjoi368mAoudRMkiChN66D8xap_nYUCtBkdFDZpThAv04leKOllua60DS5W1KL91x9CYMPmKQUWMHFVY6MqPaUsecHxDK1WujPkCnSGKpr0iiEHNpbC_5atdvXmS2dVjyih1fXxpnwW5-uyybBQKkhWXcI6HXC5ic6J4sBra17lvvBfff4sAw_FohvjPwNUCW4fUKz8qrLXYWuhTtsgzCdwXKnNbAJHFg5RPiAR3sDj6eIPJlRSv3foRh656t3015JAetowe7J2l7a_UBRmkQmZerVBEh8LCgU_BqE1Kz4ibHWHBPcBSRZVzCmfUXVUWWaYfAtBUIkz4n0TNDf3MjhksOpda2sKiJ97w7lZDPA_46hiFhfM6SP8y9GV7ToaXGxY-rsDGKxUXvCmk73l5YbxfaHfGhMpKxsSCaj40MFKyCNydU7Wn9Eha1bNW0CdenKkrTcJgpfgHkOKSjIFJMJzElcE1TWTYWxlqJqKHnMw9GmQFPe0JiYSf_NWtU2AFv7cjqCeYU6EOWN6yNMPCpIKHapVzCpwSxVmdywJYwFpte2kcu0RDICFHL1_ocSPF83azDEAcyb2sK6hu5WBR9mB-KGKnBzkktfo7TSvrq05d6jQInG3jxnFULmdvyUhIf7Wh9PoO48psknM85XQ3gCMMUlqyBw0TcsGaik-DLyFnoWo2bQW9vpPhmxO_wtQ6YBfQpIRsJlDexBaLWFX7KpWOr4wgX-0jviPLsXOGSWUQ-e6PxflfbEOB6hYdBL7uJhRO7QA8wsLvnUUxdLY7mxqzCJF2_l_O2a_Sdw7MId_KjEerVYj0VHm9svX7RdrrnS2DzbXyXzRGOy8l6OzQoDUAQRfyV2mjZgpYPxQry2G3P538x4zw-k_JNsy39rhjM0-uCTQ1d7YapQx3W20R3CxSPgk4tiu7sIKQxs-QpnHTKetaGW4MJEreDRZ_h8_oukyvaFPpItE9Yc8SIt1T-2RkAnDNXBA-g287V6lo6v_nNh7mGYC3Lx4qeG26aAsR3oX9SiSCuAp8Lyahw4Q2yPo4NTvsxLuY_b7SzMybfyQVXOCzHRx9VrQXWrTQ3iFvC1o49YQdta8tG1SA15bvhD5IpVcHi6HduW7SEll7Uk1l6hvg8GwwkDSsAqXa7Rsu7g5GL_hI-GaAP1R7VK3iD_TXLAnRoETWh56dMqw4l_QqKCggCA-WSj3WKIXcDnuTtnZragribanEi7_F_DL2q0OHuD1KqzY7c8eouznfNmOHASe_GwrcIVMr-XT1Rf5huXlnQ1l8eqgqQR1oQkc_K3ihzMJM8L_Vhd0_KLR4-1ICSL1QdOSboLjH2nVuzc7je6FyRyNOUBSZU1sT5caMBnNllX4FRwduqGSje9X6XY8a5vYd5Kpgp3AyrPv8gVLExQguIGFa-4IbLmjsM1B6UEj4VTcFM8RJ221_n3KuVDl5X-_g2rW3GHP8zUPlkYOmlJ5Z0GQ8ubDGe14nAAA9H-Rop4TaNFkMup3EOr3Ec6_GvPxzET3lcdP9qF6FdYmY9Ejhr18yGFZfDf3w3y_K7PRfRkEsdliiCSvYosgssIs8jB2VzL3HEbwwjCz_aKZT0W9NYkBxAi8cZf676phGbEJ50hoYRSIwJJU8Tu0A0hrUnkvw3Woc-88SWO4ZlpAxUZXiuFtfhQxbO1SXxByBTaWdJ9GkxriyF0zg8TQeOoZFi5ad-FLPfriP1DitrrITsJKPN-hpORrNd0yjGf9D_-9vD4Mvm8IzkEbzNpX4VHVhrwFLlpk6aeME9q01T-CX5PqmkoVk4cZihcoQe-i96Mcy-umgshZdAyxckIjGFv_vWQYxghUwNTMOotHXbx58RJQQ8QY2FoSyVbTpUXM7yL8_xLT5mh4N_qx66Gpw0t7mSUDSIB992q3vugspQWO2UKy1j5gw8UzlmgYvNTOcR5pRav6Zp-we0685y8IdrKbwH0dm6ZnSSmAlw0WD-YveLDEWJgcFYE94fkZ83czXgJb7I-JrLiyHk7K7aSmXkII-60Fm1ksQayHbJsvnzmXzbaWtp2tgCmM1hqahSnXN_eaUTaDumK9-e-iobjOXcYPERFwssEA_zrRvXFdoiINmqtwVi4so7quVBEMsjyOPsN4WjfgJo39il-yBMVlpBYMxZjZrzoxBU6RaNq3Vn2xz9PTIUnpqFm1V2wAdH-gJNvravSZxWRd8e2ub5SMBJEddGHZMmY2oaxlI1XgsNg9FLFm78WqOP3oqvjpoNPAUeKu6IbDRtuwKEZEQjBCYrih9zELsUYUD2vDr9r4JxSY2_SRx1Istk-z6cm6blTyybiBsrT3t-uULM4VHKBQGcOKF10aeZJkvclKSxI-kUIu97evHkFKcXG6mWRGXt0rzkPCzm12Dm6dLdkS1p4nQGGmlxNf913DXotB7EsBc62ddIO7O1KJTWRCIxBnFmVl2smSMkZ34xaqLcoM17k9zqA8RMYUpUjfnIjhCQCNtRpdJvVsyFVLujlhgBnkNg5ev27PYGgHzEQHeDsNOAMJOf-lzxKn8stzPJp0OjpCNsWcYW6NhbgwnS4y4zzsjGNWSSO8MFpeG-5v2B2ASKsex0TGFmRSsZIP6N_2nJP28QWQEDWL08qKJ1TyrR7P-XbpOm8UmHb2beK56hMHafXmISVakfP0dS3Oh224nYa6QMn8yYiNgvzDKik4bHHiIftnLcCaRZC8FIiioBnj69Ya0tWe0aXwgkNDiTj8ko60jsSFA6x0Y9uAQupjTGjAXkIUGRbfSa-h3qYe4dPiDb0OwpUM7beqkblKvbqNBqy8So5F8MPNaDAS7L0syTp2ugVvp0iwZCAB-4xWJqyToyzNJVrGU9K8jlX7qbh7d7NwqohBq1UT_wEjl2C4Vk1domhlfZeaUPfpMAwTMSLlogvpqsr5dcygjtcH2RL0xvorT9RItWdExi0ZEgZYR2e16sctZHqJdmHDLrcgfxHXV9XpX3I0M20fJe2yV1w5m_Kl5EDs72f8JcrKNvTgCGRa1Jmxu_3yXcWJ1hQSBFauGi6dXnBFk87FUjIewCpy6744anPrNjdBW9zZPAUN4t2E3ehNZKxRddzl9sGlUYR6xkDaKXCthj1sAwjuLfwrYaynulYXCzH9BymnYqWrBGEKQ6SP5OR7uxPfQVRnDPFqXP1kfZlwTNPcDGXUb-EWVxR9w7H6QVPTROp9nkdf_SSQ3u88x1gnD_SVwfwsIh9NXt1L-JidK1DEV2I72FcTxVH4sM4Ch8q8i6x1_Soo6CGnXNKFGUZE2xg8jo2G8O_pwSbOTULG5dXtt_4nFyCWsRhDeFBn7bvguKg0sl4cBHkD_Li8rN-3H8hFw137Q3N2v39DEXGfJEB0et2PX-4r1gVA7qqUHUcNwdvy6ZOcRQg_NYvGgcGWoQde5eAHIQ0avvSQGUHFEUb6NuiiOcKoDXipJtsbNi2UR3pIhfr8YsFQTqdz3NF2zo9IEvY0uds1VowMJAIBF001MlYmMQ3iAVutCrJnMehTpDFZztqzUJ917m72Snc2NA2LSPObaq5M6wiPpLnscG1yCJlVo52xazMfcn3jeRg-RoOAK-mHBSQ-W7oD'
    '&eventCounters={"mousemove":4,"pointermove":1,"click":4,"scroll":0,"touchstart":4,"touchend":4,"touchmove":0,"keydown":2,"keyup":2}'
    '&jsType=le'
    '&cid=ROxC_oAlhyCRnDuIxNT_gKAsk8IOlYBFcrRuxfab_kt77Rrbyhu8xH21Zm6rN1hshR8R1vYl6Mlq8rC8fFRV7M9NV8EwyGm_EF0dY2yiLhcSRRttpELcrtVbTtmEMGG2'
    '&ddk=AE3F04AD3F0D3A462481A337485081'
    '&Referer=https%3A%2F%2Fsso.garena.com%2Funiversal%2Flogin%3Fapp_id%3D10100%26redirect_uri%3Dhttps%253A%252F%252Faccount.garena.com%252F%26locale%3Den-PH'
    '&request=%2Funiversal%2Flogin%3Fapp_id%3D10100%26redirect_uri%3Dhttps%253A%252F%252Faccount.garena.com%252F%26locale%3Den-PH'
    '&responsePage=origin'
    '&ddv=5.8.0'
)

COOKIE_PAYLOAD_BYTES = COOKIE_PAYLOAD.encode("utf-8")


def _cookie_hdrs() -> dict:
    ts  = int(time.time())
    rid = random.randint(1_000_000_000, 9_999_999_999)
    return {
        "content-length"    : "6374",
        "sec-ch-ua"         : '"Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-platform": '"Android"',
        "sec-ch-ua-mobile"  : "?1",
        "user-agent"        : "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "content-type"      : "application/x-www-form-urlencoded;charset=UTF-8",
        "accept"            : "*/*",
        "origin"            : "https://sso.garena.com",
        "sec-fetch-site"    : "same-site",
        "sec-fetch-mode"    : "no-cors",
        "sec-fetch-dest"    : "empty",
        "referer"           : "https://sso.garena.com/",
        "accept-encoding"   : "gzip, deflate, br",
        "accept-language"   : "en-PH,en-US;q=0.9,en;q=0.8",
        "cookie"            : f"_ga_1M7M9L6VPX=GS2.1.s{ts}$o21$g1$t{ts}$j53$l0$h0; _ga=GA1.1.{rid}.{ts}",
    }


def _fetch_cookie() -> Optional[str]:
    sess = _cookie_session()
    try:
        r = sess.post(
            COOKIE_URL,
            headers=_cookie_hdrs(),
            data=COOKIE_PAYLOAD_BYTES,
            timeout=(CONNECT_TIMEOUT, 0.08),
            verify=False,
        )
        if r.status_code != 200:
            return None
        d = r.json()
        if d.get("status") == 200 and "cookie" in d:
            c = d["cookie"]
            if "=" in c and ";" in c:
                return c.split(";")[0].split("=")[1]
            return c
    except Exception:
        pass
    return None


def generate_cookies(
    count: int,
    prog=None,
    stop_evt: threading.Event = None,
) -> List[str]:
    result  : List[str] = []
    lock     = threading.Lock()
    stop     = stop_evt or threading.Event()
    attempted = [0]
    t0        = time.time()

    n_threads = min(COOKIE_WORKERS, max(count * 3, 200))

    barrier = threading.Barrier(n_threads, timeout=10)

    fh      = open(COOKIE_OUT, "w", encoding="utf-8")
    fh_lock = threading.Lock()

    def worker():
        try:
            barrier.wait()
        except Exception:
            pass

        while not stop.is_set():
            c = _fetch_cookie()
            with lock:
                attempted[0] += 1
                if c and len(result) < count:
                    result.append(c)
                    done_n = len(result)
                    att_n  = attempted[0]
                    with fh_lock:
                        fh.write(f"datadome={c}\n")
                        fh.flush()
                    if done_n >= count:
                        stop.set()
                        return
                    if prog and done_n % 25 == 0:
                        prog(done_n, att_n, count, time.time() - t0)
                else:
                    att_n = attempted[0]
                    if prog and att_n % 100 == 0:
                        prog(len(result), att_n, count, time.time() - t0)

    threads = [
        threading.Thread(target=worker, daemon=True)
        for _ in range(n_threads)
    ]
    for t in threads:
        t.start()

    deadline = time.time() + 300
    while not stop.is_set() and time.time() < deadline:
        if prog:
            with lock:
                prog(len(result), attempted[0], count, time.time() - t0)
        time.sleep(0.15)

    stop.set()
    for t in threads:
        t.join(timeout=1.0)

    try:
        fh.close()
    except Exception:
        pass

    return result[:count]




COOKIE_COUNTS = {
    "◈ GEN x100"   : 100,
    "◇ GEN x500"   : 500,
    "◈ GEN x1000"  : 1_000,
    "◇ GEN x2000"  : 2_000,
    "◈ GEN x5000"  : 5_000,
    "◇ GEN x10000" : 10_000,
    "◈ GEN x20000" : 20_000,
}


def start_cookie_task(cid: int, uid: int, mode: str):
    if _get(cid, "cookie_thread") and _get(cid, "cookie_thread").is_alive():
        send(cid, "◈ COOKIE TASK RUNNING\n◇ STOP IT FIRST", kb=KB_STOP)
        return

    cool = cooldown_remaining(uid)
    if cool > 0:
        send(cid, f"◈ COOLDOWN ACTIVE\n◇ WAIT {cool}s", kb=_main_kb(uid))
        return

    count = COOKIE_COUNTS.get(mode, 100)
    count = min(count, COOKIE_MAX)

    if not is_owner(uid):
        left = quota_left(uid)
        if left <= 0:
            send(cid, "◈ DAILY QUOTA EXHAUSTED\n◇ TRY AGAIN TOMORROW", kb=KB_USER_MAIN)
            return
        if count > left:
            count = left
            send(cid, f"◇ CAPPED TO REMAINING QUOTA: {count}")

    quota_consume(uid, count)
    log_activity(uid, "COOKIE_GEN", f"count={count}")

    label = f"x{count:,}"
    stop  = threading.Event()
    _set(cid, "stop", stop)

    inline_cancel = {
        "inline_keyboard": [[
            {"text": "◈ CANCEL GEN", "callback_data": f"cancelgen:{uid}"}
        ]]
    }

    pm = tg("sendMessage",
            chat_id=cid,
            text=(
                f"◈ COOKIE GEN  //  BOOT\n"
                f"◇ COUNT   : {count:,}\n"
                f"◈ TARGET  : DATADOME  //  GARENA\n"
                f"◇ THREADS : {min(COOKIE_WORKERS, max(count*3,200))}\n"
                f"◈ INITIALIZING..."
            ),
            parse_mode="HTML",
            reply_markup=inline_cancel)

    msg_id = pm.get("result", {}).get("message_id") if pm.get("ok") else None
    spin   = itertools.cycle(SPINNER_FRAMES)

    def _edit(text: str):
        if msg_id:
            tg("editMessageText",
               chat_id=cid, message_id=msg_id,
               text=text,
               parse_mode="HTML",
               reply_markup=inline_cancel)

    def run():
        t_start   = time.time()
        last_edit = [0.0]

        def prog(success, attempted, total, elapsed):
            now = time.time()
            if now - last_edit[0] < PROGRESS_REFRESH_SEC and success < total:
                return
            last_edit[0] = now
            s    = next(spin)
            bar  = _bar(success, total, w=18)
            pct  = int(success * 100 / max(total, 1))
            rate = success / elapsed if elapsed > 0 else 0
            eta  = (f"{int((total - success) / rate)}s"
                    if rate > 0 and success < total else
                    "DONE" if success >= total else "—")
            _edit(
                f"◈ COOKIE GEN  //  {label}\n"
                f"◇ TARGET  : DATADOME / GARENA\n"
                f"──────────────────\n"
                f"◈ {s} HARVEST : [{bar}] {pct}%\n"
                f"◇ COUNT   : {success:,}/{total:,}\n"
                f"──────────────────\n"
                f"◈ REQUESTS: {attempted:,}\n"
                f"◇ RATE    : ~{rate:0.1f}/s\n"
                f"◈ ETA     : {eta}\n"
                f"◇ ELAPSED : {elapsed:0.1f}s\n"
                f"──────────────────\n"
                f"◈ THREADS : {min(COOKIE_WORKERS, max(count*3,200))}"
            )

        cookies = generate_cookies(count, prog=prog, stop_evt=stop)
        elapsed = round(time.time() - t_start, 1)
        rate_avg = int(len(cookies) / max(elapsed, 1))

        cap_txt = (
            f"◈ LOQI  //  {AUTHOR_2}\n"
            f"◇ TYPE    : DATADOME COOKIE\n"
            f"◈ COUNT   : {len(cookies):,}\n"
            f"◇ ELAPSED : {elapsed}s\n"
            f"◈ AVG RATE: ~{rate_avg}/s"
        )
        send_doc(cid, COOKIE_OUT, caption=cap_txt)
        schedule_delete(COOKIE_OUT)

        send(cid,
             _box("◈ COOKIE GEN COMPLETE", [
                 f"◇ HARVESTED: {len(cookies):,}",
                 f"◈ ELAPSED  : {elapsed}s",
                 f"◇ AVG RATE : ~{rate_avg}/s",
                 "◈ FILE     : cookies.txt  //  SENT",
             ]),
             kb=KB_COOKIE if is_owner(uid) else KB_USER_COOKIE)

        _del(cid, "cookie_thread")
        _del(cid, "stop")

    t = threading.Thread(target=run, daemon=True)
    _set(cid, "cookie_thread", t)
    t.start()




def _main_kb(uid: int):
    return KB_MAIN if is_owner(uid) else KB_USER_MAIN


def cmd_start(msg: dict):
    cid  = msg["chat"]["id"]
    uid  = msg["from"]["id"]
    name = msg["from"].get("first_name", "OPERATOR")

    if is_banned(uid):
        send(cid, "◈ NODE BANNED\n◇ CONTACT OWNER")
        return

    if not is_granted(uid):
        send(cid, DENY)
        notify_owner_new_user(msg)
        return

    set_menu(uid, "main")
    role = "OWNER" if is_owner(uid) else "USER"
    send(cid,
         f"{LOGO}\n\n"
         f"◇ WELCOME, <b>{name}</b>\n"
         f"◈ ROLE  : {role}\n"
         f"◇ QUOTA : {quota_left(uid):,} cookies left today\n"
         f"◈ SELECT MODULE",
         kb=_main_kb(uid))


def cmd_main_menu(cid: int, uid: int):
    set_menu(uid, "main")
    send(cid,
         f"{LOGO}\n"
         f"◇ QUOTA : {quota_left(uid):,}\n"
         f"◈ SELECT MODULE",
         kb=_main_kb(uid))


def show_proxy_menu(cid: int, uid: int):
    set_menu(uid, "proxy")
    send(cid,
         _box("◈ PROXY GENERATOR", [
             f"◇ CAP     : {PROXY_TOTAL_CAP:,}",
             f"◈ WORKERS : {PROXY_WORKERS}",
             f"◇ TIMEOUT : {PROXY_TIMEOUT}s",
             "◈ SELECT TYPE BELOW",
         ]),
         kb=KB_PROXY)


def show_cookie_menu(cid: int, uid: int):
    set_menu(uid, "cookie")
    left = quota_left(uid)
    cap  = get_quota(uid)
    kb   = KB_COOKIE if is_owner(uid) else KB_USER_COOKIE
    send(cid,
         _box("◇ COOKIE GENERATOR", [
             f"◈ THREADS  : {COOKIE_WORKERS}",
             f"◇ DAILY CAP: {cap:,}",
             f"◈ LEFT     : {left:,}",
             f"◇ COOLDOWN : {cooldown_remaining(uid)}s",
             f"◈ MAX/RUN  : {COOKIE_MAX:,}",
             "◇ SELECT BATCH SIZE",
         ]),
         kb=kb)


def show_access(cid: int, uid: int):
    lines = [
        f"◈ YOUR UID     : {uid}",
        f"◇ OWNER        : {OWNER_ID}",
        f"◈ GRANTED      : {len(GRANTED_IDS)} users",
        f"◇ STATUS       : {'OWNER' if is_owner(uid) else 'GRANTED'}",
    ]
    send(cid, _box("◈ ACCESS NODE", lines), kb=_main_kb(uid))


def show_quota(cid: int, uid: int):
    left  = quota_left(uid)
    cap   = get_quota(uid)
    used  = cap - left
    bar   = _bar(used, cap, w=16)
    cool  = cooldown_remaining(uid)
    send(cid,
         _box("◈ QUOTA STATUS", [
             f"◇ DAILY CAP : {cap:,}",
             f"◈ USED      : {used:,}",
             f"◇ LEFT      : {left:,}",
             f"◈ [{bar}]",
             f"◇ COOLDOWN  : {cool}s",
         ]),
         kb=_main_kb(uid))


def show_about(cid: int):
    send(cid,
         _box("◈ ABOUT LOQI", [
             f"◇ VERSION  : {VERSION}",
             f"◈ BUILD    : {BUILD_DATE}",
             f"◇ AUTHOR   : {AUTHOR_1}",
             f"◈ CONTACT  : {AUTHOR_2}",
             "◇ PROXY GEN + COOKIE GEN",
             f"◈ PROXY CAP: {PROXY_TOTAL_CAP:,}",
             f"◇ COOKIE   : up to {COOKIE_MAX:,}/run",
             f"◈ SOCKS    : {'ON' if SOCKS_AVAILABLE else 'OFF'}",
         ]))


def show_admin_panel(cid: int, uid: int):
    if not is_owner(uid):
        send(cid, DENY)
        return
    set_menu(uid, "admin")
    send(cid, _box("◈ ADMIN PANEL", [
        f"◇ GRANTED : {len(GRANTED_IDS)}",
        f"◈ BANNED  : {len(BANNED_IDS)}",
        f"◇ PENDING : {len(PENDING_USERS)}",
    ]), kb=KB_ADMIN)


def show_user_mgr(cid: int, uid: int):
    if not is_owner(uid):
        send(cid, DENY)
        return
    set_menu(uid, "user_mgr")
    send(cid, _box("◈ USER MANAGER", [
        f"◇ GRANTED : {len(GRANTED_IDS)}",
        f"◈ BANNED  : {len(BANNED_IDS)}",
    ]), kb=KB_USER_MGR)


def list_all_users(cid: int):
    lines = [f"◈ GRANTED USERS ({len(GRANTED_IDS)})"]
    for g in sorted(GRANTED_IDS):
        lines.append(f"  ◇ {g}")
    if not GRANTED_IDS:
        lines.append("  ◇ none")
    send(cid, "\n".join(lines))


def list_pending(cid: int):
    lines = [f"◈ PENDING ({len(PENDING_USERS)})"]
    for uid, info in PENDING_USERS.items():
        name = info.get("name", "?")
        lines.append(f"  ◇ {uid}  {name}")
    if not PENDING_USERS:
        lines.append("  ◇ none")
    send(cid, "\n".join(lines))


def show_user_stats(cid: int):
    lines = [f"◈ USER STATS ({len(USER_USAGE)} active)"]
    for uid, u in sorted(USER_USAGE.items()):
        lines.append(f"  ◇ {uid}  used={u.get('count',0):,}")
    if not USER_USAGE:
        lines.append("  ◇ none")
    send(cid, "\n".join(lines))


def show_proxy_status(cid: int):
    send(cid, _box("◈ PROXY STATUS", [
        f"◇ CAP     : {PROXY_TOTAL_CAP:,}",
        f"◈ WORKERS : {PROXY_WORKERS}",
        f"◇ TIMEOUT : {PROXY_TIMEOUT}s",
        f"◈ SOURCES : {len(SOURCES)}",
    ]))


def notify_owner_new_user(msg: dict):
    uid  = msg["from"]["id"]
    name = msg["from"].get("first_name", "?")
    user = msg["from"].get("username", "")
    cid  = msg["chat"]["id"]

    PENDING_USERS[uid] = {"name": name, "chat_id": cid, "username": user}
    save_state()

    inline = {
        "inline_keyboard": [[
            {"text": "✓ GRANT", "callback_data": f"grant:{uid}"},
            {"text": "✗ IGNORE", "callback_data": f"ignore:{uid}"},
            {"text": "⊗ BAN",   "callback_data": f"ban:{uid}"},
        ]]
    }
    tg("sendMessage",
       chat_id=OWNER_ID,
       text=(
           f"◈ NEW USER REQUEST\n"
           f"◇ NAME : {name}\n"
           f"◈ USER : @{user}\n"
           f"◇ UID  : {uid}"
       ),
       parse_mode="HTML",
       reply_markup=inline)


def prompt_grant(cid, uid):
    _set(cid, "awaiting", "grant")
    send(cid, "◈ SEND UID TO GRANT", kb=KB_BACK)


def prompt_revoke(cid, uid):
    _set(cid, "awaiting", "revoke")
    send(cid, "◈ SEND UID TO REVOKE", kb=KB_BACK)


def prompt_ban(cid, uid):
    _set(cid, "awaiting", "ban")
    send(cid, "◈ SEND UID TO BAN", kb=KB_BACK)


def prompt_unban(cid, uid):
    _set(cid, "awaiting", "unban")
    send(cid, "◈ SEND UID TO UNBAN", kb=KB_BACK)


def prompt_reset(cid, uid):
    _set(cid, "awaiting", "reset")
    send(cid, "◈ SEND UID TO RESET QUOTA", kb=KB_BACK)


def prompt_broadcast(cid, uid):
    _set(cid, "awaiting", "broadcast")
    send(cid, "◈ SEND BROADCAST MESSAGE", kb=KB_BACK)


def do_grant(cid, uid, text):
    try:
        t = int(text.strip())
    except ValueError:
        send(cid, "◇ INVALID UID", kb=KB_ADMIN)
        return
    GRANTED_IDS.add(t)
    BANNED_IDS.discard(t)
    PENDING_USERS.pop(t, None)
    save_state()
    log_activity(uid, "GRANT", f"target={t}")
    send(cid, f"◈ GRANTED {t}", kb=KB_ADMIN)
    _del(cid, "awaiting")


def do_revoke(cid, uid, text):
    try:
        t = int(text.strip())
    except ValueError:
        send(cid, "◇ INVALID UID", kb=KB_ADMIN)
        return
    GRANTED_IDS.discard(t)
    save_state()
    log_activity(uid, "REVOKE", f"target={t}")
    send(cid, f"◈ REVOKED {t}", kb=KB_ADMIN)
    _del(cid, "awaiting")


def do_ban(cid, uid, text):
    try:
        t = int(text.strip())
    except ValueError:
        send(cid, "◇ INVALID UID", kb=KB_ADMIN)
        return
    BANNED_IDS.add(t)
    GRANTED_IDS.discard(t)
    save_state()
    log_activity(uid, "BAN", f"target={t}")
    send(cid, f"◈ BANNED {t}", kb=KB_ADMIN)
    _del(cid, "awaiting")


def do_unban(cid, uid, text):
    try:
        t = int(text.strip())
    except ValueError:
        send(cid, "◇ INVALID UID", kb=KB_ADMIN)
        return
    BANNED_IDS.discard(t)
    save_state()
    log_activity(uid, "UNBAN", f"target={t}")
    send(cid, f"◈ UNBANNED {t}", kb=KB_ADMIN)
    _del(cid, "awaiting")


def do_reset(cid, uid, text):
    try:
        t = int(text.strip())
    except ValueError:
        send(cid, "◇ INVALID UID", kb=KB_ADMIN)
        return
    USER_USAGE.pop(t, None)
    save_state()
    log_activity(uid, "RESET_QUOTA", f"target={t}")
    send(cid, f"◈ QUOTA RESET {t}", kb=KB_ADMIN)
    _del(cid, "awaiting")


def do_broadcast(cid, uid, msg):
    body = msg.get("text", "").strip()
    sent, fail = 0, 0
    for g in list(GRANTED_IDS):
        if g == OWNER_ID:
            continue
        r = send(g, f"◈ BROADCAST FROM OWNER\n\n{body}")
        if r.get("ok"):
            sent += 1
        else:
            fail += 1
    send(cid, f"◈ BROADCAST DONE\n◇ SENT {sent}\n◈ FAIL {fail}", kb=KB_ADMIN)
    log_activity(uid, "BROADCAST", f"sent={sent}")
    _del(cid, "awaiting")


def do_stop(cid: int, uid: int):
    stop = _get(cid, "stop")
    if stop:
        stop.set()
    send(cid, "◈ STOP SIGNAL SENT\n◇ TASK WINDING DOWN...", kb=_main_kb(uid))
    set_menu(uid, "main")




def answer_cb(cb_id: str, text: str = "", alert: bool = False):
    tg("answerCallbackQuery", callback_query_id=cb_id,
       text=text, show_alert=alert)


def handle_callback(cb: dict):
    uid   = cb["from"]["id"]
    cid   = cb["message"]["chat"]["id"]
    cb_id = cb["id"]
    data  = cb.get("data", "")

    if data.startswith("cancelgen:"):
        try:
            target = int(data.split(":", 1)[1])
        except ValueError:
            answer_cb(cb_id, "BAD DATA", alert=True)
            return
        if uid != target and uid != OWNER_ID:
            answer_cb(cb_id, "NOT YOUR TASK", alert=True)
            return
        stop = _get(cid, "stop")
        if stop:
            stop.set()
            answer_cb(cb_id, "◈ CANCEL SENT")
            tg("editMessageText",
               chat_id=cid,
               message_id=cb["message"]["message_id"],
               text="◈ CANCELLED\n◇ TASK WINDING DOWN...",
               parse_mode="HTML")
            log_activity(uid, "CANCEL", f"cid={cid}")
        else:
            answer_cb(cb_id, "NO ACTIVE TASK", alert=True)
        return

    if uid != OWNER_ID:
        answer_cb(cb_id, "OWNER ONLY", alert=True)
        return
    if ":" not in data:
        answer_cb(cb_id)
        return

    action, target = data.split(":", 1)
    try:
        t_uid = int(target)
    except ValueError:
        answer_cb(cb_id, "BAD UID", alert=True)
        return

    info = PENDING_USERS.get(t_uid, {})
    mid  = cb["message"]["message_id"]

    if action == "grant":
        GRANTED_IDS.add(t_uid)
        BANNED_IDS.discard(t_uid)
        PENDING_USERS.pop(t_uid, None)
        save_state()
        answer_cb(cb_id, "GRANTED")
        tg("editMessageText", chat_id=cid, message_id=mid,
           text=f"◈ GRANTED  //  UID {t_uid}", parse_mode="HTML")
        if info.get("chat_id"):
            send(info["chat_id"],
                 f"◈ ACCESS GRANTED\n◇ USE /start TO BEGIN\n"
                 f"◈ DAILY QUOTA: {USER_DAILY_QUOTA:,}")
        log_activity(uid, "GRANT", f"target={t_uid}")

    elif action == "ignore":
        answer_cb(cb_id, "IGNORED")
        tg("editMessageText", chat_id=cid, message_id=mid,
           text=f"◈ IGNORED  //  UID {t_uid}", parse_mode="HTML")
        log_activity(uid, "IGNORE", f"target={t_uid}")

    elif action == "ban":
        BANNED_IDS.add(t_uid)
        GRANTED_IDS.discard(t_uid)
        PENDING_USERS.pop(t_uid, None)
        save_state()
        answer_cb(cb_id, "BANNED")
        tg("editMessageText", chat_id=cid, message_id=mid,
           text=f"◈ BANNED  //  UID {t_uid}", parse_mode="HTML")
        log_activity(uid, "BAN", f"target={t_uid}")




def handle_message(msg: dict):
    uid  = msg["from"]["id"]
    cid  = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if is_banned(uid):
        send(cid, "◈ YOU ARE BANNED")
        return
    if flood_check(uid):
        return

    if text in ("/start", "/menu"):
        cmd_start(msg)
        return

    if not is_granted(uid):
        send(cid, DENY)
        notify_owner_new_user(msg)
        return

    if text == "/me":    show_access(cid, uid);  return
    if text == "/quota": show_quota(cid, uid);   return

    if text == "/users":
        if not is_owner(uid): send(cid, DENY); return
        list_all_users(cid); return

    if text == "/pending":
        if not is_owner(uid): send(cid, DENY); return
        list_pending(cid); return

    if text == "/banned":
        if not is_owner(uid): send(cid, DENY); return
        lines = [f"◈ BANNED ({len(BANNED_IDS)})"]
        for b in sorted(BANNED_IDS): lines.append(f"  ◇ {b}")
        if not BANNED_IDS: lines.append("  ◇ none")
        send(cid, "\n".join(lines)); return

    if text == "/stats":
        if not is_owner(uid): send(cid, DENY); return
        show_user_stats(cid); return

    awaiting = _get(cid, "awaiting")
    if awaiting == "grant":     do_grant(cid, uid, text);      return
    if awaiting == "revoke":    do_revoke(cid, uid, text);     return
    if awaiting == "ban":       do_ban(cid, uid, text);        return
    if awaiting == "unban":     do_unban(cid, uid, text);      return
    if awaiting == "reset":     do_reset(cid, uid, text);      return
    if awaiting == "broadcast": do_broadcast(cid, uid, msg);   return

    if text in ("◈◈ MAIN MENU", "◇ MAIN MENU"):
        cmd_main_menu(cid, uid); return

    if text in PROXY_TYPE_MAP:
        if text == "◈ QUICK GEN":
            generate_proxy_quick(cid, uid)
        else:
            start_proxy_task(cid, uid, text)
        return

    if text == "◈ GENERATE PROXY":
        generate_proxy_quick(cid, uid); return

    if text == "◇ COOKIE GEN":
        show_cookie_menu(cid, uid); return

    if text in COOKIE_COUNTS:
        start_cookie_task(cid, uid, text); return

    if text == "◈ STOP TASK":
        do_stop(cid, uid); return

    if text == "◈ MY QUOTA":
        show_quota(cid, uid); return

    if text in ("◇ MY PROFILE", "◈ MY ACCESS"):
        show_access(cid, uid); return

    if text in ("◈ ABOUT", "◇ ABOUT"):
        show_about(cid); return

    if text == "◈ STATUS":
        show_proxy_status(cid); return

    if not is_owner(uid):
        send(cid, "◈ USE THE KEYBOARD\n◇ TRY /quota OR /me", kb=KB_USER_MAIN)
        return

    if text == "◈ USER MANAGER":  show_user_mgr(cid, uid);    return
    if text == "◇ ADMIN PANEL":   show_admin_panel(cid, uid); return
    if text == "◈ GRANT USER":    prompt_grant(cid, uid);     return
    if text == "◇ REVOKE USER":   prompt_revoke(cid, uid);    return
    if text == "◈ BAN USER":      prompt_ban(cid, uid);       return
    if text == "◇ UNBAN USER":    prompt_unban(cid, uid);     return
    if text == "◈ RESET QUOTA":   prompt_reset(cid, uid);     return
    if text == "◈ LIST USERS":    list_all_users(cid);        return
    if text == "◇ PENDING":       list_pending(cid);          return
    if text == "◈ USER STATS":    show_user_stats(cid);       return
    if text == "◈ BROADCAST":     prompt_broadcast(cid, uid); return
    if text == "◈ VIEW USER":     list_all_users(cid);        return

    send(cid, "◈ LOQI SYSTEM\n◇ USE KEYBOARD", kb=KB_MAIN)


def handle_update(upd: dict):
    try:
        if "message" in upd:
            handle_message(upd["message"])
        elif "callback_query" in upd:
            handle_callback(upd["callback_query"])
    except Exception as e:
        print(f"[LOQI ERR] {e}")
        traceback.print_exc()


def main():
    print(
        f"\n{'═' * 56}\n"
        f"  L O Q I   B O T   //   v{VERSION}\n"
        f"  {AUTHOR_1}  /  {AUTHOR_2}\n"
        f"  DATA DIR: {DATA_DIR}\n"
        f"  PROXY  [{PROXY_TOTAL_CAP:,} cap / {PROXY_WORKERS}t / {PROXY_TIMEOUT}s]\n"
        f"  COOKIE [{COOKIE_MAX:,} max / {COOKIE_WORKERS}t]\n"
        f"  SOURCES: {len(SOURCES)} scrapers\n"
        f"  SOCKS:   {'ENABLED' if SOCKS_AVAILABLE else 'DISABLED (install PySocks)'}\n"
        f"  OUT: {PROXY_OUT}  +  {COOKIE_OUT}\n"
        f"{'═' * 56}\n"
    )

    load_state()

    me = tg("getMe")
    if not me.get("ok"):
        print(f"  [!] TOKEN INVALID: {me}")
        sys.exit(1)

    bot_name = me["result"].get("username", "LOQI")
    print(f"  [+] ONLINE AS @{bot_name}")
    print(f"  [+] OWNER  : {OWNER_ID}")
    print(f"  [+] POLLING...\n")

    while True:
        try:
            for upd in get_updates():
                handle_update(upd)
        except KeyboardInterrupt:
            print("\n  [*] SHUTDOWN — LOQI OFFLINE")
            sys.exit(0)
        except Exception as e:
            print(f"  [!] POLL ERROR: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()