#!/usr/bin/env python3
"""Extract 2024 SchweserNotes content and rebuild enhanced_concepts.json."""

import os
import re
import json
from pdfminer.high_level import extract_text

DRIVE_BASE = "/Users/joark/Library/CloudStorage/GoogleDrive-jinukahn98@gmail.com/내 드라이브/03. CFA/CFA 2024 Level I"

BOOK_MODULE_MAP = {
    "QM,ECONOMICS": ["Quantitative Methods", "Economics"],
    "PM,CI": ["Portfolio Management", "Corporate Issuers"],
    "FSA,EI": ["Financial Statement Analysis", "Equity Investments"],
    "FI,DERIV": ["Fixed Income", "Derivatives"],
    "AI,PM,ETHICS": ["Alternative Investments", "Portfolio Management", "Ethics"],
}

# Book 2 is PM,CI — but "Portfolio Management" also appears in Book 5
# We'll merge PM from both books (Book 5 has more PM content)
BOOK_PM_SOURCE = "AI,PM,ETHICS"  # primary PM source is Book 5

MODULE_KEYWORDS = {
    "Quantitative Methods": ["quantitative", "time value", "probability", "statistics", "regression", "hypothesis", "sampling", "estimation"],
    "Economics": ["economics", "supply", "demand", "gdp", "monetary", "fiscal", "currency", "exchange rate", "macroeconomics", "microeconomics"],
    "Corporate Issuers": ["corporate", "capital structure", "leverage", "dividends", "working capital", "business model"],
    "Financial Statement Analysis": ["financial statement", "balance sheet", "income statement", "cash flow", "ratio analysis", "accounting"],
    "Equity Investments": ["equity", "stock", "valuation", "dividend discount", "p/e ratio", "market efficiency"],
    "Fixed Income": ["fixed income", "bond", "yield", "duration", "convexity", "credit risk", "term structure"],
    "Derivatives": ["derivative", "option", "futures", "forward", "swap", "arbitrage", "put-call parity"],
    "Alternative Investments": ["alternative", "real estate", "hedge fund", "private equity", "commodities", "infrastructure"],
    "Portfolio Management": ["portfolio", "asset allocation", "risk", "return", "capm", "efficient frontier", "behavioral"],
    "Ethics": ["ethics", "code of ethics", "standard", "conduct", "fiduciary", "conflict of interest", "compliance"],
}


def find_pdfs():
    """Find 2024 SchweserNotes PDFs (exclude duplicates with '(1)')."""
    files = os.listdir(DRIVE_BASE)
    pdfs = {}
    for f in files:
        if "SchweserNotes" in f and "(1)" not in f and f.endswith(".pdf"):
            for key in BOOK_MODULE_MAP:
                if key in f:
                    pdfs[key] = os.path.join(DRIVE_BASE, f)
                    break
    return pdfs


def extract_pdf_text(pdf_path):
    """Extract text from PDF using pdfminer."""
    print(f"  Extracting: {os.path.basename(pdf_path)}")
    text = extract_text(pdf_path)
    print(f"  Extracted {len(text):,} chars")
    return text


def clean_text(text):
    """Clean extracted PDF text."""
    # Remove excessive whitespace but preserve paragraph breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    # Remove page numbers patterns
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    # Remove ©, page headers common in Schweser
    text = re.sub(r'©\s*Kaplan.*?\n', '\n', text)
    text = re.sub(r'PRINTED BY:.*?\n', '\n', text)
    return text.strip()


def extract_los_statements(text):
    """Extract LOS statements from text."""
    los_list = []

    # Pattern: "LOS XX.X:" or "LOS XX.X " followed by action verbs
    # Schweser uses "LOS" followed by number
    los_pattern = re.compile(
        r'LOS\s+(\d+[a-z]?)\s*[:\.]?\s*((?:calculate|describe|explain|define|identify|compare|evaluate|analyze|determine|distinguish|interpret|demonstrate|classify|list|outline|contrast|discuss|recognize|apply|construct|estimate|formulate|assess|understand|derive|use|recommend|justify|illustrate|show|state|summarize|select)\b[^\n]{20,200})',
        re.IGNORECASE
    )

    for match in los_pattern.finditer(text):
        los_num = match.group(1)
        los_text = match.group(2).strip()
        # Clean up the LOS text
        los_text = re.sub(r'\s+', ' ', los_text)
        if len(los_text) > 30:
            full_los = f"LOS {los_num}: {los_text}"
            if full_los not in los_list:
                los_list.append(full_los)

    # Alternative pattern for multi-line LOS
    if len(los_list) < 3:
        # Try broader pattern
        los_pattern2 = re.compile(
            r'(?:^|\n)\s*((?:calculate|describe|explain|define|identify|compare|evaluate|analyze|determine|distinguish|interpret|demonstrate|classify|list|outline|contrast|discuss|recognize|apply|construct|estimate|formulate|assess)\b[^\n]{30,300})',
            re.IGNORECASE | re.MULTILINE
        )
        for match in los_pattern2.finditer(text):
            stmt = match.group(1).strip()
            stmt = re.sub(r'\s+', ' ', stmt)
            if len(stmt) > 40 and stmt not in los_list:
                los_list.append(stmt)

    return los_list[:50]  # Cap at 50 LOS per module


