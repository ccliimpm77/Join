import requests
import xml.etree.ElementTree as ET
import os

def load_bad_strings(filepath):
    """Carica la lista di stringhe da rimuovere dal file specificato."""
    if not os.path.exists(filepath):
        print(f"AVVISO: {filepath} non trovato. Nessuna stringa verrà rimossa.")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        # Legge le righe, rimuove spazi bianchi e ignora righe vuote
        return [line.strip() for line in f if line.strip()]

def clean_element_text(element, bad_strings):
    """Rimuove le stringhe indesiderate dal testo di un elemento XML."""
    if element is not None and element.text:
        original_text = element.text
        for s in bad_strings:
            if s in original_text:
                original_text = original_text.replace(s, "")
        # Pulizia finale per evitare doppi spazi o spazi all'inizio/fine rimasti dopo la rimozione
        element.text = " ".join(original_text.split()).strip()

def main():
    print("Inizio unione EPG avanzata con pulizia descrizioni...")
    
    # Percorsi file configurazione
    JOIN_FILE = 'join.txt'
    STRINGS_FILE = 'stringhe.txt'
    OUTPUT_FILE = 'join.epg'

    if not os.path.exists(JOIN_FILE):
        print(f"ERRORE: {JOIN_FILE} non trovato!")
        return

    # Caricamento URL e stringhe da rimuovere
    with open(JOIN_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]
    
    bad_strings = load_bad_strings(STRINGS_FILE)
    if bad_strings:
        print(f"Caricate {len(bad_strings)} stringhe da rimuovere.")

    # Dizionario per memorizzare i canali unici (usa l'ID come chiave)
    unique_channels = {}
    # Lista per memorizzare tutti i programmi
    all_programmes = []

    for url in urls:
        try:
            print(f"Scaricamento: {url}")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            
            # Parsing del file XML
            tree = ET.fromstring(r.content)
            
            # Estrazione canali
            for channel in tree.findall('channel'):
                ch_id = channel.get('id')
                if ch_id and ch_id not in unique_channels:
                    unique_channels[ch_id] = channel
            
            # Estrazione e pulizia programmi
            for programme in tree.findall('programme'):
                # Cerchiamo tutti i tag <desc> (possono essercene più di uno per lingua)
                for desc in programme.findall('desc'):
                    clean_element_text(desc, bad_strings)
                
                all_programmes.append(programme)
                
            print(f"OK: {url} elaborato.")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # Creazione del nuovo file XML
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Advanced-Merger-Clean')

    # 1. Aggiungiamo i canali
    print(f"Inserimento di {len(unique_channels)} canali unici...")
    for ch_id in unique_channels:
        new_root.append(unique_channels[ch_id])

    # 2. Aggiungiamo i programmi (già puliti)
    print(f"Inserimento di {len(all_programmes)} programmi...")
    for prog in all_programmes:
        new_root.append(prog)

    # Scrittura del file finale
    new_tree = ET.ElementTree(new_root)
    
    with open(OUTPUT_FILE, 'wb') as f:
        new_tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print(f"Successo: {OUTPUT_FILE} creato, ottimizzato e pulito!")

if __name__ == "__main__":
    main()
