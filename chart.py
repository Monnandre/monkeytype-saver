import json
import os
import pandas as pd
import plotly.graph_objects as go
from backend import SAVE_FILE

# --- THEME CONFIG ---
BACKGROUND_COLOR = "#1c1c1c"
TEXT_COLOR = "#d7af87"
PRIMARY_ACCENT = "#3f3c32"
SECONDARY_ACCENT = "#525045"
PB_COLOR = "#d75f00"

def get_optimized_data():
    """Loads data from disk and processes it."""
    if not os.path.exists(SAVE_FILE):
        return pd.DataFrame()

    try:
        with open(SAVE_FILE, "r") as f:
            df = pd.DataFrame(json.load(f))

        if df.empty:
            return df

        # Vectorized calculations
        df["date"] = pd.to_datetime(df["timestamp"], unit='ms').dt.strftime('%Y-%m-%d %H:%M')
        df["avg_10"] = df["wpm"].rolling(window=10, min_periods=1).mean()
        df["avg_100"] = df["wpm"].rolling(window=100, min_periods=1).mean()
        df["pb"] = df["wpm"].cummax()
        df["index"] = range(1, len(df) + 1)

        return df
    except Exception as e:
        print(f"Error processing data: {e}")
        return pd.DataFrame()

def create_main_figure():
    """Creates the main Plotly figure."""
    df = get_optimized_data()
    if df.empty:
        return go.Figure().update_layout(
            title="No data found...",
            paper_bgcolor=BACKGROUND_COLOR,
            font_color=TEXT_COLOR
        )

    fig = go.Figure()

    # RAW DATA (Scattergl for performance with many points)
    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["wpm"], mode='markers', name="Speed",
        marker=dict(color=PRIMARY_ACCENT, size=5, opacity=0.4),
        customdata=df[['date', 'language', 'acc']],
        hovertemplate="Test #%{x}<br>Date: %{customdata[0]}<br>Lang: %{customdata[1]}<br>Acc: %{customdata[2]}%<br>WPM: %{y}<extra></extra>"
    ))

    # AVG 10
    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["avg_10"], mode='lines', name="Avg 10",
        line=dict(color=SECONDARY_ACCENT, width=1.5),
        hoverinfo="skip"
    ))

    # AVG 100
    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["avg_100"], mode='lines', name="Avg 100",
        line=dict(color=TEXT_COLOR, width=2),
        hovertemplate="Avg 100: %{y:.2f}<extra></extra>"
    ))

    # PB
    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["pb"], mode='lines', name="Personal Best",
        line=dict(color=PB_COLOR, width=2, dash='dash'),
        hovertemplate="PB: %{y}<extra></extra>"
    ))

    fig.update_layout(
        template="plotly_dark",
        title=f"Monkeytype Progression ({len(df)} tests)",
        margin=dict(l=50, r=20, t=60, b=50),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        font=dict(color=TEXT_COLOR),
        xaxis=dict(title="Test Number", gridcolor="#2a2a2a", showline=True),
        yaxis=dict(title="WPM", gridcolor="#2a2a2a", showline=True),
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig
