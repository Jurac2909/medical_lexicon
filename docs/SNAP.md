# Snap paket

Snap se gradi iz [`snap/snapcraft.yaml`](../snap/snapcraft.yaml) i sadrzi tri
nacina rada iste aplikacije:

| Naredba | Opis | Sucelje |
|---|---|---|
| `medical-lexicon` | graficko sucelje (Tkinter) | X11 ili Wayland sjednica |
| `medical-lexicon.cli` | analiza teksta u terminalu | - |
| `medical-lexicon.web` | web servis kao daemon (port 8080) | preglednik |

Web servis je nacin rada koji se koristi na Ubuntu Coreu jer taj sustav nema
graficki podsustav za Tkinter.

## Preduvjeti

Snap se gradi na Linuxu. Na Windowsima se koristi WSL2 s Ubuntuom.

```powershell
wsl --install -d Ubuntu-24.04
```

Snapd u WSL2 zahtijeva systemd. U WSL-u treba provjeriti sadrzi li
`/etc/wsl.conf` sljedece, i ako ne, dodati ga te ponovno pokrenuti WSL
(`wsl --shutdown`):

```ini
[boot]
systemd=true
```

Zatim, u Ubuntu okruzenju:

```bash
sudo snap install snapcraft --classic
sudo snap install lxd
sudo lxd init --auto
sudo usermod -aG lxd "$USER"    # nakon toga se treba ponovno prijaviti
```

## Gradnja

```bash
cd medical_lexicon
snapcraft pack
```

Rezultat je `medical-lexicon_1.0.0_amd64.snap`.

Prva gradnja traje dugo (torch i transformers zajedno su nekoliko GB) i
zahtijeva oko 10 GB slobodnog prostora. Korisne opcije:

```bash
snapcraft pack --verbosity=verbose   # detaljan ispis
snapcraft clean                      # brisanje medurezultata
snapcraft pack --debug               # shell u okruzenju gradnje pri gresci
```

> Ako se projekt gradi iz WSL-a, izvorni kod treba biti unutar Linux datotecnog
> sustava (npr. `~/medical_lexicon`), a ne na `/mnt/c/...`. Gradnja preko
> `/mnt/c` je vrlo spora i zna izgubiti podatak o izvrsnosti skripti.
> Skripte i hook moraju biti izvrsni:
> `chmod +x snap/hooks/configure snap/local/*.sh`

## Instalacija

Paket nije potpisan u Snap Storeu, pa se instalira zastavicom `--dangerous`:

```bash
sudo snap install ./medical-lexicon_1.0.0_amd64.snap --dangerous
```

Ako neko sucelje nije dostupno u strogom nacinu rada, paket se moze instalirati
i u razvojnom nacinu (bez ogranicenja):

```bash
sudo snap install ./medical-lexicon_1.0.0_amd64.snap --dangerous --devmode
```

### Povezivanje sucelja

Lokalno instalirani snapovi ne povezuju sva sucelja automatski:

```bash
snap connections medical-lexicon      # pregled stanja
sudo snap connect medical-lexicon:home
sudo snap connect medical-lexicon:x11
```

## Pokretanje

```bash
# Graficko sucelje
medical-lexicon

# Analiza u terminalu
medical-lexicon.cli "The patient has pneumonia and was given insulin therapy."

# Web servis (pokrece se automatski nakon instalacije)
snap services medical-lexicon
curl http://localhost:8080/healthz
```

## Konfiguracija web servisa

```bash
sudo snap set medical-lexicon port=9000      # promjena porta
sudo snap set medical-lexicon host=127.0.0.1 # samo lokalni pristup
sudo snap set medical-lexicon daemon=false   # zaustavljanje servisa
sudo snap set medical-lexicon daemon=true    # ponovno pokretanje
sudo snap set medical-lexicon offline=true   # rad bez interneta (vec preuzet model)

snap get medical-lexicon                     # pregled postavki
```

| Postavka | Zadano | Znacenje |
|---|---|---|
| `port` | `8080` | port web servisa |
| `host` | `0.0.0.0` | adresa na koju se servis veze |
| `daemon` | `true` | pokretanje i zaustavljanje web servisa |
| `offline` | `false` | koristi samo vec preuzet model, bez pristupa internetu |

Postavke obraduje hook [`snap/hooks/configure`](../snap/hooks/configure), koji
provjerava vrijednosti i ponovno pokrece servis kad se promijene.

## Dnevnik i podaci

```bash
sudo snap logs medical-lexicon -f
sudo journalctl -u snap.medical-lexicon.web -f
```

| Nacin rada | Zapisiv direktorij |
|---|---|
| GUI i CLI | `~/snap/medical-lexicon/common` |
| Web daemon | `/var/snap/medical-lexicon/common` |

Ondje se nalaze `log.txt`, direktorij `exports/` s izvozima i `hf-cache/` s
preuzetim modelom.

## Gradnja za Raspberry Pi (arm64)

Paket sadrzi `torch`, koji se instalira kao binarni wheel za tocno odredenu
arhitekturu. Zbog toga **krizna izgradnja s amd64 na arm64 nije moguca** i
`snapcraft.yaml` je namjerno ne dopusta. Postoje cetiri nacina, poredana po
pouzdanosti:

**1. GitHub Actions na arm64 posluzitelju (nacin koristen u ovom projektu)**

Repozitorij sadrzi radni tijek
[`.github/workflows/build-snap.yml`](../.github/workflows/build-snap.yml) koji
paket gradi na GitHubovom `ubuntu-24.04-arm` posluzitelju. Za javne
repozitorije ti su posluzitelji besplatni.

