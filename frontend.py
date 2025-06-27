import json
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html

# --- CONFIGURATION ---
SAVE_FILE = "monkeytype_results.json"

# Plotly theme colors (Alduin-inspired)
BACKGROUND_COLOR = "#1c1c1c"
TEXT_COLOR = "#d7af87"
PRIMARY_ACCENT = "#3f3c32"
SECONDARY_ACCENT = "#525045"
PB_COLOR = "#d75f00"


def create_main_figure():
    """
    Loads data and creates the Plotly figure.
    This function is called once when the app starts.
    """
    df = pd.DataFrame()

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data:
            df = pd.DataFrame([{
                "wpm": entry["wpm"],
                "acc": entry["acc"],
                "timestamp": entry["timestamp"],
                "language": entry.get("language", "N/A")
            } for entry in data])
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if df.empty:
        return go.Figure().update_layout(
            title="No data found. Run the data fetcher script!",
            plot_bgcolor=BACKGROUND_COLOR,
            paper_bgcolor=BACKGROUND_COLOR,
            font=dict(color=TEXT_COLOR),
        )

    df["date"] = pd.to_datetime(df["timestamp"], unit='ms').dt.strftime('%Y-%m-%d')
    df["index"] = df.index
    df["avg_10"] = df["wpm"].rolling(window=10, min_periods=1).mean()
    df["avg_100"] = df["wpm"].rolling(window=100, min_periods=1).mean()
    df["pb"] = df["wpm"].cummax()

    fig = go.Figure()

    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["wpm"], mode='markers', name="Speed",
        marker=dict(color=PRIMARY_ACCENT, size=6, opacity=0.5),
        customdata=df[['date', 'language']],
        hovertemplate="Test #%{x}<br>Date: %{customdata[0]}<br>Lang: %{customdata[1]}<br>WPM: %{y}<extra></extra>"
    ))
    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["avg_10"], mode='lines', name="Avg of 10",
        line=dict(color=SECONDARY_ACCENT, width=2),
        hovertemplate="Avg 10: %{y:.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["avg_100"], mode='lines', name="Avg of 100",
        line=dict(color=TEXT_COLOR, width=2),
        hovertemplate="Avg 100: %{y:.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scattergl(
        x=df["index"], y=df["pb"], mode='lines', name="Personal Best",
        line=dict(color=PB_COLOR, width=2, dash='dash'),
        hovertemplate="PB: %{y}<extra></extra>"
    ))

    fig.update_layout(
        title=f"Typing Speed Over Time (Data from {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')})",
        plot_bgcolor=BACKGROUND_COLOR, paper_bgcolor=BACKGROUND_COLOR,
        font=dict(color=TEXT_COLOR),
        xaxis_title="Test Number", yaxis_title="Words Per Minute (WPM)",
        legend=dict(bgcolor=BACKGROUND_COLOR, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

# Initialize the Dash app
app = dash.Dash(__name__)

def serve_layout():
    return html.Div(style={
        'backgroundColor': BACKGROUND_COLOR,
        'color': TEXT_COLOR,
        'height': '100vh',
        'display': 'flex',
        'flexDirection': 'column',
        'padding': '20px',
        'boxSizing': 'border-box'
    }, children=[
        html.H1(
            children='Monkeytype Stats',
            style={'textAlign': 'center', 'flexShrink': 0}
        ),
        dcc.Graph(
            id='main-graph',
            figure=create_main_figure(),
            style={'flexGrow': 1, 'minHeight': 0}
        )
    ])

# Assign the function to app.layout instead of the object itself.
app.layout = serve_layout
app.run(debug=False, host='0.0.0.0', port=8050)
