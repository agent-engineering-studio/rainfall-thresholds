# Il banco di taratura

Una pagina per un ente: tarare una soglia di pioggia per le frane sulle frane
del passato, e misurarne il costo in falsi allarmi sui propri dati.

> **Una soglia superata non è un'allerta.** L'allerta ufficiale è il
> bollettino di criticità del Dipartimento della Protezione Civile.

Non è un sistema di allerta e non legge pioggia dal vivo: per quello c'è
[Limen](https://github.com/agent-engineering-studio/limen). La pagina sta
prima (la taratura) e dopo (la verifica), mai nel momento dell'allerta.

## Avviarla

Con Docker, dalla radice del repository:

```bash
TARATURA_ENTE="Comune di Gioia del Colle" TARATURA_REGIONE=Puglia docker compose up taratura
# http://localhost:3001
```

Con [uv](https://docs.astral.sh/uv/) e Node:

```bash
make app        # scarica Bootstrap Italia in static/vendor e avvia su http://127.0.0.1:8000
make app-test   # i test dell'API
```

| Variabile | Che cosa fa | Senza |
|---|---|---|
| `TARATURA_ENTE` | il nome dell'ente in testata | "Banco di taratura" |
| `TARATURA_REGIONE` | la regione selezionata all'apertura, scritta come in e-ITALICA (`Puglia`, `Emilia-Romagna`); un nome sconosciuto è ignorato | nessuna: tutta Italia |
| `TARATURA_PORT` | la porta con Docker | 3001 |

La porta è aperta solo su `127.0.0.1`: per pubblicarla, mettetela dietro il
proxy del vostro sito.

## Che cosa fa

1. **Le frane.** Il catalogo e-ITALICA è già caricato (5.974 frane, 1996–2021,
   pioggia dal pluviometro più vicino). Si filtra per regione, mese e tipo di
   frana, oppure si incollano le frane dell'ente (durata in ore, pioggia in mm).
2. **La soglia.** `I = α · D^(-β)` al percentile scelto, con il grafico, la
   pioggia che chiede da 1 a 72 ore e il confronto con la soglia nazionale.
3. **Il costo in falsi allarmi.** «Non misurato» finché l'ente non carica la
   serie oraria di un suo pluviometro e le date delle frane. Allora: eventi di
   pioggia, allerte (eventi sopra soglia), frane colte e mancate, allerte per
   frana colta. Un'ora mancante va lasciata vuota, mai scritta 0.
4. **Esporta.** La soglia come blocco YAML.

## L'API

| Indirizzo | Che cosa risponde |
|---|---|
| `GET /api/config` | ente, regione, regioni, tipi di frana, la regola, il link al bollettino |
| `POST /api/taratura` | `{regioni, mesi, tipi, percentile}` oppure `{eventi_ente: [[ore, mm], ...]}` → la soglia |
| `POST /api/costo` | `{alpha, beta, serie: "ora,mm\n...", frane: ["AAAA-MM-GG", ...]}` → il costo |
| `GET /api/esporta?alpha=&beta=` | la soglia in YAML |

## Dati

e-ITALICA v4 (Brunetti M.T. et al. 2024, doi:10.5281/zenodo.14204473),
CC BY 4.0, ridotto in `data/italica_v4_eventi.csv`. Bootstrap Italia è
servito dalla pagina stessa, senza CDN.
