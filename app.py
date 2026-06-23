from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup

st.set_page_config(page_title="역발상 매수 레이더", layout="wide")

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


SECTORS_PATH = Path(__file__).with_name("sectors.json")
CATEGORY_MAP = {
    "🖥️ 반도체 밸류체인": [
        "Semi_Fabless",
        "Semi_Foundry",
        "Semi_IDM",
        "Semi_OSAT_Substrate",
        "Semi_Equipment",
    ],
    "🤖 AI & 소프트웨어": [
        "AI_Infrastructure_Cloud",
        "AI_Hardware_Server",
        "AI_Power_Cooling",
        "AI_Data_Platform",
        "AI_Service_SaaS",
    ],
    "🔋 에너지 & 원자력": [
        "Energy_Integrated",
        "Energy_Midstream",
        "Energy_Downstream",
        "Energy_Utility_Power",
        "Energy_Nuclear_Uranium",
    ],
    "🧬 헬스케어 & 바이오": [
        "Healthcare_Service_Platform",
        "Healthcare_Pharma",
        "Healthcare_Devices",
        "Healthcare_Tools_Service",
    ],
    "🛒 필수소비재": [
        "Staples_Food_Beverage",
        "Staples_Household",
        "Staples_Tobacco",
        "Staples_Retail",
    ],
    "🏦 금융": [
        "Financials_Commercial",
        "Financials_IB_Asset",
        "Financials_Payments",
    ],
    "🥇 원자재 & 리츠": [
        "Metals_Mining",
        "Metals_Royalty",
        "Metals_ETF",
        "REITs_Portfolio",
    ],
    "🚀 산업재 & 레저": [
        "Gaming_Entertainment",
        "Aerospace_Defense",
        "Travel_Leisure",
        "Industrials_Infra",
    ],
}
THEME_KOR_MAP = {
    "Semi_Fabless": "반도체 팹리스",
    "Semi_Foundry": "반도체 파운드리",
    "Semi_IDM": "종합 반도체",
    "Semi_OSAT_Substrate": "반도체 후공정·기판",
    "Semi_Equipment": "반도체 장비",
    "AI_Infrastructure_Cloud": "AI 인프라·클라우드",
    "AI_Hardware_Server": "AI 하드웨어·서버",
    "AI_Power_Cooling": "AI 전력·냉각",
    "AI_Data_Platform": "AI 데이터 플랫폼",
    "AI_Service_SaaS": "AI 서비스·SaaS",
    "REITs_Portfolio": "리츠 포트폴리오",
    "Metals_Mining": "금속·광산",
    "Metals_Royalty": "금속 로열티",
    "Metals_ETF": "금속 ETF",
    "Staples_Food_Beverage": "필수소비재 식음료",
    "Staples_Household": "필수소비재 생활용품",
    "Staples_Tobacco": "필수소비재 담배",
    "Staples_Retail": "필수소비재 유통",
    "Financials_Commercial": "상업은행",
    "Financials_IB_Asset": "투자은행·자산운용",
    "Financials_Payments": "결제 네트워크",
    "Healthcare_Service_Platform": "헬스케어 서비스·플랫폼",
    "Healthcare_Pharma": "제약",
    "Healthcare_Devices": "의료기기",
    "Healthcare_Tools_Service": "바이오 장비·위탁서비스",
    "Energy_Integrated": "종합 에너지",
    "Energy_Midstream": "에너지 미드스트림",
    "Energy_Downstream": "정유·다운스트림",
    "Energy_Utility_Power": "전력·유틸리티",
    "Energy_Nuclear_Uranium": "원자력·우라늄",
    "Gaming_Entertainment": "게임·엔터테인먼트",
    "Aerospace_Defense": "항공우주·방산",
    "Travel_Leisure": "여행·레저",
    "Industrials_Infra": "산업재·인프라",
}
COMPANY_NAME_MAP = {
    "000100.KS": "유한양행",
    "000660.KS": "SK하이닉스",
    "000990.KS": "DB하이텍",
    "005930.KS": "삼성전자",
    "010950.KS": "S-Oil",
    "012450.KS": "한화에어로스페이스",
    "015760.KS": "한국전력",
    "034020.KS": "두산에너빌리티",
    "042700.KS": "한미반도체",
    "068270.KS": "셀트리온",
    "096770.KS": "SK이노베이션",
    "097520.KQ": "엠씨넥스",
    "145720.KS": "덴티움",
    "207940.KS": "삼성바이오로직스",
    "214150.KQ": "클래시스",
    "328130.KQ": "루닛",
    "353200.KS": "대덕전자",
}
finance_kor_dict = {
    "Total Revenue": "매출액",
    "Cost Of Revenue": "매출원가",
    "Gross Profit": "매출총이익",
    "Operating Expense": "영업비용(판관비 등)",
    "Operating Income": "영업이익",
    "Net Income": "당기순이익",
    "EBITDA": "EBITDA (세전·이자지급전이익)",
    "Total Assets": "자산총계",
    "Total Liabilities Net Minority Interest": "부채총계",
    "Total Equity Gross Minority Interest": "자본총계",
    "Stockholders Equity": "주주자본",
    "Retained Earnings": "이익잉여금",
    "Cash And Cash Equivalents": "현금 및 현금성 자산",
    "Operating Cash Flow": "영업활동 현금흐름",
    "Investing Cash Flow": "투자활동 현금흐름",
    "Financing Cash Flow": "재무활동 현금흐름",
    "Free Cash Flow": "잉여현금흐름(FCF)",
}
TOP_THEME_PEERS = {
    "Semi_Fabless": ["AMD", "AVGO", "QCOM", "MRVL", "ARM"],
    "Semi_Foundry": ["TSM", "GFS", "UMC", "INTC", "005930.KS"],
    "Semi_IDM": ["005930.KS", "000660.KS", "MU", "INTC", "TXN"],
    "Semi_OSAT_Substrate": ["AMKR", "ASX", "3711.TW", "353200.KS", "009150.KS"],
    "Semi_Equipment": ["ASML", "AMAT", "LRCX", "KLAC", "TEL"],
    "AI_Infrastructure_Cloud": ["MSFT", "GOOGL", "AMZN", "META", "ORCL"],
    "AI_Hardware_Server": ["AVGO", "SMCI", "DELL", "HPE", "ANET"],
    "AI_Power_Cooling": ["VRT", "ETN", "TT", "JCI", "CARR"],
    "AI_Data_Platform": ["PLTR", "SNOW", "DDOG", "MDB", "NET"],
    "AI_Service_SaaS": ["NOW", "CRM", "ADBE", "WDAY", "INTU"],
    "REITs_Portfolio": ["EQIX", "PLD", "O", "AMT", "VICI"],
    "Metals_Mining": ["NEM", "PAAS", "FCX", "GOLD", "AEM"],
    "Metals_Royalty": ["FNV", "WPM", "RGLD", "TFPM", "SAND"],
    "Metals_ETF": ["GLD", "SLV", "CPER", "IAU", "GDX"],
    "Staples_Food_Beverage": ["KO", "PEP", "MDLZ", "KDP", "MNST"],
    "Staples_Household": ["PG", "CL", "KMB", "CHD", "CLX"],
    "Staples_Tobacco": ["PM", "MO", "BTI", "IMBBY", "JAPAF"],
    "Staples_Retail": ["WMT", "COST", "TGT", "KR", "DG"],
    "Financials_Commercial": ["JPM", "BAC", "WFC", "C", "USB"],
    "Financials_IB_Asset": ["MS", "GS", "BLK", "BX", "KKR"],
    "Financials_Payments": ["V", "MA", "AXP", "PYPL", "FI"],
    "Healthcare_Service_Platform": ["UNH", "ELV", "CI", "HUM", "CNC"],
    "Healthcare_Pharma": ["JNJ", "LLY", "MRK", "PFE", "ABBV"],
    "Healthcare_Devices": ["ISRG", "MDT", "SYK", "BSX", "ABT"],
    "Healthcare_Tools_Service": ["TMO", "DHR", "A", "IQV", "WAT"],
    "Energy_Integrated": ["XOM", "CVX", "SHEL", "TTE", "BP"],
    "Energy_Midstream": ["ENB", "EPD", "KMI", "WMB", "TRP"],
    "Energy_Downstream": ["VLO", "MPC", "PSX", "DK", "PBF"],
    "Energy_Utility_Power": ["NEE", "SO", "DUK", "AEP", "EXC"],
    "Energy_Nuclear_Uranium": ["CEG", "VST", "CCJ", "UEC", "LEU"],
    "Gaming_Entertainment": ["TTWO", "RBLX", "EA", "SONY", "NTDOY"],
    "Aerospace_Defense": ["LMT", "RTX", "NOC", "GD", "BA"],
    "Travel_Leisure": ["BKNG", "MAR", "HLT", "ABNB", "EXPE"],
    "Industrials_Infra": ["CAT", "DE", "HON", "GE", "ETN"],
}


