import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Optional

def format_volume(volume):
    """Format volume with K/M/B suffixes"""
    if volume >= 1e9:
        return f"{volume/1e9:.1f}B"
    elif volume >= 1e6:
        return f"{volume/1e6:.1f}M"
    elif volume >= 1e3:
        return f"{volume/1e3:.1f}K"
    return f"{volume:.0f}"

def create_stock_chart(df: pd.DataFrame, title: str = "") -> go.Figure:
    """
    Create an interactive stock chart with price and volume.
    Highlights breakout points and includes volume bars.
    
    Args:
        df: DataFrame with OHLCV data and breakout signals
        title: Chart title
        
    Returns:
        Plotly figure object
    """
    # Handle multi-index columns if present
    if isinstance(df.columns, pd.MultiIndex):
        ohlc_cols = {
            'Open': ('Price', 'Open'),
            'High': ('Price', 'High'),
            'Low': ('Price', 'Low'),
            'Close': ('Price', 'Close'),
            'Volume': ('Price', 'Volume')
        }
    else:
        ohlc_cols = {
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume'
        }

    # Calculate daily percentage change
    daily_change = ((df[ohlc_cols['Close']] - df[ohlc_cols['Open']]) / df[ohlc_cols['Open']] * 100)
    
    # Calculate percentage change from first day
    first_price = df[ohlc_cols['Close']].iloc[0]
    pct_change = ((df[ohlc_cols['Close']] - first_price) / first_price * 100)

    # Create figure with secondary y-axis
    fig = make_subplots(rows=2, cols=1, 
                       shared_xaxes=True,
                       vertical_spacing=0.03,
                       subplot_titles=('Price', 'Volume'),
                       row_heights=[0.7, 0.3])

    # Add candlestick with custom colors
    fig.add_trace(
        go.Candlestick(x=df.index,
                      open=df[ohlc_cols['Open']],
                      high=df[ohlc_cols['High']],
                      low=df[ohlc_cols['Low']],
                      close=df[ohlc_cols['Close']],
                      name='OHLC',
                      increasing_line_color='#26A69A',  # Green
                      decreasing_line_color='#EF5350',  # Red
                      text=[f"Date: {d.strftime('%Y-%m-%d')}<br>" +
                           f"Open: ${o:.2f}<br>" +
                           f"High: ${h:.2f}<br>" +
                           f"Low: ${l:.2f}<br>" +
                           f"Close: ${c:.2f}<br>" +
                           f"Change: {chg:+.2f}%<br>" +
                           f"From Start: {tot:+.2f}%"
                           for d, o, h, l, c, chg, tot in zip(df.index,
                                                            df[ohlc_cols['Open']], 
                                                            df[ohlc_cols['High']], 
                                                            df[ohlc_cols['Low']], 
                                                            df[ohlc_cols['Close']],
                                                            daily_change,
                                                            pct_change)],
                      hoverinfo='text'),
        row=1, col=1
    )

    # Add volume bars with matching colors
    colors = ['#EF5350' if close <= open else '#26A69A' 
              for close, open in zip(df[ohlc_cols['Close']], df[ohlc_cols['Open']])]
    fig.add_trace(
        go.Bar(x=df.index, 
               y=df[ohlc_cols['Volume']],
               name='Volume',
               marker_color=colors,
               marker_line_width=0,
               opacity=0.7,
               hovertemplate=
               "Date: %{x}<br>" +
               "Volume: " + df[ohlc_cols['Volume']].apply(format_volume) + "<br>" +
               "<extra></extra>"),
        row=2, col=1
    )

    # Add volume MA with updated color
    volume_ma_col = 'Volume_MA' if 'Volume_MA' in df.columns else ('Price', 'Volume_MA')
    fig.add_trace(
        go.Scatter(x=df.index,
                  y=df[volume_ma_col],
                  name='20D Volume MA',
                  line=dict(color='#B2DFDB', width=2),
                  hovertemplate=
                  "Date: %{x}<br>" +
                  "20D Avg Volume: " + df[volume_ma_col].apply(format_volume) + "<br>" +
                  "<extra></extra>"),
        row=2, col=1
    )

    # Highlight breakout points with updated colors
    breakouts = df[df['Is_Breakout']]
    if len(breakouts) > 0:
        # Pre-format the values for hover text
        formatted_data = np.column_stack((
            breakouts['Volume_Ratio'].round(2),
            breakouts['Forward_Returns'].round(2),
            breakouts['Price_Change_Pct'].round(2)
        ))
        
        fig.add_trace(
            go.Scatter(x=breakouts.index,
                      y=breakouts[ohlc_cols['Close']],
                      mode='markers',
                      name='Breakout Signals',
                      marker=dict(
                          color='#FFD700',  # Gold
                          size=breakouts['Volume_Ratio'] * 4,  # Size based on volume spike
                          symbol='triangle-up',
                          line=dict(color='#212121', width=2),
                          opacity=1.0  # Ensure full opacity
                      ),
                      hovertemplate=
                      "<b>Breakout Signal</b><br>" +
                      "Date: %{x}<br>" +
                      "Price: $%{y:.2f}<br>" +
                      "Volume Spike: %{customdata[0]:.2f}x<br>" +
                      "Price Change: %{customdata[2]:+.2f}%<br>" +
                      "Forward Return: %{customdata[1]:+.2f}%<br>" +
                      "<extra></extra>",
                      customdata=formatted_data),
            row=1, col=1
        )

    # Update layout with improved styling
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor='center',
            font=dict(size=24, color='#000000')
        ),
        yaxis_title='Price',
        yaxis2_title='Volume',
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='#000000',
            font=dict(size=12, color='#000000')
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="ALL")
                ]),
                bgcolor='#FFFFFF',
                activecolor='#B2DFDB',
                font=dict(size=12, color='#000000')
            ),
            gridcolor='rgba(0, 0, 0, 0.2)',
            gridwidth=1,
            griddash='dot',
            tickfont=dict(size=12, color='#000000'),
            zeroline=False
        ),
        xaxis2=dict(
            gridcolor='rgba(0, 0, 0, 0.2)',
            gridwidth=1,
            griddash='dot',
            tickfont=dict(size=12, color='#000000'),
            zeroline=False
        ),
        paper_bgcolor='white',
        plot_bgcolor='white',
        hovermode='x unified',
        font=dict(family="Arial, sans-serif", color='#000000')
    )
    
    # Update axes styling
    fig.update_yaxes(
        title_text="Price ($)", 
        row=1, col=1,
        gridcolor='rgba(0, 0, 0, 0.2)',
        gridwidth=1,
        griddash='dot',
        zeroline=False,
        tickformat='$,.2f',
        tickfont=dict(size=12, color='#000000'),
        title_font=dict(size=14, color='#000000')
    )
    fig.update_yaxes(
        title_text="Volume", 
        row=2, col=1,
        gridcolor='rgba(0, 0, 0, 0.2)',
        gridwidth=1,
        griddash='dot',
        zeroline=False,
        tickfont=dict(size=12, color='#000000'),
        title_font=dict(size=14, color='#000000')
    )

    return fig
