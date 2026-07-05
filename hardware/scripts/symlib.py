"""AuraBip — Hilfsmodul: KiCad-Symbol-Bibliotheken lesen (S-Expression-Parser).

Liest Symboldefinitionen aus .kicad_sym-Dateien, liefert Pin-Listen
(Nummer, Name, Typ, Position, Rotation) und den Roh-Text fuers Einbetten.
"""

import re

KICAD_SYM_DIR = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"


def tokenize(text):
    """S-Expression-Tokenizer: liefert '(', ')' und Atome (Strings dequoted)."""
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            yield c
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1]); j += 2
                elif text[j] == '"':
                    break
                else:
                    buf.append(text[j]); j += 1
            yield '"' + "".join(buf)
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            yield text[i:j]
            i = j


def parse(text):
    """Parst S-Expression zu verschachtelten Listen. Strings behalten '\"'-Prefix."""
    stack = [[]]
    for tok in tokenize(text):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok)
    return stack[0]


def _atom(x):
    return x[1:] if isinstance(x, str) and x.startswith('"') else x


def extract_symbol_text(lib_path, symbol_name):
    """Roh-Text einer Top-Level-Symboldefinition (fuer lib_symbols-Einbettung)."""
    with open(lib_path, "r", encoding="utf-8") as f:
        content = f.read()
    for pat in (f'(symbol "{symbol_name}"',):
        start = content.find(pat)
        if start != -1:
            break
    if start == -1:
        raise ValueError(f"Symbol '{symbol_name}' nicht in {lib_path}")
    depth = 0
    for i in range(start, len(content)):
        if content[i] == "(":
            depth += 1
        elif content[i] == ")":
            depth -= 1
            if depth == 0:
                return content[start:i + 1]
    raise ValueError("unbalanced")


def symbol_pins(lib_path, symbol_name):
    """Alle Pins eines Symbols (inkl. Sub-Units): Liste von Dicts.
    Folgt (extends "Basis") auf das Elternsymbol in derselben Lib."""
    text = extract_symbol_text(lib_path, symbol_name)
    m = re.search(r'\(extends\s+"([^"]+)"\)', text)
    if m:
        return symbol_pins(lib_path, m.group(1))
    tree = parse(text)

    pins = []

    def walk(node):
        if not isinstance(node, list) or not node:
            return
        if node[0] == "pin":
            p = {"etype": _atom(node[1]), "shape": _atom(node[2])}
            for sub in node:
                if isinstance(sub, list):
                    if sub[0] == "at":
                        p["x"] = float(_atom(sub[1]))
                        p["y"] = float(_atom(sub[2]))
                        p["rot"] = float(_atom(sub[3])) if len(sub) > 3 else 0.0
                    elif sub[0] == "name":
                        p["name"] = _atom(sub[1])
                    elif sub[0] == "number":
                        p["number"] = _atom(sub[1])
                    elif sub[0] == "length":
                        p["length"] = float(_atom(sub[1]))
            pins.append(p)
        else:
            for sub in node:
                walk(sub)

    walk(tree)
    return pins


if __name__ == "__main__":
    import sys
    lib, name = sys.argv[1], sys.argv[2]
    path = lib if lib.endswith(".kicad_sym") else rf"{KICAD_SYM_DIR}\{lib}.kicad_sym"
    for p in symbol_pins(path, name):
        print(f"  {p.get('number'):>4} {p.get('name','?'):<12} {p.get('etype'):<14} at=({p.get('x')},{p.get('y')}) rot={p.get('rot')}")
