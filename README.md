# AZAP - Arbeitszeitaufzeichnungsprogramm
Small command line utility to track work hours

## Installation

The runner scripts in [bin](./bin) expect a venv setup in a directory that starts with `./.venv`.
If you prefer a different location you have to adjust the scripts accordingly.

```bash
python -m venv .venv
souce .venv/bin/activate  # on Windows use: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

You can have two venv, one for linux and one for windows, since they have different structures which the scripts recognize.