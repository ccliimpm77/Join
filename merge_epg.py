import requests
import xml.etree.ElementTree as ET
import os

def main():
    if not os.path.exists('join.txt'):
        print("Errore: join.txt non trovato")
        return

    with open('join.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]

    root = ET.Element('tv')
    root.set('generator-info-name', 'ccliimpm77-EPG-Merger')

    for url in urls:
        try:
            print(f"Scaricamento: {url}")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            
            # Parsing dell'XML
            data = ET.fromstring(r.content)
            for item in data:
                if item.tag in ['channel', 'programme']:
                    root.append(item)
        except Exception as e:
            print(f"Errore su {url}: {e}")

    # Salvataggio
    tree = ET.ElementTree(root)
    tree.write('join.epg', encoding='utf-8', xml_declaration=True)
    print("Fine: join.epg creato.")

if __name__ == "__main__":
    main()
