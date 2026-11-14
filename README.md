# Feed RSS per Il Giornale dell'Arte (e lettura di Quotidiano Arte) su Android e-ink

Documentazione scritta il 14 novembre 2026, subito dopo aver messo in funzione tutto. È pensata per chi la rilegge a distanza di anni (probabilmente io stesso) e deve capire cosa fa questa repository, perché è fatta così, cosa era stato provato e scartato, e come rimettere in piedi le cose se si rompono. Nell'ultima sezione c'è la cronologia di come ci siamo arrivati, scritta come il racconto di una conversazione.

## 1. A cosa serve e perché esiste

Volevo leggere in un unico posto, su un Android con schermo e-ink (un Boox), gli articoli di due testate d'arte: Quotidiano Arte (quotidianoarte.com) e Il Giornale dell'Arte (ilgiornaledellarte.com). I requisiti erano tre: nessuna pubblicità, nessun fastidio (cookie, avvisi, pagine che si caricano a metà), e un'interfaccia adatta all'e-ink. In più non volevo pagare nulla né gestire un server.

La soluzione è un normale lettore RSS per Android, Feeder, che è gratuito, open source, senza pubblicità e con un'interfaccia minimale che si presta bene all'e-ink. Il problema è che solo una delle due testate offre un feed RSS: Quotidiano Arte ce l'ha, Il Giornale dell'Arte no. Questa repository serve a produrre il feed mancante, senza server e senza costi, usando le funzioni gratuite di GitHub.

## 2. Come funziona, in breve

Ogni tre ore GitHub Actions avvia lo script `build_feed.py`. Lo script legge le pagine con gli ultimi articoli del Giornale dell'Arte, trova i link, scarica gli articoli nuovi per leggerne titolo, estratto e data, e riscrive il file `docs/feed.xml`. GitHub Pages pubblica la cartella `docs` a un indirizzo fisso. Feeder sul telefono legge quell'indirizzo come un qualsiasi feed e, quando apro un articolo, scarica da solo il testo completo dal sito.

```
GitHub Actions (ogni 3 ore, 17 minuti dopo l'ora, orario UTC)
        |
        v
build_feed.py  ->  docs/feed.xml + docs/state.json  ->  commit nella repo
                                   |
                                   v
                        GitHub Pages (cartella /docs)
                                   |
                                   v
            https://spiretown.github.io/giornale-arte-feed/feed.xml
                                   |
                                   v
              Feeder (Android/Boox): titolo + estratto, poi testo intero
```

## 3. Indirizzi e dati da ricordare

- Account GitHub: `spiretown`. Repository pubblica: `https://github.com/spiretown/giornale-arte-feed`.
- Feed del Giornale dell'Arte (quello da incollare in Feeder): `https://spiretown.github.io/giornale-arte-feed/feed.xml`.
- Feed di Quotidiano Arte (esiste già, non serve nulla di mio): `https://www.quotidianoarte.com/feed/`.
- Pagine da cui lo script prende i link: `https://www.ilgiornaledellarte.com/UltimiArticoli` (la pagina "Ultime Notizie") e la home `https://www.ilgiornaledellarte.com/`.
- Cartella sul Mac usata per il primo caricamento: `~/Downloads/giornale-arte-feed` (potrebbe essere stata spostata o cancellata: la copia di riferimento è quella su GitHub).
- Pubblicazione di GitHub Pages: ramo `main`, cartella `/docs`.

## 4. Le due testate: com'è fatta ciascuna

**Quotidiano Arte** è un sito WordPress (il generatore dichiarato nella pagina è il tema Divi 4.24.0 al momento della verifica) ed è gratuito, senza paywall: la pagina si definisce un giornale online gratuito. Ha il feed RSS standard di WordPress all'indirizzo `/feed/`, verificato come RSS 2.0 valido. Ogni voce contiene l'articolo completo nell'elemento `content:encoded`, quindi in Feeder si legge senza dover scaricare altro. Gli articoli sono in ordine cronologico.

