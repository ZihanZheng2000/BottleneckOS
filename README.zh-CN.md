# Bottleneck OS

[English](README.md) | [中文](README.zh-CN.md)

Bottleneck OS 是一个面向 AI 基础设施的“瓶颈雷达”。AI 的扩张不只取决于模型和软件，也取决于 HBM 内存、GPU、先进封装、电力、网络、光互连、液冷和数据中心基础设施这些物理层。

Bottleneck OS 用来识别 AI 基础设施里哪些物理层可能在市场形成共识之前，先变成增长约束。它把公司文件、能源报告和公开材料里的证据，转化成一张可追溯的瓶颈雷达，覆盖算力、内存、电力、网络、散热和先进封装等方向。

换句话说，它想回答一个问题：AI 基础设施里，哪个环节可能最先变成限制增长的瓶颈？

系统会读取公开资料，比如 SEC EDGAR 文件、公司公告、能源报告和行业材料，用 LLM 或关键词方法提取结构化证据，然后给不同技术方向打分。输出结果是一张可追溯的瓶颈雷达。

数据完整性和证据追溯标准见 [EVIDENCE.md](EVIDENCE.md)。

---

## 追踪什么

Bottleneck OS 目前追踪 11 个核心技术方向：

| 技术 | 类别 | 可能限制什么 |
|---|---|---|
| HBM 高带宽内存 | Memory | GPU 内存带宽、模型规模和吞吐 |
| Networking / InfiniBand | Interconnect | GPU 集群扩展能力 |
| CPO 共同封装光学 | Interconnect | 下一代数据中心带宽和能效 |
| Power Infrastructure | Power | 数据中心建设、电网接入和供电能力 |
| Cooling Systems | Thermal | 高功率机柜散热和液冷改造 |
| GPU | Compute | 直接 AI 算力供应 |
| CoWoS 先进封装 | Packaging | GPU + HBM 的封装产能 |
| Switch ASIC | Networking | AI 集群交换网络 |
| Optical Transceiver | Interconnect | 800G / 1.6T 光模块供应 |
| Transformer 变压器 | Power | 变电站交付和长周期电力设备 |
| Rack Density | Infrastructure | 单机柜功率密度和机房承载能力 |

---

## 工作方式

```text
公开资料                         证据流水线                         输出
────────                         ─────────                         ────
SEC EDGAR 文件      ┐
EIA / DOE 报告      ├─► 抓取 ─► LLM 提取 ─► 打分 ─► Bottleneck Radar
行业研究和公司资料  ┘             claim 类型       0-100 分        API / 报告 / 网页
```

每条证据会被分类为：

- `demand_signal`：需求增长信号
- `capacity_signal`：产能紧张、供给不足或爬坡约束
- `technical_constraint`：技术、架构、带宽、热管理等约束
- `infrastructure_constraint`：电网、许可、建设周期、基础设施约束
- `substitution_signal`：可能缓解瓶颈的替代方案
- `counterargument`：反方证据或不确定性

只有当一个技术方向有足够证据时，系统才会给出 bottleneck score。证据不足的技术会显示为 `insufficient_evidence`。

---

## 安装和运行

需要 Python 3.10 或更高版本。

开发安装：

```powershell
pip install -e ".[dev]"
```

如果要使用 OpenAI 或 Anthropic 做 LLM 提取：

```powershell
pip install -e ".[llm]"
```

复制 `.env.example` 为 `.env`，然后填入 API key：

```text
OPENAI_API_KEY=sk-proj-...
# 或
ANTHROPIC_API_KEY=sk-ant-...
```

`.env` 已经被 `.gitignore` 忽略，不应该提交到 GitHub。

启动本地 API 和网页：

```powershell
py -m bottleneck_os --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

---

## 抓取真实公开资料

默认 RSS/API 来源配置在 `sources/feeds.txt`，包括 SEC EDGAR、EIA、DOE 和公开公司来源。

```powershell
py scripts/fetch_feeds.py --feeds sources/feeds.txt --archive-dir archive/sources
py scripts/extract_claims.py --source-dir archive/sources --llm --auto-accept
```

如果只想用一组真实公开 URL，可以用：

```powershell
py scripts/fetch_sources.py --manifest sources/manifest.real.txt --archive-dir archive/sources
```

---

## 人工审核流程

LLM 提取出来的 claim 只是草稿，不应该直接当成最终事实。正式报告建议先走 review：

```powershell
py scripts/extract_claims.py --source-dir archive/sources --llm --review-dir review/current
```

然后检查 `review/current/claims.jsonl`，把每条 claim 的 `review_status` 改成：

- `accepted`
- `rejected`
- `pending`

只用 accepted claims 生成报告：

```powershell
py scripts/report_from_review.py --review-dir review/current --as-of $TODAY
```

---

## API 是什么

这个项目不只是网页，也提供 JSON API，方便以后接别的前端、dashboard 或分析工具。

| Endpoint | 用途 |
|---|---|
| `GET /api/health` | 服务状态和证据新鲜度 |
| `GET /api/bottleneck-radar` | 当前瓶颈排名 |
| `GET /api/technology-radar` | 所有技术的关注度和动量 |
| `GET /api/bottlenecks/{technology}` | 某个技术的详细分数、证据和反方观点 |
| `GET /api/theses?technology=Power` | 为某个技术生成 thesis |
| `GET /api/coverage` | 检查哪些技术或来源证据不足 |
| `GET /api/evidence-audit` | 检查 source URL 和 evidence quote 是否可追溯 |
| `GET /api/acquisition-plan` | 推荐下一步应该补哪些来源 |
| `GET /api/expert-signal` | 查看专家来源信号 |

普通读者可以不用管 API 部分；它主要给开发者和后续集成使用。

---

## 测试

```powershell
pytest -q
pytest tests/test_evidence_audit.py -q
```

---

## 当前限制

这是一个早期系统，还有一些明确限制：

- 还不是全自动爬虫，抓取和提取需要手动触发。
- 有些技术方向的证据覆盖还不够深。
- LLM 提取的 claim 需要人工 review。
- 30 天 attention momentum 主要基于证据发布日期，不是真正长期历史时间序列。
- SemiAnalysis 等专家来源还没有完全接入默认数据源。

项目的核心原则是：不编造证据。每条正式 claim 都应该能追溯到真实公开来源和对应 quote。