def extract_key_concepts(text, module_name):
    """Extract key concepts from text."""
    concepts = []

    # Look for "Key Concepts" sections
    kc_match = re.search(r'KEY CONCEPTS?\s*\n(.*?)(?=\n[A-Z]{4,}|\Z)', text, re.DOTALL | re.IGNORECASE)
    if kc_match:
        kc_text = kc_match.group(1)
        # Extract bullet points or numbered items
        items = re.findall(r'(?:^|\n)\s*(?:[•\-\*]|\d+\.)\s*(.+?)(?=\n|$)', kc_text)
        concepts.extend([item.strip() for item in items if len(item.strip()) > 20])

    # Look for "Summary" sections
    summary_match = re.search(r'(?:STUDY SESSION SUMMARY|SUMMARY)\s*\n(.*?)(?=\n[A-Z]{4,}|\Z)', text, re.DOTALL | re.IGNORECASE)
    if summary_match:
        summary_text = summary_match.group(1)
        sentences = re.findall(r'[A-Z][^.!?]{30,200}[.!?]', summary_text)
        for s in sentences[:10]:
            s = s.strip()
            if s and s not in concepts:
                concepts.append(s)

    # Module-specific concept extraction if we have few
    if len(concepts) < 5:
        # Extract sentences with key financial terms
        keywords = MODULE_KEYWORDS.get(module_name, [])
        sentences = re.findall(r'[A-Z][^.!?\n]{40,250}[.!?]', text)
        for sent in sentences:
            sent = sent.strip()
            if any(kw in sent.lower() for kw in keywords) and sent not in concepts:
                concepts.append(sent)
                if len(concepts) >= 20:
                    break

    # Deduplicate and limit
    seen = set()
    unique_concepts = []
    for c in concepts:
        c_clean = re.sub(r'\s+', ' ', c).strip()
        if c_clean and c_clean not in seen and len(c_clean) > 20:
            seen.add(c_clean)
            unique_concepts.append(c_clean)

    return unique_concepts[:20]


