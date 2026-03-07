import requests
import xml.etree.ElementTree as ET
import os

def main():
    print("Inizio unione EPG avanzata...")
    if not os.path.exists('join.txt'):
        print("ERRORE: join.txt non trovato!")
        return

    with open('join.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]

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
            
            # Estrazione programmi
            for programme in tree.findall('programme'):
                all_programmes.append(programme)
                
            print(f"OK: {url} elaborato.")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    # Creazione del nuovo file XML strutturato correttamente
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'ccliimpm77-Advanced-Merger')

    # 1. Aggiungiamo prima tutti i canali (senza duplicati)
    print(f"Inserimento di {len(unique_channels)} canali unici...")
    for ch_id in unique_channels:
        new_root.append(unique_channels[ch_id])

    # 2. Aggiungiamo tutti i programmi dopo i canali
    print(f"Inserimento di {len(all_programmes)} programmi...")
    for prog in all_programmes:
        new_root.append(prog)

    # Scrittura del file finale
    new_tree = ET.ElementTree(new_root)
    
    # Usiamo una formattazione pulita
    with open('join.epg', 'wb') as f:
        new_tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print("Successo: join.epg creato e ottimizzato per i player!")

if __name__ == "__main__":
    main()
