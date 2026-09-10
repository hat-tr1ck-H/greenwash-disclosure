# -*- coding: utf-8 -*-
"""Step 3: aggregate disclosure scores and produce figures (English output)."""
import csv, pathlib, collections, statistics, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
DPI = 170

# 单一行业归类: 关键词命中最多者胜, 保证每家只计一次
BIZ = {
    "Energy & Utilities": ["发电量","装机容量","上网电价","煤炭产量","售电量","电力销售"],
    "Steel & Materials":  ["粗钢","钢材","水泥","熟料","有色金属","冶炼"],
    "Chemicals":          ["化学品","树脂","聚氨酯","涂料","农药","化肥"],
    "Real Estate & Construction": ["房地产开发","竣工面积","建筑工程","施工面积","物业管理"],
    "Healthcare & Pharma":["药品","临床试验","医疗器械","制剂","原料药","疫苗"],
    "TMT & Electronics":  ["半导体","集成电路","软件","芯片","元器件","面板","通信"],
    "Consumer":           ["白酒","食品","服装","零售","家居","乳业","调味品"],
    "Financials":         ["不良贷款率","资本充足率","净息差","保费","证券经纪"],
}

def load():
    p = ROOT / "data/processed/industry.csv"
    if not p.exists():
        raise SystemExit("找不到 data/processed/industry.csv, 请依次运行 02b_extract_full.py 与 04_industry.py")
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    print(f"[data] industry.csv  ({len(rows)} firms)")
    for r in rows:
        for k in ("carbon_kw","action_kw","soft_kw","pages"):
            r[k] = int(r[k] or 0)
    return rows


