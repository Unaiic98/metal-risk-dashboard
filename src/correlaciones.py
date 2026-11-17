import numpy as np
import pandas as pd

from src.data import descargar_precios
from src.riesgo import calcular_rentabilidades, quitar_rolls

PAREJAS = [("Cobre", "Aluminio"), ("Cobre", "Acero"), ("Aluminio", "Acero")]


def matriz_correlaciones(rent: pd.DataFrame) -> pd.DataFrame:
    """Correlación de cada metal con cada otro (de -1 a 1)."""
    return rent.corr()


def correlacion_movil(rent: pd.DataFrame, ventana: int = 63) -> pd.DataFrame:
    """Correlación de cada pareja de metales en los últimos 'ventana' días (63 ≈ 3 meses)."""
    resultado = {}
    for metal_a, metal_b in PAREJAS:
        movil = rent[metal_a].rolling(ventana, min_periods=50).corr(rent[metal_b])
        resultado[f"{metal_a}-{metal_b}"] = movil
    return pd.DataFrame(resultado)


def efecto_diversificacion(rent: pd.DataFrame, posiciones: dict[str, float], confianza: float = 0.99) -> dict:
    """Compara el VaR histórico de la cartera completa con la suma de los VaR de cada metal.

    Si los metales no se mueven siempre a la vez, las pérdidas de uno se compensan en parte
    con otro, y el VaR de la cartera es MENOR que la suma de los VaR individuales.
    """
    # Solo días en que hay dato fiable de todos los metales (se pierden los días de roll)
    datos = rent[list(posiciones)].dropna()
    # Ganancia o pérdida en dinero de cada metal cada día
    pyg = (pd.DataFrame(np.exp(datos)) - 1) * pd.Series(posiciones)
    pyg_cartera = pyg.sum(axis=1)

    var_individuales = -pyg.quantile(1 - confianza)
    suma = float(var_individuales.sum())
    var_cartera = float(-pyg_cartera.quantile(1 - confianza))
    return {
        "suma_de_VaR_individuales": round(suma),
        "VaR_de_la_cartera": round(var_cartera),
        "reduccion_%": round(100 * (1 - var_cartera / suma), 1),
    }


if __name__ == "__main__":
    precios = descargar_precios("2020-01-01")
    rent = quitar_rolls(calcular_rentabilidades(precios))

    print("Matriz de correlaciones (enero 2020 - hoy):")
    print(matriz_correlaciones(rent).round(2))

    movil = correlacion_movil(rent)
    print("\nCorrelación móvil a 3 meses: mínima, máxima y actual")
    resumen = pd.DataFrame({"mínima": movil.min(), "máxima": movil.max(), "actual": movil.iloc[-1]})
    print(resumen.round(2))
    print("\nFecha de la correlación máxima:")
    print(movil.idxmax())

    posiciones = {"Cobre": 1_000_000.0, "Aluminio": 1_000_000.0, "Acero": 1_000_000.0}
    print("\nVaR histórico al 99% a 1 día de una cartera con 1 millón de USD en cada metal:")
    for clave, valor in efecto_diversificacion(rent, posiciones).items():
        print(f"  {clave}: {valor:,}")