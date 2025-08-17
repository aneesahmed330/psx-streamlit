# PSX Stock Price Checker

This repository contains both bash and Python versions of a PSX (Pakistan Stock Exchange) stock price checker.

## Python Version (Recommended)

The Python version uses BeautifulSoup for reliable HTML parsing and provides colored output.

### Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

### Usage

```bash
python test.py <STOCK_SYMBOL>
```

### Examples

```bash
python test.py HBL
python test.py OGDC
python test.py TRG
python test.py LUCK
```

### Features

- **Reliable parsing**: Uses BeautifulSoup for HTML parsing
- **Colored output**: Green for positive changes, red for negative
- **Comprehensive data**: Shows price, change value, and percentage
- **Error handling**: Proper network and parsing error handling
- **Cross-platform**: Works on Linux, macOS, and Windows

### Output Format

```
HBL
Price: Rs. 275.76
Change: +4.70 1.73%
```

## Bash Version

The original bash script is available as `psx.sh` but may be less reliable due to HTML parsing limitations.

### Usage

```bash
./psx.sh <STOCK_SYMBOL>
```

## Dependencies

### Python Version
- requests
- beautifulsoup4
- colorama

### Bash Version
- curl
- grep
- sed
- tr

## Troubleshooting

If you encounter import errors, make sure you have installed the Python packages:

```bash
pip install requests beautifulsoup4 colorama
```

For virtual environment users:
```bash
python -m pip install -r requirements.txt
```
