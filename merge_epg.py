import requests
import xml.etree.ElementTree as ET
import os

def load_bad_strings(filepath):
    """Carica la lista di stringhe da rimuovere."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def aggressive_clean(elem, bad_strings):
    """
    Pulisce l'elemento in modo profondo:
    - Rimuove spazi/newline originali (prepara per una formattazione pulita)
    - Cambia 'de' in 'it' in QUALSIASI attributo
    - Rimuove icone duplicate
    - Applica blacklist stringhe
    """
    # 1. Pulizia spazi bianchi e newline esistenti nel testo
    if elem.text:
        # Applica blacklist stringhe
        for s in bad_strings:
            elem.text = elem.text.replace(s, "")
        elem.text = " ".join(elem.text.split()).strip()
    else:
        elem.text = None # Forza la rimozione di soli spazi/invio

    # Rimuove spazi tra i tag (tail)
    if elem.tail:
        elem.tail = None

    # 2. Correzione Lingua (QUALSIASI attributo che contenga 'de')
    for attr_name, attr_value in elem.attrib.items():
        if attr_value.lower() == 'de':
            elem.set(attr_name, 'it')

    # 3. Rimozione Icone Duplicate (gestione figli diretti)
    icon_count = 0
    # Iteriamo su una copia della lista figli per poterli rimuovere in sicurezza
    for child in list(elem):
        if child.tag == 'icon':
            icon_count += 1
            if icon_count > 1:
                elem.remove(child)
                continue
        
        # Pulizia ricorsiva sui figli
        aggressive_clean(child, bad_strings)

def main():
    print("Inizio Sanificazione EPG Totale...")
    
    JOIN_FILE = 'join.txt'
    STRINGS_FILE = 'stringhe.txt'
    OUTPUT_FILE = 'join.epg'

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
            
            # ELABORAZIONE CANALI
            for channel in root_input.findall('channel'):
                ch_id = channel.get('id')
                if not ch_id: continue
                
                if ch_id not in unique_channels:
                    # Assicura tag primario display-name
                    if channel.find('display-name') is None:
                        dn = ET.SubElement(channel, 'display-name')
                        dn.text = ch_id
                    
                    # Pulizia Aggressiva (Icone, Lingua, Spazi)
                    aggressive_clean(channel, bad_strings)
                    unique_channels[ch_id] = channel
            
            # ELABORAZIONE PROGRAMMI
            for prog in root_input.findall('programme'):
                if not prog.get('start') or not prog.get('channel'):
                    continue
                
                aggressive_clean(prog, bad_strings)
                all_programmes.append(prog)
                
            print(f"OK: {url} elaborato.")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # COSTRUZIONE NUOVO FILE
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Ultimate-Sanitizer-V4')

    # 1. Ordinamento Alfabetico Canali
    print("Ordinamento canali...")
    sorted_ids = sorted(unique_channels.keys(), key=lambda x: x.lower())
    for cid in sorted_ids:
        new_root.append(unique_channels[cid])

    # 2. Ordinamento e Deduplicazione Programmi
    print("Ordinamento programmi...")
    all_programmes.sort(key=lambda p: (p.get('channel', '').lower(), p.get('start', '')))
    
    seen_progs = set()
    for prog in all_programmes:
        prog_id = f"{prog.get('channel')}_{prog.get('start')}"
        if prog_id not in seen_progs:
            new_root.append(prog)
            seen_progs.add(prog_id)

    # SALVATAGGIO
    print("Scrittura file finale...")
    tree = ET.ElementTree(new_root)
    
    # ET.indent (disponibile in Python 3.9+) crea una struttura perfetta 
    # partendo da un albero a cui abbiamo rimosso tutti i vecchi spazi (tail=None)
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        pass

    with open(OUTPUT_FILE, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print(f"SUCCESSO: {OUTPUT_FILE} pulito e pronto.")
    print(f"Canali inseriti: {len(unique_channels)}")
    print(f"Programmi inseriti: {len(seen_progs)}")

if __name__ == "__main__":
    main()
