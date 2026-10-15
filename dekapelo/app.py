"""
Główny punkt wejściowy uruchamiający aplikację dekapelo:
python -m dekapelo.app
lub:
uvicorn dekapelo.ui.app:app --host 127.0.0.1 --port 8000
"""

import uvicorn
from dekapelo.database.connection import init_db


def main():
    print("Inicjalizacja lokalnej bazy danych SQLite...")
    init_db()
    print("Uruchamianie dekapelo na http://127.0.0.1:8000 ...")
    uvicorn.run("dekapelo.ui.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
