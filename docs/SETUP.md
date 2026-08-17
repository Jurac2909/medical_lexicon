# Priprema razvojnog okruzenja (Windows)

Popis alata koje treba instalirati i redoslijed kojim se postavljaju. Upute
pretpostavljaju Windows 11 i pocetak bez ijednog instaliranog alata.

Potrebno je oko **50 GB slobodnog prostora** (Docker slike, snapcraft gradnja
i virtualni stroj) te racun na Ubuntu One-u.

| Alat | Cemu sluzi | Odakle |
|---|---|---|
| Python 3.11+ | pokretanje aplikacije lokalno | <https://www.python.org/downloads/> |
| Git | dohvat i objava repozitorija | <https://git-scm.com/download/win> |
| Docker Desktop | izrada i pokretanje Docker slike | <https://www.docker.com/products/docker-desktop/> |
| WSL2 s Ubuntuom 24.04 | gradnja snap paketa (snapcraft) | ugraden u Windows |
| Multipass | Ubuntu Core u virtualnom stroju | <https://canonical.com/multipass/install> |
| VcXsrv | prikaz Tkinter prozora iz kontejnera | <https://sourceforge.net/projects/vcxsrv/> |
| Raspberry Pi Imager | zapisivanje Ubuntu Corea na SD karticu | <https://www.raspberrypi.com/software/> |

---

## Korak 0: racuni

1. Otvoriti Ubuntu One racun: <https://login.ubuntu.com>
   Isti racun koristi se za `snapcraft`, Launchpad i prvo pokretanje Ubuntu
   Corea.

2. Izraditi SSH kljuc (u PowerShellu):

```powershell
ssh-keygen -t ed25519
```

3. Sadrzaj datoteke `C:\Users\<korisnik>\.ssh\id_ed25519.pub` zalijepiti na
   <https://login.ubuntu.com/ssh-keys>.

> Bez ovog kljuca nije moguce prijaviti se na Ubuntu Core uredaj nakon prvog
> pokretanja.

4. Racun na GitHubu, za gradnju arm64 snapa preko GitHub Actions (korak 5).
   Repozitorij mora biti javan jer su arm64 posluzitelji besplatni samo za
   javne repozitorije.

---

## Korak 1: aplikacija lokalno

Provjera da aplikacija radi prije bilo kakvog pakiranja.

```powershell
git clone https://github.com/Jurac2909/medical_lexicon.git
cd medical_lexicon

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m unittest discover -s tests -t .   # svi testovi moraju proci
python main.py                              # graficko sucelje
python main.py --web                        # http://localhost:8080
```

Prvo pokretanje analize preuzima model (~500 MB).

---

## Korak 2: Docker Desktop

1. Preuzeti i instalirati Docker Desktop, zatim ponovno pokrenuti racunalo.
2. Pokrenuti Docker Desktop i pricekati da u donjem lijevom kutu pise
   `Engine running`.
3. Provjera u PowerShellu:

```powershell
docker --version
docker run hello-world
```

4. Gradnja i pokretanje aplikacije:

```powershell
cd medical_lexicon
docker compose up --build
```

Otvoriti <http://localhost:8080>. Zaustavljanje je `Ctrl+C`, pa
`docker compose down`.

---

## Korak 3: VcXsrv (Tkinter iz kontejnera)

1. Instalirati VcXsrv.
2. Pokrenuti **XLaunch** i odabrati:
   - `Multiple windows`, `Display number: 0`
   - `Start no client`
   - **oznaciti `Disable access control`**
3. Ako Windows vatrozid zatrazi dopustenje, odobriti pristup privatnim
   mrezama.
4. Pokretanje grafickog sucelja iz kontejnera:

```powershell
docker compose --profile gui up --build gui
```

---

## Korak 4: WSL2 i Ubuntu 24.04 (gradnja snapa)

Snap se moze graditi samo na Linuxu.

1. U PowerShellu **s administratorskim ovlastima**:

```powershell
wsl --install -d Ubuntu-24.04
```

2. Ponovno pokrenuti racunalo. Pri prvom pokretanju Ubuntua zadaje se
   korisnicko ime i lozinka.

