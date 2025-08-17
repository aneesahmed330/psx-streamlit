#!/bin/bash
# filepath: /home/dex/Desktop/dev/bash/psx.sh

# Simple PSX Stock Price Checker
# Usage: ./psx.sh <SYMBOL>

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# Check if symbol provided
if [ $# -eq 0 ]; then
    echo -e "${BOLD}Usage:${NC} $0 <STOCK_SYMBOL>"
    echo -e "${BOLD}Example:${NC} $0 HBL"
    exit 1
fi

# Convert to uppercase
SYMBOL=$(echo "$1" | tr '[:lower:]' '[:upper:]')

echo -e "${YELLOW}Fetching $SYMBOL...${NC}"

# Fetch data
html=$(curl -s "https://dps.psx.com.pk/company/$SYMBOL")

# Check if data exists
if [ -z "$html" ] || echo "$html" | grep -qi "page not found\|404\|error"; then
    echo -e "${RED}Error: Symbol '$SYMBOL' not found${NC}"
    exit 1
fi

# Extract price using the correct HTML structure
price=$(echo "$html" | grep -o 'class="quote__close"[^>]*>Rs\.[^<]*' | sed 's/.*>Rs\.//' | tr -d ' ')

# Extract change value
change_value=$(echo "$html" | grep -o 'class="change__value"[^>]*>[^<]*' | sed 's/.*>//' | tr -d ' ')

# Extract percentage change
percentage=$(echo "$html" | grep -o 'class="change__percent"[^>]*>[^<]*' | sed 's/.*>//' | tr -d '()' | tr -d ' ')

# Check if the change is positive or negative by looking for the CSS class
if echo "$html" | grep -q 'change__text--pos'; then
    direction="+"
elif echo "$html" | grep -q 'change__text--neg'; then
    direction="-"
else
    direction=""
fi

# Validate extracted data
if [ -z "$price" ] || [ -z "$percentage" ]; then
    echo -e "${RED}Error: Symbol '$SYMBOL' not found${NC}"
    exit 1
fi

# Determine color based on positive/negative change
if [ "$direction" = "+" ]; then
    color=$GREEN
elif [ "$direction" = "-" ]; then
    color=$RED
else
    color=$NC  # No color if direction is unknown
fi

# Display result
echo -e "\n${BOLD}$SYMBOL${NC}"
echo -e "${BOLD}Price:${NC} Rs. $price"
echo -e "${BOLD}Change:${NC} ${color}${direction}$change_value $percentage${NC}\n"