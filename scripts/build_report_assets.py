#!/usr/bin/env python3
"""Generate report figures and tables from frozen catalog and validation artifacts."""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "manuscripts/inverse-earth-studio-report-0.04.003"
FIG = REPORT / "figures"
GEN = REPORT / "generated"
CAT = ROOT / "data/derived/v2/catalog.json"
PHASE = ROOT / "data/derived/phase/stead-heldout-benchmark.json"
BS = ROOT / "manuscripts/geometry-normalized-traveltime-refinement-v001/generated/analysis.json"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8,"axes.titlesize":10,
 "axes.labelsize":8,"legend.fontsize":7,"pdf.fonttype":42,"axes.spines.top":False,
 "axes.spines.right":False,"figure.facecolor":"white","axes.facecolor":"white"})
C={"l2":"#315a7d","irls":"#d17a32","mt-lm":"#315a7d","mt-adam":"#d17a32",
 "mt-neural":"#618c65","fwi-l2":"#315a7d","fwi-multiscale":"#d17a32",
 "joint-uncoupled":"#586b7a","joint":"#287a74","pgi":"#c15c52",
 "cnn":"#315a7d","autoencoder":"#9b6b9b"}
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def fam(cat, name): return [c for c in cat["cases"] if c["family"]==name]
def ref(c, v="reference"): return next(x for x in c["variants"] if x["id"]==v)
def met(c, m, k, v="reference"): return ref(c,v)["methods"][m]["metrics"].get(k)
def outfig(f, name):
 f.tight_layout(); f.savefig(FIG/name,format="pdf",bbox_inches="tight",metadata={"Creator":"build_report_assets.py"}); plt.close(f)
def num(v, n=4): return "--" if v is None else f"{float(v):.{n}g}"
def esc(s):
 return str(s).replace("&",r"\&").replace("%",r"\%").replace("_",r"\_").replace("#",r"\#")
def tab(caption,label,headers,rows):
 spec="l"+"r"*(len(headers)-1)
 lines=[r"\begin{table}[!ht]",r"\centering",r"\small",r"\caption{"+caption+"}",r"\label{"+label+"}",
        r"\resizebox{\linewidth}{!}{%",r"\begin{tabular}{"+spec+"}",r"\toprule"," & ".join(headers)+r" \\",r"\midrule"]
 lines += [" & ".join(esc(x) for x in row)+r" \\" for row in rows]
 lines += [r"\bottomrule",r"\end{tabular}","}",r"\end{table}",""]
 return "\n".join(lines)
