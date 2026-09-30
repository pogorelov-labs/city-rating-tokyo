"""
Hepburn romaji → Russian Cyrillic in the Polivanov system (CRTKY-107).

Used by scripts/generate-name-ru.py for stations without an established Russian
name. Station names are romanised without macrons, so long vowels are not
marked — which is also how established Russian names write them (Окубо,
Отемати).

The one thing romaji cannot tell apart is い after a vowel: a diphthong in
明治 → Мэйдзи, a separate mora in 大泉 → Оидзуми. `diphthong_i` picks which
preceding vowels turn a following "i" into "й". Measured against the 413
established Russian station names on Wikidata (2026-09-30), "ae" agrees best
(й in Касай, Мэйдзи; и in Оидзуми, Суидобаси is the residual error).
"""
import re
import unicodedata

_SYLLABLES = {
    # 3 letters
    "kya": "кя", "kyu": "кю", "kyo": "кё", "sha": "ся", "shu": "сю", "sho": "сё", "shi": "си",
    "she": "сэ", "cha": "тя", "chu": "тю", "cho": "тё", "chi": "ти", "che": "тэ", "tsu": "цу",
    "nya": "ня", "nyu": "ню", "nyo": "нё", "hya": "хя", "hyu": "хю", "hyo": "хё",
    "mya": "мя", "myu": "мю", "myo": "мё", "rya": "ря", "ryu": "рю", "ryo": "рё",
    "gya": "гя", "gyu": "гю", "gyo": "гё", "bya": "бя", "byu": "бю", "byo": "бё",
    "pya": "пя", "pyu": "пю", "pyo": "пё",
    # 2 letters
    "ja": "дзя", "ju": "дзю", "jo": "дзё", "ji": "дзи", "je": "дзэ", "fu": "фу",
    "ka": "ка", "ki": "ки", "ku": "ку", "ke": "кэ", "ko": "ко",
    "sa": "са", "su": "су", "se": "сэ", "so": "со",
    "ta": "та", "te": "тэ", "to": "то",
    "na": "на", "ni": "ни", "nu": "ну", "ne": "нэ", "no": "но",
    "ha": "ха", "hi": "хи", "he": "хэ", "ho": "хо",
    "ma": "ма", "mi": "ми", "mu": "му", "me": "мэ", "mo": "мо",
    "ya": "я", "yu": "ю", "yo": "ё",
    "ra": "ра", "ri": "ри", "ru": "ру", "re": "рэ", "ro": "ро",
    "wa": "ва", "wo": "о",
    "ga": "га", "gi": "ги", "gu": "гу", "ge": "гэ", "go": "го",
    "za": "дза", "zu": "дзу", "ze": "дзэ", "zo": "дзо",
    "da": "да", "de": "дэ", "do": "до",
    "ba": "ба", "bi": "би", "bu": "бу", "be": "бэ", "bo": "бо",
    "pa": "па", "pi": "пи", "pu": "пу", "pe": "пэ", "po": "по",
    # katakana for loanwords: ファ フィ フェ フォ ティ ディ
    "fa": "фа", "fi": "фи", "fe": "фэ", "fo": "фо", "ti": "ти", "di": "ди",
}
_VOWELS = {"a": "а", "i": "и", "u": "у", "e": "э", "o": "о"}
_SOKUON = {"k": "к", "s": "с", "t": "т", "p": "п", "g": "г", "d": "д", "b": "б", "z": "д", "f": "ф", "h": "х", "j": "д", "m": "м", "r": "р", "c": "т"}

# Words with a conventional Russian form that strict Polivanov does not give.
CONVENTIONAL = {"tokyo": "Токио", "yokohama": "Иокогама"}
# English words in station names: romanise their katakana reading instead
# (Tama-Plaza → Тама-Пураза, as たまプラーザ is pronounced).
LOANWORDS = {"isle": "airu", "teleport": "terepoto", "center": "senta", "centre": "senta",
             "sports": "supotsu", "sport": "supotsu", "land": "rando",
             "plaza": "puraza", "tennis": "tenisu", "campus": "kyanpasu", "laketown": "reikutaun",
             "central": "sentoraru", "park": "paku", "seaside": "shisaido", "socio": "soshio",
             "telecom": "terekomu", "skytree": "sukaitsuri", "newtown": "nyutaun",
             "fujifilm": "fujifirumu", "island": "airando"}