def extract_formulas(text, module_name):
    """Extract formulas from text."""
    formulas = []

    # Common formula patterns
    # "Formula Name: expression" or "Name = expression"
    formula_patterns = [
        # "Name: formula" pattern
        re.compile(r'([A-Z][A-Za-z\s]{5,50}):\s*([A-Za-z0-9\s\+\-\*/\(\)\^=×÷≈∑σμ%$€£¥,\.]{10,100})\n', re.MULTILINE),
        # "Name = formula" pattern
        re.compile(r'([A-Z][A-Za-z\s]{5,40})\s*=\s*([A-Za-z0-9\s\+\-\*/\(\)\^×÷σμ%]{10,80})', re.MULTILINE),
    ]

    # Module-specific formula extraction
    formula_keywords = {
        "Quantitative Methods": ["PV", "FV", "NPV", "IRR", "EAR", "HPR", "variance", "standard deviation", "coefficient", "correlation"],
        "Economics": ["GDP", "CPI", "elasticity", "multiplier", "velocity", "money supply"],
        "Financial Statement Analysis": ["ROE", "ROA", "P/E", "EPS", "current ratio", "debt-to-equity", "asset turnover"],
        "Fixed Income": ["duration", "convexity", "YTM", "price", "coupon", "yield spread"],
        "Derivatives": ["put-call parity", "intrinsic value", "delta", "gamma", "Black-Scholes"],
        "Portfolio Management": ["Sharpe ratio", "Treynor", "Jensen's alpha", "beta", "CAPM", "efficient frontier"],
        "Equity Investments": ["DDM", "P/E", "EV/EBITDA", "Gordon growth", "FCFE", "FCFF"],
    }

    # Curated formulas based on module
    curated = {
        "Quantitative Methods": [
            ["Future Value (FV)", "FV = PV × (1 + r)^n"],
            ["Present Value (PV)", "PV = FV / (1 + r)^n"],
            ["EAR (Effective Annual Rate)", "EAR = (1 + periodic rate)^m - 1"],
            ["Holding Period Return", "HPR = (End Value - Begin Value + Income) / Begin Value"],
            ["Sample Variance", "s² = Σ(xi - x̄)² / (n-1)"],
            ["Coefficient of Variation", "CV = Standard Deviation / Mean"],
            ["Sharpe Ratio", "SR = (Rp - Rf) / σp"],
            ["Bayes' Formula", "P(A|B) = P(B|A) × P(A) / P(B)"],
            ["NPV", "NPV = Σ CFt/(1+r)^t - Initial Investment"],
            ["Roy's Safety-First Ratio", "SFRatio = (E[Rp] - RL) / σp"],
        ],
        "Economics": [
            ["GDP (Expenditure Approach)", "GDP = C + I + G + (X - M)"],
            ["Real GDP", "Real GDP = Nominal GDP / Price Level Index"],
            ["Price Elasticity of Demand", "PED = %ΔQd / %ΔP"],
            ["Money Multiplier", "Money Multiplier = 1 / Reserve Requirement"],
            ["Purchasing Power Parity", "S = P_domestic / P_foreign"],
            ["Fisher Effect", "Nominal Rate ≈ Real Rate + Expected Inflation"],
            ["Quantity Theory of Money", "MV = PQ"],
        ],
        "Corporate Issuers": [
            ["Operating Leverage (DOL)", "DOL = %ΔOperating Income / %ΔSales"],
            ["Financial Leverage (DFL)", "DFL = %ΔEPS / %ΔOperating Income"],
            ["WACC", "WACC = wd×rd×(1-t) + we×re + wp×rp"],
            ["Break-Even Quantity", "Q = Fixed Costs / (Price - Variable Cost)"],
            ["Net Working Capital", "NWC = Current Assets - Current Liabilities"],
            ["Cash Conversion Cycle", "CCC = DSO + DOH - DPO"],
        ],
        "Financial Statement Analysis": [
            ["Return on Equity (ROE)", "ROE = Net Income / Average Equity"],
            ["Return on Assets (ROA)", "ROA = Net Income / Average Total Assets"],
            ["Current Ratio", "Current Ratio = Current Assets / Current Liabilities"],
            ["Debt-to-Equity Ratio", "D/E = Total Debt / Total Equity"],
            ["Asset Turnover", "Asset Turnover = Revenue / Average Total Assets"],
            ["Net Profit Margin", "Net Profit Margin = Net Income / Revenue"],
            ["EPS (Basic)", "EPS = (Net Income - Preferred Dividends) / Weighted Avg Shares"],
            ["DuPont: ROE", "ROE = Net Profit Margin × Asset Turnover × Equity Multiplier"],
        ],
        "Equity Investments": [
            ["Gordon Growth Model (DDM)", "V0 = D1 / (r - g)"],
            ["P/E Ratio", "P/E = Price per Share / EPS"],
            ["Enterprise Value", "EV = Market Cap + Debt - Cash"],
            ["FCFE", "FCFE = CFO - FCInv + Net Borrowing"],
            ["FCFF", "FCFF = EBIT × (1-t) + D&A - CapEx - ΔWCNOA"],
            ["EV/EBITDA", "EV/EBITDA = Enterprise Value / EBITDA"],
        ],
        "Fixed Income": [
            ["Bond Price (Coupon)", "P = Σ C/(1+r)^t + FV/(1+r)^n"],
            ["Macaulay Duration", "MacDur = Σ [t × PV(CFt)] / Price"],
            ["Modified Duration", "ModDur = MacDur / (1 + r/m)"],
            ["Price Change (Duration)", "ΔP ≈ -ModDur × ΔY × P"],
            ["YTM Approximation", "YTM ≈ (Coupon + (FV-P)/n) / ((FV+P)/2)"],
            ["Current Yield", "CY = Annual Coupon / Current Price"],
            ["Convexity Adjustment", "ΔP/P ≈ -D × Δy + ½ × C × (Δy)²"],
        ],
        "Derivatives": [
            ["Put-Call Parity", "C + PV(X) = P + S"],
            ["Forward Price", "F = S × (1 + r)^T - FV(Benefits) + FV(Costs)"],
            ["Intrinsic Value (Call)", "Intrinsic Value = max(0, S - X)"],
            ["Intrinsic Value (Put)", "Intrinsic Value = max(0, X - S)"],
            ["Payoff Long Forward", "Payoff = ST - F0"],
            ["Payoff Long Call", "Payoff = max(0, ST - X)"],
            ["Payoff Long Put", "Payoff = max(0, X - ST)"],
        ],
        "Alternative Investments": [
            ["Capitalization Rate (RE)", "Cap Rate = NOI / Property Value"],
            ["Net Asset Value (NAV)", "NAV = (Assets - Liabilities) / Shares Outstanding"],
            ["Management Fee (PE)", "Management Fee = % of Committed or NAV"],
            ["IRR (PE)", "Solve: NPV = Σ CFt/(1+IRR)^t = 0"],
            ["TVPI Multiple", "TVPI = (Distributions + Residual Value) / Paid-In Capital"],
        ],
        "Portfolio Management": [
            ["Portfolio Return", "Rp = Σ wi × Ri"],
            ["Portfolio Variance (2 assets)", "σ²p = w₁²σ₁² + w₂²σ₂² + 2w₁w₂σ₁σ₂ρ₁₂"],
            ["CAPM", "E(Ri) = Rf + βi × [E(Rm) - Rf]"],
            ["Beta", "β = Cov(Ri, Rm) / Var(Rm) = ρim × σi / σm"],
            ["Sharpe Ratio", "Sharpe = (Rp - Rf) / σp"],
            ["Treynor Ratio", "Treynor = (Rp - Rf) / βp"],
            ["Jensen's Alpha", "α = Rp - [Rf + β × (Rm - Rf)]"],
            ["Information Ratio", "IR = Active Return / Tracking Error"],
        ],
        "Ethics": [
            ["No standard formulas", "Ethics is qualitative — focus on Standards and Code of Ethics"],
        ],
    }

    return curated.get(module_name, [])


