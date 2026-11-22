# Riuso nella Pubblica Amministrazione

rainfall-thresholds è una libreria per le soglie di pioggia che innescano le
frane superficiali. Questa pagina è per un ente che vuole usarla: che cosa
trova pronto, che cosa resta a lui.

!!! warning "Una soglia superata non è un'allerta"
    Dice che la pioggia somiglia a quella che in passato ha innescato frane.
    L'allerta ufficiale è il
    [bollettino di criticità](https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento/)
    del Dipartimento della Protezione Civile e, sul territorio, la protezione
    civile regionale.

## Il banco di taratura

Una pagina pronta, in italiano, con
[Bootstrap Italia](https://italia.github.io/bootstrap-italia/) servito dalla
pagina stessa, senza CDN:

- si apre sul catalogo e-ITALICA già caricato, con la regione dell'ente
  selezionata;
- tara una soglia sulle frane scelte (regione, mese, tipo di frana) o su
  quelle dell'ente;
- la confronta con la soglia nazionale e mostra la pioggia che chiede da 1 a
  72 ore;
- ne misura il costo in falsi allarmi sulla serie oraria di un pluviometro
  dell'ente e sulle date delle sue frane;
- la esporta come blocco YAML.

```bash
TARATURA_ENTE="Comune di Gioia del Colle" TARATURA_REGIONE=Puglia docker compose up taratura
```

Le istruzioni sono in
[`app/README.md`](https://github.com/agent-engineering-studio/rainfall-thresholds/tree/main/app).

## Che cosa non fa

- **Non è un sistema di allerta**, e non legge pioggia dal vivo. Il
  monitoraggio con la pioggia di adesso è un altro progetto,
  [Limen](https://github.com/agent-engineering-studio/limen).
- **Non dice dove cadrà una frana.** Pendenza, suolo, vegetazione e umidità
  contano quanto la pioggia.
- **Non valida la soglia sulla pioggia radar o di modello.** Le soglie di
  e-ITALICA sono tarate sui pluviometri.

## Che cosa resta all'ente

- **I dati della sua pioggia.** Senza una serie oraria di pluviometro, il
  costo in falsi allarmi resta «non misurato»: la pagina non lo scrive mai
  come zero.
- **Le sue frane**, con la data, se vuole una soglia locale. Con meno di un
  centinaio di frane una soglia cambia molto con il campione, e la pagina lo
  dice.
- **La decisione.** Che soglia usare, e per che cosa, è una scelta tecnica
  dell'ente e del suo centro funzionale: la pagina dà i numeri, non la scelta.
- **La pubblicazione.** La pagina ascolta solo su `127.0.0.1`: per metterla sul
  sito va dietro il proxy dell'ente.

## La spiegazione, per tutti

[Try it](explainer.md) è una pagina interattiva, senza server: si sceglie una
regione, una durata e la pioggia caduta, e si vede dove cade rispetto alla
soglia italiana e alle frane del passato. Serve a spiegare che cos'è una
soglia, per esempio a una scuola o in un incontro pubblico. La pagina è in
inglese, come il resto della documentazione.

## Il Catalogo di Developers Italia

Il file [`publiccode.yml`](https://github.com/agent-engineering-studio/rainfall-thresholds/blob/main/publiccode.yml)
descrive il progetto per il
[Catalogo del software](https://developers.italia.it/it/software) di
Developers Italia, in italiano e in inglese, ed è controllato a ogni modifica
con `italia/publiccode-parser-action`. Il campo `codiceIPA` resta vuoto finché
il software non appartiene a una pubblica amministrazione: un ente che lo
adotta può chiederne l'inserimento nel Catalogo.

## Fonti

- e-ITALICA v4, Brunetti M.T. et al. (2024),
  [doi:10.5281/zenodo.14204473](https://doi.org/10.5281/zenodo.14204473),
  CC BY 4.0.
- Caine N. (1980); Brunetti M.T. et al. (2010); Peruccacci S. et al. (2012).
