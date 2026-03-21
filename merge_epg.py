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

def aggressive_clean(elem, bad_strings):
    """Pulisce l'elemento in modo profondo (come da tua versione originale)."""
    if elem.text:
        for s in bad_strings:
            elem.text = elem.text.replace(s, "")
        elem.text = " ".join(elem.text.split()).strip()
    else:
        elem.text = None

    if elem.tail:
        elem.tail = None

    for attr_name, attr_value in elem.attrib.items():
        if attr_value.lower() == 'de':
            elem.set(attr_name, 'it')

    icon_count = 0
    for child in list(elem):
        if child.tag == 'icon':
            icon_count += 1
            if icon_count > 1:
                elem.remove(child)
                continue
        aggressive_clean(child, bad_strings)

def normalize_name(name):
    """Normalizza il nome per facilitare il matching (es: Rai 1 .it -> rai1)."""
    if not name: return ""
    name = name.lower()
    name = name.replace(".it", "")
    return re.sub(r'[^a-z0-9]', '', name)

def apply_m3u_mapping(unique_channels, all_programmes, m3u_url):
    """Sincronizza i channel ID dell'EPG con i tvg-name del file M3U."""
    print(f"Scaricamento M3U per mappatura nomi: {m3u_url}")
    try:
        r = requests.get(m3u_url, timeout=30)
        r.raise_for_status()
        m3u_content = r.text
        
        # Estrae tutti i tvg-name="Nome Canale" dall'M3U
        m3u_names = set(re.findall(r'tvg-name="([^"]+)"', m3u_content))
        print(f"Trovati {len(m3u_names)} nomi unici nell'M3U.")

        # Creiamo un dizionario di normalizzazione: { 'rai1': 'Rai 1 (TV)' }
        m3u_mapping_dict = {normalize_name(name): name for name in m3u_names}
        
        # Mappa finale: { 'ID_VECCHIO_EPG': 'NUOVO_NOME_M3U' }
        final_id_map = {}

        # 1. Trova le corrispondenze tra i canali EPG e i nomi M3U
        for old_id in list(unique_channels.keys()):
            norm_id = normalize_name(old_id)
            if norm_id in m3u_mapping_dict:
                new_id = m3u_mapping_dict[norm_id]
                final_id_map[old_id] = new_id
        
        if not final_id_map:
            print("Nessuna corrispondenza trovata tra M3U e EPG.")
            return unique_channels, all_programmes

        print(f"Mappati con successo {len(final_id_map)} canali su M3U.")

        # 2. Aggiorna i Canali (ID e Display Name)
        new_unique_channels = {}
        for old_id, channel_elem in unique_channels.items():
            if old_id in final_id_map:
                new_id = final_id_map[old_id]
                channel_elem.set('id', new_id)
                # Aggiorna o crea il display-name per farlo coincidere
                dn = channel_elem.find('display-name')
                if dn is None:
                    dn = ET.SubElement(channel_elem, 'display-name')
                dn.text = new_id
                new_unique_channels[new_id] = channel_elem
            else:
                # Se non c'è match, manteniamo il canale originale (come richiesto)
                new_unique_channels[old_id] = channel_elem

        # 3. Aggiorna i Programmi (Attributo channel)
        for prog in all_programmes:
            old_ch_id = prog.get('channel')
            if old_ch_id in final_id_map:
                prog.set('channel', final_id_map[old_ch_id])

        return new_unique_channels, all_programmes

    except Exception as e:
        print(f"ERRORE durante il mapping M3U: {e}")
        return unique_channels, all_programmes

def main():
    print("Inizio Sanificazione EPG Totale...")
    
    JOIN_FILE = 'join.txt'
    STRINGS_FILE = 'stringhe.txt'
    OUTPUT_FILE = 'join.epg'
    M3U_URL = "https://drive.google.com/uc?export=download&id=1owM9i05x7pJ03gOG_kA47NJ0GbH7dBgw"

    if not os.path.exists(JOIN_FILE):
        print(f"ERRORE: {JOIN_FILE} non trovato!")
        return

    bad_strings = load_bad_strings(STRINGS_FILE)

    with open(JOIN_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]
    
    unique_channels = {}
    all_programmes = []

    for url in urls:
        try:
            print(f"Scaricamento: {url}")
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            
            root_input = ET.fromstring(r.content)
            
            for channel in root_input.findall('channel'):
                ch_id = channel.get('id')
                if not ch_id: continue
                
                if ch_id not in unique_channels:
                    if channel.find('display-name') is None:
                        dn = ET.SubElement(channel, 'display-name')
                        dn.text = ch_id
                    
                    aggressive_clean(channel, bad_strings)
                    unique_channels[ch_id] = channel
            
            for prog in root_input.findall('programme'):
                if not prog.get('start') or not prog.get('channel'):
                    continue
                
                aggressive_clean(prog, bad_strings)
                all_programmes.append(prog)
                
            print(f"OK: {url} elaborato.")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # --- NUOVA LOGICA DI MAPPATURA M3U ---
    unique_channels, all_programmes = apply_m3u_mapping(unique_channels, all_programmes, M3U_URL)
    # -------------------------------------

    # COSTRUZIONE NUOVO FILE
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Ultimate-Sanitizer-V4-Mapped')

    print("Ordinamento canali...")
    sorted_ids = sorted(unique_channels.keys(), key=lambda x: x.lower())
    for cid in sorted_ids:
        new_root.append(unique_channels[cid])

    print("Ordinamento programmi...")
    all_programmes.sort(key=lambda p: (p.get('channel', '').lower(), p.get('start', '')))
    
    seen_progs = set()
    for prog in all_programmes:
        prog_id = f"{prog.get('channel')}_{prog.get('start')}"
        if prog_id not in seen_progs:
            new_root.append(prog)
            seen_progs.add(prog_id)

    print("Scrittura file finale...")
    tree = ET.ElementTree(new_root)
    
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        pass

    with open(OUTPUT_FILE, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print(f"SUCCESSO: {OUTPUT_FILE} pulito e mappato.")
    print(f"Canali inseriti: {len(unique_channels)}")
    print(f"Programmi inseriti: {len(seen_progs)}")

if __name__ == "__main__":
    main()
