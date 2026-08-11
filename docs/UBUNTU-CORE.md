# Ubuntu Core na Raspberry Pi-u

Ubuntu Core je minimalna, transakcijska inacica Ubuntua namijenjena IoT
uredajima. Cijeli sustav sastoji se iskljucivo od snap paketa, nema `apt`-a
niti klasicnog datotecnog sustava za instalaciju programa, a korijenski
datotecni sustav je samo za citanje.

## Koji se nacin rada koristi na uredaju i zasto

Aplikacija na Ubuntu Coreu radi kao **web servis** (`medical-lexicon.web`), a
ne kao Tkinter prozor. Razlog je tehnicki:

- Ubuntu Core nema X11 posluzitelj. Grafika se prikazuje preko Waylanda
  (snap `ubuntu-frame`, temeljen na Miru).
- Tkinter, odnosno Tk 8.6, podrzava iskljucivo X11 i **nema Wayland backend**.
  Zato se Tkinter sucelje na Ubuntu Coreu ne moze prikazati bez dodatnog
  XWayland sloja, koji na Coreu nije dio podrzanog skupa paketa.

Zbog toga isti snap na Ubuntu Coreu pokrece web sucelje, koje se otvara:

- s drugog racunala u mrezi (pristup na `http://<ip-uredaja>:8080`), ili
- na monitoru spojenom na Pi, u kiosk nacinu rada, gdje `ubuntu-frame` i
  `wpe-webkit-mir-kiosk` prikazuju istu stranicu preko cijelog zaslona.

Ovo je ujedno razlog zasto je aplikacija dobila headless nacin rada: bez njega
projekt na Ubuntu Coreu uopce ne bi bio upotrebljiv.

## Preduvjeti

**Sklopovlje**

- Raspberry Pi 4 ili 5 (64-bit), preporuceno **4 GB RAM-a ili vise**
  (ucitavanje modela trazi oko 1,5 GB)
- microSD kartica od najmanje 16 GB (snap s torchem je velik)
- mrezni kabel ili Wi-Fi, te monitor i tipkovnica za prvu konfiguraciju
- za kiosk nacin rada: monitor s HDMI ulazom

**Programska podrska (na razvojnom racunalu)**

