import os
import requests
import re
from datetime import datetime, time
import pytz
from bs4 import BeautifulSoup
from pymongo import MongoClient
from dotenv import load_dotenv
import concurrent.futures
import random

load_dotenv()
# MONGO_URI = os.getenv("MONGO_URI")
MONGO_URI = "mongodb+srv://coolminded682:7JogkfWtfUZcCWkZ@cluster0.zv3vun7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# DB_NAME = os.getenv("DB_NAME")
DB_NAME = "psx_portfolio"

USER_AGENTS = [
    # Windows Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    # Windows Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0',
    # Mac Safari
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    # Linux Chrome
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    # Linux Firefox
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0',
    # Android Chrome
    'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.196 Mobile Safari/537.36',
    # iPhone Safari
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
]

def is_trading_time():
    """Check if current time is within Pakistan trading hours (Mon-Fri, 9AM-4PM PKT)"""
    # Create timezone objects
    utc_tz = pytz.utc
    pkt_tz = pytz.timezone('Asia/Karachi')
    
    # Get current time in UTC and convert to PKT
    utc_now = datetime.now(utc_tz)
    pkt_now = utc_now.astimezone(pkt_tz)
    
    # Check if it's a weekday (0=Monday, 4=Friday)
    if pkt_now.weekday() > 4:  # 5=Saturday, 6=Sunday
        return False
    
    # Check if time is between 9:00 and 16:00 (4PM)
    trading_start = time(9, 0)
    trading_end = time(16, 0)
    current_time = pkt_now.time()
    
    return trading_start <= current_time <= trading_end

def get_mongo():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db

def fetch_price(symbol):
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': random.choice([
            'en-US,en;q=0.9',
            'en-GB,en;q=0.8',
            'en;q=0.7',
            'en-US;q=0.6',
            'en-CA,en;q=0.9',
        ]),
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
    db.prices.update_one(
        {'symbol': symbol},
        {'$set': {
            'price': price,
            'change_value': change_value,
            'percentage': percentage,
            'direction': direction,
            'fetched_at': datetime.now().isoformat()
        }},
        upsert=True
    )

def fetch_and_save_symbol(symbol):
    try:
        price, change_value, percentage, direction = fetch_price(symbol)
        if price is not None:
            save_price(symbol, price, change_value, percentage, direction)
            print(f"Updated {symbol}: Price={price}, Change={change_value}, %={percentage}")
        else:
            print(f"No price found for {symbol}")
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")

def fetch_and_save_all():
    # Check if we're in trading hours
    if not is_trading_time():
        pkt_tz = pytz.timezone('Asia/Karachi')
        pkt_now = datetime.now(pytz.utc).astimezone(pkt_tz)
        print(f"Not in trading hours. Current PKT time: {pkt_now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        return
    
    db = get_mongo()
    symbols = db.portfolio.find({}, {"_id": 0, "symbol": 1})
    tickers = [doc["symbol"] for doc in symbols]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(fetch_and_save_symbol, tickers)

if __name__ == "__main__":
    fetch_and_save_all()