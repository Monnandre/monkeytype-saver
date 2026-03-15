import json
import os
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output
from backend import run_fetch_cycle, SAVE_FILE

# --- THEME CONFIG ---
BACKGROUND_COLOR = "#1c1c1c"
TEXT_COLOR = "#d7af87"
PRIMARY_ACCENT = "#3f3c32"
SECONDARY_ACCENT = "#525045"
PB_COLOR = "#d75f00"

app = dash.Dash(__name__, update_title=None)

# Global variables for caching to prevent redundant disk reads
_CACHED_DF = None
_LAST_MTIME = 0

def get_optimized_data():
    """Loads data from disk only if the file has changed."""
    global _CACHED_DF, _LAST_MTIME
    
    if not os.path.exists(SAVE_FILE):
        return pd.DataFrame()

    current_mtime = os.path.getmtime(SAVE_FILE)
    if _CACHED_DF is not None and current_mtime == _LAST_MTIME:
        return _CACHED_DF

    try:
        with open(SAVE_FILE, "r") as f:
            df = pd.DataFrame(json.load(f))
        
        if df.empty: return df

        # Vectorized calculations (Fast)
        df["date"] = pd.to_datetime(df["timestamp"], unit='ms').dt.strftime('%Y-%m-%d %H:%M')
        df["avg_10"] = df["wpm"].rolling(window=10, min_periods=1).mean()
        df["avg_100"] = df["wpm"].rolling(window=100, min_periods=1).mean()
        df["pb"] = df["wpm"].cummax()
        df["index"] = range(1, len(df) + 1)

        _CACHED_DF = df
        _LAST_MTIME = current_mtime
        return df
    except Exception as e:
        print(f"Error processing data: {e}")
        return pd.DataFrame()

def create_main_figure():
    df = get_optimized_data()
    if df.empty:
        return go.Figure().update_layout(title="No data found...", paper_bgcolor=BACKGROUND_COLOR, font_color=TEXT_COLOR)

    fig = go.Figure()

    # RAW DATA (Scattergl is critical for 5000+ points)
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

# --- LAYOUT ---
app.layout = html.Div(style={
    'backgroundColor': BACKGROUND_COLOR, 'color': TEXT_COLOR,
    'height': '100vh', 'width': '100vw', 'display': 'flex', 
    'flexDirection': 'column', 'overflow': 'hidden'
}, children=[
    # Header Area
    html.Div([
        html.H2('Monkeytype Stats', style={'margin': '0', 'padding': '10px 20px', 'display': 'inline-block'}),
        dcc.Loading(id="loading", type="circle", children=html.Div(id="update-status", style={'display': 'inline-block', 'fontSize': '12px'}))
    ], style={'flexShrink': 0, 'borderBottom': f'1px solid {PRIMARY_ACCENT}'}),

    # Main Graph Area
    dcc.Graph(
        id='main-graph',
        figure=create_main_figure(),
        style={'flexGrow': 1},
        config={'displayModeBar': False}
    ),

    # This triggers the fetch as soon as the page loads
    dcc.Interval(id='init-fetch', interval=1, max_intervals=1)
])

# --- CALLBACKS ---
@app.callback(
    [Output('main-graph', 'figure'),
     Output('update-status', 'children')],
    Input('init-fetch', 'n_intervals')
)
def on_page_load(n):
    # 1. Fetch from API
    new_data_found = run_fetch_cycle()
    
    # 2. Return the updated figure and a status message
    status = "Data updated" if new_data_found else "Data up to date"
    return create_figure_with_fresh_data(), status

def create_figure_with_fresh_data():
    # Force a refresh of the figure
    return create_main_figure()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)