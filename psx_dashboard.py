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
    pk_tz = pytz.timezone('Asia/Karachi')
    fetched_at = datetime.now(pk_tz).isoformat()
    db.prices.insert_one({
        'symbol': symbol,
        'price': price,
        'change_value': change_value,
        'percentage': percentage,
        'direction': direction,
        'fetched_at': fetched_at
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

# --- Sidebar: Portfolio Management, Price Actions, Log Trade, Alerts ---
with st.sidebar:
    st.sidebar.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h2 style='color: #1E88E5; margin-bottom: 0;'>PSX Portfolio</h2>
        <p style='color: #A0AEC0; margin-top: 0;'>Investment Tracker</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Price Actions Section
    with st.expander("🔄 Price Actions", expanded=True):
        if st.button("💹 Fetch Latest Prices", use_container_width=True,
                    help="Fetch latest prices for all symbols"):
            with st.spinner("Fetching prices..."):
                fetch_and_save_all(portfolio_symbols)
                st.success("Prices updated successfully!")
    
    # Trade Logging Section
    with st.expander("📝 Log Trade", expanded=True):
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
                st.experimental_rerun()
    
    # Alerts Management Section
    with st.expander("🔔 Price Alerts", expanded=True):
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
                st.experimental_rerun()
        else:
            st.info("Add trades to see symbols for alerts")

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

# --- Main Content Area ---
st.title("📈 PSX Portfolio Dashboard")

# Auto-refresh every 60 seconds
REFRESH_INTERVAL = 300
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()

if time.time() - st.session_state['last_refresh'] > REFRESH_INTERVAL:
    fetch_and_save_all(portfolio_symbols)
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

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
    latest_price_map = dict(zip(prices_df['symbol'], prices_df['price']))
    trades_df = trades_df.copy()
    trades_df['Percentage Change'] = None
    trades_df['P/L Amount'] = None
    for idx, row in trades_df.iterrows():
        symbol = row['symbol']
        trade_price = row['price']
        quantity = row['quantity'] if 'quantity' in row else 0
        trade_type = row['trade_type'] if 'trade_type' in row else 'Buy'
        latest_price = latest_price_map.get(symbol)
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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio Details", "📈 Performance Analytics", "💼 Trade History", "🔔 Alerts Management"])
    
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
            st.markdown("#### Portfolio Value Over Time")
            db = get_mongo()
            # Get all price history for portfolio symbols
            price_history = list(db.prices.find({"symbol": {"$in": portfolio_symbols}}))
            if price_history:
                price_hist_df = pd.DataFrame(price_history)
                # Use errors='coerce' to handle any parsing issues and support ISO8601
                price_hist_df['fetched_at'] = pd.to_datetime(price_hist_df['fetched_at'], errors='coerce', utc=True)
                price_hist_df = price_hist_df.dropna(subset=['fetched_at'])
                # Pivot to get latest price per symbol per day
                price_hist_df['date'] = price_hist_df['fetched_at'].dt.date
                daily_prices = price_hist_df.sort_values('fetched_at').groupby(['symbol', 'date']).last().reset_index()
                # Get trades for net shares held per symbol per day
                trades_df['trade_date'] = pd.to_datetime(trades_df['trade_date'])
                trades_df['date'] = trades_df['trade_date'].dt.date
                # Build a DataFrame with all dates in price history
                all_dates = pd.date_range(start=daily_prices['date'].min(), end=daily_prices['date'].max())
                portfolio_value = []
                for d in all_dates:
                    d = d.date()
                    total_value = 0
                    for symbol in portfolio_symbols:
                        # Net shares held up to this date
                        trades_until = trades_df[(trades_df['symbol'] == symbol) & (trades_df['date'] <= d)]
                        qty_bought = trades_until[trades_until['trade_type'] == 'Buy']['quantity'].sum() if not trades_until.empty else 0
                        qty_sold = trades_until[trades_until['trade_type'] == 'Sell']['quantity'].sum() if not trades_until.empty else 0
                        net_qty = qty_bought - qty_sold
                        # Latest price for this symbol on this date
                        price_row = daily_prices[(daily_prices['symbol'] == symbol) & (daily_prices['date'] == d)]
                        if not price_row.empty:
                            price = price_row['price'].values[0]
                            total_value += net_qty * price
                    portfolio_value.append({'date': d, 'Portfolio Value': total_value})
                pv_df = pd.DataFrame(portfolio_value)
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=pv_df['date'], y=pv_df['Portfolio Value'], mode='lines+markers', name='Portfolio Value', line=dict(color='#1E88E5', width=3)))
                fig2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#A0AEC0'),
                    yaxis=dict(title='Portfolio Value (Rs.)'),
                    xaxis=dict(title='Date'),
                    height=350
                )
                st.plotly_chart(fig2, use_container_width=True)
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