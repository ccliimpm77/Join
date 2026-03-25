import xml.etree.ElementTree as ET
import urllib.request
import os

def download_file(url):
    print(f"Scaricando: {url}")
    try:
        response = urllib.request.urlopen(url)
        return response.read()
    except Exception as e:
        print(f"Errore nello scaricamento di {url}: {e}")
        return None

def main():
    # File necessari
    join_txt = 'join.txt'
    old_txt = 'old.txt'
    new_txt = 'new.txt'
    output_file = 'join.epg'

    # 1. UNIRE LE LISTE EPG
    print("Fase 1: Unione liste...")
    if not os.path.exists(join_txt):
        print(f"Errore: {join_txt} non trovato.")
        return

    all_channels = []
    all_programmes = []

    with open(join_txt, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        content = download_file(url)
        if content:
            try:
                root = ET.fromstring(content)
                # Estraiamo canali e programmi
                for channel in root.findall('channel'):
                    all_channels.append(channel)
                for programme in root.findall('programme'):
                    all_programmes.append(programme)
            except Exception as e:
                print(f"Errore nel parsing XML di {url}: {e}")

    # Creiamo la struttura XML finale
    new_root = ET.Element('tv')
    for c in all_channels:
        new_root.append(c)
    for p in all_programmes:
        new_root.append(p)

    # 3. ELIMINARE RIFERIMENTI ALLE ICONE
    # (Lo facciamo prima della sostituzione testuale per comodità strutturale)
    print("Fase 3: Rimozione icone...")
    for channel in new_root.findall('channel'):
        for icon in channel.findall('icon'):
            channel.remove(icon)
    
    for programme in new_root.findall('programme'):
        for icon in programme.findall('icon'):
            programme.remove(icon)

    # Convertiamo l'XML in stringa per le sostituzioni testuali
    xml_str = ET.tostring(new_root, encoding='unicode')

    # 2. SOSTITUZIONE STRINGHE (OLD.TXT -> NEW.TXT)
    print("Fase 2: Sostituzione stringhe...")
    if os.path.exists(old_txt) and os.path.exists(new_txt):
        with open(old_txt, 'r', encoding='utf-8') as f_old, \
             open(new_txt, 'r', encoding='utf-8') as f_new:
            
            old_lines = [l.strip() for l in f_old if l.strip()]
            new_lines = [l.strip() for l in f_new if l.strip()]
        
        # Sostituisce riga per riga (la riga 1 di old con la riga 1 di new, etc.)
        for old_s, new_s in zip(old_lines, new_lines):
            if old_s: # evita sostituzioni vuote
                xml_str = xml_str.replace(old_s, new_s)
    else:
        print("Salto fase 2: old.txt o new.txt mancanti.")

    # Salvataggio finale
    print(f"Salvataggio in {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml_str)

    print("Procedura completata.")

if __name__ == "__main__":
    main()
