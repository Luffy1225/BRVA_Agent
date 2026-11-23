from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.client import backend_client
from src.context import UserContext

class CodeshareQueryInput(BaseModel):
    category: Optional[str] = Field(None, description="推薦類型，如 'rotw' (每週精選雙倍哩程), 'codeshare' (聯營), 'popular' (熱門), 'long' (長程跨洋), 'short' (區域短程), 'cargo' (貨機)")
    airline: Optional[str] = Field(None, description="指定航空公司代碼或名稱，如 'ANA', 'NH', 'UA', 'SQ', 'EVA', '星空聯盟'")
    dep_icao: Optional[str] = Field(None, description="出發機場 ICAO，如 'RCTP'")
    arr_icao: Optional[str] = Field(None, description="抵達機場 ICAO，如 'RJAA'")

DEFAULT_ROTW_ROUTES = [
    {
        "flight_number": "BR3",
        "dep": "KIAD", "dep_name": "華盛頓杜勒斯",
        "arr": "RCTP", "arr_name": "台北桃園",
        "aircraft": "B787-9",
        "duration": "15h 0m",
        "airline": "長榮航空 (EVA Air)",
        "type": "rotw",
        "multiplier": "🌟 2.0x 雙倍哩程 (ROTW 精選)"
    },
    {
        "flight_number": "BR315",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "YBBN", "arr_name": "布里斯本",
        "aircraft": "B787-10",
        "duration": "08h 30m",
        "airline": "長榮航空 (EVA Air)",
        "type": "rotw",
        "multiplier": "🌟 2.0x 雙倍哩程 (ROTW 精選)"
    },
    {
        "flight_number": "BR395",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "VVTS", "arr_name": "胡志明新山一",
        "aircraft": "A321-200",
        "duration": "03h 25m",
        "airline": "長榮航空 (EVA Air)",
        "type": "rotw",
        "multiplier": "🌟 2.0x 雙倍哩程 (ROTW 精選)"
    },
    {
        "flight_number": "BR184 / NH5824",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "RJAA", "arr_name": "東京成田",
        "aircraft": "B787-10",
        "duration": "02h 40m",
        "airline": "長榮航空 / 全日空 (ANA Codeshare)",
        "type": "rotw",
        "multiplier": "🌟 2.0x 雙倍哩程 (ROTW 精選)"
    }
]

DEFAULT_CODESHARE_PARTNERS = [
    {"name": "全日空 (All Nippon Airways)", "code": "NH", "alliance": "Star Alliance", "routes_count": 18, "is_codeshare": True},
    {"name": "新加坡航空 (Singapore Airlines)", "code": "SQ", "alliance": "Star Alliance", "routes_count": 14, "is_codeshare": True},
    {"name": "聯合航空 (United Airlines)", "code": "UA", "alliance": "Star Alliance", "routes_count": 16, "is_codeshare": True},
    {"name": "韓亞航空 (Asiana Airlines)", "code": "OZ", "alliance": "Star Alliance", "routes_count": 10, "is_codeshare": True},
    {"name": "土耳其航空 (Turkish Airlines)", "code": "TK", "alliance": "Star Alliance", "routes_count": 8, "is_codeshare": True},
    {"name": "紐西蘭航空 (Air New Zealand)", "code": "NZ", "alliance": "Star Alliance", "routes_count": 6, "is_codeshare": True},
    {"name": "加拿大航空 (Air Canada)", "code": "AC", "alliance": "Star Alliance", "routes_count": 8, "is_codeshare": True},
    {"name": "德國漢莎航空 (Lufthansa)", "code": "LH", "alliance": "Star Alliance", "routes_count": 12, "is_codeshare": True},
]

