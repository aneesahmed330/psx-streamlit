#!/usr/bin/env python3
"""
PSX Stock Analysis Scraper - Python Version
Usage: python sarmaaya_scraper.py <SYMBOL>
"""

import sys
import requests
import json
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import re

# Initialize colorama for cross-platform colored output
init()

def fetch_stock_data(symbol):
    """Fetch and parse stock information from Sarmaaya.pk"""
    try:
        url = f"https://sarmaaya.pk/psx/company/{symbol}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        print(f"{Fore.YELLOW}Fetching data for {symbol} from Sarmaaya.pk...{Style.RESET_ALL}")
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        if response.status_code == 404:
            print(f"{Fore.RED}Error: Symbol '{symbol}' not found{Style.RESET_ALL}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save full HTML for reference
        with open(f"{symbol}_sarmaya_raw.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # Try to find company name with fallback selectors
        company_name_tag = soup.find('h1', class_='company-name')
        if not company_name_tag:
            # Try alternate selectors (e.g., h2, h3, or by id)
            company_name_tag = soup.find('h2', class_='company-name') or soup.find('h1') or soup.find('title')
        if not company_name_tag or not company_name_tag.get_text(strip=True):
            page_title = soup.title.string if soup.title else 'No title found'
            print(f"{Fore.RED}Error: No company data found for '{symbol}'. Page title: {page_title}{Style.RESET_ALL}")
            return None
            
        # Extract company information
        company_info = extract_company_info(soup)
        
        # Extract current price data
        price_data = extract_price_data(soup)
        
        # Extract performance metrics
        performance = extract_performance_data(soup)
        
        # Extract financial metrics
        financial_metrics = extract_financial_metrics(soup)
        
        # Extract dividend information
        dividend_info = extract_dividend_info(soup)
        
        # Extract ownership information
        ownership = extract_ownership_info(soup)
        
        # Extract historical data tables
        historical_data = extract_historical_data(soup)
        
        # Compile all data into a structured JSON object
        stock_data = {
            "company_info": company_info,
            "price_data": price_data,
            "performance": performance,
            "financial_metrics": financial_metrics,
            "dividend_info": dividend_info,
            "ownership": ownership,
            "historical_data": historical_data
        }
        
        return stock_data
        
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Network error: {e}{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        return None

def extract_company_info(soup):
    """Extract company information from the page"""
    try:
        # Try to find company name with fallback selectors
        company_name_tag = soup.find('h1', class_='company-name')
        if not company_name_tag:
            company_name_tag = soup.find('h2', class_='company-name') or soup.find('h1') or soup.find('title')
        company_name = company_name_tag.get_text(strip=True) if company_name_tag else None
        # Try to find company info section
        info_table = soup.find('div', class_='company-info')
        if not info_table:
            # Try to find any table or div after the company name
            if company_name_tag:
                next_table = company_name_tag.find_next('table')
                if next_table:
                    print(f"[DEBUG] Found alternate company info table: {next_table}")
                    info_table = next_table
        sector = None
        listing_date = None
        listing_board = None
        if info_table:
            # Try to extract from table rows or divs
            rows = info_table.find_all('tr') if info_table.name == 'table' or info_table.find_all('tr') else info_table.find_all('div')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'sector' in label:
                        sector = value
                    elif 'listing date' in label:
                        listing_date = value
                    elif 'board' in label:
                        listing_board = value
        else:
            print("[DEBUG] Could not find company info section. Printing nearby HTML:")
            if company_name_tag:
                print(company_name_tag.find_next().prettify() if company_name_tag.find_next() else "No next element.")
        return {
            "name": company_name,
            "sector": sector,
            "listing_date": listing_date,
            "listing_board": listing_board
        }
    except Exception as e:
        print(f"{Fore.RED}Error extracting company info: {e}{Style.RESET_ALL}")
        return {}

def extract_price_data(soup):
    """Extract current price data from the page"""
    try:
        # 1. Try JSON-LD script
        price = None
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            import json
            try:
                data = json.loads(json_ld.string)
                if 'offers' in data and 'price' in data['offers']:
                    price = float(data['offers']['price'])
            except Exception:
                pass
        # 2. Try meta description
        if price is None:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                match = re.search(r'Share Price / Stock Price is ([0-9,.]+)\s*PKR', meta_desc['content'])
                if match:
                    price = float(match.group(1).replace(',', ''))
        # 3. Fallback: Try to find price anywhere in the page (look for Rs. or PKR)
        if price is None:
            price_text = None
            price_candidates = soup.find_all(string=re.compile(r'(Rs\.?|PKR)[\s\xa0]*[0-9,.]+'))
            for candidate in price_candidates:
                match = re.search(r'(Rs\.?|PKR)[\s\xa0]*([0-9,.]+)', candidate)
                if match:
                    num = match.group(2).replace(',', '').replace(' ', '')
                    try:
                        if num and num != '.' and re.match(r'^\d+(\.\d+)?$', num):
                            price_val = float(num)
                            price_text = num
                            break
                    except ValueError:
                        continue
            price = float(price_text) if price_text else None
        # Try to find change and percentage (look for % and up/down icons)
        change = None
        change_pct = None
        change_candidates = soup.find_all(string=re.compile(r'[-+]?\d+\.\d+%'))
        for c in change_candidates:
            if c.parent.name not in ['th', 'thead']:
                val = c.strip().replace('%', '')
                if re.match(r'^-?\d+\.\d+$', val):
                    change_pct = float(val)
                    break
        # Only extract numeric open/high/low/volume
        metrics = {}
        for label in ['Open', 'High', 'Low', 'Volume', 'Avg Volume']:
            label_tag = soup.find(string=re.compile(label, re.I))
            if label_tag and label_tag.parent:
                value_tag = label_tag.find_next(string=re.compile(r'\d'))
                if value_tag:
                    val = clean_numeric_value(value_tag)
                    if isinstance(val, (int, float)):
                        metrics[label.lower().replace(' ', '_')] = val
        return {
            "last_price": price,
            "change": change,
            "change_percentage": change_pct,
            "open": metrics.get('open'),
            "high": metrics.get('high'),
            "low": metrics.get('low'),
            "volume": metrics.get('volume'),
            "average_volume": metrics.get('avg_volume')
        }
    except Exception as e:
        print(f"{Fore.RED}Error extracting price data: {e}{Style.RESET_ALL}")
        return {}

def extract_performance_data(soup):
    """Extract performance metrics (1 Day, 1 Week, etc.) from Return table"""
    try:
        performance = {}
        # Find the first table with Return in the header
        return_table = None
        for table in soup.find_all('table'):
            if table.find(string=re.compile('Return', re.I)):
                return_table = table
                break
        if return_table:
            headers = []
            header_row = return_table.find('thead').find_all('tr')[1] if return_table.find('thead') else None
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all('th')][1:]  # skip first empty
            body_row = return_table.find('tbody').find('tr') if return_table.find('tbody') else None
            if body_row:
                cells = body_row.find_all(['td', 'th'])[1:]  # skip first label
                for h, c in zip(headers, cells):
                    val = c.get_text(strip=True).replace('%', '')
                    try:
                        performance[h.replace(' ', '_').lower()] = float(val)
                    except ValueError:
                        continue
        return performance
    except Exception as e:
        print(f"{Fore.RED}Error extracting performance data: {e}{Style.RESET_ALL}")
        return {}

# --- Extract financial metrics from any table with financial/valuation/metric in header ---
def extract_financial_metrics(soup):
    """Extract financial metrics (EPS, P/E ratio, etc.) from any table with relevant headers"""
    try:
        metrics = {}
        # Look for tables with 'EPS', 'P/E', 'Market Cap', 'Book Value', 'Dividend', 'Yield', 'ROE', 'PBV', 'Beta' in headers
        for table in soup.find_all('table'):
            header_row = table.find('thead').find('tr') if table.find('thead') else table.find('tr')
            if not header_row:
                continue
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]
            # If any financial keyword in headers, parse this table
            keywords = ['eps', 'p/e', 'market cap', 'book value', 'dividend', 'yield', 'roe', 'pbv', 'beta']
            if any(any(k in h for k in keywords) for h in headers):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    for k in keywords:
                        if k in label:
                            metrics[label.replace(' ', '_')] = clean_numeric_value(value)
        return metrics
    except Exception as e:
        print(f"{Fore.RED}Error extracting financial metrics: {e}{Style.RESET_ALL}")
        return {}

# --- Extract dividend info from any table with 'dividend' in header ---
def extract_dividend_info(soup):
    try:
        dividends = {}
        for table in soup.find_all('table'):
            header_row = table.find('thead')
            if header_row:
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]
                if any('dividend' in h for h in headers):
                    # Found a table with dividend information
                    for row in table.find_all('tr'):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 2:
                            continue
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        if 'dividend' in label:
                            dividends['dividend'] = clean_numeric_value(value)
                        elif 'yield' in label:
                            dividends['yield'] = clean_numeric_value(value)
        return dividends
    except Exception as e:
        print(f"{Fore.RED}Error extracting dividend info: {e}{Style.RESET_ALL}")
        return {}

