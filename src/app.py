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

# Main UI section - Create this before any other content
main_container = st.container()
tab_nav_container = st.container()
content_container = st.container()

# Initialize session state for data persistence
if 'data' not in st.session_state:
    st.session_state.data = None
if 'summary_df' not in st.session_state:
    st.session_state.summary_df = None
if 'signals_df' not in st.session_state:
    st.session_state.signals_df = None
if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime.now().date() - timedelta(days=365)
if 'end_date' not in st.session_state:
    st.session_state.end_date = datetime.now().date() - timedelta(days=1)
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Charts"
if 'previous_ticker' not in st.session_state:
    st.session_state.previous_ticker = None
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None

# Initialize stock list if not already done
if 'stock_list' not in st.session_state:
    # Read the local CSV file
    stocks_df = pd.read_csv('src/data/us_symbols.csv')
    # Create formatted strings for the dropdown
    stocks_df['display_name'] = stocks_df.apply(lambda x: f"{x['ticker']} - {x['name']} ({x['exchange']})", axis=1)
    # Create a dictionary for easy ticker lookup
    st.session_state.ticker_to_display = dict(zip(stocks_df['ticker'], stocks_df['display_name']))
    # Store the display names list for the dropdown
    st.session_state.stock_list = stocks_df['display_name'].tolist()
    # Store the tickers list
    st.session_state.tickers = stocks_df['ticker'].tolist()
    # Set default ticker
    st.session_state.selected_ticker = 'NVDA'
    st.session_state.previous_ticker = 'NVDA'

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

def validate_ticker(ticker: str) -> Tuple[bool, Optional[yf.Ticker], str]:
    """
    Validate if the ticker exists and has data.
    
    Args:
        ticker: Stock symbol to validate
        
    Returns:
        Tuple of (is_valid, ticker_object, error_message)
    """
    if not ticker:
        return False, None, "Please enter a ticker symbol"
    
    try:
        ticker_obj = yf.Ticker(ticker)
        # Try to get info to validate ticker
        info = ticker_obj.info
        
        # Debug info
        # st.sidebar.write("Debug - Available info keys:", list(info.keys()) if info else "No info available")
        
        # More lenient validation - check if we can get any basic info
        if info and any([
            info.get('regularMarketPrice'),
            info.get('currentPrice'),
            info.get('ask'),
            info.get('bid'),
            info.get('previousClose')
        ]):
            return True, ticker_obj, ""
            
        return False, None, "No market data available for this ticker"
    except Exception as e:
        return False, None, f"Invalid ticker symbol or API error: {str(e)}"

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # Stock Selection
    st.subheader("Stock Selection")
    
    # Stock selector with company names
    selected_display = st.selectbox(
        "Select Stock",
        options=st.session_state.stock_list,
        index=st.session_state.stock_list.index(st.session_state.ticker_to_display[st.session_state.selected_ticker]),
        help="Select a stock or type to search by symbol/company name",
        key="stock_selector"
    )
    
    # Extract ticker from the selection
    temp_ticker = selected_display.split(' - ')[0]
    
    # Apply button for stock selection
    if st.button("Apply Stock Selection", type="primary"):
        if temp_ticker != st.session_state.selected_ticker:
            st.session_state.data = None
            st.session_state.summary_df = None
            st.session_state.signals_df = None
            st.session_state.previous_ticker = st.session_state.selected_ticker
            st.session_state.selected_ticker = temp_ticker
            st.rerun()
    
    # Show current selection status
    if temp_ticker != st.session_state.selected_ticker:
        st.info(f"Click 'Apply' to switch to {temp_ticker}")
        # Use the current selected ticker for validation
        ticker = st.session_state.selected_ticker
    else:
        ticker = temp_ticker
    
    # Validate ticker
    is_valid_ticker, ticker_obj, ticker_error = validate_ticker(ticker)
    if not is_valid_ticker:
        st.error(ticker_error)
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
            value=st.session_state.start_date,
            help="Select the start date for analysis",
            max_value=today - timedelta(days=1)
        )
        if start_date != st.session_state.start_date:
            st.session_state.start_date = start_date
            
    with col2:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.end_date,
            help="Select the end date for analysis",
            min_value=start_date,
            max_value=today
        )
        if end_date != st.session_state.end_date:
            st.session_state.end_date = end_date

# Validate dates
is_valid_dates, date_error = validate_dates(start_date, end_date, holding_period)
if not is_valid_dates:
    st.error(date_error)

# Check if all conditions are valid for analysis
is_ready_to_run = is_valid_ticker and is_valid_dates

# Run Analysis button with conditional styling
if st.sidebar.button(
    "Run Analysis",
    type="primary" if is_ready_to_run else "secondary",
    disabled=not is_ready_to_run
):
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
        
        # Generate report and store in session state
        st.session_state.data = df
        st.session_state.summary_df, st.session_state.signals_df = generate_signals_report(df)

def render_chart_tab():
    """Render the chart tab content"""
    st.subheader("Price and Volume Analysis")
    fig = create_stock_chart(st.session_state.data, title=f"{ticker} - Volume Breakout Analysis")
    st.plotly_chart(fig, use_container_width=True)

def render_report_tab():
    """Render the report tab content"""
    st.subheader("Breakout Signals")
    if len(st.session_state.signals_df) > 0:
        st.dataframe(
            st.session_state.signals_df.style.format({
                'Entry_Price': '${:.2f}',
                'Exit_Price': '${:.2f}',
                'Volume': '{:,.0f}',
                'Volume_MA_20': '{:,.0f}'
            })
        )
        
        # Download buttons
        csv = st.session_state.signals_df.to_csv(index=True)
        st.download_button(
            label="Download Report (CSV)",
            data=csv,
            file_name=f"{ticker}_breakout_report.csv",
            mime="text/csv"
        )
    else:
        st.info("No breakout signals found in the selected period.")

def render_summary_tab():
    """Render the summary tab content"""
    st.subheader("Strategy Summary")
    st.dataframe(
        st.session_state.summary_df,
        width=800,
        height=600
    )

# Map of tab names to their render functions
TAB_RENDERERS = {
    "Charts": render_chart_tab,
    "Report": render_report_tab,
    "Summary": render_summary_tab
}

# After all sidebar content, in the main area
with main_container:
    # Title and description
    st.title("📈 Volume Breakout Strategy Scanner")
    st.markdown("""
    This tool helps identify and analyze volume breakout patterns in stocks. 
    It looks for instances where both volume and price action show significant increases, 
    potentially indicating strong directional moves.
    """)

    if st.session_state.data is not None:
        # Tab selection
        with tab_nav_container:
            tabs = ["Charts", "Report", "Summary"]
            selected_tab = st.radio(
                label="Navigation",
                options=tabs,
                horizontal=True,
                key="tab_navigation",
                label_visibility="collapsed"
            )
            
            # Update active tab if selection changed
            if selected_tab != st.session_state.active_tab:
                st.session_state.active_tab = selected_tab

        # Content area
        with content_container:
            # Render the active tab content
            TAB_RENDERERS[st.session_state.active_tab]() 