Pokretanje: kartica **Actions** > **Build snap** > **Run workflow**. Nakon
gradnje se pri dnu stranice izvodenja preuzima artefakt
`medical-lexicon-arm64` (zip s `.snap` datotekom).

Ne trazi arm64 sklopovlje niti ovisi o Launchpadu.

**2. Gradnja na arm64 uredaju**

Na Pi se privremeno instalira Ubuntu Server 24.04 (64-bit) ili Raspberry Pi OS
64-bit, na njemu se paket izgradi, a zatim se SD kartica prepise Ubuntu Coreom.

```bash
sudo snap install snapcraft --classic
snapcraft pack --destructive-mode
```

**3. `snapcraft remote-build` (Launchpad)**

Gradnja se izvodi na Canonicalovim Launchpad posluziteljima:

```bash
snapcraft remote-build --launchpad-accept-public-upload
```

Zahtijeva Launchpad racun. Izvorni kod se pritom javno objavljuje na
Launchpadu, sto je za seminarski rad prihvatljivo.

> Ovaj nacin ovisi o dostupnosti Launchpada. Ako `git.launchpad.net` nije
> dostupan, gradnja pada s porukom `Could not push 'HEAD'` i
> `Failed to connect to git.launchpad.net port 443`. Stanje se provjerava na
> <https://status.canonical.com/>, a dostupnost izravno s:
>
> ```bash
> curl -sS -o /dev/null -m 10 -w "%{http_code}\n" https://git.launchpad.net/
> ```
>
> Zbog te ovisnosti prvi nacin (gradnja na samom uredaju) je pouzdaniji izbor
> kada uredaj postoji.

Prije pokretanja treba iz projekta maknuti prethodno izgradene `.snap`
datoteke, jer `remote-build` kopira cijeli direktorij i salje ga na
posluzitelj:

```bash
rm -f ./*.snap
rm -rf ~/.cache/snapcraft/remote-build
```

**3. GitHub Actions na arm64 posluzitelju (ne ovisi o Launchpadu)**

Repozitorij sadrzi radni tijek
[`.github/workflows/build-snap.yml`](../.github/workflows/build-snap.yml) koji
paket gradi na GitHubovom `ubuntu-24.04-arm` posluzitelju. Za javne
repozitorije ti su posluzitelji besplatni.

Pokretanje: kartica **Actions** > **Build snap** > **Run workflow**. Nakon
gradnje se pri dnu stranice izvodenja preuzima artefakt
`medical-lexicon-arm64` (zip s `.snap` datotekom).

Ovo je najpouzdaniji nacin kada nema pristupa arm64 sklopovlju, a Launchpad
nije dostupan.

**4. arm64 virtualni stroj**

Na racunalima s ARM procesorom (Apple Silicon) gradnja radi izravno u
Multipass ili UTM virtualnom stroju s Ubuntu 24.04.

Rezultat je u svim slucajevima `medical-lexicon_1.0.0_arm64.snap`.

> Ubuntu Core na uredaju **ne moze graditi snapove**: `snapcraft` je snap s
> klasicnim ogranicenjem (`classic`), a Ubuntu Core takve snapove ne dopusta.
> Gradnja na samom uredaju moguca je samo ako na njemu radi Ubuntu Server ili
> Raspberry Pi OS.

## Kako je paket slozen

- **Dio `medical-lexicon`** (plugin `python`) instalira ovisnosti iz
  `requirements.txt` u virtualno okruzenje unutar snapa te kopira izvorni kod u
  `$SNAP/app-src`. Python plugin sam po sebi ne kopira izvorni kod, nego samo
  ovisnosti, pa se to radi u `override-build`.
- **Sistemski paket `python3-tk`** dodaje tkinter, koji unutar snapa nije
  dostupan iz sustava. Skripta
  [`snap/local/common.sh`](../snap/local/common.sh) zato prosiruje `PYTHONPATH`,
  `LD_LIBRARY_PATH` te postavlja `TCL_LIBRARY` i `TK_LIBRARY`.
- **Zapisivanje** ide u `$SNAP_USER_COMMON` (korisnicke naredbe) odnosno
  `$SNAP_COMMON` (daemon), jer je `$SNAP` samo za citanje. Tu logiku sadrzi
  [`app/paths.py`](../app/paths.py).
- **Dio `launchers`** (plugin `dump`) kopira pokretacke skripte u `$SNAP/bin`.
- Iz paketa se pri pakiranju izbacuju torch testovi i zaglavlja (`prime:`
  filtri), sto stedi nekoliko stotina MB.

## Otklanjanje problema

| Problem | Uzrok i rjesenje |
|---|---|
| `bad interpreter: /bin/sh^M` | skripte imaju CRLF zavrsetke; repozitorij sadrzi `.gitattributes` koji to sprjecava, po potrebi `dos2unix snap/local/*.sh snap/hooks/configure` |
| `ModuleNotFoundError: No module named 'tkinter'` | nedostaje `python3-tk` u `stage-packages` ili `PYTHONPATH` ne pokazuje na `$SNAP/usr/lib/python3.12` |
| GUI se ne pokrece | sucelje `x11` ili `wayland` nije povezano; provjeriti `snap connections medical-lexicon` |
| Servis se stalno ponovno pokrece | `sudo snap logs medical-lexicon -f`; najcesce nema mreze za preuzimanje modela |
| `error: cannot perform operation: cannot install` | paket nije potpisan; koristiti `--dangerous` |
| Gradnja ostaje bez prostora | `snapcraft clean`, osloboditi prostor (potrebno je oko 10 GB) |
