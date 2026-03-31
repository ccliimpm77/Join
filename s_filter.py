import requests
import xml.etree.ElementTree as ET
import gzip
import io
import os

def download_content(url):
    print(f"Tentativo di scaricamento: {url}")
    try:
        # Aggiungiamo un User-Agent per evitare blocchi da parte di alcuni server
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Timeout impostato a 20 secondi per evitare attese infinite
        response = requests.get(url, timeout=20, headers=headers)
        
        # Se lo stato non è 200 (OK), solleva un'eccezione che verrà catturata dal blocco except
        response.raise_for_status()
        
        content = response.content
        
        # Gestione decompressione GZIP (se l'url finisce per .gz o se i byte iniziali sono di un gzip)
        if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
            print(f"Decompressione GZIP in corso...")
            content = gzip.decompress(content)
            
        return content
    except (requests.exceptions.RequestException, Exception) as e:
        # Questo blocco cattura: errori di connessione, timeout, 404, 500, ecc.
        print(f"!!! ATTENZIONE: Impossibile raggiungere {url}")
        print(f"!!! Motivo: {e}")
        print(f"!!! Salto questa lista e i relativi canali richiesti.\n")
        return None

def main():
    input_file = 's_epg.txt'
    output_file = 's_epg.xmltv'
    
    if not os.path.exists(input_file):
        print(f"Errore: {input_file} non trovato.")
        return

    data_to_process = []
    current_url = None
    current_channels = []

    # Leggi il file di configurazione s_epg.txt
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
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
            
            # Aggiungi l'ultimo blocco dopo la fine del ciclo
            if current_url:
                data_to_process.append((current_url, current_channels))
    except Exception as e:
        print(f"Errore nella lettura di {input_file}: {e}")
        return

    # Creazione del nuovo XML (root <tv>)
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'S-Filter-Automation')

    for url, target_channels in data_to_process:
        content = download_content(url)
        
        # Se il download è fallito (None), lo script passa al prossimo URL
        if content is None:
            continue

        try:
            # Parsing dell'XML scaricato
            tree = ET.fromstring(content)
            
            ch_count = 0
            prog_count = 0

            # 1. Filtra i tag <channel>
            for channel in tree.findall('channel'):
                channel_id = channel.get('id')
                if channel_id in target_channels:
                    new_root.append(channel)
                    ch_count += 1
            
            # 2. Filtra i tag <programme>
            for programme in tree.findall('programme'):
                channel_id = programme.get('channel')
                if channel_id in target_channels:
                    new_root.append(programme)
                    prog_count += 1
                    
            print(f"Completato: {url} (Aggiunti {ch_count} canali e {prog_count} programmi)\n")
            
        except Exception as e:
            print(f"Errore nel parsing XML di {url}: {e}. Salto...\n")

    # Salvataggio del file finale
    try:
        new_tree = ET.ElementTree(new_root)
        if hasattr(ET, 'indent'): # Indentazione disponibile da Python 3.9+
            ET.indent(new_tree, space="  ", level=0)
        
        new_tree.write(output_file, encoding='utf-8', xml_declaration=True)
        print(f"OPERAZIONE COMPLETATA: File '{output_file}' generato correttamente.")
    except Exception as e:
        print(f"Errore durante il salvataggio del file finale: {e}")

if __name__ == "__main__":
    main()