3. Provjeriti radi li systemd (snapd bez njega ne radi):

```bash
systemctl is-system-running
```

Ako naredba javlja gresku, dodati u `/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

pa u PowerShellu pokrenuti `wsl --shutdown` i ponovno otvoriti Ubuntu.

4. Instalacija alata za gradnju:

```bash
sudo snap install snapcraft --classic
sudo snap install lxd
sudo lxd init --auto
sudo usermod -aG lxd "$USER"
```

Nakon zadnje naredbe treba zatvoriti i ponovno otvoriti Ubuntu terminal.

5. Projekt mora biti unutar Linux datotecnog sustava, ne na `/mnt/c`:

```bash
git clone https://github.com/Jurac2909/medical_lexicon.git ~/medical_lexicon
cd ~/medical_lexicon
snapcraft pack
```

Gradnja traje dugo (torch je velik). Ako LXD u WSL-u ne radi, alternativa je:

```bash
snapcraft pack --destructive-mode
```

6. Instalacija i provjera:

```bash
sudo snap install ./medical-lexicon_1.0.0_amd64.snap --dangerous

medical-lexicon.cli "The patient has pneumonia."
snap services medical-lexicon
curl http://localhost:8080/healthz
medical-lexicon          # graficko sucelje se prikazuje kroz WSLg
```

---

## Korak 5: arm64 snap za Raspberry Pi

Snap sadrzi torch, koji se instalira kao binarni paket za tocno odredenu
arhitekturu, pa se arm64 verzija ne moze izgraditi na amd64 racunalu.

Gradnju obavlja GitHub Actions na arm64 posluzitelju (besplatno za javne
repozitorije), prema radnom tijeku
[`.github/workflows/build-snap.yml`](../.github/workflows/build-snap.yml):

1. Na GitHubu otvoriti karticu **Actions** > **Build snap** > **Run workflow**.
2. Nakon zavrsetka (30 do 60 minuta) pri dnu stranice izvodenja preuzeti
   artefakt `medical-lexicon-arm64`.
3. Raspakirati zip; unutra je `medical-lexicon_1.0.0_arm64.snap`.

Ostali nacini gradnje (Launchpad, arm64 uredaj, arm64 virtualni stroj) te
njihova ogranicenja opisani su u
[SNAP.md](SNAP.md#gradnja-za-raspberry-pi-arm64).

---

## Korak 6: Ubuntu Core u virtualnom stroju (vjezba)

Prije rada s uredajem cijeli se postupak moze uvjezbati u virtualnom stroju s
Ubuntu Coreom, uz amd64 snap:

```powershell
multipass launch core24 --name core-test --memory 4G --disk 20G
multipass transfer medical-lexicon_1.0.0_amd64.snap core-test:/home/ubuntu/
multipass shell core-test
```

Postupak unutar virtualnog stroja, provjera rada bez `curl`-a (Ubuntu Core ga
nema) i varijanta s vlastitim imageom opisani su u
[UBUNTU-CORE.md](UBUNTU-CORE.md#vjezba-u-virtualnom-stroju-prije-rada-s-uredajem).

---

## Korak 7: Raspberry Pi

Kada uredaj bude dostupan:

1. Instalirati Raspberry Pi Imager.
2. Zapisati **Ubuntu Core 24 (64-bit)** na microSD karticu od najmanje 16 GB.
3. Dalje prema [UBUNTU-CORE.md](UBUNTU-CORE.md).

---

## Redoslijed i trajanje

| Korak | Traje otprilike | Moze li se raditi usporedno |
|---|---|---|
| 0. Racuni i SSH kljuc | 10 min | - |
| 1. Aplikacija lokalno | 15 min | - |
| 2. Docker Desktop | 30 min | da |
| 3. VcXsrv | 10 min | da |
| 4. WSL i snap gradnja | 1 do 2 h | da |
| 5. arm64 snap (GitHub Actions) | 30 do 60 min cekanja | pokrenuti sto ranije |
| 6. Ubuntu Core u VM-u | 30 min | da |
| 7. Raspberry Pi | 1 h | ne, treba uredaj |
