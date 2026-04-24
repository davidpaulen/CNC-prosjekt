# CNC-prosjekt – Automatisk generering av G-kode frå bilete

## 📌 Om prosjektet

Dette prosjektet tek eit bilete av ei pakning og konverterer det automatisk til G-kode som kan brukast til å kutte forma med ein CNC-maskin (Prusa MK3S med drag knife).

Systemet består av fleire delar:

* 📷 Kamera (Raspberry Pi) som tek bilete
* 🧠 Python-program som analyserer bilete
* ✂️ Generering av G-kode med drag knife-kompensasjon
* 🖨️ Sending av G-kode til printer via USB

---

## ⚙️ Korleis det fungerer

1. **Ta bilete**

```bash
python program/take_picture.py
```

2. **Generer G-kode**

```bash
python program/make_gcode.py
```

3. **Send til printer**

```bash
python program/send_gkode_til_usb.py
```

4. **Start kutt**

```bash
python program/start_cut.py
```

---

## 🧠 Teknisk forklaring

### Biletebehandling

* OpenCV blir brukt til:

  * Gråskala-konvertering
  * Blur
  * Terskling (Otsu)
  * Morfologi
* Konturar blir funne med `findContours`

### Geometri

* Pixel → mm konvertering
* Normalisering til printerens koordinatsystem
* Skalering og offset

### Drag knife-kompensasjon

* Kompenserer for at kniven heng bak rotasjonspunktet
* Lager små bogar i hjørne
* Hindrar feil kutt i skarpe vinklar

### G-kode

* G21 (mm)
* G90 (absolute)
* Feedrate tilpassa små og store detaljar
* 2 rundar per kontur for betre gjennomkutt

---

## 📁 Prosjektstruktur

```text
program/
│
├─ make_gcode.py
├─ make_gcode/
│  ├─ config.py
│  ├─ geometry.py
│  ├─ dragknife.py
│  ├─ gcode.py
│  ├─ image_processing.py
│  ├─ contours.py
│  └─ debug.py
│
├─ take_picture.py
├─ send_gkode_til_usb.py
├─ start_cut.py
└─ restart_klipper_service.py
```

---

## 📦 Krav

* Python 3.x
* OpenCV
* NumPy
* Raspberry Pi med kamera
* Klipper firmware

Installer avhengigheiter:

```bash
pip install opencv-python numpy
```

---

## ⚠️ Viktige parameterar

Finnast i:

```text
program/make_gcode/config.py
```

Eksempel:

* `KNIFE_OFFSET_MM` – viktig for korrekt kutt
* `MM_PER_PIXEL` – kalibrering
* `OFFSET_X / OFFSET_Y` – plassering på bed
* `SCALE_FACTOR` – størrelse

---

## 🔧 Vidare arbeid

* Automatisk kalibrering av scale
* GUI/web-interface
* Betre filtrering av konturar
* Støtte for fleire materialtypar
* Optimalisering av G-kode (kortare kjøretid)

---

## 👤 Forfattar

David Paulen
CNC-prosjekt – Maskin- og energiteknologi
