#!/usr/bin/env python3
"""
PSX Stock Price Checker - Python Version
Usage: python test.py <SYMBOL>
"""

import sys
import requests
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import re
import json

# Initialize colorama for cross-platform colored output
init()

def fetch_and_display_stock(symbol):
    """Fetch and display stock information"""
    try:
        url = f"https://dps.psx.com.pk/company/{symbol}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"{Fore.YELLOW}Fetching {symbol}...{Style.RESET_ALL}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Check for actual 404 status, not content
        if response.status_code == 404:
            print(f"{Fore.RED}Error: Symbol '{symbol}' not found{Style.RESET_ALL}")
            return False
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract price
        price = None
        price_element = soup.select_one('.quote__close')
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_match = re.search(r'Rs\.?\s*([0-9,]+\.?[0-9]*)', price_text)
            if price_match:
                price = price_match.group(1).replace(',', '')
        
        # Extract change value
        change_value = None
        change_element = soup.select_one('.change__value')
        if change_element:
            change_text = change_element.get_text(strip=True)
            change_match = re.search(r'([0-9,]+\.?[0-9]*)', change_text)
            if change_match:
                change_value = change_match.group(1)
        
        # Extract percentage
        percentage = None
        percent_element = soup.select_one('.change__percent')
        if percent_element:
            percent_text = percent_element.get_text(strip=True)
            percent_match = re.search(r'[\(\-]?([0-9,]+\.?[0-9]*)%?[\)]?', percent_text)
            if percent_match:
                percentage = percent_match.group(1) + '%'
        
        # Determine direction based on change value
        direction = ""
        if change_value:
            try:
                change_float = float(change_value)
                if change_float > 0:
                    direction = "+"
                elif change_float < 0:
                    direction = "-"
                    change_value = str(abs(change_float))  # Make positive for display
            except ValueError:
                direction = ""
        
        # Validate data
        if not price:
            print(f"{Fore.RED}Error: Could not extract price for '{symbol}'{Style.RESET_ALL}")
            return False
        
        # Determine color
        if direction == "+":
            color = Fore.GREEN
        elif direction == "-":
            color = Fore.RED
        else:
            color = Style.RESET_ALL
        
        # Display results
        print(f"\n{Style.BRIGHT}{symbol}{Style.RESET_ALL}")
        print(f"{Style.BRIGHT}Price:{Style.RESET_ALL} Rs. {price}")
        
        if change_value and percentage:
            print(f"{Style.BRIGHT}Change:{Style.RESET_ALL} {color}{direction}{change_value} {percentage}{Style.RESET_ALL}")
        elif change_value:
            print(f"{Style.BRIGHT}Change:{Style.RESET_ALL} {color}{direction}{change_value}{Style.RESET_ALL}")
        elif percentage:
            print(f"{Style.BRIGHT}Change:{Style.RESET_ALL} {color}{direction}{percentage}{Style.RESET_ALL}")
        else:
            print(f"{Style.BRIGHT}Change:{Style.RESET_ALL} Data not available")
        
        print()
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Network error: {e}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        return False

def fetch_and_display_payouts(symbol):
    """Fetch and display payout information for a symbol from PSX"""
    try:
        url = f"https://dps.psx.com.pk/company/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        print(f"{Fore.YELLOW}Fetching payout info for {symbol}...{Style.RESET_ALL}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find the Payouts table
        payouts_header = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'Payouts' in tag.text)
        if not payouts_header:
            print(f"{Fore.RED}No payout section found for {symbol}.{Style.RESET_ALL}")
            return False
        # The table is usually the next sibling after the header
        payouts_table = payouts_header.find_next('table')
        if not payouts_table:
            print(f"{Fore.RED}No payout table found for {symbol}.{Style.RESET_ALL}")
            return False
        # Extract table headers
        headers = [th.get_text(strip=True) for th in payouts_table.find_all('th')]
        # Extract table rows
        rows = []
        for tr in payouts_table.find_all('tr')[1:]:  # skip header row
            cols = [td.get_text(strip=True) for td in tr.find_all('td')]
            if cols:
                rows.append(cols)
        if not rows:
            print(f"{Fore.RED}No payout data found for {symbol}.{Style.RESET_ALL}")
            return False
        # Print payout info
        print(f"\n{Style.BRIGHT}Payouts for {symbol}:{Style.RESET_ALL}")
        print(f"{' | '.join(headers)}")
        print('-' * 80)
        for row in rows:
            print(' | '.join(row))
        print()
        return True
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Network error: {e}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        return False