def extract_exam_tips(text, module_name):
    """Extract exam tips from text."""
    tips = []

    # Look for exam tip sections
    tip_patterns = [
        r'(?:EXAM FOCUS|PROFESSOR\'S NOTE|EXAM TIPS?|KEY REVIEW)\s*\n(.*?)(?=\n[A-Z]{4,}|\Z)',
        r'(?:for the exam|on the exam|exam prep)\s*[:,]?\s*([^\n]{30,200})',
    ]

    for pattern in tip_patterns:
        matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
        for m in matches:
            section = m.group(1)
            sentences = re.findall(r'[A-Z][^.!?\n]{20,200}[.!?]', section)
            for s in sentences[:5]:
                s = s.strip()
                if s and s not in tips:
                    tips.append(s)

    # Curated tips by module
    curated_tips = {
        "Quantitative Methods": [
            "Focus on TVM calculations — these appear frequently in the exam.",
            "Know the difference between geometric and arithmetic mean returns.",
            "Be able to calculate and interpret standard deviation and variance.",
            "Understand Type I vs Type II errors in hypothesis testing.",
            "Know when to use z-test vs t-test (population variance known vs unknown).",
            "The normal distribution is heavily tested — memorize key confidence intervals (68%, 90%, 95%, 99%).",
            "For NPV/IRR, know when they conflict and which to prefer (NPV for wealth maximization).",
        ],
        "Economics": [
            "Understand aggregate supply/demand shifts and their effects on output and price level.",
            "Know the differences between monetary and fiscal policy tools.",
            "Currency exchange rates: memorize price/base currency convention.",
            "GDP deflator vs CPI — know the difference and limitations.",
            "Understand the business cycle phases and their characteristics.",
            "Know the J-curve effect and Marshall-Lerner condition for trade balance.",
            "Understand comparative advantage vs absolute advantage for trade.",
        ],
        "Corporate Issuers": [
            "WACC calculation is frequently tested — know each component.",
            "Understand the capital structure theories (M&M with/without taxes).",
            "Know the differences between operating and financial leverage.",
            "Working capital management ratios (CCC, DSO, DOH, DPO) are testable.",
            "Understand agency conflicts and corporate governance mechanisms.",
            "Know the characteristics of different dividend policies.",
        ],
        "Financial Statement Analysis": [
            "DuPont decomposition of ROE is a high-frequency exam topic.",
            "Know how to convert between FIFO and LIFO in different inflation environments.",
            "Understand cash flow statement classifications (operating, investing, financing).",
            "Be able to compute EPS under diluted vs basic methods.",
            "Ratio analysis: memorize liquidity, solvency, profitability, and efficiency ratios.",
            "Know the difference between finance leases and operating leases.",
            "Revenue recognition (IFRS 15 / ASC 606) — 5-step model is testable.",
        ],
        "Equity Investments": [
            "DDM variants (Gordon Growth, H-Model, Multistage) appear regularly.",
            "Know the three forms of market efficiency and evidence for/against each.",
            "Understand P/E, P/B, P/S, EV/EBITDA — when each is appropriate.",
            "FCFE vs FCFF — know how to derive from financial statements.",
            "Equity risk premium and its estimation methods are testable.",
            "Understand top-down vs bottom-up analysis approaches.",
        ],
        "Fixed Income": [
            "Bond pricing and yield relationships are heavily tested.",
            "Duration is the most important fixed income concept — know Macaulay vs Modified vs Effective.",
            "Understand the yield curve shapes and theories explaining them.",
            "Know credit ratings, credit spread, and default risk concepts.",
            "Securitization structures (MBS, ABS) — know prepayment risk.",
            "Convexity: bonds with greater convexity outperform for large yield changes.",
        ],
        "Derivatives": [
            "Put-call parity is frequently tested in multiple contexts.",
            "Know payoff diagrams for all basic options and forwards.",
            "Understand how futures prices are determined (cost of carry model).",
            "Interest rate swaps — know who pays fixed/floating and net payment calculations.",
            "Options pricing factors: S, X, r, T, σ, and dividends — know direction of effect.",
            "Be able to construct synthetic positions using put-call parity.",
        ],
        "Alternative Investments": [
            "Know the fee structure of hedge funds (2-and-20 model).",
            "Real estate valuation: income approach, sales comparison, cost approach.",
            "Understand PE fund stages and lifecycle (vintage year concept).",
            "Infrastructure and commodities — know characteristics vs traditional assets.",
            "TVPI, DPI, RVPI multiples for PE performance — know the formulas.",
            "Understand diversification benefits of alternatives (low correlation).",
        ],
        "Portfolio Management": [
            "CAPM is the most tested model — know assumptions and limitations.",
            "Efficient frontier and CAL — understand optimal risky portfolio.",
            "Know three performance measures: Sharpe, Treynor, Jensen's Alpha.",
            "Systematic vs unsystematic risk — only systematic is rewarded in CAPM.",
            "Behavioral finance biases — categorize as cognitive vs emotional.",
            "Investment Policy Statement (IPS) components are testable.",
            "Asset allocation: strategic vs tactical, know the differences.",
        ],
        "Ethics": [
            "Standards I-VII — know each standard's requirements in detail.",
            "The Code of Ethics is qualitative; focus on the spirit, not just the letter.",
            "Mosaic theory: combining material non-public info with public info is NOT a violation.",
            "Soft dollar arrangements: must benefit client, full disclosure required.",
            "Know the difference between Standards and the Code — both are testable.",
            "GIPS compliance: voluntary but once claimed, must apply to all composites.",
            "Priority of transactions: clients > employer > personal.",
        ],
    }

    result = curated_tips.get(module_name, tips[:10])
    if not result:
        result = tips[:10]
    return result


