# Changelog

## 3.1.1 — 2026-09-21

- Nuova icona: parentesi angolari e play, nei colori dell'interfaccia. Dentro lo stesso file il disegno cambia con la dimensione: completo dai 48 px in su, più spesso a 32, solo il play a 16 e 24, dove le parentesi diventerebbero una macchia.

## 3.1.0 — 2026-09-11

Prima versione pubblica.

Nuovo

- Installer per Windows con disinstallazione da "App installate", collegamenti nel menu Start e, a scelta, icona sul desktop e apertura dei file `.saxcfg` con doppio clic.
- Aggiornamento automatico: all'avvio Saxon Runner controlla se c'è una versione nuova, scarica l'installer, ne verifica il checksum SHA-256 e si riapre aggiornato. Si disattiva in Impostazioni ▸ Aggiornamenti.
- Menu Help: manuale utente (F1), controllo aggiornamenti, segnalazione di un problema, pagina del progetto, donazioni.
- Il percorso di java si può indicare nelle impostazioni; altrimenti si usa JAVA_HOME, poi il PATH.

Corretto

- Nessuna finestra nera di Java a ogni esecuzione.
- I link agli errori funzionano anche con i percorsi `file:/C:/…` e con le cartelle che contengono spazi; i nomi relativi si cercano nella cartella dello stylesheet.
- Gli errori di un modulo incluso non vengono più segnati sulle righe del file aperto nell'editor.
- Se il salvataggio fallisce o viene annullato, chiudere il programma o aprire un altro file non fa più perdere le modifiche.
- Un file non risulta più "non salvato" solo perché si sono usate le frecce.
- I file in ISO-8859-1 o Windows-1252 si salvano nella loro codifica, senza caratteri sostituiti, e con i loro a capo.
- Senza cartella di output, risultato e log si scrivono accanto allo stylesheet; un errore di scrittura viene mostrato invece di essere ignorato.
- Con Watch attivo, un salvataggio durante un'esecuzione non ne avvia una seconda in parallelo: si riparte quando la prima finisce.
- I parametri extra fra virgolette (`param="due parole"`, percorsi con spazi) arrivano a Saxon interi.
- Evidenziazione della sintassi molto più veloce: su uno stylesheet di 3000 righe da circa 9 secondi a 55 millisecondi dopo ogni modifica.
- Assistente AI: l'interfaccia non viene più toccata dai thread secondari (possibili blocchi), i suggerimenti arrivati in ritardo vengono scartati, il popup non ruba più i tasti e un errore di connessione non viene più proposto come suggerimento.
- "Annulla" nelle Impostazioni annulla davvero anche le modifiche all'elenco dei JAR.
- La configurazione si salva in modo atomico; se è illeggibile ne viene conservata una copia invece di sovrascriverla.
- Il pulsante Watch non perde il colore al passaggio del mouse; STOP mostra "Interrotto" invece di "Errori".
- Scala corretta sugli schermi ad alta risoluzione.

## 3.0

Versione interna: editor XSLT, watch dei file, assistente AI locale (Ollama / LM Studio).
