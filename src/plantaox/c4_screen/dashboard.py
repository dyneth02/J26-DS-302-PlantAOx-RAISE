"""Build a compact MOCK-labelled summary and a self-contained offline dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def build_summary(funnel_path: str | Path, tiers: pd.DataFrame, candidates: pd.DataFrame,
                  cloud_meta: pd.DataFrame, ad_params: dict, signal_sources: dict,
                  output_path: str | Path | None = None) -> dict:
    funnel = pd.read_csv(funnel_path).to_dict("records")
    embedded = tiers[tiers.embedded.astype(bool)]
    plants = {}
    membership = candidates[["peptide_id"]].copy()
    if "plant" in tiers:
        membership = tiers[["peptide_id", "plant"]]
    for plant, rows in tiers.groupby("plant", sort=True) if "plant" in tiers else []:
        included = rows[rows.embedded.astype(bool)]
        plants[plant] = {"embedded": int(rows.embedded.sum()), "not_embedded": int((~rows.embedded).sum()),
            "tier_fractions": {str(int(t)): float((included.tier == t).mean()) for t in (1, 2, 3)} if len(included) else {"1":0,"2":0,"3":0}}
    lengths = candidates.sequence.str.len().value_counts().sort_index()
    distances = embedded.d_AD.dropna().to_numpy(dtype=float)
    bins, edges = np.histogram(distances, bins=30, range=(0, 2)) if len(distances) else (np.zeros(30, dtype=int), np.linspace(0, 2, 31))
    unique_tiers = tiers.drop_duplicates("peptide_id")
    result = {"status": "MOCK / PROVISIONAL", "cloud": {"source": "mock_cloud", "mock": True,
        "n_sequences": int(len(cloud_meta)), "description": "500 composition-biased synthetic sequences; seed 42"},
        "signal_sources": signal_sources, "funnel": funnel, "embedded_count": int(unique_tiers.embedded.sum()),
        "not_embedded_count": int((~unique_tiers.embedded).sum()), "tier_fractions_by_plant": plants,
        "length_distribution": {str(int(k)): int(v) for k, v in lengths.items()},
        "d_AD_histogram": {"bins": bins.astype(int).tolist(), "edges": edges.astype(float).tolist(),
                           "source": "mock_cloud"}, "ad_params": ad_params}
    if output_path is not None:
        path = Path(output_path); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def write_dashboard(summary: dict, cards: dict, output_path: str | Path) -> Path:
    payload = json.dumps({"summary": summary, "cards": cards}, separators=(",", ":"), allow_nan=False)
    page = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PlantAOP-Screen — MOCK demonstration</title><style>
body{font:15px system-ui;margin:0;background:#f4f7f6;color:#17332e}header{background:#7f1d1d;color:white;padding:14px 22px;font-weight:800;position:sticky;top:0}
main{max-width:1200px;margin:auto;padding:20px}.tabs button,select{padding:9px 14px;margin:4px;border:1px solid #9ab5aa;border-radius:8px;background:white;cursor:pointer}
.panel{display:none;background:white;padding:18px;border-radius:12px;margin-top:10px;box-shadow:0 2px 12px #1232}.panel.active{display:block}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}.card{background:#fff;border:1px solid #d4e1dc;border-left:6px solid #15803d;border-radius:9px;padding:12px}.amber{border-left-color:#d97706}.red{border-left-color:#b91c1c}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:8px;text-align:left}.badge{font-weight:bold}.small{color:#52635e;font-size:12px}#hist{display:flex;align-items:end;height:180px;gap:2px;position:relative}.bar{background:#457a69;flex:1}
</style></head><body><header>DEMO ONLY — DUMMY SIGNALS / MOCK CLOUD — NOT BIOLOGICAL RESULTS</header><main>
<h1>PlantAOP-Screen</h1><p id="notice"></p><nav class="tabs"><button onclick="show('pipeline')">Pipeline funnel</button><button onclick="show('ad')">Applicability domain</button><button onclick="show('cards')">Evidence cards</button></nav>
<section id="pipeline" class="panel active"><h2>Pipeline funnel</h2><table id="funnel"></table></section>
<section id="ad" class="panel"><h2>AD view — MOCK cloud</h2><p id="cloud"></p><label>Plant <select id="plantAd" onchange="drawAD()"></select></label><div id="hist"></div><table id="tiers"></table></section>
<section id="cards" class="panel"><h2>Evidence cards — mock inputs</h2><label>Plant <select id="plantCards" onchange="drawCards()"></select></label><label>Tier <select id="tierFilter" onchange="drawCards()"><option value="all">Tier 1 and 2</option><option value="1">Tier 1</option><option value="2">Tier 2</option></select></label><button onclick="toggleAbstain()">Show abstained</button><div id="cardGrid" class="grid"></div><p id="abstain"></p></section>
</main><script>const D=__PAYLOAD__;let abst=false;function show(id){document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===id))}
const plants=Object.keys(D.cards.plants);function options(id){document.getElementById(id).innerHTML=plants.map(p=>`<option>${p}</option>`).join('')}
document.getElementById('notice').textContent=D.cards.mock_notice;document.getElementById('cloud').textContent=`MOCK cloud: ${D.summary.cloud.n_sequences} synthetic sequences; source=${D.summary.cloud.source}; t1=${D.summary.ad_params.t1.toFixed(5)}, t2=${D.summary.ad_params.t2.toFixed(5)}.`;
options('plantAd');options('plantCards');let f=D.summary.funnel;document.getElementById('funnel').innerHTML='<tr>'+Object.keys(f[0]).map(k=>`<th>${k}</th>`).join('')+'</tr>'+f.map(r=>'<tr>'+Object.values(r).map(v=>`<td>${v}</td>`).join('')+'</tr>').join('');
function drawAD(){let p=document.getElementById('plantAd').value,t=D.summary.tier_fractions_by_plant[p]||{};document.getElementById('tiers').innerHTML='<tr><th>Tier</th><th>Fraction</th></tr>'+Object.entries(t.tier_fractions||{}).map(([k,v])=>`<tr><td>${k}</td><td>${(100*v).toFixed(2)}%</td></tr>`).join('');let a=D.summary.d_AD_histogram.bins,m=Math.max(...a,1);document.getElementById('hist').innerHTML=a.map(v=>`<div class="bar" title="${v}" style="height:${Math.max(2,160*v/m)}px"></div>`).join('')+`<span title="t1=${D.summary.ad_params.t1}" style="position:absolute;left:${Math.min(98,D.summary.ad_params.t1/2*100)}%;height:180px;border-left:2px dashed orange"></span><span title="t2=${D.summary.ad_params.t2}" style="position:absolute;left:${Math.min(98,D.summary.ad_params.t2/2*100)}%;height:180px;border-left:2px dashed red"></span>`}
function drawCards(){let p=document.getElementById('plantCards').value,g=D.cards.plants[p],filter=document.getElementById('tierFilter').value;document.getElementById('cardGrid').innerHTML=g.top_50.filter(c=>filter==='all'||c.tier==filter).map(c=>`<article class="card ${c.tier===2?'amber':''}"><b>${c.flag} · Tier ${c.tier} · Rank ${c.rank}</b><h3>${c.sequence}</h3><div>CS ${c.CS.toFixed(3)} · d_AD ${c.d_AD.toFixed(3)} · BCS ${c.BCS??'NA'} (${c.BCS_flag??'NA'})</div><p>SIM_C1 ${c.SIM_C1.toFixed(3)} · PROB_C2 ${c.PROB_C2.toFixed(3)}</p><p class="small">${c.species}; ${c.provenance.length} parent records; sources MOCK${c.injected_demo_case?' · injected demonstration':''}</p></article>`).join('');document.getElementById('abstain').textContent=ab?`RED abstained: ${g.abstained.length} candidates (CS=0).`:''}
function toggleAbstain(){abst=!abst;let p=document.getElementById('plantCards').value,g=D.cards.plants[p];if(abst){document.getElementById('cardGrid').innerHTML=g.abstained.slice(0,500).map(c=>`<article class="card red"><b>RED · Tier 3 · CS 0</b><h3>${c.sequence}</h3><p class="small">${c.plant} · ${c.injected_demo_case?'injected demo':''}</p></article>`).join('');document.getElementById('abstain').textContent=`Showing up to 500 of ${g.abstained.length} abstained candidates.`}else drawCards()}
drawAD();drawCards();</script></body></html>'''.replace("__PAYLOAD__", payload)
    path = Path(output_path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8", newline="\n")
    return path
