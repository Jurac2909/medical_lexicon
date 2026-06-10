# Analiza medicinskih pojmova (NER)

Python aplikacija koja analizira uneseni tekst pomocu **neuronske mreze**
(transformer NER model) i pronalazi medicinske strucne pojmove:
**bolesti, simptome, terapije, dijagnostiku i anatomiju**.

## Znacajke (tehnologije)

| Zahtjev | Implementacija |
|---|---|
| Neuronska mreza | `transformers` pipeline s modelom `Clinical-AI-Apollo/Medical-NER` (DeBERTa) ([app/ner.py](app/ner.py)) |
| Asinkrono dohvacanje (asyncio) | `asyncio` + `aiohttp`, opisi pojmova s Wikipedije, svi zahtjevi istovremeno ([app/fetcher.py](app/fetcher.py)) |
| Spremanje u CSV | `CSVExporter` ([app/exporters.py](app/exporters.py)) |
| Dekorator za logiranje iznimki | `@log_exceptions` pise u `log.txt`, radi za sync i async ([app/logger.py](app/logger.py)) |
| Sucelja: ABC + Protocol | apstraktna klasa `Exporter` (ABC) + `CSVExporter`, `PDFExporter` ([app/exporters.py](app/exporters.py)); strukturni tipovi `Analyzer`, `DescriptionFetcher` (`typing.Protocol`) ([app/protocols.py](app/protocols.py)) |
| Tkinter GUI | [app/gui.py](app/gui.py) |

## Instalacija

```powershell
# (preporuceno) virtualno okruzenje
python -m venv .venv
.venv\Scripts\Activate.ps1

# instalacija ovisnosti
pip install -r requirements.txt
```

> Pri **prvom** pokretanju analize model (~500 MB) se preuzima s interneta i
> sprema lokalno u cache. Sljedeca pokretanja su brza i rade offline.

## Pokretanje

```powershell
# Graficko sucelje (Tkinter)
python main.py

# Ili brza provjera iz terminala (bez GUI-ja)
python main.py --cli "The patient has pneumonia and was given insulin therapy."
```

## Kako se koristi

1. Unesite (ili zalijepite) tekst na engleskom u gornje polje.
2. Kliknite **Analyze** - neuronska mreza pronalazi pojmove, a definicije se
   asinkrono dohvacaju s Wikipedije.
3. Rezultati se prikazuju u tablici (pojam, kategorija, pouzdanost).
   **Definicije pojmova se NE prikazuju u grafickom sucelju** - vidljive su
   iskljucivo u izvezenim CSV i PDF dokumentima.
4. **CSV** ili **PDF** sprema rezultate u datoteku, zajedno s definicijama
   pojmova.

Sucelje aplikacije i oznake kategorija (disease, symptom, therapy,
diagnostics, anatomy) su na engleskom jeziku.

## Testiranje

Projekt sadrzi jedinicne testove (`unittest`) i doctestove. Testovi ne ucitavaju
neuronsku mrezu niti pristupaju internetu (koriste se lazni/mock objekti), pa se
izvode brzo.

```powershell
# Svi testovi (unit testovi + doctestovi)
python -m unittest discover -s tests -t . -v

# Samo doctestovi iz modula models.py
python -m doctest app/models.py -v
```

Sto je pokriveno:

- `tests/test_models.py` - `MedicalTerm` (vrijednosti, formatiranje, stupci)
- `tests/test_logger.py` - dekorator `@log_exceptions` (sync i async, reraise)
- `tests/test_exporters.py` - `CSVExporter`, `PDFExporter`, apstraktni `Exporter`
- `tests/test_ner.py` - logika NER analize (mapiranje kategorija, prag, dedup, sortiranje)
- `tests/test_fetcher.py` - asinkrono dohvacanje (parsiranje odgovora, greske, skracivanje)
- `tests/test_doctests.py` - ukljucuje doctestove u `unittest` izvodenje

## Struktura projekta

```
NTP_new/
├─ main.py              # ulazna tocka (GUI ili --cli)
├─ requirements.txt
├─ log.txt              # automatski generiran log iznimki
├─ app/
│  ├─ __init__.py
│  ├─ logger.py         # dekorator @log_exceptions -> log.txt
│  ├─ models.py         # MedicalTerm dataclass (+ doctestovi)
│  ├─ ner.py            # neuronska mreza (NER analiza)
│  ├─ fetcher.py        # asinkrono dohvacanje opisa (asyncio)
│  ├─ exporters.py      # Exporter (ABC), CSVExporter, PDFExporter
│  ├─ protocols.py      # typing.Protocol (Analyzer, DescriptionFetcher)
│  └─ gui.py            # Tkinter GUI
└─ tests/               # unittest + doctest
   ├─ test_models.py
   ├─ test_logger.py
   ├─ test_exporters.py
   ├─ test_ner.py
   ├─ test_fetcher.py
   └─ test_doctests.py
```

## Napomene

- Model je treniran na engleskom jeziku pa najbolje radi s engleskim tekstom.
- **Definicije pojmova nalaze se samo u izvezenim CSV i PDF dokumentima**, a ne
  u grafickom sucelju (tablica prikazuje samo pojam, kategoriju i pouzdanost).
- Sve iznimke (npr. nedostupna mreza, neinstaliran `reportlab`) biljeze se u
  `log.txt` zahvaljujuci dekoratoru `@log_exceptions`.
