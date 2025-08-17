import os
import streamlit as st
import pandas as pd
from datetime import datetime
import threading
import time
import requests
import re
from bs4 import BeautifulSoup
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

@st.cache_resource(show_spinner=False)
def get_mongo():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db

# --- DB Setup ---
def init_db():
    db = get_mongo()
    # Collections are created automatically in MongoDB on first insert
    # Optionally, create indexes for performance
    db.prices.create_index([('symbol', 1), ('fetched_at', -1)])
    db.trades.create_index([('symbol', 1), ('trade_date', -1)])

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
    db = get_mongo()
    db.prices.insert_one({
        'symbol': symbol,
        'price': price,
        'change_value': change_value,
        'percentage': percentage,
        'direction': direction,
        'fetched_at': datetime.now().isoformat()
    })

def fetch_and_save_all(tickers):
    for symbol in tickers:
        try:
            price, change_value, percentage, direction = fetch_price(symbol)
            if price is not None:
                save_price(symbol, price, change_value, percentage, direction)
        except Exception as e:
            st.warning(f"Error fetching {symbol}: {e}")

# --- Login Logic ---
def show_login():
    st.title("🔒 PSX Portfolio Login")
    with st.form("login_form"):
        email = st.text_input("Email", value="", key="login_email")
        password = st.text_input("Password", type="password", value="", key="login_pass")
        submitted = st.form_submit_button("Login")
        if submitted:
            if email == "anees.ahmed@techverx.com" and password == "87654321":
                st.session_state["authenticated"] = True
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    show_login()
    st.stop()

# --- Streamlit UI ---
st.set_page_config(page_title="PSX Portfolio Dashboard", layout="wide", page_icon="📈", initial_sidebar_state="expanded")
st.title("📈 PSX Portfolio Dashboard")

init_db()

# --- Portfolio Table Logic ---
def get_portfolio_symbols():
    db = get_mongo()
    symbols = db.portfolio.find({}, {"_id": 0, "symbol": 1})
    return [doc["symbol"] for doc in symbols]

def add_portfolio_symbol(symbol):
    db = get_mongo()
    db.portfolio.update_one({"symbol": symbol}, {"$set": {"symbol": symbol}}, upsert=True)

def remove_portfolio_symbol(symbol):
    db = get_mongo()
    db.portfolio.delete_one({"symbol": symbol})
    db.trades.delete_many({"symbol": symbol})
    db.prices.delete_many({"symbol": symbol})

# Get portfolio symbols before sidebar and all uses
portfolio_symbols = get_portfolio_symbols()

