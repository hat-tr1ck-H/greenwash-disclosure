# 技术手册 · Technical Manual

### Green Talk, Brown Silence — 数据管道实现文档

**作者：洪嘉伟** · **2026-09-10** · [English](#english-version) at the end

---

## 目录

1. [系统概览](#1-系统概览)
2. [环境搭建](#2-环境搭建)
3. [数据获取层（CNINFO API）](#3-数据获取层cninfo-api)
4. [文本抽取层](#4-文本抽取层)
5. [行业分类层](#5-行业分类层)
6. [评分与分析层](#6-评分与分析层)
7. [性能优化记录](#7-性能优化记录)
8. [已知陷阱清单](#8-已知陷阱清单)
9. [复现校验](#9-复现校验)

---

## 1. 系统概览

四个脚本构成一条线性管道，每一步的产物落盘为 CSV，便于单独调试和断点重跑。

```
01_harvest.py  ──►  data/raw/annual_reports.csv
                      (code, name, orgId, title, url)
                            │
02b_extract_full.py ──►  data/processed/disclosure_full.csv
                      (carbon_kw, action_kw, soft_kw, carbon_num)
                            │
04_industry.py  ──►  data/processed/industry.csv
                      (+ industry, sector  ← 官方行业分类)
                            │
03_analyze.py   ──►  figures/*.png + data/processed/summary.json
```

**设计原则**：每一步只依赖上一步的 CSV 产物，不依赖上游脚本的内存状态。这样任何一步失败都能单独重跑，不必从头再来。

---

## 2. 环境搭建

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 依赖

| 包 | 用途 | 备注 |
|---|---|---|
| `requests` | HTTP 请求 | 唯一网络依赖 |
| `pdfplumber` | PDF 文本抽取 | **性能瓶颈所在**，见第 7 节 |
| `matplotlib` | 出图 | 图表标签全部用英文，规避中文字体问题 |

### Python 版本注意

本项目在 **Python 3.14.7** 上开发验证通过。若使用更老的版本（3.9–3.12）同样可运行。
注意：3.14 刚发布时 pandas / akshare 等包缺少预编译 wheel，若需扩展本项目（例如加入 pandas 做回归），
建议用 3.11/3.12，或配置国内镜像：

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>
```

---

## 3. 数据获取层（CNINFO API）

### 3.1 接口

```
POST http://www.cninfo.com.cn/new/hisAnnouncement/query
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
User-Agent: <任意现代浏览器 UA>   ← 必须，否则被拒
```

### 3.2 请求参数

| 参数 | 值 | 说明 |
|---|---|---|
| `pageNum` | 1..N | 页码 |
| `pageSize` | **30** | ⚠️ **服务端硬上限**，传 50/100 也只返回 30 |
| `column` | `szse` | ⚠️ **实测不影响结果**，见陷阱 8.3 |
| `tabName` | `fulltext` | 全文检索模式 |
| `category` | `category_ndbg_szsh` | 年度报告分类 |
| `seDate` | `2026-04-01~2026-04-30` | 披露日期区间，**非会计年度** |
| `stock` | 见 3.3 | 留空 = 全市场 |
| `isHLtitle` | `true` | 标题高亮 |

### 3.3 ⚠️ orgId 拼接规则（本项目的核心逆向发现）

单公司查询需要 `stock={code},{orgId}`。官方搜索接口
`/new/information/topSearch/query` **已失效**（返回 `{"error":"系统异常"}`），
因此必须自行拼接 orgId。实测规律：

| 板块 | 代码特征 | orgId 构造 | 示例 |
|---|---|---|---|
| 上交所主板 | `6xxxxx` | `gssh0` + code | 600019 → `gssh0600019` |
| 深交所主板 | `000xxx`/`002xxx` | `gssz0` + code | 000001 → `gssz0000001` |
| 北交所 | `8xxxxx`/`920xxx` | 无规律，**须从全市场查询结果中获取** | 920166 → `gfbj0873794` |

**绕过方案**：全市场查询（`stock=` 留空）返回的每条记录**自带 `orgId` 字段**。
因此 `01_harvest.py` 直接遍历全市场，一次性建立 `code → orgId` 映射，
完全不需要碰那个已失效的搜索接口。

### 3.4 响应字段

```json
{
  "secCode": "600019",
  "secName": "宝钢股份",
  "orgId":   "gssh0600019",
  "announcementTitle": "宝钢股份2025年年度报告全文",
  "adjunctUrl": "finalpage/2026-03-21/1225022887.PDF",
  "adjunctSize": "1930",
  "announcementTime": 1774022400000
}
```

PDF 完整地址 = `http://static.cninfo.com.cn/` + `adjunctUrl`

### 3.5 采集策略

`01_harvest.py 14` 表示遍历 14 页（每页 30 条），历时约 15 秒，得到 199 家公司的年报清单。
**标题清洗规则**——排除以下四类，避免重复计数：

```python
if ("年度报告" in title and "摘要" not in title
        and "英文" not in title and "更正" not in title):
```

### 3.6 限速

页面间 `time.sleep(0.3)`。这是对公共接口的基本礼貌，也降低被限流概率。

---

## 4. 文本抽取层

### 4.1 流程

```
PDF bytes ─► pdfplumber.open(BytesIO) ─► 逐页 extract_text() ─► 拼接 ─► 关键词计数
```

### 4.2 评分词表

| 类别 | 字段名 | 词表 |
|---|---|---|
| 硬披露 | `carbon_kw` | 碳排放, 碳达峰, 碳中和, 温室气体, 碳强度, 碳配额, 碳足迹, 双碳 |
| 行动 | `action_kw` | 减排, 节能, 环保投入, 污染治理, 绿色低碳, 清洁生产, 循环经济 |
| 软话术 | `soft_kw` | 绿色发展, 可持续发展, 生态文明, 绿水青山, 低碳生活, 环保理念, 社会责任 |

### 4.3 数值抽取正则

```python
r"碳排放[量总]?[约为]?\s*([\d,，.]+\s*[万亿]?\s*吨)"
r"减排[量约]?\s*([\d,，.]+\s*[万亿]?\s*吨)"
r"温室气体排放[量约]?\s*([\d,，.]+\s*[万亿]?\s*吨)"
```

命中数极低（199 家中仅 4 家）——这本身是论文的核心发现之一。

### 4.4 ⚠️ 扫描范围的决定性影响

`SCAN_PAGES` 参数直接改变结论：

| 取值 | 含义 | 零碳披露比例 |
|---|---|---|
| `25` | 仅前 25 页 | **66%** |
| `10**6` | 全文 | **49%** |

**相差 17 个百分点。** 年报的「环境和社会责任」章节位置不固定，靠前扫描会系统性低估披露。
`02b_extract_full.py` 使用全文模式，所有论文数字以此为准。

---

## 5. 行业分类层

### 5.1 接口

```
GET https://push2delay.eastmoney.com/api/qt/stock/get
    ?secid={market}.{code}&fltt=2&invt=2&fields=f57,f58,f127
```

- `market`：`1` = 上交所（6 开头），`0` = 深交所（其余）
- **`f127`** = 官方行业名称（如「白酒Ⅱ」「普钢」「医疗器械」）

### 5.2 ⚠️ 为什么必须用 `push2delay`

`push2.eastmoney.com` 在并发查询下会**限流**——返回空 body（连错误 JSON 都不给），
且冷却时间很长（90 秒后仍不通）。
`push2delay.eastmoney.com` 是延迟行情域名，**不限制**，且 `f127` 字段完整。

脚本采用 `HOSTS` 列表按重试次数切换，配合 `max_workers=3`，实测 199 家约 25 秒完成，成功率 96%。

### 5.3 行业归并

东财细分行业（「普钢」「医疗器械」…）按关键词归并为 11 个大类：

`Financials` / `Energy & Utilities` / `Steel & Materials` / `Chemicals` /
`Real Estate & Construction` / `Healthcare & Pharma` / `TMT & Electronics` /
`Consumer` / `Industrials` / `Agriculture` / `Other`

映射表定义在 `04_industry.py` 的 `BIG` 字典中。

### 5.4 失败回退

31 家（16%）未匹配到行业（多为新上市、ST、或退市整理期），统一归入 `Other`，
在论文的行业表中如实报告，不做插补。

---

## 6. 评分与分析层

`03_analyze.py` 读取 `industry.csv`，产出：

1. **描述统计**——零披露率、中位数、带数值比例、软话术独有比例
2. **行业汇总**——每个大类/细分行业的碳均值、软均值、零披露率
3. **三张图**：
   - `fig1_industry.png` — 行业碳披露强度横向条形图
   - `fig2_gap.png` — 软话术 vs 硬披露散点图（含 45° 分界线）
   - `fig3_coverage.png` — 覆盖率饼图 + 行业沉默率
4. **`summary.json`** — 机器可读的全部汇总指标

### 图表规范

- 所有标签**使用英文**——规避 matplotlib 中文字体缺失问题（见陷阱 8.5）
- `dpi=170`，`bbox_inches="tight"`
- 行业样本量 `n < 2` 的类别不出图，但保留在 CSV 中

---

## 7. 性能优化记录

### 7.1 GIL 是真实瓶颈

| 方案 | 199 家公司耗时 |
|---|---|
| `ThreadPoolExecutor(8)` | **>8 分钟未完成**（已终止） |
| `ProcessPoolExecutor(6)` | **71 秒**（25 页模式） |
| `ProcessPoolExecutor(6)` | **612 秒**（全文模式） |

`pdfplumber` 的文本抽取是**纯 CPU 密集**操作，线程池被 GIL 串行化，8 线程实测 CPU 占用
仅 101%（等于单核）。换成进程池后获得约 7 倍加速。

**教训**：CPU 密集型任务用线程池，等于给自己加了一层调度开销。

### 7.2 输出缓冲

脚本长跑必须加 `python -u` 或在 `print()` 里加 `flush=True`，否则日志被缓冲，
看起来像卡死。本项目两者都做了。

### 7.3 全文模式的代价

全文抽取比 25 页模式慢 8.6 倍（612s vs 71s）。这个代价**必须付**——见 4.4 节，
扫描范围会改变结论。

---

## 8. 已知陷阱清单

> 这一节记录开发中真实踩过的坑，供后续维护者（和未来的我）参考。

### 8.1 `pkill -f` 会杀掉自己

```bash
pkill -f 02_extract.py     # ❌ 执行这条命令的 bash 自身命令行也含该字符串
```

后果：命令被 SIGTERM，**后续串联的命令全部不执行**，但看起来像是"跑完了"。
本项目因此浪费了一轮调试。**改用 `kill <PID>`，或让匹配串不出现在命令行里。**

### 8.2 `pageSize` 服务端上限 30

传 `50` 或 `100` 都不报错，**静默返回 30 条**。若按 `pageSize=50` 估算页数会导致漏采。

### 8.3 `column` 参数无实际作用

`column=szse` 与 `column=sse` 返回**完全相同**的结果集（同为 11187 条），
且都包含 6 开头的沪市代码。该参数可保留但不应依赖其做板块筛选。

### 8.4 日期区间 ≠ 会计年度

`seDate=2026-04-01~2026-04-30` 筛的是**披露日期**。2025 财年年报在 2026 年 1–4 月披露，
因此查 2025 年会漏掉大部分。**按披露窗口取数，不要按会计年度。**

### 8.5 matplotlib 中文字体

系统已装 Noto Sans CJK，但 matplotlib 会解析出 `Noto Sans CJK JP`（日文变体名），
且 `font.family` 设置在部分调用路径下不生效，导致中文渲染成方块（□□□）。

**规避方案**：图表标签全部用英文。若确需中文，须显式对每个文本元素传
`fontproperties=FontProperties(fname=...)`。

### 8.6 GitHub 发布环境的网络限制

- `github.com` 网页/git 端点：**间歇可用**
- `api.github.com`：**稳定可用**
- release 资源域名（`release-assets.githubusercontent.com`）：**基本不可用**（15MB 二进制超时）
- `raw.githubusercontent.com`：**不可用**（图片走 CDN 可显示，直连取不到）

结论：**发布用 git 端点 + API，不要依赖 release 资源和 raw 直连。**

### 8.7 细粒度 PAT 的权限是分开的

建仓库要 `Administration: Read and write`，推代码要 `Contents: Read and write`。
两者独立——只给前者会出现"仓库建好了但推不上去"的 403。详见第 9 节。

---

## 9. 复现校验

### 9.1 完整复现

```bash
python src/01_harvest.py 14      # ~15 s   → 199 家公司
python src/02b_extract_full.py   # ~612 s  → disclosure_full.csv
python src/04_industry.py        # ~25 s   → industry.csv
python src/03_analyze.py         # ~5 s    → figures/ + summary.json
```

**总耗时约 11 分钟。**

### 9.2 预期输出

运行 `03_analyze.py` 应得到：

```
zero carbon mentions : 97 (48.7%)
median / max         : 1 / 44
reports with a NUMBER: 4 (2.0%)
soft-only firms      : 97 (48.7%)
```

行业表首行应为 `Energy & Utilities  22  8.2  …  14%`。

### 9.3 校验要点

若结果**偏离以上数字**，依次检查：

1. `02b` 是否真的用了全文模式（`SCAN_PAGES = 10**6`）——最常见原因
2. `04_industry.py` 的行业匹配率是否 ≥ 90%
3. 采集的样本数是否为 199（若 `01_harvest.py` 参数不同则会变，属正常）
4. 巨潮是否改版了 API 响应结构

### 9.4 断点重跑

各步骤产物独立落盘，任何一步可单独重跑。例如行业匹配失败只需重跑 `04_industry.py`，
不必重新下载 199 份 PDF。

---

## English Version

### Technical Manual (abridged)

**Author: Jiawei Hong (洪嘉伟) · 2026-09-10**

This document describes the implementation of the data pipeline behind *Green Talk, Brown
Silence*. Key engineering notes:

**Data acquisition.** Annual reports are harvested from the CNINFO disclosure API via
`POST /new/hisAnnouncement/query`. Two non-obvious constraints govern the endpoint:
`pageSize` is silently capped at 30, and the official company-search endpoint is defunct,
so `orgId` values must be obtained from a market-wide query (each record carries its own
`orgId`) rather than constructed. `orgId` follows `gssh0{code}` for Shanghai listings and
`gssz0{code}` for Shenzhen, with no predictable pattern for Beijing Exchange firms.

**Text extraction.** Full-text extraction is mandatory, not optional: scanning only the
first 25 pages of each report yields a 66% zero-disclosure rate, while full-text scanning
yields 49%. The environmental section's position within a filing is not fixed.

**Concurrency.** `pdfplumber` extraction is CPU-bound. A thread pool is serialised by the
GIL and failed to complete in over 8 minutes; switching to `ProcessPoolExecutor(6)` reduced
the runtime to 71 seconds (25-page mode) and 612 seconds (full-text mode).

**Industry labels.** Official industry classification is retrieved from Eastmoney's
`f127` field. The standard `push2` host rate-limits aggressively under concurrency and
returns empty bodies; `push2delay` does not. Coverage: 191/199 firms (96%).

**Chart typography.** All figure labels are in English, deliberately: matplotlib resolves
the installed Noto Sans CJK font to its Japanese variant name and renders Chinese glyphs as
tofu boxes in several code paths. English labels sidestep the issue entirely.

**Reproducibility.** The four stages write independent CSV artefacts, so any stage can be
re-run in isolation. Full pipeline runtime is approximately 11 minutes.
