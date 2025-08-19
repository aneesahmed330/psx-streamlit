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
import pytz

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
            if email == "123" and password == "123":
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
    .sidebar-section {margin-bottom: 2rem; padding-bottom: 1.2rem; border-bottom: 1px solid #333; background: #23272f; border-radius: 10px; box-shadow: 0 2px 8px #0002;}
    .sidebar-title {font-size: 1.18rem; font-weight: bold; margin-bottom: 0.6rem; color: #ffb703; letter-spacing: 0.5px;}
    .sidebar-label {font-size: 1.01rem; color: #bbb; margin-bottom: 0.3rem;}
    .sidebar-btn {margin-top: 0.7rem; margin-bottom: 0.7rem; width: 100%; font-weight: 600;}
    .sidebar-input {background: #18191a; color: #eee; border-radius: 6px; border: 1px solid #444; padding: 0.4em 0.7em;}
    .sidebar-selectbox {background: #18191a; color: #eee; border-radius: 6px; border: 1px solid #444;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">📊 Portfolio Symbols</div>', unsafe_allow_html=True)
    new_symbol = st.text_input("Add Symbol", "", key="add_symbol_input", help="Enter PSX symbol (e.g. UBL)")
    add_col, remove_col = st.columns([1,1])
    with add_col:
        if st.button("➕ Add", key="add_symbol_btn", help="Add symbol to portfolio"):
            if new_symbol and new_symbol not in portfolio_symbols:
                add_portfolio_symbol(new_symbol)
                st.success(f"Added {new_symbol} to portfolio.")
                st.rerun()
            else:
                st.warning("Symbol already in portfolio or empty.")
    st.markdown('<div class="sidebar-label">Remove Symbol</div>', unsafe_allow_html=True)
    remove_symbol = st.selectbox("", [s for s in portfolio_symbols], key="remove_symbol", help="Select symbol to remove") if portfolio_symbols else None
    if remove_symbol:
        if st.button("🗑️ Remove", key="remove_symbol_btn", help="Remove selected symbol"):
            remove_portfolio_symbol(remove_symbol)
            st.success(f"Removed {remove_symbol} and its trades/prices.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">🔄 Price Actions</div>', unsafe_allow_html=True)
    st.button("💹 Fetch Latest Prices", help="Fetch latest prices for all symbols", key="fetch_prices_btn", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">📝 Log Trade</div>', unsafe_allow_html=True)
    with st.form("trade_form"):
        trade_symbol = st.selectbox("Symbol", portfolio_symbols, key="trade_symbol", help="Select symbol for trade")
        trade_type = st.selectbox("Type", ["Buy", "Sell"], key="trade_type", help="Buy or Sell")
        trade_qty = st.number_input("Quantity", min_value=1.0, step=1.0, key="trade_qty", help="Number of shares")
        trade_price = st.number_input("Price", min_value=0.0, step=0.01, key="trade_price", help="Trade price per share")
        trade_date = st.date_input("Date", value=datetime.now().date(), key="trade_date", help="Trade date")
        trade_notes = st.text_input("Notes", key="trade_notes", help="Optional notes")
        submitted = st.form_submit_button("Add Trade", use_container_width=True)
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
    total_investment = 0
    total_market_value = 0
    total_unrealized_pl = 0
    pk_tz = pytz.timezone('Asia/Karachi')
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
        investment = avg_buy * net_qty
        unrealized_pl = (latest_price - avg_buy) * net_qty if latest_price is not None else 0
        percent_updown = ((latest_price - avg_buy) / avg_buy * 100) if avg_buy > 0 and latest_price is not None else 0
        total_investment += investment
        total_market_value += market_value
        total_unrealized_pl += unrealized_pl
        last_update_raw = latest_row['last_update'].values[0] if not latest_row.empty else None
        if last_update_raw:
            try:
                dt = datetime.fromisoformat(last_update_raw)
                if dt.tzinfo is None:
                    dt = pytz.timezone('Asia/Karachi').localize(dt)
                dt_pk = dt.astimezone(pk_tz)
                last_update = dt_pk.strftime('%Y-%m-%d %I:%M %p')
            except Exception:
                last_update = last_update_raw
        else:
            last_update = None
        summary.append({
            'Symbol': symbol,
            'Shares Held': net_qty,
            'Avg Buy Price': round(avg_buy, 2),
            'Latest Price': latest_price,
            'Change %': latest_percentage,
            'Market Value': round(market_value, 2),
            'Investment': round(investment, 2),
            '% Up/Down': percent_updown,
            'Unrealized P/L': round(unrealized_pl, 2),
            'Last Update': last_update
        })
    total_percent_updown = ((total_market_value - total_investment) / total_investment * 100) if total_investment > 0 else 0
    return pd.DataFrame(summary), total_investment, total_market_value, total_unrealized_pl, total_percent_updown

portfolio_df, total_investment, total_market_value, total_unrealized_pl, total_percent_updown = calc_portfolio(prices_df, trades_df)

# --- Dashboard Layout ---
st.subheader("Portfolio Overview")

# Last Data Refresh
st.markdown(f"<span style='color:#bbb;'>Last Data Refresh: <b>{datetime.now(pytz.timezone('Asia/Karachi')).strftime('%Y-%m-%d %I:%M %p')}</b></span>", unsafe_allow_html=True)

# Card-style summary boxes
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div style='background:#23272f;padding:1.2em 1em 1em 1em;border-radius:10px;text-align:center;'>
    <span style='font-size:1.1em;color:#bbb;'>💰 Total Investment</span><br>
    <span style='font-size:1.3em;font-weight:bold;color:#ffb703;'>Rs. {total_investment:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div style='background:#23272f;padding:1.2em 1em 1em 1em;border-radius:10px;text-align:center;'>
    <span style='font-size:1.1em;color:#bbb;'>📈 Portfolio Market Value</span><br>
    <span style='font-size:1.3em;font-weight:bold;color:#00e676;'>Rs. {total_market_value:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div style='background:#23272f;padding:1.2em 1em 1em 1em;border-radius:10px;text-align:center;'>
    <span style='font-size:1.1em;color:#bbb;'>🟢 Unrealized P/L</span><br>
    <span style='font-size:1.3em;font-weight:bold;color:{'lime' if total_unrealized_pl>=0 else 'red'};'>Rs. {total_unrealized_pl:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div style='background:#23272f;padding:1.2em 1em 1em 1em;border-radius:10px;text-align:center;'>
    <span style='font-size:1.1em;color:#bbb;'>% Up/Down</span><br>
    <span style='font-size:1.3em;font-weight:bold;color:{'lime' if total_percent_updown>=0 else 'red'};'>{total_percent_updown:.2f}%</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2.5em;'></div>", unsafe_allow_html=True)

# --- Portfolio Allocation Pie Chart ---
if not portfolio_df.empty:
    pie_df = portfolio_df[portfolio_df['Market Value'] > 0][['Symbol', 'Market Value']]
    st.plotly_chart({
        'data': [{
            'labels': pie_df['Symbol'],
            'values': pie_df['Market Value'],
            'type': 'pie',
            'hole': .4,
            'marker': {'colors': ['#00e676', '#ffb703', '#23272f', '#2196f3', '#e53935', '#8e24aa', '#43a047', '#fbc02d', '#3949ab', '#00838f']}
        }],
        'layout': {'title': 'Portfolio Allocation', 'paper_bgcolor': '#18191a', 'font': {'color': '#bbb'}}
    }, use_container_width=True)

# --- Color Coding for Table ---
def colorize(val, pos_color='lime', neg_color='red'):
    if pd.isnull(val):
        return ''
    try:
        v = float(val)
        if v > 0:
            return f'color: {pos_color}'
        elif v < 0:
            return f'color: {neg_color}'
    except:
        pass
    return ''

styled_df = portfolio_df.style.applymap(colorize, subset=['% Up/Down', 'Unrealized P/L'])

# --- Download as CSV ---
st.download_button('Download Portfolio (CSV)', portfolio_df.to_csv(index=False), file_name='psx_portfolio.csv', mime='text/csv', use_container_width=True)

st.dataframe(styled_df, use_container_width=True, hide_index=True, column_config={
    "% Up/Down": st.column_config.NumberColumn(format="%.2f%%")
})

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
