import sys, json, threading, time, tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, "/home/claude/yt-guard")
S = "/tmp/claude-0/-home-claude/28463d6f-c55d-5b32-8136-82f75c14ab3d/scratchpad/samples/"
state = {"polls": 0, "gen": 0, "uploaded": 0, "keys": set(), "429_sent": False}
ANALYSIS = {"detected_format":"short","summary":"ویدیوی تست","language_of_video":"fa","overall_risk_score":30,
 "ai_usage":{"likely_ai_voice":True,"likely_ai_visuals":False,"likely_ai_music":False,"realistic_enough_to_mislead":False,"confidence":0.7,"evidence":"صدای یکنواخت"},
 "disclosure":{"required":"maybe","reason":"صدا شبیه TTS","suggested_description_text":"این ویدیو از صدای AI استفاده می‌کند."},
 "findings":[{"rule_id":"copyright_music","severity":"medium","timestamp":"00:05","issue":"موزیک مشکوک","evidence":"آهنگ تجاری","fix":"جایگزین کن"},
             {"rule_id":"NOT_A_RULE","severity":"weird","timestamp":None,"issue":"x","evidence":"","fix":""}],
 "copyright_suspects":[{"type":"music","timestamp":"00:05","description":"آهنگ","advice":"حذف"}],
 "retention":{"hook_score":4,"hook_comment":"ضعیف","notes":[{"timestamp":"00:00","note":"شروع کند"}]},
 "positives":["کیفیت خوب"],
 "follow_up_questions":[{"id":"q1","question":"صدا AI است؟","why":"برای افشا","options":["بله","خیر"]}]}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, obj, code=200, hdr=None):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type","application/json"); self.send_header("Content-Length", str(len(b)))
        for k,v in (hdr or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        state["keys"].add(self.headers.get("x-goog-api-key"))
        if self.path.startswith("/v1beta/models"):
            return self._j({"models":[{"name":"models/gemini-2.5-flash","supportedGenerationMethods":["generateContent"]},{"name":"models/embedding-001","supportedGenerationMethods":["embedContent"]}]})
        if self.path.startswith("/v1beta/files/"):
            state["polls"] += 1
            return self._j({"name":"files/abc","uri":f"http://127.0.0.1:{PORT}/files/abc","state":"ACTIVE","mimeType":"video/mp4"})
        self._j({}, 404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(n)
        state["keys"].add(self.headers.get("x-goog-api-key"))
        if self.path == "/upload/v1beta/files":
            return self._j({}, hdr={"X-Goog-Upload-URL": f"http://127.0.0.1:{PORT}/upload-session"})
        if self.path == "/upload-session":
            state["uploaded"] = n
            return self._j({"file":{"name":"files/abc","uri":f"http://127.0.0.1:{PORT}/files/abc","state":"PROCESSING","mimeType":"video/mp4"}})
        if ":generateContent" in self.path:
            j = json.loads(body)
            if not state["429_sent"]:
                state["429_sent"] = True
                return self._j({"error":{"code":429,"details":[{"retryDelay":"1s"}]}}, 429)
            state["gen"] += 1
            txt = j["contents"][0]["parts"][1]["text"]
            if j["generationConfig"].get("responseMimeType") == "application/json":
                a = dict(ANALYSIS)
                if "CREATOR CLARIFICATIONS" in txt: a = dict(a, overall_risk_score=20, follow_up_questions=[])
                text = "```json\n" + json.dumps(a, ensure_ascii=False) + "\n```"
            else:
                text = "تیتر ۱\nتیتر ۲"
            return self._j({"candidates":[{"content":{"parts":[{"text":text}]}}]})
        self._j({}, 404)
srv = HTTPServer(("127.0.0.1", 0), H); PORT = srv.server_port
threading.Thread(target=srv.serve_forever, daemon=True).start()

from ytguard.storage import Settings, History
from ytguard.workers import AnalyzeWorker, FollowUpWorker, ToolWorker, ModelsWorker
from ytguard.questionnaire import DEFAULT_ANSWERS
tmp = tempfile.mkdtemp()
from pathlib import Path
st = Settings(Path(tmp)/"s.json"); st["gemini_key"]="TESTKEY"; st["gemini_base"]=f"http://127.0.0.1:{PORT}"
hist = History(Path(tmp)/"h.json")
prog = []
ans = dict(DEFAULT_ANSWERS, ai_level="mostly", ai_voice="generic_tts", niche="health", third_party_music="popular_song")
w = AnalyzeWorker(st, hist, S+"static_short.mp4", "short", ans, True, None)
w.progress.connect(lambda p,t: prog.append((p,t)))
rep = w.work()
print("score", rep["score"], rep["verdict"], "findings", len(rep["findings"]), "ai_error:", repr(rep["ai_error"]))
print("upload bytes", state["uploaded"], "(orig", __import__("os").path.getsize(S+"static_short.mp4"), ")")
print("rule ids:", sorted({f['rule_id'] for f in rep["findings"]}))
print("sev set:", sorted({f['severity'] for f in rep["findings"]}), "followups:", len(rep["ai"]["follow_up_questions"]))
print("progress seq:", [p for p,_ in prog][:3], "...", prog[-1])
rep2 = FollowUpWorker(st, rep, [{"question":"صدا AI است؟","answer":"بله"}], rep["ref"]).work()
print("followup score", rep2["score"], "followups", len(rep2["ai"]["follow_up_questions"]), "gen calls", state["gen"])
tw = ToolWorker(st, S+"static_short.mp4", "titles", "fa", "", rep["ref"]).work()
print("tool:", tw["text"].replace("\n"," | "))
print("models:", ModelsWorker(st, "gemini").work())
print("keys seen:", state["keys"])
# error mapping: wrong base -> nice message
st["gemini_base"]="http://127.0.0.1:1"
try: ModelsWorker(st,"gemini").work()
except Exception as e: print("conn error msg:", e)
from ytguard import report as R
slim = {k:v for k,v in rep.items() if k not in ("ref",)}
Path(S+"../rep.json").write_text(json.dumps(slim, ensure_ascii=False))
Path(S+"../rep.html").write_text(R.to_html(rep), encoding="utf-8"); Path(S+"../rep.md").write_text(R.to_markdown(rep), encoding="utf-8")
print("exported ok", len(R.to_json(rep)))
