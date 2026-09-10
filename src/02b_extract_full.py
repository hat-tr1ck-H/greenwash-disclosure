# -*- coding: utf-8 -*-
"""Step 2: 并行下载年报 PDF 并抽取 ESG/碳披露指标"""
import requests, pdfplumber, io, csv, re, time, pathlib, json
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
SCAN_PAGES = 10**6       # 全文扫描
WORKERS = 6

CARBON_KW  = ["碳排放", "碳达峰", "碳中和", "温室气体", "碳强度", "碳配额", "碳足迹", "双碳"]
ACTION_KW  = ["减排", "节能", "环保投入", "污染治理", "绿色低碳", "清洁生产", "循环经济"]
SOFT_KW    = ["绿色发展", "可持续发展", "生态文明", "绿水青山", "低碳生活", "环保理念", "社会责任"]
NUM_PAT    = [r"碳排放[量总]?[约为]?\s*([\d,，.]+\s*[万亿]?\s*吨)",
              r"减排[量约]?\s*([\d,，.]+\s*[万亿]?\s*吨)",
              r"温室气体排放[量约]?\s*([\d,，.]+\s*[万亿]?\s*吨)"]
ENV_HEAD   = ["环境和社会责任", "环境与社会责任", "环境信息", "环保情况", "社会责任情况"]

def count_all(txt, kws):
    return sum(txt.count(k) for k in kws)

def one(row):
    code = row["code"]
    try:
        t0 = time.time()
        r = requests.get(row["url"], headers={"User-Agent": UA}, timeout=150)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            return {**row, "status": "bad_pdf", "pages": 0}
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            npg = len(pdf.pages)
            txt = "".join((p.extract_text() or "") for p in pdf.pages[:SCAN_PAGES])
        if len(txt.strip()) < 500:
            return {**row, "status": "no_text", "pages": npg}
        carbon, action, soft = count_all(txt, CARBON_KW), count_all(txt, ACTION_KW), count_all(txt, SOFT_KW)
        nums = []
        for p in NUM_PAT:
            nums += [m.strip() for m in re.findall(p, txt)]
        heads = [h for h in ENV_HEAD if h in txt]
        # 业务类型粗分类(用关键词投票)
        biz = []
        for label, kws in {
            "金融": ["不良贷款率", "资本充足率", "净息差"],
            "医药": ["药品", "临床试验", "医疗器械", "制剂"],
            "能源电力": ["发电量", "装机容量", "上网电价", "煤炭产量"],
            "钢铁建材": ["粗钢", "钢材", "水泥", "熟料"],
            "化工": ["化学品", "树脂", "聚氨酯", "涂料"],
            "TMT/电子": ["半导体", "集成电路", "软件", "芯片", "元器件"],
            "消费": ["白酒", "食品", "服装", "零售", "家居"],
            "地产建筑": ["房地产开发", "施工", "竣工面积", "建筑工程"],
        }.items():
            if sum(txt.count(k) for k in kws) >= 3:
                biz.append(label)
        return {"code": code, "name": row["name"], "orgId": row["orgId"],
                "status": "ok", "pages": npg, "chars": len(txt),
                "carbon_kw": carbon, "action_kw": action, "soft_kw": soft,
                "carbon_num": ";".join(nums[:5]), "env_head": "|".join(heads),
                "biz": "|".join(biz) or "其他", "sec": round(time.time() - t0, 1)}
    except Exception as e:
        return {"code": code, "name": row["name"], "status": f"err:{type(e).__name__}", "pages": 0}

def main():
    rows = list(csv.DictReader(open(ROOT / "data/raw/annual_reports.csv", encoding="utf-8-sig")))
    print(f"待处理 {len(rows)} 家公司, {WORKERS} 线程并行, 每份扫前 {SCAN_PAGES} 页\n")
    out, t0, done = [], time.time(), 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(one, r): r for r in rows}
        for f in as_completed(futs):
            res = f.result(); out.append(res); done += 1
            if done % 20 == 0 or done == len(rows):
                ok = sum(1 for x in out if x["status"] == "ok")
                print(f"  {done:>4}/{len(rows)}  成功 {ok}  用时 {time.time()-t0:.0f}s", flush=True)
    out.sort(key=lambda x: x["code"])
    p = ROOT / "data/processed/disclosure_full.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = ["code","name","orgId","status","pages","chars","carbon_kw","action_kw",
            "soft_kw","carbon_num","env_head","biz","sec"]
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(out)
    ok = [x for x in out if x["status"] == "ok"]
    print(f"\n✅ 成功 {len(ok)}/{len(rows)}  总耗时 {time.time()-t0:.0f}s -> {p}")
    if ok:
        z = sum(1 for x in ok if x["carbon_kw"] == 0)
        print(f"   碳关键词命中 0 次的公司: {z}/{len(ok)} ({z/len(ok)*100:.0f}%)")
        print(f"   抽出带单位碳数值的公司: {sum(1 for x in ok if x['carbon_num'])}/{len(ok)}")

if __name__ == "__main__":
    main()
