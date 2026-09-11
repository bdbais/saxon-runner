# Code review — Saxon Runner 3.0

Revisione di `SaxonRunner-3.pyw` (2084 righe), la versione da cui era compilato `SaxonRunner-3.exe`. I numeri di riga si riferiscono a `saxon_runner.py` nel primo commit del repository (*Sorgenti originali di Saxon Runner 3.0*), identico al file originale. Tutti i punti segnati come risolti sono corretti nella 3.1.0.

## In breve

Il programma è ben organizzato: classi separate per editor, pannelli di output, AI, watcher e impostazioni, nessuna dipendenza fuori dalla libreria standard, e `subprocess` chiamato con una lista di argomenti (niente `shell=True`, quindi niente iniezione di comandi dai campi della UI). Le funzioni pensate per chi scrive XSLT funzionano: errori cliccabili, suggerimenti sui codici d'errore, watch, esecuzioni recenti.

I problemi seri sono concentrati in quattro aree:

1. **Thread e Tkinter**: il pannello chat modifica i widget da un thread secondario.
2. **File**: salvataggi che possono perdere modifiche o alterare la codifica, output scritti nel posto sbagliato senza dirlo.
3. **Collegamento errori → editor**: rotto proprio con il formato di percorso che Saxon usa di solito.
4. **Prestazioni dell'editor**: l'evidenziazione è quadratica e blocca l'interfaccia sui file lunghi.

| # | Gravità | Problema | Stato |
|---|---|---|---|
| 1 | Alta | Widget Tk modificati da thread secondari | Risolto |
| 2 | Alta | File non UTF-8 alterati al primo salvataggio | Risolto |
| 3 | Alta | Modifiche perse se il salvataggio fallisce alla chiusura | Risolto |
| 4 | Alta | Link agli errori rotti con `file:/C:/…` e spazi | Risolto |
| 5 | Alta | Output scritto nella cartella di lavoro dell'exe, errori ignorati | Risolto |
| 6 | Media | Finestra console di Java a ogni esecuzione | Risolto |
| 7 | Media | Righe d'errore dei moduli inclusi segnate sul file sbagliato | Risolto |
| 8 | Media | Watch avvia esecuzioni in parallelo | Risolto |
| 9 | Media | Evidenziazione quadratica (9 s su 3000 righe) | Risolto |
| 10 | Media | Qualsiasi tasto marca il file come modificato | Risolto |
| 11 | Media | Parametri extra spezzati sugli spazi | Risolto |
| 12 | Media | Un errore di rete diventa un suggerimento da inserire | Risolto |
| 13 | Media | Suggerimenti in ritardo e popup che ruba i tasti | Risolto |
| 14 | Media | Timeout globale del socket e attributi privati | Risolto |
| 15 | Media | "Annulla" nelle impostazioni non annulla i JAR | Risolto |
| 16 | Media | Configurazione non atomica, azzerata in silenzio se corrotta | Risolto |
| 17 | Bassa | Pulsante Watch perde il colore | Risolto |
| 18 | Bassa | STOP mostrato come "Errori" | Risolto |
| 19 | Bassa | Watch OFF/ON rapido crea due thread | Risolto |
| 20 | Bassa | Ctrl+Z dopo l'apertura svuota il file; ricarica sposta il cursore | Risolto |
| 21 | Bassa | DPI impostato dopo la creazione della finestra | Risolto |
| 22 | Bassa | Ctrl+O nell'editor inserisce un a capo | Risolto |
| 23 | Bassa | Un `.saxcfg` attiva un JAR qualsiasi senza dirlo | Mitigato |
| 24 | Bassa | Output bufferizzato fino alla fine | Aperto |
| 25 | Bassa | Nessuna indicazione quando l'endpoint AI è remoto | Documentato |
| 26 | — | Organizzazione del progetto e build | Risolto |

---

## Alta

### 1. Widget Tk modificati da thread secondari

`AIClient.stream` (r. 242–266) esegue il ciclo di lettura in un thread e chiama direttamente `on_token` e `on_done`. In `AIPanel.send` (r. 474–500) quelle funzioni inseriscono testo in `chat_txt` e cambiano lo stato del pulsante: **dal thread secondario**. Tkinter non è thread-safe. A seconda di come è compilato Tcl si va da blocchi occasionali a `RuntimeError: main thread is not in main loop` o a crash di Tcl, tanto più probabili quanto più velocemente arrivano i token. Stesso schema, meno grave, in `_trigger_ac.on_result` (r. 834: `winfo_exists()` dal thread), `SettingsDialog.test_conn` (r. 1531), `_run.worker` (r. 1859–1871) e nel callback del watcher (r. 1916).

