"""Entidades compartidas por todos los modelos de la Game Intelligence Platform."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class SourceType(str, Enum):
    RIOT_OFFICIAL = "riot_official"
    CHALLENGER    = "challenger"
    OTP           = "otp"
    STATISTICS    = "statistics"
    GUIDE         = "guide"
    COMMUNITY     = "community"
    OWN_EXPERIENCE = "own_experience"


class Confidence(str, Enum):
    VERIFIED   = "verified"
    HIGH       = "high"
    MEDIUM     = "medium"
    COMMUNITY  = "community"


@dataclass
class KnowledgeSource:
    type: SourceType
    author: str | None = None
    url: str | None = None
    confidence: Confidence = Confidence.MEDIUM
    date: str | None = None      # ISO date — para detectar fuentes antiguas
    notes: str | None = None


@dataclass
class VideoReference:
    id: str
    title: str
    platform: str                # "youtube" | "twitch" | "local_asset"
    description: str
    tags: list[str] = field(default_factory=list)
    url: str | None = None
    timestamp_seconds: int | None = None
    champion: str | None = None
    matchup_vs: str | None = None
    difficulty: str | None = None   # "basic" | "intermediate" | "advanced"
    patch_version: str | None = None


@dataclass
class PatchVersion:
    major: int
    minor: int

    @property
    def full(self) -> str:
        return f"{self.major}.{self.minor}"

    def is_older_than(self, other: "PatchVersion", versions: int = 2) -> bool:
        self_n  = self.major * 100 + self.minor
        other_n = other.major * 100 + other.minor
        return (other_n - self_n) >= versions

    @classmethod
    def parse(cls, version_str: str) -> "PatchVersion":
        parts = version_str.split(".")
        return cls(major=int(parts[0]), minor=int(parts[1]))

    def __str__(self) -> str:
        return self.full