def build_summary(text, module_name):
    """Build a module summary."""
    curated_summaries = {
        "Quantitative Methods": (
            "Quantitative Methods provides the mathematical and statistical foundation for investment analysis. "
            "Core topics include the time value of money, which is foundational for valuing any cash flow stream, "
            "and statistical concepts such as probability distributions, expected value, variance, and covariance. "
            "This module also covers hypothesis testing, sampling theory, and correlation analysis used in portfolio construction."
        ),
        "Economics": (
            "Economics covers both microeconomic and macroeconomic principles relevant to investment analysis. "
            "Microeconomics focuses on supply/demand, firm behavior, and market structures, while macroeconomics "
            "examines GDP, inflation, monetary and fiscal policy, and international trade. Currency exchange rates and "
            "the business cycle are also central topics for understanding the investment environment."
        ),
        "Corporate Issuers": (
            "Corporate Issuers examines the financial decisions made by corporations, including capital structure, "
            "cost of capital (WACC), and capital budgeting. Topics include business models, leverage (operating and financial), "
            "dividend policy, working capital management, and corporate governance. Understanding how companies raise and deploy "
            "capital is essential for equity and credit analysis."
        ),
        "Financial Statement Analysis": (
            "Financial Statement Analysis is one of the most important and heavily tested topics in CFA Level I. "
            "It covers the three core financial statements (income statement, balance sheet, cash flow statement), "
            "financial ratio analysis, accounting for inventories, long-lived assets, taxes, and pensions. "
            "The DuPont framework and quality-of-earnings analysis are key tools for assessing company performance."
        ),
        "Equity Investments": (
            "Equity Investments covers how equities are organized and valued. Topics include market organization, "
            "market efficiency, equity valuation approaches (DDM, FCFE/FCFF, relative valuation), and industry analysis. "
            "Candidates should understand the assumptions behind each model and when to apply them, as well as "
            "how to identify mispriced securities relative to intrinsic value."
        ),
        "Fixed Income": (
            "Fixed Income covers the features, pricing, and risk analysis of debt securities. Key topics include "
            "bond pricing and yield measures, the term structure of interest rates, duration and convexity as interest "
            "rate risk measures, and credit analysis including ratings and spreads. Structured products such as MBS and "
            "ABS, including prepayment risk, are also covered."
        ),
        "Derivatives": (
            "Derivatives covers forwards, futures, options, and swaps — their characteristics, payoffs, and pricing. "
            "Put-call parity is a central relationship. Candidates must understand cost-of-carry pricing for forwards and "
            "futures, the factors affecting option prices, and how derivatives can be used to hedge risk or create synthetic "
            "positions. CFA Level I focuses primarily on concepts rather than complex quantitative pricing models."
        ),
        "Alternative Investments": (
            "Alternative Investments covers asset classes beyond traditional stocks and bonds: hedge funds, private equity, "
            "real estate, commodities, and infrastructure. Key topics include the fee structures, risk-return characteristics, "
            "liquidity constraints, and due diligence considerations for each asset class. These investments can provide "
            "diversification benefits due to their low correlation with traditional assets."
        ),
        "Portfolio Management": (
            "Portfolio Management introduces modern portfolio theory, including mean-variance optimization, the Capital "
            "Asset Pricing Model (CAPM), and performance evaluation. Topics include risk-return tradeoffs, asset allocation, "
            "diversification, and behavioral finance biases. The Investment Policy Statement (IPS) and the portfolio "
            "management process provide the framework for managing client portfolios."
        ),
        "Ethics": (
            "Ethics and Professional Standards are foundational to the CFA designation. The CFA Institute Code of Ethics "
            "and Standards of Professional Conduct (Standards I–VII) set out the ethical obligations of CFA members and "
            "candidates. Key areas include conflicts of interest, material non-public information, duties to clients and "
            "employers, and GIPS compliance. Ethics questions often involve applying standards to realistic scenarios."
        ),
    }

    return curated_summaries.get(module_name, f"Overview of key concepts in {module_name} for the CFA Level I examination.")


