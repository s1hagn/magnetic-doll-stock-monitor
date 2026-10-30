"""RIIZE MAGNETIC DOLL per-member stock monitoring, using Python standard library."""
import json
import os
import re
import smtplib
import ssl
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, timezone
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path

URL = "https://smtownandstore.com/product/riize-concert-tour-riizing-loud-finale-in-seoul-magnetic-doll/28247/category/2003/display/1/"
MEMBERS = ("SHOTARO", "EUNSEOK", "SUNGCHAN", "WONBIN", "SOHEE", "ANTON")
STATE = Path("stock-state.json")
SOLD_OUT = re.compile(r"\bSOLD\s*OUT\b|품절|일시품절|售罄|缺货", re.I)


class OptionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_option = False
        self.value = ""
        self.parts = []
        self.options = {}
        self.labels = {}

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "option":
            self.in_option = True
            self.value = dict(attrs).get("value", "").strip().upper()
            self.parts = []

    def handle_data(self, data):
        if self.in_option:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "option" and self.in_option:
            label = " ".join("".join(self.parts).split())
            if self.value in MEMBERS:
                if self.value in self.options:
                    raise ValueError("Duplicate member option: " + self.value)
                if self.value not in label.upper():
                    raise ValueError("Unexpected member option label: " + self.value)
                self.labels[self.value] = label
                self.options[self.value] = not bool(SOLD_OUT.search(label))
            self.in_option = False


def fetch_stock():
    # SMTOWN's stock labels are populated by JavaScript after the initial HTML response.
    # Inspect the rendered DOM, not the static HTML returned by urllib.
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page(
                locale="ko-KR",
                user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
            )
            for attempt in range(1, 3):
                try:
                    response = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
                    break
                except PlaywrightTimeoutError:
                    if attempt == 2:
                        raise
                    print("Page navigation timed out; retrying once in 3 seconds.", flush=True)
                    time.sleep(3)
            print("Browser response:", response.status if response else "none", flush=True)
            print("Browser URL:", page.url, flush=True)
            print("Page title:", page.title(), flush=True)
            # Do not wait for a specific option: a missing selector must produce
            # useful diagnostics instead of a blind 25-second timeout.
            page.wait_for_timeout(10000)
            print("Rendered option count:", page.locator("option").count(), flush=True)
            print("Number of frames:", len(page.frames), flush=True)
            print("Visible text excerpt:", repr(page.locator("body").inner_text(timeout=5000)[:650]), flush=True)
            html = page.content()
            # Match the stable product ID in the final URL rather than a translated title.
            if not re.search(r"/28247(?:/|$)", page.url):
                raise ValueError("Unexpected product page")
            parser = OptionParser()
            parser.feed(html)
            if set(parser.options) != set(MEMBERS):
                print("Parsed option labels:", repr(parser.labels), flush=True)
                raise ValueError("Expected six member choices, found: " + repr(sorted(parser.options)))
            print("Rendered option labels (after JavaScript):")
            for member in MEMBERS:
                print(member + ": " + repr(parser.labels[member][:150]))
            # Conservative rule: all six bare names could mean JavaScript was blocked.
            # Never generate a false 'everyone restocked' alert from that response.
            if not any(SOLD_OUT.search(label) for label in parser.labels.values()):
                raise ValueError("All rendered labels lack stock indicators; cannot verify availability reliably")
            return parser.options
        finally:
            browser.close()


def send_mail(subject, body):
    sender = os.environ["GMAIL_USER"].strip()
    to = os.environ.get("ALERT_TO", "siya2026z@gmail.com").strip()
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "").strip()
    if not (sender and to and password):
        raise ValueError("Incomplete Gmail SMTP configuration")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    # No automatic retry: a timeout after server acceptance could duplicate alerts.
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30, context=ssl.create_default_context()) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)


def run():
    mode = os.environ.get("MODE", "check")
    if mode not in {"check", "inspect", "test-email"}:
        raise ValueError("Unsupported MODE")
    now = datetime.now(timezone.utc)
    current = fetch_stock()
    print("Checked at UTC:", now.isoformat())
    for name in MEMBERS:
        print(name + ":", "IN STOCK" if current[name] else "SOLD OUT")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## RIIZE MAGNETIC DOLL inventory\n\n" + now.isoformat() + "\n\n")
            out.write("\n".join(f"- {name}: {'IN STOCK' if current[name] else 'SOLD OUT'}" for name in MEMBERS))
            out.write("\n\n[Product page](" + URL + ")\n")
    if mode == "inspect":
        print("Inspection only; no email and no state update.")
        return
    if any(not os.environ.get(x, "").strip() for x in ("GMAIL_USER", "GMAIL_APP_PASSWORD")):
        raise ValueError("Missing GMAIL_USER or GMAIL_APP_PASSWORD Actions secrets")
    body = "\n".join(f"{name}: {'有货' if current[name] else '售罄'}" for name in MEMBERS)
    body += "\n\n检查时间 (UTC): " + now.isoformat() + "\n商品链接: " + URL
    if mode == "test-email":
        send_mail("[测试] RIIZE MAGNETIC DOLL 库存监控", "这只是测试邮件，不表示商品已补货。\n\n" + body)
        print("Test message accepted by SMTP server.")
        return
    previous = None
    if STATE.exists():
        previous = json.loads(STATE.read_text(encoding="utf-8"))
        if previous.get("url") != URL or set(previous.get("stock", {})) != set(MEMBERS):
            raise ValueError("Unexpected saved inventory state; refusing to overwrite")
        if any(type(x) is not bool for x in previous["stock"].values()):
            raise ValueError("Invalid saved inventory state")
    newly_available = [m for m in MEMBERS if current[m] and (previous is None or not previous["stock"][m])]
    if newly_available:
        send_mail("[补货提醒] RIIZE MAGNETIC DOLL: " + ", ".join(newly_available),
                  "以下成员现已显示可购买：\n" + "\n".join(newly_available) + "\n\n" + body +
                  "\n\n商品可能很快再次售罄，请打开页面确认。")
        print("Restock alert accepted by SMTP server:", ", ".join(newly_available))
    elif previous is None:
        send_mail("[已启用] RIIZE MAGNETIC DOLL 六人库存监控",
                  "首次库存检查已完成。此邮件是启动通知，并不表示补货。\n\n" + body)
        print("Activation email accepted by SMTP server.")
    else:
        print("No newly restocked member; no alert.")
    state = {"url": URL, "stock": current, "last_success_date_utc": now.date().isoformat()}
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print("::error::Monitor failed (" + type(exc).__name__ + "): " + str(exc)[:400] + "; previous stock state was not updated.", flush=True)
        raise SystemExit(2 if isinstance(exc, PlaywrightTimeoutError) else 1)
