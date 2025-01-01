import pandas as pd
import numpy as np
from typing import Tuple, Dict

def calculate_volume_metrics(df: pd.DataFrame, lookback_period: int = 20) -> pd.DataFrame:
    """
    Calculate volume-related metrics including volume ratio over moving average.
    
    Args:
        df: DataFrame with OHLCV data
        lookback_period: Period for volume moving average (default 20 days)
    
    Returns:
        DataFrame with additional volume metrics
    """
    # Create a copy to avoid modifying original
    df = df.copy()
    
    # Calculate volume moving average (previous N days only to avoid lookahead)
    df['Volume_MA'] = df['Volume'].rolling(window=lookback_period, min_periods=lookback_period).mean().shift(1)
    
    # Calculate volume ratio (current volume / moving average)
    # Handle potential division by zero or NaN values
    df['Volume_Ratio'] = df['Volume'].div(df['Volume_MA']).replace([np.inf, -np.inf], np.nan)
    
    return df

def calculate_price_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily price changes and returns.
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        DataFrame with additional price metrics
    """
    # Create a copy to avoid modifying original
    df = df.copy()
    
    # Calculate daily price change percentage
    df['Price_Change_Pct'] = df['Close'].pct_change() * 100
    
    return df

def identify_breakout_signals(df: pd.DataFrame, 
                            volume_threshold: float = 2.0,
                            price_change_threshold: float = 2.0) -> pd.DataFrame:
    """
    Identify breakout signals based on volume and price criteria.
    
    Args:
        df: DataFrame with volume and price metrics
        volume_threshold: Volume must be this percentage greater than average
                        (e.g., 2.0 means 200% greater = 3x average volume)
        price_change_threshold: Minimum price change percentage
    
    Returns:
        DataFrame with breakout signals
    """
    # Create a copy to avoid modifying original
    df = df.copy()
    
    # Convert percentage greater than to actual ratio
    # e.g., 200% greater = 3x average (original 100% + additional 200%)
    volume_ratio_threshold = 1 + volume_threshold
    
    # Identify breakout conditions
    volume_condition = df['Volume_Ratio'] > volume_ratio_threshold
    price_condition = df['Price_Change_Pct'] > price_change_threshold
    
    # Combine conditions
    df['Is_Breakout'] = volume_condition & price_condition
    
    return df

def calculate_forward_returns(df: pd.DataFrame, 
                            holding_period: int = 10) -> pd.DataFrame:
    """
    Calculate forward returns for each breakout signal.
    Also calculates exit dates and prices for convenience.
    
    Args:
        df: DataFrame with breakout signals
        holding_period: Number of days to hold after breakout
    
    Returns:
        DataFrame with forward returns, exit dates, and exit prices
    """
    # Create a copy to avoid modifying original
    df = df.copy()
    
    # Initialize columns
    df['Forward_Returns'] = np.nan
    df['Exit_Date'] = pd.NaT
    df['Exit_Price'] = np.nan
    
    # Calculate forward returns only for breakout days
    breakout_days = df[df['Is_Breakout']].index
    
    for day in breakout_days:
        try:
            # Get the closing price on breakout day
            entry_price = df.loc[day, 'Close']
            
            # Get the closing price N days later
            exit_idx = df.index.get_loc(day) + holding_period
            if exit_idx < len(df):
                exit_date = df.index[exit_idx]
                exit_price = df.iloc[exit_idx]['Close']
                
                # Store exit information
                df.loc[day, 'Exit_Date'] = exit_date
                df.loc[day, 'Exit_Price'] = exit_price
                
                # Calculate return
                returns = (exit_price - entry_price) / entry_price * 100
                df.loc[day, 'Forward_Returns'] = returns
                
        except Exception as e:
            print(f"Error calculating returns for {day}: {str(e)}")
            continue  # Skip this signal and move to next
    
    return df

# Helper function to format with sign
def format_with_sign(value: float) -> str:
    return f"{'+' if value > 0 else ''}{value:.2f}%"

def generate_signals_report(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate a detailed report of all breakout signals and their outcomes,
    including a summary of statistics.
    Uses data that has already been processed by calculate_forward_returns.
    
    Args:
        df: DataFrame with breakout signals and forward returns
        
    Returns:
        Tuple of (summary_df, signals_df) where:
            - summary_df: DataFrame with summary statistics
            - signals_df: DataFrame with detailed signal information for each breakout
    """
    # Get summary statistics
    summary_stats = generate_breakout_summary(df)
    
    # Convert summary dict to DataFrame for easier export
    summary_df = pd.DataFrame({
        'Metric': list(summary_stats.keys()),
        'Value': list(summary_stats.values())
    })
    
    # Get only breakout days with their forward returns
    signals = df[df['Is_Breakout']].copy()
    
    # Drop rows where forward returns couldn't be calculated (e.g., at the end of the dataset)
    signals = signals.dropna(subset=['Forward_Returns'])
    
    # Create detailed signals DataFrame
    signals_df = pd.DataFrame({
        'Signal_Date': signals.index.date,  # Convert to date only
        'Entry_Price': signals['Close'].round(2),
        'Volume': signals['Volume'],
        'Volume_MA_20': signals['Volume_MA'].astype(int),  # Convert to integer
        'Volume_Ratio': signals['Volume_Ratio'].round(2).apply(lambda x: f"{x:.2f}x"),
        'Price_Change_Pct': signals['Price_Change_Pct'].apply(format_with_sign),
        'Forward_Return': signals['Forward_Returns'].apply(format_with_sign),
        'Exit_Date': pd.to_datetime(signals['Exit_Date']).dt.date,  # Convert to date only
        'Exit_Price': signals['Exit_Price'].round(2)
    })
    
    # Sort by date
    signals_df = signals_df.sort_index()
    
    return summary_df, signals_df