**Il Giornale dell'Arte** non ha nessun feed RSS. Nella home non c'è alcun link a un feed. L'indirizzo `/rss` restituisce una normale pagina HTML con un elenco di articoli, non un feed, e `/feed` non risponde. Non ho trovato nemmeno un indirizzo di sitemap né un file `robots.txt` raggiungibile. Gli articoli hanno indirizzi della forma `https://www.ilgiornaledellarte.com/Articolo/<titolo-con-trattini>`, e le sezioni stanno sotto `/Sezione/<nome>` e `/Sottosezione/<nome>` (per esempio Mostre, Economia, Libri, Fotografia, Archeologia, Musei e Fondazioni). Il sito promuove gli abbonamenti e parla di "Articoli Premium" e di un'area riservata, ma dal mio browser gli articoli si leggevano tutti senza account; non ho mai verificato quali contenuti, se ce ne sono, siano davvero a pagamento. Nel browser compare inoltre un avviso che segnala la presenza di un ad blocker e blocca la lettura. È un avviso mostrato dalla pagina nel browser: il lettore di Feeder scarica il testo senza passare dal browser e, nel mio caso, ha funzionato.

## 5. Cosa è stato provato e perché è stato scartato

**Feed di Google News con il filtro per sito** (l'indirizzo `https://news.google.com/rss/search?q=site:ilgiornaledellarte.com&hl=it&gl=IT&ceid=IT:it`): non richiede nulla, ma l'ho provato in Feeder e ha due difetti pesanti. Gli articoli non erano in ordine cronologico, e ogni link passa da una pagina di Google (con avvisi sui cookie) prima di arrivare al sito, dove poi compariva il blocco dell'ad blocker. Scartato.

**Servizi esterni che trasformano una pagina in feed** (Feedity, FetchRSS e simili) e **RSS-Bridge** (da installare su un server): non li ho provati. I primi hanno piani gratuiti limitati e dipendono da un servizio di terzi; il secondo richiede un server, che volevo evitare.

**Script su GitHub Actions + GitHub Pages**: è la soluzione adottata. Costa zero, non richiede server, gira da solo e produce un indirizzo fisso con link diretti al sito.

## 6. Lo script `build_feed.py` nel dettaglio

Lo script usa solo due librerie, `requests` e `beautifulsoup4`. Le costanti all'inizio del file regolano il comportamento: `SOURCES` (le due pagine da cui prendere i link), `MAX_ITEMS = 80` (articoli tenuti nel feed), `MAX_NEW = 30` (articoli nuovi scaricati a ogni esecuzione) e `DELAY = 1.5` (secondi di pausa tra una richiesta e l'altra, per non appesantire il sito).

La lettura delle pagine usa un User-Agent da browser normale e un timeout di 30 secondi. Dalle pagine elenco lo script prende tutti i link il cui percorso inizia con `/Articolo/`, accetta solo l'host `www.ilgiornaledellarte.com` (o senza `www`), scarta frammenti e parametri, e mantiene l'ordine in cui compaiono nella pagina, eliminando i doppioni. Il filtro sull'host c'è perché nei test un link del sottodominio Vernissage veniva accettato per errore.

Per ogni articolo non ancora noto, scarica la pagina e ne legge i metadati: il titolo da `og:title` (o `twitter:title`, o in ultima istanza dal tag `<title>`), togliendo il suffisso "| Il Giornale dell'Arte"; l'estratto da `og:description` (o `description`); la data da `article:published_time`, oppure dal campo `datePublished` nei dati strutturati JSON-LD, oppure dal primo tag `<time datetime>`. Se non trova nessuna data, usa la data di primo avvistamento, calcolata come "adesso meno N secondi", dove N è la posizione dell'articolo nella pagina (0 è il più recente): così l'ordine della pagina viene rispettato anche senza date. Un articolo che non si riesce a scaricare viene saltato e ritentato alla corsa successiva.

