"""Formal coverage policy for Bottleneck OS.

This module defines the source and technology universe the system intends to
cover. Current data coverage can be audited against this policy so reports do
not quietly become "whatever we happened to find."
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceTarget:
    name: str
    category: str
    priority: str
    expected_source_types: tuple[str, ...]


@dataclass(frozen=True)
class TechnologyTarget:
    name: str
    category: str
    priority: str
    aliases: tuple[str, ...]


TECHNOLOGY_UNIVERSE = [
    TechnologyTarget("GPU", "Compute", "core", ("accelerator", "AI accelerator", "Blackwell", "Rubin")),
    TechnologyTarget("CPU", "Compute", "watch", ("server CPU", "Grace", "x86")),
    TechnologyTarget("Inference ASIC", "Compute", "watch", ("ASIC", "custom silicon", "inference chip")),
    TechnologyTarget("HBM", "Memory", "core", ("high bandwidth memory", "HBM3E", "HBM4")),
    TechnologyTarget("DRAM", "Memory", "watch", ("DDR5", "LPDDR", "server memory")),
    TechnologyTarget("NAND", "Memory", "watch", ("SSD", "flash storage")),
    TechnologyTarget("CoWoS", "Packaging", "core", ("advanced packaging", "interposer", "2.5D packaging")),
    TechnologyTarget("Substrate", "Packaging", "watch", ("ABF", "package substrate")),
    TechnologyTarget("Networking", "Networking", "core", ("ethernet", "infiniband", "switching", "AI fabric")),
    TechnologyTarget("Switch ASIC", "Networking", "core", ("Tomahawk", "Spectrum-X", "Jericho")),
    TechnologyTarget("Retimer", "Networking", "watch", ("PCIe retimer", "SerDes")),
    TechnologyTarget("Optical Transceiver", "Optical", "core", ("800G", "1.6T", "pluggable optics")),
    TechnologyTarget("CPO", "Optical", "core", ("co-packaged optics", "silicon photonics")),
    TechnologyTarget("LPO", "Optical", "watch", ("linear pluggable optics",)),
    TechnologyTarget("Laser", "Optical", "watch", ("CW laser", "EML", "high-power laser")),
    TechnologyTarget("Power", "Power", "core", ("grid", "substation", "interconnect", "electricity")),
    TechnologyTarget("Transformer", "Power", "core", ("large power transformer", "LPT")),
    TechnologyTarget("Backup Generation", "Power", "watch", ("fuel cell", "gas turbine", "generator")),
    TechnologyTarget("800V DC", "Power", "watch", ("HVDC", "800 VDC")),
    TechnologyTarget("Cooling", "Cooling", "core", ("liquid cooling", "thermal", "CDU", "chiller")),
    TechnologyTarget("Immersion Cooling", "Cooling", "watch", ("immersion",)),
    TechnologyTarget("Heat Rejection", "Cooling", "watch", ("heat exchanger", "water", "dry cooler")),
    TechnologyTarget("Data Center Land", "Data Center", "watch", ("land", "site selection")),
    TechnologyTarget("Permits", "Data Center", "watch", ("permitting", "interconnection queue")),
    TechnologyTarget("Rack Density", "Data Center", "core", ("rack-scale", "rack density", "NVL72")),
]


SOURCE_UNIVERSE = [
    SourceTarget("Serenity", "expert_research", "core", ("analyst_note", "research_report")),
    SourceTarget("SemiAnalysis", "expert_research", "core", ("analyst_note", "research_report")),
    SourceTarget("Dylan Patel", "expert_research", "core", ("interview_transcript", "public_post")),
    SourceTarget("NVIDIA", "primary_company", "core", ("technical_blog", "product_page", "presentation")),
    SourceTarget("Broadcom", "primary_company", "core", ("press_release", "presentation", "earnings_transcript")),
    SourceTarget("Arista", "primary_company", "core", ("whitepaper", "presentation", "earnings_transcript")),
    SourceTarget("Micron", "primary_company", "core", ("earnings_transcript", "press_release")),
    SourceTarget("SK Hynix", "primary_company", "core", ("company_article", "earnings_transcript", "press_release")),
    SourceTarget("TSMC", "primary_company", "core", ("press_release", "presentation", "earnings_transcript")),
    SourceTarget("Lumentum", "primary_company", "core", ("product_page", "earnings_transcript", "presentation")),
    SourceTarget("Coherent", "primary_company", "core", ("investor_presentation", "product_page", "earnings_transcript")),
    SourceTarget("IEA", "infrastructure_research", "core", ("research_report",)),
    SourceTarget("EIA", "infrastructure_research", "watch", ("dataset", "research_report")),
    SourceTarget("Uptime Institute", "infrastructure_research", "watch", ("industry_report",)),
    SourceTarget("Schneider Electric", "infrastructure_vendor", "watch", ("whitepaper", "industry_report")),
    SourceTarget("Bloom Energy", "infrastructure_vendor", "watch", ("industry_report", "whitepaper")),
    SourceTarget("AFCOM", "infrastructure_research", "watch", ("industry_article", "industry_report")),
    SourceTarget("OCP", "conference", "watch", ("conference_talk", "presentation")),
    SourceTarget("OFC", "conference", "watch", ("conference_talk", "presentation")),
    SourceTarget("GTC", "conference", "watch", ("conference_talk", "presentation")),
]


EVIDENCE_GATE = {
    "min_evidence_items": 3,
    "min_independent_sources": 2,
    "required_claim_groups": {
        "demand": ("demand_signal",),
        "constraint": (
            "capacity_signal",
            "technical_constraint",
            "infrastructure_constraint",
            "substitution_signal",
        ),
        "counterargument": ("counterargument", "substitution_signal"),
    },
}


def source_names() -> set[str]:
    return {source.name for source in SOURCE_UNIVERSE}


def technology_names() -> set[str]:
    return {technology.name for technology in TECHNOLOGY_UNIVERSE}


def core_source_names() -> set[str]:
    return {source.name for source in SOURCE_UNIVERSE if source.priority == "core"}


def core_technology_names() -> set[str]:
    return {technology.name for technology in TECHNOLOGY_UNIVERSE if technology.priority == "core"}
