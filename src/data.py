import yfinance as yf
import pandas as pd

TICKERS = {
    "Cobre": "HG=F",
    "Aluminio": "ALI=F",
    "Acero": "HRC=F",
}


def descargar_precios(inicio: str) -> pd.DataFrame:
    """Devuelve un DataFrame con fechas como índice y una columna por metal."""
    # 1. Pedir los datos a Yahoo
    datos = yf.download(["HG=F", "ALI=F", "HRC=F"], start=inicio, progress=False)
    # 2. Solo nos interesa el cierre
    datos = datos["Close"]
    # 3. Poner nombres legibles
    datos = datos.rename(columns={"HG=F": "Cobre", "ALI=F": "Aluminio", "HRC=F": "Acero"})
    # 4. Quitar días incompletos
    datos = datos.dropna()
    return datos


if __name__ == "__main__":
    precios = descargar_precios("2018-01-01")
    print(precios.tail())
    print(f"\nFilas: {len(precios)}  |  Desde {precios.index[0].date()} hasta {precios.index[-1].date()}")