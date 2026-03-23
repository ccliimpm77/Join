#!/usr/bin/env python3
"""
fix_epg.py — Correttore automatico XMLTV per join.epg
======================================================
Correzioni applicate:
  1. Timezone mista (+0100/+0000) → normalizzazione a +0100 (CET/CEST)
  2. Sovrapposizioni programmi → rimozione duplicati sovrapposti
  3. xmltv_ns malformato (anno invece stagione) → rimozione tag non validi
  4. <rating> senza attributo system → aggiunta system="age"
  5. Channel ID 'Super!' → rinomina in 'Super' (carattere ! rimosso)
  6. Channel ID 'Radio105TV.it' → normalizzazione stile a 'Radio 105 TV'
  7. Capitalizzazione display-name ('boing' → 'Boing', 'Rai yoyo' → 'Rai Yoyo')
  8. Rimozione icone duplicate nello stesso canale

Uso:
  python3 fix_epg.py                          # legge URL, scrive join.epg
  python3 fix_epg.py --input file.epg        # legge file locale
  python3 fix_epg.py --output out.epg        # scrive su file diverso
  python3 fix_epg.py --dry-run               # mostra solo il report senza scrivere
  python3 fix_epg.py --timezone +0000        # normalizza su UTC invece di CET
"""

import argparse
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

SOURCE_URL = "https://raw.githubusercontent.com/ccliimpm77/Join/refs/heads/main/join.epg"
DEFAULT_OUTPUT = "join.epg"

# ─── Timezone helpers ────────────────────────────────────────────────────────

def parse_xmltv_ts(ts: str) -> datetime:
    """Parsa un timestamp XMLTV tipo '20260323005800 +0100' in un datetime aware."""
    ts = ts.strip()
    dt_part, tz_part = ts[:14], ts[15:]
    dt = datetime.strptime(dt_part, "%Y%m%d%H%M%S")
    sign = 1 if tz_part[0] == '+' else -1
    h, m = int(tz_part[1:3]), int(tz_part[3:5])
    offset = timezone(timedelta(hours=sign * h, minutes=sign * m))
    return dt.replace(tzinfo=offset)

def format_xmltv_ts(dt: datetime, target_tz_str: str) -> str:
    """Converte un datetime aware nel formato XMLTV con la timezone target."""
    sign = '+' if not target_tz_str.startswith('-') else '-'
    h = int(target_tz_str[1:3])
    m = int(target_tz_str[3:5])
    offset = timezone(timedelta(hours=(1 if sign == '+' else -1) * h + m / 60))
    dt_local = dt.astimezone(offset)
    return dt_local.strftime(f"%Y%m%d%H%M%S {target_tz_str}")

# ─── xmltv_ns validation ─────────────────────────────────────────────────────

VALID_NS_RE = re.compile(r'^\d* \. \d* \. \d*$')

def is_valid_xmltv_ns(value: str) -> bool:
    """True se il valore rispetta il formato 'S . E . P' (es. '2 . 6 .')."""
    v = (value or '').strip()
    if not VALID_NS_RE.match(v):
        return False
    parts = [p.strip() for p in v.split('.')]
    # Parte 0 = stagione (0-based, non un anno a 4 cifre)
    if parts[0] and len(parts[0]) == 4 and parts[0].isdigit() and int(parts[0]) > 100:
        return False  # è un anno, non una stagione
    return True

# ─── Core fixes ──────────────────────────────────────────────────────────────

def fix_channel_ids(root: ET.Element, stats: dict) -> dict:
    """
    Restituisce una mappa old_id → new_id per le rinomina degli ID canale.
    Applica le correzioni direttamente sugli elementi <channel>.
    """
    renames = {
        "Super!": "Super",
        "Radio105TV.it": "Radio 105 TV",
    }
    capitalize_dn = {
        "boing": "Boing",
        "Rai yoyo": "Rai Yoyo",
    }

    applied_renames = {}
    for ch in root.findall("channel"):
        old_id = ch.get("id", "")

        # Rinomina ID
        if old_id in renames:
            new_id = renames[old_id]
            ch.set("id", new_id)
            applied_renames[old_id] = new_id
            stats["channel_id_renamed"] += 1

        # Capitalizza display-name
        for dn in ch.findall("display-name"):
            text = dn.text or ""
            if text in capitalize_dn:
                dn.text = capitalize_dn[text]
                stats["displayname_capitalized"] += 1

        # Rimuovi icone duplicate nello stesso canale
        icons = ch.findall("icon")
        seen_srcs = set()
        for icon in icons:
            src = icon.get("src", "")
            if src in seen_srcs:
                ch.remove(icon)
                stats["duplicate_icons_removed"] += 1
            else:
                seen_srcs.add(src)

    return applied_renames