# Particles and the 前 "in front of" suffix stay lowercase inside a name, as the
# established names write them (Тёкоку-но-Мори, Ои-Кэйбадзё-маэ).
LOWERCASE = {"no", "ga", "mae"}


def _plain(text: str) -> str:
    """Drop macrons/circumflexes: Ōkubo → Okubo."""
    return "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))


def word(w: str, diphthong_i: str = "ae") -> str:
    """One romaji word → Cyrillic, lowercase."""
    w = LOANWORDS.get(w.lower(), w.lower())
    out, i, prev = [], 0, None
    while i < len(w):
        c = w[i]
        if c == "'":
            i += 1
            continue
        if c == "n" and (i + 1 == len(w) or w[i + 1] not in "aiueoy"):
            out.append("нъ" if i + 1 < len(w) and w[i + 1] == "'" else "н")
            i, prev = i + 1, None
            continue
        if c == "h" and prev in _VOWELS and (i + 1 == len(w) or w[i + 1] not in "aiueoy"):
            i += 1  # "oh" long-vowel spelling: Inuboh → Инубо
            continue
        if c == "m" and (i + 1 == len(w) or w[i + 1] in "bmp"):  # Shim-Mikawashima
            out.append("м")
            i, prev = i + 1, None
            continue
        if w.startswith("tch", i) or (i + 1 < len(w) and c == w[i + 1] and c in _SOKUON):
            out.append(_SOKUON[c])  # small っ: double the next consonant
            i += 1
            continue
        for size in (3, 2):
            seg = w[i:i + size]
            if seg in _SYLLABLES:
                out.append(_SYLLABLES[seg])
                i, prev = i + size, seg[-1]
                break
        else:
            if c in _VOWELS:
                out.append("й" if c == "i" and prev is not None and prev in diphthong_i else _VOWELS[c])
                i, prev = i + 1, c
            else:
                out.append(c)  # not romaji; left visible for review
                i, prev = i + 1, None
    return "".join(out)


def reading_key(name: str) -> str:
    """Fold a Cyrillic name to compare it with a kana reading (CRTKY-134):
    ё/е, й/и, separators, vowel length and m/n before labials compare equal,
    and the conventional forms count as their strict ones (Токио = Токё)."""
    s = name.lower()
    for romaji, conventional in CONVENTIONAL.items():
        s = s.replace(conventional.lower(), word(romaji))
    s = re.sub(r"[^а-я0-9]|ъ", "", s.replace("ё", "е").replace("й", "и"))
    s = re.sub(r"(?<=[ею])у", "", s)            # long yōon: кёу → кё, сюу → сю
    s = re.sub(r"([аиуэоея])\1+", r"\1", s)     # doubled vowels: оо → о
    s = s.replace("оу", "о")                    # long o spelled out: тоукёу → токё
    return re.sub(r"м(?=[бпм])", "н", s)


def transliterate(name: str, diphthong_i: str = "ae") -> str:
    """A station name (words joined by hyphens/spaces) → Polivanov Cyrillic."""
    name = re.sub(r"[\u2010-\u2015\u2212]", "-", _plain(name).strip())  # dash variants
    parts = re.split(r"([-\s]+)", name)
    out = []
    for idx, part in enumerate(parts):
        if not part:
            continue
        if re.fullmatch(r"[-\s]+", part):
            # Russian joins the words of a station name with hyphens (Кэйсэй-Уэно,
            # not "Keisei Ueno"); a space only sets off a bracketed alias.
            nxt = parts[idx + 1] if idx + 1 < len(parts) else ""
            out.append(" " if nxt.startswith("(") or parts[idx - 1].endswith(")") else "-")
            continue
        key = part.lower().strip("'()")
        if part.isascii() and part.isalpha() and part.isupper() and len(part) >= 2:
            out.append(part)  # acronyms stay Latin: YRP-Ноби
            continue
        if key in CONVENTIONAL:
            out.append(CONVENTIONAL[key])
            continue
        cyr = word(part, diphthong_i)
        if not (idx > 0 and key in LOWERCASE):
            cyr = re.sub(r"[а-яё]", lambda m: m.group(0).upper(), cyr, count=1)  # "(дайни" → "(Дайни"
        out.append(cyr)
    return "".join(out)
