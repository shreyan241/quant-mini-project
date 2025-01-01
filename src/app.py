import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_market_calendars as mcal
from datetime import datetime, timedelta
import plotly.graph_objects as go
from typing import Tuple, Optional

from analysis.metrics import (
    calculate_volume_metrics,
    calculate_price_changes,
    identify_breakout_signals,
    calculate_forward_returns,
    generate_signals_report
)
from visualization.charts import create_stock_chart
from data.stock_data import get_stock_data

# Page config
st.set_page_config(
    page_title="Volume Breakout Scanner",
    page_icon="📈",
    layout="wide"
)

# Title and description
st.title("📈 Volume Breakout Strategy Scanner")
st.markdown("""
This tool helps identify and analyze volume breakout patterns in stocks. 
It looks for instances where both volume and price action show significant increases, 
potentially indicating strong directional moves.
""")

def validate_dates(start_date: datetime, end_date: datetime, holding_period: int) -> Tuple[bool, str]:
    """
    Validate the selected date range considering trading days and holding period.
    
    Args:
        start_date: Selected start date
        end_date: Selected end date
        holding_period: Number of trading days for holding period
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Convert date objects to pandas Timestamp
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    today = pd.Timestamp.now().normalize()
    
    # Get NYSE calendar
    nyse = mcal.get_calendar('NYSE')
    
    # Check if end_date is after start_date
    if end_ts <= start_ts:
        return False, "End date must be after start date"
    
    # Calculate trading days up to today
    trading_days_to_today = nyse.valid_days(start_date=end_ts, end_date=today)
    
    # Check if we have enough future data for holding period
    if len(trading_days_to_today) <= holding_period:
        return False, f"End date must be at least {holding_period} trading days before today"
    
    # Calculate trading days for analysis period
    trading_days = nyse.valid_days(start_date=start_ts, end_date=end_ts)
    
    # Check if we have enough trading days for analysis (minimum 30 days recommended)
    if len(trading_days) < 30:
        return False, "Selected period too short (minimum 30 days recommended)"
    
    return True, ""

def validate_ticker(ticker: str) -> Tuple[bool, Optional[yf.Ticker]]:
    """
    Validate if the ticker exists and has data.
    
    Args:
        ticker: Stock symbol to validate
        
    Returns:
        Tuple of (is_valid, ticker_object)
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        # Try to get info to validate ticker
        info = ticker_obj.info
        return True, ticker_obj
    except:
        return False, None

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # Stock Selection
    st.subheader("Stock Selection")
    ticker = st.text_input(
        "Enter Stock Symbol",
        value="NVDA",
        help="Enter a valid stock symbol (e.g., AAPL, MSFT, GOOGL)"
    ).upper()
    
    # Validate ticker
    is_valid_ticker, ticker_obj = validate_ticker(ticker)
    if not is_valid_ticker:
        st.error("Invalid ticker symbol. Please enter a valid stock symbol.")
    else:
        # Show stock info
        info = ticker_obj.info
        st.success(f"Selected: {info.get('longName', ticker)}")
        if 'sector' in info:
            st.info(f"Sector: {info['sector']}")
    
    # Strategy Parameters
    st.subheader("Strategy Parameters")
    
    volume_threshold = st.slider(
        "Volume Breakout Threshold",
        min_value=1.0,
        max_value=10.0,
        value=2.0,
        step=0.1,
        help="Minimum ratio of current volume to 20-day moving average"
    )
    
    price_threshold = st.slider(
        "Price Change Threshold (%)",
        min_value=1.0,
        max_value=10.0,
        value=2.0,
        step=0.1,
        help="Minimum daily price change percentage"
    )
    
    holding_period = st.slider(
        "Holding Period (Trading Days)",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
        help="Number of trading days to hold position"
    )
    
    # Date Range
    st.subheader("Date Range")
    today = datetime.now().date()
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=today - timedelta(days=365),
            help="Select the start date for analysis",
            max_value=today - timedelta(days=1)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=today - timedelta(days=holding_period + 1),  # Default to holding_period days before today
            help="Select the end date for analysis",
            min_value=start_date,
            max_value=today
        )

# Validate dates
is_valid_dates, date_error = validate_dates(start_date, end_date, holding_period)
if not is_valid_dates:
    st.error(date_error)
    st.stop()

# Run Analysis button
if st.sidebar.button("Run Analysis", type="primary"):
    if not is_valid_ticker:
        st.error("Please enter a valid ticker symbol before running analysis.")
        st.stop()
    
    with st.spinner(f"Analyzing {ticker}..."):
        # Fetch data with holding period adjustment
        data = get_stock_data(ticker, start_date, end_date, holding_period)
        
        if data is None:
            st.error("Could not fetch sufficient data for the selected period and holding period.")
            st.stop()
        
        # Process data
        df = calculate_volume_metrics(data)
        df = calculate_price_changes(df)
        df = identify_breakout_signals(df, volume_threshold, price_threshold)
        df = calculate_forward_returns(df, holding_period)
        
        # Generate report
        summary_df, signals_df = generate_signals_report(df)
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Charts", "Signals", "Summary"])
        
        with tab1:
            st.subheader("Price and Volume Analysis")
            fig = create_stock_chart(df, title=f"{ticker} - Volume Breakout Analysis")
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Breakout Signals")
            if len(signals_df) > 0:
                st.dataframe(
                    signals_df.style.format({
                        'Price': '${:.2f}',
                        'Volume_Ratio': '{:.2f}x',
                        'Price_Change_Pct': '{:+.2f}%',
                        'Forward_Return': '{:+.2f}%'
                    })
                )
                
                # Download buttons
                csv = signals_df.to_csv(index=True)
                st.download_button(
                    label="Download Signals (CSV)",
                    data=csv,
                    file_name=f"{ticker}_breakout_signals.csv",
                    mime="text/csv"
                )
            else:
                st.info("No breakout signals found in the selected period.")
        
        with tab3:
            st.subheader("Strategy Summary")
            st.dataframe(summary_df) 