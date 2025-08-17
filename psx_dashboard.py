import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime
import threading
import time
import requests
import re
from bs4 import BeautifulSoup
from pathlib import Path

PORTFOLIO_FILE = 'portfolio.json'
DB_FILE = 'psx_prices.db'

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
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            trade_type TEXT NOT NULL, -- Buy/Sell
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            trade_date TEXT NOT NULL,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- Price Fetch Logic ---
def fetch_price(symbol):
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
        change_match = re.search(r'([\-]?[0-9,]+\.?[0-9]*)', change_text)
        if change_match:
            change_value = float(change_match.group(1))
    percentage = None
    percent_element = soup.select_one('.change__percent')
    if percent_element:
        percent_text = percent_element.get_text(strip=True)
        percent_match = re.search(r'([\-+]?\d+\.?\d*)%?', percent_text)
        if percent_match:
            percentage = f"{percent_match.group(1)}%"
    direction = ""
    if change_value is not None:
        if change_value > 0:
            direction = "+"
        elif change_value < 0:
            direction = "-"
    return price, change_value, percentage, direction

def save_price(symbol, price, change_value, percentage, direction):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO prices (symbol, price, change_value, percentage, direction, fetched_at) VALUES (?, ?, ?, ?, ?, ?)''',
        (symbol, price, change_value, percentage, direction, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def fetch_and_save_all(tickers):
    for symbol in tickers:
        try:
            price, change_value, percentage, direction = fetch_price(symbol)
            if price is not None:
                save_price(symbol, price, change_value, percentage, direction)
        except Exception as e:
            st.warning(f"Error fetching {symbol}: {e}")

# --- Streamlit UI ---
st.set_page_config(page_title="PSX Portfolio Dashboard", layout="wide", page_icon="📈", initial_sidebar_state="expanded")
st.title("📈 PSX Portfolio Dashboard")

init_db()

# Load tickers from portfolio.json
if not Path(PORTFOLIO_FILE).exists():
    st.error(f"Portfolio file {PORTFOLIO_FILE} not found.")
    st.stop()
with open(PORTFOLIO_FILE) as f:
    data = json.load(f)
tickers = data.get('tickers', [])

# Sidebar: Fetch prices
if st.sidebar.button("Fetch Latest Prices", help="Fetch latest prices for all tickers"):
    fetch_and_save_all(tickers)
    st.sidebar.success("Prices updated!")

# Sidebar: Add trade
st.sidebar.header("Log Trade")
with st.sidebar.form("trade_form"):
    trade_symbol = st.selectbox("Symbol", tickers)
    trade_type = st.selectbox("Type", ["Buy", "Sell"])
    trade_qty = st.number_input("Quantity", min_value=1.0, step=1.0)
    trade_price = st.number_input("Price", min_value=0.0, step=0.01)
    trade_date = st.date_input("Date", value=datetime.now().date())
    trade_notes = st.text_input("Notes")
    submitted = st.form_submit_button("Add Trade")
    if submitted:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''INSERT INTO trades (symbol, trade_type, quantity, price, trade_date, notes) VALUES (?, ?, ?, ?, ?, ?)''',
            (trade_symbol, trade_type, trade_qty, trade_price, trade_date.isoformat(), trade_notes))
        conn.commit()
        conn.close()
        st.sidebar.success("Trade logged!")

# --- Auto-refresh every 60 seconds ---
REFRESH_INTERVAL = 300  # seconds
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()

if time.time() - st.session_state['last_refresh'] > REFRESH_INTERVAL:
    fetch_and_save_all(tickers)
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

st.info(f"Auto-refresh every {REFRESH_INTERVAL} seconds. Last refresh: {datetime.fromtimestamp(st.session_state['last_refresh']).strftime('%H:%M:%S')}")

# --- Portfolio Analytics ---
def get_latest_prices():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('''
        SELECT symbol, price, change_value, percentage, direction, MAX(fetched_at) as last_update
        FROM prices
        WHERE symbol IN ({})
        GROUP BY symbol
    '''.format(','.join(['?']*len(tickers))), conn, params=tickers)
    conn.close()
    return df

def get_trades():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('''SELECT * FROM trades''', conn)
    conn.close()
    return df

prices_df = get_latest_prices()
trades_df = get_trades()

# Calculate positions and analytics
def calc_portfolio(prices_df, trades_df):
    summary = []
    for symbol in tickers:
        trades = trades_df[trades_df['symbol'] == symbol]
        buys = trades[trades['trade_type'] == 'Buy']
        sells = trades[trades['trade_type'] == 'Sell']
        qty_bought = buys['quantity'].sum()
        qty_sold = sells['quantity'].sum()
        net_qty = qty_bought - qty_sold
        avg_buy = (buys['quantity'] * buys['price']).sum() / qty_bought if qty_bought > 0 else 0
        latest_row = prices_df[prices_df['symbol'] == symbol]
        latest_price = latest_row['price'].values[0] if not latest_row.empty else None
        latest_percentage = latest_row['percentage'].values[0] if not latest_row.empty else None
        market_value = net_qty * latest_price if latest_price is not None else 0
        unrealized_pl = (latest_price - avg_buy) * net_qty if latest_price is not None else 0
        summary.append({
            'Symbol': symbol,
            'Shares Held': net_qty,
            'Avg Buy Price': round(avg_buy, 2),
            'Latest Price': latest_price,
            'Change %': latest_percentage,
            'Market Value': round(market_value, 2),
            'Unrealized P/L': round(unrealized_pl, 2),
            'Last Update': latest_row['last_update'].values[0] if not latest_row.empty else None
        })
    return pd.DataFrame(summary)

portfolio_df = calc_portfolio(prices_df, trades_df)

# --- Dashboard Layout ---
st.subheader("Portfolio Overview")
st.dataframe(portfolio_df, use_container_width=True, hide_index=True)

st.subheader("Trade Logs")
for symbol in tickers:
    st.markdown(f"### {symbol} Trades")
    st.dataframe(trades_df[trades_df['symbol'] == symbol].sort_values('trade_date', ascending=False), use_container_width=True, hide_index=True)

st.caption("Made with Streamlit. Data auto-refreshes on price fetch or trade log.")
