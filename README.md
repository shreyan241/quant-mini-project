# Volume Breakout Strategy Scanner

A Streamlit-based web application that helps identify and analyze volume breakout patterns in stocks. The tool scans for instances where both volume and price action show significant increases, potentially indicating strong directional moves.

Hosted at: [Volume Breakout Scanner](https://quant-mini-project.streamlit.app/)

## Project Overview

This project implements a volume breakout strategy scanner based on the [problem statement](https://docs.google.com/document/d/1sYQE5kW0TocdvVvC69kWsbwT-HyVkwveTrXsG4Tk91w/edit?tab=t.0). The scanner helps identify potential trading opportunities by analyzing volume and price patterns.

### Features

1. **Stock Selection**
   - Search and select from all US-listed stocks
   - Company information and sector display
   - Real-time validation of ticker symbols

2. **Strategy Parameters**
   - Volume Breakout Threshold: Minimum ratio of current volume to 20-day moving average
   - Price Change Threshold: Minimum daily price change percentage
   - Holding Period: Number of trading days to hold position

3. **Analysis Components**
   - Interactive price and volume charts
   - Detailed breakout signals report
   - Strategy performance summary
   - Downloadable CSV reports

4. **Date Range Selection**
   - Flexible date range selection
   - Trading calendar awareness
   - Validation for sufficient data availability

### Strategy Details

The strategy identifies breakout signals based on two main criteria:
1. Volume spike above the moving average (configurable threshold)
2. Price increase above a minimum threshold

For each identified signal, the scanner:
- Calculates forward returns over the holding period
- Tracks win rate and average returns
- Analyzes volume patterns
- Provides detailed entry and exit points

## Setup Instructions

1. **Create Python Environment**
   ```bash
   conda create -n quant python=3.11
   conda activate quant
   ```

2. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd quant-mini-project
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Application**
   ```bash
   streamlit run src/app.py
   ```

The application will be available at `http://localhost:8501`

## Project Structure

```
quant-mini-project/
├── src/
│   ├── analysis/         # Analysis and metrics calculation
│   ├── data/            # Data handling and storage
│   ├── visualization/   # Charts and plotting functions
│   └── app.py          # Main Streamlit application
├── requirements.txt    # Project dependencies
└── README.md          # Project documentation
```

## Dashboard Components

1. **Charts Tab**
   - Price candlestick chart
   - Volume bars with moving average
   - Breakout signals visualization

2. **Signals Tab**
   - Detailed breakout signals table
   - Entry and exit prices
   - Volume ratios and returns
   - CSV export functionality

3. **Summary Tab**
   - Strategy performance metrics
   - Win rate and return statistics
   - Volume analysis
   - Trading frequency metrics

## Deployment

The application is deployed on Streamlit Cloud and automatically updates with new commits to the main branch. Visit the [live application](https://quant-mini-project.streamlit.app/) to try it out.