def fix_programmes(root: ET.Element, target_tz: str, renames: dict, stats: dict):
    """Applica tutte le correzioni sui <programme>."""
    programmes = root.findall("programme")

    # Raggruppa per canale per rilevare sovrapposizioni
    by_channel = defaultdict(list)
    for p in programmes:
        channel = renames.get(p.get("channel", ""), p.get("channel", ""))
        by_channel[channel].append(p)

    to_remove = set()  # elementi da rimuovere (id Python)

    for channel, progs in by_channel.items():
        # Converti e ordina per start
        parsed = []
        for p in progs:
            try:
                start_dt = parse_xmltv_ts(p.get("start", ""))
                stop_dt  = parse_xmltv_ts(p.get("stop",  ""))
                parsed.append((start_dt, stop_dt, p))
            except Exception:
                parsed.append((None, None, p))

        parsed.sort(key=lambda x: x[0] or datetime.min.replace(tzinfo=timezone.utc))

        # Rileva sovrapposizioni con loop iterativo (gestisce catene a cascata)
        changed = True
        while changed:
            changed = False
            clean = [x for x in parsed if id(x[2]) not in to_remove]
            for i in range(len(clean) - 1):
                s0, e0, p0 = clean[i]
                s1, e1, p1 = clean[i + 1]
                if s0 is None or s1 is None:
                    continue
                if s1 < e0:
                    # Tiene il programma con durata maggiore; in caso di parità, il secondo
                    dur0 = (e0 - s0).total_seconds() if e0 else 0
                    dur1 = (e1 - s1).total_seconds() if e1 else 0
                    if dur0 >= dur1:
                        to_remove.add(id(p1))
                    else:
                        to_remove.add(id(p0))
                    stats["overlaps_removed"] += 1
                    changed = True
                    break  # riparti dal ciclo dopo ogni rimozione

    # Applica per ogni <programme>
    for p in programmes:
        # Aggiorna channel ID se rinominato
        old_ch = p.get("channel", "")
        if old_ch in renames:
            p.set("channel", renames[old_ch])

        # Normalizza timezone
        for attr in ("start", "stop"):
            val = p.get(attr, "")
            if val:
                try:
                    dt = parse_xmltv_ts(val)
                    p.set(attr, format_xmltv_ts(dt, target_tz))
                    stats["timestamps_normalized"] += 1
                except Exception:
                    pass

        # Rimuovi <episode-num system="xmltv_ns"> malformati
        for en in p.findall("episode-num"):
            if en.get("system") == "xmltv_ns":
                if not is_valid_xmltv_ns(en.text or ""):
                    p.remove(en)
                    stats["invalid_xmltv_ns_removed"] += 1

        # Aggiungi system="age" ai <rating> che ne sono privi
        for r in p.findall("rating"):
            if not r.get("system"):
                r.set("system", "age")
                stats["rating_system_added"] += 1

    # Rimuovi i programmi sovrapposti dall'albero
    for p in programmes:
        if id(p) in to_remove:
            root.remove(p)

# ─── Pretty-print XML ────────────────────────────────────────────────────────

def indent_xml(elem: ET.Element, level: int = 0):
    """Aggiunge indentazione leggibile all'albero XML (in-place)."""
    pad = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = pad
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = pad
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = pad
    if not level:
        elem.tail = "\n"

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Correttore XMLTV per join.epg")
    parser.add_argument("--input",    default=None,       help="File EPG locale (default: scarica da GitHub)")
    parser.add_argument("--output",   default=DEFAULT_OUTPUT, help=f"File di output (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--timezone", default="+0100",    help="Timezone target, es. +0100 o +0000 (default: +0100)")
    parser.add_argument("--dry-run",  action="store_true", help="Mostra solo il report, non scrive")
    args = parser.parse_args()

    # Validazione timezone
    if not re.match(r'^[+-]\d{4}$', args.timezone):
        print(f"[ERRORE] Formato timezone non valido: '{args.timezone}'. Usare es. +0100 o +0000", file=sys.stderr)
        sys.exit(1)

    # Lettura
    if args.input:
        print(f"[INFO] Lettura da file locale: {args.input}")
        with open(args.input, "rb") as f:
            raw = f.read()
    else:
        print(f"[INFO] Download da: {SOURCE_URL}")
        try:
            req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "fix_epg/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except Exception as e:
            print(f"[ERRORE] Download fallito: {e}", file=sys.stderr)
            sys.exit(1)

    # Parse XML
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"[ERRORE] XML non valido: {e}", file=sys.stderr)
        sys.exit(1)

    # Statistiche
    stats = defaultdict(int)
    stats["channels_before"] = len(root.findall("channel"))
    stats["programmes_before"] = len(root.findall("programme"))

    # ── Applica correzioni ──
    print("[INFO] Correzione ID canale e display-name...")
    renames = fix_channel_ids(root, stats)

    print(f"[INFO] Correzione programmi (timezone target: {args.timezone})...")
    fix_programmes(root, args.timezone, renames, stats)

    stats["channels_after"] = len(root.findall("channel"))
    stats["programmes_after"] = len(root.findall("programme"))

    # ── Report ──
    print()
    print("=" * 55)
    print("  REPORT CORREZIONI")
    print("=" * 55)
    print(f"  Canali:                        {stats['channels_before']} → {stats['channels_after']}")
    print(f"  Programmi:                     {stats['programmes_before']} → {stats['programmes_after']}")
    print(f"  Timestamp normalizzati:        {stats['timestamps_normalized']}")
    print(f"  Sovrapposizioni rimosse:       {stats['overlaps_removed']}")
    print(f"  xmltv_ns malformati rimossi:   {stats['invalid_xmltv_ns_removed']}")
    print(f"  <rating> system= aggiunti:     {stats['rating_system_added']}")
    print(f"  Channel ID rinominati:         {stats['channel_id_renamed']}")
    if renames:
        for old, new in renames.items():
            print(f"    '{old}' → '{new}'")
    print(f"  Display-name capitalizzati:    {stats['displayname_capitalized']}")
    print(f"  Icone duplicate rimosse:       {stats['duplicate_icons_removed']}")
    print("=" * 55)

    if args.dry_run:
        print("[INFO] --dry-run: nessun file scritto.")
        return

    # ── Scrittura ──
    indent_xml(root)
    tree = ET.ElementTree(root)
    ET.register_namespace("", "")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("<?xml version='1.0' encoding='utf-8'?>\n")
        tree.write(f, encoding="unicode", xml_declaration=False)

    print(f"[OK] File scritto: {args.output}")

if __name__ == "__main__":
    main()