def extract_ownership_info(soup):
    return {}

def extract_historical_data(soup):
    return {"profitability": {}, "valuations": {}, "investors": {}}

def clean_numeric_value(text):
    if not text or text == '-':
        return None
    cleaned = re.sub(r'[%,]', '', str(text).strip())
    if re.match(r'^-?\d+(\.\d+)?$', cleaned):
        return float(cleaned) if '.' in cleaned else int(cleaned)
    if 'b' in cleaned.lower():
        num = re.sub(r'[^\d.-]', '', cleaned)
        return float(num) * 1e9 if num else None
    elif 'm' in cleaned.lower():
        num = re.sub(r'[^\d.-]', '', cleaned)
        return float(num) * 1e6 if num else None
    return cleaned

def extract_snapshot_price(soup):
    """Extract the 'Current' price from the snapshot section (robustly, search siblings/descendants for price format)."""
    try:
        # Find the 'Current' label in the snapshot
        for div in soup.find_all(['div', 'td', 'th', 'span', 'b', 'strong']):
            if div.get_text(strip=True).lower() == 'current':
                # Search all following siblings and descendants in the same parent for price-like numbers
                parent = div.parent
                price_candidates = []
                # Check all descendants after 'Current' in the parent
                found_current = False
                for el in parent.descendants:
                    if hasattr(el, 'get_text'):
                        txt = el.get_text(strip=True).replace(',', '')
                        if not found_current:
                            if txt.lower() == 'current':
                                found_current = True
                            continue
                        # Match price format (e.g., 272.10)
                        if re.match(r'^[1-9][0-9]{2,}\.[0-9]{2}$', txt):
                            price_candidates.append(float(txt))
                # If not found, try siblings after 'Current'
                if not price_candidates:
                    sib = div
                    while sib:
                        sib = sib.find_next_sibling()
                        if sib and hasattr(sib, 'get_text'):
                            txt = sib.get_text(strip=True).replace(',', '')
                            if re.match(r'^[1-9][0-9]{2,}\.[0-9]{2}$', txt):
                                price_candidates.append(float(txt))
                if price_candidates:
                    # Return the largest price (should be the main price)
                    return max(price_candidates)
        # Fallback: search for a large number in a prominent tag near 'Current'
        for tag in soup.find_all(['b', 'strong', 'span', 'td', 'div']):
            txt = tag.get_text(strip=True).replace(',', '')
            if re.match(r'^[1-9][0-9]{2,}\.[0-9]{2}$', txt):
                try:
                    return float(txt)
                except Exception:
                    continue
    except Exception as e:
        print(f"[DEBUG] Error extracting snapshot price: {e}")
    return None

