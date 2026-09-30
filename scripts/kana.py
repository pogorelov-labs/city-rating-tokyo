"""
Kana → Hepburn romaji, for checking station names against their reading
(CRTKY-134). Wikidata records each station's reading in kana (P1814); an
English or Russian name that disagrees with it is a misreading, whatever
source it came from.

`to_romaji` spells long vowels out (とうきょう → toukyou) and marks ん before a
vowel or y (しんおおくぼ → shin'ookubo). `romaji_key` folds what is only
spelling style, so one reading compares equal however it was romanised:
Shinbashi = Shimbashi, Ōkubo = Ookubo = Okubo, Inubō = Inuboh.
"""
import re
import unicodedata

_BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "i", "ゑ": "e", "を": "o", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ゔ": "vu", "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
}
_YOON = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
_SMALL_VOWEL = {"ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o"}


def _hiragana(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def _syllables(s: str) -> list:
    out, i = [], 0
    while i < len(s):
        c, nxt = s[i], s[i + 1:i + 2]
        if c in ("っ", "ー"):
            out.append(c)
            i += 1
        elif c in _BASE and nxt in _YOON:              # きょ → kyo, しゃ → sha
            stem = _BASE[c][:-1]
            out.append(stem + ("" if stem in ("sh", "ch", "j") else "y") + _YOON[nxt])
            i += 2
        elif c in _BASE and nxt in _SMALL_VOWEL:       # ふぁ → fa, てぃ → ti, うぃ → wi
            out.append((_BASE[c][:-1] or "w") + _SMALL_VOWEL[nxt])
            i += 2
        else:
            out.append(_BASE.get(c, ""))               # punctuation, digits, Latin drop out
            i += 1
    return out


def to_romaji(kana: str) -> str:
    """Hepburn romaji of a kana reading, without a trailing えき (駅)."""
    s = re.sub(r"えき$", "", _hiragana(unicodedata.normalize("NFKC", kana)))
    syl = _syllables(s)
    out = []
    for j, cur in enumerate(syl):
        nxt = next((x for x in syl[j + 1:] if x not in ("っ", "ー")), "")
        if cur == "っ":                                # small tsu doubles the consonant
            out.append("t" if nxt.startswith("ch") else nxt[:1])
        elif cur == "ー":                              # long-vowel mark repeats the vowel
            out.append(out[-1][-1] if out and out[-1][-1:] in tuple("aiueo") else "")
        elif cur == "n" and nxt[:1] in tuple("aiueoy"):  # ん before a vowel: shin'ookubo
            out.append("n'")
        else:
            out.append(cur)
    return "".join(out)


def romaji_key(s: str) -> str:
    """Fold spelling style: case, macrons, separators, m/n before b/m/p, vowel length."""
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    s = re.sub(r"m(?=[bmp])", "n", s)
    s = re.sub(r"([aiueo])\1+", r"\1", s)
    s = s.replace("ou", "o")
    return re.sub(r"oh(?![aiueoy])", "o", s)


def readings(kanas) -> set:
    """romaji_key of each kana reading a station has."""
    return {romaji_key(to_romaji(k)) for k in kanas}
