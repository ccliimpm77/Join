import requests
import xml.etree.ElementTree as ET
import os

def download_and_parse(url):
    try:
        print(f"Scaricamento di: {url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        
        # Usiamo parser per gestire eventuali errori di codifica
        parser = ET.XMLParser(encoding="utf-8")
        return ET.fromstring(response.content, parser=parser)
    except Exception as e:
        print(f"Errore con {url}: {e}")
        return None

def main():
    if not os.path.exists('join.txt'):
        print("Errore: file join.txt non trovato!")
        return

    with open('join.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Creazione della struttura base del file EPG
    merged_root = ET.Element('tv')
    merged_root.set('generator-info-name', 'ccliimpm77-EPG-Merger')

    data_added = False
    for url in urls:
        root = download_and_parse(url)
        if root is not None:
            # Estraiamo canali e programmi
            for child in root:
                if child.tag in ['channel', 'programme']:
                    merged_root.append(child)
                    data_added = True

    if data_added:
        # Salvataggio con intestazione XML corretta
        tree = ET.ElementTree(merged_root)
        tree.write('join.epg', encoding='utf-8', xml_declaration=True)
        print("File join.epg creato con successo.")
    else:
        print("Non è stato possibile recuperare dati dai link forniti.")

if __name__ == "__main__":
    main()
