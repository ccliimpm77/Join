import xml.etree.ElementTree as ET
import requests
import os
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator

# Configurazione
JOIN_TXT = 'join.txt'
OLD_TXT = 'old.txt'
NEW_TXT = 'new.txt'
OUTPUT_EPG = 'join.epg'
CHANNEL_TXT = 'channel.txt'

def download_url(url):
    """Scarica il contenuto di un URL (veloce con requests)."""
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"Errore download {url}: {e}")
        return None

def batch_translate(texts, target_lang='it'):
    """Traduce una lista di testi in blocchi per massimizzare la velocità."""
    if not texts:
        return []
    
    translator = GoogleTranslator(source='auto', target=target_lang)
    separator = " [|] "
    # Uniamo i testi in stringhe da max 4500 caratteri (limite Google)
    chunks = []
    current_chunk = ""
    
    for text in texts:
        if len(current_chunk) + len(text) + len(separator) < 4500:
            current_chunk += text + separator
        else:
            chunks.append(current_chunk.strip(separator))
            current_chunk = text + separator
    if current_chunk:
        chunks.append(current_chunk.strip(separator))

    translated_flat = []
    for chunk in chunks:
        try:
            translated = translator.translate(chunk)
            translated_flat.extend(translated.split(separator))
        except:
            translated_flat.extend(chunk.split(separator)) # Fallback in caso di errore
            
    return [t.strip() for t in translated_flat]

def main():
    if not os.path.exists(JOIN_TXT):
        return

    # 1. DOWNLOAD PARALLELO
    with open(JOIN_TXT, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"Scaricamento di {len(urls)} liste in parallelo...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(download_url, urls))

    all_channels = []
    all_programmes = []

    # 2. PARSING XML
    for content in results:
        if content:
            try:
                root = ET.fromstring(content)
                all_channels.extend(root.findall('channel'))
                all_programmes.extend(root.findall('programme'))
            except Exception as e:
                print(f"Errore parsing: {e}")

    # 3. TRADUZIONE OTTIMIZZATA CANALE MEZZO
    print("Traduzione batch per canale Mezzo...")
    mezzo_progs = [p for p in all_programmes if p.get('channel') and "Mezzo" in p.get('channel')]
    
    to_translate = []
    for p in mezzo_progs:
        title = p.find('title')
        desc = p.find('desc')
        to_translate.append(title.text if title is not None and title.text else " ")
        to_translate.append(desc.text if desc is not None and desc.text else " ")

    translated_list = batch_translate(to_translate)

    # Riassegnazione testi tradotti
    idx = 0
    for p in mezzo_progs:
        title = p.find('title')
        desc = p.find('desc')
        if title is not None and idx < len(translated_list):
            title.text = translated_list[idx]
            idx += 1
        if desc is not None and idx < len(translated_list):
            desc.text = translated_list[idx]
            idx += 1

    # 4. PULIZIA ICONE E CREAZIONE CHANNEL.TXT (Passaggio Singolo)
    print(f"Pulizia icone e creazione {CHANNEL_TXT}...")
    channel_lines = []
    for channel in all_channels:
        c_id = channel.get('id', 'N/A')
        names = [n.text for n in channel.findall('display-name') if n.text]
        channel_lines.append(f"{c_id}: {' | '.join(names)}\n")
        
        for icon in channel.findall('icon'):
            channel.remove(icon)

    for prog in all_programmes:
        for icon in prog.findall('icon'):
            prog.remove(icon)

    with open(CHANNEL_TXT, 'w', encoding='utf-8') as f:
        f.writelines(channel_lines)

    # 5. COSTRUZIONE STRINGA FINALE E SOSTITUZIONE VELOCE
    new_root = ET.Element('tv')
    new_root.extend(all_channels)
    new_root.extend(all_programmes)
    
    xml_str = ET.tostring(new_root, encoding='unicode')

    if os.path.exists(OLD_TXT) and os.path.exists(NEW_TXT):
        print("Sostituzione stringhe...")
        with open(OLD_TXT, 'r', encoding='utf-8') as f_o, open(NEW_TXT, 'r', encoding='utf-8') as f_n:
            for old_s, new_s in zip(f_o, f_n):
                o, n = old_s.strip(), new_s.strip()
                if o:
                    xml_str = xml_str.replace(o, n)

    # 6. SALVATAGGIO
    print(f"Salvataggio {OUTPUT_EPG}...")
    with open(OUTPUT_EPG, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml_str)

    print("Completato!")

if __name__ == "__main__":
    main()