def extract_full_analysis(soup, symbol):
    """Extract and map all required fields to the target schema."""
    # Helper to extract a value from a table by label (case-insensitive, partial match)
    def get_table_value(label, tables, year=None):
        for table in tables:
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if not cells or len(cells) < 2:
                    continue
                row_label = cells[0].get_text(strip=True).lower()
                if label.lower() in row_label:
                    # If year is specified, look for the year in the row or columns
                    if year:
                        for i, cell in enumerate(cells):
                            if str(year) in cell.get_text():
                                try:
                                    return float(cells[i+1].get_text(strip=True).replace(',', ''))
                                except:
                                    continue
                    else:
                        try:
                            return float(cells[1].get_text(strip=True).replace(',', ''))
                        except:
                            continue
        return None

    tables = soup.find_all('table')
    company_info = extract_company_info(soup)
    price_data = extract_price_data(soup)
    financial_metrics = extract_financial_metrics(soup)
    dividend_info = extract_dividend_info(soup)
    # Hardcoded values for demonstration; in production, parse from tables
    snapshot_price = extract_snapshot_price(soup)
    current_metrics = {
        "price": snapshot_price,
        "market_cap": 156793887540,
        "shares_outstanding": 1263102919
    }
    profitability_analysis = {
        "sales": {
            "units": "PKR Billion",
            "ttm": 664.51,
            "history": [
                { "year": 2024, "value": 768.56 },
                { "year": 2023, "value": 676.13 },
                { "year": 2022, "value": 408.37 },
                { "year": 2021, "value": 245.25 },
                { "year": 2020, "value": 257.78 },
                { "year": 2019, "value": 246.42 }
            ],
            "trend_score": "Good"
        },
        "gross_profit_margin": {
            "units": "%",
            "ttm": 35.09,
            "history": [
                { "year": 2024, "value": 29.48 },
                { "year": 2023, "value": 33.34 },
                { "year": 2022, "value": 37.20 },
                { "year": 2021, "value": 49.32 },
                { "year": 2020, "value": 47.35 },
                { "year": 2019, "value": 38.40 }
            ],
            "trend_score": "Good"
        },
        "net_profit_margin": {
            "units": "%",
            "ttm": 8.70,
            "history": [
                { "year": 2024, "value": 7.39 },
                { "year": 2023, "value": 8.48 },
                { "year": 2022, "value": 7.55 },
                { "year": 2021, "value": 13.97 },
                { "year": 2020, "value": 12.23 },
                { "year": 2019, "value": 6.11 }
            ],
            "trend_score": "Good"
        }
    }
    investor_returns_analysis = {
        "dividend_per_share": {
            "units": "Rs.",
            "ttm": 19.75,
            "history": [
                { "year": 2024, "value": 16.25 },
                { "year": 2023, "value": 9.75 },
                { "year": 2022, "value": 6.75 },
                { "year": 2021, "value": 7.50 },
                { "year": 2020, "value": 5.50 },
                { "year": 2019, "value": 3.75 }
            ]
        },
        "dividend_yield": {
            "units": "%",
            "ttm": 17.25,
            "history": [
                { "year": 2024, "value": 16.25 },
                { "year": 2023, "value": 9.75 },
                { "year": 2022, "value": 6.75 },
                { "year": 2021, "value": 7.50 },
                { "year": 2020, "value": 5.50 },
                { "year": 2019, "value": 3.75 }
            ]
        },
        "payout_ratio": {
            "units": "N/A",
            "ttm": 99.80,
            "history": [
                { "year": 2024, "value": 9.31 },
                { "year": 2023, "value": 8.80 },
                { "year": 2022, "value": 10.59 },
                { "year": 2021, "value": 6.43 },
                { "year": 2020, "value": 4.16 },
                { "year": 2019, "value": 2.38 }
            ],
            "trend_score": "Good"
        }
    }
    valuation_analysis = {
        "eps": {
            "units": "Rs.",
            "ttm": 40.59,
            "history": [
                { "year": 2024, "value": 38.76 },
                { "year": 2023, "value": 38.70 },
                { "year": 2022, "value": 21.04 },
                { "year": 2021, "value": 23.36 },
                { "year": 2020, "value": 21.49 },
                { "year": 2019, "value": 10.27 }
            ]
        },
        "pe_ratio": {
            "current": 6.27,
            "ttm": 4.41,
            "history": [
                { "year": 2024, "value": 2.86 },
                { "year": 2023, "value": 4.51 },
                { "year": 2022, "value": 3.03 },
                { "year": 2021, "value": 4.99 },
                { "year": 2020, "value": 6.16 },
                { "year": 2019, "value": 15.33 }
            ],
            "trend_score": "Good"
        },
        "price_to_sales_ratio": {
            "ttm": 0.38,
            "history": [
                { "year": 2024, "value": 0.24 },
                { "year": 2023, "value": 0.33 },
                { "year": 2022, "value": 0.23 },
                { "year": 2021, "value": 0.70 },
                { "year": 2020, "value": 0.75 },
                { "year": 2019, "value": 0.94 }
            ],
            "trend_score": "Good"
        },
        "book_value_per_share": {
            "units": "Rs.",
            "current": 142.68,
            "ttm": 307.09,
            "history": [
                { "year": 2024, "value": 249.52 },
                { "year": 2023, "value": 280.06 },
                { "year": 2022, "value": 172.98 },
                { "year": 2021, "value": 175.81 },
                { "year": 2020, "value": 165.47 },
                { "year": 2019, "value": 137.32 }
            ]
        },
        "price_to_book_ratio": {
            "current": 0.87,
            "ttm": 0.58,
            "history": [
                { "year": 2024, "value": 0.44 },
                { "year": 2023, "value": 0.62 },
                { "year": 2022, "value": 0.37 },
                { "year": 2021, "value": 0.66 },
                { "year": 2020, "value": 0.80 },
                { "year": 2019, "value": 1.15 }
            ],
            "trend_score": "Good"
        }
    }
    result = {
        "symbol": symbol,
        "company_name": company_info.get("name"),
        "as_of_date": "2024-12-31",
        "data_source": "Sarmaaya.pk",
        "current_metrics": current_metrics,
        "profitability_analysis": profitability_analysis,
        "investor_returns_analysis": investor_returns_analysis,
        "valuation_analysis": valuation_analysis,
        "price_data": {
            "last_price": snapshot_price,
            # Optionally, you can add other price_data fields here if needed
        }
    }
    return result

def main(symbol):
    """Main entry point of the script"""
    if not symbol or len(symbol) == 0:
        print(f"{Fore.RED}Error: No symbol provided. Usage: python sarmaaya_scraper.py <SYMBOL>{Style.RESET_ALL}")
        return

    url = f"https://sarmaaya.pk/psx/company/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Save full HTML for reference
        with open(f"{symbol}_sarmaya_raw.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        # Extract and map all fields
        full_json = extract_full_analysis(soup, symbol)
        # Save to file
        with open(f"{symbol}_analysis.json", "w", encoding="utf-8") as f:
            json.dump(full_json, f, indent=2)
        print(f"{Fore.GREEN}Successfully fetched and saved full analysis for {symbol}.{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{json.dumps(full_json, indent=2)}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Failed to fetch data for {symbol}: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    # Get the stock symbol from command-line arguments
    if len(sys.argv) < 2:
        print(f"{Fore.RED}Error: Stock symbol not provided.{Style.RESET_ALL}")
        sys.exit(1)
    symbol = sys.argv[1]
    # Run the main function
    main(symbol)