def load_sectors() -> dict[str, list[str]]:
    with SECTORS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def format_theme_name(theme: str) -> str:
    return THEME_KOR_MAP.get(theme, theme)


def format_ticker_name(ticker: str) -> str:
    return COMPANY_NAME_MAP.get(ticker, ticker)


def format_ticker_label(ticker: str) -> str:
    company_name = format_ticker_name(ticker)
    return f"{company_name} ({ticker})" if company_name != ticker else ticker


def flatten_tickers(sectors: dict[str, list[str]]) -> list[dict[str, str]]:
    return [
        {
            "label": f"{format_ticker_label(ticker)} | {format_theme_name(theme)}",
            "ticker": ticker,
            "theme": theme,
        }
        for theme, tickers in sectors.items()
        for ticker in tickers
    ]


def find_category_for_theme(theme: str) -> str:
    for category, themes in CATEGORY_MAP.items():
        if theme in themes:
            return category
    return next(iter(CATEGORY_MAP))


def get_available_themes(category: str, sectors: dict[str, list[str]]) -> list[str]:
    return [theme for theme in CATEGORY_MAP[category] if theme in sectors]


def dedupe_tickers(tickers: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for ticker in tickers:
        normalized = ticker.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def get_default_top_peer_tickers(
    ticker: str,
    selected_theme: str,
    sectors: dict[str, list[str]],
) -> list[str]:
    candidates = TOP_THEME_PEERS.get(selected_theme, []) + sectors.get(selected_theme, [])
    return [
        peer_ticker
        for peer_ticker in dedupe_tickers(candidates)
        if peer_ticker != ticker.upper()
    ][:5]


def parse_peer_ticker_input(peer_input: str, ticker: str) -> list[str]:
    raw_tickers = peer_input.replace("\n", ",").replace(" ", ",").split(",")
    return [
        peer_ticker
        for peer_ticker in dedupe_tickers(raw_tickers)
        if peer_ticker != ticker.upper()
    ][:5]


def build_google_peer_search_url(selected_theme: str) -> str:
    query = f"{format_theme_name(selected_theme)} {selected_theme} top 5 public companies stock tickers"
    return f"https://www.google.com/search?q={quote_plus(query)}"


def safe_number(value) -> float | None:
    if value in (None, "N/A", "n/a", "-", ""):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number != number:
        return None

    return number


def normalize_yield(value: float | None) -> float | None:
    if value is None:
        return None

    return value / 100 if value > 0.2 else value


def apply_design_system_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --brand-primary: #cc785c;
            --brand-primary-active: #a9583e;
            --brand-ink: #141413;
            --brand-body: #3d3d3a;
            --brand-muted: #6c6a64;
            --brand-hairline: #e6dfd8;
            --brand-canvas: #faf9f5;
            --brand-surface-soft: #f5f0e8;
            --brand-surface-card: #efe9de;
            --brand-surface-strong: #e8e0d2;
            --brand-dark: #181715;
            --brand-dark-elevated: #252320;
            --brand-on-dark: #faf9f5;
            --brand-on-dark-soft: #a09d96;
            --brand-teal: #5db8a6;
            --brand-amber: #e8a55a;
            --brand-error: #c64545;
        }

        .stApp {
            background: var(--brand-canvas);
            color: var(--brand-body);
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .block-container {
            max-width: 1500px;
            padding-top: 3rem;
            padding-bottom: 4rem;
        }

        section[data-testid="stSidebar"] {
            background: var(--brand-dark);
            border-right: 1px solid var(--brand-dark-elevated);
        }

        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] * {
            color: var(--brand-on-dark) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] .stCaptionContainer {
            color: var(--brand-on-dark-soft) !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
        section[data-testid="stSidebar"] [role="radiogroup"] label {
            background: var(--brand-dark-elevated) !important;
            border-color: #34312c;
            border-radius: 8px;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"],
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
        section[data-testid="stSidebar"] div[data-baseweb="select"] div {
            background-color: var(--brand-dark-elevated) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stTextInput"] input,
        section[data-testid="stSidebar"] [data-testid="stTextInput"] div {
            background-color: var(--brand-dark-elevated) !important;
            color: var(--brand-on-dark) !important;
            border-color: #34312c !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] span,
        section[data-testid="stSidebar"] div[data-baseweb="select"] input,
        section[data-testid="stSidebar"] div[data-baseweb="select"] svg,
        section[data-testid="stSidebar"] [role="radiogroup"] p,
        section[data-testid="stSidebar"] [role="radiogroup"] span,
        section[data-testid="stSidebar"] label p {
            color: var(--brand-on-dark) !important;
            fill: var(--brand-on-dark) !important;
        }

        div[data-baseweb="popover"] ul,
        div[data-baseweb="popover"] li,
        div[data-baseweb="menu"],
        div[role="listbox"] {
            background: var(--brand-canvas) !important;
            color: var(--brand-ink) !important;
        }

        div[data-baseweb="popover"] li,
        div[role="option"],
        div[role="option"] *,
        div[data-baseweb="menu"] * {
            color: var(--brand-ink) !important;
        }

        div[role="option"]:hover,
        div[role="option"][aria-selected="true"] {
            background: var(--brand-surface-card) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] {
            background: var(--brand-dark-elevated);
            border: 1px solid #34312c;
            border-radius: 12px;
        }

        h1, h2, h3, h4,
        [data-testid="stHeading"] h1,
        [data-testid="stHeading"] h2,
        [data-testid="stHeading"] h3 {
            color: var(--brand-ink);
            font-family: Georgia, "Times New Roman", serif !important;
            font-weight: 400 !important;
            letter-spacing: 0 !important;
        }

        h1,
        [data-testid="stHeading"] h1 {
            font-size: clamp(2.4rem, 4.8vw, 4rem) !important;
            line-height: 1.06 !important;
            margin-bottom: 1.5rem;
        }

        h2, h3,
        [data-testid="stHeading"] h2,
        [data-testid="stHeading"] h3 {
            line-height: 1.15 !important;
        }

        p, li, label, [data-testid="stCaptionContainer"] {
            color: var(--brand-body);
            letter-spacing: 0;
        }

        a {
            color: var(--brand-primary);
            text-decoration-color: rgba(204, 120, 92, 0.45);
        }

        a:hover {
            color: var(--brand-primary-active);
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stRadio"] label {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--brand-body-strong, #252523);
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 3.1rem;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background: var(--brand-surface-soft);
            border: 1px solid var(--brand-hairline);
            border-radius: 8px;
        }

        [data-testid="stMetric"] {
            background: var(--brand-surface-card);
            border: 1px solid var(--brand-hairline);
            border-radius: 12px;
            padding: 1.35rem 1.5rem;
        }

        [data-testid="stMetricLabel"] p {
            color: var(--brand-muted);
            font-size: 0.82rem;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--brand-ink);
            font-family: Georgia, "Times New Roman", serif;
            font-weight: 400;
        }

        [data-testid="stMetricDelta"] {
            color: var(--brand-muted);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
            background: var(--brand-surface-soft);
            border: 1px solid var(--brand-hairline);
            border-radius: 12px;
            padding: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: var(--brand-muted);
            font-weight: 600;
            padding: 0.7rem 1rem;
        }

        .stTabs [aria-selected="true"] {
            background: var(--brand-surface-card);
            color: var(--brand-ink);
        }

        .stButton > button,
        .stDownloadButton > button {
            background: var(--brand-primary);
            border: 1px solid var(--brand-primary);
            border-radius: 8px;
            color: #ffffff;
            font-weight: 600;
            min-height: 40px;
            padding: 0.7rem 1.2rem;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: var(--brand-primary-active);
            border-color: var(--brand-primary-active);
            color: #ffffff;
        }

        [data-testid="stAlert"] {
            background: var(--brand-surface-card);
            border: 1px solid var(--brand-hairline);
            border-radius: 12px;
            color: var(--brand-body);
        }

        [data-testid="stDataFrame"] {
            background: var(--brand-surface-soft);
            border: 1px solid var(--brand-hairline);
            border-radius: 12px;
            padding: 0.25rem;
        }

        [data-testid="stPlotlyChart"] {
            background: var(--brand-surface-soft);
            border: 1px solid var(--brand-hairline);
            border-radius: 12px;
            padding: 1rem;
        }

        hr {
            border-color: var(--brand-hairline);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_price_data(ticker: str):
    try:
        data = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception as exc:
        st.error(f"{ticker} 주가 데이터를 불러오지 못했습니다: {exc}")
        return None

    if data.empty:
        st.warning(f"{ticker}의 최근 3년 일봉 데이터가 비어 있습니다.")
        return None

    return data


@st.cache_data
def load_ticker_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


def extract_valuation_metrics(info: dict) -> dict[str, float | None]:
    trailing_pe = safe_number(info.get("trailingPE"))
    forward_pe = safe_number(info.get("forwardPE"))

    return {
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
        "per": trailing_pe if trailing_pe is not None else forward_pe,
        "pbr": safe_number(info.get("priceToBook")),
        "roe": safe_number(info.get("returnOnEquity")),
        "dividend_yield": normalize_yield(safe_number(info.get("dividendYield"))),
    }


@st.cache_data
def load_theme_valuation_average(tickers: tuple[str, ...]) -> dict[str, dict[str, float | int | None]]:
    values: dict[str, list[float]] = {
        "per": [],
        "trailing_pe": [],
        "forward_pe": [],
        "pbr": [],
        "roe": [],
        "dividend_yield": [],
    }

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info or {}
            metrics = extract_valuation_metrics(info)
        except Exception:
            continue

        for key, value in metrics.items():
            if value is not None:
                values[key].append(value)

    return {
        key: {
            "average": sum(metric_values) / len(metric_values) if metric_values else None,
            "count": len(metric_values),
        }
        for key, metric_values in values.items()
    }


@st.cache_data
def load_financial_statements(ticker: str):
    try:
        stock = yf.Ticker(ticker)
    except Exception:
        return {}

    statements = {}
    for key, attribute in {
        "income_statement": "financials",
        "balance_sheet": "balance_sheet",
        "cashflow": "cashflow",
    }.items():
        try:
            statements[key] = getattr(stock, attribute)
        except Exception:
            statements[key] = None

    return statements


def format_ratio(value: float | None, suffix: str = "x") -> str:
    if value is None:
        return "정보 없음"
    return f"{value:,.2f}{suffix}"


def format_percent(value: float | None) -> str:
    if value is None:
        return "정보 없음"
    return f"{value * 100:,.2f}%"


def has_average_data(average_data: dict[str, dict[str, float | int | None]]) -> bool:
    return any(metric["average"] is not None for metric in average_data.values())


def get_peer_valuation_average(
    ticker: str,
    peer_tickers: list[str],
) -> tuple[str, dict[str, dict[str, float | int | None]]]:
    peers = [
        peer_ticker
        for peer_ticker in dedupe_tickers(peer_tickers)
        if peer_ticker != ticker.upper()
    ][:5]
    return "상위 5개 비교기업 평균", load_theme_valuation_average(tuple(peers))


def render_valuation_metrics(
    ticker: str,
    peer_tickers: list[str],
) -> None:
    info = load_ticker_info(ticker)
    metrics = extract_valuation_metrics(info)
    peer_label, theme_average = get_peer_valuation_average(ticker, peer_tickers)

    st.markdown("### 핵심 가치 지표")
    st.caption(f"비교 기준: {', '.join(peer_tickers) if peer_tickers else '비교기업 미입력'}")
    per_col, pbr_col, roe_col, div_col = st.columns(4)

    per_value = (
        f"TTM {format_ratio(metrics['trailing_pe'])} / FWD {format_ratio(metrics['forward_pe'])}"
        if metrics["trailing_pe"] is not None or metrics["forward_pe"] is not None
        else "정보 없음"
    )
    per_average = (
        f"{peer_label} TTM {format_ratio(theme_average['trailing_pe']['average'])} / "
        f"FWD {format_ratio(theme_average['forward_pe']['average'])}"
    )
    per_col.metric("PER", per_value, delta=per_average, delta_color="off")

    pbr_col.metric(
        "PBR",
        format_ratio(metrics["pbr"]),
        delta=f"{peer_label} {format_ratio(theme_average['pbr']['average'])}",
        delta_color="off",
    )
    roe_col.metric(
        "ROE",
        format_percent(metrics["roe"]),
        delta=f"{peer_label} {format_percent(theme_average['roe']['average'])}",
        delta_color="off",
    )
    div_col.metric(
        "배당수익률",
        format_percent(metrics["dividend_yield"]),
        delta=f"{peer_label} {format_percent(theme_average['dividend_yield']['average'])}",
        delta_color="off",
    )


def render_company_profile(ticker: str) -> None:
    info = load_ticker_info(ticker)

    sector = info.get("sector") or "정보 없음"
    industry = info.get("industry") or "정보 없음"
    summary = info.get("longBusinessSummary") or "기업 소개 정보가 제공되지 않았습니다."

    st.markdown(f"### {format_ticker_label(ticker)} 기업 소개")
    st.markdown(f"**섹터:** {sector}")
    st.markdown(f"**산업:** {industry}")
    st.markdown("#### 비즈니스 요약")
    st.markdown(summary)


def render_financial_statement(title: str, data) -> None:
    st.subheader(title)

    if data is None or getattr(data, "empty", True):
        st.info("제공되는 재무제표 데이터가 없습니다.")
        return

    translated_data = data.copy()
    translated_data.index = [
        finance_kor_dict.get(str(index_name), str(index_name))
        for index_name in translated_data.index
    ]
    translated_data.index.name = "항목"
    display_data = translated_data.reset_index()
    display_data.columns = [str(column) for column in display_data.columns]

    st.dataframe(display_data, width="stretch", height=360, hide_index=True)


def render_financial_statements(ticker: str) -> None:
    statements = load_financial_statements(ticker)

    if not statements:
        st.info("재무제표 데이터를 불러오지 못했습니다.")
        return

    render_financial_statement("손익계산서", statements.get("income_statement"))
    render_financial_statement("재무상태표", statements.get("balance_sheet"))
    render_financial_statement("현금흐름표", statements.get("cashflow"))


@st.cache_data
def load_ticker_news(ticker: str) -> list[dict[str, str]]:
    try:
        news_items = yf.Ticker(ticker).news or []
    except Exception:
        return []

    parsed_news = []
    for item in news_items[:5]:
        content = item.get("content", {}) if isinstance(item, dict) else {}
        title = item.get("title") or content.get("title")
        provider = content.get("provider", {}) if isinstance(content.get("provider"), dict) else {}
        publisher = item.get("publisher") or provider.get("displayName") or provider.get("name")
        link = (
            item.get("link")
            or item.get("url")
            or content.get("url")
            or content.get("canonicalUrl", {}).get("url")
            or content.get("clickThroughUrl", {}).get("url")
        )

        if not title or not link:
            continue

        parsed_news.append(
            {
                "title": str(title),
                "publisher": str(publisher or "언론사 정보 없음"),
                "link": str(link),
            }
        )

    return parsed_news


@st.cache_data
def translate_text_to_korean(text: str) -> str:
    cleaned_text = " ".join(str(text).split())
    if not cleaned_text:
        return ""

    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "ko",
                "dt": "t",
                "q": cleaned_text[:1800],
            },
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        translated = "".join(part[0] for part in payload[0] if part and part[0])
        return translated or cleaned_text
    except Exception:
        return cleaned_text


@st.cache_data
def fetch_article_summary_ko(url: str) -> str:
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
                )
            },
            timeout=5,
        )
        response.raise_for_status()
    except Exception:
        return "기사 본문을 불러오지 못해 헤드라인 중심으로만 확인했습니다."

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    paragraphs = [
        " ".join(paragraph.get_text(" ", strip=True).split())
        for paragraph in soup.find_all("p")
    ]
    paragraphs = [
        paragraph
        for paragraph in paragraphs
        if len(paragraph) >= 80 and "cookie" not in paragraph.lower()
    ]

    if not paragraphs:
        return "기사 본문 요약에 필요한 문단을 찾지 못했습니다."

    article_text = " ".join(paragraphs[:8])
    sentences = []
    for sentence in article_text.replace("?", ".").replace("!", ".").split("."):
        sentence = sentence.strip()
        if len(sentence) >= 40:
            sentences.append(sentence)
        if len(sentences) >= 3:
            break

    summary = ". ".join(sentences) or article_text[:700]
    return translate_text_to_korean(summary)