def build_los_for_module(text, module_name):
    """Build LOS list for a module with curated fallback."""
    # Try to extract from text first
    extracted = extract_los_statements(text)

    curated_los = {
        "Quantitative Methods": [
            "LOS 1a: Interpret interest rates as required rates of return, discount rates, or opportunity costs",
            "LOS 1b: Explain an interest rate as the sum of a real risk-free rate and premiums for inflation, default, liquidity, and maturity risk",
            "LOS 1c: Calculate and interpret the effective annual rate, given the stated annual interest rate and the frequency of compounding",
            "LOS 1d: Calculate the solution for time value of money problems with different compounding periods",
            "LOS 2a: Calculate and interpret the future value (FV) and present value (PV) of a single sum of money, an annuity, and a series of unequal cash flows",
            "LOS 2b: Demonstrate the use of a timeline in modeling and solving time value of money problems",
            "LOS 3a: Describe the characteristics of and differences among nominal, ordinal, interval, and ratio scales",
            "LOS 3b: Calculate and interpret measures of central tendency, including mean, median, and mode",
            "LOS 3c: Calculate and interpret measures of dispersion, including range, variance, and standard deviation",
            "LOS 3d: Calculate and interpret the coefficient of variation and Sharpe ratio",
            "LOS 4a: Define a random variable, an outcome, and an event",
            "LOS 4b: Identify the two defining properties of probability, and distinguish among empirical, subjective, and a priori probabilities",
            "LOS 4c: Calculate and interpret conditional probabilities using Bayes' formula",
            "LOS 5a: Describe a normal distribution and the empirical rule",
            "LOS 5b: Calculate probabilities for normally distributed random variables",
            "LOS 6a: Explain hypothesis testing and the process of testing hypotheses",
            "LOS 6b: Identify the appropriate test statistic and interpret results for a test of the population mean",
            "LOS 6c: Distinguish between Type I and Type II errors",
            "LOS 7a: Calculate and interpret the net present value (NPV) and the internal rate of return (IRR) of an investment",
            "LOS 7b: Contrast the NPV rule to the IRR rule and identify problems with the IRR rule",
        ],
        "Economics": [
            "LOS 8a: Distinguish among types of markets: goods, factor, and financial markets",
            "LOS 8b: Explain the principles of demand and supply analysis and how prices are determined in competitive markets",
            "LOS 8c: Describe the effects of a shift in demand or supply on equilibrium price and quantity",
            "LOS 9a: Calculate and interpret price, income, and cross-price elasticities of demand",
            "LOS 9b: Describe the demand for and supply of labor, and how wages are determined",
            "LOS 10a: Describe the characteristics of perfect competition, monopolistic competition, oligopoly, and monopoly",
            "LOS 10b: Explain price discrimination and its welfare effects",
            "LOS 11a: Describe the components of GDP using the expenditure and income approaches",
            "LOS 11b: Compare the monetary and fiscal policy tools available to governments",
            "LOS 11c: Describe the phases of the business cycle and their characteristics",
            "LOS 12a: Describe how exchange rates are quoted and calculate cross-exchange rates",
            "LOS 12b: Describe the carry trade and calculate its profit",
            "LOS 12c: Explain absolute and relative purchasing power parity",
            "LOS 12d: Describe the factors that cause exchange rates to change",
            "LOS 13a: Describe the benefits and costs of international trade",
            "LOS 13b: Distinguish between comparative and absolute advantage",
        ],
        "Corporate Issuers": [
            "LOS 14a: Describe the objective of capital structure and explain the factors that influence it",
            "LOS 14b: Explain the Modigliani-Miller propositions with and without taxes",
            "LOS 14c: Describe target capital structure and explain factors that affect it",
            "LOS 15a: Calculate and interpret the weighted average cost of capital (WACC)",
            "LOS 15b: Explain the effect of taxes on the cost of debt and cost of equity",
            "LOS 16a: Calculate and interpret the net present value (NPV) and IRR of capital projects",
            "LOS 16b: Explain the factors affecting capital allocation decisions",
            "LOS 17a: Describe the types of dividends and share repurchases and how they affect shareholders",
            "LOS 17b: Compare dividend policies and explain their effect on shareholder value",
            "LOS 18a: Describe working capital and calculate the cash conversion cycle",
            "LOS 18b: Describe methods for managing a company's working capital",
            "LOS 19a: Describe the types of leverage and calculate and interpret operating, financial, and total leverage",
            "LOS 19b: Explain the relationship between leverage and the risk and return characteristics of a company",
            "LOS 20a: Describe the key elements of a business model",
            "LOS 20b: Explain the roles of stakeholders and describe corporate governance mechanisms",
        ],
        "Financial Statement Analysis": [
            "LOS 21a: Describe the roles of financial reporting and financial statement analysis",
            "LOS 21b: Identify the financial statements and supplementary information provided in financial reports",
            "LOS 22a: Describe the general features of financial statements under IFRS and US GAAP",
            "LOS 22b: Describe useful attributes of financial reports, including understandability, timeliness, and comparability",
            "LOS 23a: Describe the components of the income statement and calculate comprehensive income",
            "LOS 23b: Describe the components of the balance sheet and their relationships",
            "LOS 23c: Describe the components of the statement of cash flows and their classification",
            "LOS 24a: Describe common financial ratios and their interpretation",
            "LOS 24b: Calculate and interpret activity, liquidity, solvency, profitability, and valuation ratios",
            "LOS 24c: Describe the DuPont analysis of return on equity",
            "LOS 25a: Describe the effects of accounting choices on financial ratios",
            "LOS 25b: Explain the FIFO, LIFO, and weighted-average cost methods",
            "LOS 26a: Describe the treatment of long-lived assets under IFRS and US GAAP",
            "LOS 26b: Calculate and interpret depreciation methods and their effects on financial statements",
            "LOS 27a: Describe income tax accounting and calculate income tax expense",
            "LOS 27b: Distinguish between temporary and permanent differences in income tax",
            "LOS 28a: Distinguish between operating and finance leases and their financial statement effects",
        ],
        "Equity Investments": [
            "LOS 29a: Describe the characteristics of equity markets and equity market indexes",
            "LOS 29b: Explain the uses of market indexes and the differences among weighting methods",
            "LOS 30a: Describe the forms of market efficiency and market anomalies",
            "LOS 30b: Explain the implications of each form of market efficiency",
            "LOS 31a: Describe characteristics and uses of equity valuation models",
            "LOS 31b: Estimate the intrinsic value of a common stock using the dividend discount model",
            "LOS 31c: Calculate and interpret the value of a common stock using price multiples",
            "LOS 32a: Calculate and interpret free cash flow to equity (FCFE) and free cash flow to firm (FCFF)",
            "LOS 32b: Explain advantages and limitations of each equity valuation model",
            "LOS 33a: Describe the elements that need to be covered in an equity research report",
            "LOS 33b: Distinguish between company and industry analysis",
        ],
        "Fixed Income": [
            "LOS 34a: Describe basic features of a fixed-income security",
            "LOS 34b: Describe the content of a bond indenture",
            "LOS 35a: Describe yield measures for fixed-rate bonds, floating-rate notes, and money market instruments",
            "LOS 35b: Calculate and interpret the full price, accrued interest, and flat price of a bond",
            "LOS 36a: Calculate a bond's price given a market discount rate",
            "LOS 36b: Identify the relationship among a bond's price, coupon rate, maturity, and market discount rate",
            "LOS 37a: Calculate and interpret Macaulay duration, modified duration, and money duration of a bond",
            "LOS 37b: Explain how a bond's maturity, coupon, and yield affect its interest rate risk",
            "LOS 37c: Calculate and interpret convexity and explain its role in estimating price changes",
            "LOS 38a: Describe the term structure of interest rates and how it relates to bond yields",
            "LOS 38b: Compare the spot rate, forward rate, and yield to maturity",
            "LOS 39a: Describe credit risk and distinguish between default risk and recovery rate",
            "LOS 39b: Explain the four Cs of credit analysis: capacity, collateral, covenants, character",
            "LOS 40a: Describe covered bonds, asset-backed securities, and mortgage-backed securities",
            "LOS 40b: Explain prepayment risk and how it affects MBS valuation",
        ],
        "Derivatives": [
            "LOS 41a: Define a derivative and describe the basic features of derivative markets",
            "LOS 41b: Distinguish between exchange-traded and over-the-counter derivatives",
            "LOS 42a: Describe the characteristics of forward contracts and how they are priced",
            "LOS 42b: Calculate the payoff of a forward contract at expiration",
            "LOS 43a: Describe the characteristics of futures contracts and how they differ from forwards",
            "LOS 43b: Explain how futures prices are determined using the cost-of-carry model",
            "LOS 44a: Define basic option types (calls and puts) and describe their characteristics",
            "LOS 44b: Calculate the value at expiration of long and short call and put options",
            "LOS 44c: Explain put-call parity and calculate the price of one option given the price of the other",
            "LOS 44d: Describe the factors that affect option prices and how they affect call and put values",
            "LOS 45a: Describe the characteristics of swap contracts and calculate the net payment",
            "LOS 45b: Explain interest rate swaps, currency swaps, and equity swaps",
        ],
        "Alternative Investments": [
            "LOS 46a: Describe characteristics of alternative investments compared to traditional investments",
            "LOS 46b: Explain the potential benefits of adding alternative investments to a portfolio",
            "LOS 47a: Describe hedge fund strategies and the typical structure of hedge funds",
            "LOS 47b: Explain the fee structure of hedge funds and calculate fees under the 2-and-20 model",
            "LOS 48a: Describe private equity strategies including venture capital, growth equity, and buyouts",
            "LOS 48b: Describe the life cycle of a private equity fund and explain performance metrics (TVPI, DPI, RVPI)",
            "LOS 49a: Describe commercial real estate investments and valuation approaches",
            "LOS 49b: Calculate the capitalization rate and value of real estate using the income approach",
            "LOS 50a: Describe commodity investments and how commodity prices are determined",
            "LOS 50b: Explain the roll return and its significance for commodity futures investors",
            "LOS 51a: Describe infrastructure investments and their risk-return characteristics",
        ],
        "Portfolio Management": [
            "LOS 52a: Describe the portfolio management process and components of an investment policy statement (IPS)",
            "LOS 52b: Describe the components of risk and return and how risk is measured",
            "LOS 53a: Calculate and interpret the mean, variance, and covariance of a portfolio",
            "LOS 53b: Describe the efficient frontier and identify the optimal portfolio",
            "LOS 53c: Explain the capital allocation line and the capital market line",
            "LOS 54a: Describe the assumptions underlying the CAPM and explain its implications",
            "LOS 54b: Calculate and interpret a security's beta and apply the CAPM to determine expected return",
            "LOS 54c: Identify and explain limitations of the CAPM",
            "LOS 55a: Calculate and interpret the Sharpe ratio, Treynor ratio, and Jensen's alpha",
            "LOS 55b: Explain how to evaluate portfolio performance",
            "LOS 56a: Describe the major types of investor behavioral biases",
            "LOS 56b: Distinguish between cognitive and emotional biases and explain their investment implications",
            "LOS 57a: Describe the components of a strategic asset allocation and tactical asset allocation",
        ],
        "Ethics": [
            "LOS 58a: Describe the six components of the Code of Ethics",
            "LOS 58b: List the seven Standards of Professional Conduct",
            "LOS 59a (Standard I): Describe knowledge of the law and the obligations under Standard I(A)",
            "LOS 59b (Standard I): Describe the requirements of Standards I(B) through I(D) regarding independence, misrepresentation, and misconduct",
            "LOS 60a (Standard II): Describe the requirements of Standard II(A) regarding material nonpublic information",
            "LOS 60b (Standard II): Explain the mosaic theory and its application",
            "LOS 61a (Standard III): Describe the fiduciary duties under Standard III: duties to clients",
            "LOS 61b (Standard III): Distinguish between discretionary and non-discretionary accounts and suitability requirements",
            "LOS 62a (Standard IV): Describe duties to employers under Standards IV(A) through IV(C)",
            "LOS 63a (Standard V): Describe the components of investment analysis, recommendations, and actions under Standard V",
            "LOS 64a (Standard VI): Describe the disclosure requirements under Standard VI regarding conflicts of interest",
            "LOS 65a (Standard VII): Describe the requirements of Standard VII regarding conduct as a member and GIPS",
            "LOS 66a: Describe the key features of the Global Investment Performance Standards (GIPS)",
            "LOS 66b: Explain why GIPS are important and how they are administered",
        ],
    }

    # Return curated if we have them; otherwise use extracted
    curated = curated_los.get(module_name, [])
    if curated:
        return curated
    return extracted if extracted else [f"LOS: Study {module_name} concepts and apply them to investment analysis."]


