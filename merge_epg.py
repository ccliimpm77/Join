import requests
import xml.etree.ElementTree as ET
import os
import re

def load_bad_strings(filepath):
    """Carica la lista di stringhe da rimuovere."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def clean_non_standard_symbols(text):
    """
    Rimuove caratteri invisibili, Emoji, simboli non standard e caratteri di controllo.
    Mantiene: Lettere (anche accentate), Numeri, Spazi e Punteggiatura comune.
    """
    if not text:
        return text
    
    # Rimuove caratteri di controllo (0-31 e 127-159) e caratteri invisibili comuni
    text = re.sub(r'[^\x20-\x7E\u00A0-\u00FF]', '', text)
    
    # Rimuove spazi doppi creati dalla pulizia
    text = " ".join(text.split()).strip()
    return text

def aggressive_clean(elem, bad_strings):
    """
    Pulisce l'elemento in modo profondo.
    """
    if elem.text:
        for s in bad_strings:
            elem.text = elem.text.replace(s, "")
        elem.text = clean_non_standard_symbols(elem.text)
    else:
        elem.text = None

    if elem.tail:
        elem.tail = None

    for attr_name, attr_value in elem.attrib.items():
        if attr_value.lower() == 'de':
            elem.set(attr_name, 'it')
        
        if isinstance(attr_value, str):
            elem.set(attr_name, clean_non_standard_symbols(attr_value))

    for child in list(elem):
        if child.tag == 'icon':
            elem.remove(child)
            continue
        aggressive_clean(child, bad_strings)

def normalize_name_for_match(name):
    """Normalizza solo per il confronto."""
    if not name: return ""
    name = name.lower().replace(".it", "")
    return re.sub(r'[^a-z0-9]', '', name)

def apply_m3u_mapping(unique_channels, all_programmes, m3u_url):
    """Sincronizza ID e Nomi EPG con il case esatto del file M3U."""
    print(f"Sincronizzazione Case-Mismatch con M3U: {m3u_url}")
    try:
        r = requests.get(m3u_url, timeout=30)
        r.raise_for_status()
        m3u_content = r.text
        m3u_names = set(re.findall(r'tvg-name="([^"]+)"', m3u_content))
        m3u_mapping_dict = {normalize_name_for_match(n): n for n in m3u_names}
        
        final_id_map = {}
        for old_id, ch_elem in unique_channels.items():
            norm_id = normalize_name_for_match(old_id)
            dn_elem = ch_elem.find('display-name')
            norm_dn = normalize_name_for_match(dn_elem.text) if dn_elem is not None else ""

            if norm_id in m3u_mapping_dict:
                final_id_map[old_id] = m3u_mapping_dict[norm_id]
            elif norm_dn in m3u_mapping_dict:
                final_id_map[old_id] = m3u_mapping_dict[norm_dn]

        new_unique_channels = {}
        for old_id, ch_elem in unique_channels.items():
            if old_id in final_id_map:
                new_name = final_id_map[old_id]
                ch_elem.set('id', new_name)
                for dn in ch_elem.findall('display-name'):
                    ch_elem.remove(dn)
                new_dn = ET.SubElement(ch_elem, 'display-name')
                new_dn.text = new_name
                new_unique_channels[new_name] = ch_elem
            else:
                new_unique_channels[old_id] = ch_elem

        for prog in all_programmes:
            ch_id = prog.get('channel')
            if ch_id in final_id_map:
                prog.set('channel', final_id_map[ch_id])

        return new_unique_channels, all_programmes
    except Exception as e:
        print(f"Errore M3U: {e}")
        return unique_channels, all_programmes

def main():
    print("Inizio Sanificazione (No Icone - No Simboli Speciali)...")
    JOIN_FILE = 'join.txt'
    STRINGS_FILE = 'stringhe.txt'
    OUTPUT_FILE = 'join.epg'
    M3U_URL = "https://drive.google.com/uc?export=download&id=1owM9i05x7pJ03gOG_kA47NJ0GbH7dBgw"

    # Mappatura manuale per canali specifici
    MANUAL_ID_MAP = {
        "La7Cinema.it": "La7 Cinema",
        "RadioitaliaTV.it": "Radio Italia TV"
    }

    if not os.path.exists(JOIN_FILE): return
    bad_strings = load_bad_strings(STRINGS_FILE)
    
    with open(JOIN_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]
    
    unique_channels = {}
    all_programmes = []

    for url in urls:
        try:
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            
            # Processamento Canali
            for ch in root.findall('channel'):
                cid = ch.get('id')
                if not cid: continue
                
                # Applica correzione manuale ID se presente nella lista
                if cid in MANUAL_ID_MAP:
                    cid = MANUAL_ID_MAP[cid]
                    ch.set('id', cid)
                
                if cid not in unique_channels:
                    aggressive_clean(ch, bad_strings)
                    unique_channels[cid] = ch
            
            # Processamento Programmi
            for pr in root.findall('programme'):
                pid = pr.get('channel')
                if pid and pr.get('start'):
                    
                    # Applica correzione manuale ID anche ai programmi
                    if pid in MANUAL_ID_MAP:
                        pid = MANUAL_ID_MAP[pid]
                        pr.set('channel', pid)
                        
                    aggressive_clean(pr, bad_strings)
                    all_programmes.append(pr)
            
            print(f"OK: {url}")
        except Exception as e: print(f"Errore {url}: {e}")

    unique_channels, all_programmes = ap
