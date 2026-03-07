import requests
import xml.etree.ElementTree as ET
import gzip
import io

def download_and_parse(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.content
        
        # Gestisce i file compressi .gz
        if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
            content = gzip.decompress(content)
            
        return ET.fromstring(content)
    except Exception as e:
        print(f"Errore nel download di {url}: {e}")
        return None

def main():
    # Legge i link da join.txt
    with open('join.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Nodo radice per il nuovo file EPG
    merged_root = ET.Element('tv')
    
    for url in urls:
        print(f"Elaborazione: {url}")
        root = download_and_parse(url)
        if root is not None:
            # Unisce i canali e i programmi
            for child in root:
                if child.tag in ['channel', 'programme']:
                    merged_root.append(child)

    # Crea l'albero XML e lo salva
    tree = ET.ElementTree(merged_root)
    tree.write('join.epg', encoding='utf-8', xml_declaration=True)
    print("File join.epg creato con successo.")

if __name__ == "__main__":
    main()
