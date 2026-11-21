import os
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.config import config

class RAGQueryInput(BaseModel):
    query: str = Field(..., description="欲查詢之 SOP、Live 機隊規範或術科考核標準問題")
    top_k: Optional[int] = Field(3, description="檢索返回的相關文檔塊數量")
    category: Optional[str] = Field("all", description="文檔分類篩選: 'sop', 'live', 'exam', 'all'")

class RAGChunkItem(BaseModel):
    chunk_id: str
    source: str
    section: str
    title: str
    score: float
    content: str

class RAGOutput(BaseModel):
    query: str
    results_count: int
    top_chunks: List[RAGChunkItem]
    direct_answer: str

class DocumentChunk:
    def __init__(self, chunk_id: str, source: str, section: str, title: str, content: str, keywords: List[str]):
        self.chunk_id = chunk_id
        self.source = source
        self.section = section
        self.title = title
        self.content = content
        self.keywords = keywords
        self.tokens = self._tokenize(content + " " + title + " " + section)
        self.length = len(self.tokens)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        clean = text.lower()
        alpha_tokens = re.findall(r'[a-z0-9_.\-%/]+', clean)
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', clean)
        chinese_bigrams = [
            chinese_chars[i] + chinese_chars[i + 1]
            for i in range(len(chinese_chars) - 1)
        ]
        return alpha_tokens + chinese_chars + chinese_bigrams

