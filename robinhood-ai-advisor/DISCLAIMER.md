# Important Disclaimer

**This software is an educational tool. It is NOT financial advice.**

- It does **not** recommend specific securities, predict prices, or guarantee
  any outcome. The "tips" are deterministic observations about diversification,
  concentration, cash, and risk — prompts for *you* to think, not instructions.
- All investing involves risk, **including loss of principal**. Past
  performance does not guarantee future results.
- You are solely responsible for every order you confirm. Always do your own
  due diligence and consider consulting a licensed financial professional.

## About the Robinhood connection

There are two ways to connect, with different risk profiles:

1. **Official Robinhood Agentic Trading MCP** (recommended) —
   `https://agent.robinhood.com/mcp/trading`. Robinhood's own hosted server,
   authorized via OAuth to a dedicated agentic account, with a broker-side kill
   switch and per-trade notifications. This is the supported, sanctioned path.
   See [`ROBINHOOD_AGENTIC.md`](ROBINHOOD_AGENTIC.md). Agentic Trading is itself
   a real brokerage product — review Robinhood's terms and start small.
2. **`robin_stocks` (unofficial)** — the community
   [`robin_stocks`](https://github.com/jmfernandes/robin_stocks) library
   automates Robinhood's private API using your credentials. It can break
   without notice and automating account access may carry risks (including, in
   principle, to your account standing). Use at your own risk. Your credentials
   live only in your local `.env` (git-ignored) and are sent only to
   Robinhood's own login endpoint by `robin_stocks`.

## Trade safety model

1. **Nothing trades in one step.** Every order is `propose` → `confirm` with a
   one-time token that expires in 5 minutes.
2. **Live trading is off by default.** Orders only reach the broker when
   `RH_ADVISOR_ALLOW_LIVE_TRADES=yes` **and** `RH_ADVISOR_BROKER=robinhood`.
   Otherwise everything is simulated (dry-run).
3. **Per-order ceiling.** Proposals above `RH_ADVISOR_MAX_ORDER_USD` are flagged.

By using this software you accept these terms and all associated risk.