def main():
 FIG.mkdir(parents=True,exist_ok=True); GEN.mkdir(parents=True,exist_ok=True)
 cat,phase,bs=load(CAT),load(PHASE),load(BS)
 if cat.get("schema")!="inverse-earth.catalog/v2" or not cat.get("complete"): raise SystemExit("incomplete catalog")
 grav=fam(cat,"gravity"); mts=fam(cat,"mt"); fwi=fam(cat,"seismic"); joint=fam(cat,"joint"); learned=fam(cat,"learned")

 # Gravity model correlation versus recovered centroid-depth error.
 fig,ax=plt.subplots(figsize=(7,3.8))
 for m in ("l2","irls"):
  xs=[met(c,m,"correlation") for c in grav]; ys=[met(c,m,"centroid_error_m") for c in grav]
  ax.scatter(xs,ys,s=42,color=C[m],label=m.upper(),edgecolor="white",linewidth=.5)
  if m=="l2":
   for c,x,y in zip(grav,xs,ys): ax.annotate(c["id"].replace("GRAVITY_",""),(x,y),xytext=(4,4),textcoords="offset points",fontsize=6)
 ax.set(xlabel="Model correlation (dimensionless)",ylabel="Centroid-depth error (m)",title="Gravity reference cases: fit and geometry recovery are distinct")
 ax.legend(frameon=False); ax.grid(alpha=.2); outfig(fig,"report-gravity-correlation-depth.pdf")
 # Single-case perturbation sensitivity.
 stock=next(c for c in grav if c["id"]=="GRAVITY_INTRUSION"); variants=stock["variants"]; x=np.arange(len(variants))
 fig,ax=plt.subplots(figsize=(7,3.6))
 for m,marker,ls in (("l2","o","-"),("irls","s","--")):
  ax.plot(x,[met(stock,m,"model_rmse",v["id"]) for v in variants],marker=marker,ls=ls,ms=4,label=m.upper(),color=C[m])
 ax.set_xticks(x,[v["id"].replace("_"," ") for v in variants],rotation=25,ha="right")
 ax.set(ylabel="Density-contrast RMSE (g cm$^{-3}$)",title="Offset stock: fixed constructor with one named perturbation per variant")
 ax.legend(frameon=False); ax.grid(axis="y",alpha=.2); outfig(fig,"report-gravity-variant-sensitivity.pdf")
 # MT active/held-out fit.
 fig,ax=plt.subplots(figsize=(7.1,4))
 marks={"mt-lm":"o","mt-adam":"s","mt-neural":"^"}
 for m in marks:
  for i,c in enumerate(mts):
   a=met(c,m,"active_component_wrms"); h=met(c,m,"log_model_rmse")
   if a is None or h is None: continue
   ax.scatter(a,h,marker=marks[m],s=42,color=C[m],edgecolor="white",linewidth=.4,label=m if i==0 else None)
   ax.annotate(c["id"].replace("MT_",""),(a,h),xytext=(3,3),textcoords="offset points",fontsize=6)
 lim=max(ax.get_xlim()[1],1.5); ax.axvline(1.5,color="#a7463c",lw=.7,ls=":")
 ax.set(xlabel="Active complex-component WRMS (σ units)",ylabel="log-resistivity model RMSE (log10 Ω m)",
        title="Layered MT solver comparison: data fit and model recovery")
 ax.legend(frameon=False,ncol=3); ax.grid(alpha=.18); outfig(fig,"report-mt-active-withheld-wrms.pdf")
 # FWI data/model metrics.
 fig,ax=plt.subplots(figsize=(8,4.1)); xx=[]; active=[]; held=[]; labels=[]
 for c in fwi:
  for m in ("fwi-l2","fwi-multiscale"):
   q=ref(c)["methods"][m]["metrics"]; xx.append(len(xx)); active.append(q["active_wrms"]); held.append(q["withheld_wrms"])
   labels.append(c["id"].replace("FWI_","")+"\n"+m.replace("fwi-",""))
 xx=np.arange(len(xx)); w=.36
 ax.bar(xx-w/2,active,w,label="active receivers",color="#7397ad",edgecolor="#263238",hatch="//")
 ax.bar(xx+w/2,held,w,label="withheld receivers",color="#d89a54",edgecolor="#263238",hatch="..")
 ax.axhline(2,color="#a7463c",ls="--",lw=1,label="2σ criterion")
 ax.set_xticks(xx,labels,fontsize=6); ax.set_ylabel("Waveform WRMS (declared noise units)")
 ax.set_title("FWI reference cases and negative controls"); ax.legend(frameon=False,ncol=3); ax.grid(axis="y",alpha=.18)
 outfig(fig,"report-fwi-active-withheld.pdf")
 # Joint structural coupling against optimized independent baseline; show the small delta around zero.
 fig,ax=plt.subplots(figsize=(7,3.8)); xx=np.arange(len(joint)); w=.23
 for j,(m,hatch) in enumerate(zip(("joint-uncoupled","joint","pgi"),("//","xx",".."))):
  ax.bar(xx+(j-1)*w,[met(c,m,"independent_baseline_ratio")-1 for c in joint],w,label=m,color=C[m],edgecolor="#263238",hatch=hatch)
 ax.axhline(0,color="#333",lw=.8,ls="--"); ax.set_xticks(xx,[c["id"].replace("JOINT_","") for c in joint])
 ax.set(ylabel="Change in density RMSE ratio vs uncoupled",title="Coupling effect under compatible and conflicting structure")
 ax.legend(frameon=False,ncol=3); ax.grid(axis="y",alpha=.18); outfig(fig,"report-joint-coupling-controls.pdf")
 # Learned depth-integrated target against same-observation classical estimate.
 fig,ax=plt.subplots(figsize=(7,3.6)); xx=np.arange(len(learned)); w=.34
 colors={"l2":"#7f8c95","cnn":"#315a7d"}
 for j,(m,hatch) in enumerate(zip(("l2","cnn"),("//",".."))):
  ax.bar(xx+(j-.5)*w,[met(c,m,"column_rmse") for c in learned],w,label=m.upper(),color=colors[m],edgecolor="#263238",hatch=hatch)
 ax.set_xticks(xx,[c["id"].replace("LEARNED_","") for c in learned])
 ax.set(ylabel="Column-density RMSE (catalog units)",title="Learned gravity target against the matched L2 baseline")
 ax.legend(frameon=False); ax.grid(axis="y",alpha=.18); outfig(fig,"report-learned-column-baseline.pdf")
 # Held-out phase-picker F1 under fixed perturbations.
 conds=("nominal","drop_E","drop_N","drop_Z","noise_0p1","shift_plus_800"); xx=np.arange(len(conds)); w=.24
 fig,ax=plt.subplots(figsize=(7.2,4))
 for j,(m,hatch) in enumerate(zip(("M00","M08","M13"),("//","xx",".."))):
  vals=[phase["metrics"][c][m]["P"]["f1_at_0p5s"] for c in conds]
  ax.bar(xx+(j-1)*w,vals,w,label=m,color={"M00":"#8f989f","M08":"#d17a32","M13":"#315a7d"}[m],edgecolor="#263238",hatch=hatch)
 ax.set_xticks(xx,[c.replace("_"," ") for c in conds],rotation=22,ha="right"); ax.set_ylim(0,1.05)
 ax.set(ylabel="P-phase F1 within ±0.5 s",title="Frozen STEAD held-out benchmark under channel and signal shifts")
 ax.legend(frameon=False,ncol=3); ax.grid(axis="y",alpha=.18); outfig(fig,"report-phase-picker-perturbations.pdf")
 # Catalog verdicts by family, with unresolved and negative-control rows retained.
 counts={}
 for family in sorted({c["family"] for c in cat["cases"]}):
  counts[family]={"recovered":0,"unresolved":0,"negative-control":0}
  for c in fam(cat,family):
   for v in c["variants"]:
    for m in v["methods"].values():
     s=m.get("evaluation",{}).get("status","unresolved"); counts[family][s]=counts[family].get(s,0)+1
 fig,ax=plt.subplots(figsize=(7.2,3.8)); families=list(counts); bottom=np.zeros(len(families))
 for s,color,hatch in (("recovered","#4f8a66","//"),("unresolved","#d39a45","xx"),("negative-control","#a94e48","..")):
  vals=np.array([counts[f].get(s,0) for f in families]); ax.bar(families,vals,bottom=bottom,label=s,color=color,edgecolor="#263238",hatch=hatch,linewidth=.35)
  for i,v in enumerate(vals):
   if v: ax.text(i,bottom[i]+v/2,str(int(v)),ha="center",va="center",fontsize=7,color="white")
  bottom+=vals
 ax.set(ylabel="Method × variant verdict records",title="Catalog status by family (not a pooled accuracy score)")
 ax.legend(frameon=False,ncol=3); ax.grid(axis="y",alpha=.18); outfig(fig,"report-catalog-verdict-counts.pdf")
 # Geometry-normalized proposed-method preregistered failure.
 primary=bs["primary"]; keys=("id_test","family_only","acquisition_only","joint_ood"); x=np.arange(len(keys))
 fig,ax=plt.subplots(figsize=(7,3.8))
 for j,(q,color,marker,ls) in enumerate((("velocity","#315a7d","o","-"),("travel_time","#d17a32","s","--"))):
  vals=np.array([primary[k][q]["ratio"] for k in keys]); ci=np.array([primary[k][q]["ci95"] for k in keys])
  ax.errorbar(x+(j-.5)*.32,vals,yerr=np.vstack((vals-ci[:,0],ci[:,1]-vals)),fmt=marker+ls,capsize=3,color=color,label=q.replace("_"," "))
 ax.axhline(1,color="#333",lw=.8,ls="--",label="pass boundary")
 ax.set_xticks(x,["in-distribution","family shift","acquisition shift","joint shift"])
 ax.set(ylabel="Candidate / baseline error ratio",title="Geometry-normalized refinement: bootstrap 95% intervals, 20,000 resamples")
 ax.legend(frameon=False,ncol=3); ax.grid(axis="y",alpha=.18); outfig(fig,"report-refinement-negative-result.pdf")

 # Data-derived booktabs tables: one per result family plus benchmark and proposed-method receipts.
 blocks=[]
 inventory=[]
 for family in sorted({c["family"] for c in cat["cases"]}):
  cs=fam(cat,family); inventory.append((family,len(cs),sum(len(c["variants"]) for c in cs),
     len({m for c in cs for v in c["variants"] for m in v["methods"]})))
 blocks.append(tab("Committed experiment coverage by physical family, including case, variant, and method-key counts for this frozen release artifact.","tab:generated-family-inventory",
  ["Family","Cases","Variants","Method keys"],inventory))
 rows=[]
 for c in grav:
  for m in ("l2","irls"): rows.append((c["id"],m,num(met(c,m,"wrms")),num(met(c,m,"correlation")),num(met(c,m,"baseline_ratio")),num(met(c,m,"centroid_error_m"),5)))
 blocks.append(tab("Gravity reference recovery reports data fit and geometric error separately for every case and solver.","tab:generated-gravity",
  ["Case","Method","WRMS","Correlation","RMSE ratio","Depth error (m)"],rows))
 rows=[]
 for c in mts:
  for m in ("mt-lm","mt-adam","mt-neural"):
   q=ref(c)["methods"][m]
   rows.append((c["id"],m,num(met(c,m,"active_component_wrms")),num(met(c,m,"initial_component_wrms"),5),
    num(met(c,m,"log_model_rmse"),5),q["evaluation"]["status"]))
 blocks.append(tab("Layered MT reference results report active fit, initial-model error, and the explicit solver verdict on each synthetic sounding.","tab:generated-mt",
  ["Case","Solver","Active WRMS","Initial WRMS","log-rho RMSE","Status"],rows))
 rows=[]
 for c in fwi:
  for m in ("fwi-l2","fwi-multiscale"):
   q=ref(c)["methods"][m]; z=q["metrics"]
   rows.append((c["id"],m,num(z.get("model_rmse_ratio")),num(z.get("active_wrms")),num(z.get("withheld_wrms")),q["evaluation"]["status"]))
 blocks.append(tab("Acoustic FWI reference cases preserve active fit, held-out fit, model ratios, and unresolved outcomes for each frozen model.","tab:generated-fwi",
  ["Case","Schedule","Model ratio","Active WRMS","Withheld WRMS","Status"],rows))
 rows=[]
 for c in joint:
  for m in ("joint-uncoupled","joint","pgi"):
   q=ref(c)["methods"][m]; z=q["metrics"]
   rows.append((c["id"],m,num(z.get("independent_baseline_ratio")),num(z.get("independent_magnetic_baseline_ratio")),
    num(z.get("wrms")),num(z.get("magnetic_wrms")),q["evaluation"]["status"]))
 blocks.append(tab("Joint priors are compared with optimized uncoupled estimates while both physical residuals remain visible for each structure.","tab:generated-joint",
  ["Case","Method","Density ratio","Magnetic ratio","Gravity WRMS","Magnetic WRMS","Status"],rows))
 rows=[]
 for c in learned:
  for m in ("l2","cnn","autoencoder"):
   q=ref(c)["methods"].get(m)
   if q:
    z=q["metrics"]; rows.append((c["id"],m,num(z.get("column_rmse")),num(z.get("classical_column_rmse")),
     num(z.get("classical_baseline_ratio")),str(z.get("above_threshold","--")),q["evaluation"]["status"]))
 blocks.append(tab("Learned gravity outputs compare column targets with classical estimates; flags are not calibrated geological classifications.","tab:generated-learned",
  ["Case","Method","Column RMSE","Classical RMSE","Ratio","AE flag","Status"],rows))
 rows=[]
 for cond in conds:
  for m in ("M00","M08","M13"):
   for ph in ("P","S"):
    z=phase["metrics"][cond][m][ph]
    rows.append((cond,m,ph,num(z["precision_at_0p5s"],3),num(z["recall_at_0p5s"],3),
     num(z["f1_at_0p5s"],3),num(z["timing_absolute_median_s"],3)))
 blocks.append(tab("Frozen STEAD held-out phase scores use analyst annotations, a fixed half-second arrival tolerance, and named signal perturbations.","tab:generated-phase",
  ["Condition","Model","Phase","Precision","Recall","F1","Median abs. error (s)"],rows))
 rows=[]
 for k in keys:
  z=primary[k]; v=z["velocity"]; t=z["travel_time"]
  rows.append((k.replace("_"," "),str(v["n"]),num(v["ratio"]),f"[{num(v['ci95'][0])}, {num(v['ci95'][1])}]",
   num(t["ratio"]),f"[{num(t['ci95'][0])}, {num(t['ci95'][1])}]",str(z["flags"])))
 blocks.append(tab("Preregistered refinement cohorts report candidate-to-baseline error ratios and bootstrap intervals; values above one favor the baseline.","tab:generated-refinement",
  ["Shift cohort","n","Velocity ratio",r"95\% CI","Time ratio",r"95\% CI","Flags"],rows))
 (GEN/"tables.tex").write_text("\n".join(blocks),encoding="utf-8")
 print(f"Built 9 vector figures and {len(blocks)} data-derived result tables from catalog {cat['version']}.")
if __name__=="__main__": main()
