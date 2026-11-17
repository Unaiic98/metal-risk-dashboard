import numpy as np
import pandas as pd

from src.data import descargar_precios
from src.riesgo import calcular_rentabilidades, quitar_rolls


def rentabilidades_a_plazo(rent: pd.Series, horizonte: int) -> np.ndarray:
    """Todas las rentabilidades logarítmicas a 'horizonte' días que han ocurrido en el pasado.

    Los días de cambio de contrato cuentan como 0: quien está cubierto con futuros
    pasa de un contrato al siguiente y ese salto no le supone ganancia ni pérdida.
    """
    a_plazo = rent.fillna(0).rolling(horizonte).sum().dropna()
    return a_plazo.to_numpy()


def simular_cobertura(
    rent: pd.Series,
    valor: float,
    horizonte: int = 21,
    cobertura: float = 0.0,
    vol_base_anual: float = 0.05,
    coste_pct: float = 0.001,
    simulaciones: int = 100_000,
    semilla: int = 42,
) -> np.ndarray:
    """Simula la ganancia o pérdida de una exposición al metal con una cobertura con futuros.

    - valor: dinero expuesto. Positivo si la empresa TIENE el metal (pierde si baja el precio);
      negativo si lo TIENE QUE COMPRAR (pierde si sube).
    - cobertura: fracción cubierta con futuros (0 = nada, 1 = todo, 1,5 = sobrecubierta).
    - vol_base_anual: volatilidad anual de la diferencia entre el precio real de la empresa
      y el futuro (riesgo de base).
    - coste_pct: coste de la cobertura (comisiones, horquilla) sobre lo cubierto.
    """
    generador = np.random.default_rng(semilla)

    # 1. Escenarios del futuro: meses reales del pasado elegidos al azar
    historia = rentabilidades_a_plazo(rent, horizonte)
    r_futuro = generador.choice(historia, simulaciones)

    # 2. Riesgo de base: el precio de la empresa no se mueve exactamente como el futuro
    vol_base = vol_base_anual * np.sqrt(horizonte / 252)
    r_fisico = r_futuro + generador.normal(0, vol_base, simulaciones)

    # 3. Ganancia o pérdida de cada parte
    pyg_fisico = valor * (np.exp(r_fisico) - 1)
    pyg_futuros = -cobertura * valor * (np.exp(r_futuro) - 1)
    coste = cobertura * abs(valor) * coste_pct

    return pyg_fisico + pyg_futuros - coste


def resumen_riesgo(pyg: np.ndarray, confianza: float = 0.99) -> dict:
    """VaR, Expected Shortfall, desviación típica y resultado medio de una simulación."""
    umbral = np.quantile(pyg, 1 - confianza)
    return {
        "VaR": float(-umbral),
        "Exp_Shortfall": float(-pyg[pyg <= umbral].mean()),
        "desviacion": float(pyg.std()),
        "resultado_medio": float(pyg.mean()),
    }


def curva_cobertura(rent: pd.Series, valor: float, **parametros) -> pd.DataFrame:
    """VaR y resultado medio para coberturas del 0% al 150%, con los mismos escenarios."""
    filas = []
    for cobertura in np.arange(0, 1.51, 0.1):
        pyg = simular_cobertura(rent, valor, cobertura=cobertura, **parametros)
        filas.append({"cobertura_%": round(cobertura * 100), **resumen_riesgo(pyg)})
    return pd.DataFrame(filas).set_index("cobertura_%")


if __name__ == "__main__":
    VALOR = 1_000_000.0  # stock de 1 millón de USD de cada metal
    HORIZONTE = 21  # un mes hasta vender el stock

    precios = descargar_precios("2020-01-01")
    rent = quitar_rolls(calcular_rentabilidades(precios))

    print(f"Stock de {VALOR:,.0f} USD durante {HORIZONTE} días. Riesgo al 99%.\n")
    for metal in ["Cobre", "Aluminio", "Acero"]:
        print(f"--- {metal} ---")
        filas = {}
        for cobertura in [0.0, 0.5, 1.0]:
            pyg = simular_cobertura(rent[metal], VALOR, HORIZONTE, cobertura)
            filas[f"{cobertura:.0%} cubierto"] = resumen_riesgo(pyg)
        print(pd.DataFrame(filas).round(0).to_string())
        print()

    print("Cobre: VaR según el % cubierto (base del 5% anual)")
    print(curva_cobertura(rent["Cobre"], VALOR, horizonte=HORIZONTE)["VaR"].round(0).to_string())