from statistics import NormalDist

import numpy as np
import pandas as pd

from src.data import descargar_precios
from src.riesgo import calcular_rentabilidades, quitar_rolls


def perdida_en_dinero(rentabilidad: float, posicion: float) -> float:
    """Convierte una rentabilidad logarítmica en pérdida en dinero (positiva = se pierde)."""
    return -posicion * (np.exp(rentabilidad) - 1)


def var_historico(rent: pd.Series, posicion: float, confianza: float = 0.99) -> float:
    """VaR histórico: la pérdida que solo se superó el (1 - confianza)% de los días pasados."""
    peor_rentabilidad = float(rent.dropna().quantile(1 - confianza))
    return perdida_en_dinero(peor_rentabilidad, posicion)


def var_parametrico(rent: pd.Series, posicion: float, confianza: float = 0.99) -> float:
    """VaR paramétrico: supone que las rentabilidades siguen una distribución normal."""
    media = rent.mean()
    desviacion = rent.std()
    z = NormalDist().inv_cdf(1 - confianza)  # p. ej. -2,33 para el 99%
    peor_rentabilidad = media + z * desviacion
    return perdida_en_dinero(peor_rentabilidad, posicion)


def var_montecarlo(
    rent: pd.Series,
    posicion: float,
    confianza: float = 0.99,
    simulaciones: int = 100_000,
    semilla: int = 42,
) -> float:
    """VaR Monte Carlo: simula muchos días posibles y mira el peor (1 - confianza)%."""
    generador = np.random.default_rng(semilla)
    simuladas = generador.normal(rent.mean(), rent.std(), simulaciones)
    perdidas = -posicion * (np.exp(simuladas) - 1)
    return float(np.quantile(perdidas, confianza))


def expected_shortfall(rent: pd.Series, posicion: float, confianza: float = 0.99) -> float:
    """Expected Shortfall: la pérdida MEDIA de los días que superan el VaR histórico."""
    rent = rent.dropna()
    umbral = rent.quantile(1 - confianza)
    peores_dias = rent[rent <= umbral]
    return perdida_en_dinero(peores_dias.mean(), posicion)


if __name__ == "__main__":
    POSICION = 1_000_000  # 1 millón de USD invertidos en cada metal

    precios = descargar_precios("2020-01-01")
    rent = quitar_rolls(calcular_rentabilidades(precios))

    for confianza in [0.95, 0.99]:
        print(f"\nVaR a 1 día al {confianza:.0%} para una posición de {POSICION:,.0f} USD")
        print(f"{'Metal':10s}{'Histórico':>12s}{'Paramétrico':>14s}{'Monte Carlo':>14s}{'Exp. Shortfall':>16s}")
        for metal in ["Cobre", "Aluminio", "Acero"]:
            serie = rent[metal]
            print(
                f"{metal:10s}"
                f"{var_historico(serie, POSICION, confianza):>12,.0f}"
                f"{var_parametrico(serie, POSICION, confianza):>14,.0f}"
                f"{var_montecarlo(serie, POSICION, confianza):>14,.0f}"
                f"{expected_shortfall(serie, POSICION, confianza):>16,.0f}"
            )