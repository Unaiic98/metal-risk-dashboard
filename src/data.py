from datetime import date

import pandas as pd
import yfinance as yf

TICKERS = {
    "Cobre": "HG=F",
    "Aluminio": "ALI=F",
    "Acero": "HRC=F",
}


def descargar_precios(inicio: str) -> pd.DataFrame:
    """Devuelve un DataFrame con fechas como índice y una columna por metal."""
    # 1. Pedir los datos a Yahoo
    datos = yf.download(["HG=F", "ALI=F", "HRC=F"], start=inicio, progress=False)
    # Si Yahoo falla, unas veces devuelve None y otras una tabla vacía: se comprueban las dos
    if datos is None or datos.empty:
        raise ValueError("No se han podido descargar los precios de Yahoo Finance")
    # 2. Solo nos interesa el cierre
    datos = pd.DataFrame(datos["Close"])
    # 3. Poner nombres legibles
    datos = datos.rename(columns={"HG=F": "Cobre", "ALI=F": "Aluminio", "HRC=F": "Acero"})
    # 4. Quitar el día de hoy: el mercado aún no ha cerrado y el precio no es definitivo
    datos = pd.DataFrame(datos[datos.index < pd.Timestamp(date.today())])
    # 5. Quitar días incompletos
    datos = datos.dropna()
    # 6. Si un metal ha fallado, su columna estaba vacía y el dropna habrá borrado todo
    if datos.empty:
        raise ValueError("Falta al menos un metal en la descarga de Yahoo Finance")
    return datos


if __name__ == "__main__":
    precios = descargar_precios("2020-01-01")
    fechas = pd.DatetimeIndex(precios.index)
    print(precios.tail())
    print(f"\nFilas: {len(precios)}  |  Desde {fechas[0].date()} hasta {fechas[-1].date()}")