#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RISE ETF 143 Daily Market Data Auto-Updater
Designed for GitHub Actions Automated Daily Execution.
"""

import os
import sys
import json
import datetime
import urllib.request

def get_kst_now():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    return utc_now + datetime.timedelta(hours=9)

def fetch_json(url, timeout=10):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        print(f"[Warning] Failed to fetch {url}: {e}")
        return None

def main():
    kst_now = get_kst_now()
    today_str = kst_now.strftime("%Y-%m-%d")
    date_label = kst_now.strftime("%y/%m/%d") + " 종가 기준"

    print(f"=== RISE ETF Daily Update Starting: {today_str} (KST {kst_now.strftime('%H:%M:%S')}) ===")

    # 1. Base path configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    latest_file = os.path.join(data_dir, "latest.json")
    if not os.path.exists(latest_file):
        print(f"[Error] {latest_file} not found! Cannot load base template.")
        sys.exit(1)

    with open(latest_file, "r", encoding="utf-8") as f:
        base_data = json.load(f)

    # 2. Fetch live ETF quotes from Naver Finance API (All Korean ETFs in 1 single call)
    etf_api_url = "https://finance.naver.com/api/sise/etfItemList.nhn"
    etf_resp = fetch_json(etf_api_url)
    live_quotes = {}
    if etf_resp and "result" in etf_resp and "etfItemList" in etf_resp["result"]:
        for item in etf_resp["result"]["etfItemList"]:
            code = str(item.get("itemcode", "")).strip()
            if code:
                live_quotes[code] = item
        print(f"✔ Successfully fetched {len(live_quotes)} Korean ETF quotes from KRX/Naver.")
    else:
        print("ℹ Live ETF API not available or throttled. Preserving existing baseline prices.")

    # 3. Update 143 items in the master list
    updated_items = []
    updated_count = 0
    for row in base_data.get("items", []):
        code = str(row[0]).strip()
        if code in live_quotes:
            q = live_quotes[code]
            now_val = q.get("nowVal", 0)
            change_rate = q.get("changeRate", 0.0)
            nav = q.get("nav", 0)
            quant = q.get("quant", 0)
            market_sum = q.get("marketSum", 0)

            if now_val > 0:
                row[5] = f"{int(now_val):,}"
                row[6] = f"{int(nav):,}" if nav > 0 else row[6]
                
                # Disparity (괴리율)
                if nav > 0:
                    disp = ((now_val - nav) / nav) * 100
                    row[7] = f"{disp:+.2f}%"
                
                # 1D Change
                row[8] = f"{change_rate:+.2f}%"
                # Volume (백만 단위)
                row[16] = f"{int(quant * now_val / 1000000):,}" if quant > 0 else row[16]
                # AUM (억 단위)
                row[17] = f"{int(market_sum):,}" if market_sum > 0 else row[17]
                updated_count += 1

        updated_items.append(row)

    print(f"✔ Processed 143 items ({updated_count} refreshed with live KRX closing quotes).")

    # 4. Construct daily JSON payload
    daily_payload = {
        "date": today_str,
        "baseDateLabel": date_label,
        "macro": base_data.get("macro", {}),
        "briefing": base_data.get("briefing", {}),
        "report": base_data.get("report", {}),
        "news": base_data.get("news", []),
        "focusCodes": base_data.get("focusCodes", ["477170", "0176E0", "485690", "148020"]),
        "focusReasons": base_data.get("focusReasons", {}),
        "items": updated_items
    }

    # 5. Save files: latest.json AND today's date archive (e.g. data/2026-09-11.json)
    today_file = os.path.join(data_dir, f"{today_str}.json")

    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(daily_payload, f, ensure_ascii=False, indent=2)
    print(f"✔ Saved: {latest_file}")

    with open(today_file, "w", encoding="utf-8") as f:
        json.dump(daily_payload, f, ensure_ascii=False, indent=2)
    print(f"✔ Saved Date Archive: {today_file}")

    print("=== RISE ETF Daily Update Completed Successfully! ===")

if __name__ == "__main__":
    main()
