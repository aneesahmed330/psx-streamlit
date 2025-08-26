# PSX Portfolio Dashboard 📈

A comprehensive **Pakistan Stock Exchange (PSX) Portfolio Management Dashboard** built with Streamlit. Track your investments, analyze stock performance, predict future returns, and manage your complete PSX portfolio with professional-grade analytics.

## 🚀 Features Overview

### 📊 **Portfolio Management**
- **Real-time Portfolio Tracking**: Live portfolio value, P&L, and performance metrics
- **Trade Management**: Log buy/sell trades with detailed history and analytics
- **Investment Calculations**: Automatic average cost, market value, and unrealized P&L calculation
- **FIFO Profit Calculation**: Accurate realized profit calculation using First-In-First-Out method

### 💹 **Price Monitoring & Alerts**
- **Live Price Fetching**: Real-time price updates from PSX with parallel processing
- **Price History**: Comprehensive historical price tracking and visualization
- **Smart Alerts**: Set min/max price alerts with enable/disable functionality
- **Auto-refresh**: Configurable automatic price refresh intervals

### 📈 **Advanced Analytics**
- **Portfolio Performance Charts**: Interactive pie charts, bar charts, and trend analysis
- **Normalized Price Comparison**: Compare multiple stocks on a normalized scale
- **Portfolio Value Over Time**: Track your portfolio growth with time-series visualization
- **Performance Metrics Cards**: Best/worst performers, largest holdings, total gains/losses

### 🔍 **Stock Analytics & Comparison**
- **7-Day Performance Analysis**: Daily percentage changes with consistent performer highlighting
- **Single Stock Deep Dive**: Comprehensive financials, ratios, dividend history, and scoring
- **Multi-Stock Comparison**: Side-by-side comparison with relative scoring and radar charts
- **Advanced Scoring System**: 10-point weighted scoring based on financial metrics
- **Visual Analytics**: Trend charts, score breakdowns, and performance radar

### 📊 **Professional Trade Analytics**
- **Monthly Investment Analysis**: Track investment patterns by symbol and time
- **Buy/Sell Volume Analysis**: Visualize trading activity across symbols
- **Cumulative Investment vs P&L**: Track growth and drawdowns over time
- **Win Rate & Return Analysis**: Trading effectiveness metrics and statistics
- **Portfolio Allocation**: Investment distribution analysis with pie charts

### 🔮 **Future Predictor**
- **SIP Simulation**: Monthly investment simulation with realistic growth projections
- **Dividend Forecasting**: Project future dividend income based on historical patterns
- **Portfolio Projection**: Multi-year capital growth simulation with annual rebalancing
- **ROI & CAGR Calculation**: Return on investment and compound annual growth rate metrics
- **Conservative Modeling**: Capped growth rates and realistic assumptions

### 🏦 **Stock Database Management**
- **Company Information**: Automatic fetching of financials, ratios, and payout data
- **Parallel Processing**: High-speed data fetching with threading for optimal performance
- **Smart Caching**: Intelligent caching system for faster load times
- **Data Validation**: Robust data cleaning and validation for reliable analytics

## 🛠 **Technical Specifications**

### **Technology Stack**
- **Frontend**: Streamlit with custom CSS styling
- **Backend**: Python with MongoDB integration
- **Visualization**: Plotly for interactive charts and graphs
- **Data Processing**: Pandas for efficient data manipulation
- **Web Scraping**: BeautifulSoup with requests for PSX data extraction
- **Parallel Processing**: ThreadPoolExecutor for optimized performance

### **Key Dependencies**
```python
streamlit>=1.28.0
pandas>=1.5.0
plotly>=5.15.0
pymongo>=4.5.0
beautifulsoup4>=4.12.0
requests>=2.31.0
python-dotenv>=1.0.0
pytz>=2023.3
numpy>=1.24.0
```

## 📦 **Installation & Setup**

### **1. Clone Repository**
```bash
git clone https://github.com/yourusername/psx-portfolio-dashboard.git
cd psx-portfolio-dashboard
```

### **2. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **3. Environment Configuration**
Create a `.env` file with your MongoDB configuration:
```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=psx_portfolio
```

