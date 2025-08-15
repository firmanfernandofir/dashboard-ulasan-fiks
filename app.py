import pandas as pd
import re
from datetime import datetime, timedelta
from dash import Dash, html, dcc, dash_table, Input, Output
import plotly.graph_objs as go
import os

# === STEP 1: Load & Parse Dataset ===
# Ambil langsung dari GitHub raw link
DATA_URL = "https://raw.githubusercontent.com/firmanfernandofir/dashboard-ulasan-fiks/main/data.csv"
df = pd.read_csv(DATA_URL)

def parse_date_flexible(text):
    """Parse tanggal absolut & relatif bahasa Indonesia"""
    text = str(text).strip().lower()
    today = datetime.today()

    dt = pd.to_datetime(text, errors="coerce", dayfirst=False)
    if pd.notna(dt):
        return dt

    try:
        if "sebulan" in text:
            return today - timedelta(days=30)
        elif "bulan" in text:
            match = re.search(r"(\d+)\s+bulan", text)
            if match:
                return today - timedelta(days=30 * int(match.group(1)))
        elif "setahun" in text:
            return today - timedelta(days=365)
        elif "tahun" in text:
            match = re.search(r"(\d+)\s+tahun", text)
            if match:
                return today - timedelta(days=365 * int(match.group(1)))
        elif "minggu" in text:
            match = re.search(r"(\d+)\s+minggu", text)
            if match:
                return today - timedelta(weeks=int(match.group(1)))
        elif "hari" in text:
            match = re.search(r"(\d+)\s+hari", text)
            if match:
                return today - timedelta(days=int(match.group(1)))
    except:
        return None
    return None

df["parsed_date"] = df["date"].apply(parse_date_flexible)
df = df.dropna(subset=["parsed_date"])

df["year"] = df["parsed_date"].dt.year
df["month"] = df["parsed_date"].dt.month
df["week"] = df["parsed_date"].dt.to_period("W").apply(lambda r: r.start_time)

if "link" not in df.columns:
    df["link"] = "https://google.com"
else:
    df["link"] = df["link"].fillna("https://google.com")
    df.loc[df["link"].astype(str).str.strip() == "", "link"] = "https://google.com"

# === STEP 2: Build Dash App ===
app = Dash(__name__)
server = app.server  # untuk Railway
app.title = "Dashboard Ulasan PDAM Sidoarjo"

app.layout = html.Div([
    html.H2("📊 Dashboard Ulasan PDAM Sidoarjo", style={"textAlign": "center"}),

    html.Div([
        html.Label("Pilih Tahun:"),
        dcc.Dropdown(
            id="filter-year",
            options=[{"label": str(y), "value": y} for y in sorted(df["year"].unique())],
            value=None,
            placeholder="Semua Tahun",
            clearable=True
        ),
        html.Label("Pilih Bulan:"),
        dcc.Dropdown(
            id="filter-month",
            options=[{"label": f"{m:02d}", "value": m} for m in range(1, 13)],
            value=None,
            placeholder="Semua Bulan",
            clearable=True
        )
    ], style={"width": "40%", "display": "inline-block", "verticalAlign": "top"}),

    dcc.Graph(id="grafik-tahunan"),
    dcc.Graph(id="grafik-bulanan"),
    dcc.Graph(id="grafik-mingguan"),

    html.H3("📄 Daftar Ulasan + Link Sumber"),
    dash_table.DataTable(
        id="tabel-ulasan",
        columns=[
            {"name": "Tanggal", "id": "parsed_date"},
            {"name": "Ulasan", "id": "snippet"},
            {"name": "Link", "id": "link", "presentation": "markdown"},
        ],
        style_cell={'textAlign': 'left', 'whiteSpace': 'normal', 'height': 'auto'},
        style_table={'overflowX': 'auto', 'maxHeight': '600px', 'overflowY': 'scroll'},
        markdown_options={"html": True},
        page_size=10,
    )
])

@app.callback(
    [Output("grafik-tahunan", "figure"),
     Output("grafik-bulanan", "figure"),
     Output("grafik-mingguan", "figure"),
     Output("tabel-ulasan", "data")],
    [Input("filter-year", "value"),
     Input("filter-month", "value")]
)
def update_dashboard(selected_year, selected_month):
    dff = df.copy()
    if selected_year:
        dff = dff[dff["year"] == selected_year]
    if selected_month:
        dff = dff[dff["month"] == selected_month]

    yearly_summary = dff.groupby("year").agg(jumlah_ulasan=("snippet", "count")).reset_index()
    fig_year = go.Figure([go.Bar(
        x=yearly_summary["year"], y=yearly_summary["jumlah_ulasan"],
        text=yearly_summary["jumlah_ulasan"], textposition="outside"
    )])
    fig_year.update_layout(title="Jumlah Ulasan per Tahun", template="plotly_white")

    monthly_summary = dff.groupby("month").agg(jumlah_ulasan=("snippet", "count")).reset_index()
    fig_month = go.Figure([go.Bar(
        x=monthly_summary["month"], y=monthly_summary["jumlah_ulasan"],
        text=monthly_summary["jumlah_ulasan"], textposition="outside"
    )])
    fig_month.update_layout(title="Jumlah Ulasan per Bulan", template="plotly_white")

    weekly_summary = dff.groupby("week").agg(jumlah_ulasan=("snippet", "count")).reset_index()
    fig_week = go.Figure([go.Bar(
        x=weekly_summary["week"], y=weekly_summary["jumlah_ulasan"],
        text=weekly_summary["jumlah_ulasan"], textposition="outside"
    )])
    fig_week.update_layout(title="Jumlah Ulasan per Minggu", template="plotly_white")

    tabel_data = [
        {
            "parsed_date": row["parsed_date"].strftime("%Y-%m-%d"),
            "snippet": row["snippet"],
            "link": f"[Klik Link]({row['link']})"
        }
        for _, row in dff.sort_values("parsed_date", ascending=False).iterrows()
    ]

    return fig_year, fig_month, fig_week, tabel_data

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=False, host="0.0.0.0", port=port)
