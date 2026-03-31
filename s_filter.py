import requests
import xml.etree.ElementTree as ET
import gzip
import io
import os

def download_content(url):
    print(f"Scaricando: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.content
        
        # Se l'URL finisce con .gz o i dati sono compressi, decomprimi
        if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
            print("Decompressione GZIP in corso...")
            content = gzip.decompress(content)
            
        return content
    except Exception as e:
        print(f"Errore nel download di {url}: {e}")
        return None

def main():
    input_file = 's_epg.txt'
    output_file = 's_epg.xmltv'
    
    if not os.path.exists(input_file):
        print(f"Errore: {input_file} non trovato.")
        return

    # Struttura per memorizzare i dati: { url: [lista_canali] }
    data_to_process = []
    current_url = None
    current_channels = []

    # Leggi il file di configurazione s_epg.txt
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('http'):
                if current_url:
                    data_to_process.append((current_url, current_channels))
                current_url = line
                current_channels = []
            else:
                current_channels.append(line)
        
        # Aggiungi l'ultimo blocco
        if current_url:
            data_to_process.append((current_url, current_channels))

    # Creazione del nuovo XML (root <tv>)
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'S-Filter-Automation')

    for url, target_channels in data_to_process:
        content = download_content(url)
        if not content:
            continue

        try:
            # Parsing dell'XML scaricato
            tree = ET.fromstring(content)
            
            # 1. Filtra i tag <channel>
            for channel in tree.findall('channel'):
                channel_id = channel.get('id')
                if channel_id in target_channels:
                    new_root.append(channel)
            
            # 2. Filtra i tag <programme>
            for programme in tree.findall('programme'):
                channel_id = programme.get('channel')
                if channel_id in target_channels:
                    new_root.append(programme)
                    
            print(f"Completato filtraggio per {url}")
            
        except Exception as e:
            print(f"Errore nel parsing XML di {url}: {e}")

    # Salvataggio del file finale
    new_tree = ET.ElementTree(new_root)
    ET.indent(new_tree, space="  ", level=0) # Formattazione leggibile
    new_tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"File {output_file} creato con successo!")

if __name__ == "__main__":
    main()
