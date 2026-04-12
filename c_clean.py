import re
import os

def clean_epg():
    # File names
    epg_file = 'join.epg'
    old_file = 'c_old.txt'
    new_file = 'c_new.txt'
    temp_file = 'join.epg.tmp'

    # Controllo se i file esistono
    if not all(os.path.exists(f) for f in [epg_file, old_file, new_file]):
        print("Errore: Assicurati che join.epg, c_old.txt e c_new.txt siano nella cartella.")
        return

    # 1. Caricamento mappature c_old -> c_new
    with open(old_file, 'r', encoding='utf-8') as f:
        old_lines = [line.strip() for line in f]
    with open(new_file, 'r', encoding='utf-8') as f:
        new_lines = [line.strip() for line in f]
    
    # Creiamo una lista di tuple (vecchio, nuovo) per la sostituzione
    replacements = list(zip(old_lines, new_lines))

    # Processamento del file join.epg
    with open(epg_file, 'r', encoding='utf-8') as f_in, \
         open(temp_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            # --- PUNTO 1: Sostituzione stringhe da c_old a c_new ---
            for old_str, new_str in replacements:
                if old_str in line:
                    line = line.replace(old_str, new_str)

            # --- PUNTO 2 e 3: Elimina righe con "icon src" o "display-name" ---
            if 'icon src' in line or 'display-name' in line:
                continue

            # Scriviamo la riga corrente (modificata o originale) nel file
            f_out.write(line)

            # --- PUNTO 4: Cerca channel id, estrai valore e aggiungi display-name ---
            if 'channel id="' in line:
                # Usiamo regex per estrarre il valore tra le virgolette dopo channel id=
                match = re.search(r'channel id="([^"]+)"', line)
                if match:
                    channel_id_value = match.group(1)
                    # Crea la nuova riga display-name
                    new_display_name = f'    <display-name lang="it">{channel_id_value}</display-name>\n'
                    f_out.write(new_display_name)

    # Sostituiamo il file originale con quello pulito
    os.replace(temp_file, epg_file)
    print("Elaborazione completata con successo su join.epg.")

if __name__ == "__main__":
    clean_epg()
