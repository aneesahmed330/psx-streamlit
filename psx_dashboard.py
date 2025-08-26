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
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import concurrent.futures
import plotly.express as px


# helper functions

# --- Number formatting helper ---
def format_international_number(n):
    try:
        n = float(n)
        abs_n = abs(n)
        if abs_n >= 1_000_000_000_000:
            return f"{n/1_000_000_000_000:.2f}T"
        elif abs_n >= 1_000_000_000:
            return f"{n/1_000_000_000:.2f}B"
        elif abs_n >= 1_000_000:
            return f"{n/1_000_000:.2f}M"
        elif abs_n >= 1_000:
            return f"{n/1_000:.2f}K"
        else:
            return f"{n:.2f}"
    except Exception:
        return n

# ------

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="PSX Portfolio Dashboard", 
    layout="wide", 
    page_icon="📈", 
    initial_sidebar_state="expanded"
)

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# --- Alerts CRUD Functions ---

def get_alerts():
    db = get_mongo()
    rows = list(db.alerts.find())
    df = pd.DataFrame(rows)
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df

def add_alert(symbol, min_price, max_price, enabled):
    db = get_mongo()
    db.alerts.insert_one({
        'symbol': symbol,
        'min_price': float(min_price),
        'max_price': float(max_price),
        'enabled': bool(enabled)
    })

def delete_alert(symbol, min_price, max_price):
    db = get_mongo()
    db.alerts.delete_one({
        'symbol': symbol,
        'min_price': float(min_price),
        'max_price': float(max_price)
    })

def set_alert_enabled(symbol, min_price, max_price, enabled):
    db = get_mongo()
    db.alerts.update_one(
        {'symbol': symbol, 'min_price': float(min_price), 'max_price': float(max_price)},
        {'$set': {'enabled': bool(enabled)}}
    )

# --- Stocks Collection CRUD Functions ---
def get_stocks():
    db = get_mongo()
    rows = list(db.stocks.find())
    df = pd.DataFrame(rows)
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df

def add_stock(symbol):
    db = get_mongo()
    db.stocks.update_one(
        {'symbol': symbol.upper()},
        {'$set': {
            'symbol': symbol.upper(),
            'payouts': [],
            'financials': {'annual': [], 'quarterly': []},
            'ratios': []
        }},
        upsert=True
    )
    # Invalidate both caches when stock is added
    get_cached_stocks_df.clear()
    get_stock_symbols_only.clear()

def delete_stock(symbol):
    db = get_mongo()
    db.stocks.delete_one({'symbol': symbol.upper()})
    # Invalidate both caches when stock is deleted
    get_cached_stocks_df.clear()
    get_stock_symbols_only.clear()

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_stocks_df():
    return get_stocks()

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_symbols_only():
    """Fast function to get just stock symbols without full data"""
    db = get_mongo()
    # Only fetch symbol field, not the heavy financial data
    docs = list(db.stocks.find({}, {"symbol": 1, "_id": 0}))
    return [doc["symbol"] for doc in docs]

