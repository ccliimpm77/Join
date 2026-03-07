import requests
import xml.etree.ElementTree as ET
import os
import re

def download_and_parse(url):
    try:
        # Pulisce il link da eventuali spazi o scritte extra alla fine
        url = url.split(' ')[0].strip()
        if not url.startswith('http'):
            return None
            
        print(f"Scaricamento: {url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, timeout=30, headers=headers)
        r.raise_for_status()
        
        # Prova a leggere l'XML
        return ET.fromstring(r.content)
    except Exception as e:
        print(f"Salto {url} per errore: {e}")
        return None

def main():
    if not os.path.exists('join.txt'):
        print("Errore: join.txt non trovato")
        return

    with open('join.txt', 'r', encoding='utf-8') as f:
        urls = f.readlines()

    root = ET.Element('tv')
    root.set('generator-info-name', 'ccliimpm77-Merger')
    
    data_added = False
    for url in urls:
        if url.strip():
            data = download_and_parse(url)
            if data is not None:
                for item in data:
                    if item.tag in ['channel', 'programme']:
                        root.append(item)
                        data_added = True

    if data_added:
        tree = ET.ElementTree(root)
        # Salvataggio forzato in UTF-8
        with open('join.epg', 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)
        print("Successo: join.epg creato.")
    else:
        print("Errore: Nessun dato XML valido trovato nei link.")
        # Creiamo comunque un file vuoto per non far fallire l'azione
        with open('join.epg', 'w') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?><tv></tv>')

if __name__ == "__main__":
    main()