def render_news_item(news: dict[str, str]) -> None:
    translated_title = translate_text_to_korean(news["title"])
    summary_ko = fetch_article_summary_ko(news["link"])

    st.markdown(f"- [{translated_title}]({news['link']})")
    st.markdown(f"  - 언론사: `{news['publisher']}`")
    st.markdown(f"  - 요약: {summary_ko}")


def render_recent_news(ticker: str) -> None:
    st.subheader("📰 최근 관련 뉴스 헤드라인")

    news_items = load_ticker_news(ticker)
    if not news_items:
        st.info("최근 뉴스 데이터를 불러오지 못했거나 제공되는 뉴스가 없습니다.")
        return

    for news in news_items[:3]:
        render_news_item(news)


def analyze_news_impact(news_items: list[dict[str, str]]) -> dict[str, str | list[str]]:
    if not news_items:
        return {
            "tone": "뉴스 데이터 부족",
            "summary": "최근 뉴스 헤드라인을 불러오지 못해 가격 데이터 중심으로만 판단합니다.",
            "risk": "뉴스 기반 리스크 신호는 확인되지 않았습니다.",
            "headlines": [],
        }

    positive_keywords = [
        "beat",
        "beats",
        "upgrade",
        "upgrades",
        "surge",
        "record",
        "growth",
        "profit",
        "strong",
        "raises",
        "partnership",
        "launch",
        "호실적",
        "상향",
        "강세",
        "성장",
        "수주",
        "협력",
    ]
    negative_keywords = [
        "miss",
        "downgrade",
        "falls",
        "drop",
        "decline",
        "lawsuit",
        "probe",
        "risk",
        "warning",
        "cut",
        "weak",
        "tariff",
        "ban",
        "하락",
        "부진",
        "소송",
        "조사",
        "리스크",
        "경고",
        "규제",
    ]

    headlines = [news["title"] for news in news_items[:5]]
    joined = " ".join(headlines).lower()
    positive_score = sum(1 for keyword in positive_keywords if keyword in joined)
    negative_score = sum(1 for keyword in negative_keywords if keyword in joined)

    if positive_score > negative_score:
        tone = "긍정 우위"
        summary = "최근 헤드라인은 실적, 성장, 상향 조정 같은 긍정 재료가 상대적으로 더 많이 보입니다."
        risk = "다만 가격이 이미 빠르게 반응했을 수 있어 단기 과열 여부를 함께 확인해야 합니다."
    elif negative_score > positive_score:
        tone = "리스크 우위"
        summary = "최근 헤드라인은 하락, 부진, 규제, 경고성 이슈 같은 리스크 신호가 더 강합니다."
        risk = "낙폭이 커 보여도 뉴스 악재가 진행 중이면 바닥 확인 전까지 보수적인 접근이 필요합니다."
    else:
        tone = "중립"
        summary = "최근 헤드라인은 한쪽 방향으로 뚜렷하게 쏠리지 않아 가격 흐름과 실적 지표 확인이 더 중요합니다."
        risk = "명확한 뉴스 촉매가 약하면 박스권 흐름이 길어질 수 있습니다."

    return {
        "tone": tone,
        "summary": summary,
        "risk": risk,
        "headlines": [translate_text_to_korean(headline) for headline in headlines[:3]],
    }