# Custom CSS for professional styling with enhanced tabs
st.markdown("""
<style>
    /* Main styling */
    .main { background-color: #0E1117; }
    
    /* Headers */
    h1, h2, h3 { color: #1E88E5; }
    
    /* Sidebar styling */
    .css-1d391kg { background-color: #0E1117; }
    .sidebar .sidebar-content { background-color: #0E1117; }
    
    /* Cards */
    .card { 
        background-color: #1E2130; 
        padding: 1.5rem; 
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(30,136,229,0.12) 0%, rgba(30,33,48,0.95) 100%);
        border: 1.5px solid #1E88E5;
        box-shadow: 0 6px 24px 0 rgba(30,136,229,0.10), 0 1.5px 8px 0 rgba(0,0,0,0.10);
        border-radius: 18px;
        padding: 1.2rem 0.8rem 1rem 0.8rem;
        min-width: 170px;
        min-height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: flex-start;
        transition: box-shadow 0.2s, transform 0.2s;
        position: relative;
        overflow: visible;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: 0 10px 32px 0 rgba(30,136,229,0.18), 0 2px 12px 0 rgba(0,0,0,0.18);
        transform: scale(1.025);
        border-color: #00E396;
    }
    [data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-size: 1.5rem !important;
        font-weight: 700;
        min-width: 120px;
        white-space: normal !important;
        word-break: break-word !important;
        line-height: 1.15;
        text-align: left;
        letter-spacing: 0.5px;
        text-shadow: 0 2px 8px rgba(30,136,229,0.10);
        margin-bottom: 0.2rem;
    }
    [data-testid="stMetricLabel"] {
        color: #A0AEC0;
        font-size: 1.15rem;
        font-weight: 600;
        white-space: normal;
        overflow-wrap: break-word;
        letter-spacing: 0.2px;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        text-shadow: 0 1px 4px rgba(30,136,229,0.08);
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1E88E5;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #1976D2;
        transform: translateY(-1px);
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background-color: #1E2130;
        color: white;
        border: 1px solid #2D3748;
    }
    
    .stNumberInput > div > div > input {
        background-color: #1E2130;
        color: white;
        border: 1px solid #2D3748;
    }
    
    .stSelectbox > div > div > select {
        background-color: #1E2130;
        color: white;
        border: 1px solid #2D3748;
    }
    
    /* Dataframes */
    .dataframe { 
        background-color: #1E2130; 
        color: white;
    }
    
    /* Enhanced Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0E1117;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1E2130;
        border-radius: 8px 8px 0px 0px;
        gap: 1px;
        padding: 10px 16px;
        font-weight: 600;
        font-size: 14px;
        border-bottom: 2px solid transparent;
        transition: all 0.2s ease-in-out;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #2D3748;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1E88E5;
        color: white;
        border-bottom: 2px solid #1E88E5;
    }
    
    /* Tab content */
    .tab-content {
        background-color: #1E2130;
        border-radius: 0 8px 8px 8px;
        padding: 1.5rem;
        margin-top: -1px;
        border: 1px solid #2D3748;
    }
    
    /* Section headers */
    .section-header {
        color: #1E88E5;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #2D3748;
    }
    
    /* Success/error messages */
    .stSuccess { background-color: #2D5740; }
    .stError { background-color: #5D3B45; }
    .stWarning { background-color: #5D4F3B; }
    .stInfo { background-color: #2D4A6B; }
    
    /* Custom badges */
    .badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .badge-success {
        background-color: #2D5740;
        color: #00E396;
    }
    
    .badge-danger {
        background-color: #5D3B45;
        color: #FF4560;
    }
    
    .badge-warning {
        background-color: #5D4F3B;
        color: #FEB019;
    }
    
    /* Chart containers */
    .chart-container {
        background-color: #1E2130;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #2D3748;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def get_mongo():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db

# --- DB Setup ---
def init_db():
    db = get_mongo()
    db.prices.create_index([('symbol', 1), ('fetched_at', -1)])
    db.trades.create_index([('symbol', 1), ('trade_date', -1)])

# --- Price Fetch Logic ---
def fetch_price(symbol):
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Referer': 'https://www.google.com/'
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
    pk_tz = pytz.timezone('Asia/Karachi')
    fetched_at = datetime.now(pk_tz).isoformat()
    # Always insert a new record, never update
    db.prices.insert_one({
        'symbol': symbol,
        'price': price,
        'change_value': change_value,
        'percentage': percentage,
        'direction': direction,
        'fetched_at': fetched_at
    })

def fetch_and_save_all(tickers):
    """Fetch prices for all tickers in parallel using threads for speed."""
    def fetch_and_save_single(symbol):
        try:
            price, change_value, percentage, direction = fetch_price(symbol)
            if price is not None:
                save_price(symbol, price, change_value, percentage, direction)
                return (symbol, "success", price)
            else:
                return (symbol, "no_price", None)
        except Exception as e:
            return (symbol, "error", str(e))
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_symbol = {executor.submit(fetch_and_save_single, symbol): symbol for symbol in tickers}
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                results.append((symbol, "exception", str(exc)))
    
    # Show results summary
    success_count = len([r for r in results if r[1] == "success"])
    error_count = len([r for r in results if r[1] in ["error", "exception", "no_price"]])
    
    if success_count > 0:
        st.success(f"✅ Successfully updated {success_count}/{len(tickers)} prices")
    if error_count > 0:
        errors = [f"{r[0]}: {r[2]}" for r in results if r[1] in ["error", "exception", "no_price"]]
        st.warning(f"⚠️ {error_count} errors occurred:\n" + "\n".join(errors[:3]) + ("..." if len(errors) > 3 else ""))
    
    return results

# --- Login Logic ---
def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center; margin-bottom: 2rem;'>"
                   "<h1 style='color: #1E88E5;'>🔒 PSX Portfolio</h1>"
                   "<p style='color: #A0AEC0;'>Track your Pakistan Stock Exchange investments</p>"
                   "</div>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.text_input("Email", value="", key="login_email", placeholder="Enter your email")
            st.text_input("Password", type="password", value="", key="login_pass", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                if st.session_state.login_email == "123" and st.session_state.login_pass == "123":
                    st.session_state["authenticated"] = True
                    st.success("Login successful! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    show_login()
    st.stop()

# Initialize database
init_db()

# --- Portfolio Table Logic ---
def get_portfolio_symbols_from_trades():
    db = get_mongo()
    trades = list(db.trades.find())
    df = pd.DataFrame(trades)
    if df.empty:
        return []
    # Calculate net shares for each symbol
    df['quantity'] = df['quantity'].astype(float)
    df['trade_type'] = df['trade_type'].str.capitalize()
    buy = df[df['trade_type'] == 'Buy'].groupby('symbol')['quantity'].sum()
    sell = df[df['trade_type'] == 'Sell'].groupby('symbol')['quantity'].sum()
    net = buy.subtract(sell, fill_value=0)
    # Only include symbols with net shares > 0
    symbols = net[net > 0].index.tolist()
    return symbols

# Get portfolio symbols from trades only
portfolio_symbols = get_portfolio_symbols_from_trades()

# --- Functions to fetch and save company info ---
def fetch_and_save_company_info(symbol):
    """Fetch payouts, financials, ratios for a symbol and update the stocks collection."""
    from dev_work.test import fetch_payouts_json, fetch_financials_tidy_json, fetch_ratios_tidy_json
    payouts = fetch_payouts_json(symbol)
    financials = fetch_financials_tidy_json(symbol)
    ratios = fetch_ratios_tidy_json(symbol)
    db = get_mongo()
    db.stocks.update_one(
        {'symbol': symbol.upper()},
        {'$set': {
            'payouts': payouts,
            'financials': financials,
            'ratios': ratios
        }}
    )

def fetch_and_save_all_company_info(symbols):
    """Fetch company info for all symbols in parallel using threads for speed."""
    def fetch_and_save(symbol):
        try:
            fetch_and_save_company_info(symbol)
            return (symbol, None)
        except Exception as e:
            return (symbol, str(e))
    
    results = []
    # Increase workers for faster parallel processing
    max_workers = min(16, len(symbols))  # Use up to 16 workers, but not more than symbols
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks at once for better efficiency
        future_to_symbol = {executor.submit(fetch_and_save, symbol): symbol for symbol in symbols}
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_symbol):
            try:
                result = future.result(timeout=30)  # 30 second timeout per symbol
                results.append(result)
            except concurrent.futures.TimeoutError:
                symbol = future_to_symbol[future]
                results.append((symbol, "Timeout - took longer than 30 seconds"))
            except Exception as exc:
                symbol = future_to_symbol[future]
                results.append((symbol, str(exc)))
    
    # Invalidate both caches when company info is fetched
    get_cached_stocks_df.clear()
    get_stock_symbols_only.clear()
    return results

# --- Sidebar: Portfolio Management, Price Actions, Log Trade, Alerts ---
with st.sidebar:
    st.sidebar.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h2 style='color: #1E88E5; margin-bottom: 0;'>PSX Portfolio</h2>
        <p style='color: #A0AEC0; margin-top: 0;'>Investment Tracker</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Price Actions Section
    with st.expander("🔄 Price Actions", expanded=False):
        if st.button("💹 Fetch Latest Prices", use_container_width=True,
                    help="Fetch latest prices for all symbols (portfolio + stocks)"):
            with st.spinner("Fetching prices..."):
                # Get symbols from both portfolio (trades) and stocks collection
                stocks_df = get_stocks()
                stock_symbols = stocks_df['symbol'].tolist() if not stocks_df.empty else []
                
                # Combine and deduplicate
                all_symbols = list(set(portfolio_symbols + stock_symbols))
                
                if all_symbols:
                    duplicates_removed = len(portfolio_symbols) + len(stock_symbols) - len(all_symbols)
                    st.info(f"Fetching prices for {len(portfolio_symbols)} portfolio + {len(stock_symbols)} analytics symbols = {len(all_symbols)} unique symbols" + 
                           (f" ({duplicates_removed} duplicates removed)" if duplicates_removed > 0 else ""))
                    
                    # Time the operation
                    import time
                    start_time = time.time()
                    fetch_and_save_all(all_symbols)
                    end_time = time.time()
                    
                    # Calculate and display timing
                    elapsed = end_time - start_time
                    if elapsed < 1:
                        time_str = f"{elapsed*1000:.0f}ms"
                    elif elapsed < 60:
                        time_str = f"{elapsed:.1f}s"
                    else:
                        time_str = f"{elapsed/60:.1f}min"
                    
                    st.success(f"⚡ Completed in {time_str} using parallel fetching!")
                else:
                    st.warning("No symbols found to fetch prices for. Add some trades or stocks first.")
        # New button for company info
        if st.button("🏢 Fetch Company Info", use_container_width=True,
                    help="Fetch payouts, financials, ratios for all stocks (parallel fetching for speed)"):
            stocks_df = get_cached_stocks_df()
            stock_symbols = stocks_df['symbol'].tolist() if not stocks_df.empty else []
            
            if stock_symbols:
                st.info(f"Fetching company info for {len(stock_symbols)} stocks...")
                
                with st.spinner("Fetching company info for all stocks (parallel)..."):
                    # Time the operation
                    import time
                    start_time = time.time()
                    results = fetch_and_save_all_company_info(stock_symbols)
                    end_time = time.time()
                    
                    # Calculate timing
                    elapsed = end_time - start_time
                    if elapsed < 1:
                        time_str = f"{elapsed*1000:.0f}ms"
                    elif elapsed < 60:
                        time_str = f"{elapsed:.1f}s"
                    else:
                        time_str = f"{elapsed/60:.1f}min"
                    
                    # Show results
                    errors = [f"{s}: {e}" for s, e in results if e]
                    success_count = len([r for r in results if not r[1]])
                    
                    if errors:
                        st.warning(f"⚠️ {len(errors)} errors occurred:\n" + "\n".join(errors[:3]) + ("..." if len(errors) > 3 else ""))
                    
                    if success_count > 0:
                        st.success(f"✅ Successfully updated company info for {success_count}/{len(stock_symbols)} stocks")
                    
                    st.success(f"⚡ Completed in {time_str} using parallel fetching!")
            else:
                st.warning("No stocks found. Add some stocks first in 'Manage Stock Symbols' section.")
    
    # Trade Logging Section
    with st.expander("📝 Log Trade", expanded=False):
        with st.form("trade_form"):
            trade_symbol = st.selectbox("Symbol", portfolio_symbols, key="trade_symbol", 
                                       help="Select symbol for trade") if portfolio_symbols else None
            trade_type = st.selectbox("Type", ["Buy", "Sell"], key="trade_type", help="Buy or Sell")
            col1, col2 = st.columns(2)
            with col1:
                trade_qty = st.number_input("Quantity", min_value=1.0, step=1.0, key="trade_qty", 
                                          help="Number of shares")
            with col2:
                trade_price = st.number_input("Price", min_value=0.0, step=0.01, key="trade_price", 
                                            help="Trade price per share")
            trade_date = st.date_input("Date", value=datetime.now().date(), key="trade_date", 
                                     help="Trade date")
            trade_notes = st.text_input("Notes", key="trade_notes", help="Optional notes",
                                       placeholder="Trade notes (optional)")
            submitted = st.form_submit_button("💾 Add Trade", use_container_width=True)
            if submitted and trade_symbol:
                db = get_mongo()
                db.trades.insert_one({
                    'symbol': trade_symbol,
                    'trade_type': trade_type,
                    'quantity': trade_qty,
                    'price': trade_price,
                    'trade_date': trade_date.isoformat(),
                    'notes': trade_notes
                })
                st.success("Trade logged successfully!")
                st.rerun()
    
    # Alerts Management Section
    with st.expander("🔔 Price Alerts", expanded=False):
        if portfolio_symbols:
            alert_symbol = st.selectbox("Symbol", portfolio_symbols, key="alert_symbol", 
                                      help="Select symbol for alert")
            col1, col2 = st.columns(2)
            with col1:
                min_price = st.number_input("Min Price", min_value=0.0, step=0.01, 
                                          key="min_price", help="Alert if price goes below")
            with col2:
                max_price = st.number_input("Max Price", min_value=0.0, step=0.01, 
                                          key="max_price", help="Alert if price goes above")
            enabled = st.checkbox("Enabled", value=True, key="alert_enabled")
            if st.button("💾 Save Alert", use_container_width=True):
                add_alert(alert_symbol, min_price, max_price, enabled)
                st.success(f"Alert set for {alert_symbol}.")
                st.rerun()
        else:
            st.info("Add trades to see symbols for alerts")
    
    # --- Stocks Management Section ---
    with st.expander("🏦 Manage Stock Symbols", expanded=False):
        # Use fast symbol-only fetch for UI display
        stock_symbols = get_stock_symbols_only()
        # Remove symbol UI
        if stock_symbols:
            remove_col1, remove_col2 = st.columns([3,1])
            with remove_col1:
                symbol_to_remove = st.selectbox("Select Symbol to Remove", stock_symbols, key="remove_stock_select")
            with remove_col2:
                st.markdown("<div style='height:1.7em'></div>", unsafe_allow_html=True)
                if st.button("❌", key="remove_stock_btn", use_container_width=True):
                    if symbol_to_remove:
                        delete_stock(symbol_to_remove)
                        st.success(f"Removed symbol: {symbol_to_remove}")
                        st.rerun()
        else:
            st.info("No stocks added yet.")
        # Add symbol UI
        with st.form("add_stock_form"):
            new_stock = st.text_input("Add New Symbol", max_chars=10, key="add_stock_input")
            if st.form_submit_button("➕ Add Symbol", use_container_width=True):
                if new_stock:
                    add_stock(new_stock)
                    st.success(f"Added symbol: {new_stock.upper()}")
                    st.rerun()

# --- Optimized Data Fetching with Caching ---
@st.cache_data(ttl=300, show_spinner=False)
def get_price_history_df(symbols):
    db = get_mongo()
    price_history = list(db.prices.find({"symbol": {"$in": symbols}}))
    return pd.DataFrame(price_history)

@st.cache_data(ttl=300, show_spinner=False)
def get_trades_df():
    db = get_mongo()
    trades = list(db.trades.find())
    return pd.DataFrame(trades)

# --- Main Content Area ---
st.title("📈 PSX Portfolio Dashboard")

# Fetch all data ONCE, filter in-memory for charts
price_hist_df = get_price_history_df(portfolio_symbols)
trades_df = get_trades_df()
alerts_df = get_alerts()

# Pre-load stock symbols on app startup for instant tab switching
# This is a small, fast query that prevents delays on first tab load
try:
    stock_symbols_preloaded = get_stock_symbols_only()
except:
    stock_symbols_preloaded = []

# Auto-refresh every 60 seconds
REFRESH_INTERVAL = 300
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()

if time.time() - st.session_state['last_refresh'] > REFRESH_INTERVAL:
    fetch_and_save_all(portfolio_symbols)
    st.session_state['last_refresh'] = time.time()
    st.rerun()

# Status bar
status_col1, status_col2 = st.columns([3, 1])
# with status_col1:
#     pk_tz = pytz.timezone('Asia/Karachi')
#     last_refresh_dt = datetime.fromtimestamp(st.session_state['last_refresh'], tz=pk_tz)
#     st.info(f"Auto-refresh every {REFRESH_INTERVAL//60} minutes. Last refresh: {last_refresh_dt.strftime('%Y-%m-%d %I:%M:%S %p')} (PKT)")
# with status_col2:
#     if st.button("🔄 Manual Refresh", use_container_width=True):
#         with st.spinner("Refreshing data..."):
#             fetch_and_save_all(portfolio_symbols)
#             st.session_state['last_refresh'] = time.time()
#             st.success("Data refreshed!")
#             time.sleep(1)
#             st.rerun()

# --- Portfolio Data Functions ---
def get_latest_prices():
    db = get_mongo()
    # For each symbol, get the most recent price record (by fetched_at)
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

def get_alerts():
    db = get_mongo()
    rows = list(db.alerts.find())
    df = pd.DataFrame(rows)
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    return df

def get_trades_with_pct_change(trades_df, prices_df):
    # Add 'Percentage Change' and 'P/L Amount' columns to each trade row
    db = get_mongo()
    trades_df = trades_df.copy()
    trades_df['Percentage Change'] = None
    trades_df['P/L Amount'] = None
    for idx, row in trades_df.iterrows():
        symbol = row['symbol']
        trade_price = row['price']
        quantity = row['quantity'] if 'quantity' in row else 0
        trade_type = row['trade_type'] if 'trade_type' in row else 'Buy'
        # Always get the latest price for this symbol from the DB
        latest_price_doc = db.prices.find({"symbol": symbol}).sort("fetched_at", -1).limit(1)
        latest_price = None
        for doc in latest_price_doc:
            latest_price = doc.get('price')
        if latest_price and trade_price:
            pct = ((latest_price - trade_price) / trade_price) * 100
            trades_df.at[idx, 'Percentage Change'] = f"{pct:.2f}"
            # For Buy trades, P/L = (latest - buy) * qty; for Sell, can be 0 or (sell - latest) * qty
            if trade_type == 'Buy':
                pl = (latest_price - trade_price) * quantity
            elif trade_type == 'Sell':
                pl = (trade_price - latest_price) * quantity
            else:
                pl = 0
            trades_df.at[idx, 'P/L Amount'] = f"{pl:.2f}"
    return trades_df

prices_df = get_latest_prices()
trades_df = get_trades()
alerts_df = get_alerts()

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
            'Shares Held': int(round(net_qty)),
            'Avg Buy Price': round(avg_buy, 2),
            'Latest Price': round(latest_price, 2) if latest_price is not None else None,
            'Change %': latest_percentage,
            'Market Value': round(market_value, 2),
            'Investment': round(investment, 2),
            '% Up/Down': round(percent_updown, 2),
            'Unrealized P/L': round(unrealized_pl, 2),
            'Last Update': last_update
        })
    total_percent_updown = ((total_market_value - total_investment) / total_investment * 100) if total_investment > 0 else 0
    return pd.DataFrame(summary), total_investment, total_market_value, total_unrealized_pl, total_percent_updown

portfolio_df, total_investment, total_market_value, total_unrealized_pl, total_percent_updown = calc_portfolio(prices_df, trades_df)

# --- Realized Profit Calculation ---
def calc_realized_profit(trades_df):
    realized = 0.0
    if trades_df.empty:
        return 0.0
    for symbol in trades_df['symbol'].unique():
        symbol_trades = trades_df[trades_df['symbol'] == symbol].sort_values('trade_date')
        # Build FIFO buy queue: list of [qty_remaining, price]
        buy_queue = []
        for _, row in symbol_trades.iterrows():
            if row['trade_type'] == 'Buy':
                buy_queue.append([row['quantity'], row['price']])
            elif row['trade_type'] == 'Sell':
                qty_to_sell = row['quantity']
                sell_price = row['price']
                # FIFO: match sell to earliest buys
                while qty_to_sell > 0 and buy_queue:
                    buy_qty, buy_price = buy_queue[0]
                    matched_qty = min(qty_to_sell, buy_qty)
                    realized += (sell_price - buy_price) * matched_qty
                    buy_queue[0][0] -= matched_qty
                    qty_to_sell -= matched_qty
                    if buy_queue[0][0] == 0:
                        buy_queue.pop(0)
    return realized

realized_profit = calc_realized_profit(trades_df)

# --- Dashboard Layout ---
st.subheader("Portfolio Overview")

# Portfolio metrics
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("💰 Total Investment", f"Rs. {total_investment:,.2f}")
with col2:
    st.metric("📈 Market Value", f"Rs. {total_market_value:,.2f}")
with col3:
    st.metric("📊 Unrealized P/L", f"Rs. {total_unrealized_pl:,.2f}")
with col4:
    st.metric("💵 Realized Profit", f"Rs. {realized_profit:,.2f}")
with col5:
    st.metric("🔄 % Change", f"{total_percent_updown:+.2f}%")

# Portfolio visualization and data with enhanced tabs
if not portfolio_df.empty and portfolio_df['Market Value'].sum() > 0:
    # Create tabs with icons and better styling
    tab_labels = [
        "📊 Portfolio Details",
        "📈 Performance Analytics",
        "💼 Trade History",
        "📊 Stock Analytics & Comparison",
        "🔮 Future Predictor",
        "🔔 Alerts Management"
    ]
    tab1, tab2, tab3, tab5, tab6, tab4 = st.tabs(tab_labels)
    # --- New Tab: Stock Analytics & Comparison ---
    # tab5_label = "📊 Stock Analytics & Comparison"
    # tabs = [tab1, tab2, tab3, tab4]
    # tab5 = st.tabs([tab5_label])[0]
    # tabs.append(tab5)
    # --- End Tab Setup ---

    with tab1:
        st.markdown("### Portfolio Holdings")
        
        # Color coding for table
        def colorize(val, pos_color='#00E396', neg_color='#FF4560'):
            if pd.isnull(val):
                return ''
            try:
                if isinstance(val, str) and '%' in val:
                    v = float(val.replace('%', ''))
                else:
                    v = float(val)
                if v > 0:
                    return f'color: {pos_color}; font-weight: bold;'
                elif v < 0:
                    return f'color: {neg_color}; font-weight: bold;'
            except:
                pass
            return ''

        styled_df = portfolio_df.style.applymap(colorize, subset=['% Up/Down', 'Unrealized P/L', 'Change %'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Shares Held": st.column_config.NumberColumn(format="%d"),
                "Avg Buy Price": st.column_config.NumberColumn(format="%.2f"),
                "Latest Price": st.column_config.NumberColumn(format="%.2f"),
                "Market Value": st.column_config.NumberColumn(format="%.2f"),
                "Investment": st.column_config.NumberColumn(format="%.2f"),
                "% Up/Down": st.column_config.NumberColumn(format="%.2f%%"),
                "Unrealized P/L": st.column_config.NumberColumn(format="%.2f"),
            }
        )
        
        st.download_button('📥 Download Portfolio (CSV)', portfolio_df.to_csv(index=False), 
                          file_name='psx_portfolio.csv', mime='text/csv', use_container_width=True)
    
    with tab2:
        st.markdown("### Performance Analytics")
        
        if not portfolio_df.empty:
            # Create two columns for charts
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.markdown("#### Portfolio Allocation")
                pie_df = portfolio_df[portfolio_df['Market Value'] > 0][['Symbol', 'Market Value']]
                
                fig = go.Figure(data=[go.Pie(
                    labels=pie_df['Symbol'],
                    values=pie_df['Market Value'],
                    hole=.4,
                    marker_colors=['#1E88E5', '#FF4560', '#00E396', '#FEB019', '#775DD0', '#3F51B5', '#546E7A', '#D4526E', '#8D5B4C', '#F86624']
                )])
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#A0AEC0'),
                    showlegend=True,
                    legend=dict(orientation='h', y=-0.1),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with chart_col2:
                st.markdown("#### Performance Overview")
                # Performance bar chart
                perf_df = portfolio_df[['Symbol', '% Up/Down']].copy()
                perf_df['Color'] = perf_df['% Up/Down'].apply(lambda x: '#00E396' if x >= 0 else '#FF4560')
                fig = go.Figure(data=[go.Bar(
                    x=perf_df['Symbol'],
                    y=perf_df['% Up/Down'],
                    marker_color=perf_df['Color']
                )])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#A0AEC0'),
                    yaxis=dict(title='% Change'),
                    xaxis=dict(title='Symbol'),
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # --- Performance Metrics Cards ---
            st.markdown("#### Performance Metrics")
            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
            # Best Performer
            best_row = portfolio_df.loc[portfolio_df['% Up/Down'].idxmax()] if not portfolio_df.empty else None
            worst_row = portfolio_df.loc[portfolio_df['% Up/Down'].idxmin()] if not portfolio_df.empty else None
            largest_row = portfolio_df.loc[portfolio_df['Market Value'].idxmax()] if not portfolio_df.empty else None
            total_gain = total_market_value - total_investment
            with perf_col1:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #23243a 0%, #1e2130 100%); border-radius: 16px; padding: 1.2rem 1rem 1rem 1rem; box-shadow: 0 2px 16px 0 #1e88e522; border: 1.5px solid #1E88E5;'>
                    <div style='color:#A0AEC0; font-size:1.1rem; font-weight:600; margin-bottom:0.2rem;'>🚀 Best Performer</div>
                    <div style='font-size:2rem; font-weight:700; color:#fff;'>{best_row['Symbol'] if best_row is not None else '-'}</div>
                    <div style='color:#00E396; font-size:1.1rem; font-weight:600; margin-top:0.2rem;'>↑ {f"{best_row['% Up/Down']:.2f}" if best_row is not None else '--'}%</div>
                </div>""", unsafe_allow_html=True)
            with perf_col2:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #23243a 0%, #1e2130 100%); border-radius: 16px; padding: 1.2rem 1rem 1rem 1rem; box-shadow: 0 2px 16px 0 #ff456022; border: 1.5px solid #FF4560;'>
                    <div style='color:#A0AEC0; font-size:1.1rem; font-weight:600; margin-bottom:0.2rem;'>📉 Worst Performer</div>
                    <div style='font-size:2rem; font-weight:700; color:#fff;'>{worst_row['Symbol'] if worst_row is not None else '-'}</div>
                    <div style='color:#FF4560; font-size:1.1rem; font-weight:600; margin-top:0.2rem;'>↓ {f"{abs(worst_row['% Up/Down']):.2f}" if worst_row is not None else '--'}%</div>
                </div>""", unsafe_allow_html=True)
            with perf_col3:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #23243a 0%, #1e2130 100%); border-radius: 16px; padding: 1.2rem 1rem 1rem 1rem; box-shadow: 0 2px 16px 0 #feb01922; border: 1.5px solid #FEB019;'>
                    <div style='color:#A0AEC0; font-size:1.1rem; font-weight:600; margin-bottom:0.2rem;'>🏆 Largest Holding</div>
                    <div style='font-size:2rem; font-weight:700; color:#fff;'>{largest_row['Symbol'] if largest_row is not None else '-'}</div>
                    <div style='color:#00E396; font-size:1.1rem; font-weight:600; margin-top:0.2rem;'>Rs. {f"{largest_row['Market Value']:,.2f}" if largest_row is not None else '--'}</div>
                </div>""", unsafe_allow_html=True)
            with perf_col4:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #23243a 0%, #1e2130 100%); border-radius: 16px; padding: 1.2rem 1rem 1rem 1rem; box-shadow: 0 2px 16px 0 #00e39622; border: 1.5px solid #00E396;'>
                    <div style='color:#A0AEC0; font-size:1.1rem; font-weight:600; margin-bottom:0.2rem;'>💵 Total Gain/Loss</div>
                    <div style='font-size:2rem; font-weight:700; color:#fff;'>Rs. {total_gain:,.2f}</div>
                    <div style='color: {'#00E396' if total_gain >= 0 else '#FF4560'}; font-size:1.1rem; font-weight:600; margin-top:0.2rem;'>{'↑ Gain' if total_gain >= 0 else '↓ Loss'}</div>
                </div>""", unsafe_allow_html=True)
            # --- New Graph: Portfolio Value Over Time ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### Portfolio Value Over Time")
            db = get_mongo()
            # Get all price history for portfolio symbols
            price_history = list(db.prices.find({"symbol": {"$in": portfolio_symbols}}))
            if price_history:
                price_hist_df = pd.DataFrame(price_history)
                price_hist_df['fetched_at'] = pd.to_datetime(price_hist_df['fetched_at'], errors='coerce', utc=True)
                price_hist_df = price_hist_df.dropna(subset=['fetched_at'])
                price_hist_df = price_hist_df.sort_values('fetched_at')
                trades_df['trade_date'] = pd.to_datetime(trades_df['trade_date'], errors='coerce', utc=True)
                # Build a DataFrame of all unique timestamps
                all_times = price_hist_df['fetched_at'].sort_values().unique()
                pk_tz = pytz.timezone('Asia/Karachi')
                # Precompute net shares for each symbol at each timestamp (vectorized)
                portfolio_value = []
                for t in all_times:
                    # For each symbol, get net shares held up to t
                    mask = (trades_df['trade_date'] <= t)
                    trades_until = trades_df[mask]
                    if trades_until.empty:
                        portfolio_value.append({'timestamp': t.tz_convert(pk_tz), 'Portfolio Value': 0})
                        continue
                    net_qty = trades_until.groupby(['symbol', 'trade_type'])['quantity'].sum().unstack(fill_value=0)
                    net_qty['net'] = net_qty.get('Buy', 0) - net_qty.get('Sell', 0)
                    # For each symbol, get latest price up to t
                    latest_prices = price_hist_df[price_hist_df['fetched_at'] <= t].sort_values('fetched_at').groupby('symbol').tail(1)
                    merged = net_qty[['net']].merge(latest_prices[['symbol', 'price']], left_index=True, right_on='symbol', how='left')
                    merged['value'] = merged['net'] * merged['price']
                    total_value = merged['value'].sum()
                    portfolio_value.append({'timestamp': t.tz_convert(pk_tz), 'Portfolio Value': total_value})
                pv_df = pd.DataFrame(portfolio_value)
                # --- Date Range Filter for Portfolio Value Over Time ---
                if not pv_df.empty:
                    min_date = pv_df['timestamp'].min().date()
                    max_date = pv_df['timestamp'].max().date()
                    date_range = st.date_input(
                        "Select Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                        key="portfolio_value_date_range"
                    )
                    if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
                        start_date, end_date = date_range
                        mask = (pv_df['timestamp'].dt.date >= start_date) & (pv_df['timestamp'].dt.date <= end_date)
                        pv_df = pv_df[mask]
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=pv_df['timestamp'],
                    y=pv_df['Portfolio Value'],
                    mode='lines+markers',
                    name='Portfolio Value',
                    line=dict(color='#1E88E5', width=3),
                    marker=dict(size=8, color='#1E88E5', opacity=0.85, line=dict(width=1, color='#fff')),
                    hovertemplate='<b>Date/Time:</b> %{x|%b %d, %Y %I:%M %p}<br><b>Value:</b> Rs. %{y:,.0f}<extra></extra>'
                ))
                fig2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#A0AEC0'),
                    yaxis=dict(title='Portfolio Value (Rs.)', tickformat=',', separatethousands=True),
                    xaxis=dict(title='Date/Time (PKT)', tickangle=30, showgrid=True, tickformat='%b %d\n%I:%M %p'),
                    height=400,
                    hovermode='x unified',
                    margin=dict(l=40, r=20, t=30, b=60)
                )
                st.plotly_chart(fig2, use_container_width=True)
                # --- Normalized Price Trend Chart (Optimized) ---
                st.markdown("#### Normalized Price Trend (Compare Symbols)")
                norm_symbols = st.multiselect(
                    "Select Symbols to Compare",
                    options=portfolio_symbols,
                    default=portfolio_symbols,
                    key="norm_price_symbols"
                )
                norm_price_df = price_hist_df[price_hist_df['symbol'].isin(norm_symbols)].copy()
                norm_price_df['fetched_at_pkt'] = norm_price_df['fetched_at'].dt.tz_convert(pk_tz)
                # Filter for trading hours (8:00 to 16:00 PKT)
                norm_price_df = norm_price_df[
                    (norm_price_df['fetched_at_pkt'].dt.time >= pd.to_datetime('08:00').time()) &
                    (norm_price_df['fetched_at_pkt'].dt.time <= pd.to_datetime('16:00').time())
                ]
                if not norm_price_df.empty:
                    min_norm_date = norm_price_df['fetched_at_pkt'].min().date()
                    max_norm_date = norm_price_df['fetched_at_pkt'].max().date()
                    norm_date_range = st.date_input(
                        "Select Date Range for Price Trend",
                        value=(min_norm_date, max_norm_date),
                        min_value=min_norm_date,
                        max_value=max_norm_date,
                        key="norm_price_date_range"
                    )
                    if norm_date_range and isinstance(norm_date_range, tuple) and len(norm_date_range) == 2:
                        norm_start, norm_end = norm_date_range
                        norm_price_df = norm_price_df[(norm_price_df['fetched_at_pkt'].dt.date >= norm_start) & (norm_price_df['fetched_at_pkt'].dt.date <= norm_end)]
                def normalize_group(df):
                    if df.empty:
                        return df
                    first_price = df.iloc[0]['price']
                    df = df.assign(norm_price=df['price'] / first_price if first_price else None)
                    return df
                norm_price_df = norm_price_df.sort_values(['symbol', 'fetched_at_pkt'])
                norm_price_df = norm_price_df.groupby('symbol', group_keys=False).apply(normalize_group)
                # --- Use trading slot index as x-axis to remove non-trading hour gaps ---
                fig_norm = go.Figure()
                for symbol in norm_symbols:
                    sym_df = norm_price_df[norm_price_df['symbol'] == symbol].sort_values('fetched_at_pkt').copy()
                    if not sym_df.empty:
                        sym_df = sym_df.reset_index(drop=True)
                        sym_df['slot_idx'] = range(len(sym_df))
                        fig_norm.add_trace(go.Scatter(
                            x=sym_df['slot_idx'],
                            y=sym_df['norm_price'],
                            mode='lines+markers',
                            name=symbol,
                            line=dict(width=2),
                            marker=dict(size=6, opacity=0.8),
                            hovertemplate=f'<b>{symbol}</b><br>Date/Time: %{{customdata|%b %d %H:%M}}<br>Norm. Price: %{{y:.2f}}<extra></extra>',
                            customdata=sym_df['fetched_at_pkt']
                        ))
                all_slots = norm_price_df.sort_values('fetched_at_pkt').reset_index(drop=True)
                all_slots['slot_idx'] = range(len(all_slots))
                tick_step = max(1, len(all_slots) // 10)
                tickvals = all_slots['slot_idx'][::tick_step].tolist()
                ticktext = all_slots['fetched_at_pkt'][::tick_step].dt.strftime('%b %d\n%H:%M').tolist()
                fig_norm.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#A0AEC0'),
                    yaxis=dict(title='Normalized Price (Start=1.0)', tickformat='.2f'),
                    xaxis=dict(
                        title='Date/Time (8am–4pm, trading hours only)',
                        tickmode='array',
                        tickvals=tickvals,
                        ticktext=ticktext,
                        tickangle=30,
                        showgrid=True
                    ),
                    height=650,
                    hovermode='x unified',
                    margin=dict(l=40, r=20, t=30, b=60)
                )
                st.plotly_chart(fig_norm, use_container_width=True)
            else:
                st.info("Not enough price history to plot portfolio value over time.")
    
    with tab3:
        st.markdown("### Trade History")
        # --- Date Range Filter ---
        min_date = trades_df['trade_date'].min() if not trades_df.empty else None
        max_date = trades_df['trade_date'].max() if not trades_df.empty else None
        date_range = None
        if min_date and max_date:
            min_date_obj = pd.to_datetime(min_date).date()
            max_date_obj = pd.to_datetime(max_date).date()
            date_range = st.date_input(
                "Filter by Date Range",
                value=(min_date_obj, max_date_obj),
                min_value=min_date_obj,
                max_value=max_date_obj,
                key="trade_date_range"
            )
        if not trades_df.empty:
            selected_symbol = st.selectbox("Filter by Symbol", ["All"] + portfolio_symbols, key="trade_filter")
            if selected_symbol != "All":
                filtered_trades = trades_df[trades_df['symbol'] == selected_symbol]
            else:
                filtered_trades = trades_df
            # --- Apply date filter if selected ---
            if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                filtered_trades = filtered_trades[(pd.to_datetime(filtered_trades['trade_date']).dt.date >= start_date) & (pd.to_datetime(filtered_trades['trade_date']).dt.date <= end_date)]
            if not filtered_trades.empty:
                filtered_trades = filtered_trades.sort_values('trade_date', ascending=False)
                # Add percentage change and P/L amount columns
                filtered_trades = get_trades_with_pct_change(filtered_trades, prices_df)
                # --- Calculate total invested for filtered trades (Buy only) ---
                total_invested = filtered_trades[filtered_trades['trade_type'] == 'Buy'].apply(lambda row: row['quantity'] * row['price'], axis=1).sum() if not filtered_trades.empty else 0
                # Trade statistics
                trade_col1, trade_col2, trade_col3, trade_col4, trade_col5 = st.columns([1,1,1,1.5,1.5])
                with trade_col1:
                    total_trades = len(filtered_trades)
                    st.metric("Total Trades", total_trades)
                with trade_col2:
                    buy_trades = len(filtered_trades[filtered_trades['trade_type'] == 'Buy'])
                    st.metric("Buy Orders", buy_trades)
                with trade_col3:
                    sell_trades = len(filtered_trades[filtered_trades['trade_type'] == 'Sell'])
                    st.metric("Sell Orders", sell_trades)
                with trade_col4:
                    st.metric(
                        label="Total Invested",
                        value=f"Rs. {total_invested:,.2f}",
                        help=f"Total Invested: Rs. {total_invested:,.2f}"
                    )
                with trade_col5:
                    total_pl = filtered_trades['P/L Amount'].dropna().astype(float).sum()
                    st.metric(
                        label="Total P/L",
                        value=f"Rs. {total_pl:,.2f}",
                        help=f"Total P/L: Rs. {total_pl:,.2f}"
                    )
                # Color function for percentage change and P/L amount
                def pct_color(val):
                    try:
                        v = float(val)
                        if v > 0:
                            return 'color: #00E396; font-weight: bold;'
                        elif v < 0:
                            return 'color: #FF4560; font-weight: bold;'
                    except:
                        pass
                    return ''
                styled_trades = filtered_trades.copy()
                if 'quantity' in styled_trades.columns:
                    styled_trades['quantity'] = styled_trades['quantity'].apply(lambda x: int(round(x)) if pd.notnull(x) else x)
                if 'price' in styled_trades.columns:
                    styled_trades['price'] = styled_trades['price'].apply(lambda x: round(x, 2) if pd.notnull(x) else x)
                styled_trades = styled_trades.style.applymap(pct_color, subset=['Percentage Change', 'P/L Amount'])
                st.dataframe(
                    styled_trades,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'quantity': st.column_config.NumberColumn(format="%d"),
                        'price': st.column_config.NumberColumn(format="%.2f"),
                    }
                )
            else:
                st.info("No trades for selected symbol.")
        else:
            st.info("No trade history available.")

        # --- Professional Analytics Dropdown ---
        st.markdown("---")
        st.markdown("### 📊 Trade Analytics")

        # Helper: Ensure P/L Amount column exists and is numeric
        def ensure_pl_amount(df, prices_df=None):
            if 'P/L Amount' not in df.columns:
                # Use get_trades_with_pct_change if available
                if prices_df is not None:
                    try:
                        df = get_trades_with_pct_change(df, prices_df)
                    except Exception:
                        df['P/L Amount'] = 0.0
                else:
                    df['P/L Amount'] = 0.0
            # Ensure numeric
            df['P/L Amount'] = pd.to_numeric(df['P/L Amount'], errors='coerce').fillna(0.0)
            return df

        # Date filter for analytics
        analytics_min_date = trades_df['trade_date'].min() if not trades_df.empty else None
        analytics_max_date = trades_df['trade_date'].max() if not trades_df.empty else None
        analytics_date_range = None
        if analytics_min_date and analytics_max_date:
            analytics_min_date_obj = pd.to_datetime(analytics_min_date).date()
            analytics_max_date_obj = pd.to_datetime(analytics_max_date).date()
            analytics_date_range = st.date_input(
                "Filter Analytics by Date Range",
                value=(analytics_min_date_obj, analytics_max_date_obj),
                min_value=analytics_min_date_obj,
                max_value=analytics_max_date_obj,
                key="analytics_date_range"
            )
        # Filter trades_df for analytics
        filtered_trades = trades_df.copy()
        if analytics_date_range and isinstance(analytics_date_range, tuple) and len(analytics_date_range) == 2:
            start_date, end_date = analytics_date_range
            filtered_trades = filtered_trades[(pd.to_datetime(filtered_trades['trade_date']).dt.date >= start_date) & (pd.to_datetime(filtered_trades['trade_date']).dt.date <= end_date)]
        # Ensure P/L Amount is present and numeric
        filtered_trades = ensure_pl_amount(filtered_trades, prices_df if 'prices_df' in globals() else None)

        analytics_options = [
            "Monthly Investment per Symbol",
            "Monthly Buy/Sell Volume",
            "Cumulative Investment vs. P/L",
            "Win Rate & Average Return",
"Portfolio Allocation by Investment"
        ]
        selected_analytics = st.selectbox("Select Analytics to View", analytics_options, key="trade_analytics_select")

        import plotly.express as px
        import plotly.graph_objects as go
        import numpy as np

        if selected_analytics == "Monthly Investment per Symbol":
            st.markdown("Shows how much you invested in each symbol per month. Helps spot concentration and diversification.")
            if not filtered_trades.empty:
                filtered_trades['trade_date'] = pd.to_datetime(filtered_trades['trade_date'], errors='coerce')
                filtered_trades['month'] = filtered_trades['trade_date'].dt.to_period('M').astype(str)
                monthly_invest = filtered_trades[filtered_trades['trade_type'] == 'Buy'].groupby(['month', 'symbol']).apply(
                    lambda x: (x['quantity'] * x['price']).sum()).reset_index(name='Invested')
                fig = px.bar(monthly_invest, x='month', y='Invested', color='symbol', barmode='group',
                             title='Monthly Investment per Symbol')
                fig.update_layout(xaxis_title='Month', yaxis_title='Invested Amount (Rs.)', height=400,
                                 paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#A0AEC0'))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for selected date range.")

        elif selected_analytics == "Monthly Buy/Sell Volume":
            st.markdown("Shows the number of shares bought and sold per symbol each month. Helps visualize trading activity.")
            if not filtered_trades.empty:
                filtered_trades['trade_date'] = pd.to_datetime(filtered_trades['trade_date'], errors='coerce')
                filtered_trades['month'] = filtered_trades['trade_date'].dt.to_period('M').astype(str)
                buy_vol = filtered_trades[filtered_trades['trade_type'] == 'Buy'].groupby(['month', 'symbol'])['quantity'].sum().reset_index(name='Buy Volume')
                sell_vol = filtered_trades[filtered_trades['trade_type'] == 'Sell'].groupby(['month', 'symbol'])['quantity'].sum().reset_index(name='Sell Volume')
                merged = pd.merge(buy_vol, sell_vol, on=['month', 'symbol'], how='outer').fillna(0)
                melted = merged.melt(id_vars=['month', 'symbol'], value_vars=['Buy Volume', 'Sell Volume'], var_name='Type', value_name='Volume')
                fig = px.bar(melted, x='month', y='Volume', color='Type', barmode='group', facet_col='symbol',
                             title='Monthly Buy/Sell Volume per Symbol')
                fig.update_layout(xaxis_title='Month', yaxis_title='Volume', height=400,
                                 paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#A0AEC0'))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for selected date range.")

        elif selected_analytics == "Cumulative Investment vs. P/L":
            st.markdown("Tracks your cumulative investment and cumulative P/L over time. Helps you see growth and drawdowns.")
            if not filtered_trades.empty:
                filtered_trades['trade_date'] = pd.to_datetime(filtered_trades['trade_date'], errors='coerce')
                filtered_trades = filtered_trades.sort_values('trade_date')
                filtered_trades['invested'] = np.where(filtered_trades['trade_type'] == 'Buy', filtered_trades['quantity'] * filtered_trades['price'], 0)
                filtered_trades['pl'] = filtered_trades['P/L Amount']
                filtered_trades['cum_invested'] = filtered_trades['invested'].cumsum()
                filtered_trades['cum_pl'] = filtered_trades['pl'].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=filtered_trades['trade_date'], y=filtered_trades['cum_invested'], mode='lines+markers', name='Cumulative Invested', line=dict(color='#1E88E5')))
                fig.add_trace(go.Scatter(x=filtered_trades['trade_date'], y=filtered_trades['cum_pl'], mode='lines+markers', name='Cumulative P/L', line=dict(color='#00E396')))
                fig.update_layout(title='Cumulative Investment vs. Cumulative P/L', xaxis_title='Date', yaxis_title='Amount (Rs.)', height=400,
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#A0AEC0'))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for selected date range.")

        elif selected_analytics == "Win Rate & Average Return":
            st.markdown("Shows your win rate (profitable trades %) and average return per trade. Helps assess trading effectiveness.")
            if not filtered_trades.empty:
                filtered_trades['pl'] = filtered_trades['P/L Amount']
                wins = filtered_trades[filtered_trades['pl'] > 0]
                losses = filtered_trades[filtered_trades['pl'] < 0]
                total_trades = len(filtered_trades)
                win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
                avg_return = filtered_trades['pl'].mean() if total_trades > 0 else 0
                best_trade = filtered_trades['pl'].max() if total_trades > 0 else 0
                worst_trade = filtered_trades['pl'].min() if total_trades > 0 else 0
                st.metric("Win Rate", f"{win_rate:.2f}%")
                st.metric("Average Return per Trade", f"Rs. {avg_return:.2f}")
                st.metric("Best Trade", f"Rs. {best_trade:.2f}")
                st.metric("Worst Trade", f"Rs. {worst_trade:.2f}")
                # Pie chart for win/loss
                fig = px.pie(names=['Wins', 'Losses'], values=[len(wins), len(losses)],
                             title='Win vs. Loss Trades', color_discrete_sequence=['#00E396', '#FF4560'])
                fig.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#A0AEC0'))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for selected date range.")

        elif selected_analytics == "Portfolio Allocation by Investment":
            st.markdown("Shows what percentage of your total investment went to each symbol. Helps visualize portfolio concentration.")
            if not filtered_trades.empty:
                # Calculate total investment per symbol (only Buy trades)
                buy_trades = filtered_trades[filtered_trades['trade_type'] == 'Buy']
                if not buy_trades.empty:
                    symbol_investment = buy_trades.groupby('symbol').apply(
                        lambda x: (x['quantity'] * x['price']).sum()
                    ).reset_index(name='Total Investment')
                    
                    # Create pie chart
                    fig = px.pie(symbol_investment, 
                                values='Total Investment', 
                                names='symbol',
                                title='Portfolio Allocation by Investment Amount',
                                color_discrete_sequence=['#1E88E5', '#FF4560', '#00E396', '#FEB019', '#775DD0', '#3F51B5', '#546E7A', '#D4526E', '#8D5B4C', '#F86624'])
                    
                    fig.update_layout(
                        height=500,
                        paper_bgcolor='rgba(0,0,0,0)', 
                        font=dict(color='#A0AEC0'),
                        showlegend=True,
                        legend=dict(orientation='v', x=1.02, y=0.5)
                    )
                    
                    fig.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        hovertemplate='<b>%{label}</b><br>Investment: Rs. %{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show investment breakdown table
                    symbol_investment['Percentage'] = (symbol_investment['Total Investment'] / symbol_investment['Total Investment'].sum() * 100).round(2)
                    
                    # Sort by percentage descending for better display
                    symbol_investment = symbol_investment.sort_values('Percentage', ascending=False)
                    
                    # Format for display while keeping numeric sorting
                    display_df = symbol_investment.copy()
                    display_df['Total Investment'] = display_df['Total Investment'].apply(lambda x: f"Rs. {x:,.2f}")
                    
                    st.dataframe(
                        display_df[['symbol', 'Total Investment', 'Percentage']], 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "symbol": "Symbol",
                            "Total Investment": "Total Investment",
                            "Percentage": st.column_config.NumberColumn("Percentage", format="%.2f%%")
                        }
                    )
                else:
                    st.info("No buy trades found in the selected date range.")
            else:
                st.info("No data for selected date range.")
    
    with tab5:
        st.markdown("### Stock Analytics & Comparison")
        
        # Use pre-loaded data - no database calls on tab load!
        if not stock_symbols_preloaded:
            st.warning("No stocks available for analytics. Add stocks in the sidebar to get started.")
        else:
            # Clean UI - no unnecessary messages
            
            # Use pre-loaded symbols - no database calls
            def get_stock_symbols_lazy():
                return stock_symbols_preloaded
            # --- 7-Day Stock Performance Table ---
            st.markdown("#### 📈 Stock Performance Analysis")
            
            # Input controls with form to prevent auto-rerun
            with st.form("performance_analysis_form"):
                perf_col1, perf_col2, perf_col3 = st.columns([1, 2, 1])
                
                with perf_col1:
                    num_days = st.number_input(
                        "Number of Days", 
                        min_value=1, 
                        max_value=7, 
                        value=7, 
                        step=1,
                        key="performance_days",
                        help="Select how many trading days to analyze (max 7)"
                    )
                
                with perf_col2:
                    stock_source = st.selectbox(
                        "Stock Source",
                        options=["Portfolio Stocks", "System Stocks", "Both"],
                        index=2,  # Default to "Both"
                        key="stock_source",
                        help="Portfolio: from trades | System: from stocks table | Both: combined"
                    )
                
                with perf_col3:
                    st.markdown("<div style='height:1.7em'></div>", unsafe_allow_html=True)  # Align button
                    show_performance = st.form_submit_button("📊 Analyze Performance", use_container_width=True)
            
            @st.cache_data(ttl=300)  # Cache for 5 minutes
            def get_performance_data(symbols_list, days_count):
                try:
                    # Query prices from database
                    prices_collection = db.prices
                    performance_data = []
                    
                    for symbol in symbols_list:
                        row_data = {"Symbol": symbol}
                        
                        # Get recent records for this symbol (get more to ensure we have enough data)
                        recent_docs = list(prices_collection.find(
                            {"symbol": symbol},
                            sort=[("fetched_at", -1)]
                        ).limit(1000))  # High limit to ensure we get at least 30 days of data
                        

                        
                        if recent_docs:
                            from datetime import datetime
                            
                            # Group by date and keep only the latest record per date (excluding weekends)
                            date_records = {}

                            
                            for doc in recent_docs:
                                fetched_at = doc.get('fetched_at')
                                if fetched_at:
                                    # Extract date from timestamp
                                    if isinstance(fetched_at, str):
                                        try:
                                            dt = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
                                            date_str = dt.strftime('%Y-%m-%d')
                                            weekday = dt.weekday()  # Monday=0, Sunday=6
                                        except:
                                            date_str = fetched_at[:10]  # YYYY-MM-DD
                                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                                            weekday = date_obj.weekday()
                                    else:
                                        date_str = fetched_at.strftime('%Y-%m-%d')
                                        weekday = fetched_at.weekday()
                                    
                                    # Skip weekends (Saturday=5, Sunday=6)
                                    if weekday >= 5:
                                        continue
                                    
                                    # Group all records by date first
                                    if date_str not in date_records:
                                        date_records[date_str] = []
                                    date_records[date_str].append(doc)
                            

                            
                            # For each date, find the record with the latest timestamp
                            final_date_records = {}
                            for date_str, docs_for_date in date_records.items():
                                if docs_for_date:
                                    # Sort by fetched_at to get the latest one for this date
                                    latest_doc = max(docs_for_date, key=lambda x: x.get('fetched_at', ''))
                                    final_date_records[date_str] = latest_doc
                            

                            
                            # Sort dates and take the last N unique trading days
                            all_dates = sorted(final_date_records.keys(), reverse=True)
                            sorted_dates = all_dates[:days_count]
                            sorted_dates.reverse()  # Oldest to newest for display
                            

                            
                            # Extract percentages for each unique date
                            for date_str in sorted_dates:
                                doc = final_date_records[date_str]
                                percentage = doc.get('percentage', '0%')
                                
                                # Clean percentage string and convert to float
                                if isinstance(percentage, str):
                                    clean_pct = percentage.replace('%', '').strip()
                                    try:
                                        pct_value = float(clean_pct)
                                    except ValueError:
                                        pct_value = None
                                else:
                                    pct_value = float(percentage) if percentage else None
                                
                                # Format date for display (e.g., "Aug 25")
                                try:
                                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                                    display_date = date_obj.strftime('%b %d')
                                except:
                                    display_date = date_str
                                
                                row_data[display_date] = pct_value
                            
                            # Calculate net change by summing all daily percentage changes
                            daily_percentages = []
                            for date_str in sorted_dates:
                                doc = final_date_records[date_str]
                                percentage = doc.get('percentage', '0%')
                                
                                # Clean percentage string and convert to float
                                if isinstance(percentage, str):
                                    clean_pct = percentage.replace('%', '').strip()
                                    try:
                                        pct_value = float(clean_pct)
                                        daily_percentages.append(pct_value)
                                    except ValueError:
                                        pass  # Skip invalid percentages
                                else:
                                    if percentage:
                                        daily_percentages.append(float(percentage))
                            
                            # Sum all daily percentages for net change
                            if daily_percentages:
                                net_change = sum(daily_percentages)
                                row_data["_net_change"] = net_change
                                

                            else:
                                row_data["_net_change"] = None
                        else:
                            # No data for this symbol
                            row_data["_net_change"] = None
                        
                        performance_data.append(row_data)
                    
                    # Create DataFrame
                    df = pd.DataFrame(performance_data)
                    
                    # Reorder columns to put Net Change at the end
                    if not df.empty:
                        # Get all columns except Symbol and _net_change
                        date_columns = [col for col in df.columns if col not in ['Symbol', '_net_change']]
                        # Sort date columns chronologically
                        date_columns.sort()
                        
                        # Reorder: Symbol, then date columns, then Net Change
                        net_change_col = f'Net Change ({days_count}d)'
                        column_order = ['Symbol'] + date_columns + [net_change_col]
                        
                        # Rename _net_change to Net Change (Nd)
                        df = df.rename(columns={'_net_change': net_change_col})
                        
                        # Reorder columns
                        df = df.reindex(columns=column_order)
                    
                    return df
                
                except Exception as e:
                    st.error(f"Error fetching performance data: {e}")
                    import traceback
                    st.error(traceback.format_exc())
                    return pd.DataFrame()
            
            # Only generate data when button is clicked
            if show_performance:
                # Get the appropriate symbols based on selection
                if stock_source == "Portfolio Stocks":
                    analysis_symbols = portfolio_symbols
                elif stock_source == "System Stocks":
                    analysis_symbols = get_stock_symbols_lazy()
                else:  # Both
                    analysis_symbols = list(set(portfolio_symbols + get_stock_symbols_lazy()))
                
                if not analysis_symbols:
                    st.warning(f"No symbols available for {stock_source.lower()}. Add some stocks or trades first.")
                    perf_df = pd.DataFrame()
                else:
                    st.info(f"Analyzing {len(analysis_symbols)} symbols from {stock_source.lower()} for the last {num_days} trading days.")
                    perf_df = get_performance_data(analysis_symbols, num_days)
            else:
                perf_df = pd.DataFrame()
            
            if not perf_df.empty:
                # Prepare display dataframe with enhanced visuals
                display_df = perf_df.copy()
                
                # Analyze performance patterns for highlighting
                net_change_col = f'Net Change ({num_days}d)'
                percentage_cols = [col for col in display_df.columns if col not in ["Symbol", net_change_col]]
                
                # Identify consistent performers
                all_green_stocks = []  # All positive days
                all_red_stocks = []    # All negative days
                mixed_stocks = []      # Mixed performance
                
                for idx, row in display_df.iterrows():
                    symbol = row['Symbol']
                    daily_values = [row[col] for col in percentage_cols if pd.notna(row[col])]
                    
                    if daily_values:
                        if all(val > 0 for val in daily_values):
                            all_green_stocks.append(symbol)
                        elif all(val < 0 for val in daily_values):
                            all_red_stocks.append(symbol)
                        else:
                            mixed_stocks.append(symbol)
                
                # Enhanced formatting function with badges
                def format_percentage_enhanced(val, symbol, col_name):
                    if pd.isna(val) or val is None:
                        return "-"
                    
                    formatted = f"{val:.2f}%"
                    if val > 0:
                        return f"🟢 {formatted}"
                    elif val < 0:
                        return f"🔴 {formatted}"
                    else:
                        return f"⚪ {formatted}"
                
                # Keep symbols clean - no badges in the table
                
                # Format percentage columns
                for col in percentage_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df.apply(
                            lambda row: format_percentage_enhanced(row[col], row['Symbol'], col), 
                            axis=1
                        )
                
                # Format Net Change column
                if net_change_col in display_df.columns:
                    display_df[net_change_col] = display_df.apply(
                        lambda row: format_percentage_enhanced(row[net_change_col], row['Symbol'], net_change_col), 
                        axis=1
                    )
                
                # Show simple performance summary if there are consistent performers
                if all_green_stocks or all_red_stocks:
                    perf_summary = []
                    if all_green_stocks:
                        perf_summary.append(f"🚀 Consistent Gainers: {', '.join(all_green_stocks)}")
                    if all_red_stocks:
                        perf_summary.append(f"📉 Consistent Decliners: {', '.join(all_red_stocks)}")
                    
                    st.info(" | ".join(perf_summary))
                
                # Clean, simple dataframe display
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                        **{col: st.column_config.TextColumn(col, width="small") 
                           for col in display_df.columns if col != "Symbol"}
                    }
                )
                
                st.caption("🟢 Positive | 🔴 Negative | ⚪ No Change | - No Data")
                st.caption(f"*Shows the last {num_days} trading days of price data with daily percentage changes from {stock_source.lower()}.*")
                
            # else:
                # Clean UI - removed unnecessary "no data" message
            
            st.markdown("---")  # Separator
            # --- Single Stock Analytics ---
            st.markdown("#### Single Stock Analytics")
            with st.form("analytics_form"):
                # Load symbols only when form is displayed
                available_symbols = get_stock_symbols_lazy()
                if not available_symbols:
                    st.warning("No stocks available. Add stocks in the sidebar first.")
                    selected_stock = None
                    show_analytics = False
                else:
                    selected_stock = st.selectbox("Select Stock for Analysis", available_symbols, key="analytics_single_stock")
                    show_analytics = st.form_submit_button("Show Analytics")
            if show_analytics and selected_stock:
                # Load full stocks data only when analytics is requested
                stocks_df = get_cached_stocks_df()
                stock_row = stocks_df[stocks_df['symbol'] == selected_stock.upper()]
                if not stock_row.empty:
                    stock_data = stock_row.iloc[0]
                    # --- Financials ---
                    st.markdown("**Financials (Annual)**")
                    st.markdown("Click column headers to sort. Numbers are shown in millions (M), billions (B), or trillions (T) for readability.")
                    annual_fin = pd.DataFrame(stock_data['financials']['annual']) if stock_data['financials'] and 'annual' in stock_data['financials'] else pd.DataFrame()
                    if not annual_fin.empty:
                        # Remove commas before converting to float for numeric columns
                        for col in ['Mark-up Earned', 'Total Income', 'Profit after Taxation', 'EPS']:
                            if col in annual_fin.columns:
                                annual_fin[col] = annual_fin[col].astype(str).str.replace(',', '').astype(float)
                        # Format numbers for display
                        display_fin = annual_fin.copy()
                        for col in ['Mark-up Earned', 'Total Income', 'Profit after Taxation']:
                            if col in display_fin.columns:
                                display_fin[col] = display_fin[col].apply(format_international_number)
                        st.dataframe(display_fin, use_container_width=True, hide_index=True)
                        # Graph: EPS, Profit after Tax, Total Income
                        fig = go.Figure()
                        if 'EPS' in annual_fin.columns:
                            fig.add_trace(go.Bar(x=annual_fin['period'], y=annual_fin['EPS'], name='EPS'))
                        if 'Profit after Taxation' in annual_fin.columns:
                            fig.add_trace(go.Bar(x=annual_fin['period'], y=annual_fin['Profit after Taxation'], name='Profit after Taxation'))
                        if 'Total Income' in annual_fin.columns:
                            fig.add_trace(go.Bar(x=annual_fin['period'], y=annual_fin['Total Income'], name='Total Income'))
                        fig.update_layout(barmode='group', title=f"{selected_stock} Key Financials (Annual)", xaxis_title="Year", yaxis_title="Amount", height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No annual financials available.")
                    # --- Payouts ---
                    st.markdown("**Dividend Payouts**")
                    payouts = pd.DataFrame(stock_data['payouts']) if stock_data['payouts'] else pd.DataFrame()
                    if not payouts.empty:
                        st.dataframe(payouts, use_container_width=True, hide_index=True)
                    else:
                        st.info("No payout data available.")
                    # --- Ratios ---
                    st.markdown("**Key Ratios**")
                    ratios = pd.DataFrame(stock_data['ratios']) if stock_data['ratios'] else pd.DataFrame()
                    if not ratios.empty:
                        # Remove commas and parentheses before converting to float for numeric columns
                        for col in ['EPS Growth (%)', 'Net Profit Margin (%)', 'PEG']:
                            if col in ratios.columns:
                                ratios[col] = ratios[col].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
                                ratios[col] = pd.to_numeric(ratios[col], errors='coerce')
                        st.dataframe(ratios, use_container_width=True, hide_index=True)
                        # Graph: EPS Growth, Net Profit Margin
                        fig2 = go.Figure()
                        if 'EPS Growth (%)' in ratios.columns:
                            fig2.add_trace(go.Scatter(x=ratios['period'], y=ratios['EPS Growth (%)'], mode='lines+markers', name='EPS Growth (%)'))
                        if 'Net Profit Margin (%)' in ratios.columns:
                            fig2.add_trace(go.Scatter(x=ratios['period'], y=ratios['Net Profit Margin (%)'], mode='lines+markers', name='Net Profit Margin (%)'))
                        fig2.update_layout(title=f"{selected_stock} Ratios Over Time", xaxis_title="Year", yaxis_title="%", height=400)
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("No ratio data available.")
                    # --- Scoring System ---
                    st.markdown("**Stock Score (out of 10)**")
                    def score_stock(annual_fin, ratios, payouts):
                        score = 0
                        reasons = []
                        # EPS Growth
                        if not ratios.empty and 'EPS Growth (%)' in ratios.columns:
                            eps_growth = ratios['EPS Growth (%)'].astype(float).mean()
                            if eps_growth > 20:
                                score += 2
                                reasons.append("Strong EPS growth")
                            elif eps_growth > 5:
                                score += 1
                                reasons.append("Moderate EPS growth")
                            else:
                                reasons.append("Low EPS growth")
                        # Net Profit Margin
                        if not ratios.empty and 'Net Profit Margin (%)' in ratios.columns:
                            margin = ratios['Net Profit Margin (%)'].astype(float).mean()
                            if margin > 15:
                                score += 2
                                reasons.append("High profit margin")
                            elif margin > 8:
                                score += 1
                                reasons.append("Moderate profit margin")
                            else:
                                reasons.append("Low profit margin")
                        # PEG Ratio
                        if not ratios.empty and 'PEG' in ratios.columns:
                            peg = ratios['PEG'].astype(float).mean()
                            if peg < 1:
                                score += 2
                                reasons.append("Attractive PEG ratio (<1)")
                            elif peg < 2:
                                score += 1
                                reasons.append("Fair PEG ratio (<2)")
                            else:
                                reasons.append("High PEG ratio")
                        # Dividend Consistency
                        if not payouts.empty:
                            if len(payouts) >= 4:
                                score += 2
                                reasons.append("Consistent dividend payouts")
                            elif len(payouts) >= 2:
                                score += 1
                                reasons.append("Some dividend payouts")
                            else:
                                reasons.append("Few or no dividends")
                        # Recent EPS/Profit Growth
                        if not annual_fin.empty and 'EPS' in annual_fin.columns:
                            eps = annual_fin['EPS'].astype(float)
                            if len(eps) >= 2 and eps.iloc[-1] > eps.iloc[-2]:
                                score += 1
                                reasons.append("Recent EPS growth")
                        score = min(score, 10)
                        return score, reasons
                    score, reasons = score_stock(annual_fin, ratios, payouts)
                    st.metric(label="Stock Score", value=f"{score}/10")
                    st.markdown("<ul>" + "".join([f"<li>{r}</li>" for r in reasons]) + "</ul>", unsafe_allow_html=True)
            st.markdown("---")
            # --- Multi-Stock Comparison ---
            st.markdown("#### Multi-Stock Comparison")
            with st.form("multi_stock_comparison_form"):
                # Load symbols only when form is displayed
                available_symbols = get_stock_symbols_lazy()
                if not available_symbols:
                    st.warning("No stocks available. Add stocks in the sidebar first.")
                    compare_stocks = []
                    compare_submitted = False
                else:
                    default_stocks = available_symbols[:2] if len(available_symbols) >= 2 else available_symbols
                    compare_stocks = st.multiselect("Select Stocks to Compare", available_symbols, default=default_stocks, key="analytics_multi_stock")
                    compare_submitted = st.form_submit_button("Compare")
            if compare_submitted and compare_stocks:
                # Load full stocks data only when comparison is requested
                stocks_df = get_cached_stocks_df()
                comp_df = stocks_df[stocks_df['symbol'].isin(compare_stocks)]
                # Compare EPS (latest year), Profit after Tax, Net Profit Margin, PEG, Dividend Count
                comp_data = []
                for _, row in comp_df.iterrows():
                    symbol = row['symbol']
                    annual = pd.DataFrame(row['financials']['annual']) if row['financials'] and 'annual' in row['financials'] else pd.DataFrame()
                    ratios = pd.DataFrame(row['ratios']) if row['ratios'] else pd.DataFrame()
                    payouts = pd.DataFrame(row['payouts']) if row['payouts'] else pd.DataFrame()
                    # Remove commas for numeric columns in annual and ratios
                    for col in ['Mark-up Earned', 'Total Income', 'Profit after Taxation', 'EPS']:
                        if col in annual.columns:
                            annual[col] = annual[col].astype(str).str.replace(',', '').astype(float)
                    for col in ['EPS Growth (%)', 'Net Profit Margin (%)', 'PEG']:
                        if col in ratios.columns:
                            ratios[col] = ratios[col].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
                            ratios[col] = pd.to_numeric(ratios[col], errors='coerce')
                    # Metrics for scoring
                    # EPS Growth (last 3 years avg)
                    eps_growths = []
                    if 'EPS' in annual.columns and len(annual) >= 2:
                        eps_vals = annual['EPS'].values[::-1]  # oldest to newest
                        for i in range(1, len(eps_vals)):
                            prev, curr = eps_vals[i-1], eps_vals[i]
                            if prev != 0:
                                eps_growths.append((curr - prev) / abs(prev) * 100)
                    avg_eps_growth = sum(eps_growths[-3:]) / min(3, len(eps_growths)) if eps_growths else 0
                    # Net Profit Margin (avg)
                    avg_margin = ratios['Net Profit Margin (%)'].mean() if 'Net Profit Margin (%)' in ratios.columns and not ratios.empty else 0
                    # PEG Ratio (avg, lower is better)
                    avg_peg = ratios['PEG'].mean() if 'PEG' in ratios.columns and not ratios.empty else None
                    # Dividend Consistency
                    div_count = len(payouts)
                    # Dividend Growth (last 3 payouts)
                    div_growth = 0
                    if div_count >= 2:
                        try:
                            # Extract payout % from Details (e.g., '110%(F) (D)')
                            payout_perc = [float(re.search(r'(\d+\.?\d*)%', d['Details']).group(1)) for d in payouts.to_dict('records') if re.search(r'(\d+\.?\d*)%', d['Details'])]
                            if len(payout_perc) >= 2:
                                div_growth = (payout_perc[0] - payout_perc[-1]) / abs(payout_perc[-1]) * 100 if payout_perc[-1] != 0 else 0
                        except Exception:
                            div_growth = 0
                    # Profit after Tax Growth (last 3 years avg)
                    pat_growths = []
                    if 'Profit after Taxation' in annual.columns and len(annual) >= 2:
                        pat_vals = annual['Profit after Taxation'].values[::-1]
                        for i in range(1, len(pat_vals)):
                            prev, curr = pat_vals[i-1], pat_vals[i]
                            if prev != 0:
                                pat_growths.append((curr - prev) / abs(prev) * 100)
                    avg_pat_growth = sum(pat_growths[-3:]) / min(3, len(pat_growths)) if pat_growths else 0
                    # EPS Level (latest year)
                    latest_eps = float(annual['EPS'].iloc[-1]) if not annual.empty and 'EPS' in annual.columns else None
                    # Profit Margin Trend (last 3 years)
                    margin_trend = 0
                    if 'Net Profit Margin (%)' in ratios.columns and len(ratios) >= 2:
                        margin_vals = ratios['Net Profit Margin (%)'].values[::-1]
                        if len(margin_vals) >= 2 and margin_vals[-1] != 0:
                            margin_trend = (margin_vals[0] - margin_vals[-1]) / abs(margin_vals[-1]) * 100
                    comp_data.append({
                        'Symbol': symbol,
                        'Latest EPS': latest_eps,
                        'Latest Profit': float(annual['Profit after Taxation'].iloc[-1]) if not annual.empty and 'Profit after Taxation' in annual.columns else None,
                        'Net Profit Margin (%)': avg_margin,
                        'PEG': avg_peg,
                        'Dividend Count': div_count,
                        'EPS Growth': avg_eps_growth,
                        'PAT Growth': avg_pat_growth,
                        'Dividend Growth': div_growth,
                        'Margin Trend': margin_trend
                    })
                comp_df_final = pd.DataFrame(comp_data)
                # --- Relative Scoring ---
                # Define weights
                weights = {
                    'EPS Growth': 2.0,
                    'Net Profit Margin (%)': 1.5,
                    'PEG': 1.5,
                    'Dividend Count': 1.5,
                    'Dividend Growth': 1.0,
                    'PAT Growth': 1.0,
                    'Latest EPS': 0.5,
                    'Margin Trend': 1.0
                }
                # Normalize metrics (min-max, except PEG: lower is better)
                norm_df = comp_df_final.copy()
                for col in ['EPS Growth', 'Net Profit Margin (%)', 'Dividend Count', 'Dividend Growth', 'PAT Growth', 'Latest EPS', 'Margin Trend']:
                    if col in norm_df.columns:
                        minv, maxv = norm_df[col].min(), norm_df[col].max()
                        if maxv != minv:
                            norm_df[col] = (norm_df[col] - minv) / (maxv - minv)
                        else:
                            norm_df[col] = 1  # If all same, give full score
                # PEG: lower is better
                if 'PEG' in norm_df.columns:
                    minv, maxv = norm_df['PEG'].min(), norm_df['PEG'].max()
                    if maxv != minv:
                        norm_df['PEG'] = (maxv - norm_df['PEG']) / (maxv - minv)
                    else:
                        norm_df['PEG'] = 1
                # Calculate weighted score
                norm_df['Score'] = 0
                for k, w in weights.items():
                    if k in norm_df.columns:
                        norm_df['Score'] += norm_df[k].fillna(0) * w
                # Scale to 10
                max_score = sum(weights.values())
                norm_df['Score'] = (norm_df['Score'] / max_score * 10).round(2)
                # Merge score into comp_df_final
                comp_df_final['Score'] = norm_df['Score']
                st.dataframe(comp_df_final[['Symbol','Latest EPS','Latest Profit','Net Profit Margin (%)','PEG','Dividend Count','Score']], use_container_width=True, hide_index=True)
                # --- Score Bar Chart ---
                fig_score = go.Figure(data=[go.Bar(
                    x=comp_df_final['Symbol'],
                    y=comp_df_final['Score'],
                    marker_color='#1E88E5',
                    text=comp_df_final['Score'],
                    textposition='auto',
                    name='Score'
                )])
                fig_score.update_layout(title="Relative Stock Score (Best = Highest)", yaxis_title="Score (0-10)", xaxis_title="Symbol", height=350)
                st.plotly_chart(fig_score, use_container_width=True)
                # Comparison Graphs
                fig_cmp = make_subplots(rows=1, cols=2, subplot_titles=("EPS", "Net Profit Margin (%)"))
                fig_cmp.add_trace(go.Bar(x=comp_df_final['Symbol'], y=comp_df_final['Latest EPS'], name='EPS'), row=1, col=1)
                fig_cmp.add_trace(go.Bar(x=comp_df_final['Symbol'], y=comp_df_final['Net Profit Margin (%)'], name='Net Profit Margin'), row=1, col=2)
                fig_cmp.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_cmp, use_container_width=True)
                # PEG and Dividend Count
                fig_cmp2 = make_subplots(rows=1, cols=2, subplot_titles=("PEG Ratio", "Dividend Count"))
                fig_cmp2.add_trace(go.Bar(x=comp_df_final['Symbol'], y=comp_df_final['PEG'], name='PEG'), row=1, col=1)
                fig_cmp2.add_trace(go.Bar(x=comp_df_final['Symbol'], y=comp_df_final['Dividend Count'], name='Dividends'), row=1, col=2)
                fig_cmp2.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_cmp2, use_container_width=True)

                # --- Color function for table ---
                def colorize_comp(val, col):
                    if pd.isnull(val):
                        return ''
                    try:
                        if col in ['PEG']:
                            # Lower is better
                            if val == comp_df_final[col].min():
                                return 'color: #00E396; font-weight: bold;'
                            elif val == comp_df_final[col].max():
                                return 'color: #FF4560;'
                        else:
                            # Higher is better
                            if val == comp_df_final[col].max():
                                return 'color: #00E396; font-weight: bold;'
                            elif val == comp_df_final[col].min():
                                return 'color: #FF4560;'
                    except:
                        pass
                    return ''
                st.markdown("**How to read this table:** Green = best value, Red = worst value for each metric. Score is a weighted sum (see below). ⭐ = best-in-class.")
                styled_comp = comp_df_final[['Symbol','Latest EPS','Latest Profit','Net Profit Margin (%)','PEG','Dividend Count','Score']].copy()
                # Add star for best in each metric
                for col in ['Latest EPS','Latest Profit','Net Profit Margin (%)','PEG','Dividend Count','Score']:
                    if col in styled_comp.columns:
                        best = styled_comp[col].max() if col != 'PEG' else styled_comp[col].min()
                        styled_comp[col] = styled_comp[col].apply(lambda v: f"⭐ {v}" if v == best else v)
                styled_comp = styled_comp.style.applymap(lambda v: colorize_comp(float(str(v).replace('⭐','').strip()), 'Latest EPS'), subset=['Latest EPS']) \
                    .applymap(lambda v: colorize_comp(float(str(v).replace('⭐','').strip()), 'Latest Profit'), subset=['Latest Profit']) \
                    .applymap(lambda v: colorize_comp(float(str(v).replace('⭐','').strip()), 'Net Profit Margin (%)'), subset=['Net Profit Margin (%)']) \
                    .applymap(lambda v: colorize_comp(float(str(v).replace('⭐','').strip()), 'PEG'), subset=['PEG']) \
                    .applymap(lambda v: colorize_comp(float(str(v).replace('⭐','').strip()), 'Dividend Count'), subset=['Dividend Count']) \
                    .applymap(lambda v: colorize_comp(float(str(v).replace('⭐','').strip()), 'Score'), subset=['Score'])
                st.dataframe(styled_comp, use_container_width=True, hide_index=True)

                # --- Radar/Spider Chart for Score Breakdown ---
                st.markdown("**Radar Chart: Stock Strengths Across Metrics**")
                st.markdown("This chart shows how each stock performs (0=worst, 1=best among compared) in each metric. The bigger the area, the stronger the stock overall.")
                radar_metrics = ['EPS Growth','Net Profit Margin (%)','PEG','Dividend Count','Dividend Growth','PAT Growth','Latest EPS','Margin Trend']
                radar_labels = ['EPS Growth','Profit Margin','PEG (lower=better)','Dividends','Div. Growth','PAT Growth','EPS','Margin Trend']
                radar_norm = norm_df[radar_metrics].fillna(0).clip(0,1)
                fig_radar = go.Figure()
                for i, row in radar_norm.iterrows():
                    values = row.values.tolist()
                    values += values[:1]  # close the loop
                    fig_radar.add_trace(go.Scatterpolar(
                        r=values,
                        theta=radar_labels + [radar_labels[0]],
                        fill='toself',
                        name=comp_df_final.iloc[i]['Symbol'],
                        opacity=0.5
                    ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0,1])),
                    showlegend=True,
                    height=450
                )
                st.plotly_chart(fig_radar, use_container_width=True)

                # --- Stacked Bar Chart for Score Breakdown ---
                st.markdown("**Score Breakdown by Metric (Stacked Bar)**")
                st.markdown("Each bar shows how much each metric contributed to the total score for each stock.")
                metric_contribs = []
                for i, row in norm_df.iterrows():
                    contrib = {k: row[k]*w for k, w in weights.items()}
                    contrib['Symbol'] = comp_df_final.iloc[i]['Symbol']
                    metric_contribs.append(contrib)
                contrib_df = pd.DataFrame(metric_contribs)
                fig_stack = go.Figure()
                for k in weights.keys():
                    fig_stack.add_trace(go.Bar(
                        x=contrib_df['Symbol'],
                        y=contrib_df[k],
                        name=k
                    ))
                fig_stack.update_layout(barmode='stack', height=400, yaxis_title='Score Contribution', xaxis_title='Symbol')
                st.plotly_chart(fig_stack, use_container_width=True)

                # --- Trend Line Chart for Selected Metric ---
                st.markdown("**Metric Trend Over Time**")
                st.markdown("Select a metric to see how it has changed over time for each stock.")
                trend_options = {
                    'EPS (Annual)': ('annual','EPS'),
                    'Profit after Tax (Annual)': ('annual','Profit after Taxation'),
                    'Net Profit Margin (%) (Yearly)': ('ratios','Net Profit Margin (%)'),
                    'Dividend % (from Details)': ('payouts','Details')
                }
                trend_metric = st.selectbox("Select Metric for Trend Chart", list(trend_options.keys()), key="trend_metric_select")
                trend_type, trend_col = trend_options[trend_metric]
                fig_trend = go.Figure()
                for _, row in comp_df.iterrows():
                    symbol = row['symbol']
                    if trend_type == 'annual':
                        annual = pd.DataFrame(row['financials']['annual']) if row['financials'] and 'annual' in row['financials'] else pd.DataFrame()
                        if not annual.empty and trend_col in annual.columns:
                            y = annual[trend_col].astype(str).str.replace(',', '').astype(float)
                            x = annual['period']
                            fig_trend.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name=symbol))
                    elif trend_type == 'ratios':
                        ratios = pd.DataFrame(row['ratios']) if row['ratios'] else pd.DataFrame()
                        if not ratios.empty and trend_col in ratios.columns:
                            y = ratios[trend_col].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
                            y = pd.to_numeric(y, errors='coerce')
                            x = ratios['period']
                            fig_trend.add_trace(go.Scatter(x=x, y=y, mode='lines+markers', name=symbol))
                    elif trend_type == 'payouts':
                        payouts = pd.DataFrame(row['payouts']) if row['payouts'] else pd.DataFrame()
                        if not payouts.empty and 'Details' in payouts.columns:
                            # Extract payout % from Details
                            payout_perc = [float(re.search(r'(\d+\.?\d*)%', d).group(1)) for d in payouts['Details'] if re.search(r'(\d+\.?\d*)%', d)]
                            x = payouts['Financial Results'][:len(payout_perc)]
                            fig_trend.add_trace(go.Scatter(x=x, y=payout_perc, mode='lines+markers', name=symbol))
                fig_trend.update_layout(height=400, yaxis_title=trend_metric, xaxis_title='Period/Year')
                st.plotly_chart(fig_trend, use_container_width=True)

    with tab6:
        st.markdown("# Future Capital & Dividend Predictor")
        st.markdown("""
        Enter your investment details and let the system project your future capital and monthly dividends, using the best stocks based on the scoring system. Dividends are assumed to be reinvested. All projections are based on historical growth and payout patterns.
        """)
        # --- UI Inputs ---
        with st.form("future_predictor_form"):
            invest_amt = st.number_input("Investment Amount (Rs.)", min_value=1000.0, value=100000.0, step=1000.0)
            years = st.number_input("Investment Duration (years)", min_value=1, max_value=30, value=5, step=1)
            num_stocks = st.number_input("Number of Stocks to Include", min_value=1, max_value=20, value=5, step=1)
            weighting_method = st.selectbox("Weighting Method", ["Proportional to Score", "Equal Weight"], index=0)
            submitted = st.form_submit_button("Simulate Future Portfolio")
        if submitted:
            # --- Stock Selection ---
            stocks_df = get_stocks()
            if stocks_df.empty:
                st.warning("No stocks available for simulation.")
            else:
                # Use the same scoring as in comparison
                comp_data = []
                for _, row in stocks_df.iterrows():
                    symbol = row['symbol']
                    annual = pd.DataFrame(row['financials']['annual']) if row['financials'] and 'annual' in row['financials'] else pd.DataFrame()
                    ratios = pd.DataFrame(row['ratios']) if row['ratios'] else pd.DataFrame()
                    payouts = pd.DataFrame(row['payouts']) if row['payouts'] else pd.DataFrame()
                    for col in ['Mark-up Earned', 'Total Income', 'Profit after Taxation', 'EPS']:
                        if col in annual.columns:
                            annual[col] = annual[col].astype(str).str.replace(',', '').astype(float)
                    for col in ['EPS Growth (%)', 'Net Profit Margin (%)', 'PEG']:
                        if col in ratios.columns:
                            ratios[col] = ratios[col].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
                            ratios[col] = pd.to_numeric(ratios[col], errors='coerce')
                    eps_growths = []
                    if 'EPS' in annual.columns and len(annual) >= 2:
                        eps_vals = annual['EPS'].values[::-1]
                        for i in range(1, len(eps_vals)):
                            prev, curr = eps_vals[i-1], eps_vals[i]
                            if prev != 0:
                                eps_growths.append((curr - prev) / abs(prev) * 100)
                    avg_eps_growth = sum(eps_growths[-3:]) / min(3, len(eps_growths)) if eps_growths else 0
                    avg_margin = ratios['Net Profit Margin (%)'].mean() if 'Net Profit Margin (%)' in ratios.columns and not ratios.empty else 0
                    avg_peg = ratios['PEG'].mean() if 'PEG' in ratios.columns and not ratios.empty else None
                    div_count = len(payouts)
                    div_growth = 0
                    if div_count >= 2:
                        try:
                            payout_perc = [float(re.search(r'(\d+\.?\d*)%', d['Details']).group(1)) for d in payouts.to_dict('records') if re.search(r'(\d+\.?\d*)%', d['Details'])]
                            if len(payout_perc) >= 2:
                                div_growth = (payout_perc[0] - payout_perc[-1]) / abs(payout_perc[-1]) * 100 if payout_perc[-1] != 0 else 0
                        except Exception:
                            div_growth = 0
                    pat_growths = []
                    if 'Profit after Taxation' in annual.columns and len(annual) >= 2:
                        pat_vals = annual['Profit after Taxation'].values[::-1]
                        for i in range(1, len(pat_vals)):
                            prev, curr = pat_vals[i-1], pat_vals[i]
                            if prev != 0:
                                pat_growths.append((curr - prev) / abs(prev) * 100)
                    avg_pat_growth = sum(pat_growths[-3:]) / min(3, len(pat_growths)) if pat_growths else 0
                    latest_eps = float(annual['EPS'].iloc[-1]) if not annual.empty and 'EPS' in annual.columns else None
                    margin_trend = 0
                    if 'Net Profit Margin (%)' in ratios.columns and len(ratios) >= 2:
                        margin_vals = ratios['Net Profit Margin (%)'].values[::-1]
                        if len(margin_vals) >= 2 and margin_vals[-1] != 0:
                            margin_trend = (margin_vals[0] - margin_vals[-1]) / abs(margin_vals[-1]) * 100
                    comp_data.append({
                        'Symbol': symbol,
                        'Latest EPS': latest_eps,
                        'Net Profit Margin (%)': avg_margin,
                        'PEG': avg_peg,
                        'Dividend Count': div_count,
                        'EPS Growth': avg_eps_growth,
                        'PAT Growth': avg_pat_growth,
                        'Dividend Growth': div_growth,
                        'Margin Trend': margin_trend,
                        'Annual': annual,
                        'Payouts': payouts
                    })
                comp_df = pd.DataFrame(comp_data)
                # --- Scoring (same as comparison) ---
                weights = {
                    'EPS Growth': 2.0,
                    'Net Profit Margin (%)': 1.5,
                    'PEG': 1.5,
                    'Dividend Count': 1.5,
                    'Dividend Growth': 1.0,
                    'PAT Growth': 1.0,
                    'Latest EPS': 0.5,
                    'Margin Trend': 1.0
                }
                norm_df = comp_df.copy()
                for col in ['EPS Growth', 'Net Profit Margin (%)', 'Dividend Count', 'Dividend Growth', 'PAT Growth', 'Latest EPS', 'Margin Trend']:
                    if col in norm_df.columns:
                        minv, maxv = norm_df[col].min(), norm_df[col].max()
                        if maxv != minv:
                            norm_df[col] = (norm_df[col] - minv) / (maxv - minv)
                        else:
                            norm_df[col] = 1
                if 'PEG' in norm_df.columns:
                    minv, maxv = norm_df['PEG'].min(), norm_df['PEG'].max()
                    if maxv != minv:
                        norm_df['PEG'] = (maxv - norm_df['PEG']) / (maxv - minv)
                    else:
                        norm_df['PEG'] = 1
                norm_df['Score'] = 0
                for k, w in weights.items():
                    if k in norm_df.columns:
                        norm_df['Score'] += norm_df[k].fillna(0) * w
                max_score = sum(weights.values())
                norm_df['Score'] = (norm_df['Score'] / max_score * 10).round(2)
                comp_df['Score'] = norm_df['Score']
                # --- Select Top N Stocks ---
                comp_df = comp_df.sort_values('Score', ascending=False).reset_index(drop=True)
                top_stocks = comp_df.head(int(num_stocks))
                if top_stocks.empty:
                    st.warning("No stocks available for simulation.")
                else:
                    if weighting_method == "Equal Weight":
                        weights_arr = np.ones(len(top_stocks)) / len(top_stocks)
                    else:
                        scores = top_stocks['Score'].values
                        weights_arr = scores / scores.sum() if scores.sum() > 0 else np.ones(len(scores)) / len(scores)
                    top_stocks = top_stocks.copy()
                    top_stocks['Weight'] = weights_arr
                    # --- Realistic Simulation ---
                    periods = years
                    annual_results = []
                    capital = 0.0
                    stock_caps = np.zeros(len(top_stocks))
                    total_investment = 0.0
                    # Estimate annual price growth and dividend yield for each stock (capped)
                    price_cagrs = []
                    div_yields = []
                    for idx, row in top_stocks.iterrows():
                        annual = row['Annual']
                        payouts = row['Payouts']
                        # Price CAGR: use EPS growth as proxy if price not available, cap at 12%
                        if 'EPS' in annual.columns and len(annual) >= 2:
                            eps_vals = annual['EPS'].values[::-1]
                            n = len(eps_vals) - 1
                            if n > 0 and eps_vals[0] > 0:
                                cagr = (eps_vals[-1] / eps_vals[0]) ** (1/n) - 1
                            else:
                                cagr = 0.08
                        else:
                            cagr = 0.08
                        cagr = max(0.04, min(0.12, cagr))  # Cap between 4% and 12%
                        price_cagrs.append(cagr)
                        # Dividend yield: average of last 3 payouts as % of EPS or capital, cap at 7%
                        if not payouts.empty and 'Details' in payouts.columns:
                            payout_perc = [float(re.search(r'(\d+\.?\d*)%', d).group(1)) for d in payouts['Details'] if re.search(r'(\d+\.?\d*)%', d)]
                            avg_payout = np.mean(payout_perc[-3:]) if payout_perc else 0
                            div_yield = avg_payout / 100
                        else:
                            div_yield = 0.03
                        div_yield = max(0.01, min(0.07, div_yield))  # Cap between 1% and 7%
                        div_yields.append(div_yield)
                    # --- Simulate each year ---
                    for year in range(1, periods+1):
                        # Add new investment for the year
                        capital += invest_amt * 12
                        total_investment += invest_amt * 12
                        stock_caps += (invest_amt * 12) * top_stocks['Weight'].values
                        # Apply annual price growth
                        for i in range(len(stock_caps)):
                            stock_caps[i] *= (1 + price_cagrs[i])
                        # Dividends for this year
                        dividends = [stock_caps[i] * div_yields[i] for i in range(len(stock_caps))]
                        total_div = sum(dividends)
                        # Reinvest dividends
                        capital = sum(stock_caps) + total_div
                        stock_caps = (np.array(stock_caps) + np.array(dividends))
                        # Rebalance to weights (annually)
                        stock_caps = capital * top_stocks['Weight'].values
                        annual_results.append({
                            'Year': year,
                            'Capital': capital,
                            'Total Dividend': total_div
                        })
                    # --- Output ---
                    st.success(f"Simulation complete! Portfolio of {len(top_stocks)} stocks.")
                    st.markdown(f"**Total Investment:** Rs. {total_investment:,.2f}")
                    st.markdown(f"**Final Projected Capital:** Rs. {capital:,.2f}")
                    avg_annual_div = np.mean([r['Total Dividend'] for r in annual_results[-1:]])
                    st.markdown(f"**Projected Annual Dividend (last year):** Rs. {avg_annual_div:,.2f}")
                    st.markdown(f"**Projected Monthly Dividend (last year avg):** Rs. {avg_annual_div/12:,.2f}")
                    # ROI and CAGR
                    roi = (capital - total_investment) / total_investment * 100 if total_investment > 0 else 0
                    cagr = ((capital / total_investment) ** (1/years) - 1) * 100 if total_investment > 0 else 0
                    st.markdown(f"**ROI:** {roi:.2f}%")
                    st.markdown(f"**CAGR:** {cagr:.2f}%")
                    # Chart: Capital and Dividend over time
                    years_list = [r['Year'] for r in annual_results]
                    capitals = [r['Capital'] for r in annual_results]
                    dividends = [r['Total Dividend'] for r in annual_results]
                    fig_proj = go.Figure()
                    fig_proj.add_trace(go.Scatter(x=years_list, y=capitals, mode='lines+markers', name='Capital'))
                    fig_proj.add_trace(go.Scatter(x=years_list, y=dividends, mode='lines+markers', name='Annual Dividend'))
                    fig_proj.update_layout(title="Projected Capital & Annual Dividend Over Time", xaxis_title="Year", yaxis_title="Rs.", height=400)
                    st.plotly_chart(fig_proj, use_container_width=True)
                    # Table: Yearly breakdown
                    st.markdown("**Yearly Breakdown**")
                    st.dataframe(pd.DataFrame(annual_results), use_container_width=True, hide_index=True)
                    # Show selected stocks and weights
                    st.markdown("**Selected Stocks and Weights**")
                    st.dataframe(top_stocks[['Symbol','Score','Weight']], use_container_width=True, hide_index=True)
                    # Notes
                    st.info("""
                    **Assumptions (Realistic Simulation):**
                    - Price growth is estimated from historical EPS growth (CAGR), capped at 12% per year.
                    - Dividend yield is based on recent payout history, capped at 7% per year.
                    - Compounding and rebalancing are annual (not monthly).
                    - Dividends are reinvested at year end.
                    - If fewer stocks are available than requested, all are used.
                    - This is a simulation, not a guarantee. Past performance does not guarantee future results.
                    - ROI = (Final Capital - Total Invested) / Total Invested. CAGR = annualized return.
                    """)
    
    with tab4:
        st.markdown("### Alerts Management")
        alerts_df = get_alerts() if 'get_alerts' in globals() else pd.DataFrame()
        if not alerts_df.empty:
            st.markdown("#### Active Alerts")
            # Table header
            header_cols = st.columns([2, 2, 2, 1.5, 2])
            header_cols[0].markdown("**Symbol**")
            header_cols[1].markdown("**Min Price**")
            header_cols[2].markdown("**Max Price**")
            header_cols[3].markdown("**Status**")
            header_cols[4].markdown("**Actions**")
            # Table rows
            for idx, alert in alerts_df.iterrows():
                row_cols = st.columns([2, 2, 2, 1.5, 2])
                row_cols[0].markdown(f"<b>{alert['symbol']}</b>", unsafe_allow_html=True)
                row_cols[1].markdown(f"Rs. {alert['min_price']:.2f}")
                row_cols[2].markdown(f"Rs. {alert['max_price']:.2f}")
                status_icon = "🟢" if alert['enabled'] else "🔴"
                status_label = "Enabled" if alert['enabled'] else "Disabled"
                status_color = "#00E396" if alert['enabled'] else "#FF4560"
                row_cols[3].markdown(
                    f"<span style='color:{status_color};font-weight:bold;'>{status_icon} {status_label}</span>",
                    unsafe_allow_html=True
                )
                toggle_label = "Disable" if alert['enabled'] else "Enable"
                with row_cols[4]:
                    tcol1, tcol2 = st.columns([1, 1])
                    if tcol1.button(toggle_label, key=f"toggle_{idx}"):
                        set_alert_enabled(alert['symbol'], alert['min_price'], alert['max_price'], not alert['enabled'])
                        st.rerun()
                    if tcol2.button("Delete", key=f"delete_{idx}"):
                        delete_alert(alert['symbol'], alert['min_price'], alert['max_price'])
                        st.success(f"Alert for {alert['symbol']} deleted")
                        st.rerun()
            st.markdown("<hr style='margin:0.5em 0 0.5em 0; border:0; border-top:1px solid #222;'>", unsafe_allow_html=True)
        else:
            st.info("No alerts set. Use the form below to create one.")
        st.markdown("---")
        st.markdown("#### Create New Alert")
        with st.form("new_alert_form"):
            alert_col1, alert_col2, alert_col3 = st.columns(3)
            with alert_col1:
                new_alert_symbol = st.selectbox("Symbol", portfolio_symbols, key="new_alert_symbol")
            with alert_col2:
                new_min_price = st.number_input("Min Price", min_value=0.0, step=1.0, key="new_min_price")
            with alert_col3:
                new_max_price = st.number_input("Max Price", min_value=0.0, step=1.0, key="new_max_price")
            new_alert_enabled = st.checkbox("Enabled", value=True, key="new_alert_enabled")
            if st.form_submit_button("💾 Create Alert", use_container_width=True):
                add_alert(new_alert_symbol, new_min_price, new_max_price, new_alert_enabled)
                st.success(f"Alert created for {new_alert_symbol}")
                st.rerun()

# --- Helper: Ensure P/L Amount column exists and is numeric ---
def ensure_pl_amount(df, prices_df=None):
    if 'P/L Amount' not in df.columns:
        # Use get_trades_with_pct_change if available
        if prices_df is not None:
            try:
                df = get_trades_with_pct_change(df, prices_df)
            except Exception:
                df['P/L Amount'] = 0.0
        else:
            df['P/L Amount'] = 0.0
    # Ensure numeric
    df['P/L Amount'] = pd.to_numeric(df['P/L Amount'], errors='coerce').fillna(0.0)
    return df