### **4. Run Application**
```bash
streamlit run psx_dashboard.py
```

### **5. Access Dashboard**
Open your browser and navigate to `http://localhost:8501`

## 🔐 **Authentication**
Default login credentials:
- **Email**: `123`
- **Password**: `123`

## 📱 **User Interface**

### **Dashboard Tabs**
1. **📊 Portfolio Details**: Holdings overview with color-coded performance
2. **📈 Performance Analytics**: Visual charts, metrics, and trend analysis
3. **💼 Trade History**: Complete trade log with filtering and analytics
4. **📊 Stock Analytics & Comparison**: Deep stock analysis and comparison tools
5. **🔮 Future Predictor**: Investment simulation and forecasting
6. **🔔 Alerts Management**: Price alert configuration and monitoring

### **Sidebar Features**
- **🔄 Price Actions**: Manual price fetching and company info updates
- **📝 Log Trade**: Quick trade entry form
- **🔔 Price Alerts**: Alert creation and management
- **🏦 Manage Stocks**: Add/remove stocks for analytics

## 🎯 **Key Capabilities**

### **Real-time Monitoring**
- Live portfolio value tracking
- Automatic price updates every 5 minutes
- Real-time P&L calculations
- Instant alert notifications

### **Advanced Analytics**
- **Weighted Scoring System**: EPS Growth, Profit Margins, PEG Ratios, Dividend Consistency
- **Relative Performance Analysis**: Compare stocks against each other
- **Trend Analysis**: Historical performance patterns and projections
- **Risk Assessment**: Portfolio diversification and allocation analysis

### **Professional Reporting**
- **Exportable Data**: Download portfolio and trade data as CSV
- **Visual Reports**: Professional charts and graphs for presentations
- **Performance Metrics**: Comprehensive KPIs and financial ratios
- **Historical Analysis**: Track performance over custom date ranges

## 🚀 **Performance Optimizations**

- **Parallel Data Fetching**: Multi-threaded price and company data retrieval
- **Smart Caching**: 5-minute TTL caching for frequently accessed data
- **Lazy Loading**: On-demand data loading for faster tab switching
- **Optimized Queries**: Efficient MongoDB aggregation pipelines
- **Progressive Enhancement**: Form-based interactions to prevent unnecessary reruns

## 📊 **Supported Metrics**

### **Financial Metrics**
- EPS (Earnings Per Share) and growth rates
- Net Profit Margin and trends
- PEG Ratio (Price/Earnings to Growth)
- Dividend yield and consistency
- Profit After Tax (PAT) growth
- Revenue and income analysis

### **Portfolio Metrics**
- Total investment and market value
- Realized and unrealized P&L
- Portfolio percentage changes
- Asset allocation and diversification
- Win rate and average returns
- CAGR and ROI calculations

## 🔧 **Data Sources**
- **PSX Company Pages**: Real-time price data from official PSX listings
- **Financial Reports**: Automatic extraction of annual and quarterly data
- **Dividend History**: Complete payout records and analysis
- **Market Ratios**: Key financial ratios and growth metrics

## 📈 **Visualization Features**
- **Interactive Charts**: Plotly-powered responsive visualizations
- **Customizable Views**: Date range filtering and symbol selection
- **Color-coded Performance**: Green/red indicators for gains/losses
- **Professional Styling**: Dark theme with modern UI components
- **Responsive Design**: Optimized for desktop and mobile viewing

## 🛡️ **Data Management**
- **MongoDB Integration**: Scalable document-based storage
- **Data Validation**: Input sanitization and error handling
- **Backup & Recovery**: Robust data persistence and integrity
- **Historical Preservation**: Complete audit trail of all transactions

## 🔄 **Future Enhancements**
- [ ] Mobile app development
- [ ] Real-time WebSocket price feeds
- [ ] Advanced technical indicators
- [ ] Portfolio optimization algorithms
- [ ] Risk management tools
- [ ] Social trading features

## 🤝 **Contributing**
Contributions are welcome! Please feel free to submit pull requests, report bugs, or suggest new features.

## 📄 **License**
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 📞 **Support**
For support, questions, or feedback, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for the Pakistani investment community**
