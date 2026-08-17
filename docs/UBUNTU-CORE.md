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
snap get medical-lexicon
```

Ubuntu Core nema `curl`, pa se odgovor servisa provjerava iz preglednika.
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

Sve ostalo (instalacija snapa, rad servisa, `snap set`, dnevnici) ponasa se
jednako.

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
```

> Ubuntu Core ima namjerno minimalan sustav i **ne sadrzi `curl` ni `wget`**.
> Stanje servisa provjerava se gornjim `snap` naredbama, a odgovor servisa
> najlakse iz preglednika na drugom racunalu. Ako je provjera potrebna na
> samom uredaju, moguce je bez dodatnih alata:
>
> ```bash
> exec 3<>/dev/tcp/127.0.0.1/8080
> printf 'GET /api/info HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3
> cat <&3
> ```
>
> ili instalirati alat kao snap: `sudo snap install curl`.

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
sudo snap logs medical-lexicon -n 20
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
| Analiza vraca `No medical terms found` za ocito medicinski tekst | model nije potpuno preuzet pri prvom pokretanju (HF Hub ogranicava brzinu neprijavljenim zahtjevima), pa su tezine ucitane samo djelomicno. Analizu treba ponoviti kad se preuzimanje dovrsi. **Prije demonstracije obavezno pokrenuti jednu probnu analizu.** |
| `medical-lexicon` (GUI) ne radi na uredaju | uz nepostojanje X servera, graficka naredba iz snapa koristi `gnome` prosirenje koje trazi sadrzajni snap `gnome-46-2404`, a on nije dio Ubuntu Core modela; za Tkinter na uredaju koristi se `gui` Docker slika uz udaljeni X server |