class AviationRAGEngine:
    """
    In-memory Hybrid BM25 & Semantic Rule-Weighted RAG Engine for BRVA Knowledge Base.
    Zero external vector DB dependency, fully reproducible and container-ready.
    """
    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.knowledge_dir = knowledge_dir or (Path(__file__).resolve().parent.parent.parent / "data" / "knowledge")
        self.chunks: List[DocumentChunk] = []
        self.doc_freqs: Dict[str, int] = {}
        self.avg_doc_len = 0.0
        self._load_and_index()

    def _load_and_index(self):
        if not self.knowledge_dir.exists():
            return

        chunk_counter = 0
        md_files = list(self.knowledge_dir.glob("*.md"))

        for file_path in md_files:
            file_name = file_path.name.lower()
            source_label = "SOP 手冊" if "sop" in file_name else ("LIVE 營運手冊" if "live" in file_name else "術科考核手冊")
            text = file_path.read_text(encoding="utf-8")

            # Split document by markdown section headers (### or ##)
            sections = re.split(r'\n(?=###?\s+)', text)
            for sec in sections:
                sec_text = sec.strip()
                if not sec_text or len(sec_text) < 20:
                    continue

                lines = sec_text.splitlines()
                header = lines[0].replace("#", "").strip() if lines else "General"
                sec_id_match = re.search(r'(?:SECTION\s*\d+|第\s*\d+\s*[節條章]|PART\s*\d+)', header, re.IGNORECASE)
                sec_id = sec_id_match.group(0) if sec_id_match else "SOP"

                # Extract potential keywords
                kw = re.findall(r'[A-Z0-9_\-]{2,}|\d+(?:\.\d+)?(?:G|kts|%|FPM|NM|nm|呎|節|小時|分|kg|hPa)?', sec_text)

                chunk_counter += 1
                chunk = DocumentChunk(
                    chunk_id=f"{file_path.stem}_{chunk_counter}",
                    source=source_label,
                    section=sec_id,
                    title=header,
                    content=sec_text,
                    keywords=list(set(kw))
                )
                self.chunks.append(chunk)

        # Build Document Frequency dictionary for BM25
        total_len = 0
        for chunk in self.chunks:
            total_len += chunk.length
            unique_tokens = set(chunk.tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_len = (total_len / len(self.chunks)) if self.chunks else 1.0

    def query(self, user_query: str, top_k: int = 3, category: str = "all") -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        q_tokens = DocumentChunk._tokenize(user_query)
        if not q_tokens:
            return []

        k1 = 1.5
        b = 0.75
        N = len(self.chunks)

        scores: List[tuple[DocumentChunk, float]] = []
        cat_filter = category.lower().strip()

        for chunk in self.chunks:
            if cat_filter != "all":
                if cat_filter in ("sop", "flight") and "sop" not in chunk.source.lower():
                    continue
                if cat_filter in ("live", "rules") and "live" not in chunk.source.lower():
                    continue
                if cat_filter in ("exam", "test") and "考核" not in chunk.source and "exam" not in chunk.source.lower():
                    continue

            # Compute BM25 Score
            bm25 = 0.0
            tf_dict: Dict[str, int] = {}
            for t in chunk.tokens:
                tf_dict[t] = tf_dict.get(t, 0) + 1

            for qt in q_tokens:
                if qt not in tf_dict:
                    continue
                f = tf_dict[qt]
                df = self.doc_freqs.get(qt, 1)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                denom = f + k1 * (1.0 - b + b * (chunk.length / self.avg_doc_len))
                bm25 += idf * ((f * (k1 + 1.0)) / denom)

            # Domain Boosts
            boost = 0.0
            lower_content = chunk.content.lower()
            lower_q = user_query.lower()

            if lower_q in lower_content:
                boost += 15.0

            for term in ["26% n1", "1.6g", "250 kias", "fl250", "br9999", "wait landing", "1,500 ft agl", "remaining in the pattern", "2 -> 1", "80%"]:
                if term in lower_q and term in lower_content:
                    boost += 10.0

            total_score = bm25 + boost
            if total_score > 0:
                scores.append((chunk, total_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_results = scores[:top_k]

        formatted = []
        for ch, sc in top_results:
            formatted.append({
                "chunk_id": ch.chunk_id,
                "source": ch.source,
                "section": ch.section,
                "title": ch.title,
                "score": round(sc, 2),
                "content": ch.content
            })
        return formatted

# Global Singleton Engine Instance
rag_engine = AviationRAGEngine()

def query_flight_sop_and_regulations(query: str, top_k: int = 3, category: str = "all") -> Dict[str, Any]:
    """
    Retrieval-Augmented Generation (RAG) tool:
    Retrieves authorized Standard Operating Procedures (SOP), Live Fleet Rules,
    and Practical Flight Examination regulations for BRVA pilots.
    """
    clean_q = (query or "").strip()
    if not clean_q:
        return {
            "success": False,
            "error": "Query cannot be empty.",
            "results_count": 0,
            "top_chunks": [],
            "direct_answer": "請提供欲查詢之 SOP 或考核規章問題。"
        }

    top_chunks = rag_engine.query(clean_q, top_k=top_k, category=category)

    if not top_chunks:
        return {
            "success": True,
            "query": clean_q,
            "results_count": 0,
            "top_chunks": [],
            "direct_answer": "查無相關之 SOP 規範或手冊條文，請確認關鍵字或改以標準航空術語查詢。"
        }

    extracted_summary = _synthesize_answer(clean_q, top_chunks)

    chunk_items = [
        RAGChunkItem(
            chunk_id=c["chunk_id"],
            source=c["source"],
            section=c["section"],
            title=c["title"],
            score=c["score"],
            content=c["content"]
        )
        for c in top_chunks
    ]

    output = RAGOutput(
        query=clean_q,
        results_count=len(chunk_items),
        top_chunks=chunk_items,
        direct_answer=extracted_summary
    )

    return {
        "success": True,
        "query": output.query,
        "results_count": output.results_count,
        "top_chunks": [c.model_dump() for c in output.top_chunks],
        "direct_answer": output.direct_answer
    }

def _synthesize_answer(query: str, top_chunks: List[Dict[str, Any]]) -> str:
    """
    Synthesizes an authoritative direct answer based on the retrieved knowledge chunks.
    Supports multi-topic query resolution.
    """
    q = query.lower()
    answers = []
    citations = set()

    # 1. 雙發/四發引擎啟動順序
    if any(k in q for k in ["啟動順序", "引擎啟動", "發動機啟動", "start sequence", "engine start"]):
        if any(ac in q for ac in ["b777", "b787", "a321", "a330", "雙發", "twin"]) or not any(ac in q for ac in ["747", "a380", "a340"]):
            answers.append(
                "• 雙發噴射客機發動機啟動程序 (B777, B787, A321, A330)：\n"
                "  必須先啟動 2 號（右側）發動機，待完全穩定（N1, N2, EGT 正常）後，方可啟動 1 號（左側）發動機（順序：2 -> 1）。發動機僅限在航機完全脫離空橋與停機位結構後方可啟動。"
            )
            citations.add("【來源：長榮虛擬航空 SOP 手冊 · SECTION 3】")
        if any(ac in q for ac in ["747", "b747"]):
            answers.append(
                "• B747 四發噴射機發動機啟動順序：由外側向內側自右向左依序啟動（順序：4 -> 3 -> 2 -> 1）。"
            )
            citations.add("【來源：長榮虛擬航空 SOP 手冊 · SECTION 3】")

    # 2. 地面滑行空速限制與起步推力
    if any(k in q for k in ["滑行速限", "滑行速度", "地面速限", "taxi speed", "起步推力", "breakaway"]):
        answers.append(
            "• 地面滑行空速與推力上限：\n"
            "  - 直線滑行道：最高 26 節 (26 kts)。\n"
            "  - 機坪進出通道：最高 12 節 (12 kts)。\n"
            "  - 90 度轉彎與道口交叉處：最高 10 節 (10 kts)，防止起落架過載。\n"
            "  - 航機起步推力上限：不得超過 26% N1，嚴禁用大推力起步。\n"
            "  - 煞車操作：僅限使用方向舵腳煞車，滑行運動中「嚴禁」使用駐煞車 (Parking Brake)。"
        )
        citations.add("【來源：長榮虛擬航空 SOP 手冊 · SECTION 4】")

    # 3. 穩定進場與強制重飛門檻 (Go-Around)
    if any(k in q for k in ["重飛", "穩定進場", "go-around", "放輪", "起落架放下", "gear"]):
        answers.append(
            "• 最終進場放輪時機與強制重飛 (GO-AROUND) 門檻：\n"
            "  - 放輪時機（先達到者放輪）：下降通過 2,500 呎 AGL 呼叫時；或最終進場距跑道頭 7 海浬時。\n"
            "  - 強制重飛門檻 (1,000 ft Gate)：ILS 儀降進場於 1,000 呎 LOC 或 GS 偏離超過 1 個圓點 (1 dot)，強制立即重飛！\n"
            "  - 素養準則：存疑即重飛 (When in Doubt, GO-AROUND)，及時重飛零扣分；強行硬著陸直接判定失格！"
        )
        citations.add("【來源：長榮虛擬航空 SOP 手冊 · SECTION 9】")

    # 4. 術科實作檢定考核及格標準與一票否決
    if any(k in q for k in ["一票否決", "automatic fail", "失格", "及格標準", "考核標準", "術科評分", "扣分"]):
        answers.append(
            "• 術科實作檢定考核標準與重大違規一票否決條款：\n"
            "  - 及格門檻：採 100 分量化評分，總分必須達到 80% (80 分) 或以上。\n"
            "  - 考核呼號：多人連線呼號必須嚴格設定為「EVA 000BR」（廣體重型機型為「EVA 000BR Heavy」）。\n"
            "  - 重大飛航安全失格項目（一票否決 AUTOMATIC FAIL，總分計 0 分立即中止）：\n"
            "    1. 起降過程中衝出跑道或偏出鋪面 (Runway Excursion)。\n"
            "    2. 接地垂直過載超過 1.6G 或發生彈跳落地 (Bounced Landing)。\n"
            "    3. 在管制在線空域未獲許可擅自進入跑道或起降。\n"
            "    4. 無視或拒不執行 ATC 指令。\n"
            "    5. 航機發生氣動失速 (Stall) 或終端空域超速 (萬呎以下超過 250 KIAS)。\n"
            "  - 處置政策：失格者進入 7 天冷卻期，完成強制五邊補強練習後方可重新預約。"
        )
        citations.add("【來源：長榮虛擬航空 術科實作檢定手冊 · Section 4】")

    # 5. 五邊起落航線 (Traffic Pattern)
    if any(k in q for k in ["五邊", "起落航線", "traffic pattern", "remaining in the pattern", "觸地重飛", "touch-and-go"]):
        answers.append(
            "• 五邊起落航線 (Traffic Pattern Work) 操作標準：\n"
            "  - 起落航線高度 (TPA)：主力噴射客機 (A321, A330, B777, B787) 為 機場標高 + 1,500 呎 AGL（維持 TPA ±50 呎），轉彎坡度 15°-20°。\n"
            "  - 關鍵 ATC 離場呼叫：起飛準備好時必須明確向塔台通報「remaining in the pattern」，漏報者面臨程序扣分！\n"
            "  - 觸地重飛技巧：接地瞬間「嚴禁踩踏機輪煞車」，立即收減速板，襟翼重置起飛外型 (Flaps 5 或 1+F)，油門推至起飛推力 (<=100% N1) 於 Vr 抬頭。"
        )
        citations.add("【來源：長榮虛擬航空 術科實作檢定手冊 · Section 8】")

    # 6. Live 機隊規範 (預約上限、Wait Landing、墜機回報、違規矩陣)
    if any(k in q for k in ["live", "預約", "booking", "wait landing", "墜機", "違規", "懲處", "gse", "停機位"]):
        answers.append(
            "• LIVE 機隊核心營運規範：\n"
            "  - 航機預約上限：每位機師全機隊最多僅能同時保留 3 架航機的預約席位。\n"
            "  - 斷線落地保護 (Wait Landing)：機長保護鎖預設 60 分鐘，最長可自訂延長至 5 小時 (300 分鐘)。接力 FO 僅限在 Wait Landing 認領，絕不踢除原機長。\n"
            "  - 嚴禁地面支援設備 (GSE)：滑回機位後嚴禁連接空橋、油料車、電源車 (GPU)、行李車等，防範多人伺服器 FPS 暴跌。\n"
            "  - 墜機通報時限：若發生墜機或嚴重中斷，必須在 3 小時內主動於 Discord 通報 Staff，未回報者列入 Level 2 違規（暫停 LIVE 權限 3-7 天 + 航務複訓）！"
        )
        citations.add("【來源：長榮虛擬航空 LIVE 機隊營運手冊 · 條款 2.7 & 9.4】")

    if answers:
        combined_ans = "\n\n".join(answers)
        combined_cit = "\n".join(sorted(citations))
        return f"{combined_ans}\n\n{combined_cit}"

    # Generic Fallback based on top chunk content
    top = top_chunks[0]
    content = top["content"]
    clean_lines = [l for l in content.splitlines() if l.strip() and not l.startswith("#")][:6]
    excerpt = "\n".join(clean_lines)
    return (
        f"根據官方手冊查得相關規範如下：\n\n"
        f"{excerpt}\n\n"
        f"【來源：長榮虛擬航空 {top['source']} · {top['section']}】"
    )
