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
    """
    Pulisce l'elemento in modo profondo:
    - Rimuove spazi/newline originali
    - Cambia 'de' in 'it' negli attributi
    - RIMUOVE TUTTE LE ICONE (richiesta specifica)
    - Applica blacklist stringhe
    """
    # 1. Pulizia spazi bianchi e blacklist
    if elem.text:
        for s in bad_strings:
            elem.text = elem.text.replace(s, "")
        elem.text = " ".join(elem.text.split()).strip()
    else:
        elem.text = None

    if elem.tail:
        elem.tail = None

    # 2. Correzione Lingua
    for attr_name, attr_value in elem.attrib.items():
        if attr_value.lower() == 'de':
            elem.set(attr_name, 'it')

    # 3. Rimozione TOTALE delle Icone e pulizia ricorsiva
    for child in list(elem):
        if child.tag == 'icon':
            elem.remove(child) # Elimina ogni riferimento alle icone
            continue
        
        # Continua la pulizia sui figli (es. display-name, desc, ecc.)
        aggressive_clean(child, bad_strings)

def normalize_name(name):
    """Normalizza il nome per il matching (es: Rai 1 .it -> rai1)."""
    if not name: return ""
    name = name.lower()
    name = name.replace(".it", "")
    return re.sub(r'[^a-z0-9]', '', name)

def apply_m3u_mapping(unique_channels, all_programmes, m3u_url):
    """Sincronizza ID e Nomi EPG con il case esatto del file M3U."""
    print(f"Scaricamento M3U per correzione nomi e case: {m3u_url}")
    try:
        r = requests.get(m3u_url, timeout=30)
        r.raise_for_status()
        m3u_content = r.text
        
        # Estrazione nomi dall'M3U (tvg-name)
        m3u_names = set(re.findall(r'tvg-name="([^"]+)"', m3u_content))
        m3u_mapping_dict = {normalize_name(name): name for name in m3u_names}
        
        final_id_map = {}

        for old_id, channel_elem in unique_channels.items():
            norm_id = normalize_name(old_id)
            dn_elem = channel_elem.find('display-name')
            norm_dn = normalize_name(dn_elem.text) if dn_elem is not None else ""

            # Se troviamo un match nell'M3U (per ID o per Display Name)
            if norm_id in m3u_mapping_dict:
                final_id_map[old_id] = m3u_mapping_dict[norm_id]
            elif norm_dn in m3u_mapping_dict:
                final_id_map[old_id] = m3u_mapping_dict[norm_dn]

        if not final_id_map:
            return unique_channels, all_programmes

        print(f"Corrispondenze trovate: {len(final_id_map)} canali allineati all'M3U.")

        # Aggiornamento Canali
        new_unique_channels = {}
        for old_id, channel_elem in unique_channels.items():
            if old_id in final_id_map:
                new_name_m3u = final_id_map[old_id]
                channel_elem.set('id', new_name_m3u)
                
                # Sostituiamo il display-name con quello esatto dell'M3U
                for dn in channel_elem.findall('display-name'):
                    channel_elem.remove(dn)
                new_dn = ET.SubElement(channel_elem, 'display-name')
                new_dn.text = new_name_m3u
                
                new_unique_channels[new_name_m3u] = channel_elem
            else:
                new_unique_channels[old_id] = channel_elem

        # Aggiornamento ID nei Programmi
        for prog in all_programmes:
            old_ch_id = prog.get('channel')
            if old_ch_id in final_id_map:
                prog.set('channel', final_id_map[old_ch_id])

        return new_unique_channels, all_programmes

    except Exception as e:
        print(f"ERRORE mapping M3U: {e}")
        return unique_channels, all_programmes

def main():
    print("Inizio Sanificazione EPG (Rimozione Icone + Case Matching M3U)...")
    
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
                    # La pulizia ora rimuove anche le icone
                    aggressive_clean(channel, bad_strings)
                    unique_channels[ch_id] = channel
            
            for prog in root_input.findall('programme'):
                if not prog.get('start') or not prog.get('channel'): continue
                aggressive_clean(prog, bad_strings)
                all_programmes.append(prog)
            print(f"OK: {url}")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # Applica il mapping dei nomi e del Case (es. LA7 -> La7)
    unique_channels, all_programmes = apply_m3u_mapping(unique_channels, all_programmes, M3U_URL)

    # COSTRUZIONE XML FINALE
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Ultimate-NoIcons-V5')

    print("Ordinamento canali...")
    for cid in sorted(unique_channels.keys(), key=lambda x: x.lower()):
        new_root.append(unique_channels[cid])

    print("Ordinamento programmi...")
    all_programmes.sort(key=lambda p: (p.get('channel', '').lower(), p.get('start', '')))
    seen_progs = set()
    for prog in all_programmes:
        prog_id = f"{prog.get('channel')}_{prog.get('start')}"
        if prog_id not in seen_progs:
            new_root.append(prog)
            seen_progs.add(prog_id)

    print("Scrittura file finale senza icone...")
    tree = ET.ElementTree(new_root)
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        pass

    with open(OUTPUT_FILE, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print(f"SUCCESSO: {OUTPUT_FILE} pronto. Icone rimosse e nomi sincronizzati con M3U.")

if __name__ == "__main__":
    main()
