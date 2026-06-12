# Your Investment Plan (Starter Template)

> Educational framework, **not** financial advice. See `DISCLAIMER.md`.
> The `plan` command / MCP `investment_plan` tool fills the live numbers from
> your actual portfolio. This document is the human-readable companion.

## 1. Foundations (do these before buying anything)

- [ ] **Emergency fund**: 3–6 months of expenses in cash/HYSA *outside* the
      brokerage. This is what keeps you from panic-selling in a downturn.
- [ ] **High-interest debt** (credit cards, etc.) paid down — it's a guaranteed
      "return" that beats most market gains.
- [ ] **Goal & horizon written down**: what is this money for, and when do you
      need it? (Retirement in 20 years ≠ a house down payment in 2 years.)

## 2. Pick a risk profile

| Profile | Equities | Bonds | Cash | Alt/Crypto | Typical fit |
|--------------|---------|-------|------|-----------|--------------|
| Conservative | 40% | 45% | 12% | 3% | Short horizon / low tolerance for swings |
| Balanced | 65% | 25% | 5% | 5% | Medium horizon, moderate risk |
| Aggressive | 85% | 3% | 2% | 10% | Long horizon, can stomach big drawdowns |

The tool compares your **current** allocation to the target you pick and shows
the dollar gaps.

## 3. Automate contributions (dollar-cost averaging)

Pick a fixed amount per month and invest it on schedule regardless of headlines.
This removes timing guesswork and is the single highest-leverage habit for most
investors. New money is directed first at your **most underweight** bucket, so
you rebalance by *buying* (tax-friendlier than selling).

## 4. Diversify the core, keep speculation small

- A low-cost broad-market index ETF can be the diversified "core."
- Individual stocks and crypto are the "satellite" — keep any single name and
  the whole speculative sleeve to sizes you could afford to lose.
- Watch single-name concentration: a common personal cap is **10%** per stock.

## 5. Rebalance on a cadence, not on emotion

- Review quarterly, or whenever a bucket drifts more than ~5% from target.
- Prefer rebalancing with new contributions; sell to rebalance only when needed
  (mind taxes on gains).

## 6. Monitoring checklist

- [ ] Single position > 10% of account? Decide: trim or hold (and why).
- [ ] Sector > 40% of invested money? Consider spreading out.
- [ ] Crypto > your chosen cap? Resize.
- [ ] Cash > 30% with no plan for it? Schedule contributions.
- [ ] A holding down >30%? Re-check the original thesis — broken or intact?
- [ ] Annual review: goals, income, risk tolerance still the same?

## 7. How to run the numbers

```bash
python -m rh_advisor.cli plan --risk balanced --monthly 500
```

Or ask Claude (connected via the MCP server) things like:
*"Pull my portfolio, build a balanced plan with $500/month, and walk me through
the biggest gaps and one concrete first step."*
