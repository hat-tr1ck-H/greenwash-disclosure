# -*- coding: utf-8 -*-
"""Step 4: 补真实行业分类(东方财富官方行业 f127)"""
import requests, csv, pathlib, time, collections
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parent.parent
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9"}
HOSTS = ["https://push2delay.eastmoney.com", "https://push2.eastmoney.com"]
BIG = {
    "银行":"Financials","保险":"Financials","证券":"Financials","多元金融":"Financials",
    "电力":"Energy & Utilities","燃气":"Energy & Utilities","煤炭":"Energy & Utilities",
    "石油":"Energy & Utilities","能源金属":"Energy & Utilities","光伏":"Energy & Utilities",
    "风电":"Energy & Utilities","电池":"Energy & Utilities","电网":"Energy & Utilities",
    "钢铁":"Steel & Materials","水泥":"Steel & Materials","玻璃":"Steel & Materials",
    "有色":"Steel & Materials","金属":"Steel & Materials","建材":"Steel & Materials","冶":"Steel & Materials",
    "化学":"Chemicals","化工":"Chemicals","农药":"Chemicals","化肥":"Chemicals","塑料":"Chemicals",
    "橡胶":"Chemicals","化纤":"Chemicals","涂料":"Chemicals","油服":"Chemicals",
    "房地产":"Real Estate & Construction","房屋建设":"Real Estate & Construction",
    "工程建设":"Real Estate & Construction","建筑":"Real Estate & Construction",
    "装修":"Real Estate & Construction","物业":"Real Estate & Construction","基础建设":"Real Estate & Construction",
    "医药":"Healthcare & Pharma","医疗":"Healthcare & Pharma","生物制品":"Healthcare & Pharma",
    "中药":"Healthcare & Pharma","制药":"Healthcare & Pharma",
    "半导体":"TMT & Electronics","电子":"TMT & Electronics","软件":"TMT & Electronics",
    "通信":"TMT & Electronics","计算机":"TMT & Electronics","光学":"TMT & Electronics",
    "元件":"TMT & Electronics","互联网":"TMT & Electronics","IT服务":"TMT & Electronics",
    "游戏":"TMT & Electronics","影视":"TMT & Electronics","出版":"TMT & Electronics",
    "食品":"Consumer","饮料":"Consumer","白酒":"Consumer","服装":"Consumer","纺织":"Consumer",
    "零售":"Consumer","商业":"Consumer","家居":"Consumer","家电":"Consumer","汽车":"Consumer",
    "旅游":"Consumer","教育":"Consumer","酒店":"Consumer","饰品":"Consumer",
    "机械":"Industrials","专用设备":"Industrials","通用设备":"Industrials","自动化":"Industrials",
    "航空":"Industrials","军工":"Industrials","船舶":"Industrials","电气":"Industrials",
    "农业":"Agriculture","牧":"Agriculture","渔":"Agriculture","种植":"Agriculture","林业":"Agriculture",
}
def big(ind):
    for k, v in BIG.items():
        if k in ind: return v
    return "Other"

def fetch(code, tries=4):
    secid = ("1." if code[0] == "6" else "0.") + code
    for i in range(tries):
        host = HOSTS[min(i, len(HOSTS)-1)]
        try:
            r = requests.get(host + "/api/qt/stock/get",
                params={"secid": secid, "fltt": 2, "invt": 2, "fields": "f57,f58,f127"},
                headers=H, timeout=15)
            if not r.text.strip():
                time.sleep(1.0 + i); continue
            d = r.json().get("data") or {}
            ind = (d.get("f127") or "").strip()
            if ind and ind != "-":
                return {"industry": ind, "sector": big(ind)}
            time.sleep(0.6 + i)
        except Exception:
            time.sleep(1.0 + i)
    return {"industry": "", "sector": "Other"}

def main():
    src = list(csv.DictReader(open(ROOT/"data/processed/disclosure_full.csv", encoding="utf-8-sig")))
    print(f"查询 {len(src)} 家公司行业 (低并发+重试)...")
    out, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(fetch, r["code"]): r for r in src}
        for i, f in enumerate(as_completed(futs), 1):
            r = futs[f]; d = f.result()
            out.append({"code": r["code"], "name": r["name"], "industry": d["industry"],
                        "sector": d["sector"], "carbon_kw": int(r["carbon_kw"] or 0),
                        "soft_kw": int(r["soft_kw"] or 0), "action_kw": int(r["action_kw"] or 0),
                        "pages": int(r["pages"] or 0), "carbon_num": r.get("carbon_num", "")})
            if i % 40 == 0: print(f"  {i}/{len(src)}  {time.time()-t0:.0f}s", flush=True)
    out.sort(key=lambda x: x["code"])
    p = ROOT/"data/processed/industry.csv"
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["code","name","industry","sector","carbon_kw","soft_kw","action_kw","pages","carbon_num"])
        w.writeheader(); w.writerows(out)
    ok = sum(1 for d in out if d["industry"])
    print(f"\n✅ 行业分类: {ok}/{len(out)}  ({ok/len(out)*100:.0f}%)  -> {p}")
    print("\n大类分布:")
    for k, v in collections.Counter(d["sector"] for d in out).most_common():
        print(f"  {k:<30}{v:>4}")
    print("\n细分行业 Top 20:")
    for k, v in collections.Counter(d["industry"] for d in out if d["industry"]).most_common(20):
        print(f"  {k:<18}{v:>4}")

if __name__ == "__main__":
    main()
