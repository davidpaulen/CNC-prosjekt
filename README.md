# CNC-prosjekt – Generering av G-kode frå bilete

## Om prosjektet

Dette prosjektet går ut på å ta eit bilete av ei pakning og gjere det om til G-kode som kan brukast til å kutte forma med ein CNC-maskin. Systemet er laga for ein Prusa MK3S med drag knife, der kniven følgjer konturen frå biletet.

Løysinga er delt opp i fleire steg: først blir det teke eit bilete med Raspberry Pi, deretter blir biletet behandla i Python for å finne konturar. Desse konturane blir gjort om til koordinatar i millimeter, før det blir generert G-kode som maskina kan køyre.

---

## Bruk av systemet

Programmet er delt opp i fleire delar som blir køyrde etter kvarandre.

Først blir det teke eit bilete av objektet som skal kuttast ved å køyre `take_picture.py`. Dette lagrar biletet i data-mappa.

Deretter blir `make_gcode.py` køyrt. Denne fila analyserer biletet, finn konturane og genererer G-kode.

Når G-koden er generert, kan han sendast til printeren med `send_gkode_til_usb.py`, og sjølve kutteprosessen blir starta med `start_cut.py`.

---

## Teknisk forklaring

### Biletebehandling

Biletet blir først gjort om til gråskala og filtrert for å redusere støy. Deretter blir det brukt terskling for å skilje objektet frå bakgrunnen. Etter dette blir konturane funne med OpenCV.

### Geometri og skalering

Konturane som blir funne i pixlar blir gjort om til millimeter basert på ein kalibreringsfaktor. I tillegg blir dei flytta slik at dei passar innanfor arbeidsområdet til printeren.

### Drag knife-kompensasjon

Sidan kniven ikkje står rett under rotasjonspunktet, må bana justerast. Dette blir gjort ved å legge inn små justeringar i hjørne slik at kuttet blir korrekt.

### Generering av G-kode

Basert på konturane blir det generert G-kode med absolutte koordinatar. Programmet tilpassar også hastigheit basert på om det er små eller store detaljar, og køyrer fleire rundar for å sikre gjennomkutt.

---

## Prosjektstruktur

Koden er delt opp slik at hovudfila `make_gcode.py` styrer flyten, medan dei ulike delane av programmet er delt opp i eigne modular for biletebehandling, geometri, G-kode og drag knife-logikk.

---

## Krav

Prosjektet krev Python 3 med bibliotek som OpenCV og NumPy. I tillegg trengst ein Raspberry Pi med kamera og ein printer med Klipper firmware.

---

## Vidare arbeid

Moglege forbetringar er betre kalibrering av skalering, enklare brukargrensesnitt og meir optimal generering av G-kode for kortare køyretid.

---

## Forfattar

David Paulen
CNC-prosjekt – Maskin- og energiteknologi