Lo script tiene la memoria degli articoli già visti in `docs/state.json`, per non riscaricare ogni volta tutto. Alla fine ordina gli articoli per data decrescente, ne tiene al massimo 80, ripulisce dallo stato quelli usciti dal feed e scrive `docs/feed.xml` in formato RSS 2.0. Se non trova nessun link `/Articolo/`, scrive un errore e termina con codice 1: sul lato GitHub l'esecuzione risulta fallita (croce rossa) e GitHub manda una mail. Con l'opzione `--dry` lo script stampa quello che trova senza scrivere nulla, ed è il modo giusto per verificare dopo un guasto.

Una scelta voluta: nel feed ci sono soltanto titolo, link, data ed estratto, non il testo completo. Il sito GitHub Pages è pubblico, e non voglio ripubblicare in rete gli articoli di una testata; il testo lo scarica Feeder sul mio telefono, per mio uso personale. Un dettaglio osservato: nel feed pubblicato le date hanno tutte l'ora 00:00:00, quindi il sito fornisce solo il giorno, e l'ordine tra articoli dello stesso giorno non è garantito (segue l'ordine di scoperta).

## 7. Il workflow GitHub Actions

Il file `.github/workflows/feed.yml` fa partire il lavoro ogni tre ore (`cron: "17 */3 * * *"`, cioè al minuto 17 delle ore 0, 3, 6, ... in orario UTC) e anche a mano dalla scheda Actions (`workflow_dispatch`). Ha il permesso di scrittura sul contenuto della repository (`contents: write`) per poter salvare il feed aggiornato. I passaggi sono: scaricare la repo, installare Python 3.12, installare `requests` e `beautifulsoup4`, eseguire lo script, e fare commit e push della cartella `docs` solo se è cambiato qualcosa. GitHub può disattivare i workflow programmati dopo 60 giorni senza attività nella repository: se il feed smette di aggiornarsi, per prima cosa va controllata la scheda Actions e, se il workflow è disattivato, riattivato con un clic.

## 8. Ricostruire tutto da zero

1. Verificare lo script in locale, dalla cartella del progetto: `python3 -m venv ~/feedvenv`, poi `~/feedvenv/bin/pip install requests beautifulsoup4`, poi `~/feedvenv/bin/python build_feed.py --dry`. Deve elencare gli articoli con la data e chiudersi con "Articoli nel feed: N".
2. Creare su GitHub un repository pubblico (nome `giornale-arte-feed`), senza README, `.gitignore` o licenza.
3. Caricare i file con `git init -b main`, `git add .`, `git commit -m "Primo commit"`, `git remote add origin https://github.com/spiretown/giornale-arte-feed.git`, `git push -u origin main`. Se chiede la password va usato un token personale (GitHub, Settings, Developer settings, Personal access tokens, Tokens classic) con le voci `repo` e `workflow` spuntate: senza `workflow` il push dei file in `.github/workflows` viene rifiutato.
4. Nella scheda Actions abilitare i workflow, scegliere "Aggiorna feed" e premere "Run workflow". Dopo circa un minuto, con la spunta verde, nella repo compare la cartella `docs`.
5. In Settings, Pages: "Deploy from a branch", ramo `main`, cartella `/docs`, Save. Dopo uno o due minuti il feed è raggiungibile all'indirizzo del punto 3 della sezione "Indirizzi".

Il passo 5 va fatto dopo il passo 4, perché la cartella `docs` deve esistere prima di poterla scegliere.

## 9. Configurazione di Feeder

In Feeder si aggiunge il feed con l'indirizzo completo che finisce con `feed.xml` (e quello di Quotidiano Arte con `/feed/`). Per il feed del Giornale dell'Arte, nelle impostazioni del singolo feed vanno sistemate due opzioni: scaricare l'articolo intero per impostazione predefinita (altrimenti si vede solo l'estratto) e aprire le voci nel lettore di Feeder invece che nel browser (altrimenti ogni tocco apre il sito, con cookie e avviso dell'ad blocker). Per l'e-ink, su Boox si possono usare le impostazioni per singola app per rendere più leggibile la grafica; questo era un suggerimento e non l'ho mai verificato nel dettaglio.

## 10. Manutenzione e risoluzione dei problemi

**Il feed non si aggiorna più.** Aprire la scheda Actions della repository e guardare l'ultima esecuzione. Se è rossa, aprirla e leggere il messaggio. Il caso più probabile è "ERRORE: nessun link /Articolo/ trovato": significa che il sito ha cambiato struttura o blocca l'accesso. In quel caso si aprono nel browser le pagine `/UltimiArticoli` e un articolo, si guarda com'è fatto l'indirizzo degli articoli e dove stanno titolo e data, e si aggiornano le funzioni `article_links` e `parse_article` nello script. Se invece Actions risulta disattivato, riattivarlo (vedi sezione 7).

**In Feeder compare "nessun feed trovato".** Quasi sempre l'indirizzo è incompleto: deve cominciare con `https://` e finire con `feed.xml`. Provare ad aprirlo nel browser del telefono: se si vede del testo XML con gli articoli, il feed è raggiungibile; se dà errore 404, il sito di GitHub Pages non è ancora pronto (basta aspettare un paio di minuti).

**Toccando un articolo si apre il sito del Giornale dell'Arte.** È normale che il link punti al sito, ma Feeder dovrebbe aprirlo nel suo lettore. Controllare le due opzioni del feed descritte nella sezione 9. Se il testo completo non compare nemmeno così, il sito potrebbe caricare il testo con JavaScript: in quel caso lo script andrebbe cambiato per leggere il testo in modo diverso.

**Errore "remote origin already exists" al primo caricamento.** Significa che il collegamento con GitHub esiste già. Si risolve con `git remote set-url origin https://github.com/spiretown/giornale-arte-feed.git` e poi `git push -u origin main`.

## 11. Limiti noti e idee per il futuro

Non so quali articoli del Giornale dell'Arte siano davvero a pagamento: gli articoli che ho letto erano aperti, ma il sito parla di contenuti premium e un domani potrebbe chiudere di più. Le date hanno solo il giorno. Lo script è stato scritto basandosi sulla struttura osservata dalle pagine e provato con pagine simulate, perché la rete dell'ambiente in cui l'ho sviluppato non raggiungeva il sito; la verifica reale è stata la prima esecuzione su GitHub, che ha prodotto un feed con 30 articoli in ordine, con link diretti. Idee possibili: feed separati per sezione (per esempio Mostre o Fotografia) leggendo le pagine `/Sezione/...`; un'intestazione Atom con l'indirizzo del feed; e, nello stesso spirito, la mia cartella `~/Desktop/reflow` che ricompone i PDF dei quotidiani per il Boox è un progetto affine, ma separato da questo.

## 12. Cronologia della conversazione

Ho chiesto a Claude un'app Android capace di raccogliere gli articoli di Quotidiano Arte e del Giornale dell'Arte in un posto solo, senza pubblicità e adatta all'e-ink. Claude ha controllato i due siti: Quotidiano Arte ha un feed RSS completo, Il Giornale dell'Arte no. Ha consigliato Feeder come app, e per il secondo sito un feed generato.

Ho provato il feed di Google News con il filtro per sito. Non era in ordine cronologico e i link passavano da Google, con il blocco dell'ad blocker al clic. Claude ha quindi proposto la soluzione senza server né costi: uno script su GitHub che produce un feed con link diretti. Mi ha dato lo zip con `build_feed.py` e il workflow, e un test con pagine simulate ha corretto un difetto (accettava anche link di un sottodominio sbagliato).

Ho seguito i passi dal Mac: prova locale, creazione della repository, caricamento (con un errore "remote origin already exists" risolto con `git remote set-url`), esecuzione del workflow, attivazione di Pages. Claude ha verificato il feed pubblicato: 30 articoli, ordinati, link diretti. In Feeder prima l'indirizzo non veniva riconosciuto ("nessun feed trovato"), poi il feed è partito; infine ho sistemato le due opzioni del feed (testo intero e apertura nel lettore). Al termine tutto funzionava.
