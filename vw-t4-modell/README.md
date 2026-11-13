# VW T4 Kurzschnauze (1990–1995) zum 3D-Druck

Modell des VW T4 (Typ 70, Kurzschnauze, kurzer Radstand, Caravelle/Kombi mit
Schiebetür rechts). Die Proportionen sind an einer Seiten-, Front- und
Heckansicht des T4 Kurzschnauze (Baujahr 1990) abgeglichen.

![Mehrfarbig](vorschau_farbig.png)
![Einfarbig](vorschau_einfarbig.png)

## Dateien

| Datei | Inhalt |
|---|---|
| `vw_t4_1-30.stl` | **Empfohlen.** 1:30, 159 × 73 × 65 mm, ein Körper |
| `vw_t4_1-30_sockel.stl` | 1:30 mit Unterboden-Sockel, kommt ohne Stützen aus (von der Seite sieht man den Sockel) |
| `vw_t4_1-43.stl` | 1:43, 111 × 51 × 45 mm |
| `mehrfarbig_1-30/*.stl` | Teile je Farbe für das AMS (siehe unten) |
| `vw_t4.py` | Generator-Skript (Python, manifold3d) |
| `render_chromium.js` | Vorschau-Renderer (three.js in Chromium) |

## Was am Modell typisch T4 ist

- Kurze, um 37° geneigte Haube, die fast in derselben Linie in die flache
  Frontscheibe übergeht, mit kleinem Knick am Windlauf
- Um die Ecken gezogene Frontscheibe; die A-Säule sitzt weit hinten
- Seitenwände ab der Gürtellinie deutlich eingezogen, Dachkanten gerundet
- Heckklappe nach vorn geneigt, sehr große Heckscheibe
- Frontmaske mit Rechteck-Scheinwerfern (zweigeteilt) und Blinkern um die Ecke.
  Der Kühlergrill ist zweiteilig: oberer Grill mit Lamellen, Querstreb in
  Wagenfarbe, unterer Grill.
- Hohe, schwarze Stoßfänger, die bis an die Radläufe reichen. Hinten ist die
  Ladekante abgesenkt, die Heckklappe reicht dort bis unten.
- Heckleuchten an den Ecken über dem Stoßfänger (rot oben, orange unten)
- Schiebetür rechts mit schwarzer Abdeckung der Führungsschiene, Türfugen,
  seitliche Sicke, Regenrinnen
- Große, schwarze Außenspiegel, Scheibenwischer, Windlaufgitter, Türgriffe,
  Kennzeichen vorn und hinten
- Radläufe mit Lippe und schwarzer Radhaus-Auskleidung, Stahlfelgen mit
  Radkappe, Reifen mit Profil

Logos sind absichtlich nicht enthalten.

## Druck auf dem Bambu Lab P2S (Bambu Studio)

**Einfarbig (`vw_t4_1-30.stl`)**
- Ausrichtung: auf den Rädern lassen (so, wie die Datei geladen wird)
- Profil: 0,4-mm-Düse, *0.12 mm Fine* (oder *0.08 mm Extra Fine* für feinere Fugen)
- Wände 3, Füllung 10–15 % Gyroid
- Stützen: **Tree (auto), „nur auf der Druckplatte“**. Gestützt werden der
  flache Unterboden, die Stoßfänger-Unterseiten und die Spiegel. Wer keine
  Stützen will, nimmt `vw_t4_1-30_sockel.stl`.
- PLA Matte zeigt die Fugen und Fenster am besten

**Mehrfarbig mit AMS (`mehrfarbig_1-30/`)**
1. In Bambu Studio alle STL-Dateien aus dem Ordner **gleichzeitig** importieren.
2. Die Frage „als ein Objekt mit mehreren Teilen laden?“ mit **Ja** beantworten.
3. Den Teilen die Filamente zuweisen:

| Teil | Farbe |
|---|---|
| `karosserie` | Weiß oder Wagenfarbe |
| `schwarz` | Schwarz (Stoßfänger, Reifen, Grill, Spiegel, Radhäuser, Leisten) |
| `glas` | Schwarz oder Dunkelgrau |
| `silber` | Silber/Grau (Felgen, Kennzeichen) |
| `scheinwerfer` | Weiß/Natur |
| `orange` | Orange (Blinker) |
| `rot` | Rot (Rückleuchten) |

Mit nur 4 AMS-Slots: Glas schwarz drucken und die Scheinwerfer in Weiß,
dann reichen Weiß, Schwarz, Silber und Orange; die roten Leuchten werden dann
z. B. orange oder später bemalt. Das Teil `karosserie` hat 2 winzige
Netzfehler, die Bambu Studio beim Import selbst repariert.

## Anpassen

```bash
pip install manifold3d numpy
python3 vw_t4.py                    # 1:30 + Mehrfarben-Teile
python3 vw_t4.py --scale 25         # 1:25 (~191 mm lang)
python3 vw_t4.py --sockel           # mit Unterboden-Sockel
```

Alle Maße im Skript sind Originalmaße in mm. Die Karosserie entsteht aus
horizontalen Schnitten: Vorderkante, Hinterkante, Breite und Eckradien sind
jeweils als Profil über die Höhe hinterlegt (`XF_PTS`, `XR_PTS`, `W_PTS`, `RF_PTS`).
