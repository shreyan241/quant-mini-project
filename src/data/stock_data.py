import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_data(ttl="1h")
def get_stock_data(ticker: str, start_date: datetime, end_date: datetime, holding_period: int = 10) -> Optional[pd.DataFrame]:
    """
    Get stock data from Yahoo Finance with adjusted end date for holding period.
    
    Args:
        ticker: Stock symbol
        start_date: Start date for data
        end_date: End date for analysis
        holding_period: Number of trading days to extend beyond end_date (default 0)
        
    Returns:
        DataFrame with stock data or None if data not available
    """
    try:
        # Adjust end date by adding holding period days
        adjusted_end_date = end_date + timedelta(days=holding_period + 5)  # Add a few extra days for buffer
        
        # Fetch data
        df = yf.download(
            ticker,
            start=start_date,
            end=adjusted_end_date,
            progress=False
        )
        
        if len(df) == 0:
            logger.error(f"No data received for {ticker}")
            return None
        
        # Flatten column multi-index and rename columns
        if isinstance(df.columns, pd.MultiIndex):
            # Get the first level of column names (Open, High, Low, Close, Volume)
            df.columns = df.columns.get_level_values(0)
        
        # Validate required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Missing required columns for {ticker}")
            return None
            
        # Clean data
        df = clean_data(df)
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and preprocesses the data.
    
    Args:
        df: Raw DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    # Forward fill missing values (for market holidays)
    df = df.ffill()
    
    # Remove any remaining missing values
    df = df.dropna()
    
    # Ensure datetime index
    df.index = pd.to_datetime(df.index)
    
    # Sort by date
    df = df.sort_index()
    
    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]
    
    return df 