"""Monitor six BABY RIIZE KEY RING variants without changing magnetic-doll state."""
import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from playwright.sync_api import sync_playwright
from monitor import MEMBERS, SOLD_OUT, send_mail

URL = "https://smtownandstore.com/product/pop-up-riize-2025-we-little-riize-baby-riize-key-ring/26236/category/57/display/1/"
STATE = Path("baby-riize-state.json")


class BabyOptionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.value = ""
        self.parts = []
        self.labels = {}

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "option":
            self.active = True
            self.value = dict(attrs).get("value", "").strip().upper()
            self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "option" and self.active:
            if self.value in MEMBERS:
                if self.value in self.labels:
                    raise ValueError("Duplicate BABY RIIZE option: " + self.value)
                self.labels[self.value] = " ".join("".join(self.parts).split())
            self.active = False


def fetch_stock():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page(
                locale="ko-KR",
                user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
            )
            response = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            print("BABY RIIZE browser status:", response.status if response else "none", flush=True)
            print("BABY RIIZE browser URL:", page.url, flush=True)
            page.wait_for_timeout(10000)
            html = page.content()
            if "BABY RIIZE" not in html.upper() or "KEY RING" not in html.upper():
                raise ValueError("Unexpected BABY RIIZE product page")
            parser = BabyOptionParser()
            parser.feed(html)
            if set(parser.labels) != set(MEMBERS):
                raise ValueError("Expected six BABY RIIZE variants, got " + repr(parser.labels))
            for member in MEMBERS:
                print("BABY RIIZE option", member, repr(parser.labels[member][:150]), flush=True)
            # A page where all stock labels vanish is ambiguous, not proof of a restock.
            if not any(SOLD_OUT.search(label) for label in parser.labels.values()):
                raise ValueError("No SOLD OUT labels; availability cannot be verified safely")
            return {member: not bool(SOLD_OUT.search(parser.labels[member])) for member in MEMBERS}
        finally:
            browser.close()


def run():
    mode = os.environ.get("MODE", "check")
    if mode not in {"check", "inspect", "test-email"}:
        raise ValueError("Unsupported MODE")
    current = fetch_stock()
    now = datetime.now(timezone.utc)
    body = "\n".join(f"{m}: {'有货' if current[m] else '售罄'}" for m in MEMBERS)
    body += "\n\n检查时间 (UTC): " + now.isoformat() + "\n商品链接: " + URL
    print("BABY RIIZE checked UTC:", now.isoformat(), flush=True)
    for member in MEMBERS:
        print("BABY RIIZE", member, "IN STOCK" if current[member] else "SOLD OUT", flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("\n## BABY RIIZE KEY RING inventory\n\n")
            out.write("\n".join(f"- {m}: {'IN STOCK' if current[m] else 'SOLD OUT'}" for m in MEMBERS))
            out.write("\n\n[Product page](" + URL + ")\n")
    if mode == "inspect":
        print("Inspection only; no email/state update.")
        return
    if any(not os.environ.get(x, "").strip() for x in ("GMAIL_USER", "GMAIL_APP_PASSWORD")):
        raise ValueError("Missing Gmail Actions secrets")
    if mode == "test-email":
        send_mail("[测试] BABY RIIZE KEY RING 库存监控",
                  "这只是测试邮件，不表示商品已补货。\n\n" + body)
        return

    previous = None
    if STATE.exists():
        previous = json.loads(STATE.read_text(encoding="utf-8"))
        if previous.get("url") != URL or set(previous.get("stock", {})) != set(MEMBERS):
            raise ValueError("Unexpected BABY RIIZE saved state; refusing to overwrite")
        if any(type(x) is not bool for x in previous["stock"].values()):
            raise ValueError("Invalid BABY RIIZE saved state")
    newly_available = [m for m in MEMBERS if current[m] and
                       (previous is None or not previous["stock"][m])]
    if newly_available:
        send_mail("[补货提醒] BABY RIIZE KEY RING: " + ", ".join(newly_available),
                  "以下成员现已显示可购买：\n" + "\n".join(newly_available) +
                  "\n\n" + body + "\n\n请打开页面确认。")
        print("BABY RIIZE restock alert:", ", ".join(newly_available))
    elif previous is None:
        send_mail("[已启用] BABY RIIZE KEY RING 六人库存监控",
                  "首次库存检查已完成，此邮件不代表补货。\n\n" + body)
        print("BABY RIIZE activation notification sent.")
    else:
        print("BABY RIIZE: no new restock.")
    STATE.write_text(json.dumps(
        {"url": URL, "stock": current, "last_success_date_utc": now.date().isoformat()},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print("::error::BABY RIIZE monitor failed (" + type(exc).__name__ +
              "): " + str(exc)[:400] + "; previous state not updated.", flush=True)
        raise SystemExit(1)