**Correzione:** una coda (`ui_call`) svuotata dal main loop ogni 30 ms. I thread di lavoro accodano la funzione e non toccano più i widget; `AIClient` consegna i token già sul thread di Tk.

### 2. File non UTF-8 alterati al primo salvataggio

`load_file` legge con `encoding="utf-8", errors="replace"` (r. 994–995), `save_file` riscrive in UTF-8 (r. 1017). Uno stylesheet in ISO-8859-1 o Windows-1252 (frequente nei progetti SAP) aperto e salvato perde tutte le lettere accentate, sostituite da `U+FFFD`, e il file non corrisponde più alla sua dichiarazione `<?xml encoding="ISO-8859-1"?>`. Nessun avviso.

**Correzione:** lettura binaria con riconoscimento della codifica (UTF-8 con o senza BOM, poi cp1252, poi latin-1) e salvataggio nella stessa codifica e con gli stessi a capo. Se il testo contiene un carattere che la codifica non rappresenta, il salvataggio si ferma con un messaggio chiaro.

### 3. Modifiche perse se il salvataggio fallisce alla chiusura

In `_on_close` (r. 2064–2070) e in `load_file` (r. 987–992), rispondendo "Sì, salva" viene chiamato `save_file()` ma il valore restituito è ignorato. Se il salvataggio fallisce (file in sola lettura, disco pieno) o se l'utente annulla il "Salva con nome" di un file nuovo, il programma si chiude o carica l'altro file comunque: modifiche perse.

**Correzione:** `confirm_unsaved()` restituisce `False` se il salvataggio non è riuscito, e chiusura, apertura e aggiornamento si fermano.

### 4. Link agli errori rotti con `file:/C:/…` e spazi

Saxon indica i file come URI `file:/C:/Users/…/My%20Dir/a.xsl`: una sola barra dopo `file:` e spazi codificati. È il formato che compare anche nei log della cartella `dist` originale. `_LOC_RE` (r. 125–126) riconosce come URI solo `file:///`. La seconda alternativa cattura comunque il testo, ma `_clean` (r. 1368–1375) non toglie `file:/` e non decodifica `%20`, e il percorso che ne esce non esiste. I nomi relativi (`a.xsl`, tipici di Saxon 10+) vengono risolti rispetto alla cartella di lavoro del programma invece che a quella dello stylesheet. Risultato: il clic su un errore dà "Errore apertura" proprio nei casi più comuni.

**Correzione:** `resolve_location()` usa `urllib.parse` e `url2pathname` (gestisce anche `\\server\share`) e risolve i nomi relativi rispetto alla cartella dello stylesheet. Coperto da test.

### 5. Output scritto nella cartella di lavoro dell'exe, errori ignorati

La cartella di output predefinita è `os.getcwd()` (r. 1725, 1828). Per un exe avviato dal menu Start è la cartella d'installazione o `C:\Windows\System32`, spesso non scrivibili. La scrittura dei due file è dentro `except Exception: pass` (r. 1845–1848), e la barra di stato dice comunque "✅ Completato → C:\…\output.log": un file che non esiste.

**Correzione:** senza cartella indicata si scrive accanto allo stylesheet; una cartella inesistente viene segnalata prima di partire; un errore di scrittura compare in console e nella barra di stato.

## Media

### 6. Finestra console di Java a ogni esecuzione

L'exe è compilato senza console (`console=False`), `java.exe` è un programma console e `Popen` (r. 1841) non passa `CREATE_NO_WINDOW`: Windows apre una finestra nera per ogni trasformazione, e con Watch attivo a ogni salvataggio. **Correzione:** `creationflags=CREATE_NO_WINDOW`.

### 7. Righe d'errore dei moduli inclusi segnate sul file sbagliato

`_parse_err_lines` (r. 1879–1885) raccoglie i numeri di riga di qualunque `.xsl` citato nello stderr, e `mark_error_lines` (r. 1853) li segna sul file aperto nell'editor. Con `xsl:include`/`xsl:import`, un errore alla riga 7 di `common.xsl` evidenzia la riga 7 dello stylesheet principale. **Correzione:** `error_lines_for()` tiene solo le righe il cui file corrisponde a quello aperto.

### 8. Watch avvia esecuzioni in parallelo

