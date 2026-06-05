import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="PSX Golden Cross Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 PSX Golden Cross & Moving Average Dashboard")
st.markdown("Track 50-Day and 200-Day Moving Averages for **Pakistan Stock Exchange (PSX)** companies.")

# --- SIDEBAR INTERFACE ---
st.sidebar.header("Configuration")

st.sidebar.info(
    "Enter the standard symbol. The app handles the system backend extensions automatically.\n\n"
    "**Popular Examples:**\n"
    "- `SYS` (Systems Limited)\n"
    "- `HUBC` (Hub Power Company)\n"
    "- `EFERT` (Engro Fertilizers)\n"
    "- `OGDC` (OGDCL)\n"
    "- `^KSE100` (Market Benchmark)"
)

ticker_input = st.sidebar.text_input("Enter PSX Stock Ticker:", value="SYS").strip().upper()

# Date Selection (3 years back to ensure plenty of historical data for a 200-day MA)
end_date = datetime.today()
start_date = end_date - timedelta(days=3*365)

# --- DATA FETCHING & CALCULATION ---
@st.cache_data(ttl=3600)
def load_data(symbol_raw, start, end):
    if symbol_raw.startswith("^"):
        symbols_to_try = [symbol_raw]
    else:
        symbols_to_try = [f"{symbol_raw}.PSX", f"{symbol_raw}.KA"]
        
    adjusted_start = start - timedelta(days=250)
    
    for symbol in symbols_to_try:
        try:
            df = yf.download(symbol, start=adjusted_start, end=end, progress=False)
            if df is not None and not df.empty and len(df) > 200:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                # Compute Moving Averages
                df['50_MA'] = df['Close'].rolling(window=50).mean()
                df['200_MA'] = df['Close'].rolling(window=200).mean()
                
                df = df[df.index >= pd.to_datetime(start)]
                return df, symbol
        except Exception:
            continue
    return None, None

if ticker_input:
    with st.spinner(f"Scanning market data for '{ticker_input}'..."):
        data, active_symbol = load_data(ticker_input, start_date, end_date)
        
    if data is not None and len(data) > 0:
        
        # --- GOLDEN CROSS CALCULATION ---
        latest_data = data.tail(2)
        status_message = "No fresh technical crossover detected today."
        status_color = "info"
        
        if len(latest_data) == 2:
            prev_50, prev_200 = latest_data['50_MA'].iloc[0], latest_data['200_MA'].iloc[0]
            curr_50, curr_200 = latest_data['50_MA'].iloc[1], latest_data['200_MA'].iloc[1]
            
            if prev_50 <= prev_200 and curr_50 > curr_200:
                status_message = f"🚀 GOLDEN CROSS DETECTED on {ticker_input}! (Major Long-Term Bullish Breakout)"
                status_color = "success"
            elif prev_50 >= prev_200 and curr_50 < curr_200:
                status_message = f"⚠️ DEATH CROSS DETECTED on {ticker_input}! (Major Long-Term Bearish Breakdown)"
                status_color = "error"
            else:
                if curr_50 > curr_200:
                    status_message = f"Bullish Structure: 50-Day MA is holding above the 200-Day MA."
                    status_color = "success"
                else:
                    status_message = f"Bearish Structure: 50-Day MA is currently tracking below the 200-Day MA."
                    status_color = "warning"

        # Signal Status Alert Layout
        if status_color == "success": st.success(status_message)
        elif status_color == "warning": st.warning(status_message)
        elif status_color == "error": st.error(status_message)
        else: st.info(status_message)

        # --- METRICS DISPLAY ---
        col1, col2, col3 = st.columns(3)
        latest_close = float(data['Close'].iloc[-1])
        latest_50 = float(data['50_MA'].iloc[-1])
        latest_200 = float(data['200_MA'].iloc[-1])
        
        col1.metric("Latest Close Price", f"Rs. {latest_close:,.2f}")
        col2.metric("50-Day MA", f"Rs. {latest_50:,.2f}")
        col3.metric("200-Day MA", f"Rs. {latest_200:,.2f}")

        # --- INTERACTIVE PLOTLY GRAPH ---
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=data.index, y=data['Close'], 
            mode='lines', name='Close Price', 
            line=dict(color='#A6AEBF', width=1.5)
        ))

        fig.add_trace(go.Scatter(
            x=data.index, y=data['50_MA'], 
            mode='lines', name='50-Day MA', 
            line=dict(color='#FF4B4B', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=data.index, y=data['200_MA'], 
            mode='lines', name='200-Day MA', 
            line=dict(color='#0068C9', width=2)
        ))

        fig.update_layout(
            title=f"{ticker_input} Analysis ({active_symbol})",
            xaxis_title="Date",
            yaxis_title="Price (PKR)",
            hovermode="x unified",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=60, b=10),
            height=500,
            
            # MOBILE LOCK DOWN PROPERTIES BELOW:
            dragmode=False,  # Completely blocks touch-drag box selections
            xaxis=dict(
                fixedrange=True  # Locks horizontal axes completely against pinch zooms
            ),
            yaxis=dict(
                fixedrange=True, # Locks vertical axes completely against pinch zooms
                tickformat=".2f" # Forces standard currency display with no raw decimals
            )
        )

        # Hides the upper menu toolbar buttons which cause layout issues on mobile screens
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with st.expander("Show Historic Raw Data"):
            st.dataframe(data[['Close', '50_MA', '200_MA']].tail(30).sort_index(ascending=False), use_container_width=True)
            
    else:
        st.error(f"Could not retrieve data for symbol '{ticker_input}'. Make sure the ticker is typed correctly without any suffix.")
