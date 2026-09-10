# -*- coding: utf-8 -*-
"""Step 1: 从巨潮资讯网采集 A 股年报清单(含 orgId)"""
import requests, json, time, csv, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
SEASON = "2026-04-01~2026-04-30"   # 年报密集披露期

def page(pn, ps=30, retries=3):
    body = (f"pageNum={pn}&pageSize={ps}&column=szse&tabName=fulltext&plate=&stock="
            f"&searchkey=&secid=&category=category_ndbg_szsh&trade=&seDate={SEASON}"
            "&sortName=&sortType=&isHLtitle=true")
    for i in range(retries):
        try:
            r = requests.post(URL, headers=H, data=body.encode(), timeout=30)
            return r.json()
        except Exception:
            time.sleep(1.5 * (i + 1))
    return {}

def main(max_pages=14):
    recs, seen = [], set()
    for pn in range(1, max_pages + 1):
        d = page(pn)
        anns = d.get("announcements") or []
        if not anns:
            print(f"  page {pn}: 无数据, 停止"); break
        for a in anns:
            t = a["announcementTitle"]
            if ("年度报告" in t and "摘要" not in t and "英文" not in t
                    and "更正" not in t and "取消" not in t and "已取消" not in t):
                if a["secCode"] in seen:
                    continue
                seen.add(a["secCode"])
                recs.append({"code": a["secCode"], "name": a["secName"], "orgId": a["orgId"],
                             "title": t, "url": "http://static.cninfo.com.cn/" + a["adjunctUrl"],
                             "size_kb": a.get("adjunctSize", "")})
        print(f"  page {pn:>3}: 累计 {len(recs)} 家")
        time.sleep(0.3)
    out = ROOT / "data/raw/annual_reports.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["code","name","orgId","title","url","size_kb"])
        w.writeheader(); w.writerows(recs)
    print(f"\n✅ 保存 {len(recs)} 条 -> {out}")
    return recs

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
