import numpy as np
import pandas as pd

from src.data import descargar_precios

DIAS_HABILES_ANO = 252


def calcular_rentabilidades(precios: pd.DataFrame) -> pd.DataFrame:
    """Rentabilidad logarítmica diaria de cada metal."""
    ratio = precios / precios.shift(1)
    rentabilidades = pd.DataFrame(np.log(ratio))
    # Quitar el primer día porque no tiene día anterior
    rentabilidades = rentabilidades.dropna()
    return rentabilidades


def quitar_rolls_acero(rent: pd.DataFrame) -> pd.DataFrame:
    """Elimina la rentabilidad del acero el último miércoles de cada mes.

    Ese día Yahoo cambia de contrato en HRC=F, y el salto de precio
    no es un movimiento real del mercado.
    """
    fechas = pd.DatetimeIndex(rent.index)
    # 1. ¿Es miércoles? (lunes=0, martes=1, miércoles=2...)
    es_miercoles = fechas.day_of_week == 2
    # 2. ¿Es la última semana del mes? Si dentro de 7 días ya es otro mes, sí
    ultima_semana = (fechas + pd.Timedelta(days=7)).month != fechas.month
    # 3. Último miércoles = las dos condiciones a la vez
    es_roll = es_miercoles & ultima_semana
    # 4. Copiar la tabla y marcar esos días del acero como "sin dato"
    rent = rent.copy()
    rent.loc[es_roll, "Acero"] = np.nan
    return rent


def volatilidad_anual(rent: pd.DataFrame) -> pd.Series:
    """Volatilidad anualizada de cada metal (desviación típica diaria × √252)."""
    return rent.std() * np.sqrt(DIAS_HABILES_ANO)


def volatilidad_movil(rent: pd.DataFrame, ventana: int = 21) -> pd.DataFrame:
    """Volatilidad anualizada calculada sobre los últimos 'ventana' días, día a día."""
    vol = rent.rolling(window=ventana, min_periods=15).std()
    return vol * np.sqrt(DIAS_HABILES_ANO)


if __name__ == "__main__":
    precios = descargar_precios("2018-01-01")
    rent = quitar_rolls_acero(calcular_rentabilidades(precios))

    print("Volatilidad anual (%):")
    print((volatilidad_anual(rent) * 100).round(1))

    vol_movil = volatilidad_movil(rent)
    print("\nVolatilidad móvil MÁXIMA (%):")
    print((vol_movil.max() * 100).round(1))
    print("\nFecha de la volatilidad móvil máxima:")
    print(vol_movil.idxmax())
    print("\nVolatilidad móvil HOY (%):")
    print((vol_movil.iloc[-1] * 100).round(1))