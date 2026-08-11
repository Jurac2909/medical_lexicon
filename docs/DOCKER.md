# Docker

Aplikacija se u Dockeru isporucuje kroz jedan `Dockerfile` s dva cilja
(build target):

| Cilj  | Sto pokrece | Kada se koristi |
|---|---|---|
| `web` | headless web servis na portu 8080 | zadani nacin rada, radi bez grafickog sustava |
| `gui` | izvorno Tkinter sucelje preko X11 | prikaz desktop aplikacije iz kontejnera |

Oba cilja dijele zajednicki sloj (`base`) s Pythonom i ovisnostima, pa se
slike grade brzo i zauzimaju manje prostora.

## Preduvjeti

- **Windows:** Docker Desktop (s WSL2 backendom)
- **Linux:** `docker` i `docker compose` dodatak
- Za `gui` cilj na Windowsima dodatno: [VcXsrv](https://sourceforge.net/projects/vcxsrv/)

## Zasto Ubuntu 24.04 kao osnovna slika

Slika se temelji na `ubuntu:24.04`, istoj distribuciji na kojoj se temelje
snap paket (`base: core24`) i Ubuntu Core 24 na Raspberry Pi-u. Aplikacija se
tako u sve tri isporuke izvodi nad istim skupom sistemskih biblioteka, sto
uklanja razlike u ponasanju izmedu razvojnog i ciljnog okruzenja.

Dodatno, `python3-tk` iz distribucijskog repozitorija daje ispravan tkinter,
sto sluzbena `python:3.12-slim` slika nema (njezin Python je preveden bez
`_tkinter` modula, pa instalacija paketa `python3-tk` ondje ne pomaze).

## Brzo pokretanje (web servis)

```powershell
docker compose up --build
```

Aplikacija je dostupna na <http://localhost:8080>.

Pri prvom pokretanju servis preuzima NER model (~500 MB) u imenovani volumen
`model-cache`, pa je prva analiza sporija. Model ostaje spremljen i sljedeca
pokretanja rade odmah (i bez interneta, osim dohvata definicija s Wikipedije).

Zaustavljanje:

```powershell
docker compose down          # zadrzava volumen s modelom
docker compose down -v       # brise i preuzeti model
```

## Provjera rada

```powershell
docker compose ps                    # status i healthcheck
docker compose logs -f web           # dnevnik servisa
curl http://localhost:8080/healthz   # {"status": "ok", ...}
```

Analiza preko REST API-ja:

```bash
curl -X POST http://localhost:8080/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The patient has pneumonia and was given insulin therapy."}'
```

PowerShell inacica:

```powershell
Invoke-RestMethod -Uri http://localhost:8080/api/analyze -Method Post `
  -ContentType "application/json" `
  -Body '{"text": "The patient has pneumonia and was given insulin therapy."}'
```

## Izvoz rezultata

CSV i PDF izvozi zapisuju se u direktorij `exports/` na hostu (povezan s
`/data/exports` u kontejneru), a istovremeno se nude i kao preuzimanje u
pregledniku.

> Na Linuxu se moze pojaviti greska zbog dozvola jer servis u kontejneru radi
> kao korisnik `medlex` (UID 10001). Rjesenje:
> `mkdir -p exports && chmod 777 exports`.

## Graficko sucelje preko X11

### Windows

1. Instalirati i pokrenuti **VcXsrv** (XLaunch) s opcijom
   **Disable access control**.
2. Pokrenuti kontejner:

```powershell
docker compose --profile gui up --build gui
```

Ako se prozor ne pojavi, provjeriti je li `DISPLAY` postavljen na
`host.docker.internal:0` (zadana vrijednost u `docker-compose.yml`) i
propusta li vatrozid Windowsa VcXsrv.

### Linux

```bash
xhost +local:docker
DISPLAY=$DISPLAY docker compose --profile gui up --build gui
```

Na Linuxu treba u `docker-compose.yml` odkomentirati i povezivanje X11
uticnice:

```yaml
- /tmp/.X11-unix:/tmp/.X11-unix
```

## Analiza u terminalu

```powershell
docker compose --profile cli run --rm cli --cli "The patient reports chest pain and fever."
```

## Jedinicni testovi u kontejneru

```powershell
docker compose --profile test run --rm test
```

Testovi ne ucitavaju neuronsku mrezu niti pristupaju internetu (koriste
lazne objekte), pa se izvode u nekoliko sekundi.

## Ugradnja modela u sliku (offline rad)

Ako kontejner mora raditi bez pristupa internetu, model se moze ugraditi u
samu sliku:

```powershell
docker compose build --build-arg PRELOAD_MODEL=true web
```

Slika time naraste za oko 500 MB, ali je odmah spremna za rad.

## Raspberry Pi (arm64)

Raspberry Pi ima ARM procesor, pa slika izgradena na obicnom racunalu (amd64)
na njemu ne radi. Sliku treba izgraditi za `linux/arm64`.

### 1. Gradnja

Na razvojnom racunalu, uz Docker Desktop (buildx je ukljucen):

```powershell
docker buildx build --platform linux/arm64 --target web -t medical-lexicon:web-arm64 --load .
docker buildx build --platform linux/arm64 --target gui -t medical-lexicon:gui-arm64 --load .
```

Alternativa je gradnja izravno na uredaju (`sudo docker build --target web -t medical-lexicon:web .`),
sto je jednostavnije, ali traje osjetno dulje.

### 2. Prijenos slike na uredaj

Bez registra, izravno preko SSH-a:

```bash
docker save medical-lexicon:web-arm64 | gzip | ssh <korisnik>@<ip-uredaja> "gunzip | sudo docker load"
```

Ili preko Docker Huba:

```bash
docker tag medical-lexicon:web-arm64 <korisnik>/medical-lexicon:web
docker push <korisnik>/medical-lexicon:web
# na uredaju:
sudo docker pull <korisnik>/medical-lexicon:web
```

### 3. Docker na Ubuntu Coreu

Ubuntu Core nema `apt`, pa se Docker instalira kao snap:

```bash
sudo snap install docker
sudo snap connect docker:home
snap connections docker
```

Dva ogranicenja koja vrijede samo na Ubuntu Coreu:

- Sve naredbe traze `sudo`, jer se na Ubuntu Coreu korisnik ne moze dodati u
  grupu `docker`.
- Docker vidi **samo kucni direktorij**. Datoteke poput `docker-compose.yml` i
  svi direktoriji koji se povezuju u kontejner moraju biti unutar `$HOME`.

### 4. Pokretanje web servisa na uredaju

```bash
sudo docker run -d --name medical-lexicon \
  -p 8080:8080 \
  -e MEDLEX_PRELOAD=1 \
  -v /home/<korisnik>/medlex-data:/data \
  --restart unless-stopped \
  medical-lexicon:web-arm64
```

Provjera:

```bash
sudo docker logs -f medical-lexicon
curl http://localhost:8080/api/info    # "machine": "aarch64"
```

### 5. Pokretanje Tkinter sucelja s uredaja

Kontejner s grafickim suceljem treba X server. Koji se koristi, ovisi o
sustavu na uredaju:

**Ubuntu Core (nema vlastiti X server)**

X11 radi preko mreze, pa se prozor moze prikazati na X serveru koji radi na
prijenosnom racunalu:

1. Na Windows racunalu pokrenuti **VcXsrv** s opcijom **Disable access
   control** i dopustiti mu pristup kroz vatrozid (TCP 6000).
2. Na uredaju pokrenuti kontejner s adresom racunala:

```bash
sudo docker run --rm -e DISPLAY=<ip-racunala>:0 medical-lexicon:gui-arm64
```

Aplikacija se izvodi na Raspberry Pi-u, a prozor se iscrtava na racunalu.

**Raspberry Pi OS ili Ubuntu Desktop (imaju lokalni X server)**

```bash
xhost +local:docker
sudo docker run --rm \
  -e DISPLAY=:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  medical-lexicon:gui-arm64
```

Prozor se prikazuje na monitoru spojenom na Raspberry Pi.

> Na Linuxu se uz `docker compose` moze koristiti i pripremljena nadogradnja
> koja povezuje X11 uticnicu:
> `docker compose -f docker-compose.yml -f docker-compose.linux.yml --profile gui up gui`

Model se na Pi-u ucitava sporije, a analiza kratkog teksta traje oko 2 do 5
sekundi. Za `gui` sliku treba racunati na oko 1,5 GB radne memorije, pa je
preporuka Pi s 4 GB ili vise.

## Konfiguracija

| Varijabla | Zadano | Znacenje |
|---|---|---|
| `MEDLEX_HOST` | `0.0.0.0` | adresa na koju se servis veze |
| `MEDLEX_PORT` | `8080` | port web servisa |
| `MEDLEX_DATA_DIR` | `/data` | zapisiv direktorij (dnevnik, izvozi) |
| `HF_HOME` | `/data/hf-cache` | predmemorija preuzetog modela |
| `MEDLEX_PRELOAD` | `1` (compose) | ucitavanje modela pri pokretanju |

## Velicina slike

Na `amd64` se `torch` instalira iz CPU-only indeksa
(`https://download.pytorch.org/whl/cpu`), cime se izbjegavaju CUDA paketi i
slika je oko 2 GB manja. Na `arm64` je sluzbeni PyPI paket ionako bez CUDA
podrske.

## Otklanjanje problema

| Problem | Uzrok i rjesenje |
|---|---|
| `Ports are not available: 8080` | port je zauzet; promijeniti mapiranje u `docker-compose.yml` (npr. `"8081:8080"`) |
| Prva analiza traje jako dugo | preuzima se model; pratiti `docker compose logs -f web` |
| `unhealthy` status | model se jos ucitava (healthcheck ima 90 s odgode) ili nema pristupa internetu |
| GUI se ne prikazuje | X server nije pokrenut ili `DISPLAY` nije ispravan |
| Nema definicija u izvozu | nema pristupa Wikipediji; detalji su u `log.txt` unutar volumena `/data` |