DEFAULT_FEATURED_ROUTES = [
    {
        "flight_number": "BR184 / NH5824",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "RJAA", "arr_name": "東京成田",
        "aircraft": "B787-10",
        "duration": "02h 40m",
        "airline": "長榮航空 / 全日空 (ANA Codeshare)",
        "type": "codeshare",
        "multiplier": "1.2x 聯營加成"
    },
    {
        "flight_number": "BR198 / NH5826",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "RJAA", "arr_name": "東京成田",
        "aircraft": "B777-300ER",
        "duration": "02h 45m",
        "airline": "長榮航空 / 全日空 (ANA Codeshare)",
        "type": "codeshare",
        "multiplier": "1.2x 聯營加成"
    },
    {
        "flight_number": "BR225 / SQ5825",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "WSSS", "arr_name": "新加坡樟宜",
        "aircraft": "B777-300ER",
        "duration": "04h 35m",
        "airline": "長榮航空 / 新加坡航空 (SQ Codeshare)",
        "type": "codeshare",
        "multiplier": "1.2x 聯營加成"
    },
    {
        "flight_number": "BR012 / UA6772",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "KLAX", "arr_name": "洛杉磯國際",
        "aircraft": "B777-300ER",
        "duration": "11h 20m",
        "airline": "長榮航空 / 聯合航空 (UA Codeshare)",
        "type": "long",
        "multiplier": "1.5x 長程跨洋"
    },
    {
        "flight_number": "BR028 / UA6774",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "KSFO", "arr_name": "舊金山國際",
        "aircraft": "B777-300ER",
        "duration": "10h 50m",
        "airline": "長榮航空 / 聯合航空 (UA Codeshare)",
        "type": "long",
        "multiplier": "1.5x 長程跨洋"
    },
    {
        "flight_number": "BR130 / NH5830",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "RJBB", "arr_name": "大阪關西",
        "aircraft": "B787-9",
        "duration": "02h 15m",
        "airline": "長榮航空 / 全日空 (ANA Codeshare)",
        "type": "short",
        "multiplier": "1.0x 標準"
    },
    {
        "flight_number": "BR867",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "VHHH", "arr_name": "香港赤鱲角",
        "aircraft": "A321-200 / B78X",
        "duration": "01h 50m",
        "airline": "長榮航空 (EVA Air)",
        "type": "popular",
        "multiplier": "1.0x 黃金穿梭"
    },
    {
        "flight_number": "BR618 (Cargo)",
        "dep": "RCTP", "dep_name": "台北桃園",
        "arr": "PANC", "arr_name": "安克拉治貨運樞紐",
        "aircraft": "B777F 全貨機",
        "duration": "08h 30m",
        "airline": "長榮貨運 (EVA Cargo)",
        "type": "cargo",
        "multiplier": "1.3x 貨運加成"
    }
]

def query_codeshare_partners(user_context: Optional[UserContext] = None) -> Dict[str, Any]:
    """
    Queries the list of official Codeshare airline partners and their fleet routes count.
    Answers questions like: '現在有幾個 codeshare?', '有哪些聯營合作航空公司?'.
    """
    token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None

    # Try live query from backend
    backend_res = backend_client.get("/api/airlines", params={"includeNonCodeshare": "false"}, user_token=token)

    partners = []
    if backend_res and isinstance(backend_res, dict) and backend_res.get("success"):
        raw_airlines = backend_res.get("data") or []
        for a in raw_airlines:
            if a.get("isCodeshare") or not a.get("isMain"):
                mappings = a.get("routeAircraftMappings") or []
                partners.append({
                    "name": a.get("name", "Codeshare Airline"),
                    "code": a.get("code", "XX"),
                    "alliance": a.get("alliance") or "Star Alliance",
                    "routes_count": len(mappings) if mappings else 12,
                    "is_codeshare": True
                })

    if not partners:
        partners = DEFAULT_CODESHARE_PARTNERS

    total_codeshares = len(partners)

    lines = [
        f"🤝 **長榮虛擬航空 · 星空聯盟與聯營夥伴總覽 (Codeshare Network)**\n",
        f"目前長榮虛擬航空航網中共有 **{total_codeshares} 家** 官方 Codeshare 聯營合作航空公司：\n"
    ]

    for p in partners:
        c_code = p.get("code")
        c_name = p.get("name")
        c_alliance = p.get("alliance")
        routes_c = p.get("routes_count")
        lines.append(f"• **{c_name}** (`{c_code}`) ｜ 聯盟：`{c_alliance}` ｜ 聯營航線：約 `{routes_c}` 條")

    lines.append(
        "\n💡 **機長權益提醒**：執飛掛載 Codeshare 班號之航班，享有星空聯盟里程積累加成，並可於 Dispatch Center 直接簽派放行！"
    )

    summary_text = "\n".join(lines).strip()
    return {
        "status": "SUCCESS",
        "total_codeshare_partners": total_codeshares,
        "partners": partners,
        "summary": summary_text,
        "summary_text": summary_text
    }

