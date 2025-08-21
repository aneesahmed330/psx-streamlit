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
        background-color: #1E2130;
        border: 1px solid #2D3748;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    [data-testid="stMetricValue"] { color: #FFFFFF; }
    [data-testid="stMetricLabel"] { color: #A0AEC0; }
    
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

# Get portfolio symbols
portfolio_symbols = get_portfolio_symbols()

# Sidebar: Portfolio Management
with st.sidebar:
    st.sidebar.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h2 style='color: #1E88E5; margin-bottom: 0;'>PSX Portfolio</h2>
        <p style='color: #A0AEC0; margin-top: 0;'>Investment Tracker</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Portfolio Management Section
    with st.expander("📊 Portfolio Management", expanded=True):
        new_symbol = st.text_input("Add Symbol", "", key="add_symbol_input", 
                                  help="Enter PSX symbol (e.g. UBL)", placeholder="Symbol")
        add_col, remove_col = st.columns(2)
        with add_col:
            if st.button("➕ Add", key="add_symbol_btn", use_container_width=True,
                        help="Add symbol to portfolio"):
                if new_symbol and new_symbol not in portfolio_symbols:
                    add_portfolio_symbol(new_symbol)
                    st.success(f"Added {new_symbol} to portfolio.")
                    st.rerun()
                else:
                    st.warning("Symbol already in portfolio or empty.")
        
        if portfolio_symbols:
            remove_symbol = st.selectbox("Remove Symbol", portfolio_symbols, 
                                       key="remove_symbol", help="Select symbol to remove")
            if st.button("🗑️ Remove", key="remove_symbol_btn", use_container_width=True,
                       help="Remove selected symbol"):
                remove_portfolio_symbol(remove_symbol)
                st.success(f"Removed {remove_symbol} and its trades/prices.")
                st.rerun()
        else:
            st.info("No symbols in portfolio")
    
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
                # Alert saving logic would go here
                st.success(f"Alert set for {alert_symbol}.")
        else:
            st.info("Add symbols to portfolio to set alerts")

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
with status_col1:
    pk_tz = pytz.timezone('Asia/Karachi')
    last_refresh_dt = datetime.fromtimestamp(st.session_state['last_refresh'], tz=pk_tz)
    st.info(f"Auto-refresh every {REFRESH_INTERVAL//60} minutes. Last refresh: {last_refresh_dt.strftime('%Y-%m-%d %I:%M:%S %p')} (PKT)")
with status_col2:
    if st.button("🔄 Manual Refresh", use_container_width=True):
        with st.spinner("Refreshing data..."):
            fetch_and_save_all(portfolio_symbols)
            st.session_state['last_refresh'] = time.time()
            st.success("Data refreshed!")
            time.sleep(1)
            st.rerun()

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
            'Shares Held': round(net_qty, 2),
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

# --- Dashboard Layout ---
st.subheader("Portfolio Overview")

# Portfolio metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Total Investment", f"Rs. {total_investment:,.2f}")
with col2:
    st.metric("📈 Market Value", f"Rs. {total_market_value:,.2f}")
with col3:
    st.metric("📊 Unrealized P/L", f"Rs. {total_unrealized_pl:,.2f}")
with col4:
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
                "Shares Held": st.column_config.NumberColumn(format="%.2f"),
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
            
            # Additional performance metrics
            st.markdown("#### Performance Metrics")
            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
            
            with perf_col1:
                best_performer = portfolio_df.loc[portfolio_df['% Up/Down'].idxmax()]
                st.metric("🚀 Best Performer", best_performer['Symbol'], f"{best_performer['% Up/Down']:.2f}%")
            
            with perf_col2:
                worst_performer = portfolio_df.loc[portfolio_df['% Up/Down'].idxmin()]
                st.metric("📉 Worst Performer", worst_performer['Symbol'], f"{worst_performer['% Up/Down']:.2f}%")
            
            with perf_col3:
                largest_holding = portfolio_df.loc[portfolio_df['Market Value'].idxmax()]
                st.metric("🏆 Largest Holding", largest_holding['Symbol'], f"Rs. {largest_holding['Market Value']:,.2f}")
            
            with perf_col4:
                total_gain_loss = portfolio_df['Unrealized P/L'].sum()
                st.metric("💵 Total Gain/Loss", f"Rs. {total_gain_loss:,.2f}")
    
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
                styled_trades = filtered_trades.style.applymap(pct_color, subset=['Percentage Change', 'P/L Amount'])
                st.dataframe(styled_trades, use_container_width=True, hide_index=True)
            else:
                st.info("No trades for selected symbol.")
        else:
            st.info("No trade history available.")
    
    with tab4:
        st.markdown("### Alerts Management")
        
        # Mock alerts data (replace with your actual alerts logic)
        alerts_data = [
            {"symbol": "UBL", "min_price": 180.0, "max_price": 220.0, "enabled": True},
            {"symbol": "HBL", "min_price": 90.0, "max_price": 120.0, "enabled": False},
            {"symbol": "PSO", "min_price": 150.0, "max_price": 200.0, "enabled": True}
        ]
        
        alerts_df = pd.DataFrame(alerts_data)
        
        if not alerts_df.empty:
            st.markdown("#### Active Alerts")
            
            for _, alert in alerts_df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                
                with col1:
                    st.markdown(f"**{alert['symbol']}**")
                
                with col2:
                    st.markdown(f"Min: Rs. {alert['min_price']:.2f}")
                
                with col3:
                    st.markdown(f"Max: Rs. {alert['max_price']:.2f}")
                
                with col4:
                    status = "🟢 Enabled" if alert['enabled'] else "🔴 Disabled"
                    st.markdown(status)
                
                with col5:
                    if st.button("Delete", key=f"delete_{alert['symbol']}"):
                        st.success(f"Alert for {alert['symbol']} deleted")
                        # Add your delete logic here
            
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
                st.success(f"Alert created for {new_alert_symbol}")
                # Add your alert creation logic here

else:
    st.info("Your portfolio is empty. Add symbols to get started.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #A0AEC0;'>PSX Portfolio Dashboard • Made with Streamlit</div>", 
            unsafe_allow_html=True)