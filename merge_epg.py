import requests
import xml.etree.ElementTree as ET
import os
from xml.dom import minidom

def load_bad_strings(filepath):
    """Carica la lista di stringhe da rimuovere."""
    if not os.path.exists(filepath):
        print(f"AVVISO: {filepath} non trovato.")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def clean_element_text(element, bad_strings):
    """Pulisce il testo eliminando le stringhe indesiderate e spazi extra."""
    if element is not None and element.text:
        original_text = element.text
        for s in bad_strings:
            original_text = original_text.replace(s, "")
        element.text = " ".join(original_text.split()).strip()

def sanitize_and_fix_epg(root):
    """
    Controlla l'integrità del file EPG:
    - Rimuove programmi senza attributi obbligatori (start, channel).
    - Rimuove programmi duplicati (stesso canale e stesso orario).
    - Assicura che la struttura sia coerente.
    """
    seen_programmes = set()
    to_remove = []
    
    programmes = root.findall('programme')
    print(f"Validazione in corso su {len(programmes)} programmi...")

    for prog in programmes:
        start = prog.get('start')
        channel = prog.get('channel')
        
        # 1. Controllo attributi obbligatori
        if not start or not channel:
            to_remove.append(prog)
            continue
            
        # 2. Controllo duplicati (Chiave: canale + orario inizio)
        prog_id = f"{channel}_{start}"
        if prog_id in seen_programmes:
            to_remove.append(prog)
        else:
            seen_programmes.add(prog_id)

    # Rimozione dei programmi non validi o duplicati
    for prog in to_remove:
        root.remove(prog)
    
    print(f"Pulizia completata: rimosse {len(to_remove)} voci non valide o duplicate.")

def prettify(elem):
    """Ritorna una stringa XML formattata correttamente (indentata)."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def main():
    print("Inizio unione EPG con controllo integrità...")
    
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
            
            tree = ET.fromstring(r.content)
            
            # Canali
            for channel in tree.findall('channel'):
                ch_id = channel.get('id')
                if ch_id and ch_id not in unique_channels:
                    unique_channels[ch_id] = channel
            
            # Programmi
            for programme in tree.findall('programme'):
                for desc in programme.findall('desc'):
                    clean_element_text(desc, bad_strings)
                all_programmes.append(programme)
                
            print(f"OK: {url} elaborato.")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # Creazione root
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Advanced-Sanitizer')

    # Aggiunta canali
    for ch_id in unique_channels:
        new_root.append(unique_channels[ch_id])

    # Aggiunta programmi
    for prog in all_programmes:
        new_root.append(prog)

    # --- FASE DI CONTROLLO INTEGRITÀ ---
    sanitize_and_fix_epg(new_root)
    # ----------------------------------

    # Salvataggio con formattazione pulita
    print("Salvataggio file finale...")
    try:
        xml_string = prettify(new_root)
        # Il modulo minidom aggiunge una sua dichiarazione XML, 
        # scriviamo in 'w' (stringa) invece di 'wb'
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        print(f"Successo: {OUTPUT_FILE} creato e validato!")
    except Exception as e:
        print(f"Errore durante il salvataggio: {e}")

if __name__ == "__main__":
    main()
