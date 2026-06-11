# CFA Level I 2026 Module → Topic 매핑

# quiz_data.json의 토픽명 → 모듈명 매핑
TOPIC_ALIAS = {
    "Ethical & Professional Standards": "Ethics",
    "Quantitative Methods": "Quantitative Methods",
    "Economics": "Economics",
    "Financial Statement Analysis": "Financial Statement Analysis",
    "Corporate Issuers": "Corporate Issuers",
    "Equity Investments": "Equity Investments",
    "Fixed Income": "Fixed Income",
    "Derivatives": "Derivatives",
    "Alternative Investments": "Alternative Investments",
    "Portfolio Management": "Portfolio Management",
}

MODULE_COLORS = {
    "Ethics": "#6B7280",
    "Quantitative Methods": "#8B5CF6",
    "Economics": "#F59E0B",
    "Financial Statement Analysis": "#10B981",
    "Corporate Issuers": "#EF4444",
    "Equity Investments": "#3B82F6",
    "Fixed Income": "#06B6D4",
    "Derivatives": "#EC4899",
    "Alternative Investments": "#14B8A6",
    "Portfolio Management": "#F97316",
}

MODULES = {
    "Ethics": {
        "color": "#6B7280",
        "topics": {
            "Code of Ethics & Standards": list(range(1, 4)),
            "GIPS": [4],
        }
    },
    "Quantitative Methods": {
        "color": "#8B5CF6",
        "topics": {
            "Time Value of Money": [5],
            "Discounted Cash Flow": [6],
            "Statistical Concepts": [7, 8, 9],
            "Probability": [10, 11],
            "Hypothesis Testing": [12, 13],
            "Technical Analysis": [14],
        }
    },
    "Economics": {
        "color": "#F59E0B",
        "topics": {
            "Demand & Supply": [15, 16],
            "Market Structures": [17],
            "Macro: GDP & IS-LM": [18, 19],
            "Monetary & Fiscal Policy": [20],
            "International Trade": [21, 22],
        }
    },
    "Financial Statement Analysis": {
        "color": "#10B981",
        "topics": {
            "Intro to FSA": [23],
            "Balance Sheet": [24],
            "Income Statement": [25],
            "Cash Flow": [26],
            "Financial Analysis": [27, 28],
            "Inventories": [29],
            "Long-Lived Assets": [30],
            "Income Taxes": [31],
            "Non-Current Liabilities": [32],
        }
    },
    "Corporate Issuers": {
        "color": "#EF4444",
        "topics": {
            "Corporate Governance": [33],
            "Capital Budgeting": [34],
            "Cost of Capital": [35],
            "Leverage": [36],
            "Working Capital": [37],
        }
    },
    "Equity Investments": {
        "color": "#3B82F6",
        "topics": {
            "Market Organization": [38],
            "Market Indices": [39],
            "Equity Valuation": [40],
        }
    },
    "Fixed Income": {
        "color": "#06B6D4",
        "topics": {
            "Fixed Income Basics": [41, 42],
            "FI Valuation": [43, 44],
            "MBS & ABS": [45],
            "Credit Analysis": [46],
        }
    },
    "Derivatives": {
        "color": "#EC4899",
        "topics": {
            "Derivative Markets": [47],
            "Forward & Futures": [48],
            "Options & Swaps": [49],
        }
    },
    "Alternative Investments": {
        "color": "#14B8A6",
        "topics": {
            "Real Estate & PE": [50],
            "Hedge Funds & Commodities": [51],
        }
    },
    "Portfolio Management": {
        "color": "#F97316",
        "topics": {
            "Portfolio Basics": [52],
            "Risk & Return": [53, 54],
            "Portfolio Construction": [55],
        }
    },
}


def module_names() -> list[str]:
    return list(MODULES.keys())


def topics_for_module(module: str) -> dict:
    return MODULES.get(module, {}).get("topics", {})


def module_color(module: str) -> str:
    return MODULES.get(module, {}).get("color", "#6B7280")


def get_module_for_reading(reading_num: int) -> tuple:
    """return (module_name, topic_name) or (None, None)"""
    for mod_name, mod_data in MODULES.items():
        for topic_name, readings in mod_data["topics"].items():
            if reading_num in readings:
                return mod_name, topic_name
    return (None, None)