def process_book(book_key, pdf_path, modules):
    """Process a single book and extract data for its modules."""
    text = extract_pdf_text(pdf_path)
    text = clean_text(text)

    results = {}

    # Split text proportionally among modules if multiple in same book
    # Use section markers or page estimates
    if len(modules) == 1:
        module_texts = [text]
    elif len(modules) == 2:
        # Try to find section break
        mid = len(text) // 2
        # Look for study session headers near the middle
        patterns = [
            r'STUDY SESSION \d+',
            r'TOPIC \d+',
        ]
        split_pos = mid
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches and len(matches) >= 2:
                # Use the middle-ish match
                mid_match = matches[len(matches)//2]
                split_pos = mid_match.start()
                break
        module_texts = [text[:split_pos], text[split_pos:]]
    else:  # 3 modules (Book 5: AI, PM, Ethics)
        third = len(text) // 3
        module_texts = [text[:third], text[third:2*third], text[2*third:]]

    for i, module_name in enumerate(modules):
        mod_text = module_texts[i] if i < len(module_texts) else text

        print(f"  Processing: {module_name}")

        results[module_name] = {
            "summary": build_summary(mod_text, module_name),
            "key_concepts": extract_key_concepts(mod_text, module_name),
            "formulas": extract_formulas(mod_text, module_name),
            "exam_tips": extract_exam_tips(mod_text, module_name),
            "los": build_los_for_module(mod_text, module_name),
        }

    return results


def main():
    print("Finding 2024 SchweserNotes PDFs...")
    pdfs = find_pdfs()
    print(f"Found {len(pdfs)} PDFs: {list(pdfs.keys())}")

    all_modules = {}

    # Special handling: Book 2 has PM,CI but Book 5 also has PM
    # We'll use Book 5's PM as the primary source
    pm_from_book2 = None

    for book_key, pdf_path in sorted(pdfs.items()):
        modules = BOOK_MODULE_MAP[book_key]
        print(f"\nProcessing Book [{book_key}] -> {modules}")

        results = process_book(book_key, pdf_path, modules)

        for module, data in results.items():
            if module == "Portfolio Management" and book_key == "PM,CI":
                pm_from_book2 = data  # Save but don't use yet
                print(f"  Saved PM from Book 2 as backup")
            elif module not in all_modules:
                all_modules[module] = data
            else:
                # Merge: append to existing (for PM appearing in both books)
                existing = all_modules[module]
                new_los = [l for l in data["los"] if l not in existing["los"]]
                existing["los"].extend(new_los)
                new_concepts = [c for c in data["key_concepts"] if c not in existing["key_concepts"]]
                existing["key_concepts"].extend(new_concepts[:5])

    # Ensure all 10 required modules are present
    required_modules = [
        "Quantitative Methods", "Economics", "Corporate Issuers",
        "Financial Statement Analysis", "Equity Investments", "Fixed Income",
        "Derivatives", "Alternative Investments", "Portfolio Management", "Ethics"
    ]

    for mod in required_modules:
        if mod not in all_modules:
            print(f"WARNING: {mod} missing — using curated data")
            all_modules[mod] = {
                "summary": build_summary("", mod),
                "key_concepts": [],
                "formulas": extract_formulas("", mod),
                "exam_tips": extract_exam_tips("", mod),
                "los": build_los_for_module("", mod),
            }

    # Reorder to match required order
    ordered = {mod: all_modules[mod] for mod in required_modules if mod in all_modules}

    # Validate
    print("\nValidating extracted data:")
    for mod, data in ordered.items():
        n_los = len(data["los"])
        n_concepts = len(data["key_concepts"])
        n_formulas = len(data["formulas"])
        n_tips = len(data["exam_tips"])
        print(f"  {mod}: {n_los} LOS, {n_concepts} concepts, {n_formulas} formulas, {n_tips} tips")

    # Save
    output_path = "/Users/joark/cfa-l1-study-tool/data/enhanced_concepts.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")

    return ordered


if __name__ == "__main__":
    main()
