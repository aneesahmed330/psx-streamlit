#!/usr/bin/env python3
"""
PSX Stock Price Checker - Python Version (Working)
Usage: python psx_checker.py <SYMBOL>
"""

import sys
import requests
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import re

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

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print(f"{Style.BRIGHT}Usage:{Style.RESET_ALL} python {sys.argv[0]} <STOCK_SYMBOL>")
        print(f"{Style.BRIGHT}Example:{Style.RESET_ALL} python {sys.argv[0]} HBL")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    success = fetch_and_display_stock(symbol)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
