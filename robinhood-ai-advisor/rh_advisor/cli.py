"""Command-line interface for the Robinhood AI Advisor.

Examples
--------
    python -m rh_advisor.cli summary
    python -m rh_advisor.cli tips
    python -m rh_advisor.cli plan --risk balanced --monthly 500
    python -m rh_advisor.cli propose --symbol VOO --side buy --usd 200
    python -m rh_advisor.cli confirm --token a1b2c3d4

By default it uses the offline demo portfolio. Set RH_ADVISOR_BROKER=robinhood
(in your .env) to use your real account.
"""

from __future__ import annotations

import argparse
import sys

from .service import Advisor

BANNER = "Robinhood AI Advisor — educational tool, NOT financial advice."


def _money(x: float) -> str:
    return f"${x:,.2f}"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def cmd_summary(advisor: Advisor, _args) -> int:
    p = advisor.portfolio()
    print(BANNER)
    print(f"\nAccount: {p['account_label']}  (broker={p['broker']}, "
          f"live_trading={'ARMED' if p['live_trading_armed'] else 'off'})")
    print(f"Total value: {_money(p['total_value'])}   Cash: {_money(p['cash'])}\n")
    print(f"{'SYMBOL':<8}{'QTY':>10}{'PRICE':>12}{'VALUE':>14}{'GAIN%':>10}  SECTOR")
    print("-" * 72)
    for pos in p["positions"]:
        print(f"{pos['symbol']:<8}{pos['quantity']:>10g}{_money(pos['price']):>12}"
              f"{_money(pos['equity']):>14}{_pct(pos['unrealized_gain_pct']):>10}  {pos['sector']}")
    return 0


def cmd_metrics(advisor: Advisor, _args) -> int:
    m = advisor.metrics()
    print(BANNER + "\n")
    print(f"Total value:          {_money(m['total_value'])}")
    print(f"Invested / Cash:      {_money(m['invested_equity'])} / {_money(m['cash'])} "
          f"({_pct(m['cash_pct'])} cash)")
    print(f"Positions:            {m['num_positions']}")
    print(f"Top holding:          {m['top_holding_symbol']} at {_pct(m['top_holding_pct'])}")
    print(f"Concentration (HHI):  {m['concentration_hhi']:.3f}")
    print(f"Crypto exposure:      {_pct(m['crypto_pct'])}")
    print(f"Unrealized gain:      {_money(m['total_unrealized_gain'])} "
          f"({_pct(m['total_unrealized_gain_pct'])})")
    print(f"Diversification:      {m['diversification_score']:.0f}/100")
    print("\nSector allocation (of invested):")
    for sector, pct in m["sector_allocation"].items():
        print(f"  {sector:<22}{_pct(pct)}")
    return 0


def cmd_tips(advisor: Advisor, _args) -> int:
    print(BANNER + "\n")
    icons = {"warning": "⚠️ ", "suggestion": "💡", "info": "ℹ️ "}
    for t in advisor.tips():
        print(f"{icons.get(t['severity'], '•')} [{t['category']}] {t['title']}")
        print(f"    {t['detail']}\n")
    print("Tips are educational observations, not financial advice.")
    return 0


def cmd_plan(advisor: Advisor, args) -> int:
    plan = advisor.plan(args.risk, args.monthly)
    print(BANNER + "\n")
    print(f"Investment plan — {plan['risk_profile']} profile, "
          f"{_money(plan['monthly_contribution'])}/mo contribution\n")
    print(f"{'BUCKET':<12}{'CURRENT':>12}{'TARGET':>12}{'GAP ($)':>14}")
    print("-" * 50)
    for r in plan["rows"]:
        print(f"{r['bucket']:<12}{_pct(r['current_pct']):>12}{_pct(r['target_pct']):>12}"
              f"{_money(r['gap_usd']):>14}")
    if plan["contribution_split"]:
        print("\nSuggested split of new monthly money:")
        for bucket, amt in plan["contribution_split"].items():
            print(f"  {bucket:<12}{_money(amt)}")
    print("\nAction checklist:")
    for i, action in enumerate(plan["actions"], 1):
        print(f"  {i}. {action}")
    return 0


def cmd_propose(advisor: Advisor, args) -> int:
    try:
        proposal = advisor.propose_trade(
            symbol=args.symbol, side=args.side,
            amount_usd=args.usd, quantity=args.shares,
            asset_type=args.asset_type,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(BANNER + "\n")
    print(proposal["summary"])
    if proposal["warnings"]:
        print("\nWarnings:")
        for w in proposal["warnings"]:
            print(f"  ! {w}")
    print(f"\nTo execute:  python -m rh_advisor.cli confirm --token {proposal['token']}")
    return 0


def cmd_confirm(advisor: Advisor, args) -> int:
    try:
        result = advisor.confirm_trade(args.token)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    status = "ACCEPTED" if result["accepted"] else "NOT submitted"
    mode = "DRY-RUN" if result["dry_run"] else "LIVE"
    print(f"[{mode}] {status}: {result['detail']}")
    if result["broker_order_id"]:
        print(f"Broker order id: {result['broker_order_id']}")
    return 0 if result["accepted"] or result["dry_run"] else 1


def cmd_pending(advisor: Advisor, _args) -> int:
    pending = advisor.pending_trade()
    if not pending:
        print("No pending proposal.")
        return 0
    print(pending["summary"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rh-advisor", description=BANNER)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary", help="Show holdings table").set_defaults(func=cmd_summary)
    sub.add_parser("metrics", help="Show risk/diversification metrics").set_defaults(func=cmd_metrics)
    sub.add_parser("tips", help="Show educational tips").set_defaults(func=cmd_tips)

    p_plan = sub.add_parser("plan", help="Generate an investment plan")
    p_plan.add_argument("--risk", choices=["conservative", "balanced", "aggressive"], default=None)
    p_plan.add_argument("--monthly", type=float, default=None, help="Monthly contribution in USD")
    p_plan.set_defaults(func=cmd_plan)

    p_prop = sub.add_parser("propose", help="Propose a trade (does NOT submit)")
    p_prop.add_argument("--symbol", required=True)
    p_prop.add_argument("--side", required=True, choices=["buy", "sell"])
    p_prop.add_argument("--usd", type=float, default=None, help="Dollar amount")
    p_prop.add_argument("--shares", type=float, default=None, help="Share/unit quantity")
    p_prop.add_argument("--asset-type", default="stock", choices=["stock", "crypto"])
    p_prop.set_defaults(func=cmd_propose)

    p_conf = sub.add_parser("confirm", help="Confirm & submit a proposed trade")
    p_conf.add_argument("--token", required=True)
    p_conf.set_defaults(func=cmd_confirm)

    sub.add_parser("pending", help="Show the current pending proposal").set_defaults(func=cmd_pending)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    advisor = Advisor()
    return args.func(advisor, args)


if __name__ == "__main__":
    raise SystemExit(main())