def fetch_and_save_html(symbol, filename="output.html"):
    """Fetch the HTML for a symbol and save to a file for inspection."""
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    print(f"Fetching HTML for {symbol}...")
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"HTML saved to {filename}")

def fetch_payouts_json(symbol):
    """Fetch payout information for a symbol from PSX and return as JSON list."""
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    payouts_section = soup.find('div', id='payouts')
    if not payouts_section:
        print("No payouts section found.")
        return []
    table = payouts_section.find('table')
    if not table:
        print("No payouts table found.")
        return []
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    payouts = []
    for tr in table.find_all('tr')[1:]:  # skip header row
        cols = [td.get_text(strip=True) for td in tr.find_all('td')]
        if cols and len(cols) == len(headers):
            payout = dict(zip(headers, cols))
            payouts.append(payout)
    return payouts

def extract_financials_from_html(html_path):
    """Extract annual and quarterly financials from a local HTML file and return as JSON dict."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    financials_section = soup.find('div', id='financials')
    if not financials_section:
        print("No financials section found.")
        return {}
    result = {}
    for tab_name in ["Annual", "Quarterly"]:
        # Find the tab panel for this tab
        panel = financials_section.find('div', class_='tabs__panel', attrs={'data-name': tab_name})
        if not panel:
            continue
        table = panel.find('table')
        if not table:
            continue
        # Get years/quarters from header
        header_cells = table.find_all('th')
        periods = [th.get_text(strip=True) for th in header_cells[1:]]  # skip first empty cell
        # Get row labels and values
        rows = []
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if not tds:
                continue
            label = tds[0].get_text(strip=True)
            values = [td.get_text(strip=True) for td in tds[1:]]
            row = {"label": label}
            for i, period in enumerate(periods):
                row[period] = values[i] if i < len(values) else None
            rows.append(row)
        result[tab_name.lower()] = rows
    return result

def restructure_financials(financials):
    def restructure_block(block):
        periods = []
        if not block:
            return periods
        period_keys = [k for k in block[0] if k != 'label']
        for period in period_keys:
            row = {'period': period}
            for item in block:
                row[item['label']] = item.get(period)
            periods.append(row)
        return periods
    return {
        'annual': restructure_block(financials.get('annual', [])),
        'quarterly': restructure_block(financials.get('quarterly', []))
    }

def fetch_financials_tidy_json(symbol):
    """Fetch annual and quarterly financials for a symbol from PSX and return as tidy JSON."""
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    financials_section = soup.find('div', id='financials')
    if not financials_section:
        print("No financials section found.")
        return {}
    result = {}
    for tab_name in ["Annual", "Quarterly"]:
        panel = financials_section.find('div', class_='tabs__panel', attrs={'data-name': tab_name})
        if not panel:
            continue
        table = panel.find('table')
        if not table:
            continue
        header_cells = table.find_all('th')
        periods = [th.get_text(strip=True) for th in header_cells[1:]]
        rows = []
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if not tds:
                continue
            label = tds[0].get_text(strip=True)
            values = [td.get_text(strip=True) for td in tds[1:]]
            row = {"label": label}
            for i, period in enumerate(periods):
                row[period] = values[i] if i < len(values) else None
            rows.append(row)
        result[tab_name.lower()] = rows
    # Restructure to tidy format
    return restructure_financials(result)

def extract_ratios_from_html(html_path):
    """Extract ratios from a local HTML file and return as tidy JSON list (one record per year)."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    ratios_section = soup.find('div', id='ratios')
    if not ratios_section:
        print("No ratios section found.")
        return []
    table = ratios_section.find('table')
    if not table:
        print("No ratios table found.")
        return []
    header_cells = table.find_all('th')
    periods = [th.get_text(strip=True) for th in header_cells[1:]]  # skip first empty cell
    # Get row labels and values
    rows = []
    for tr in table.find_all('tr')[1:]:
        tds = tr.find_all('td')
        if not tds:
            continue
        label = tds[0].get_text(strip=True)
        values = [td.get_text(strip=True) for td in tds[1:]]
        row = {"label": label}
        for i, period in enumerate(periods):
            row[period] = values[i] if i < len(values) else None
        rows.append(row)
    # Restructure to tidy format
    tidy = []
    for i, period in enumerate(periods):
        record = {"period": period}
        for row in rows:
            record[row["label"]] = row.get(period)
        tidy.append(record)
    return tidy

