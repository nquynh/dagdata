import argparse
import pandas as pd
import yfinance as yf


def fetch_data(ticker: str = "HPG"):  # default ticker HPG
    """Download price history and financial statements using yfinance."""
    # Many Vietnamese stocks are available with '.VN' suffix on Yahoo Finance
    symbol = ticker if ticker.endswith(".VN") else f"{ticker}.VN"
    stock = yf.Ticker(symbol)

    history = stock.history(period="5y")
    info = stock.info
    financials = stock.quarterly_financials
    balance_sheet = stock.quarterly_balance_sheet
    cashflow = stock.quarterly_cashflow

    return history, info, financials, balance_sheet, cashflow


def calculate_metrics(price: float, info: dict, financials: pd.DataFrame,
                      balance_sheet: pd.DataFrame) -> dict:
    """Compute P/E, ROE and EPS growth."""
    metrics = {}

    eps = info.get("trailingEps") or info.get("epsTrailingTwelveMonths")
    metrics["PE"] = price / eps if eps else None

    try:
        net_income = financials.loc["Net Income"].iloc[0]
        equity = balance_sheet.loc["Total Stockholder Equity"].iloc[0]
        metrics["ROE"] = net_income / equity
    except Exception:
        metrics["ROE"] = None

    try:
        eps_curr = financials.loc["Diluted EPS"].iloc[0]
        eps_prev = financials.loc["Diluted EPS"].iloc[1]
        metrics["EPS_Growth"] = (eps_curr - eps_prev) / eps_prev
    except Exception:
        metrics["EPS_Growth"] = None

    return metrics


def discounted_cash_flow(cashflows: pd.Series, discount: float = 0.1,
                         perpetual_growth: float = 0.02) -> float:
    """Simple DCF valuation using free cash flow series."""
    n = len(cashflows)
    pv = sum(cf / (1 + discount) ** (i + 1) for i, cf in enumerate(cashflows))
    terminal = cashflows.iloc[-1] * (1 + perpetual_growth) / (
        discount - perpetual_growth
    )
    pv_terminal = terminal / (1 + discount) ** n
    return pv + pv_terminal


def summarize(ticker: str, metrics: dict, dcf_value: float):
    print(f"Summary for {ticker}:\n")
    print(f"P/E Ratio: {metrics.get('PE'):.2f}" if metrics.get('PE') else "P/E Ratio: N/A")
    if metrics.get("ROE") is not None:
        print(f"ROE: {metrics['ROE']:.2%}")
    else:
        print("ROE: N/A")
    if metrics.get("EPS_Growth") is not None:
        print(f"EPS Growth: {metrics['EPS_Growth']:.2%}")
    else:
        print("EPS Growth: N/A")
    print(f"DCF estimated value per share: {dcf_value:.2f}\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze HPG stock")
    parser.add_argument("--ticker", default="HPG", help="Ticker symbol, default HPG")
    parser.add_argument(
        "--discount", type=float, default=0.1, help="Discount rate for DCF"
    )
    parser.add_argument(
        "--growth", type=float, default=0.02, help="Perpetual growth rate"
    )
    args = parser.parse_args()

    history, info, financials, balance_sheet, cashflow = fetch_data(args.ticker)

    last_price = history["Close"].iloc[-1]
    metrics = calculate_metrics(last_price, info, financials, balance_sheet)

    try:
        fcf = (
            cashflow.loc["Total Cash From Operating Activities"]
            + cashflow.loc["Capital Expenditures"]
        )
        dcf_value = discounted_cash_flow(fcf, args.discount, args.growth)
    except Exception:
        dcf_value = float("nan")

    summarize(args.ticker, metrics, dcf_value)


if __name__ == "__main__":
    main()
