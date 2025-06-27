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
    # 1. Initialize an empty DataFrame at the very beginning.
    # This guarantees 'df' always exists, solving the UnboundLocalError.
    df = pd.DataFrame()

    # 2. Try to load and process the data.
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # If data was loaded and is not empty, create the full DataFrame.
        # This will overwrite the empty one we created above.
        if data:
            df = pd.DataFrame([{
                "wpm": entry["wpm"],
                "acc": entry["acc"],
                "timestamp": entry["timestamp"],
                "language": entry.get("language", "N/A")
            } for entry in data])
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is invalid, do nothing.
        # 'df' will remain the empty DataFrame we initialized earlier.
        pass

    # 3. Now, we can safely check if the DataFrame is empty.
    # This single check handles all cases: file not found, bad JSON, or empty file.
    if df.empty:
        return go.Figure().update_layout(
            title="No data found. Run the data fetcher script!",
            plot_bgcolor=BACKGROUND_COLOR,
            paper_bgcolor=BACKGROUND_COLOR,
            font=dict(color=TEXT_COLOR),
        )

    # If we get here, it means we have data, so proceed with calculations.
    df["date"] = pd.to_datetime(df["timestamp"], unit='ms').dt.strftime('%Y-%m-%d')
    df["index"] = df.index
    df["avg_10"] = df["wpm"].rolling(window=10, min_periods=1).mean()
    df["avg_100"] = df["wpm"].rolling(window=100, min_periods=1).mean()
    df["pb"] = df["wpm"].cummax()

    # Create the figure
    fig = go.Figure()

    # Add traces... (the rest of the function remains the same)
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

    # Configure the layout
    fig.update_layout(
        title=f"Typing Speed Over Time (Data from {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')})",
        plot_bgcolor=BACKGROUND_COLOR, paper_bgcolor=BACKGROUND_COLOR,
        font=dict(color=TEXT_COLOR),
        xaxis_title="Test Number", yaxis_title="Words Per Minute (WPM)",
        legend=dict(bgcolor=BACKGROUND_COLOR, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig
# --- APP INITIALIZATION AND LAYOUT ---

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server # Expose the server variable for Gunicorn

# Define the app layout. The figure is generated once and passed directly.
app.layout = html.Div(style={
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
    # The graph is created by calling our function. No callback is needed.
    dcc.Graph(
        id='main-graph',
        figure=create_main_figure(),
        style={'flexGrow': 1, 'minHeight': 0} # minHeight is a flexbox trick to prevent overflow
    )
    # The dcc.Interval and the @app.callback have been removed.
])


app.run(debug=False, host='0.0.0.0', port=8050)