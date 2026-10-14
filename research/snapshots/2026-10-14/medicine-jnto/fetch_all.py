#!/usr/bin/env python3
"""Fetch JNTO emergency guide search.php for all 47 prefectures, eng + jpn."""
import json, random, string, subprocess, sys, time, pathlib

PREFS = [
 ("a01_hokkaido","Hokkaido"),("a02_aomori","Aomori"),("a03_akita","Akita"),("a04_iwate","Iwate"),
 ("a05_miyagi","Miyagi"),("a06_yamagata","Yamagata"),("a07_fukushima","Fukushima"),
 ("a08_tokyo","Tokyo"),("a09_ibaraki","Ibaraki"),("a10_tochigi","Tochigi"),("a11_gunma","Gunma"),
 ("a12_saitama","Saitama"),("a13_chiba","Chiba"),("a14_kanagawa","Kanagawa"),
 ("a15_yamanashi","Yamanashi"),("a16_nagano","Nagano"),("a17_nigata","Niigata"),("a18_toyama","Toyama"),
 ("a19_ishikawa","Ishikawa"),("a20_fukui","Fukui"),("a21_shizuoka","Shizuoka"),
 ("a22_aichi","Aichi"),("a23_gifu","Gifu"),("a24_mie","Mie"),
 ("a25_kyoto","Kyoto"),("a26_shiga","Shiga"),("a27_nara","Nara"),("a28_wakayama","Wakayama"),
 ("a29_osaka","Osaka"),("a30_hyogo","Hyogo"),("a31_okayama","Okayama"),("a32_hiroshima","Hiroshima"),
 ("a33_yamaguchi","Yamaguchi"),("a34_tottori","Tottori"),("a35_shimane","Shimane"),
 ("a36_kagawa","Kagawa"),("a37_tokushima","Tokushima"),("a38_kochi","Kochi"),("a39_ehime","Ehime"),
 ("a40_fukuoka","Fukuoka"),("a41_saga","Saga"),("a42_nagasaki","Nagasaki"),("a43_kumamoto","Kumamoto"),
 ("a44_oita","Oita"),("a45_miyazaki","Miyazaki"),("a46_kagoshima","Kagoshima"),("a47_okinawa","Okinawa"),
]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE = "https://www.jnto.go.jp/emergency"
outdir = pathlib.Path("raw")

def randstr(n=8):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def fetch(code, slang, attempt=1):
    qs = randstr()
    r = subprocess.run([
        "curl", "-sS", "--max-time", "60",
        "-A", UA,
        "-H", f"Referer: {BASE}/eng/mi_guide.html",
        "-H", "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-o", str(outdir / f"{code}_{slang}.json"),
        "-w", "%{http_code}",
        "-X", "POST", f"{BASE}/search.php?{qs}",
        "--data", f"search-lang={slang}&location=&lat=&lng=&cb-area={code}&freeword=",
    ], capture_output=True, text=True)
    http = r.stdout.strip()
    try:
        data = json.loads((outdir / f"{code}_{slang}.json").read_text(encoding="utf-8"))
        ok = http == "200" and "rdata" in data
    except Exception:
        ok = False
        data = None
    return ok, http, data

results = {}
fails = []
for code, name in PREFS:
    for slang in ("eng", "jpn"):
        ok, http, data = fetch(code, slang)
        tries = 1
        while not ok and tries < 4:
            time.sleep(2 * tries)
            ok, http, data = fetch(code, slang)
            tries += 1
        n = len(data["rdata"]) if ok else -1
        results[(code, slang)] = n
        if not ok:
            fails.append((code, slang, http))
        print(f"{code:16s} {slang}  HTTP {http}  rows={n}  tries={tries}", flush=True)
        time.sleep(0.7)  # be polite

print("\nSUMMARY")
total_e = sum(v for (c, s), v in results.items() if s == "eng")
total_j = sum(v for (c, s), v in results.items() if s == "jpn")
print("eng total:", total_e, "jpn total:", total_j, "failures:", fails)
