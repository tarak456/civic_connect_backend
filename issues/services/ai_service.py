import math
import re
from typing import Dict, Any, Optional
from ..models import Issue, Department


class CivicAIService:
    """
    Modular AI service for Civic Connect.
    Provides:
    1. Issue classification & confidence scoring
    2. Severity estimation
    3. Department recommendation
    4. Proximity & semantic duplicate detection
    """

    DEPARTMENT_MAP = {
        Issue.Category.POTHOLE: "Roads Department",
        Issue.Category.ROAD_DAMAGE: "Roads Department",
        Issue.Category.GARBAGE: "Sanitation Department",
        Issue.Category.ILLEGAL_DUMPING: "Sanitation Department",
        Issue.Category.STREETLIGHT: "Electrical & Lighting Department",
        Issue.Category.DRAINAGE: "Drainage & Sewerage Department",
        Issue.Category.WATER_LEAKAGE: "Water Works Department",
        Issue.Category.OTHER: "Public Works Department",
    }

    CATEGORY_KEYWORDS = {
        Issue.Category.POTHOLE: ["pothole", "crater", "hole", "road cavity", "asphalt depression", "tar pit"],
        Issue.Category.GARBAGE: ["garbage", "trash", "waste", "litter", "rubbish", "refuse", "bin overflow"],
        Issue.Category.STREETLIGHT: ["streetlight", "street light", "lamp", "dark", "pole", "light out", "illumination", "bulb"],
        Issue.Category.DRAINAGE: ["drain", "drainage", "sewer", "gutter", "overflow", "clogged drain", "manhole", "culvert"],
        Issue.Category.WATER_LEAKAGE: ["water leakage", "pipe burst", "pipeline", "water leak", "dripping", "water supply", "broken pipe"],
        Issue.Category.ROAD_DAMAGE: ["road damage", "crack", "broken road", "pavement", "uneven road", "cobblestone", "sidewalk broken"],
        Issue.Category.ILLEGAL_DUMPING: ["illegal dumping", "dump yard", "construction debris", "debris", "hazardous waste"],
    }

    HIGH_SEVERITY_WORDS = ["major", "severe", "deep", "massive", "dangerous", "emergency", "hazardous", "flood", "live wire", "injury", "accident", "urgent"]
    MEDIUM_SEVERITY_WORDS = ["moderate", "broken", "overflow", "crack", "flickering", "bad", "smell", "annoying"]

    @classmethod
    def haversine_distance_meters(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great-circle distance between two coordinates in meters."""
        r = 6371000  # meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    @classmethod
    def analyze(
        cls,
        image_file=None,
        description: str = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Runs comprehensive AI analysis on the civic report.
        """
        text = (description or "").lower()
        filename = (image_file.name.lower() if hasattr(image_file, "name") else "")

        # 1. Category Classification
        detected_category = Issue.Category.OTHER
        detected_label = "Other Civic Issue"
        confidence = 0.85

        highest_match_count = 0
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text) or kw in filename)
            if matches > highest_match_count:
                highest_match_count = matches
                detected_category = category
                detected_label = dict(Issue.Category.choices).get(category, "Civic Issue")

        if highest_match_count > 0:
            confidence = min(0.96, 0.88 + (highest_match_count * 0.03))
        else:
            # Heuristic from common filename or general context
            if "pothole" in filename or "road" in filename:
                detected_category = Issue.Category.POTHOLE
                detected_label = "Pothole"
                confidence = 0.92
            elif "garbage" in filename or "trash" in filename:
                detected_category = Issue.Category.GARBAGE
                detected_label = "Garbage / Waste"
                confidence = 0.91
            elif "light" in filename or "lamp" in filename:
                detected_category = Issue.Category.STREETLIGHT
                detected_label = "Streetlight"
                confidence = 0.94
            elif "water" in filename or "leak" in filename:
                detected_category = Issue.Category.WATER_LEAKAGE
                detected_label = "Water Leakage"
                confidence = 0.90
            elif "drain" in filename:
                detected_category = Issue.Category.DRAINAGE
                detected_label = "Drainage"
                confidence = 0.93

        # 2. Severity Scoring
        severity = Issue.Severity.LOW
        if any(word in text for word in cls.HIGH_SEVERITY_WORDS):
            severity = Issue.Severity.HIGH
        elif any(word in text for word in cls.MEDIUM_SEVERITY_WORDS):
            severity = Issue.Severity.MEDIUM
        else:
            # Baseline severity based on category
            if detected_category in (Issue.Category.POTHOLE, Issue.Category.WATER_LEAKAGE, Issue.Category.DRAINAGE):
                severity = Issue.Severity.MEDIUM
            elif detected_category in (Issue.Category.ROAD_DAMAGE,):
                severity = Issue.Severity.MEDIUM
            else:
                severity = Issue.Severity.LOW

        # 3. Department Recommendation
        suggested_dept_name = cls.DEPARTMENT_MAP.get(detected_category, "Public Works Department")
        dept_obj = Department.objects.filter(name__icontains=suggested_dept_name.split()[0]).first()
        dept_id = dept_obj.id if dept_obj else None

        # 4. Duplicate Detection
        is_duplicate = False
        duplicate_issue_id = None
        duplicate_title = None
        duplicate_similarity = 0.0
        duplicate_distance_meters = None

        if latitude is not None and longitude is not None:
            # Look at open or recent issues
            open_statuses = [
                Issue.Status.REPORTED,
                Issue.Status.UNDER_REVIEW,
                Issue.Status.ASSIGNED,
                Issue.Status.IN_PROGRESS,
            ]
            candidates = Issue.objects.filter(
                status__in=open_statuses,
                latitude__isnull=False,
                longitude__isnull=False,
            )

            for issue in candidates:
                dist = cls.haversine_distance_meters(latitude, longitude, issue.latitude, issue.longitude)
                # Within 200m radius
                if dist <= 200:
                    sim = 0.5
                    if issue.category == detected_category:
                        sim += 0.4
                    desc_words = set(text.split())
                    issue_words = set((issue.description or "").lower().split())
                    if desc_words and issue_words:
                        overlap = len(desc_words.intersection(issue_words)) / max(len(desc_words), 1)
                        sim += min(0.1, overlap * 0.2)

                    if sim > duplicate_similarity:
                        duplicate_similarity = round(sim, 2)
                        duplicate_issue_id = issue.id
                        duplicate_title = issue.title
                        duplicate_distance_meters = round(dist, 1)

            if duplicate_similarity >= 0.70:
                is_duplicate = True

        return {
            "detected_issue": detected_label,
            "category": detected_category,
            "category_label": detected_label,
            "confidence": round(confidence, 2),
            "severity": severity,
            "suggested_department_id": dept_id,
            "suggested_department_name": suggested_dept_name,
            "is_duplicate": is_duplicate,
            "duplicate_issue_id": duplicate_issue_id,
            "duplicate_title": duplicate_title,
            "duplicate_similarity": duplicate_similarity,
            "duplicate_distance_meters": duplicate_distance_meters,
        }