def main():
    rows = load()
    n = len(rows)

    zero   = sum(1 for r in rows if r["carbon_kw"] == 0)
    nums   = [r for r in rows if r["carbon_num"]]
    softonly = [r for r in rows if r["soft_kw"] > 0 and r["carbon_kw"] == 0]
    med    = statistics.median(r["carbon_kw"] for r in rows)

    print(f"\n=== SAMPLE: {n} A-share annual reports ===\n")
    print("[1] Carbon disclosure")
    print(f"    zero carbon mentions : {zero} ({zero/n*100:.1f}%)")
    print(f"    any carbon mention   : {n-zero} ({(n-zero)/n*100:.1f}%)")
    print(f"    median / max         : {med:.0f} / {max(r['carbon_kw'] for r in rows)}")
    print(f"    reports with a NUMBER: {len(nums)} ({len(nums)/n*100:.1f}%)")
    print(f"\n[2] Rhetoric without data")
    print(f"    soft-only firms      : {len(softonly)} ({len(softonly)/n*100:.1f}%)")

    agg = collections.defaultdict(list)
    for r in rows: agg[r["sector"]].append(r)
    stats = []
    for ind, rs in agg.items():
        stats.append({"industry": ind, "n": len(rs),
                      "carbon": statistics.mean(x["carbon_kw"] for x in rs),
                      "soft":   statistics.mean(x["soft_kw"]   for x in rs),
                      "zero_pct": sum(1 for x in rs if x["carbon_kw"]==0)/len(rs)*100})
    stats.sort(key=lambda d: -d["carbon"])
    print(f"\n[3] Stratification by industry (single label per firm)")
    print(f"    {'Industry':<30}{'N':>4}{'Carbon':>9}{'Soft':>7}{'Zero%':>7}")
    for s in stats:
        print(f"    {s['industry']:<30}{s['n']:>4}{s['carbon']:>9.1f}{s['soft']:>7.1f}{s['zero_pct']:>6.0f}%")
    tot = sum(s["n"] for s in stats)
    print(f"    {'TOTAL':<30}{tot:>4}   (每家公司仅计一次)")

    # ---- Fig 1: 行业碳披露强度 ----
    ss = [s for s in stats if s["n"] >= 2]
    if ss:
        fig, ax = plt.subplots(figsize=(10.5, 5.6))
        names=[s["industry"] for s in ss][::-1]; vals=[s["carbon"] for s in ss][::-1]
        ns=[s["n"] for s in ss][::-1]
        colors=["#b03a2e" if v>=4 else "#e59866" if v>=1.5 else "#95a5a6" for v in vals]
        bars=ax.barh(names, vals, color=colors)
        for b,v,c in zip(bars, vals, ns):
            ax.text(v+max(vals)*0.02, b.get_y()+b.get_height()/2, f"{v:.1f}  (n={c})",
                    va="center", fontsize=9.5, color="#2c3e50")
        ax.set_xlabel("Mean count of hard carbon terms per annual report", fontsize=11)
        ax.set_title(f"Environmental disclosure is stratified by industry\n"
                     f"Carbon-related terms in {n} Chinese A-share annual reports (FY2025)",
                     fontsize=12.5, pad=13)
        ax.grid(axis="x", alpha=.25); ax.set_axisbelow(True)
        ax.set_xlim(0, max(vals)*1.28)
        plt.tight_layout(); plt.savefig(ROOT/"figures/fig1_industry.png", dpi=DPI, bbox_inches="tight"); plt.close()
        print("\n    saved figures/fig1_industry.png")

    # ---- Fig 2: soft vs hard scatter ----
    fig, ax = plt.subplots(figsize=(8.2, 6.2))
    xs=[r["carbon_kw"] for r in rows]; ys=[r["soft_kw"] for r in rows]
    ax.scatter(xs, ys, alpha=.5, s=28, c="#2471a3", edgecolors="white", linewidths=.5)
    lim=max(max(xs),max(ys))*1.06
    ax.plot([0,lim],[0,lim],"--",color="#b03a2e",lw=1.5,label="rhetoric = evidence")
    ax.fill_between([0,lim],[0,lim],[lim,lim], color="#b03a2e", alpha=.05)
    ax.set_xlabel("HARD disclosure  —  carbon terms: emissions, targets, intensity", fontsize=10.5)
    ax.set_ylabel("SOFT rhetoric  —  green / ecological / low-carbon language", fontsize=10.5)
    ax.set_title(f"Rhetoric vs evidence in annual reports\n"
                 f"Shaded region = more green language than carbon data  ({n} firms)", fontsize=12.5, pad=13)
    ax.legend(frameon=False, fontsize=10); ax.grid(alpha=.25); ax.set_axisbelow(True)
    plt.tight_layout(); plt.savefig(ROOT/"figures/fig2_gap.png", dpi=DPI, bbox_inches="tight"); plt.close()
    print("    saved figures/fig2_gap.png")

    # ---- Fig 3: coverage + zero-rate by industry ----
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    axes[0].pie([zero, n-zero], labels=[f"No carbon\nmention\n{zero} firms", f"Discloses\ncarbon\n{n-zero} firms"],
                autopct="%1.0f%%", startangle=90, colors=["#aeb6bf","#229954"],
                wedgeprops={"edgecolor":"white","linewidth":2.2}, textprops={"fontsize":11})
    axes[0].set_title(f"Carbon disclosure coverage\n(n={n})", fontsize=12)
    ss2=[s for s in stats if s["n"]>=2]
    axes[1].barh([s["industry"] for s in ss2][::-1], [s["zero_pct"] for s in ss2][::-1],
                 color="#d68910")
    axes[1].set_xlabel("% of firms with ZERO carbon disclosure", fontsize=10.5)
    axes[1].set_title("Silence rate by industry", fontsize=12)
    axes[1].grid(axis="x", alpha=.25); axes[1].set_axisbelow(True)
    plt.tight_layout(); plt.savefig(ROOT/"figures/fig3_coverage.png", dpi=DPI, bbox_inches="tight"); plt.close()
    print("    saved figures/fig3_coverage.png")

    summary={"n_companies":n,"zero_carbon":zero,"coverage_pct":round((n-zero)/n*100,1),
             "median_carbon":med,"with_hard_numbers":len(nums),"soft_only":len(softonly),
             "by_industry":[{"industry":s["industry"],"n":s["n"],"carbon_mean":round(s["carbon"],2),
                             "soft_mean":round(s["soft"],2),"zero_pct":round(s["zero_pct"],1)} for s in stats]}
    json.dump(summary, open(ROOT/"data/processed/summary.json","w",encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\n    saved data/processed/summary.json")

if __name__=="__main__":
    main()
