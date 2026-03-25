import xml.etree.ElementTree as ET
import urllib.request
import re
import os

def clean_non_standard_chars(text):
    """Punto 4: Elimina caratteri non standard XMLTV."""
    # Mantiene solo caratteri stampabili e validi XML
    return re.sub(r'[^\x09\x0A\x0D\x20-\x7E\xA0-\xFF]', '', text)

def download_file(url):
    print(f"Scaricando: {url}")
    try:
        response = urllib.request.urlopen(url)
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Errore nello scaricamento di {url}: {e}")
        return None

def main():
    # File necessari
    join_txt = 'join.txt'
    old_txt = 'old.txt'
    new_txt = 'new.txt'
    output_file = 'join.epg'
    channelid_file = 'channelid.txt'

    # 1. UNIRE LE LISTE EPG
    print("Fase 1: Unione liste...")
    if not os.path.exists(join_txt):
        print(f"Errore: {join_txt} non trovato.")
        return

    combined_xml_content = ""
    with open(join_txt, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    all_channels = []
    all_programmes = []

    for url in urls:
        content = download_file(url)
        if content:
            try:
                # Rimuoviamo i tag di apertura/chiusura per estrarre il contenuto
                # Usiamo ElementTree per parse parziale
                root = ET.fromstring(content)
                for channel in root.findall('channel'):
                    all_channels.append(channel)
                for programme in root.findall('programme'):
                    all_programmes.append(programme)
            except Exception as e:
                print(f"Errore nel parsing XML di {url}: {e}")

    # Creiamo un nuovo root XML
    new_root = ET.Element('tv')
    for c in all_channels:
        new_root.append(c)
    for p in all_programmes:
        new_root.append(p)

    # Convertiamo in stringa per le sostituzioni testuali
    xml_str = ET.tostring(new_root, encoding='unicode')

    # 2. SOSTITUZIONE STRINGHE (OLD.TXT -> NEW.TXT)
    print("Fase 2: Sostituzione stringhe...")
    if os.path.exists(old_txt) and os.path.exists(new_txt):
        with open(old_txt, 'r') as f_old, open(new_txt, 'r') as f_new:
            old_lines = [l.strip() for l in f_old if l.strip()]
            new_lines = [l.strip() for l in f_new if l.strip()]
        
        for old_s, new_s in zip(old_lines, new_lines):
            xml_str = xml_str.replace(old_s, new_s)

    # 4. ELIMINARE CARATTERI NON STANDARD (Prima del parsing finale per sicurezza)
    print("Fase 4: Pulizia caratteri non standard...")
    xml_str = clean_non_standard_chars(xml_str)

    # Riparsiamo la stringa modificata per le operazioni strutturali (punti 3 e 5)
    root = ET.fromstring(xml_str)

    # 3. ELIMINARE ICONE e 5. UNIFORMARE DISPLAY-NAME
    print("Fase 3 e 5: Rimozione icone e reset display-name...")
    channels_data = []

    for channel in root.findall('channel'):
        channel_id = channel.get('id')
        
        # Punto 3: Rimuovi icone
        for icon in channel.findall('icon'):
            channel.remove(icon)
        
        # Punto 5: Elimina tutti i display-name e creane uno uguale all'ID
        for dn in channel.findall('display-name'):
            channel.remove(dn)
        
        new_dn = ET.SubElement(channel, 'display-name')
        new_dn.text = channel_id
        
        channels_data.append(channel_id)

    # Anche i programmi potrebbero avere icone, le rimuoviamo (Punto 3 esteso)
    for programme in root.findall('programme'):
        for icon in programme.findall('icon'):
            programme.remove(icon)

    # Salvataggio finale join.epg
    print(f"Salvataggio {output_file}...")
    tree = ET.ElementTree(root)
    with open(output_file, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding='utf-8', xml_declaration=False)

    # 6. CREARE CHANNELID.TXT
    print(f"Fase 6: Creazione {channelid_file}...")
    # Rimuoviamo duplicati mantenendo l'ordine
    unique_channels = list(dict.fromkeys(channels_data))
    with open(channelid_file, 'w') as f:
        for cid in unique_channels:
            f.write(f"{cid}\n")

    print("Procedura completata con successo.")

if __name__ == "__main__":
    main()