`_on_file_changed` (r. 1908–1916) chiama `_run()` senza controllare se un'esecuzione è in corso. Con una trasformazione lenta e salvataggi ravvicinati partono più `java` insieme: scrivono sugli stessi `output.log`/`console.log`, `self.process` punta solo all'ultimo (STOP ferma solo quello) e le schede mostrano il risultato di chi finisce per ultimo. **Correzione:** un'esecuzione alla volta; un cambiamento durante l'esecuzione ne programma una sola successiva.

### 9. Evidenziazione quadratica

`_highlight` (r. 1091–1100) converte ogni corrispondenza da offset a indice Tk con `_off` (r. 1102–1107), che copia e scandisce tutto il testo precedente: costo proporzionale a *corrispondenze × lunghezza del file*. Parte 260 ms dopo ogni tasto, sul thread dell'interfaccia. Misurato sulla sola conversione degli indici:

| Stylesheet | 3.0 | 3.1 |
|---|---|---|
| 1000 righe, 11 000 corrispondenze | 0,97 s | 21 ms |
| 3000 righe, 33 000 corrispondenze | 8,95 s | 55 ms |

**Correzione:** inizi riga calcolati una volta e ricerca binaria (`bisect`), più `tag_add` con molte coppie per chiamata. Un test verifica che gli indici siano identici a quelli del calcolo originale.

### 10. Qualsiasi tasto marca il file come modificato

`_on_edit` è legato a `<KeyRelease>` e imposta `dirty` per ogni tasto (r. 803–804): frecce, Ctrl, Maiusc, F3. Aprire un file e muoversi con le frecce basta per sentirsi chiedere "Salvare?" alla chiusura. **Correzione:** si usa l'evento `<<Modified>>` del widget Text, che scatta solo quando il testo cambia.

### 11. Parametri extra spezzati sugli spazi

