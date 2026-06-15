"""Local web dashboard (FastAPI).

Run it:
    pip install fastapi uvicorn
    python web/app.py
    # then open http://127.0.0.1:8000

It serves a single-page dashboard (static/index.html) plus a small JSON API
backed by the same Advisor facade the CLI and MCP server use. Trades still go
through propose -> confirm, so nothing is submitted without a second step.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the sibling rh_advisor package importable when run as a script.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rh_advisor.service import Advisor  # noqa: E402

try:
    from fastapi import FastAPI, Body
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:  # pragma: no cover
    raise SystemExit(
        "FastAPI is not installed. Run: pip install fastapi uvicorn"
    )

app = FastAPI(title="Robinhood AI Advisor", docs_url="/api/docs")
_STATIC = Path(__file__).resolve().parent / "static"


def advisor() -> Advisor:
    return Advisor()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/api/portfolio")
def api_portfolio():
    return advisor().portfolio()


@app.get("/api/metrics")
def api_metrics():
    return advisor().metrics()


@app.get("/api/tips")
def api_tips():
    return advisor().tips()


@app.get("/api/plan")
def api_plan(risk: str = "balanced", monthly: float = 0.0):
    return advisor().plan(risk, monthly)


@app.post("/api/propose")
def api_propose(payload: dict = Body(...)):
    try:
        return advisor().propose_trade(
            symbol=payload["symbol"],
            side=payload["side"],
            amount_usd=payload.get("amount_usd"),
            quantity=payload.get("quantity"),
            asset_type=payload.get("asset_type", "stock"),
        )
    except (KeyError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/api/confirm")
def api_confirm(payload: dict = Body(...)):
    try:
        return advisor().confirm_trade(payload["token"])
    except (KeyError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


# Mount any extra static assets under /static (index.html is served at /).
if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
