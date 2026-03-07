import requests
import xml.etree.ElementTree as ET
import os

def main():
    print("Inizio processo...")
    if not os.path.exists('join.txt'):
        print("ERRORE: join.txt non trovato!")
        return

    with open('join.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]

    print(f"Link trovati: {len(urls)}")

    root = ET.Element('tv')
    root.set('generator-info-name', 'ccliimpm77-EPG-Merger')

    count = 0
    for url in urls:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = ET.fromstring(r.content)
            for item in data:
                if item.tag in ['channel', 'programme']:
                    root.append(item)
                    count += 1
            print(f"OK: {url}")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    print(f"Totale elementi aggiunti: {count}")
    
    # Scrittura file
    tree = ET.ElementTree(root)
    tree.write('join.epg', encoding='utf-8', xml_declaration=True)
    print("File join.epg salvato correttamente sul disco.")

if __name__ == "__main__":
    main()