@st.cache_data
def load_monthly_price_data(ticker: str):
    try:
        data = yf.download(
            ticker,
            period="max",
            interval="1mo",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception as exc:
        st.error(f"{ticker} 장기 데이터를 불러오지 못했습니다: {exc}")
        return None

    if data.empty:
        st.warning(f"{ticker}의 상장 이후 월봉 데이터가 비어 있습니다.")
        return None

    return data


def get_price_column(data, column_name: str):
    if hasattr(data.columns, "nlevels") and data.columns.nlevels > 1:
        if column_name in data.columns.get_level_values(0):
            column_data = data.xs(column_name, axis=1, level=0)
            if hasattr(column_data, "columns"):
                return column_data.iloc[:, 0].dropna()
            return column_data.dropna()

        for column in data.columns:
            if column_name in column:
                column_data = data[column]
                if hasattr(column_data, "columns"):
                    return column_data.iloc[:, 0].dropna()
                return column_data.dropna()

    if column_name in data.columns:
        column_data = data[column_name]
        if hasattr(column_data, "columns"):
            return column_data.iloc[:, 0].dropna()
        return column_data.dropna()

    return None


def calculate_stats(data) -> dict[str, str | float] | None:
    close = get_price_column(data, "Close")
    high = get_price_column(data, "High")
    low = get_price_column(data, "Low")

    if close is None or high is None or low is None or close.empty:
        return None

    current_price = float(close.iloc[-1])
    one_year_high = float(high.tail(252).max())
    drawdown = ((current_price / one_year_high) - 1) * 100 if one_year_high else 0

    recent_high = float(high.tail(20).max())
    recent_low = float(low.tail(20).min())
    box_range = ((recent_high - recent_low) / current_price) * 100 if current_price else 0
    sideways_status = "안정적 횡보 중" if box_range <= 8 else "변동성 높음"

    return {
        "current_price": current_price,
        "drawdown": drawdown,
        "box_range": box_range,
        "sideways_status": sideways_status,
    }


def calculate_period_return(data, trading_days: int) -> float | None:
    close = get_price_column(data, "Close")
    if close is None or len(close) <= trading_days:
        return None

    previous_price = float(close.iloc[-trading_days])
    current_price = float(close.iloc[-1])
    if previous_price == 0:
        return None

    return ((current_price / previous_price) - 1) * 100


@st.cache_data
def load_market_snapshot(tickers: tuple[str, ...]) -> dict[str, dict[str, float | None]]:
    snapshots = {}

    for ticker in tickers:
        try:
            data = yf.download(
                ticker,
                period="5d",
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )
        except Exception:
            snapshots[ticker] = {"price": None, "change": None}
            continue

        close = get_price_column(data, "Close") if data is not None and not data.empty else None
        if close is None or len(close) < 2:
            snapshots[ticker] = {"price": None, "change": None}
            continue

        current_price = float(close.iloc[-1])
        previous_price = float(close.iloc[-2])
        change = ((current_price / previous_price) - 1) * 100 if previous_price else None
        snapshots[ticker] = {"price": current_price, "change": change}

    return snapshots


def format_market_value(ticker: str, price: float | None) -> str:
    if price is None:
        return "정보 없음"
    if ticker == "KRW=X":
        return f"{price:,.2f}원"
    return f"{price:,.2f}"


def render_home_dashboard(ticker_records: list[dict[str, str]]) -> None:
    st.markdown("# 이준섭을 숭배하라")
    st.markdown("## 오늘의 시장 대시보드")
    st.caption("시장 방향, 딥 밸류 후보, 하락률 상위 종목을 한 번에 확인합니다.")

    st.subheader("🌐 글로벌 시장 동향")
    market_tickers = {
        "^KS11": "코스피 지수",
        "^GSPC": "S&P 500",
        "KRW=X": "원/달러 환율",
    }
    snapshots = load_market_snapshot(tuple(market_tickers.keys()))
    market_cols = st.columns(3)

    for column, (ticker, label) in zip(market_cols, market_tickers.items()):
        snapshot = snapshots.get(ticker, {})
        price = snapshot.get("price")
        change = snapshot.get("change")
        column.metric(
            f"{label} ({ticker})",
            format_market_value(ticker, price),
            delta=f"{change:.2f}%" if change is not None else "전일 대비 정보 없음",
        )

    st.subheader("🚨 오늘의 딥 밸류(Deep Value) 현황")
    records = tuple((record["ticker"], record["theme"]) for record in ticker_records)
    with st.spinner("전체 종목의 딥 밸류 조건을 점검하는 중입니다."):
        radar_results = screen_contrarian_candidates(records)
    count = len(radar_results)
    st.info(
        f"현재 역발상 매수 조건에 부합하는 숨은 우량주가 **{count}개** 포착되었습니다. "
        "좌측 메뉴의 '매수 레이더'에서 확인하세요!"
    )

    radar_top10 = st.session_state.get("radar_drawdown_top10", pd.DataFrame())
    overview_col, drawdown_col = st.columns([1, 1.4])
    with overview_col:
        st.markdown("### 🎯 후보군 요약")
        st.metric("조건 통과 후보", f"{count}개")
        st.metric(
            "하락률 TOP 10 후보",
            f"{len(radar_top10)}개" if not radar_top10.empty else "정보 없음",
            delta="조건 미충족 종목까지 포함",
            delta_color="off",
        )
        if not radar_results.empty:
            theme_counts = (
                radar_results["소속 테마"]
                .value_counts()
                .rename_axis("테마")
                .reset_index(name="후보 수")
            )
            st.dataframe(theme_counts, width="stretch", hide_index=True, height=220)
        else:
            st.caption("조건 통과 후보가 없으면 오른쪽 하락률 상위 후보부터 점검하세요.")

    with drawdown_col:
        st.markdown("### 📉 고점 대비 하락률 TOP 후보")
        if radar_top10.empty:
            st.info("하락률 후보 데이터를 계산하지 못했습니다.")
        else:
            st.caption("표에서 종목 행을 선택하면 개별 종목 분석 화면으로 이동합니다.")
            top10_event = st.dataframe(
                radar_top10.head(10),
                width="stretch",
                hide_index=True,
                height=360,
                column_order=[
                    "종목명(티커)",
                    "소속 테마",
                    "현재가",
                    "고점 대비 하락률(%)",
                    "20일 박스폭(%)",
                    "PER",
                    "배당수익률(%)",
                ],
                selection_mode="single-row",
                on_select="rerun",
                key="home_drawdown_top10_table",
            )
            selected_rows = top10_event.selection.rows
            if selected_rows:
                selected_ticker = radar_top10.iloc[selected_rows[0]].get("티커")
                if selected_ticker:
                    st.session_state.pending_analysis_ticker = selected_ticker
                    st.rerun()

    st.subheader("빠른 이동")
    guide_left, guide_right = st.columns(2)
    with guide_left:
        st.markdown(
            """
            ### 📊 개별 종목 분석
            테마별 종목의 차트, 밸류에이션, 재무제표, 최신 뉴스를 심층 분석합니다.
            """
        )
    with guide_right:
        st.markdown(
            """
            ### 🔍 역발상 매수 레이더
            전체 종목을 스크리닝하여 낙폭 과대 후 바닥을 다지는 매수 적기 종목을 자동 발굴합니다.
            """
        )


def render_market_brief(ticker: str, theme: str, data) -> None:
    ticker_label = format_ticker_label(ticker)
    stats = calculate_stats(data) if data is not None else None
    info = load_ticker_info(ticker)
    metrics = extract_valuation_metrics(info)
    three_month_return = calculate_period_return(data, 63) if data is not None else None
    news_items = load_ticker_news(ticker)
    news_impact = analyze_news_impact(news_items)

    if stats is None:
        st.markdown("### 최근 동향")
        st.info("가격 데이터가 부족해 최근 동향을 계산할 수 없습니다.")
        st.markdown("### 시장 분위기")
        st.info("시장 분위기를 판단할 데이터가 부족합니다.")
        st.markdown("### 향후 전망")
        st.info("전망을 계산할 데이터가 부족합니다.")
        return

    drawdown = stats["drawdown"]
    box_range = stats["box_range"]
    sideways_status = stats["sideways_status"]
    current_price = stats["current_price"]

    trend_text = (
        f"{ticker_label}는 현재 {current_price:,.2f} 수준에서 거래되고 있으며, "
        f"최근 52주 최고가 대비 {drawdown:.2f}% 위치에 있습니다. "
    )
    if three_month_return is not None:
        trend_text += f"최근 약 3개월 수익률은 {three_month_return:.2f}%입니다. "
    trend_text += (
        "낙폭이 큰 구간에 진입해 역발상 관찰 대상입니다."
        if drawdown <= -20
        else "아직 52주 고점 대비 과도한 할인 구간은 아닙니다."
    )
    trend_text += f" 최근 뉴스 톤은 **{news_impact['tone']}**으로 분류됩니다."

    mood_text = (
        f"최근 20거래일 고저 변동폭은 {box_range:.2f}%로, 현재 판정은 "
        f"**{sideways_status}**입니다. "
    )
    mood_text += (
        "가격이 좁은 범위에서 눌려 있어 매도 압력 둔화 여부를 볼 만합니다."
        if sideways_status == "안정적 횡보 중"
        else "아직 가격 변동성이 커서 분할 접근과 손절 기준 설정이 중요합니다."
    )
    mood_text += f" {news_impact['summary']}"

    valuation_parts = []
    if metrics["per"] is not None:
        valuation_parts.append(f"PER {metrics['per']:.2f}배")
    if metrics["pbr"] is not None:
        valuation_parts.append(f"PBR {metrics['pbr']:.2f}배")
    if metrics["dividend_yield"] is not None:
        valuation_parts.append(f"배당수익률 {metrics['dividend_yield'] * 100:.2f}%")

    valuation_text = ", ".join(valuation_parts) if valuation_parts else "가치 지표 정보 부족"
    outlook_text = (
        f"{format_theme_name(theme)} 테마 내에서 {valuation_text} 상태입니다. "
        "고점 대비 하락률과 횡보 여부가 동시에 충족될수록 역발상 매수 후보로서의 우선순위가 높아집니다. "
        f"{news_impact['risk']} "
        "실적 발표, 금리와 업황 변화가 동시에 확인될 때 실제 매수 판단의 신뢰도가 올라갑니다."
    )
    if news_impact["headlines"]:
        headline_text = " / ".join(news_impact["headlines"])
        outlook_text += f" 참고할 최근 헤드라인: {headline_text}"

    st.markdown("### 최근 동향")
    st.markdown(trend_text)

    st.markdown("### 시장 분위기")
    st.markdown(mood_text)

    st.markdown("### 향후 전망")
    st.markdown(outlook_text)


@st.cache_data
def load_screening_price_data(ticker: str):
    try:
        data = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception:
        return None

    if data is None or data.empty:
        return None

    return data


@st.cache_data
def load_screening_profile(ticker: str) -> dict:
    info = load_ticker_info(ticker)
    metrics = extract_valuation_metrics(info)

    return {
        "display_name": format_ticker_name(ticker)
        if ticker in COMPANY_NAME_MAP
        else info.get("shortName") or info.get("longName") or ticker,
        "per": metrics["per"],
        "dividend_yield": metrics["dividend_yield"],
    }


def screen_contrarian_candidates(
    records: tuple[tuple[str, str], ...],
    show_progress: bool = False,
) -> pd.DataFrame:
    candidates = []
    drawdown_rows = []
    total_count = len(records)
    progress_bar = st.progress(0) if show_progress and total_count else None
    status_box = st.empty() if show_progress else None
    started_at = time.monotonic()

    for index, (ticker, theme) in enumerate(records, start=1):
        if status_box is not None:
            status_box.caption(
                f"{index}/{total_count} 점검 중: {ticker} · 현재 후보 {len(candidates)}개"
            )
        if progress_bar is not None:
            progress_bar.progress(index / total_count)

        data = load_screening_price_data(ticker)

        if data is None or data.empty:
            continue

        stats = calculate_stats(data)
        if stats is None:
            continue

        drawdown_rows.append(
            {
                "ticker": ticker,
                "theme": theme,
                "current_price": stats["current_price"],
                "drawdown": stats["drawdown"],
                "box_range": stats["box_range"],
            }
        )

        if stats["drawdown"] > -20 or stats["box_range"] > 8:
            continue

        profile = load_screening_profile(ticker)
        display_name = profile["display_name"]

        candidates.append(
            {
                "티커": ticker,
                "종목명(티커)": f"{display_name} ({ticker})" if display_name != ticker else ticker,
                "소속 테마": format_theme_name(theme),
                "현재가": round(stats["current_price"], 2),
                "고점 대비 하락률(%)": round(stats["drawdown"], 2),
                "PER": round(profile["per"], 2) if profile["per"] is not None else None,
                "배당수익률(%)": (
                    round(profile["dividend_yield"] * 100, 2)
                    if profile["dividend_yield"] is not None
                    else None
                ),
            }
        )

    if status_box is not None:
        elapsed = time.monotonic() - started_at
        status_box.caption(
            f"점검 완료: {total_count}개 종목 · 후보 {len(candidates)}개 · 소요 {elapsed:.1f}초"
        )
    if progress_bar is not None:
        progress_bar.progress(1.0)

    top_drawdown_rows = sorted(drawdown_rows, key=lambda row: row["drawdown"])[:10]
    top10 = []
    for row in top_drawdown_rows:
        profile = load_screening_profile(row["ticker"])
        display_name = profile["display_name"]
        top10.append(
            {
                "티커": row["ticker"],
                "종목명(티커)": (
                    f"{display_name} ({row['ticker']})"
                    if display_name != row["ticker"]
                    else row["ticker"]
                ),
                "소속 테마": format_theme_name(row["theme"]),
                "현재가": round(row["current_price"], 2),
                "고점 대비 하락률(%)": round(row["drawdown"], 2),
                "20일 박스폭(%)": round(row["box_range"], 2),
                "PER": round(profile["per"], 2) if profile["per"] is not None else None,
                "배당수익률(%)": (
                    round(profile["dividend_yield"] * 100, 2)
                    if profile["dividend_yield"] is not None
                    else None
                ),
            }
        )
    st.session_state.radar_drawdown_top10 = pd.DataFrame(
        top10,
        columns=[
            "티커",
            "종목명(티커)",
            "소속 테마",
            "현재가",
            "고점 대비 하락률(%)",
            "20일 박스폭(%)",
            "PER",
            "배당수익률(%)",
        ],
    )

    return pd.DataFrame(
        candidates,
        columns=[
            "티커",
            "종목명(티커)",
            "소속 테마",
            "현재가",
            "고점 대비 하락률(%)",
            "PER",
            "배당수익률(%)",
        ],
    )


def render_stats(data) -> None:
    stats = calculate_stats(data)

    if stats is None:
        st.info("핵심 지표를 계산할 수 있는 가격 데이터가 부족합니다.")
        return

    current_col, drawdown_col, sideways_col = st.columns(3)

    current_col.metric("현재 주가", f"{stats['current_price']:,.2f}")

    with drawdown_col:
        st.metric("52주 최고가 대비 하락률", f"{stats['drawdown']:.2f}%")
        if stats["drawdown"] <= -20:
            st.markdown(
                "<span style='color:#ff4b4b;font-weight:700;'>-20% 이하 역발상 관심권</span>",
                unsafe_allow_html=True,
            )

    sideways_col.metric(
        "바닥 횡보 상태",
        stats["sideways_status"],
        delta=f"20일 박스폭 {stats['box_range']:.2f}%",
        delta_color="off",
    )


def render_finance_glossary() -> None:
    with st.sidebar.expander("📚 주식 및 재무 용어 사전"):
        st.markdown(
            """
            **PER (주가수익비율)**  
            주가가 1주당 수익의 몇 배인지 나타내는 지표. 동종 업계 평균 대비 낮을수록 저평가.

            **PBR (주가순자산비율)**  
            주가가 1주당 순자산의 몇 배인지 나타내는 지표. 1 미만이면 장부상 가치보다 주가가 싼 상태.

            **ROE (자기자본이익률)**  
            회사 자본으로 1년에 몇 %의 이익을 냈는지 나타내는 수익성 지표.

            **매출액 (Revenue)**  
            기업이 본업을 통해 벌어들인 총금액.

            **영업이익 (Operating Income)**  
            매출액에서 원가와 각종 판관비를 뺀 본업의 순수 이익.

            **당기순이익 (Net Income)**  
            영업이익에서 세금, 이자 등 모든 비용을 빼고 최종적으로 남은 진짜 이익.
            """
        )


def render_daily_candlestick(data, ticker: str) -> None:
    if go is None:
        st.error("Plotly가 설치되지 않아 차트를 표시할 수 없습니다. requirements.txt 설치 후 다시 실행해 주세요.")
        return

    open_price = get_price_column(data, "Open")
    high = get_price_column(data, "High")
    low = get_price_column(data, "Low")
    close = get_price_column(data, "Close")

    if any(series is None for series in [open_price, high, low, close]):
        st.info("캔들스틱 차트를 그릴 수 있는 OHLC 데이터가 부족합니다.")
        return

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=data.index,
                open=open_price,
                high=high,
                low=low,
                close=close,
                name=ticker,
                increasing_line_color="#00a86b",
                decreasing_line_color="#e64b3c",
            )
        ]
    )
    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=40, b=10),
        title=f"{format_ticker_label(ticker)} 최근 3년 일봉",
        xaxis_title=None,
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")