def recommend_routes_and_codeshares(
    category: Optional[str] = None,
    airline: Optional[str] = None,
    dep_icao: Optional[str] = None,
    arr_icao: Optional[str] = None,
    user_context: Optional[UserContext] = None
) -> Dict[str, Any]:
    """
    Recommends virtual routes based on user preferences (e.g. 'codeshare', 'popular', 'long', 'short', 'cargo')
    or specific airline/codeshare partners (e.g. 'ANA', 'United', 'Singapore Airlines').
    """
    token = user_context.delegation_token if (user_context and user_context.is_authenticated) else None

    # Query backend routes if available
    params = {}
    if dep_icao:
        params["dept"] = dep_icao.strip().upper()
    if arr_icao:
        params["arr"] = arr_icao.strip().upper()
    if airline:
        params["airline"] = airline.strip()

    backend_res = backend_client.get("/api/routes", params=params, user_token=token)

    routes_pool = []
    if backend_res and isinstance(backend_res, dict) and backend_res.get("success"):
        raw_routes = backend_res.get("data") or backend_res.get("routes") or []
        for r in raw_routes:
            al = r.get("airline") or {}
            al_name = al.get("name") if isinstance(al, dict) else "長榮航空"
            r_fn = r.get("routeNumber") or r.get("flightNumber") or "BR"
            ac_val = r.get("aircraft") or "B78X"
            if isinstance(ac_val, list):
                ac_val = ", ".join(ac_val)
            routes_pool.append({
                "flight_number": r_fn,
                "dep": r.get("departureICAO", "RCTP"),
                "dep_name": r.get("deptAirport", "台北桃園"),
                "arr": r.get("arrivalICAO", "RJAA"),
                "arr_name": r.get("arrAirport", "目的地"),
                "aircraft": ac_val,
                "duration": r.get("flightTime", "02h 40m"),
                "airline": al_name,
                "type": "codeshare" if (al.get("isCodeshare") or "NH" in r_fn or "UA" in r_fn or "SQ" in r_fn) else "regular",
                "multiplier": "1.2x 獎勵"
            })

    if not routes_pool:
        routes_pool = DEFAULT_FEATURED_ROUTES

    # 1. Check if user explicitly asked for ROTW or general recommendation
    is_rotw_focused = False
    if category:
        cat_lower = category.lower().strip()
        if any(k in cat_lower for k in ["rotw", "每週", "當週", "雙倍", "加倍"]):
            is_rotw_focused = True

    # Try querying active calendar events for ROTW
    live_rotw_routes = []
    try:
        cal_res = backend_client.get("/api/calendar/events", params={"includeRotw": "true", "limit": "10"}, user_token=token)
        if cal_res and isinstance(cal_res, dict) and cal_res.get("success"):
            events = cal_res.get("data") or []
            for ev in events:
                t_up = str(ev.get("title", "")).upper()
                meta = ev.get("metadata") or {}
                if "ROTW" in t_up or meta.get("isROTW"):
                    # Event is active ROTW
                    break
    except Exception as e:
        print(f"[crewcenter_codeshare_tool] ROTW live event check error: {e}")

    # Fallback / static ROTW pool
    rotw_pool = list(DEFAULT_ROTW_ROUTES)

    if is_rotw_focused:
        filtered = rotw_pool
        if dep_icao:
            filtered = [r for r in filtered if r["dep"].upper() == dep_icao.strip().upper()]
        if arr_icao:
            filtered = [r for r in filtered if r["arr"].upper() == arr_icao.strip().upper()]
        if not filtered:
            filtered = rotw_pool

        lines = [
            f"🌟 **長榮航網 · ROTW (Route of the Week) 當週精選雙倍哩程航線**\n",
            f"長榮虛擬航空每週精選雙倍航線 (ROTW) 現正開放中！執飛以下指定航班享有 **2.0x 飛行哩程與虛擬積分加倍**：\n"
        ]

        for idx, r in enumerate(filtered[:4], 1):
            fn = r.get("flight_number")
            dep = r.get("dep")
            dep_n = r.get("dep_name", dep)
            arr = r.get("arr")
            arr_n = r.get("arr_name", arr)
            ac = r.get("aircraft")
            dur = r.get("duration")
            al = r.get("airline")
            mul = r.get("multiplier", "🌟 2.0x 雙倍哩程")

            lines.append(
                f"**{idx}. 航班：`{fn}`** ｜ `{al}`\n"
                f"   • 航線起訖：**{dep} ({dep_n}) 🛫 ➔ {arr} ({arr_n}) 🛬**\n"
                f"   • 推薦機型：`{ac}` ｜ 預估飛行時間：`{dur}`\n"
                f"   • 營運加成：<span style='color: #10b981; font-weight: 700;'>{mul}</span>\n"
            )

        lines.append(
            "👉 **機長快速簽派**：直接對我說「**幫我簽派 BR3**」或「**簽派 BR315**」，將立刻為您生成 SimBrief 放行單，起飛即可享受雙倍哩程加成！"
        )
        summary_text = "\n".join(lines).strip()
        return {
            "status": "SUCCESS",
            "category": "rotw",
            "recommended_count": len(filtered[:4]),
            "routes": filtered[:4],
            "summary": summary_text,
            "summary_text": summary_text
        }

    # Apply filters locally
    filtered = list(routes_pool)

    if airline:
        al_clean = airline.upper()
        if "ANA" in al_clean or "NH" in al_clean or "全日空" in al_clean:
            filtered = [r for r in filtered if "NH" in r["flight_number"] or "ANA" in r["airline"] or "全日空" in r["airline"]]
        elif "UA" in al_clean or "UNITED" in al_clean or "聯合" in al_clean:
            filtered = [r for r in filtered if "UA" in r["flight_number"] or "United" in r["airline"] or "聯合" in r["airline"]]
        elif "SQ" in al_clean or "SINGAPORE" in al_clean or "星航" in al_clean or "新航" in al_clean:
            filtered = [r for r in filtered if "SQ" in r["flight_number"] or "SQ" in r["airline"] or "新加坡" in r["airline"]]

    if category:
        cat_clean = category.lower().strip()
        if "codeshare" in cat_clean or "聯營" in cat_clean:
            filtered = [r for r in filtered if r.get("type") == "codeshare" or "Codeshare" in r.get("airline", "") or "/" in r.get("flight_number", "")]
        elif "long" in cat_clean or "長程" in cat_clean or "跨洋" in cat_clean:
            filtered = [r for r in filtered if r.get("type") == "long" or any(c in r.get("arr", "") for c in ["KLAX", "KSFO", "KJFK", "EGLL", "EDDF"])]
        elif "short" in cat_clean or "短程" in cat_clean:
            filtered = [r for r in filtered if r.get("type") == "short" or any(c in r.get("arr", "") for c in ["VHHH", "RJBB", "RCKH"])]
        elif "cargo" in cat_clean or "貨機" in cat_clean or "貨運" in cat_clean:
            filtered = [r for r in filtered if r.get("type") == "cargo" or "Cargo" in r.get("flight_number", "")]

    if dep_icao:
        filtered = [r for r in filtered if r["dep"].upper() == dep_icao.strip().upper()]
    if arr_icao:
        filtered = [r for r in filtered if r["arr"].upper() == arr_icao.strip().upper()]

    if not filtered:
        filtered = DEFAULT_FEATURED_ROUTES[:4]

    # For general recommendations, always feature ROTW routes at the top with 2.0x bonus
    if not airline and (not category or category in ["popular", "recommend"]):
        rotw_samples = DEFAULT_ROTW_ROUTES[:2]
        rotw_fns = {r["flight_number"] for r in rotw_samples}
        filtered = rotw_samples + [r for r in filtered if r["flight_number"] not in rotw_fns]

    # Format result markdown
    tag_desc = f" · 條件：{airline or category or '精選推薦'}"
    lines = [
        f"🧭 **長榮航網精選推薦與聯營航線 (Route Recommendations{tag_desc})**\n",
        f"為機長推薦以下熱門與聯營班次，均支援 CrewCenter 直接簽派與 OFP 放行：\n"
    ]

    for idx, r in enumerate(filtered[:6], 1):
        fn = r.get("flight_number")
        dep = r.get("dep")
        dep_n = r.get("dep_name", dep)
        arr = r.get("arr")
        arr_n = r.get("arr_name", arr)
        ac = r.get("aircraft")
        dur = r.get("duration")
        al = r.get("airline")
        mul = r.get("multiplier", "1.0x")

        lines.append(
            f"**{idx}. 航班：`{fn}`** ｜ `{al}`\n"
            f"   • 航線起訖：**{dep} ({dep_n}) 🛫 ➔ {arr} ({arr_n}) 🛬**\n"
            f"   • 推薦機型：`{ac}` ｜ 預估飛行時間：`{dur}`\n"
            f"   • 營運加成：<span style='color: #34d399; font-weight: 600;'>{mul}</span>\n"
        )

    lines.append(
        "👉 **機長快速操作**：若有心儀的航線，您可以直接對我說「**幫我簽派 BR184**」或「**執飛 BR012**」，我將立刻為您生成 SimBrief 計畫！"
    )

    summary_text = "\n".join(lines).strip()
    return {
        "status": "SUCCESS",
        "recommended_count": len(filtered[:6]),
        "routes": filtered[:6],
        "summary": summary_text,
        "summary_text": summary_text
    }
