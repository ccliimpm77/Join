import requests
import xml.etree.ElementTree as ET
import os

def load_bad_strings(filepath):
    """Carica la lista di stringhe da rimuovere."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def deep_clean_element(element, bad_strings):
    """
    Funzione ricorsiva che corregge ogni elemento e i suoi figli:
    - Cambia lang='de' in lang='it'
    - Rimuove icone duplicate
    - Pulisce i testi dalle stringhe indesiderate
    """
    # 1. Correzione attributo lingua
    if element.get('lang') == 'de':
        element.set('lang', 'it')
    
    # 2. Pulizia testo
    if element.text:
        for s in bad_strings:
            element.text = element.text.replace(s, "")
        element.text = " ".join(element.text.split()).strip()

    # 3. Gestione icone duplicate (mantiene solo la prima)
    icons = element.findall('icon')
    if len(icons) > 1:
        # Teniamo solo la prima, rimuoviamo le altre
        for extra_icon in icons[1:]:
            element.remove(extra_icon)

    # 4. Ricorsione sui figli (per gestire display-name, desc, title, ecc.)
    for child in list(element):
        deep_clean_element(child, bad_strings)

def main():
    print("Inizio Elaborazione EPG (Deep Cleaning)...")
    
    JOIN_FILE = 'join.txt'
    STRINGS_FILE = 'stringhe.txt'
    OUTPUT_FILE = 'join.epg'

    if not os.path.exists(JOIN_FILE):
        print(f"ERRORE: {JOIN_FILE} non trovato!")
        return

    with open(JOIN_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]
    
    bad_strings = load_bad_strings(STRINGS_FILE)
    unique_channels = {}
    all_programmes = []

    for url in urls:
        try:
            print(f"Scaricamento: {url}")
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            
            root_input = ET.fromstring(r.content)
            
            # Elaborazione Canali
            for channel in root_input.findall('channel'):
                ch_id = channel.get('id')
                if not ch_id: continue
                
                if ch_id not in unique_channels:
                    # Assicuriamo la presenza del display-name (tag primario)
                    if channel.find('display-name') is None:
                        dn = ET.SubElement(channel, 'display-name')
                        dn.text = ch_id
                    
                    # Pulizia profonda (lingua, icone, testi)
                    deep_clean_element(channel, bad_strings)
                    unique_channels[ch_id] = channel
            
            # Elaborazione Programmi
            for prog in root_input.findall('programme'):
                if not prog.get('start') or not prog.get('channel'):
                    continue
                
                # Pulizia profonda anche sui programmi
                deep_clean_element(prog, bad_strings)
                all_programmes.append(prog)
                
            print(f"OK: {url} elaborato.")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # Creazione struttura finale
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Advanced-Fixer-V3')

    # 1. Ordinamento alfabetico canali per ID
    print("Ordinamento canali...")
    sorted_channel_ids = sorted(unique_channels.keys())
    for ch_id in sorted_channel_ids:
        new_root.append(unique_channels[ch_id])

    # 2. Ordinamento e Filtro Duplicati Programmi
    print("Validazione programmi...")
    # Ordiniamo per canale e orario
    all_programmes.sort(key=lambda p: (p.get('channel', ''), p.get('start', '')))
    
    seen_progs = set()
    for prog in all_programmes:
        prog_id = f"{prog.get('channel')}_{prog.get('start')}"
        if prog_id not in seen_progs:
            new_root.append(prog)
            seen_progs.add(prog_id)

    # Scrittura del file
    print("Salvataggio join.epg...")
    tree = ET.ElementTree(new_root)
    
    # Formattazione per evitare spazi eccessivi (Python 3.9+)
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        pass

    # Salvataggio con codifica esplicita per evitare troncamenti
    with open(OUTPUT_FILE, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print(f"SUCCESSO! File creato con {len(sorted_channel_ids)} canali e {len(seen_progs)} programmi.")

if __name__ == "__main__":
    main()
