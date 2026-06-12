"""Rules-based tips engine (the offline "AI brain").

These are *observations and educational prompts*, not financial advice. Every
tip is derived deterministically from the metrics so you can see exactly why it
fired. The richer, conversational analysis comes from attaching Claude through
the MCP server — this engine guarantees something useful even offline.
"""

from __future__ import annotations

from dataclasses import dataclass

from .metrics import PortfolioMetrics

# Tunable thresholds, gathered in one place so they are easy to audit/adjust.
TOP_HOLDING_WARN = 0.25       # any single position above 25% of the account
SECTOR_WARN = 0.40            # any single sector above 40% of invested money
CASH_DRAG_WARN = 0.30         # more than 30% sitting in cash
CASH_BUFFER_LOW = 0.02        # less than 2% cash = no dry powder
CRYPTO_WARN = 0.20            # crypto above 20% of the account
FEW_POSITIONS = 5            # fewer than 5 holdings = thin diversification
BIG_LOSER = -0.30            # a position down more than 30%
BIG_WINNER = 0.60            # a position up more than 60% (trim-to-target prompt)


@dataclass
class Tip:
    severity: str     # "info" | "suggestion" | "warning"
    category: str     # "concentration" | "diversification" | "cash" | "risk" | "positive"
    title: str
    detail: str

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
        }


def generate_tips(m: PortfolioMetrics) -> list[Tip]:
    tips: list[Tip] = []

    if m.total_value <= 0:
        return [Tip("info", "info", "Empty account",
                    "No holdings or cash detected yet. Fund the account to get tailored tips.")]

    # --- concentration in a single name ------------------------------------
    if m.top_holding_pct >= TOP_HOLDING_WARN:
        tips.append(Tip(
            "warning", "concentration",
            f"{m.top_holding_symbol} is {m.top_holding_pct:.0%} of your account",
            f"A single position above {TOP_HOLDING_WARN:.0%} means your results "
            f"ride heavily on one company. Many investors cap single names near "
            f"5–10%. Consider whether you'd be comfortable if {m.top_holding_symbol} "
            f"dropped 30% tomorrow.",
        ))

    # --- overall concentration (HHI) ---------------------------------------
    if m.concentration_hhi >= 0.25 and m.num_positions >= 2:
        tips.append(Tip(
            "suggestion", "concentration",
            "Your holdings are concentrated",
            f"Concentration index (HHI) is {m.concentration_hhi:.2f}; below ~0.15 is "
            f"generally considered well-spread. Adding positions or trimming the "
            f"largest one would lower single-bet risk.",
        ))

    # --- breadth ------------------------------------------------------------
    if m.num_positions and m.num_positions < FEW_POSITIONS and m.invested_equity > 0:
        tips.append(Tip(
            "suggestion", "diversification",
            f"Only {m.num_positions} holding(s)",
            "A low-cost, broad index ETF (e.g., a total-market or S&P 500 fund) is "
            "a common way to get instant diversification without picking many names.",
        ))

    # --- sector concentration ----------------------------------------------
    for sector, pct in m.sector_allocation.items():
        if sector not in {"Unknown", "Crypto"} and pct >= SECTOR_WARN:
            tips.append(Tip(
                "warning", "diversification",
                f"{pct:.0%} of invested money is in {sector}",
                f"Heavy exposure to one sector ({sector}) means a sector-wide "
                f"downturn hits most of your portfolio at once. Spreading across "
                f"sectors smooths that out.",
            ))
            break

    # --- cash position ------------------------------------------------------
    if m.cash_pct >= CASH_DRAG_WARN:
        tips.append(Tip(
            "suggestion", "cash",
            f"{m.cash_pct:.0%} of the account is uninvested cash",
            "Cash is safe but can be a drag over long horizons. If this isn't your "
            "emergency buffer, a steady dollar-cost-averaging schedule puts idle "
            "cash to work without trying to time the market.",
        ))
    elif 0 < m.cash_pct < CASH_BUFFER_LOW:
        tips.append(Tip(
            "info", "cash",
            "Almost no cash buffer",
            "You're nearly fully invested. Keeping a little dry powder (and a "
            "separate emergency fund) helps you avoid forced selling at bad times.",
        ))

    # --- crypto volatility --------------------------------------------------
    if m.crypto_pct >= CRYPTO_WARN:
        tips.append(Tip(
            "warning", "risk",
            f"Crypto is {m.crypto_pct:.0%} of your account",
            "Crypto is far more volatile than broad equities. Many people keep "
            "speculative assets to a small slice (often <10%) they can afford to "
            "lose. Size it to your risk tolerance.",
        ))

    # --- individual position movers ----------------------------------------
    for w in m.weights:
        if w.unrealized_gain_pct <= BIG_LOSER:
            tips.append(Tip(
                "info", "risk",
                f"{w.symbol} is down {abs(w.unrealized_gain_pct):.0%}",
                "Not a sell signal — just a flag to revisit your original reason "
                "for buying. If the thesis still holds, a drawdown alone isn't a "
                "reason to act; if it's broken, that's worth knowing.",
            ))
        elif w.unrealized_gain_pct >= BIG_WINNER and w.weight >= 0.10:
            tips.append(Tip(
                "suggestion", "concentration",
                f"{w.symbol} is up {w.unrealized_gain_pct:.0%} and now {w.weight:.0%} of the account",
                "Winners can quietly grow into an outsized bet. Some investors "
                "periodically trim back to a target weight to lock in gains and "
                "rebalance.",
            ))

    # --- positive reinforcement --------------------------------------------
    if m.diversification_score >= 70 and m.top_holding_pct < TOP_HOLDING_WARN:
        tips.append(Tip(
            "info", "positive",
            "Solid diversification",
            f"Diversification score {m.diversification_score:.0f}/100 with no single "
            f"position dominating. Keep contributions regular and review periodically.",
        ))

    if not tips:
        tips.append(Tip(
            "info", "positive", "No red flags detected",
            "Nothing in the rules engine stands out. Attach Claude via the MCP "
            "server for a deeper, conversational review.",
        ))

    return tips
