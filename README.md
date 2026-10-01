# Malmö kommunfullmäktiges närvaro

Python-paket för att hämta information om Malmö kommunfullmäktiges ledamöter,
möten och protokoll, och sammanställa närvaro per möte och paragraf.

## Krav

- Python 3.10 eller senare
- Internetanslutning när data eller PDF-filer behöver hämtas

## Installation

Kör kommandona från projektets rotmapp, där `pyproject.toml` finns.

Skapa och aktivera en virtuell miljö i Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

I PowerShell aktiverar du miljön med:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Installera paketet och dess testberoende:

```bash
python -m pip install -e ".[test]"
```

## Kör programmet

Från projektroten, med den virtuella miljön aktiverad:

```bash
python -m malmo_council_attendance
```

Programmet hämtar eller läser cachad information om förtroendevalda och möten,
laddar ner protokoll-PDF:er som saknas lokalt, läser protokollen och sparar en
närvarotabell. Körningen skriver även statusmeddelanden till terminalen.

## Cache och resultat

Programmet skapar och använder filer under `data/`:

- `council.json`: cachad information om ledamöter och roller.
- `meeting_protocol_links.csv`: mötesdatum och protokollänkar.
- `pdfs/`: nedladdade mötesprotokoll. Befintliga PDF-filer hämtas inte igen.
- `reading_cache/`: cachade resultat från protokollstolkningen.
- `attendance.csv`: närvaroraderna som analysen producerar.
- `analysis_meetings.csv` och `analysis_summary.json`: mötesstatus och
  sammanfattning av analysurvalet.

Cacheinställningarna finns nära toppen av
`src/malmo_council_attendance/__main__.py`:

- `use_council_cache = True`: återanvänd grunddata. Sätt till `False` för att
  hämta om API-data och skriva om cachen.
- `use_meetings_cache = True`: återanvänd mötes- och protokollänkar. Sätt till
  `False` för att läsa mötessidan och leta upp protokollänkarna igen.
- `use_reading_cache = True`: återanvänd tolkade protokoll. Sätt till `False`
  när PDF-tolkningen har ändrats och protokollen ska läsas om.

PDF-filer som redan finns i `data/pdfs/` behålls och laddas inte ner igen.
Mappen `data/` är lokal programdata och är exkluderad från Git.

## Tester

Kör hela testsviten från projektroten:

```bash
python -m pytest -q
```

För en enskild testfil, till exempel:

```bash
python -m pytest tests/test_io.py -q
```