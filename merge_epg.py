import xml.etree.ElementTree as ET
import urllib.request
import os
import time
from deep_translator import GoogleTranslator

def download_file(url):
    print(f"Scaricando: {url}")
    try:
        response = urllib.request.urlopen(url)
        return response.read()
    except Exception as e:
        print(f"Errore nello scaricamento di {url}: {e}")
        return None

def translate_text(text, target_lang='it'):
    if not text or len(text) < 2:
        return text
    try:
        # Traduzione via Google (deep-translator)
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        print(f"Errore traduzione: {e}")
        return text

def main():
    join_txt = 'join.txt'
    old_txt = 'old.txt'
    new_txt = 'new.txt'
    output_file = 'join.epg'
    channel_info_file = 'channel.txt'

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
                all_channels.extend(root.findall('channel'))
                all_programmes.extend(root.findall('programme'))
            except Exception as e:
                print(f"Errore parsing XML: {e}")

    # --- NUOVA FUNZIONE: TRADUZIONE CANALE "MEZZO" ---
    print("Fase: Traduzione programmi canale Mezzo...")
    # Cerchiamo i programmi il cui canale contiene "Mezzo"
    mezzo_programmes = [p for p in all_programmes if "Mezzo" in (p.get('channel') or "")]
    
    for prog in mezzo_programmes:
        # Traduci Titolo
        title_node = prog.find('title')
        if title_node is not None:
            title_node.text = translate_text(title_node.text)
        
        # Traduci Descrizione
        desc_node = prog.find('desc')
        if desc_node is not None:
            desc_node.text = translate_text(desc_node.text)
        
        # Piccolo delay per non essere bloccati da Google (opzionale)
        # time.sleep(0.1)

    # 3. ELIMINARE RIFERIMENTI ALLE ICONE
    print("Fase 3: Rimozione icone...")
    for channel in all_channels:
        for icon in channel.findall('icon'):
            channel.remove(icon)
    for programme in all_programmes:
        for icon in programme.findall('icon'):
            programme.remove(icon)

    # 6. CREA CHANNEL.TXT (Punto richiesto: ID e tutti i Display Name)
    print(f"Fase: Creazione {channel_info_file}...")
    with open(channel_info_file, 'w', encoding='utf-8') as cf:
        for channel in all_channels:
            c_id = channel.get('id')
            names = [dn.text for dn in channel.findall('display-name') if dn.text]
            names_str = " | ".join(names)
            cf.write(f"{c_id}: {names_str}\n")

    # Ricostruiamo l'XML per le fasi successive
    new_root = ET.Element('tv')
    for c in all_channels: new_root.append(c)
    for p in all_programmes: new_root.append(p)
    
    xml_str = ET.tostring(new_root, encoding='unicode')

    # 2. SOSTITUZIONE STRINGHE (OLD -> NEW)
    print("Fase 2: Sostituzione stringhe...")
    if os.path.exists(old_txt) and os.path.exists(new_txt):
        with open(old_txt, 'r', encoding='utf-8') as f_old, \
             open(new_txt, 'r', encoding='utf-8') as f_new:
            old_lines = [l.strip() for l in f_old if l.strip()]
            new_lines = [l.strip() for l in f_new if l.strip()]
        
        for old_s, new_s in zip(old_lines, new_lines):
            xml_str = xml_str.replace(old_s, new_s)

    # Salvataggio finale join.epg
    print(f"Salvataggio in {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml_str)

    print("Procedura completata.")

if __name__ == "__main__":
    main()
