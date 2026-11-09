import sys, json, time
sys.path.insert(0, "/home/claude/yt-guard")
from ytguard.local_checks import *
S = "/tmp/claude-0/-home-claude/28463d6f-c55d-5b32-8136-82f75c14ab3d/scratchpad/samples/"
ff = find_ffmpeg()
print("ffmpeg:", ff, "ffprobe:", find_ffprobe(ff))
for name in ("long_test.mp4", "static_short.mp4"):
    info = media_info(S+name, ff)
    fmt, amb = guess_format(info)
    print("\n==", name, {k: info[k] for k in ("duration","width","height","fps","orientation","has_audio")}, fmt, amb)
    t=time.time()
    r = run_local_checks(S+name, fmt, ff)
    print("time %.1fs"%(time.time()-t), "audio:", {k: r["audio"].get(k) for k in ("lufs","true_peak","silence_total")}, "metrics:", r["metrics"], "meta:", r["meta"])
    for f in r["findings"]:
        print(" -", f["severity"], f["rule_id"], "|", f["issue"], "|", f["evidence"])
# fallback path without ffprobe
import ytguard.local_checks as lc
lc.find_ffprobe = lambda ff: None
i2 = lc.media_info(S+"static_short.mp4", ff)
print("\nfallback parse:", {k: i2[k] for k in ("duration","width","height","fps","has_audio","orientation")}, i2["tags"].get("comment"))
