# Analiza medicinskih pojmova (NER)

Python aplikacija koja analizira uneseni tekst pomocu **neuronske mreze**
(transformer NER model) i pronalazi medicinske strucne pojmove:
**bolesti, simptome, terapije, dijagnostiku i anatomiju**. Definicije
pronadenih pojmova asinkrono se dohvacaju s Wikipedije, a rezultati se izvoze
u CSV ili PDF.

Projekt je nastao na kolegiju *Napredne tehnike programiranja*, a za kolegij
*Operativni sustavi* prosiren je isporukom u tri oblika: **Docker slika**,
**snap paket** i **Ubuntu Core uredaj (Raspberry Pi)**.

## Sadrzaj

- [Nacini rada](#nacini-rada)
- [Arhitektura](#arhitektura)
- [Brzo pokretanje](#brzo-pokretanje)
- [REST API](#rest-api)
- [Struktura projekta](#struktura-projekta)
- [Testiranje](#testiranje)
- [Tehnologije](#tehnologije-napredne-tehnike-programiranja)
- [Isporuka](#isporuka-operativni-sustavi)

## Nacini rada

Ista jezgra aplikacije dostupna je kroz tri sucelja, ovisno o okruzenju u
kojem se izvodi:

| Nacin rada | Naredba | Namjena |
|---|---|---|
| Graficko sucelje | `python main.py` | radna povrsina (Windows, Linux) |
| Terminal | `python main.py --cli "tekst"` | brza provjera i skripte |
| Web servis | `python main.py --web` | Docker, posluzitelj, Ubuntu Core |

Web nacin rada dodan je zato sto Tkinter sucelje ne moze raditi u kontejneru
bez X servera niti na Ubuntu Coreu, koji koristi Wayland, a Tk podrzava samo
X11. Detaljno obrazlozenje je u
[docs/UBUNTU-CORE.md](docs/UBUNTU-CORE.md#koji-se-nacin-rada-koristi-na-uredaju-i-zasto).

## Arhitektura

```
                        +---------------------------+
                        |         app/              |
                        |                           |
   sucelja  ----------> |  ner.py       neuronska   |
                        |  fetcher.py   asyncio     |
   gui.py    (Tkinter)  |  exporters.py CSV / PDF   |
   main.py   (--cli)    |  models.py    dataclass   |
   web.py    (aiohttp)  |  logger.py    dekorator   |
                        |  paths.py     putanje     |
                        +---------------------------+
                                    |
             +----------------------+----------------------+
             |                      |                      |
       Docker slika            snap paket            Ubuntu Core
       (web, gui)         (GUI, CLI, daemon)        (Raspberry Pi)
```

Jezgra aplikacije ne poznaje nacin isporuke. Sucelja i pakiranja dodaju se oko
nje, a jedina prilagodba koju je pakiranje zahtijevalo je
[`app/paths.py`](app/paths.py), koji odreduje zapisiv direktorij (u snapu je
`$SNAP` samo za citanje, a u kontejneru se koristi volumen `/data`).

## Brzo pokretanje

> Postupak instalacije svih potrebnih alata na Windowsima (Docker, WSL,
> snapcraft, Multipass) opisan je korak po korak u [docs/SETUP.md](docs/SETUP.md).

### Lokalno

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py                    # graficko sucelje
python main.py --web              # http://localhost:8080
python main.py --cli "The patient has pneumonia."
```

> Pri prvom pokretanju analize model (~500 MB) preuzima se s interneta i
> sprema u lokalnu predmemoriju. Sljedeca pokretanja rade odmah.

### Docker

```powershell
docker compose up --build
```

Aplikacija je na <http://localhost:8080>. Upute za graficko sucelje preko
X11, CLI profil i gradnju za arm64 nalaze se u [docs/DOCKER.md](docs/DOCKER.md).

### Snap

```bash
snapcraft pack
sudo snap install ./medical-lexicon_1.0.0_amd64.snap --dangerous

medical-lexicon                              # graficko sucelje
medical-lexicon.cli "The patient has pneumonia."
snap services medical-lexicon                # web servis na portu 8080
```

Detalji, ukljucujuci gradnju za arm64, su u [docs/SNAP.md](docs/SNAP.md).

### Ubuntu Core na Raspberry Pi-u

```bash
scp medical-lexicon_1.0.0_arm64.snap <korisnik>@<ip-uredaja>:~/
ssh <korisnik>@<ip-uredaja>
sudo snap install ~/medical-lexicon_1.0.0_arm64.snap --dangerous
```

Aplikacija je zatim dostupna na `http://<ip-uredaja>:8080`. Cjelovit postupak,
ukljucujuci izradu vlastitog Ubuntu Core imagea i kiosk prikaz na monitoru
uredaja, opisan je u [docs/UBUNTU-CORE.md](docs/UBUNTU-CORE.md).

## REST API

| Metoda | Putanja | Opis |
|---|---|---|
| `GET` | `/` | web sucelje |
| `GET` | `/healthz` | provjera rada (koristi je Docker healthcheck) |
| `GET` | `/api/info` | verzija, model, arhitektura i ime uredaja |
| `POST` | `/api/analyze` | analiza teksta, vraca pronadene pojmove |
| `POST` | `/api/export/csv` | izvoz u CSV (s definicijama) |
| `POST` | `/api/export/pdf` | izvoz u PDF (s definicijama) |

```bash
curl -X POST http://localhost:8080/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The patient has pneumonia and was given insulin therapy."}'
```

```json
{
  "count": 2,
  "elapsed_seconds": 1.84,
  "terms": [
    {
      "text": "pneumonia",
      "category": "disease",
      "score": 0.9312,
      "description": "Pneumonia is an inflammatory condition of the lung...",
      "source_url": "https://en.wikipedia.org/wiki/Pneumonia"
    }
  ]
}
```

## Struktura projekta

```
medical_lexicon/
├─ main.py                   # ulazna tocka (GUI, --cli, --web)
├─ requirements.txt
├─ app/
│  ├─ logger.py              # dekorator @log_exceptions -> log.txt
│  ├─ models.py              # MedicalTerm dataclass (+ doctestovi)
│  ├─ ner.py                 # neuronska mreza (NER analiza)
│  ├─ fetcher.py             # asinkrono dohvacanje opisa (asyncio)
│  ├─ exporters.py           # Exporter (ABC), CSVExporter, PDFExporter
│  ├─ protocols.py           # typing.Protocol (Analyzer, DescriptionFetcher)
│  ├─ paths.py               # zapisivi direktoriji (snap, kontejner, lokalno)
│  ├─ gui.py                 # Tkinter sucelje
│  ├─ web.py                 # aiohttp web servis i REST API
│  └─ webui/                 # HTML, CSS i JavaScript web sucelja
├─ tests/                    # unittest + doctest
├─ Dockerfile                # ciljevi: base, web, gui
├─ docker-compose.yml        # servisi: web, gui, cli, test
├─ snap/
│  ├─ snapcraft.yaml         # definicija snap paketa
│  ├─ hooks/configure        # snap set port / host / daemon
│  ├─ local/                 # pokretacke skripte
│  └─ gui/                   # ikona i desktop unos
├─ ubuntu-core/
│  ├─ medical-lexicon.json         # model assertion (headless servis)
│  ├─ medical-lexicon-kiosk.json   # model assertion (prikaz na monitoru)
│  └─ medical-lexicon-vm.json      # model assertion (vjezba u virtualnom stroju)
└─ docs/
   ├─ SETUP.md               # priprema alata na Windowsima, korak po korak
   ├─ DOCKER.md
   ├─ SNAP.md
   └─ UBUNTU-CORE.md
```

## Testiranje

Projekt sadrzi jedinicne testove (`unittest`) i doctestove. Testovi ne
ucitavaju neuronsku mrezu niti pristupaju internetu (koriste se lazni objekti),
pa se izvode u nekoliko sekundi.

```powershell
python -m unittest discover -s tests -t . -v
```

Isti testovi mogu se pokrenuti i unutar Docker kontejnera:

```powershell
docker compose --profile test run --rm test
```

Sto je pokriveno:

- `tests/test_models.py` - `MedicalTerm` (vrijednosti, formatiranje, stupci)
- `tests/test_logger.py` - dekorator `@log_exceptions` (sync i async, reraise)
- `tests/test_exporters.py` - `CSVExporter`, `PDFExporter`, apstraktni `Exporter`
- `tests/test_ner.py` - logika NER analize (mapiranje kategorija, prag, dedup)
- `tests/test_fetcher.py` - asinkrono dohvacanje (parsiranje, greske, skracivanje)
- `tests/test_paths.py` - odabir zapisivog direktorija (snap, kontejner, lokalno)
- `tests/test_web.py` - REST API, izvozi i obrada gresaka (aiohttp test klijent)
- `tests/test_doctests.py` - ukljucuje doctestove u `unittest` izvodenje

## Tehnologije (Napredne tehnike programiranja)

| Zahtjev | Implementacija |
|---|---|
| Neuronska mreza | `transformers` pipeline s modelom `Clinical-AI-Apollo/Medical-NER` (DeBERTa) ([app/ner.py](app/ner.py)) |
| Asinkrono dohvacanje (asyncio) | `asyncio` + `aiohttp`, opisi pojmova s Wikipedije, svi zahtjevi istovremeno ([app/fetcher.py](app/fetcher.py)) |
| Spremanje u CSV | `CSVExporter` ([app/exporters.py](app/exporters.py)) |
| Dekorator za logiranje iznimki | `@log_exceptions` pise u `log.txt`, radi za sync i async ([app/logger.py](app/logger.py)) |
| Sucelja: ABC + Protocol | apstraktna klasa `Exporter` (ABC) + `CSVExporter`, `PDFExporter` ([app/exporters.py](app/exporters.py)); strukturni tipovi `Analyzer`, `DescriptionFetcher` (`typing.Protocol`) ([app/protocols.py](app/protocols.py)) |
| Tkinter GUI | [app/gui.py](app/gui.py) |

## Isporuka (Operativni sustavi)

| Cjelina | Sadrzaj | Dokumentacija |
|---|---|---|
| Docker aplikacija | `Dockerfile` s ciljevima `web` i `gui`, `docker-compose.yml` s profilima za web servis, graficko sucelje, CLI i testove | [docs/DOCKER.md](docs/DOCKER.md) |
| Snap aplikacija | `snap/snapcraft.yaml` s tri naredbe (GUI, CLI, daemon), konfiguracijski hook i pokretacke skripte | [docs/SNAP.md](docs/SNAP.md) |
| Ubuntu Core i Raspberry Pi | model assertion za headless i kiosk izvedbu, postupak izrade i zapisivanja imagea, rad na uredaju | [docs/UBUNTU-CORE.md](docs/UBUNTU-CORE.md) |

## Napomene

- Model je treniran na engleskom jeziku pa najbolje radi s engleskim tekstom.
- **Definicije pojmova nalaze se samo u izvezenim CSV i PDF dokumentima**, a ne
  u sucelju (tablica prikazuje pojam, kategoriju i pouzdanost). Isto pravilo
  vrijedi za graficko i za web sucelje.
- Sve iznimke (npr. nedostupna mreza, neinstaliran `reportlab`) biljeze se u
  `log.txt` zahvaljujuci dekoratoru `@log_exceptions`. U snapu i kontejneru
  dnevnik se nalazi u zapisivom direktoriju opisanom u
  [app/paths.py](app/paths.py).