- `medical-lexicon_1.0.0_arm64.snap` izgraden za arm64
  (vidi [SNAP.md](SNAP.md#gradnja-za-raspberry-pi-arm64))
- Ubuntu One racun s dodanim SSH javnim kljucem
  (<https://login.ubuntu.com/ssh-keys>)
- za vlastiti image: `snapcraft` i `ubuntu-image`

```bash
sudo snap install ubuntu-image --classic
```

---

## Vjezba u virtualnom stroju (prije rada s uredajem)

Cijeli postupak moze se uvjezbati bez Raspberry Pi-a, u virtualnom stroju s
Ubuntu Coreom. Razlikuje se samo arhitektura: u virtualnom stroju koristi se
**amd64** snap (`snapcraft pack`), a na uredaju **arm64** snap.

### Brzi nacin: Multipass

Najjednostavniji put na Windowsima. Multipass ima gotovu Ubuntu Core 24 sliku.

```powershell
multipass launch core24 --name core-test --memory 4G --disk 20G
multipass transfer medical-lexicon_1.0.0_amd64.snap core-test:/home/ubuntu/
multipass shell core-test
```

Unutar virtualnog stroja:

```bash
sudo snap install /home/ubuntu/medical-lexicon_1.0.0_amd64.snap --dangerous

snap services medical-lexicon
sudo snap logs medical-lexicon -f
sudo snap set medical-lexicon port=8080
curl http://localhost:8080/api/info
```

Web sucelje s Windowsa se otvara preko adrese virtualnog stroja:

```powershell
multipass info core-test        # IPv4 adresa
```

Virtualnom stroju treba dati najmanje 4 GB memorije jer ucitavanje modela
trazi oko 1,5 GB.

### Potpuni nacin: vlastiti image i QEMU

Ovako se uvjezbava i potpisivanje modela te `ubuntu-image`, dakle cijeli put B.
Koristi se model [`medical-lexicon-vm.json`](../ubuntu-core/medical-lexicon-vm.json),
koji je jednak modelu za Raspberry Pi osim sto ima `pc` i `pc-kernel` umjesto
`pi` i `pi-kernel`, te arhitekturu `amd64`.

```bash
snap sign -k moj-kljuc ubuntu-core/medical-lexicon-vm.json > ubuntu-core/medical-lexicon-vm.model

ubuntu-image snap --allow-snapd-kernel-mismatch \
  ubuntu-core/medical-lexicon-vm.model \
  --snap medical-lexicon_1.0.0_amd64.snap
```

Dobiveni `pc.img` pokrece se u QEMU-u (Ubuntu Core na amd64 trazi UEFI):

```bash
sudo apt install qemu-system-x86 ovmf
cp /usr/share/OVMF/OVMF_VARS.fd .

qemu-system-x86_64 -smp 2 -m 4096 -machine q35 -enable-kvm \
  -drive file=/usr/share/OVMF/OVMF_CODE.fd,if=pflash,format=raw,unit=0,readonly=on \
  -drive file=OVMF_VARS.fd,if=pflash,format=raw,unit=1 \
  -drive file=pc.img,format=raw,if=virtio \
  -netdev user,id=net0,hostfwd=tcp::8080-:8080,hostfwd=tcp::8022-:22 \
  -device virtio-net-pci,netdev=net0
```

Web sucelje je zatim na `http://localhost:8080`, a SSH na portu 8022.

### Sto se u virtualnom stroju ne moze provjeriti

- Ponasanje na arm64 arhitekturi i stvarna brzina analize na Raspberry Pi-u.
- Pi gadget, particioniranje SD kartice i pokretanje na stvarnom sklopovlju.
- Kiosk prikaz preko HDMI izlaza.

Sve ostalo (instalacija snapa, servis, `snap set`, dnevnici, prijenos s USB
sticka) ponasa se jednako.

---

## Put A: sluzbeni image i rucna instalacija snapa

Najbrzi put do radnog uredaja. Ne zahtijeva potpisivanje modela.

### A1. Zapisivanje sustava na karticu

1. Pokrenuti **Raspberry Pi Imager**.
2. Odabrati `Choose OS` > `Other general-purpose OS` > `Ubuntu` >
   **Ubuntu Core 24 (64-bit)**.
3. Odabrati karticu i zapisati sustav.

### A2. Prva konfiguracija

1. Umetnuti karticu u Pi, spojiti monitor, tipkovnicu i mrezu te ukljuciti
   uredaj.
2. Pratiti `console-conf` carobnjak: odabrati mrezu i unijeti Ubuntu One
   e-postu. Uredaj preuzima SSH kljuc s racuna.
3. Na kraju carobnjak ispisuje naredbu za prijavu, primjerice:

```bash
ssh <ubuntu-one-korisnik>@10.0.0.42
```

### A3. Prijenos i instalacija snapa

S razvojnog racunala:

```bash
scp medical-lexicon_1.0.0_arm64.snap <korisnik>@<ip-uredaja>:~/
```

Na uredaju:

```bash
sudo snap install ~/medical-lexicon_1.0.0_arm64.snap --dangerous
```

Instalacija velikog snapa traje nekoliko minuta jer se paket raspakirava na
microSD karticu.

### A4. Provjera i konfiguracija

```bash
snap services medical-lexicon               # servis mora biti active
sudo snap logs medical-lexicon -f           # pracenje pokretanja
snap get medical-lexicon                    # port, host, daemon

curl http://localhost:8080/healthz
curl http://localhost:8080/api/info         # "machine": "aarch64"
```

Promjena porta:

```bash
sudo snap set medical-lexicon port=8080
```

### A5. Pristup s drugog racunala

U pregledniku na racunalu u istoj mrezi otvoriti:

```
http://<ip-uredaja>:8080
```

Podnozje stranice prikazuje ime uredaja i arhitekturu (`aarch64`), sto je
najjednostavniji dokaz da analiza doista radi na Raspberry Pi-u.

---

## Put B: vlastiti Ubuntu Core image s ugradenom aplikacijom

Ovaj put daje image u kojem je aplikacija **vec instalirana pri prvom
pokretanju**. Koristi se model assertion iz
[`ubuntu-core/medical-lexicon.json`](../ubuntu-core/medical-lexicon.json).

### B1. Priprema modela

1. Dohvatiti svoj developer ID:

```bash
snapcraft whoami
```

2. U `medical-lexicon.json` zamijeniti `<vas developer account id>` i
   `<vas brand id>` dobivenim identifikatorom (u pravilu je isti za oba polja).

3. Osvjeziti vremensku oznaku:

```bash
date -Iseconds --utc
```

Rezultat upisati u polje `timestamp`.

4. Provjeriti da se naziv datoteke u polju `file` podudara s izgradenim
   snapom (`medical-lexicon_1.0.0_arm64.snap`).

### B2. Potpisivanje modela

```bash
snapcraft list-keys
snapcraft create-key moj-kljuc      # ako kljuc jos ne postoji
snapcraft register-key moj-kljuc

snap sign -k moj-kljuc ubuntu-core/medical-lexicon.json > ubuntu-core/medical-lexicon.model
```

### B3. Izrada imagea

```bash
ubuntu-image snap --allow-snapd-kernel-mismatch \
  ubuntu-core/medical-lexicon.model \
  --snap medical-lexicon_1.0.0_arm64.snap
```

Rezultat je datoteka `pi.img`.

### B4. Zapisivanje imagea

Linux:

```bash
sudo dd if=pi.img of=/dev/sdX bs=4M status=progress conv=fsync
```

Windows ili macOS: Raspberry Pi Imager (`Use custom`) ili balenaEtcher.

> Prije zapisivanja obavezno provjeriti naziv uredaja. Pogresan naziv znaci
> brisanje pogresnog diska.

### B5. Pokretanje

Nakon `console-conf` carobnjaka i prijave preko SSH-a, aplikacija je vec
instalirana:

```bash
snap list                       # medical-lexicon je na popisu
snap services medical-lexicon
curl http://localhost:8080/healthz
```

---

## Kiosk nacin rada: prikaz na monitoru Raspberry Pi-a

Ako aplikacija treba biti vidljiva na zaslonu spojenom na Pi, koristi se model
[`ubuntu-core/medical-lexicon-kiosk.json`](../ubuntu-core/medical-lexicon-kiosk.json),
koji uz aplikaciju ukljucuje i graficki sloj:

| Snap | Uloga |
|---|---|
| `ubuntu-frame` | Wayland kompozitor (prikaz preko cijelog zaslona) |
| `mesa-2404` | graficki upravljacki programi za core24 |
| `wpe-webkit-mir-kiosk` | preglednik koji prikazuje web sucelje |
| `core22`, `mesa-core22` | baza koju jos zahtijeva WPE WebKit |

Postupak potpisivanja i izrade imagea jednak je putu B, samo s drugom
datotekom modela:

```bash
snap sign -k moj-kljuc ubuntu-core/medical-lexicon-kiosk.json > ubuntu-core/medical-lexicon-kiosk.model

ubuntu-image snap --allow-snapd-kernel-mismatch \
  ubuntu-core/medical-lexicon-kiosk.model \
  --snap medical-lexicon_1.0.0_arm64.snap
```

Nakon pokretanja uredaja treba usmjeriti preglednik na lokalni servis:

```bash
sudo snap set wpe-webkit-mir-kiosk url=http://localhost:8080
sudo snap set ubuntu-frame daemon=true
sudo snap set wpe-webkit-mir-kiosk daemon=true

sudo snap restart wpe-webkit-mir-kiosk
```

Provjera grafickog sloja:

```bash
snap services
sudo journalctl -u snap.ubuntu-frame.daemon -f
sudo journalctl -u snap.wpe-webkit-mir-kiosk.daemon -f
```

---

## Rad bez mreze i bez SSH-a (prijenos USB stickom)

Ako se uredaju pristupa lokalno (monitor i tipkovnica), a datoteke se prenose
USB stickom, treba rijesiti tri stvari: prijavu na uredaj, prijenos snapa i
model koji se inace preuzima s interneta.

### 1. Prijava bez SSH-a

Ubuntu Core u zadanoj postavi nema lozinku za lokalnu prijavu: `console-conf`
preuzima javni SSH kljuc s Ubuntu One racuna i prijava ide preko SSH-a. Za
lokalnu prijavu koristi se **system-user assertion**, koja se s USB sticka
automatski ucitava pri pokretanju i stvara lokalnog korisnika s lozinkom.

> Ovo radi **samo s vlastitim imageom** (put B), jer assertion mora biti
> potpisan istim brand identifikatorom kojim je potpisan i model. Sluzbeni
> image iz Raspberry Pi Imagera potpisao je Canonical, pa za njega vlastitu
> system-user assertion nije moguce izraditi.

U modelu (`ubuntu-core/medical-lexicon.json`) treba izbaciti unos za
`console-conf` kako uredaj ne bi trazio prolazak kroz carobnjak koji zahtijeva
mrezu:

```json
        {
            "name": "console-conf",
            "type": "app",
            "default-channel": "24/stable",
            "id": "ASctKBEHzVt3f1pbZLoekCvcigRjtuqw"
        },
```

Zatim se izraduje `system-user.json`:

```json
{
    "type": "system-user",
    "authority-id": "<vas developer account id>",
    "brand-id": "<vas developer account id>",
    "series": ["16"],
    "models": ["medical-lexicon-pi-arm64"],
    "email": "<vasa-ubuntu-one-adresa>",
    "name": "Ime Prezime",
    "username": "student",
    "password": "<hash lozinke>",
    "since": "2026-08-11T10:00:00+00:00",
    "until": "2027-08-11T10:00:00+00:00"
}
```

Polje `models` mora sadrzavati naziv modela iz vlastite model assertion.
Hash lozinke izraduje se s:

```bash
sudo apt install whois          # zbog naredbe mkpasswd
mkpasswd -m sha512crypt -s
# ili bez dodatnih paketa:
openssl passwd -6
```

Potpisivanje (`--chain` ukljucuje i potrebne assertion datoteke racuna):

```bash
snap sign -k moj-kljuc system-user.json --chain > auto-import.assert
```

Datoteka `auto-import.assert` kopira se u **korijenski direktorij USB sticka**
(FAT32 ili ext4). Kada se stick umetne u uredaj, snapd ucitava assertion i
stvara korisnika, nakon cega je moguca lokalna prijava korisnickim imenom i
lozinkom. Stvaranje korisnika pri prvom pokretanju moze potrajati nekoliko
minuta.

### 2. Instalacija snapa s USB sticka

Ubuntu Core ne montira USB uredaje automatski, pa se to radi rucno:

```bash
lsblk                                   # pronalazenje uredaja, npr. sda1
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb

cp /mnt/usb/medical-lexicon_1.0.0_arm64.snap ~/
sudo snap install ~/medical-lexicon_1.0.0_arm64.snap --dangerous
```

> USB stick treba formatirati u exFAT ili ext4 ako je snap veci od 4 GB, jer
> FAT32 ne podrzava datoteke te velicine.

### 3. Prijenos modela (rad potpuno bez interneta)

Bez interneta servis ne moze preuzeti NER model, pa se predmemorija modela
priprema na racunalu i prenosi USB stickom.

Na racunalu, uz instalirane ovisnosti:

```powershell
$env:HF_HOME = "$PWD\hf-cache"
python -c "from transformers import AutoTokenizer, AutoModelForTokenClassification; m='Clinical-AI-Apollo/Medical-NER'; AutoTokenizer.from_pretrained(m); AutoModelForTokenClassification.from_pretrained(m)"
```

Ili iz vec pokrenutog Docker kontejnera:

```powershell
docker compose up -d web
docker compose cp web:/data/hf-cache ./hf-cache
```

Direktorij `hf-cache` (oko 500 MB) kopira se na USB stick, a na uredaju:

```bash
sudo mkdir -p /var/snap/medical-lexicon/common/hf-cache
sudo cp -r /mnt/usb/hf-cache/. /var/snap/medical-lexicon/common/hf-cache/

sudo snap set medical-lexicon offline=true
sudo snap restart medical-lexicon.web
```

Postavka `offline=true` sprjecava pokusaje provjere modela na internetu
(`HF_HUB_OFFLINE`), pa se servis pokrece odmah umjesto da ceka istek mreznog
zahtjeva.

Bez interneta analiza radi u cijelosti, ali **definicije pojmova s Wikipedije
ostaju prazne**. Izvoz u CSV i PDF i dalje radi.

### 4. Pregled sucelja bez druge mreze

Ako uredaj nije u mrezi s racunalom, web sucelje se pregledava na samom
uredaju, u kiosk nacinu rada (`ubuntu-frame` + `wpe-webkit-mir-kiosk`)
opisanom gore, na monitoru spojenom na Raspberry Pi.

## Ponasanje na Raspberry Pi-u

| Pojava | Objasnjenje |
|---|---|
| Prvo pokretanje servisa traje nekoliko minuta | preuzima se model (~500 MB) u `/var/snap/medical-lexicon/common/hf-cache` |
| Prva analiza traje dulje od sljedecih | model se ucitava u radnu memoriju |
| Analiza kratkog teksta na Pi 4 | oko 2 do 5 sekundi (bez grafickog ubrzanja) |
| Zauzece radne memorije | oko 1,5 GB tijekom analize |

Servis je namjerno postavljen tako da model ucitava odmah pri pokretanju
(`MEDLEX_PRELOAD=1`), pa je uredaj spreman prije prve demonstracije. Zahtjevi
se obraduju jedan po jedan jer visedretveno izvodenje modela na Pi-u nema
smisla.

Ako uredaj ima 2 GB RAM-a ili manje, ucitavanje modela moze zavrsiti
prekidom procesa (OOM). Ubuntu Core nema zamjensku memoriju (swap) pa u tom
slucaju treba koristiti uredaj s vise memorije.

## Otklanjanje problema

| Problem | Uzrok i rjesenje |
|---|---|
| `snap install` javlja gresku arhitekture | snap je izgraden za amd64; potreban je arm64 paket |
| Servis je u stanju `inactive` | `sudo snap start medical-lexicon.web` i provjera `sudo snap logs medical-lexicon -f` |
| Servis se stalno ponovno pokrece | najcesce nema mreze za preuzimanje modela; provjeriti `ping api.snapcraft.io` |
| Stranica nije dostupna izvana | servis slusa na `127.0.0.1`; postaviti `sudo snap set medical-lexicon host=0.0.0.0` |
| Nema mjesta na kartici | snap s torchem trazi nekoliko GB; koristiti vecu karticu |
| Prazan zaslon u kiosk nacinu | provjeriti `snap get wpe-webkit-mir-kiosk url` i radi li servis na tom portu |
| Nema definicija pojmova | uredaj nema pristup Wikipediji; analiza i dalje radi, ali bez opisa |
| `medical-lexicon` (GUI) ne radi na uredaju | uz nepostojanje X servera, graficka naredba iz snapa koristi `gnome` prosirenje koje trazi sadrzajni snap `gnome-46-2404`, a on nije dio Ubuntu Core modela; za Tkinter na uredaju koristi se `gui` Docker slika uz udaljeni X server |

## Odnos snapa i Dockera na Ubuntu Coreu

Ubuntu Core podrzava oba nacina isporuke, ali ne na jednak nacin.

**Snap je izvorni nacin isporuke.** Cijeli sustav sastoji se od snapova, paket
se automatski pokrece kao servis, konfigurira se s `snap set`, azurira
transakcijski i vraca na prethodnu verziju ako azuriranje ne uspije.

**Docker je podrzan, ali kao gost u sustavu.** Sam Docker instalira se kao
snap:

```bash
sudo snap install docker
sudo snap connect docker:home
```

Uz to dolaze ogranicenja kojih na obicnom Linuxu nema:

- sve naredbe traze `sudo`, jer se korisnik na Ubuntu Coreu ne moze dodati u
  grupu `docker`,
- Docker vidi samo kucni direktorij, pa se datoteke i direktoriji koji se
  povezuju u kontejner moraju nalaziti unutar `$HOME`,
- slika mora biti izgradena za `arm64`.

Postupak je opisan u [DOCKER.md](DOCKER.md#raspberry-pi-arm64).

Zbog toga ovaj projekt isporucuje aplikaciju u oba oblika: **snap paket** kao
izvorni nacin isporuke na uredaju (i nacin koji trazi zadatak), te **Docker
sliku** za razvoj i posluzitelje, koja se po potrebi moze pokrenuti i na
uredaju.

Za graficko sucelje vrijedi isto ogranicenje u oba slucaja: Ubuntu Core nema X
server, pa se Tkinter prozor moze prikazati samo na X serveru koji radi na
drugom racunalu (`DISPLAY=<ip-racunala>:0`, uz VcXsrv na Windowsima). Za
prikaz na monitoru spojenom na sam uredaj koristi se kiosk nacin rada opisan
gore.
