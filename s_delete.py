import os

def main():
    # 1. Cancella join.old se esiste
    file_da_eliminare = "join.old"
    if os.path.exists(file_da_eliminare):
        os.remove(file_da_eliminare)
        print(f"File {file_da_eliminare} eliminato con successo.")
    else:
        print(f"File {file_da_eliminare} non trovato, salto il passaggio.")

    # 2. Rinomina join.epg in join.old
    file_da_rinominare = "join.epg"
    nuovo_nome = "join.old"
    
    if os.path.exists(file_da_rinominare):
        # Se esiste già un vecchio join.old (magari non rimosso), lo sovrascriviamo
        if os.path.exists(nuovo_nome):
            os.remove(nuovo_nome)
        
        os.rename(file_da_rinominare, nuovo_nome)
        print(f"File {file_da_rinominare} rinominato in {nuovo_nome}.")
    else:
        print(f"File {file_da_rinominare} non trovato. Impossibile rinominare.")

if __name__ == "__main__":
    main()