def generate_breakout_summary(df: pd.DataFrame) -> Dict:
    """
    Generate comprehensive summary statistics for breakout signals.
    
    Args:
        df: DataFrame with breakout signals and returns
    
    Returns:
        Dictionary with summary statistics. Returns zeros/empty values if no breakout trades.
    """
    breakout_data = df[df['Is_Breakout']].copy()
    
    # Drop any rows with NaN in critical columns
    breakout_data = breakout_data.dropna(subset=['Forward_Returns', 'Volume_Ratio', 'Price_Change_Pct'])
    
    # If no breakout trades or all were dropped, return zeros/empty values
    if len(breakout_data) == 0:
        return {
            'Total_Breakout_Days': '0',
            'Average_Return': '0.00%',
            'Win_Rate': '0.00%',
            'Best_Trade': '0.00%',
            'Worst_Trade': '0.00%',
            'Avg_Win_Size': '0.00%',
            'Avg_Loss_Size': '0.00%',
            'Avg_Days_Between_Signals': 'N/A',
            'Avg_Volume_Ratio': '0.00x',
            'Max_Volume_Ratio': '0.00x',
            'Min_Volume_Ratio': '0.00x',
            'Avg_Price_Change': '0.00%',
            'Max_Price_Change': '0.00%',
            'Min_Price_Change': '0.00%',
            'First_Signal_Date': None,
            'Last_Signal_Date': None
        }
    
    # Basic Statistics
    total_trades = len(breakout_data)
    winning_trades = breakout_data['Forward_Returns'] > 0
    losing_trades = breakout_data['Forward_Returns'] <= 0
    
    # Calculate consecutive signals
    breakout_data['Days_Between_Signals'] = breakout_data.index.to_series().diff().dt.days
    
    # Separate winning and losing trades
    winning_returns = breakout_data.loc[winning_trades, 'Forward_Returns']
    losing_returns = breakout_data.loc[losing_trades, 'Forward_Returns']
    
    # Volume Analysis
    volume_ratios = breakout_data['Volume_Ratio']
    
    # Helper function to safely calculate mean
    def safe_mean(series):
        return series.mean() if len(series) > 0 else 0.0
    
    summary = {
        # Basic Metrics
        'Total_Breakout_Days': str(total_trades),
        'Average_Return': format_with_sign(safe_mean(breakout_data['Forward_Returns'])),
        'Win_Rate': f"{(winning_trades.sum() / total_trades * 100):.2f}%",
        
        # Risk Metrics
        'Best_Trade': format_with_sign(breakout_data['Forward_Returns'].max()),
        'Worst_Trade': format_with_sign(breakout_data['Forward_Returns'].min()),
        
        # Trade Analysis
        'Avg_Win_Size': format_with_sign(safe_mean(winning_returns)),
        'Avg_Loss_Size': format_with_sign(safe_mean(losing_returns)),
        'Avg_Days_Between_Signals': str(int(safe_mean(breakout_data['Days_Between_Signals']))) if len(breakout_data) > 1 else 'N/A',
        
        # Volume Analysis
        'Avg_Volume_Ratio': f"{safe_mean(volume_ratios):.2f}x",
        'Max_Volume_Ratio': f"{volume_ratios.max():.2f}x",
        'Min_Volume_Ratio': f"{volume_ratios.min():.2f}x",
        
        # Price Analysis
        'Avg_Price_Change': format_with_sign(safe_mean(breakout_data['Price_Change_Pct'])),
        'Max_Price_Change': format_with_sign(breakout_data['Price_Change_Pct'].max()),
        'Min_Price_Change': format_with_sign(breakout_data['Price_Change_Pct'].min()),
        
        # First and Last Signal
        'First_Signal_Date': str(breakout_data.index.min().date()) if len(breakout_data) > 0 else None,
        'Last_Signal_Date': str(breakout_data.index.max().date()) if len(breakout_data) > 0 else None
    }
    
    return summary 