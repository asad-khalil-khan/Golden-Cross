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
st.markdown("Track 50-Day and 100-Day Moving Averages for **Pakistan Stock Exchange (PSX)** companies.")

# --- SIDEBAR INTERFACE ---
st.sidebar.header("Configuration")

# Standard instructions for PSX tickers
st.sidebar.info("Enter symbols without suffix. The app automatically appends '.KA'.\n\nExamples:\n- SYS (Systems Ltd)\n- HUBC (Hubco)\n- EFERT (Engro Fert)\n- OGDC (OGDCL)")

ticker_input = st.sidebar.text_input("Enter PSX Stock Ticker:", value="SYS").strip().upper()

# Handle standard benchmark indices vs equity components
if ticker_input.startswith("^"):
    ticker = ticker_input
else:
    ticker = f"{ticker_input}.KA"

# Date Selection (2 years back to compute 100-day MA properly)
end_date = datetime.today()
start_date = end_date - timedelta(days=2*365)

# --- DATA FETCHING & CALCULATION ---
@st.cache_data(ttl=3600)  # Cache for 1 hour to keep performance swift on deployment
def load_data(symbol, start, end):
    try:
        adjusted_start = start - timedelta(days=150)
        df = yf.download(symbol, start=adjusted_start, end=end)
        if df.empty:
            return None
        
        # Flattens MultiIndex columns from newer yfinance outputs
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Calculate Moving Averages
        df['50_MA'] = df['Close'].rolling(window=50).mean()
        df['100_MA'] = df['Close'].rolling(window=100).mean()
        
        # Filter back to user's main display window
        df = df[df.index >= pd.to_datetime(start)]
        return df
    except Exception as e:
        return None

if ticker_input:
    with st.spinner(f"Fetching data for {ticker}..."):
        data = load_data(ticker, start_date, end_date)
        
    if data is not None and len(data) > 0:
        
        # --- GOLDEN CROSS CALCULATION ---
        latest_data = data.tail(2)
        status_message = "No fresh crossover detected recently."
        status_color = "info"
        
        if len(latest_data) == 2:
            prev_50, prev_100 = latest_data['50_MA'].iloc[0], latest_data['100_MA'].iloc[0]
            curr_50, curr_100 = latest_data['50_MA'].iloc[1], latest_data['100_MA'].iloc[1]
            
            if prev_50 <= prev_100 and curr_50 > curr_100:
                status_message = f"🚀 GOLDEN CROSS DETECTED on {ticker_input}! (Bullish Signal)"
                status_color = "success"
            elif prev_50 >= prev_100 and curr_50 < curr_100:
                status_message = f"⚠️ DEATH CROSS DETECTED on {ticker_input}! (Bearish Signal)"
                status_color = "error"
            else:
                if curr_50 > curr_100:
                    status_message = "Bullish Outlook: 50-Day MA is currently holding above the 100-Day MA."
                    status_color = "success"
                else:
                    status_message = "Bearish Outlook: 50-Day MA is running below the 100-Day MA."
                    status_color = "warning"

        # Display Live Technical Alignment Alerts
        if status_color == "success": st.success(status_message)
        elif status_color == "warning": st.warning(status_message)
        elif status_color == "error": st.error(status_message)
        else: st.info(status_message)

        # --- METRICS GRID ---
        col1, col2, col3 = st.columns(3)
        latest_close = float(data['Close'].iloc[-1])
        latest_50 = float(data['50_MA'].iloc[-1])
        latest_100 = float(data['100_MA'].iloc[-1])
        
        col1.metric("Latest Close Price", f"Rs. {latest_close:,.2f}")
        col2.metric("50-Day MA", f"Rs. {latest_50:,.2f}")
        col3.metric("100-Day MA", f"Rs. {latest_100:,.2f}")

        # --- INTERACTIVE GRAPH ---
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
            x=data.index, y=data['100_MA'], 
            mode='lines', name='100-Day MA', 
            line=dict(color='#0068C9', width=2)
        ))

        fig.update_layout(
            title=f"{ticker_input} Price Performance (PKR)",
            xaxis_title="Date",
            yaxis_title="Price (PKR)",
            hovermode="x unified",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=60, b=20),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Show Historic Raw Data"):
            st.dataframe(data[['Close', '50_MA', '100_MA']].tail(30).sort_index(ascending=False), use_container_width=True)
            
    else:
        st.error(f"Could not retrieve data for symbol '{ticker_input}'. Make sure it is active on the Pakistan Stock Exchange.")
