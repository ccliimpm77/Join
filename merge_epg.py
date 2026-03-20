import requests
import xml.etree.ElementTree as ET
import os

def load_bad_strings(filepath):
    """Carica la lista di stringhe da rimuovere dal file."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def fix_element(elem, bad_strings):
    """
    Applica correzioni formali all'elemento:
    - Cambia lingua da 'de' a 'it'
    - Pulisce il testo dalle stringhe indesiderate
    - Rimuove icone duplicate
    """
    # 1. Cambio lingua
    if elem.get('lang') == 'de':
        elem.set('lang', 'it')
    
    # 2. Pulizia testo (per descrizioni, titoli, ecc.)
    if elem.text:
        for s in bad_strings:
            elem.text = elem.text.replace(s, "")
        elem.text = " ".join(elem.text.split()).strip()

    # 3. Rimozione icone duplicate all'interno dell'elemento
    icons = elem.findall('icon')
    if len(icons) > 1:
        for duplicate in icons[1:]:
            elem.remove(duplicate)

def main():
    print("Inizio Elaborazione EPG Professionale...")
    
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
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            
            # Parsing
            root_input = ET.fromstring(r.content)
            
            # Elaborazione Canali
            for channel in root_input.findall('channel'):
                ch_id = channel.get('id')
                if not ch_id: continue
                
                if ch_id not in unique_channels:
                    # Controllo tag primario <display-name>
                    if channel.find('display-name') is None:
                        dn = ET.SubElement(channel, 'display-name')
                        dn.text = ch_id
                    
                    # Fix icone e lingua nel canale
                    fix_element(channel, bad_strings)
                    for child in channel:
                        fix_element(child, bad_strings)
                        
                    unique_channels[ch_id] = channel
            
            # Elaborazione Programmi
            for prog in root_input.findall('programme'):
                # Controllo integrità attributi base
                if not prog.get('start') or not prog.get('channel'):
                    continue
                
                # Fix icone, lingua e descrizioni nel programma
                fix_element(prog, bad_strings)
                for child in prog:
                    fix_element(child, bad_strings)
                
                all_programmes.append(prog)
                
            print(f"OK: {url} elaborato.")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # Creazione nuovo XML
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Ultimate-Merger')

    # 1. ORDINAMENTO ALFABETICO CANALI
    print("Ordinamento canali...")
    sorted_channel_ids = sorted(unique_channels.keys())
    for ch_id in sorted_channel_ids:
        new_root.append(unique_channels[ch_id])

    # 2. FILTRO DUPLICATI E ORDINAMENTO PROGRAMMI
    print("Validazione e ordinamento programmi...")
    # Ordiniamo per canale e poi per orario di inizio
    all_programmes.sort(key=lambda p: (p.get('channel', ''), p.get('start', '')))
    
    seen_progs = set()
    for prog in all_programmes:
        prog_id = f"{prog.get('channel')}_{prog.get('start')}"
        if prog_id not in seen_progs:
            new_root.append(prog)
            seen_progs.add(prog_id)

    # Scrittura Finale
    print("Generazione file finale...")
    tree = ET.ElementTree(new_root)
    
    # ET.indent corregge i problemi di newline e formattazione (Python 3.9+)
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        # Fallback per versioni Python vecchie
        pass

    with open(OUTPUT_FILE, 'wb') as f:
        # Usiamo write direttamente per evitare troncamenti tipici delle stringhe di minidom
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print(f"SUCCESSO: {OUTPUT_FILE} creato correttamente.")
    print(f"Canali: {len(sorted_channel_ids)} | Programmi: {len(seen_progs)}")

if __name__ == "__main__":
    main()