# Sidebar: Portfolio Management
with st.sidebar:
    st.markdown("""
    <style>
    .sidebar-section {margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #444;}
    .sidebar-title {font-size: 1.2rem; font-weight: bold; margin-bottom: 0.5rem; color: #ffb703;}
    .sidebar-label {font-size: 0.95rem; color: #bbb; margin-bottom: 0.2rem;}
    .sidebar-btn {margin-top: 0.5rem; margin-bottom: 0.5rem;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">📊 Manage Portfolio Symbols</div>', unsafe_allow_html=True)
    new_symbol = st.text_input("Add Symbol to Portfolio", "")
    add_col, remove_col = st.columns([1,1])
    with add_col:
        if st.button("➕ Add Symbol", key="add_symbol_btn"):
            if new_symbol and new_symbol not in portfolio_symbols:
                add_portfolio_symbol(new_symbol)
                st.success(f"Added {new_symbol} to portfolio.")
                st.rerun()
            else:
                st.warning("Symbol already in portfolio or empty.")
    st.markdown('<div class="sidebar-label">Remove Symbol</div>', unsafe_allow_html=True)
    remove_symbol = st.selectbox("", [s for s in portfolio_symbols], key="remove_symbol") if portfolio_symbols else None
    # Move remove button below dropdown
    if remove_symbol:
        if st.button("🗑️ Remove Selected", key="remove_symbol_btn"):
            remove_portfolio_symbol(remove_symbol)
            st.success(f"Removed {remove_symbol} and its trades/prices.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">🔄 Price Actions</div>', unsafe_allow_html=True)
    if st.button("💹 Fetch Latest Prices", help="Fetch latest prices for all symbols", key="fetch_prices_btn"):
        fetch_and_save_all(portfolio_symbols)
        st.success("Prices updated!")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">📝 Log Trade</div>', unsafe_allow_html=True)
    with st.form("trade_form"):
        trade_symbol = st.selectbox("Symbol", portfolio_symbols)
        trade_type = st.selectbox("Type", ["Buy", "Sell"])
        trade_qty = st.number_input("Quantity", min_value=1.0, step=1.0)
        trade_price = st.number_input("Price", min_value=0.0, step=0.01)
        trade_date = st.date_input("Date", value=datetime.now().date())
        trade_notes = st.text_input("Notes")
        submitted = st.form_submit_button("Add Trade")
        if submitted:
            db = get_mongo()
            db.trades.insert_one({
                'symbol': trade_symbol,
                'trade_type': trade_type,
                'quantity': trade_qty,
                'price': trade_price,
                'trade_date': trade_date.isoformat(),
                'notes': trade_notes
            })
            st.success("Trade logged!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Auto-refresh every 60 seconds ---
REFRESH_INTERVAL = 300  # seconds
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()

if time.time() - st.session_state['last_refresh'] > REFRESH_INTERVAL:
    fetch_and_save_all(portfolio_symbols)
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

st.info(f"Auto-refresh every {REFRESH_INTERVAL} seconds. Last refresh: {datetime.fromtimestamp(st.session_state['last_refresh']).strftime('%H:%M:%S')}")

# --- Portfolio Analytics ---
def get_latest_prices():
    db = get_mongo()
    pipeline = [
        {"$match": {"symbol": {"$in": portfolio_symbols}}},
        {"$sort": {"fetched_at": -1}},
        {"$group": {
            "_id": "$symbol",
            "symbol": {"$first": "$symbol"},
            "price": {"$first": "$price"},
            "change_value": {"$first": "$change_value"},
            "percentage": {"$first": "$percentage"},
            "direction": {"$first": "$direction"},
            "last_update": {"$first": "$fetched_at"}
        }}
    ]
    rows = list(db.prices.aggregate(pipeline))
    df = pd.DataFrame(rows)
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df

def get_trades():
    db = get_mongo()
    rows = list(db.trades.find())
    df = pd.DataFrame(rows)
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df

prices_df = get_latest_prices()
trades_df = get_trades()

def calc_portfolio(prices_df, trades_df):
    summary = []
    if 'symbol' not in trades_df.columns:
        trades_df['symbol'] = None
    if 'symbol' not in prices_df.columns:
        prices_df['symbol'] = None
    for symbol in portfolio_symbols:
        trades = trades_df[trades_df['symbol'] == symbol]
        buys = trades[trades['trade_type'] == 'Buy'] if 'trade_type' in trades.columns else pd.DataFrame()
        sells = trades[trades['trade_type'] == 'Sell'] if 'trade_type' in trades.columns else pd.DataFrame()
        qty_bought = buys['quantity'].sum() if 'quantity' in buys.columns else 0
        qty_sold = sells['quantity'].sum() if 'quantity' in sells.columns else 0
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
selected_symbol = st.selectbox("Select Symbol to View Trade Log", portfolio_symbols)
filtered_trades = trades_df[trades_df['symbol'] == selected_symbol]
if 'trade_date' not in filtered_trades.columns:
    filtered_trades['trade_date'] = ''
if not filtered_trades.empty:
    filtered_trades = filtered_trades.sort_values('trade_date', ascending=False)
    st.dataframe(filtered_trades, use_container_width=True, hide_index=True)
else:
    st.info(f"No trades found for {selected_symbol}.")

st.caption("Made with Streamlit. Data auto-refreshes on price fetch or trade log.")
