"""Seeded catalogs (clinical, financial and printing defaults).

Every list here is editable in the application; the seeds only make a new clinic
usable on day one and are written once, during set-up.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SeedItem:
    """A catalog row to insert when it does not exist yet."""

    code: str
    label: str
    extra: dict[str, object] | None = None


#: Payment methods (Bangladesh: cash, bank, cards and the common MFS wallets).
PAYMENT_METHODS: tuple[tuple[str, str, bool], ...] = (
    ("cash", "Cash", False),
    ("bank", "Bank transfer", True),
    ("card", "Card", True),
    ("bkash", "bKash", True),
    ("nagad", "Nagad", True),
    ("rocket", "Rocket", True),
    ("upay", "Upay", True),
    ("other", "Other", False),
)

#: Tooth status vocabulary for the dental chart (adult + paediatric).
TOOTH_STATUSES: tuple[tuple[str, str, str, str], ...] = (
    ("normal", "Normal", "neutral", "fill"),
    ("affected", "Affected", "warning", "fill"),
    ("caries", "Caries", "danger", "fill"),
    ("filled", "Filled", "primary", "fill"),
    ("treated", "Treated", "success", "fill"),
    ("missing", "Missing", "neutral", "cross"),
    ("impacted", "Impacted", "warning", "triangle"),
    ("fractured", "Fractured", "danger", "line"),
    ("root_canal", "Root canal", "primary", "dot"),
    ("crown", "Crown", "primary", "ring"),
    ("bridge", "Bridge", "primary", "bar"),
    ("implant", "Implant", "success", "square"),
    ("supernumerary", "Supernumerary", "warning", "star"),
    ("other", "Other", "neutral", "dot"),
)

#: Treatment categories.
TREATMENT_CATEGORIES: tuple[str, ...] = (
    "Diagnostic",
    "Preventive",
    "Restorative",
    "Endodontics",
    "Periodontics",
    "Prosthodontics",
    "Orthodontics",
    "Oral surgery",
    "Cosmetic",
    "Other",
)

#: Expense categories (docs/04 §5).
EXPENSE_CATEGORIES: tuple[str, ...] = (
    "Rent",
    "Electricity",
    "Internet",
    "Accessories & supplies",
    "Staff salary",
    "Maintenance",
    "Equipment",
    "Marketing",
    "Other",
)

#: Clinical catalogs: complaints, examinations, advice.
CLINICAL_CATALOGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "complaint",
        (
            "Toothache / দাঁতে ব্যথা",
            "Sensitivity",
            "Bleeding gums / মাড়ি থেকে রক্ত",
            "Swelling",
            "Bad breath",
            "Broken tooth",
            "Missing tooth",
            "Staining",
            "Routine check-up",
        ),
    ),
    (
        "examination",
        (
            "Caries present",
            "Gingivitis",
            "Periodontitis",
            "Plaque/calculus",
            "Mobile tooth",
            "Impacted tooth",
            "Root stump",
            "Worn dentition",
            "Soft tissue lesion",
        ),
    ),
    (
        "advice",
        (
            "Brush twice daily",
            "Floss daily",
            "Avoid sweets",
            "Warm saline rinse",
            "Review after 7 days",
            "Review after 3 months",
        ),
    ),
    (
        "diagnosis",
        (
            "Dental caries",
            "Pulpitis",
            "Apical periodontitis",
            "Gingivitis",
            "Chronic periodontitis",
            "Dentine hypersensitivity",
        ),
    ),
)

#: Medicine catalog seeds (Bangladesh common brands/generics); free text always allowed.
MEDICINES: tuple[tuple[str, str, str], ...] = (
    ("Paracetamol", "Tablet", "500 mg"),
    ("Ibuprofen", "Tablet", "400 mg"),
    ("Amoxicillin", "Capsule", "500 mg"),
    ("Metronidazole", "Tablet", "400 mg"),
    ("Azithromycin", "Tablet", "500 mg"),
    ("Cephalexin", "Capsule", "500 mg"),
    ("Diclofenac Sodium", "Tablet", "50 mg"),
    ("Chlorhexidine", "Mouthwash", "0.2%"),
    ("Omeprazole", "Capsule", "20 mg"),
    ("Vitamin C", "Tablet", "500 mg"),
)

#: Default printer profiles (A4 for documents, thermal for receipts).
PRINTER_PROFILES: tuple[tuple[str, str, int | None, int | None, int], ...] = (
    ("A4 prescription", "A4", 210, 297, 11),
    ("A5 prescription", "A5", 148, 210, 10),
    ("A4 invoice", "A4", 210, 297, 10),
    ("80 mm receipt", "80mm", 80, None, 9),
    ("58 mm receipt", "58mm", 58, None, 9),
)

DEFAULT_PROFILE_FOR: dict[str, str] = {
    "prescription": "A4 prescription",
    "invoice": "A4 invoice",
    "receipt": "80 mm receipt",
    "report": "A4 invoice",
}
