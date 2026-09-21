# Saxon Runner — Manuale utente

Versione 3.1 · [Scarica](https://github.com/bdbais/saxon-runner/releases/latest) · [Pagina del progetto](https://saxonrunner.bais.info/) · [Segnala un problema](https://github.com/bdbais/saxon-runner/issues)

Saxon Runner è un'interfaccia grafica per [Saxon](https://www.saxonica.com/), il processore XSLT e XQuery, su Windows. Invece di scrivere a mano

```
java -jar saxon-he-12.5.jar -xsl:trasforma.xsl -s:input.xml
```

scegli lo stylesheet e il file XML, premi **ESEGUI** e trovi il risultato e gli errori in due schede separate. Un clic su un errore apre lo stylesheet alla riga giusta.

- [1. Requisiti](#1-requisiti)
- [2. Installazione](#2-installazione)
- [3. Primo avvio: indicare Saxon](#3-primo-avvio-indicare-saxon)
- [4. Eseguire una trasformazione](#4-eseguire-una-trasformazione)
- [5. Leggere risultato ed errori](#5-leggere-risultato-ed-errori)
- [6. L'editor XSLT](#6-leditor-xslt)
- [7. Watch: riesecuzione automatica](#7-watch-riesecuzione-automatica)
- [8. Esecuzioni recenti e file .saxcfg](#8-esecuzioni-recenti-e-file-saxcfg)
- [9. Assistente AI locale](#9-assistente-ai-locale)
- [10. Aggiornamenti](#10-aggiornamenti)
- [11. Disinstallazione](#11-disinstallazione)
- [12. Dove stanno i file](#12-dove-stanno-i-file)
- [13. Problemi frequenti](#13-problemi-frequenti)
- [14. Scorciatoie da tastiera](#14-scorciatoie-da-tastiera)

---

## 1. Requisiti

| Cosa | Note |
|---|---|
| Windows 10 o 11, 64 bit | |
| Java | Saxon è un programma Java. Le versioni recenti di Saxon richiedono Java 11 o successivo: se non sai quale hai, installa un JDK 17 o 21 (per esempio Eclipse Temurin o Microsoft Build of OpenJDK). |
| Un JAR di Saxon | Saxon **HE** è gratuito ([download da Saxonica](https://www.saxonica.com/download/java.xml)). PE ed EE sono a pagamento e cercano il file di licenza nella stessa cartella del JAR. |

Saxon non è incluso in Saxon Runner: ognuno usa la versione (e la licenza) che gli serve, e può averne più d'una configurata.

> **Saxon 12 HE:** estrai lo zip scaricato *per intero* e lascia la cartella `lib` accanto al JAR. Il JAR la usa per le librerie `xmlresolver`; senza, Saxon si ferma con `NoClassDefFoundError`.

## 2. Installazione

### Con l'installer (consigliato)

1. Scarica **[SaxonRunner-Setup.exe](https://github.com/bdbais/saxon-runner/releases/latest/download/SaxonRunner-Setup.exe)**.
2. Avvialo. Alla prima domanda scegli se installare **solo per te** (nessuna password di amministratore; è la scelta consigliata) o **per tutti gli utenti** del PC.
3. Facoltativo: icona sul desktop e apertura dei file `.saxcfg` con doppio clic.

L'installazione per utente va in `%LOCALAPPDATA%\Programs\Saxon Runner`, quella per tutti in `C:\Program Files\Saxon Runner`. Nel menu Start compaiono Saxon Runner, questo manuale e il disinstallatore.

Solo la versione installata **si aggiorna da sola** (vedi [Aggiornamenti](#10-aggiornamenti)).

> **"Windows ha protetto il PC"** — l'eseguibile non è firmato con un certificato commerciale, e SmartScreen lo segnala finché non è diffuso. Fai clic su **Ulteriori informazioni ▸ Esegui comunque**. Se vuoi verificare il file, confronta il suo SHA-256 con quello pubblicato in `SHA256SUMS.txt` nella stessa release: `Get-FileHash .\SaxonRunner-Setup.exe` in PowerShell.

### Versione portatile

**[SaxonRunner-portable.exe](https://github.com/bdbais/saxon-runner/releases/latest/download/SaxonRunner-portable.exe)** è un unico file da mettere dove vuoi, anche su una chiavetta. Non si installa e non si aggiorna da sola: quando esce una versione nuova ti avvisa e ti porta alla pagina di download.

### Aggiornare dalla versione 3.0

Impostazioni, JAR e esecuzioni recenti stanno nello stesso file della 3.0 (`%USERPROFILE%\.saxon_runner_config.json`) e vengono ritrovati così come sono. La vecchia copia di `SaxonRunner.exe` si può cancellare.

## 3. Primo avvio: indicare Saxon

1. Menu **Strumenti ▸ Impostazioni…** (oppure il pulsante *Impostazioni…* in alto a sinistra).
2. Scheda **Saxon JAR** ▸ **Aggiungi JAR…** e scegli il file, per esempio `saxon-he-12.5.jar`.
3. Il primo JAR aggiunto diventa quello **attivo** (segnato con ●). Con più JAR (HE ed EE, versioni diverse) selezionane uno e premi **Imposta attivo ✓**, oppure fai doppio clic. **Su ↑** e **Giù ↓** cambiano solo l'ordine dell'elenco.
4. **Java da usare**: lascialo vuoto e Saxon Runner usa `JAVA_HOME`, poi il `java` che trova nel PATH. Indica un `java.exe` preciso se ne hai più d'uno installato.
5. **OK** salva; **Annulla** scarta tutte le modifiche fatte nella finestra.

## 4. Eseguire una trasformazione

La colonna di sinistra, **CONFIGURAZIONE**, contiene tutto quello che serve:

| Campo | Cosa mettere |
|---|---|
| Saxon JAR (attivo) | Solo lettura: si cambia nelle Impostazioni. |
| Script XSLT | Lo stylesheet (`…` per sfogliare). Viene aperto anche nell'editor. |
| XML sorgente | Il documento da trasformare. |
| Cartella output | Dove scrivere i due file qui sotto. **Vuota = la cartella dello stylesheet.** |
| File risultato | Copia del risultato (stdout di Saxon). Predefinito `output.log`. |
| File console log | Copia di messaggi ed errori (stderr). Predefinito `console.log`. |
| Parametri extra Saxon | Opzioni e parametri aggiuntivi, come sulla riga di comando. |

Premi **▶ ESEGUI**. Saxon Runner lancia

```
java -jar <JAR attivo> -xsl:<Script XSLT> -s:<XML sorgente> <parametri extra>
```

La riga esatta compare in cima alla scheda *Console / Errori*. **■ STOP** interrompe un'esecuzione lunga.

**Parametri extra**, qualche esempio:

| Scrivi | Effetto |
|---|---|
| `data=2026-09-11` | Passa il parametro `$data` allo stylesheet |
| `titolo="Ordini di settembre"` | Parametro con spazi: le virgolette lo tengono insieme |
| `?limite=10` | Parametro valutato come espressione XPath (numero, non stringa) |
| `-t` | Saxon stampa versione e tempi |
| `-o:"C:\Output finali\risultato.xml"` | Scrive il risultato in un file: la scheda *Risultato* resterà vuota |

La barra di stato sotto i pulsanti dice come è andata: ✅ completato (con il percorso del file risultato), ❌ errori, ⛔ interrotto. Se i file di log non si possono scrivere (cartella in sola lettura, file aperto in un altro programma) lo dice qui, e la trasformazione resta comunque visibile nelle schede.

## 5. Leggere risultato ed errori

**📄 Risultato** mostra quello che Saxon ha prodotto. **🖥 Console / Errori** mostra i messaggi, colorati:

| Colore | Significato |
|---|---|
| Rosso, grassetto | Errore o codice d'errore (`XPST0003`, `XTSE0010`, …) |
| Giallo | Avviso |
| Lilla sottolineato | Posizione nel file (`on line 12 column 5 of …`): **cliccabile** |
| Grigio | Stack trace di Java |

Quando ci sono errori, in cima alla console compare una barra con il conteggio e i pulsanti **▲ Prec. / ▼ Succ.** per scorrerli.

- **Clic su un codice d'errore** (sottolineato in giallo): spiegazione in italiano e suggerimento su cosa controllare.
- **Clic su una posizione**: apre il file nell'editor e porta il cursore su quella riga. Funziona anche per i moduli inclusi con `xsl:include`/`xsl:import` e per i percorsi con spazi.
- Le righe con errori vengono evidenziate in rosso anche nell'editor, ma solo se l'errore riguarda il file aperto.

In entrambe le schede: **Cerca** (Invio o ▼ per il successivo, ▲ per il precedente), **Clear** toglie le evidenziazioni, **🗑 Pulisci** svuota, **💾 Salva** salva il contenuto in un file.

## 6. L'editor XSLT

La scheda **✏️ Editor** apre lo stylesheet scelto: evidenziazione della sintassi, numeri di riga, rientro automatico, riga corrente. Il nome del file compare nella scheda, con ● quando ci sono modifiche non salvate.

- **💾 Salva** / Ctrl+S, **Salva con nome** / Ctrl+Maiusc+S.
- **📂 Apri…** apre un altro file XSLT o XML.
- **🔍 Trova** / Ctrl+F e **Sostituisci** / Ctrl+H: F3 o Invio per il successivo, Maiusc+Invio per il precedente. **Aa** attivo = maiuscole e minuscole indifferenti. **Sost.** sostituisce l'occorrenza corrente, **Tutti** tutte.
- **↕ Riga** / Ctrl+G: vai a una riga.
- Ctrl+Z / Ctrl+Y: annulla / ripeti.

Il file viene salvato **nella sua codifica e con i suoi a capo**: uno stylesheet in ISO-8859-1 resta ISO-8859-1. Se scrivi un carattere che quella codifica non può rappresentare, il salvataggio si ferma e te lo dice invece di sostituirlo.

Se chiudi il programma o apri un altro file con modifiche non salvate, Saxon Runner chiede se salvarle; se il salvataggio non riesce, resta tutto com'era.

## 7. Watch: riesecuzione automatica

**◯ Watch OFF** ▸ **⬤ Watch ON**: da quel momento Saxon Runner controlla lo stylesheet e l'XML sorgente e rilancia la trasformazione ogni volta che uno dei due cambia su disco, anche quando lo salvi dall'editor o da un altro programma. Se un salvataggio arriva mentre un'esecuzione è ancora in corso, la nuova parte appena quella finisce, una volta sola.

## 8. Esecuzioni recenti e file .saxcfg

Ogni esecuzione finisce nell'elenco **RECENT RUNS** (fino a 100; la stessa coppia XSLT + XML compare una volta sola). Doppio clic o **Carica** ripristinano tutti i campi e aprono lo stylesheet nell'editor. **Elimina** toglie una voce, **Clear all** le toglie tutte.

Per conservare o condividere una configurazione usa i file **`.saxcfg`** (JSON con stylesheet, XML, cartella e nomi di output, parametri e JAR):

| Menu File | Scorciatoia |
|---|---|
| Nuovo (svuota XSLT, XML e parametri) | Ctrl+N |
| Apri… | Ctrl+O |
| Salva | Ctrl+S (fuori dall'editor) |
| Salva con nome… | Ctrl+Maiusc+S (fuori dall'editor) |

Se all'installazione hai scelto l'associazione dei file, un doppio clic su un `.saxcfg` apre Saxon Runner già configurato. Un `.saxcfg` ricevuto da altri può attivare un JAR diverso dal tuo: dopo l'apertura la barra di stato dice quale JAR verrà eseguito.

## 9. Assistente AI locale

Facoltativo. Saxon Runner può usare un modello linguistico **che gira sul tuo computer** con [Ollama](https://ollama.com) o LM Studio, o qualsiasi servizio compatibile con l'API OpenAI.

**Preparazione con Ollama**

1. Installa Ollama da <https://ollama.com>.
2. Scarica un modello adatto al codice, per esempio: `ollama pull qwen2.5-coder:7b` (oppure `mistral`, `deepseek-coder-v2`).
3. In **Impostazioni ▸ 🤖 AI Locale**: endpoint `http://localhost:11434` (LM Studio: `http://localhost:1234`), nome del modello come l'hai scaricato, poi **🔌 Testa connessione**.

Il pallino accanto a *✨ Check AI* nella barra dell'editor è verde quando l'assistente risponde, rosso con "offline" quando non lo trova.

**Cosa fa**

- **Autocompletamento**: quando smetti di scrivere per un attimo (0,7 s, regolabile) propone tre completamenti. ↑ ↓ per scegliere, **Tab** o **Invio** per inserire, **Esc** per chiudere; se continui a scrivere il popup sparisce da solo.
- **✨ Check AI**: analizza lo stylesheet e segna nell'editor le righe con problemi (rosso = errore, giallo = avviso), con la spiegazione nel pannello.
- **🤖 Chat AI**: apre sotto l'editor un pannello di chat che conosce lo stylesheet aperto. **📋 Includi XSL** chiede un riassunto di cosa fa, **🗑 Cancella** ricomincia la conversazione.

Le risposte di un modello possono essere sbagliate: il riferimento resta quello che dice Saxon quando esegui.

**Cosa viene inviato, e a chi.** Solo all'endpoint che hai indicato: per l'autocompletamento le ultime 40 righe prima del cursore, per il controllo i primi 3000 caratteri dello stylesheet, per la chat i tuoi messaggi e i primi 4000 caratteri come contesto. Con un endpoint su `localhost` non esce niente dal computer. Se indichi un server remoto, il codice va a quel server. Per spegnere tutto: togli la spunta a *Abilita funzionalità AI*; per il solo autocompletamento, a *Autocompletamento mentre scrivi*.

## 10. Aggiornamenti

Pochi secondi dopo l'avvio Saxon Runner chiede a GitHub il numero dell'ultima versione pubblicata. Non invia file, percorsi o impostazioni. Se c'è una versione più recente compare una finestra con le novità e tre scelte:

- **⬇ Aggiorna ora** (versione installata): scarica l'installer, ne verifica il checksum SHA-256 con quello pubblicato, chiede di salvare eventuali modifiche, chiude il programma, installa e lo riapre aggiornato. Impostazioni e cronologia restano.
- **Più tardi**: te lo richiederà al prossimo avvio.
- **Salta questa versione**: non te la riproporrà all'avvio. Si può sempre aggiornare a mano con **Help ▸ Controlla aggiornamenti…**.

La versione portatile e quella avviata dai sorgenti mostrano invece **Apri la pagina di download**.

Per non controllare più all'avvio: **Impostazioni ▸ Aggiornamenti** ▸ togli la spunta. Da lì c'è anche **Controlla ora**.

## 11. Disinstallazione

**Impostazioni di Windows ▸ App ▸ App installate ▸ Saxon Runner ▸ Disinstalla**, oppure **menu Start ▸ Saxon Runner ▸ Disinstalla Saxon Runner**.

Alla fine il disinstallatore chiede se eliminare anche le impostazioni (JAR configurati, esecuzioni recenti, impostazioni AI). La risposta predefinita è **No**, utile se pensi di reinstallarlo. I tuoi stylesheet, file XML, output e JAR di Saxon non vengono mai toccati.

La versione portatile si "disinstalla" cancellando l'exe; le impostazioni stanno nei file indicati qui sotto.

## 12. Dove stanno i file

| File | Contenuto |
|---|---|
| `%USERPROFILE%\.saxon_runner_config.json` | JAR, java, esecuzioni recenti, impostazioni AI e aggiornamenti |
| `%USERPROFILE%\.saxon_runner_config.json.corrotto` | Compare solo se la configurazione era illeggibile: è la copia del file originale |
| `%USERPROFILE%\.saxon_runner.log` | Compare solo in caso di errori imprevisti del programma: allegalo quando segnali un problema |
| `%LOCALAPPDATA%\Programs\Saxon Runner\` | Programma installato per l'utente (per tutti: `C:\Program Files\Saxon Runner\`) |

## 13. Problemi frequenti

**"java non trovato".** Java non è installato, oppure non è nel PATH. Installa un JDK o indica il percorso di `java.exe` in *Impostazioni ▸ Saxon JAR ▸ Java da usare*.

**"Saxon JAR non impostato".** Aggiungi un JAR in *Strumenti ▸ Impostazioni ▸ Saxon JAR*.

**`NoClassDefFoundError: org/xmlresolver/…` con Saxon 12.** Manca la cartella `lib` accanto al JAR: estrai di nuovo lo zip di Saxon per intero.

**`UnsupportedClassVersionError`.** Il Java in uso è troppo vecchio per quella versione di Saxon: installa un Java più recente e, se serve, indicalo nelle impostazioni.

**Saxon PE/EE: "No license file found".** Metti il file di licenza (`saxon-license.lic`) nella stessa cartella del JAR.

**La scheda Risultato è vuota ma non ci sono errori.** Hai usato `-o:` nei parametri extra: il risultato è nel file indicato.

**Il clic su un errore dice che il file non esiste.** Succede se l'errore riguarda un file che Saxon ha letto da un URL (`http:`) o da un archivio: l'editor apre solo file locali.

**L'assistente AI risulta offline.** Ollama non è avviato, oppure endpoint o nome del modello non corrispondono: verifica con *🔌 Testa connessione* e con `ollama list`.

**"Impossibile controllare gli aggiornamenti".** Di solito un proxy o un firewall aziendale che blocca `api.github.com`. Il programma funziona lo stesso; puoi scaricare le nuove versioni dalla [pagina delle release](https://github.com/bdbais/saxon-runner/releases).

**L'antivirus blocca l'exe.** Gli eseguibili creati con PyInstaller a volte generano falsi positivi. Verifica il checksum con `SHA256SUMS.txt` della release e, se è corretto, segnala il falso positivo al produttore dell'antivirus.

Per tutto il resto: **Help ▸ Segnala un problema**, indicando versione di Saxon Runner (*Help ▸ Informazioni*), versione di Saxon e, se c'è, il contenuto di `.saxon_runner.log`.

## 14. Scorciatoie da tastiera

| Dove | Tasti | Azione |
|---|---|---|
| Ovunque | F1 | Questo manuale |
| Ovunque | Ctrl+N / Ctrl+O | Nuova configurazione / apri `.saxcfg` |
| Fuori dall'editor | Ctrl+S / Ctrl+Maiusc+S | Salva configurazione / con nome |
| Editor | Ctrl+S / Ctrl+Maiusc+S | Salva lo stylesheet / con nome |
| Editor | Ctrl+F / Ctrl+H | Trova / Sostituisci |
| Editor | F3, Invio · Maiusc+Invio | Occorrenza successiva · precedente (nel campo Cerca) |
| Editor | Ctrl+G | Vai alla riga |
| Editor | Ctrl+Z / Ctrl+Y | Annulla / Ripeti |
| Editor | Tab | Due spazi, o accetta il suggerimento dell'AI |
| Editor | Esc | Chiude il popup dei suggerimenti o la barra di ricerca |

---

Saxon Runner è gratuito e open source (licenza Apache 2.0). Se ti fa risparmiare tempo puoi [offrire un caffè](https://paypal.me/bellizia). Saxon è un prodotto di Saxonica Ltd; questo progetto non è affiliato con Saxonica.
