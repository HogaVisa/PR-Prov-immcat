"""
ircc_dashboard_pr_by_country.py
--------------------------------
Generates a self-contained interactive HTML dashboard from the cleaned IRCC
PR by Country long-format CSV. Country selection happens in the browser —
all 217 countries are embedded in the HTML and charts update dynamically.

Usage:
    python ircc_dashboard_pr_by_country.py <long_clean_csv> [--countries "A,B,C"] [--output_dir ./outputs]

Examples:
    python ircc_dashboard_pr_by_country.py pr_citz_long_clean.csv
    python ircc_dashboard_pr_by_country.py pr_citz_long_clean.csv --countries "Hong Kong SAR,Vietnam" --output_dir ./outputs

Options:
    --countries     Comma-separated list of countries shown on load (max 5, default: HK SAR, China PRC, Vietnam)
    --output_dir    Where to save pr_dashboard.html (default: same folder as input CSV)

Output:
    pr_dashboard.html — single self-contained interactive HTML file, open in any browser
"""

import sys
import os
import argparse
import json
import numpy as np
import pandas as pd


MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
MAX_COUNTRIES = 5

DEFAULT_COUNTRIES = [
    "Hong Kong SAR",
    "China, People's Republic of",
    "Vietnam",
]


def load(path):
    df = pd.read_csv(path, parse_dates=["Date"])
    df["Month"] = pd.Categorical(df["Month"], categories=MONTHS, ordered=True)
    return df


def detect_partial_year(df):
    current = df["Year"].max()
    return int(current) if df[df["Year"] == current]["Month"].nunique() < 12 else None


def safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def build_payload(df, exclude_yr):
    all_countries = sorted(df["Country"].unique().tolist())
    sub = df[df["Year"] < exclude_yr].copy() if exclude_yr else df.copy()

    total_by_year = {}
    for yr, grp in sub.groupby("Year"):
        v = safe(grp["Admissions"].sum(min_count=1))
        total_by_year[int(yr)] = v

    payload = {}
    for country in all_countries:
        csub = sub[sub["Country"] == country]

        # Annual
        annual = {}
        for yr, grp in csub.groupby("Year"):
            annual[int(yr)] = safe(grp["Admissions"].sum(min_count=1))

        # YoY
        yoy = {}
        yrs = sorted(annual.keys())
        for i, yr in enumerate(yrs):
            prev = annual.get(yrs[i-1]) if i > 0 else None
            curr = annual.get(yr)
            if i == 0 or not prev or not curr:
                yoy[yr] = None
            else:
                yoy[yr] = round((curr - prev) / prev * 100, 1)

        # Seasonality — explicit month-by-month groupby to avoid Categorical issues
        season = {}
        month_grp = csub.groupby(csub["Month"].astype(str))["Admissions"].mean()
        for m in MONTHS:
            v = safe(month_grp.get(m))
            season[m] = round(v, 1) if v is not None else None

        # Share of total
        share = {}
        for yr, ann in annual.items():
            tot = total_by_year.get(yr)
            share[yr] = round(ann / tot * 100, 2) if ann and tot else None

        payload[country] = {
            "annual": annual,
            "yoy":    yoy,
            "season": season,
            "share":  share,
        }

    return payload, all_countries


def validate_defaults(defaults, available):
    if len(defaults) > MAX_COUNTRIES:
        print(f"  Warning: default list trimmed to {MAX_COUNTRIES}.")
        defaults = defaults[:MAX_COUNTRIES]
    missing = [c for c in defaults if c not in available]
    if missing:
        print(f"  Warning — not found in dataset: {missing}. Check COUNTRIES.md.")
    return [c for c in defaults if c in available]


