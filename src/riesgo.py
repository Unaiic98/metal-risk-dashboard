import numpy as np
import pandas as pd

from src.data import descargar_precios

DIAS_HABILES_ANO = 252
METALES_CON_ROLL = ["Aluminio", "Acero"]


def calcular_rentabilidades(precios: pd.DataFrame) -> pd.DataFrame:
    """Rentabilidad logarítmica diaria de cada metal."""
    ratio = precios / precios.shift(1)
    rentabilidades = pd.DataFrame(np.log(ratio))
    # Quitar el primer día porque no tiene día anterior
    rentabilidades = rentabilidades.dropna()
    return rentabilidades


def dias_de_roll(fechas: pd.DatetimeIndex, metal: str) -> np.ndarray:
    """Devuelve True en los días en que Yahoo cambia de contrato en el futuro continuo.

    - Acero (HRC): el contrato deja de cotizar el día hábil anterior al último
      miércoles del mes, así que el cambio aparece el primer día de mercado
      a partir de ese miércoles.
    - Aluminio y cobre (ALI, HG): el contrato vence el antepenúltimo día hábil
      del mes, así que el cambio aparece el penúltimo día hábil.

    El último mes de los datos se ignora porque puede estar incompleto.
    """
    mes = fechas.to_period("M")
    es_roll = np.zeros(len(fechas), dtype=bool)

    for periodo in mes.unique()[:-1]:
        # Posiciones (0, 1, 2...) de los días de mercado de ese mes
        pos = np.where(mes == periodo)[0]

        if metal == "Acero":
            # Buscar el último miércoles del mes yendo hacia atrás desde el último día
            ultimo_miercoles = periodo.end_time.normalize()
            while ultimo_miercoles.day_of_week != 2:
                ultimo_miercoles -= pd.Timedelta(days=1)
            # Primer día de mercado a partir de ese miércoles (por si es festivo)
            despues = pos[fechas[pos] >= ultimo_miercoles]
            if len(despues) > 0:
                es_roll[despues[0]] = True
        elif len(pos) >= 3:
            # Penúltimo día de mercado del mes
            es_roll[pos[-2]] = True

    return es_roll


def quitar_rolls(rent: pd.DataFrame) -> pd.DataFrame:
    """Marca como "sin dato" (NaN) la rentabilidad de los días de cambio de contrato."""
    fechas = pd.DatetimeIndex(rent.index)
    # Copiar la tabla para no modificar la original
    rent = rent.copy()
    for metal in METALES_CON_ROLL:
        es_roll = dias_de_roll(fechas, metal)
        rent.loc[es_roll, metal] = np.nan
    return rent


def volatilidad_anual(rent: pd.DataFrame) -> pd.Series:
    """Volatilidad anualizada de cada metal (desviación típica diaria × √252)."""
    return rent.std() * np.sqrt(DIAS_HABILES_ANO)


def volatilidad_movil(rent: pd.DataFrame, ventana: int = 21) -> pd.DataFrame:
    """Volatilidad anualizada calculada sobre los últimos 'ventana' días, día a día."""
    vol = rent.rolling(window=ventana, min_periods=15).std()
    return vol * np.sqrt(DIAS_HABILES_ANO)


if __name__ == "__main__":
    precios = descargar_precios("2020-01-01")
    rent = calcular_rentabilidades(precios)

    # Comprobación: ¿los días de roll se mueven más que el resto?
    print("Movimiento medio |rentabilidad| (%): días de roll vs resto de días")
    fechas = pd.DatetimeIndex(rent.index)
    for metal in ["Cobre", "Aluminio", "Acero"]:
        es_roll = dias_de_roll(fechas, metal)
        en_roll = rent.loc[es_roll, metal].abs().mean() * 100
        resto = rent.loc[~es_roll, metal].abs().mean() * 100
        print(f"  {metal:9s} roll: {en_roll:.2f}%   resto: {resto:.2f}%")

    rent_limpia = quitar_rolls(rent)
    print("\nDías eliminados por metal:")
    print(rent_limpia.isna().sum())

    print("\nVolatilidad anual ANTES de quitar rolls (%):")
    print((volatilidad_anual(rent) * 100).round(1))
    print("\nVolatilidad anual DESPUÉS de quitar rolls (%):")
    print((volatilidad_anual(rent_limpia) * 100).round(1))

    vol_movil = volatilidad_movil(rent_limpia)
    print("\nVolatilidad móvil MÁXIMA (%):")
    print((vol_movil.max() * 100).round(1))
    print("\nFecha de la volatilidad móvil máxima:")
    print(vol_movil.idxmax())

    print("\nDías con |rentabilidad| > 8% tras limpiar:")
    for metal in ["Cobre", "Aluminio", "Acero"]:
        serie = rent_limpia[metal]
        print(f"\n{metal}:")
        print(serie[serie.abs() > 0.08])