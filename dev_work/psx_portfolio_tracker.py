#!/usr/bin/env python3
"""
PSX Portfolio Tracker
- Reads tickers from portfolio.json
- Fetches prices in parallel every 30 seconds
- Saves results to SQLite (psx_prices.db)
- Excel can read from SQLite for live portfolio tracking
"""

import json
import time
import threading
import sqlite3
from datetime import datetime
from pathlib import Path
from test import fetch_and_display_stock  # Reuse your fetch logic
import sys
import streamlit as st

PORTFOLIO_FILE = 'portfolio.json'
DB_FILE = 'psx_prices.db'
FETCH_INTERVAL = 30  # seconds

# --- DB Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            price REAL,
            change_value REAL,
            percentage TEXT,
            direction TEXT,
            fetched_at TEXT
        )
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol_time ON prices(symbol, fetched_at)
    ''')
    conn.commit()
    conn.close()

# --- Fetch Logic ---
def fetch_and_save(symbol):
    from test import fetch_and_display_stock
    import requests
    import re
    from bs4 import BeautifulSoup
    from colorama import Fore, Style
    try:
        url = f"https://dps.psx.com.pk/company/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        price = None
        price_element = soup.select_one('.quote__close')
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_match = re.search(r'Rs\.?\s*([0-9,]+\.?[0-9]*)', price_text)
            if price_match:
                price = float(price_match.group(1).replace(',', ''))
        change_value = None
        change_element = soup.select_one('.change__value')
        if change_element:
            change_text = change_element.get_text(strip=True)
            change_match = re.search(r'([0-9,]+\.?[0-9]*)', change_text)
            if change_match:
                change_value = float(change_match.group(1))
        percentage = None
        percent_element = soup.select_one('.change__percent')
        if percent_element:
            percent_text = percent_element.get_text(strip=True)
            percent_match = re.search(r'[\(\-]?([0-9,]+\.?[0-9]*)%?[\)]?', percent_text)
            if percent_match:
                percentage = percent_match.group(1) + '%'
        direction = ""
        if change_value is not None:
            if change_value > 0:
                direction = "+"
            elif change_value < 0:
                direction = "-"
        if price is not None:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''INSERT INTO prices (symbol, price, change_value, percentage, direction, fetched_at) VALUES (?, ?, ?, ?, ?, ?)''',
                (symbol, price, change_value, percentage, direction, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            print(f"{Style.BRIGHT}{symbol}{Style.RESET_ALL}: Rs. {price} {direction}{change_value if change_value is not None else ''} {percentage if percentage else ''}")
        else:
            print(f"{Fore.RED}Failed to fetch price for {symbol}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error fetching {symbol}: {e}{Style.RESET_ALL}")

# --- Main Loop ---
def main():
    st.set_page_config(page_title="PSX Portfolio Dashboard", layout="wide", page_icon="📈", initial_sidebar_state="expanded")
    init_db()
    if not Path(PORTFOLIO_FILE).exists():
        print(f"Portfolio file {PORTFOLIO_FILE} not found.")
        sys.exit(1)
    with open(PORTFOLIO_FILE) as f:
        data = json.load(f)
    tickers = data.get('tickers', [])
    print(f"Tracking: {', '.join(tickers)}")
    while True:
        threads = []
        for symbol in tickers:
            t = threading.Thread(target=fetch_and_save, args=(symbol,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print(f"--- Sleeping {FETCH_INTERVAL} seconds ---\n")
        time.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    main()