def fetch_ratios_tidy_json(symbol):
    """Fetch ratios for a symbol from PSX and return as tidy JSON list (one record per year)."""
    url = f"https://dps.psx.com.pk/company/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    ratios_section = soup.find('div', id='ratios')
    if not ratios_section:
        print("No ratios section found.")
        return []
    table = ratios_section.find('table')
    if not table:
        print("No ratios table found.")
        return []
    header_cells = table.find_all('th')
    periods = [th.get_text(strip=True) for th in header_cells[1:]]  # skip first empty cell
    # Get row labels and values
    rows = []
    for tr in table.find_all('tr')[1:]:
        tds = tr.find_all('td')
        if not tds:
            continue
        label = tds[0].get_text(strip=True)
        values = [td.get_text(strip=True) for td in tds[1:]]
        row = {"label": label}
        for i, period in enumerate(periods):
            row[period] = values[i] if i < len(values) else None
        rows.append(row)
    # Restructure to tidy format
    tidy = []
    for i, period in enumerate(periods):
        record = {"period": period}
        for row in rows:
            record[row["label"]] = row.get(period)
        tidy.append(record)
    return tidy

def fetch_all_psx_data(symbol):
    """Fetch all PSX data for a symbol and return as a single JSON object."""
    # Stock info
    stock_info = {}
    try:
        url = f"https://dps.psx.com.pk/company/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Price
        price = None
        price_element = soup.select_one('.quote__close')
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_match = re.search(r'Rs\.?\s*([0-9,]+\.?[0-9]*)', price_text)
            if price_match:
                price = price_match.group(1).replace(',', '')
        # Change value
        change_value = None
        change_element = soup.select_one('.change__value')
        if change_element:
            change_text = change_element.get_text(strip=True)
            change_match = re.search(r'([0-9,]+\.?[0-9]*)', change_text)
            if change_match:
                change_value = change_match.group(1)
        # Percentage
        percentage = None
        percent_element = soup.select_one('.change__percent')
        if percent_element:
            percent_text = percent_element.get_text(strip=True)
            percent_match = re.search(r'[\(\-]?([0-9,]+\.?[0-9]*)%?[\)]?', percent_text)
            if percent_match:
                percentage = percent_match.group(1) + '%'
        # Direction
        direction = ""
        if change_value:
            try:
                change_float = float(change_value)
                if change_float > 0:
                    direction = "+"
                elif change_float < 0:
                    direction = "-"
                    change_value = str(abs(change_float))
            except ValueError:
                direction = ""
        stock_info = {
            "symbol": symbol,
            "price": price,
            "change_value": direction + change_value if change_value else None,
            "percentage": percentage,
        }
    except Exception as e:
        stock_info = {"error": str(e)}
    # Payouts
    payouts = fetch_payouts_json(symbol)
    # Financials
    financials = fetch_financials_tidy_json(symbol)
    # Ratios
    ratios = fetch_ratios_tidy_json(symbol)
    return {
        "stock": stock_info,
        "payouts": payouts,
        "financials": financials,
        "ratios": ratios
    }

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print(f"{Style.BRIGHT}Usage:{Style.RESET_ALL} python {sys.argv[0]} <STOCK_SYMBOL> [--payouts]")
        print(f"{Style.BRIGHT}Example:{Style.RESET_ALL} python {sys.argv[0]} HBL --payouts")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    show_payouts = '--payouts' in sys.argv
    
    if show_payouts:
        success = fetch_and_display_payouts(symbol)
    else:
        success = fetch_and_display_stock(symbol)
    
    if not success:
        sys.exit(1)

# CLI usage: python test.py --extract-payouts output.html
if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].isalpha():
        symbol = sys.argv[1].upper()
        all_data = fetch_all_psx_data(symbol)
        print(json.dumps(all_data, indent=2, ensure_ascii=False))
        sys.exit(0)
    
    main()