def render_monthly_line(data, ticker: str) -> None:
    if go is None:
        st.error("Plotly가 설치되지 않아 차트를 표시할 수 없습니다. requirements.txt 설치 후 다시 실행해 주세요.")
        return

    close = get_price_column(data, "Close")

    if close is None or close.empty:
        st.info("장기 라인 차트를 그릴 수 있는 종가 데이터가 부족합니다.")
        return

    fig = go.Figure(
        data=[
            go.Scatter(
                x=close.index,
                y=close,
                mode="lines",
                name=ticker,
                line=dict(color="#2563eb", width=4, shape="spline"),
            )
        ]
    )
    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=40, b=10),
        title=f"{format_ticker_label(ticker)} 상장 이후 월봉 흐름",
        xaxis_title=None,
        yaxis_title="Price",
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")


def main() -> None:
    sectors = load_sectors()
    ticker_records = flatten_tickers(sectors)
    label_to_record = {record["label"]: record for record in ticker_records}
    ticker_to_record = {record["ticker"]: record for record in ticker_records}
    search_labels = list(label_to_record.keys())

    if "selected_theme" not in st.session_state:
        st.session_state.selected_theme = ticker_records[0]["theme"]
    if "selected_ticker" not in st.session_state:
        st.session_state.selected_ticker = ticker_records[0]["ticker"]
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = find_category_for_theme(
            st.session_state.selected_theme
        )

    active_record = ticker_to_record.get(st.session_state.selected_ticker, ticker_records[0])
    st.session_state.selected_theme = active_record["theme"]
    st.session_state.selected_category = find_category_for_theme(active_record["theme"])
    active_label = active_record["label"]

    def sync_from_global_search() -> None:
        record = label_to_record[st.session_state.global_search]
        category = find_category_for_theme(record["theme"])
        st.session_state.selected_category = category
        st.session_state.selected_theme = record["theme"]
        st.session_state.selected_ticker = record["ticker"]
        st.session_state.sidebar_category = category
        st.session_state.sidebar_theme = record["theme"]
        st.session_state.ticker_picker = record["ticker"]

    def sync_from_sidebar_category() -> None:
        category = st.session_state.sidebar_category
        available_themes = get_available_themes(category, sectors)
        theme = available_themes[0]
        ticker = sectors[theme][0]
        record = ticker_to_record[ticker]
        st.session_state.selected_category = category
        st.session_state.selected_theme = theme
        st.session_state.selected_ticker = ticker
        st.session_state.sidebar_theme = theme
        st.session_state.ticker_picker = ticker
        st.session_state.global_search = record["label"]

    def sync_from_sidebar_theme() -> None:
        theme = st.session_state.sidebar_theme
        category = find_category_for_theme(theme)
        st.session_state.selected_theme = theme
        st.session_state.selected_category = category
        st.session_state.sidebar_category = category
        if st.session_state.selected_ticker not in sectors[theme]:
            st.session_state.selected_ticker = sectors[theme][0]
        record = ticker_to_record[st.session_state.selected_ticker]
        st.session_state.global_search = record["label"]
        st.session_state.ticker_picker = record["ticker"]

    def sync_from_ticker_picker() -> None:
        ticker = st.session_state.ticker_picker
        record = ticker_to_record[ticker]
        category = find_category_for_theme(record["theme"])
        st.session_state.selected_category = category
        st.session_state.selected_theme = record["theme"]
        st.session_state.selected_ticker = record["ticker"]
        st.session_state.sidebar_category = category
        st.session_state.sidebar_theme = record["theme"]
        st.session_state.global_search = record["label"]

    pending_analysis_ticker = st.session_state.pop("pending_analysis_ticker", None)
    if pending_analysis_ticker in ticker_to_record:
        record = ticker_to_record[pending_analysis_ticker]
        category = find_category_for_theme(record["theme"])
        st.session_state.page_mode = "📊 개별 종목 분석"
        st.session_state.selected_category = category
        st.session_state.selected_theme = record["theme"]
        st.session_state.selected_ticker = record["ticker"]
        st.session_state.sidebar_category = category
        st.session_state.sidebar_theme = record["theme"]
        st.session_state.ticker_picker = record["ticker"]
        st.session_state.global_search = record["label"]

    apply_design_system_styles()

    page_mode = st.sidebar.radio(
        "메뉴",
        ["🏠 홈 (대시보드 요약)", "📊 개별 종목 분석", "🔍 역발상 매수 레이더"],
        key="page_mode",
    )

    title_col, refresh_col = st.columns([8, 2], vertical_alignment="center")
    with title_col:
        st.title("📈 딥 밸류(Deep Value) 우량주 스크리너")
    with refresh_col:
        st.write("")
        if st.button("🔄 최신 데이터로 업데이트", use_container_width=True):
            st.cache_data.clear()
            st.session_state.pop("radar_results", None)
            st.session_state.pop("radar_drawdown_top10", None)
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()

    if page_mode == "🏠 홈 (대시보드 요약)":
        render_home_dashboard(ticker_records)

    elif page_mode == "📊 개별 종목 분석":
        if "global_search" not in st.session_state:
            st.session_state.global_search = active_label
        st.selectbox(
            "통합 검색",
            search_labels,
            key="global_search",
            on_change=sync_from_global_search,
        )

        st.sidebar.header("설정")
        if "sidebar_category" not in st.session_state:
            st.session_state.sidebar_category = st.session_state.selected_category
        if "sidebar_theme" not in st.session_state:
            st.session_state.sidebar_theme = st.session_state.selected_theme

        selected_category = st.sidebar.selectbox(
            "대분류",
            list(CATEGORY_MAP.keys()),
            key="sidebar_category",
            on_change=sync_from_sidebar_category,
        )
        available_themes = get_available_themes(selected_category, sectors)
        if st.session_state.sidebar_theme not in available_themes:
            st.session_state.sidebar_theme = available_themes[0]
        selected_theme = st.sidebar.selectbox(
            "소분류",
            available_themes,
            key="sidebar_theme",
            format_func=format_theme_name,
            on_change=sync_from_sidebar_theme,
        )

        if "ticker_picker" not in st.session_state:
            st.session_state.ticker_picker = st.session_state.selected_ticker
        if st.session_state.ticker_picker not in sectors[selected_theme]:
            st.session_state.ticker_picker = sectors[selected_theme][0]
        selected_ticker = st.sidebar.selectbox(
            "기업/티커",
            sectors[selected_theme],
            key="ticker_picker",
            format_func=format_ticker_label,
            on_change=sync_from_ticker_picker,
        )
        default_peer_tickers = get_default_top_peer_tickers(
            selected_ticker,
            selected_theme,
            sectors,
        )
        st.sidebar.link_button(
            "Google에서 상위 비교기업 확인",
            build_google_peer_search_url(selected_theme),
            use_container_width=True,
        )
        peer_input = st.sidebar.text_input(
            "동종업계 상위 5개 비교기업",
            value=", ".join(default_peer_tickers),
            key=f"peer_input_{selected_theme}_{selected_ticker}",
            help="Google에서 확인한 같은 테마 대표 기업 티커 5개를 쉼표로 입력하세요. 선택 기업은 평균에서 제외됩니다.",
        )
        peer_tickers = parse_peer_ticker_input(peer_input, selected_ticker)
        render_finance_glossary()

        st.subheader(format_theme_name(selected_theme))
        st.caption(f"{selected_category} · {format_ticker_label(selected_ticker)}")

        tab1, tab2, tab3 = st.tabs(["📊 차트 및 스탯", "🏢 기업 소개", "💰 재무제표"])

        with tab1:
            with st.spinner(f"{selected_ticker} 최근 3년 일봉 데이터를 불러오는 중입니다."):
                price_data = load_price_data(selected_ticker)

            render_market_brief(selected_ticker, selected_theme, price_data)
            render_valuation_metrics(selected_ticker, peer_tickers)

            if price_data is not None:
                render_stats(price_data)

                chart_view = st.radio(
                    "차트 보기",
                    ["최근 3년 (일봉)", "상장 이후 (월봉/연봉)"],
                    horizontal=True,
                )

                if chart_view == "최근 3년 (일봉)":
                    render_daily_candlestick(price_data, selected_ticker)
                else:
                    with st.spinner(f"{selected_ticker} 상장 이후 월봉 데이터를 불러오는 중입니다."):
                        monthly_data = load_monthly_price_data(selected_ticker)
                    if monthly_data is not None:
                        render_monthly_line(monthly_data, selected_ticker)

        with tab2:
            render_company_profile(selected_ticker)

        with tab3:
            render_financial_statements(selected_ticker)

        st.divider()
        render_recent_news(selected_ticker)

    else:
        st.subheader("🔍 역발상 매수 레이더")
        st.info(
            f"버튼을 누르면 {len(ticker_records)}개 전 종목을 스크리닝하여 "
            "낙폭 과대 후 횡보 중인 종목을 찾습니다. 진행률이 아래에 표시되며, "
            "한 번 조회된 종목 데이터는 수동 업데이트 전까지 캐시에 보관됩니다."
        )

        if st.button("레이더 가동 (전체 종목 스크리닝)", type="primary"):
            records = tuple((record["ticker"], record["theme"]) for record in ticker_records)
            with st.spinner("전체 종목의 낙폭과 횡보 상태를 점검하는 중입니다."):
                st.session_state.radar_results = screen_contrarian_candidates(
                    records,
                    show_progress=True,
                )

        if "radar_results" in st.session_state:
            results = st.session_state.radar_results
            radar_column_order = [
                "종목명(티커)",
                "소속 테마",
                "현재가",
                "고점 대비 하락률(%)",
                "20일 박스폭(%)",
                "PER",
                "배당수익률(%)",
            ]
            if results.empty:
                st.warning("현재 역발상 매수 조건에 부합하는 종목이 없습니다.")
                top10 = st.session_state.get("radar_drawdown_top10", pd.DataFrame())
                if not top10.empty:
                    st.subheader("📉 고점 대비 하락률 TOP 10")
                    st.caption(
                        "조건 2개를 모두 통과하지는 못했지만, 전체 종목 중 하락폭이 가장 큰 순서입니다. "
                        "종목 행을 선택하면 개별 종목 분석 화면으로 이동합니다."
                    )
                    top10_event = st.dataframe(
                        top10,
                        width="stretch",
                        hide_index=True,
                        column_order=radar_column_order,
                        selection_mode="single-row",
                        on_select="rerun",
                        key="radar_drawdown_top10_table",
                    )
                    selected_rows = top10_event.selection.rows
                    if selected_rows:
                        selected_ticker = top10.iloc[selected_rows[0]].get("티커")
                        if selected_ticker:
                            st.session_state.pending_analysis_ticker = selected_ticker
                            st.rerun()
            else:
                st.success(f"{len(results)}개 종목이 역발상 매수 조건을 통과했습니다.")
                st.caption("종목 행을 선택하면 개별 종목 분석 화면으로 이동합니다.")
                results_event = st.dataframe(
                    results,
                    width="stretch",
                    hide_index=True,
                    column_order=[
                        "종목명(티커)",
                        "소속 테마",
                        "현재가",
                        "고점 대비 하락률(%)",
                        "PER",
                        "배당수익률(%)",
                    ],
                    selection_mode="single-row",
                    on_select="rerun",
                    key="radar_results_table",
                )
                selected_rows = results_event.selection.rows
                if selected_rows:
                    selected_ticker = results.iloc[selected_rows[0]].get("티커")
                    if selected_ticker:
                        st.session_state.pending_analysis_ticker = selected_ticker
                        st.rerun()

                visible_results = results.drop(columns=["티커"], errors="ignore")
                csv_data = visible_results.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 스크리닝 결과 다운로드 (CSV)",
                    data=csv_data,
                    file_name="contrarian_screening_results.csv",
                    mime="text/csv",
                )


if __name__ == "__main__":
    main()