def build_html(payload, all_countries, defaults, exclude_yr, source_date):
    payload_json   = json.dumps(payload, ensure_ascii=False)
    countries_json = json.dumps(all_countries, ensure_ascii=False)
    defaults_json  = json.dumps(defaults, ensure_ascii=False)
    months_json    = json.dumps(MONTHS)
    note = (f"Partial year ({exclude_yr}) excluded from all aggregations. " if exclude_yr else "") + \
           f"Suppressed IRCC values (&lt;5) treated as NaN. Source: IRCC, {source_date}."
    palette_json = json.dumps(["#1D9E75","#7F77DD","#D85A30","#378ADD","#EF9F27"])

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>IRCC PR by Country — Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box}
body{margin:0;padding:20px 28px;font-family:Arial,sans-serif;font-size:13px;background:#f5f5f5;color:#333}
h1{font-size:16px;font-weight:600;margin:0 0 2px}
.subtitle{font-size:11px;color:#999;margin:0 0 16px}
.layout{display:flex;gap:20px;align-items:flex-start}
.sidebar{width:230px;flex-shrink:0;background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:14px;position:sticky;top:20px}
.sidebar h2{font-size:12px;font-weight:600;margin:0 0 6px;color:#555}
.limit-note{font-size:11px;color:#aaa;margin:0 0 8px;line-height:1.4}
.search{width:100%;padding:6px 8px;font-size:12px;border:1px solid #ddd;border-radius:5px;margin-bottom:8px;outline:none}
.search:focus{border-color:#1D9E75}
.clist{max-height:440px;overflow-y:auto;border:1px solid #eee;border-radius:5px}
.ci{display:flex;align-items:flex-start;gap:7px;padding:6px 8px;cursor:pointer;border-bottom:1px solid #f5f5f5;transition:background .1s}
.ci:last-child{border-bottom:none}
.ci:hover{background:#f9f9f9}
.ci.selected{background:#f0faf5}
.ci.disabled{opacity:.4;pointer-events:none}
.ci input[type=checkbox]{margin-top:2px;flex-shrink:0;accent-color:#1D9E75;cursor:pointer}
.ci .swatch{width:10px;height:10px;border-radius:2px;flex-shrink:0;margin-top:3px}
.ci .cname{font-size:12px;line-height:1.4;word-break:break-word}
.main{flex:1;min-width:0}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:12px 14px;min-width:145px;flex:1}
.card-lbl{font-size:11px;font-weight:600;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-val{font-size:22px;font-weight:700}
.card-sub{font-size:11px;color:#888;margin-top:2px}
.card-yoy{font-size:11px;margin-top:2px}
.up{color:#1a7a4a}.down{color:#c0392b}
.chart-wrap{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:12px;margin-bottom:14px}
.chart-title{font-size:12px;font-weight:600;color:#555;margin-bottom:6px}
.footer{font-size:10px;color:#aaa;margin-top:8px}
.empty{padding:40px;text-align:center;color:#aaa;font-size:13px}
</style>
</head>
<body>
<h1>Canada — Permanent Residents by Country of Citizenship</h1>
<p class="subtitle">Source: IRCC open data &nbsp;·&nbsp; ircc_dashboard_pr_by_country.py</p>
<div class="layout">
  <div class="sidebar">
    <h2>Select countries</h2>
    <p class="limit-note">Up to """ + str(MAX_COUNTRIES) + """ countries. Charts update instantly.</p>
    <input class="search" type="text" id="search" placeholder="Search..." oninput="filterList()">
    <div class="clist" id="clist"></div>
  </div>
  <div class="main">
    <div class="cards" id="cards"></div>
    <div class="chart-wrap"><div class="chart-title">Annual PR admissions</div>
      <div id="cAnnual" style="height:260px"></div></div>
    <div class="chart-wrap"><div class="chart-title">Year-over-year change (%)</div>
      <div id="cYoY" style="height:220px"></div></div>
    <div class="chart-wrap"><div class="chart-title">Average admissions by month (seasonality)</div>
      <div id="cSeason" style="height:220px"></div></div>
    <div class="chart-wrap"><div class="chart-title">Share of total Canadian PR admissions (%)</div>
      <div id="cShare" style="height:220px"></div></div>
    <p class="footer">""" + note + """</p>
  </div>
</div>
<script>
const DATA    = """ + payload_json + """;
const ALL     = """ + countries_json + """;
const MONTHS  = """ + months_json + """;
const PALETTE = """ + palette_json + """;
const DASH    = ['solid','dash','dot','dashdot','longdash'];
const MAX     = """ + str(MAX_COUNTRIES) + """;

let selected = """ + defaults_json + """.filter(c => ALL.includes(c));

const GRID = 'rgba(200,200,200,0.3)';
const TICK = '#888';
const BASE_LAYOUT = {
  margin:{l:55,r:20,t:10,b:40},
  paper_bgcolor:'white', plot_bgcolor:'white',
  font:{family:'Arial,sans-serif',size:11,color:'#555'},
  legend:{orientation:'h',y:1.14,x:0},
  xaxis:{showgrid:true,gridcolor:GRID,tickfont:{color:TICK}},
  yaxis:{showgrid:true,gridcolor:GRID,tickfont:{color:TICK}},
};
const CFG = {responsive:true, displayModeBar:false};

function years(c)   { return Object.keys(DATA[c].annual).map(Number).sort((a,b)=>a-b); }
function annuals(c) { return years(c).map(y => DATA[c].annual[y]); }
function yoys(c)    { return years(c).map(y => DATA[c].yoy[y]); }
function seasons(c) { return MONTHS.map(m => DATA[c].season[m]); }
function shares(c)  { return years(c).map(y => DATA[c].share[y]); }

function sanitizeId(s) { return s.replace(/[^a-zA-Z0-9]/g,'_'); }

function buildList() {
  var q   = document.getElementById('search').value.toLowerCase();
  var div = document.getElementById('clist');
  div.innerHTML = '';
  ALL.filter(function(c){ return c.toLowerCase().indexOf(q) !== -1; }).forEach(function(c) {
    var isSel = selected.indexOf(c) !== -1;
    var isDis = !isSel && selected.length >= MAX;
    var idx   = selected.indexOf(c);
    var colour = isSel ? PALETTE[idx] : '#ccc';
    var item = document.createElement('div');
    item.className = 'ci' + (isSel?' selected':'') + (isDis?' disabled':'');

    var swatch = document.createElement('div');
    swatch.className = 'swatch';
    swatch.style.background = colour;

    var chk = document.createElement('input');
    chk.type = 'checkbox';
    chk.id = 'chk_' + sanitizeId(c);
    if (isSel) chk.checked = true;
    if (isDis) chk.disabled = true;

    var lbl = document.createElement('label');
    lbl.htmlFor = 'chk_' + sanitizeId(c);
    lbl.className = 'cname';
    lbl.title = c;
    lbl.textContent = c;

    item.appendChild(swatch);
    item.appendChild(chk);
    item.appendChild(lbl);

    if (!isDis) {
      item.addEventListener('click', function(e) {
        if (e.target === chk) return;
        toggleCountry(c);
      });
      chk.addEventListener('change', function() { toggleCountry(c); });
    }
    div.appendChild(item);
  });
}

function filterList() { buildList(); }

function toggleCountry(c) {
  var idx = selected.indexOf(c);
  if (idx !== -1) {
    selected.splice(idx, 1);
  } else if (selected.length < MAX) {
    selected.push(c);
  }
  buildList();
  render();
}

function renderCards() {
  var el = document.getElementById('cards');
  el.innerHTML = '';
  selected.forEach(function(c, i) {
    var ann  = DATA[c].annual;
    var yoy  = DATA[c].yoy;
    var yrs  = Object.keys(ann).map(Number).sort(function(a,b){return a-b;});
    var last = yrs[yrs.length - 1];
    var val  = ann[last];
    var yoyV = yoy[last];
    var peak = yrs.reduce(function(a,b){ return (ann[a]||0)>(ann[b]||0)?a:b; });
    var colour = PALETTE[i];

    var card = document.createElement('div');
    card.className = 'card';

    var lbl = document.createElement('div');
    lbl.className = 'card-lbl';
    lbl.style.color = colour;
    lbl.title = c;
    lbl.textContent = c;
    card.appendChild(lbl);

    var valEl = document.createElement('div');
    valEl.className = 'card-val';
    valEl.textContent = val != null ? Number(val).toLocaleString() : '\u2014';
    card.appendChild(valEl);

    var sub1 = document.createElement('div');
    sub1.className = 'card-sub';
    sub1.textContent = last + ' admissions';
    card.appendChild(sub1);

    if (yoyV != null) {
      var yoyEl = document.createElement('div');
      yoyEl.className = 'card-yoy ' + (yoyV >= 0 ? 'up' : 'down');
      yoyEl.textContent = (yoyV >= 0 ? '\u25b2' : '\u25bc') + ' ' + Math.abs(yoyV).toFixed(1) + '% YoY';
      card.appendChild(yoyEl);
    }

    var hr = document.createElement('div');
    hr.className = 'card-sub';
    hr.style.cssText = 'margin-top:6px;border-top:1px solid #eee;padding-top:6px';
    hr.textContent = 'Peak: ' + (ann[peak] != null ? Number(ann[peak]).toLocaleString() : '\u2014') + ' (' + peak + ')';
    card.appendChild(hr);

    el.appendChild(card);
  });
}

function render() {
  var divIds = ['cAnnual','cYoY','cSeason','cShare'];
  if (selected.length === 0) {
    divIds.forEach(function(id) {
      document.getElementById(id).innerHTML = '<div class="empty">Select at least one country.</div>';
    });
    document.getElementById('cards').innerHTML = '';
    return;
  }

  renderCards();

  // Chart 1: Annual
  Plotly.newPlot('cAnnual',
    selected.map(function(c,i) {
      return {
        x: years(c), y: annuals(c), name: c,
        type: 'scatter', mode: 'lines+markers',
        line: {color:PALETTE[i], width:2, dash:DASH[i]},
        marker: {size:4},
        hovertemplate: '%{x}: %{y:,}<extra>' + c + '</extra>',
      };
    }),
    Object.assign({}, BASE_LAYOUT, {
      yaxis: Object.assign({}, BASE_LAYOUT.yaxis, {tickformat:','}),
    }), CFG);

  // Chart 2: YoY
  var yoyTraces = selected.map(function(c,i) {
    return {
      x: years(c), y: yoys(c), name: c,
      type: 'scatter', mode: 'lines+markers',
      line: {color:PALETTE[i], width:2, dash:DASH[i]},
      marker: {size:4}, connectgaps: false,
      hovertemplate: '%{x}: %{y:.1f}%<extra>' + c + '</extra>',
    };
  });
  yoyTraces.push({
    x: years(selected[0]), y: years(selected[0]).map(function(){return 0;}),
    mode:'lines', showlegend:false, hoverinfo:'skip',
    line:{color:'rgba(150,150,150,0.4)', width:1, dash:'dot'},
  });
  Plotly.newPlot('cYoY', yoyTraces,
    Object.assign({}, BASE_LAYOUT, {
      yaxis: Object.assign({}, BASE_LAYOUT.yaxis, {ticksuffix:'%'}),
    }), CFG);

  // Chart 3: Seasonality — scatter lines to avoid bar chart axis issues
  Plotly.newPlot('cSeason',
    selected.map(function(c,i) {
      return {
        x: MONTHS, y: seasons(c), name: c,
        type: 'scatter', mode: 'lines+markers',
        line: {color:PALETTE[i], width:2, dash:DASH[i]},
        marker: {size:5},
        hovertemplate: '%{x}: %{y:,}<extra>' + c + '</extra>',
      };
    }),
    Object.assign({}, BASE_LAYOUT, {
      xaxis: Object.assign({}, BASE_LAYOUT.xaxis, {type:'category'}),
      yaxis: Object.assign({}, BASE_LAYOUT.yaxis, {tickformat:','}),
    }), CFG);

  // Chart 4: Share
  Plotly.newPlot('cShare',
    selected.map(function(c,i) {
      return {
        x: years(c), y: shares(c), name: c,
        type: 'scatter', mode: 'lines+markers',
        line: {color:PALETTE[i], width:2, dash:DASH[i]},
        marker: {size:4},
        hovertemplate: '%{x}: %{y:.2f}%<extra>' + c + '</extra>',
      };
    }),
    Object.assign({}, BASE_LAYOUT, {
      yaxis: Object.assign({}, BASE_LAYOUT.yaxis, {ticksuffix:'%'}),
    }), CFG);
}

buildList();
render();
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--countries", default=None)
    parser.add_argument("--output_dir", default=None)
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.dirname(os.path.abspath(args.input_csv))
    os.makedirs(output_dir, exist_ok=True)

    defaults = (
        [c.strip() for c in args.countries.split(",")]
        if args.countries else DEFAULT_COUNTRIES
    )

    print(f"Loading:  {args.input_csv}")
    df = load(args.input_csv)

    exclude_yr = detect_partial_year(df)
    if exclude_yr:
        print(f"  Partial year detected ({exclude_yr}) — excluded from aggregations.")

    all_countries = sorted(df["Country"].unique().tolist())
    defaults = validate_defaults(defaults, all_countries)

    print("Building payload for all countries...")
    payload, all_countries = build_payload(df, exclude_yr)

    source_date = str(int(df["Year"].max()))
    html = build_html(payload, all_countries, defaults, exclude_yr, source_date)

    out_path = os.path.join(output_dir, "pr_dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Saved:    {out_path}")
    print("Done. Open pr_dashboard.html in any browser.")


if __name__ == "__main__":
    main()
