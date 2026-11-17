import numpy as np
import pandas as pd

from src.data import descargar_precios


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
    es_miercoles = fechas.weekday == 2
    # 2. ¿Es la última semana del mes? Si dentro de 7 días ya es otro mes, sí
    ultima_semana = (fechas + pd.Timedelta(days=7)).month != fechas.month
    # 3. Último miércoles = las dos condiciones a la vez
    es_roll = es_miercoles & ultima_semana
    # 4. Copiar la tabla y marcar esos días del acero como "sin dato"
    rent = rent.copy()
    rent.loc[es_roll, "Acero"] = np.nan
    return rent


if __name__ == "__main__":
    precios = descargar_precios("2018-01-01")
    rent = calcular_rentabilidades(precios)
    rent_limpia = quitar_rolls_acero(rent)

    print("Días de roll eliminados en el acero:", rent_limpia["Acero"].isna().sum())

    print("\nDesviación típica diaria ANTES:")
    print(rent.std())
    print("\nDesviación típica diaria DESPUÉS:")
    print(rent_limpia.std())

    acero = rent_limpia["Acero"]
    saltos = acero[acero.abs() > 0.08]
    print(f"\nAcero: {len(saltos)} días con |rentabilidad| > 8% tras limpiar")
    print(saltos)