# Bottleneck OS Source Policy

This policy defines the intended research universe for the production version of Bottleneck OS. It exists to prevent the system from becoming "whatever we happened to find."

## Scope

Domain: AI infrastructure bottlenecks.

Included categories:

- Compute
- Memory
- Packaging
- Networking
- Optical
- Power
- Cooling
- Data center physical infrastructure

Excluded categories:

- stock picking
- technical trading
- brokerage data
- generic market sentiment
- unsourced social-media rumor
- broad macro commentary without an AI infrastructure mechanism

## Technology Universe

The machine-readable version lives in [bottleneck_os/policy.py](bottleneck_os/policy.py).

Core technologies include:

- GPU
- HBM
- CoWoS
- Networking
- Switch ASIC
- Optical Transceiver
- CPO
- Power
- Transformer
- Cooling
- Rack Density

Watch-list technologies include CPU, inference ASICs, DRAM, NAND, substrates, retimers, LPO, lasers, backup generation, 800V DC, immersion cooling, heat rejection, data center land, and permits.

## Source Universe

Core source classes:

- expert research: Serenity, SemiAnalysis, Dylan Patel public material
- primary companies: NVIDIA, Broadcom, Arista, Micron, SK Hynix, TSMC, Lumentum, Coherent
- infrastructure research: IEA

Watch-list source classes:

- EIA
- Uptime Institute
- Schneider Electric
- Bloom Energy
- AFCOM
- OCP
- OFC
- GTC

## Collection Rule

For a formal report:

- Every evidence item must keep source name, source type, date, title, URL, claim, quote, confidence, and technology.
- Every scored technology must pass the evidence gate.
- Reports must include source coverage and technology coverage.
- Missing core sources must be visible in the report.
- Premium or inaccessible sources must be marked as missing or partial, not silently implied.

## Evidence Gate

A technology can receive a bottleneck score only if it has:

- at least 3 evidence items
- at least 2 independent source names
- at least 1 demand-side signal
- at least 1 capacity, technical, infrastructure, or substitution constraint signal
- at least 1 counterargument or uncertainty note

## Production Standard

The production system should support:

- manual-trigger source ingestion
- URL/PDF/text ingestion
- automatic claim extraction
- source coverage audit
- dated run reports
- traceability from score to evidence quote
- reproducible tests
- a clear distinction between "covered", "partial", and "missing"
