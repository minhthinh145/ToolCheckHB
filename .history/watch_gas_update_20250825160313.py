# filepath: c:\Users\ADMIN\Desktop\ToolDiem\watch_gas_update.py
import requests
import time
import re
import json
import random
import string
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from getpass import getpass
import os

# ==== CẤU HÌNH ====
BASE_ID = "AKfycbzfqVJUKLHIfBPiPP_ewZMxnZaRqWLK0XN862DcEepD0O3_MA6kn-obSxokKUsrLT1SCw"
CHECK_INTERVAL_SEC = 5
TARGET_DATE = "30/05/2025"
STOP_ON_CHANGE = True          # Sau khi gửi email thì dừng
PRINT_FULL_LIST = True

# Danh sách email nhận
LIST_EMAILS = [
    "minhthinh0384360149@gmail.com","minhthinh.221005@gmail.com","thuyhuynh091271@gmail.com"
]

# Cookie (nếu cần để truy cập)
COOKIE_NID = "NID=525=AWClXcJDrJM90HxJC0algDKmVe5sLJ-1_nuWyeQKGHdpV9BXu3lKpBz4j5Pie85jYuF4fqyLX01n6Rv9q3X8JpDgLXLhDwfEH7Y6ySU9SfAcdL1z8OXqQUjAlBV3Pz-JsFfm5_0pYZr8KrhU23JkPEe36WefxUnlYi_r-5qY-uQMQH-vutp7OZJTQ7AB0rAY"

ENC_REQUEST_PARAM = "%5B%22getMain%22%2C%22%5B%5D%22%2Cnull%2C%5B0%5D%2Cnull%2Cnull%2C1%2C0%5D"
XSSI_PREFIX = ")]}'"
DATE_REGEX = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")

def _rand_id():
    return ''.join(random.choices(string.digits, k=8))

def build_urls():
    nocache = _rand_id()
    callback_url = f"https://script.google.com/macros/s/{BASE_ID}/callback?nocache_id={nocache}"
    referer_exec = f"https://script.google.com/a/macros/hcmue.edu.vn/s/{BASE_ID}/exec"
    return callback_url, referer_exec

def fetch_raw():
    url, referer_exec = build_urls()
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "Origin": "https://script.google.com",
        "Referer": referer_exec,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-GPC": "1",
        "X-Same-Domain": "1",
    }
    if COOKIE_NID:
        headers["Cookie"] = COOKIE_NID
    data = f"request={ENC_REQUEST_PARAM}"
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=15)
    except Exception as e:
        print(f"[FETCH] POST error: {e}")
        return ""
    if resp.status_code != 200:
        print(f"[FETCH] POST {resp.status_code}. Trying GET fallback...")
        get_url = f"{url}&{data}"
        try:
            resp2 = requests.get(get_url, headers=headers, timeout=15)
            if resp2.status_code != 200:
                print(f"[FETCH] GET fallback {resp2.status_code}")
                return ""
            text = resp2.text
        except Exception as e:
            print(f"[FETCH] GET error: {e}")
            return ""
    else:
        text = resp.text
    text = text.strip()
    if text.startswith(XSSI_PREFIX):
        text = text[len(XSSI_PREFIX):].lstrip()
    return text

def extract_dates(struct_json_text):
    try:
        parsed = json.loads(struct_json_text)
    except Exception:
        return []
    dates = []
    for entry in parsed:
        if isinstance(entry, list) and len(entry) >= 2 and entry[0] == "op.exec":
            payload = entry[1]
            if isinstance(payload, list) and len(payload) >= 2:
                nested_str = payload[1]
                try:
                    nested = json.loads(nested_str)
                    for item in nested:
                        if isinstance(item, list) and item:
                            txt = item[0]
                            if isinstance(txt, str):
                                for d in DATE_REGEX.findall(txt):
                                    dates.append(normalize_date(d))
                except Exception:
                    pass
    out, seen = [], set()
    for d in dates:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out

def normalize_date(d: str) -> str:
    try:
        dd, mm, yy = d.split("/")
        return f"{int(dd):02d}/{int(mm):02d}/{int(yy):04d}"
    except Exception:
        return d

def send_email(smtp_user, smtp_pass, old_first, new_first, dates, reason):
    if not LIST_EMAILS:
        print("[EMAIL] LIST_EMAILS rỗng, bỏ qua gửi.")
        return
    subject = f"[WATCH] Thay đổi cập nhật: {old_first} -> {new_first}" if new_first else f"[WATCH] {reason}"
    body_lines = [
        f"Thời điểm: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Lý do kích hoạt: {reason}",
        f"Giá trị cũ (first): {old_first}",
        f"Giá trị mới (first): {new_first}",
        f"Danh sách hiện tại: {dates}",
        f"TARGET_DATE: {TARGET_DATE}",
    ]
    body = "\n".join(body_lines)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(LIST_EMAILS)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, LIST_EMAILS, msg.as_string())
        print("[EMAIL] Đã gửi thông báo.")
    except Exception as e:
        print(f"[EMAIL] Lỗi gửi: {e}")

def main():
    print(f"Start watching. TARGET_DATE={TARGET_DATE} interval={CHECK_INTERVAL_SEC}s")
    print("Tool đang chạy 24/7 trên Render 🚀")

    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    prev_first = None
    first_seen_target = None
    email_sent = False

    while True:
        start = time.time()
        raw = fetch_raw()
        now = datetime.now().strftime("%H:%M:%S")
        if not raw:
            print(f"[{now}] Empty response.")
            time.sleep(max(0, CHECK_INTERVAL_SEC - (time.time() - start)))
            continue

        dates = extract_dates(raw)
        if PRINT_FULL_LIST:
            print(f"[{now}] Dates: {dates if dates else 'None'}")
        else:
            print(f"[{now}] First: {dates[0] if dates else 'None'}")

        trigger_reason = None
        new_first = None

        if dates:
            new_first = dates[0]
            if prev_first is None:
                prev_first = new_first
                if new_first == TARGET_DATE:
                    first_seen_target = datetime.now()
            else:
                if new_first != prev_first:
                    trigger_reason = f"Thay đổi first date {prev_first} -> {new_first}"
            if TARGET_DATE and new_first != TARGET_DATE and first_seen_target and prev_first == TARGET_DATE:
                trigger_reason = f"TARGET_DATE {TARGET_DATE} biến mất (now={new_first})"
        else:
            if prev_first is not None:
                trigger_reason = "Mất toàn bộ danh sách dates"

        if trigger_reason and not email_sent:
            print(f"[{now}] CHANGE DETECTED: {trigger_reason}")
            send_email(smtp_user, smtp_pass, prev_first, new_first, dates, trigger_reason)
            email_sent = True
            if STOP_ON_CHANGE:
                break
            # Cập nhật prev_first để tiếp tục theo dõi vòng sau
            prev_first = new_first
        else:
            # Không có thay đổi đáng kể
            if new_first:
                prev_first = prev_first or new_first

        elapsed = time.time() - start
        time.sleep(max(0, CHECK_INTERVAL_SEC - elapsed))

if __name__ == "__main__":
    main()