`extra.split()` (r. 1821) divide anche dentro le virgolette: `titolo="Ordini di settembre"` diventa tre argomenti e Saxon si ferma, lo stesso per `-o:"C:\Output finali\x.xml"`. `shlex.split` non va bene su Windows perché tratta `\` come escape. **Correzione:** `split_args()` divide come `cmd.exe` (spazi fuori dalle virgolette doppie) e lascia intatte le barre rovesciate. Coperto da test.

### 12. Un errore di rete diventa un suggerimento

`AIClient.once` restituisce `"[Errore AI: …]"` invece di sollevare un'eccezione (r. 230–231), e `autocomplete` usa la risposta grezza come suggerimento quando non trova righe numerate (r. 280–281). Con Ollama spento il popup propone di inserire nel codice il messaggio d'errore. **Correzione:** `once` solleva l'eccezione, `autocomplete` restituisce un elenco vuoto.

### 13. Suggerimenti in ritardo e popup che ruba i tasti

La risposta dell'autocompletamento arriva secondi dopo e viene mostrata anche se nel frattempo si è scritto altro o spostato il cursore (r. 833–838): accettarla inserisce il testo nel punto sbagliato. Il popup prende il focus (r. 350), quindi i tasti successivi finiscono nella lista invece che nell'editor. **Correzione:** contatore di generazione e controllo della posizione del cursore; il popup non prende il focus e l'editor gli inoltra ↑ ↓ Tab Invio Esc.

### 14. Timeout globale del socket e attributi privati

Per lo streaming `_post` (r. 181–190) cambia `socket.setdefaulttimeout`, che è globale e vale anche per le richieste degli altri thread in quel momento, e poi usa `r.fp.raw._sock`, un attributo privato che non esiste per ogni tipo di risposta (in quel caso l'`AttributeError` diventa "Errore connessione AI"). **Correzione:** `urlopen(…, timeout=…)`, che si applica a connessione e singole letture; 300 s di attesa massima fra due pezzi, per i modelli lenti su CPU.

### 15. "Annulla" nelle impostazioni non annulla i JAR

`SettingsDialog` lavora direttamente sul dizionario di configurazione (r. 1449). Aggiungi, rimuovi e *Imposta attivo* (r. 1563–1596) lo modificano subito: "Annulla" chiude la finestra ma le modifiche restano in memoria e vengono salvate alla prima esecuzione (`_add_to_recent` → `_save_cfg`). **Correzione:** la finestra lavora su una copia (`deepcopy`) applicata solo con OK.

### 16. Configurazione non atomica, azzerata in silenzio se corrotta

`_save_cfg` (r. 1643–1647) scrive direttamente sul file: un'interruzione a metà lascia un JSON troncato. Al riavvio `_load_cfg` (r. 1637–1640) ignora l'errore e riparte dai valori predefiniti, e il primo salvataggio sovrascrive il file: elenco dei JAR e cronologia persi senza avviso. **Correzione:** scrittura su file temporaneo e `os.replace`; se il file è illeggibile viene rinominato `.corrotto` e l'utente viene avvisato.

## Bassa

17. **Pulsante Watch.** `_Btn` ripristina all'uscita del mouse il colore catturato alla creazione (r. 606–608): dopo "Watch ON" (r. 1900) il viola torna grigio al primo passaggio del mouse. Ora il pulsante ricorda il colore corrente (`set_colors`).
18. **STOP.** `_stop` scrive "⛔ Interrotto" (r. 1877), poi il worker sovrascrive con "❌ Errori (exit 1)" e passa alla console (r. 1856–1858). Ora l'interruzione resta tale.
19. **Watcher.** Con OFF/ON ravvicinati il vecchio thread di `_poll`, ancora in `sleep`, trova `_running` di nuovo vero e continua accanto al nuovo (r. 561–586): doppie esecuzioni. Ora ogni thread ha una generazione.
20. **Undo e ricarica.** Dopo `load_file` la pila di undo contiene l'inserimento del file (r. 998–999): Ctrl+Z svuota l'editor. Ricaricando dal watch il cursore finisce in fondo al file. Ora `edit_reset()` dopo il caricamento, e posizione e scorrimento conservati nella ricarica.
21. **DPI.** `SetProcessDpiAwareness` è chiamata dopo `tk.Tk()` (r. 2075–2078), quando Tk ha già calcolato la scala: testo e dimensioni incoerenti sugli schermi ad alta risoluzione. Spostata prima.
22. **Ctrl+O nell'editor.** Il binding di classe del Text di Tk inserisce un a capo prima che la scorciatoia della finestra apra la configurazione. Disattivato.
23. **`.saxcfg` e JAR.** Aprire un `.saxcfg` (r. 2023–2026) aggiunge e attiva il JAR che contiene, che verrà eseguito alla prossima esecuzione. È un'azione dell'utente, ma un file ricevuto da altri può puntare a un JAR qualsiasi. Ora la barra di stato dice quale JAR è stato attivato; resta da valutare una conferma esplicita.
24. **Output bufferizzato.** `communicate()` (r. 1844) raccoglie tutto l'output e lo mostra solo alla fine: niente avanzamento per le trasformazioni lunghe, e un output di molti MB viene inserito nel Text in un colpo solo. Aperto: servirebbe la lettura incrementale di stdout/stderr.
25. **Endpoint AI remoto.** Con un endpoint diverso da `localhost`, autocompletamento e controllo inviano parti dello stylesheet a quel server senza un'indicazione nell'interfaccia. Ora è documentato nel manuale; un avviso nelle impostazioni sarebbe utile.

## Progetto e build

- **Tre copie del programma** (`SaxonRunner.pyw` v1, `SaxonRunner-2.pyw`, `SaxonRunner-3.pyw`) e nessun controllo di versione. `build_exe.bat` compila la v1 in `SaxonRunner.exe`, mentre `SaxonRunner.spec` compila la v3 *con lo stesso nome*: quale versione contenga `dist\SaxonRunner.exe` dipende dall'ultimo comando lanciato.
- **README fermo alla v1**: descrive menu in inglese (*Tools ▸ Settings*, *Add JAR…*) che nella v3 sono in italiano.
- **`upx=True`** nella spec: la compressione UPX è fra le cause più frequenti di falsi positivi antivirus sugli exe PyInstaller.
- **Versione ripetuta** in tre punti ("v3.0" nella docstring, nel titolo e in *Informazioni*).
- **`requirements`** contiene solo PyInstaller, che serve per compilare, non per eseguire.
- **File da non pubblicare**: `dist\console.log`, `dist\output.log` e `.idea\workspace.xml` contengono percorsi assoluti di progetti di lavoro. Esclusi dal repository con `.gitignore`.
- **Nessun test.**

Nella 3.1 il programma sta in `saxon_runner.py` con un solo `__version__`, `SaxonRunner.pyw` è il lanciatore, la spec non usa UPX e include l'icona, `requirements-dev.txt` dichiara PyInstaller, 23 test coprono le funzioni senza interfaccia e l'aggiornamento, e la CI su Windows compila, avvia l'exe in modalità `--self-test`, crea l'installer, prova installazione e disinstallazione e pubblica la release a ogni tag.
