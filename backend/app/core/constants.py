"""
Hardcoded exam and subject data for MVP.
Only NEET and TNPSC are supported. Subjects are fixed per exam.
Custom subjects are NOT allowed.
"""

from typing import List
from dataclasses import dataclass


@dataclass
class SubjectInfo:
    name: str
    icon: str       # emoji icon for the subject
    color: str      # tailwind-compatible color label


@dataclass
class ExamInfo:
    id: str         # "NEET" or "TNPSC"
    name: str
    tag: str
    description: str
    subjects: List[SubjectInfo]


EXAM_DATA: List[ExamInfo] = [
    ExamInfo(
        id="NEET",
        name="NEET",
        tag="Medical Entrance",
        description="National Eligibility cum Entrance Test for undergraduate medical admissions.",
        subjects=[
            SubjectInfo(name="Physics",   icon="⚛️",  color="blue"),
            SubjectInfo(name="Chemistry", icon="🧪",  color="green"),
            SubjectInfo(name="Botany",    icon="🌿",  color="emerald"),
            SubjectInfo(name="Zoology",   icon="🦎",  color="amber"),
        ],
    ),
    ExamInfo(
        id="TNPSC",
        name="TNPSC",
        tag="Civil Services",
        description="Tamil Nadu Public Service Commission exam for government service recruitment.",
        subjects=[
            SubjectInfo(name="History",        icon="🏛️",  color="orange"),
            SubjectInfo(name="Geography",      icon="🌍",  color="teal"),
            SubjectInfo(name="Polity",         icon="⚖️",  color="indigo"),
            SubjectInfo(name="Economics",      icon="📈",  color="purple"),
            SubjectInfo(name="Science",        icon="🔬",  color="cyan"),
            SubjectInfo(name="Current Affairs",icon="📰",  color="rose"),
        ],
    ),
]

# Flat lookup: exam_id → ExamInfo
EXAM_MAP = {e.id: e for e in EXAM_DATA}

# Valid exam IDs
VALID_EXAM_IDS = list(EXAM_MAP.keys())


def get_subjects_for_exam(exam_id: str) -> List[str]:
    """Return list of subject names for a given exam. Returns [] if not found."""
    exam = EXAM_MAP.get(exam_id)
    return [s.name for s in exam.subjects] if exam else []


def is_valid_subject(exam_id: str, subject: str) -> bool:
    """Check if a subject name belongs to the given exam."""
    return subject in get_subjects_for_exam(exam_id)
