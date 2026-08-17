# Analiza medicinskih pojmova (NER)

Python aplikacija koja u tekstu prepoznaje medicinske strucne pojmove
(**bolesti, simptome, terapije, dijagnostiku i anatomiju**) pomocu
**neuronske mreze** (transformer NER model). Definicije pronadenih pojmova
asinkrono se dohvacaju s Wikipedije, a rezultati se izvoze u CSV ili PDF.

Projekt je nastao na kolegiju *Napredne tehnike programiranja*, a za kolegij
*Operativni sustavi* prosiren je isporukom u obliku **Docker slike** i
**snap paketa**.

## Nacini rada

Ista jezgra aplikacije dostupna je kroz tri sucelja:

| Nacin rada | Naredba | Namjena |
|---|---|---|
| Graficko sucelje | `python main.py` | radna povrsina (Tkinter) |
| Terminal | `python main.py --cli "tekst"` | brza provjera |
| Web servis | `python main.py --web` | kontejner i posluzitelj |

Web nacin rada dodan je zato sto Tkinter treba X server, kojeg u kontejneru i
na posluzitelju nema.

## Pokretanje

**Lokalno**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

**Docker** - upute: [docs/DOCKER.md](docs/DOCKER.md)

```powershell
docker compose up --build          # web sucelje na http://localhost:8080
```

**Snap** - upute: [docs/SNAP.md](docs/SNAP.md)

```bash
snapcraft pack
sudo snap install ./medical-lexicon_1.0.0_amd64.snap --dangerous
```

> Pri prvom pokretanju analize model (~500 MB) preuzima se s interneta i
> sprema u lokalnu predmemoriju.

## REST API

| Metoda | Putanja | Opis |
|---|---|---|
| `GET` | `/` | web sucelje |
| `GET` | `/healthz` | provjera rada |
| `GET` | `/api/info` | verzija, model, arhitektura i ime uredaja |
| `POST` | `/api/analyze` | analiza teksta |
| `POST` | `/api/export/csv` | izvoz u CSV (s definicijama) |
| `POST` | `/api/export/pdf` | izvoz u PDF (s definicijama) |

## Testiranje

Jedinicni testovi (`unittest`) i doctestovi. Ne ucitavaju neuronsku mrezu niti
pristupaju internetu, pa se izvode u nekoliko sekundi.

```powershell
python -m unittest discover -s tests -t . -v
```

## Tehnologije (Napredne tehnike programiranja)

| Zahtjev | Implementacija |
|---|---|
| Neuronska mreza | `transformers` pipeline s modelom `Clinical-AI-Apollo/Medical-NER` (DeBERTa) ([app/ner.py](app/ner.py)) |
| Asinkrono dohvacanje (asyncio) | `asyncio` + `aiohttp`, opisi pojmova s Wikipedije ([app/fetcher.py](app/fetcher.py)) |
| Spremanje u CSV | `CSVExporter` ([app/exporters.py](app/exporters.py)) |
| Dekorator za logiranje iznimki | `@log_exceptions` pise u `log.txt`, radi za sync i async ([app/logger.py](app/logger.py)) |
| Sucelja: ABC + Protocol | `Exporter` (ABC) ([app/exporters.py](app/exporters.py)); `Analyzer`, `DescriptionFetcher` (`typing.Protocol`) ([app/protocols.py](app/protocols.py)) |
| Tkinter GUI | [app/gui.py](app/gui.py) |

## Isporuka (Operativni sustavi)

| Cjelina | Stanje | Dokumentacija |
|---|---|---|
| Docker aplikacija | izradeno i provjereno | [docs/DOCKER.md](docs/DOCKER.md) |
| Snap aplikacija | izradeno i provjereno (amd64 i arm64) | [docs/SNAP.md](docs/SNAP.md) |
| Ubuntu Core | pripremljeno, provjereno u virtualnom stroju | [docs/UBUNTU-CORE.md](docs/UBUNTU-CORE.md) |

Priprema razvojnog okruzenja na Windowsima opisana je u
[docs/SETUP.md](docs/SETUP.md).

## Napomene

- Model je treniran na engleskom jeziku pa najbolje radi s engleskim tekstom.
- **Definicije pojmova nalaze se samo u izvezenim CSV i PDF dokumentima**, a ne
  u sucelju, koje prikazuje pojam, kategoriju i pouzdanost.
- Iznimke se biljeze u `log.txt` zahvaljujuci dekoratoru `@log_exceptions`.
