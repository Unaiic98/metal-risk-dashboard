import math
from statistics import NormalDist

import pandas as pd

from src.data import descargar_precios
from src.riesgo import calcular_rentabilidades, quitar_rolls

VENTANA = 250  
LAMBDA_EWMA = 0.94  


def var_historico_movil(rent: pd.Series, confianza: float = 0.99) -> pd.Series:
    """Para cada día, el umbral de VaR calculado SOLO con los 250 días anteriores."""
    umbral = rent.rolling(VENTANA, min_periods=200).quantile(1 - confianza)
    return umbral.shift(1)


def var_parametrico_movil(rent: pd.Series, confianza: float = 0.99) -> pd.Series:
    """Igual, pero suponiendo una normal con la media y la desviación de los 250 días anteriores."""
    z = NormalDist().inv_cdf(1 - confianza)
    media = rent.rolling(VENTANA, min_periods=200).mean()
    desviacion = rent.rolling(VENTANA, min_periods=200).std()
    return (media + z * desviacion).shift(1)


def volatilidad_ewma(rent: pd.Series) -> pd.Series:
    """Volatilidad EWMA prevista para cada día, usando solo datos hasta el día anterior."""
    varianza = (rent**2).ewm(alpha=1 - LAMBDA_EWMA, adjust=False).mean()
    volatilidad = (varianza**0.5).shift(1)
    return volatilidad.where(volatilidad > 0)


def var_ewma(rent: pd.Series, confianza: float = 0.99) -> pd.Series:
    """VaR normal con volatilidad EWMA: los días recientes pesan más que los antiguos."""
    z = NormalDist().inv_cdf(1 - confianza)
    return z * volatilidad_ewma(rent)


def var_fhs(rent: pd.Series, confianza: float = 0.99) -> pd.Series:
    """Simulación histórica filtrada: días pasados reescalados a la volatilidad de hoy.

    1. Se "filtra" cada día pasado dividiéndolo por la volatilidad que había entonces.
       Un -6% en un día de volatilidad 3% cuenta como "-2 veces la volatilidad".
    2. Se busca el 1% peor de esos días filtrados (los 250 anteriores).
    3. Se multiplica por la volatilidad prevista para hoy.
    """
    volatilidad = volatilidad_ewma(rent)
    filtradas = rent / volatilidad
    peor_filtrada = filtradas.rolling(VENTANA, min_periods=200).quantile(1 - confianza).shift(1)
    return peor_filtrada * volatilidad


def test_kupiec(excepciones: int, dias: int, confianza: float) -> float:
    """p-valor del test de Kupiec: ¿es creíble ver tantas excepciones si el VaR es correcto?

    Si sale menor que 0,05, el número de excepciones es demasiado alto (o bajo)
    para ser casualidad, y el modelo se rechaza.
    """
    p = 1 - confianza
    tasa = excepciones / dias
    log_modelo = (dias - excepciones) * math.log(1 - p) + excepciones * math.log(p)
    if excepciones == 0:
        log_real = 0.0
    else:
        log_real = (dias - excepciones) * math.log(1 - tasa) + excepciones * math.log(tasa)
    estadistico = -2 * (log_modelo - log_real)
    return math.erfc(math.sqrt(estadistico / 2))


def backtest(rent: pd.Series, umbral_var: pd.Series, confianza: float) -> dict:
    """Cuenta los días en que la rentabilidad real fue peor que el VaR previsto."""
    validos = rent.notna() & umbral_var.notna()
    real = rent[validos]
    previsto = umbral_var[validos]
    dias = len(real)
    excepciones = int((real < previsto).sum())
    return {
        "dias": dias,
        "excepciones": excepciones,
        "esperadas": round(dias * (1 - confianza), 1),
        "tasa_%": round(100 * excepciones / dias, 2),
        "p_valor": round(test_kupiec(excepciones, dias, confianza), 3),
    }


if __name__ == "__main__":
    CONFIANZA = 0.99
    precios = descargar_precios("2020-01-01")
    rent = quitar_rolls(calcular_rentabilidades(precios))

    metodos = {
        "Histórico": var_historico_movil,
        "Paramétrico": var_parametrico_movil,
        "EWMA": var_ewma,
        "FHS": var_fhs,
    }

    # Para comparar en igualdad de condiciones, todos empiezan el mismo día
    inicio = rent.index[VENTANA]

    filas = []
    for metal in ["Cobre", "Aluminio", "Acero"]:
        serie = rent[metal]
        for nombre, funcion in metodos.items():
            umbral = funcion(serie, CONFIANZA)
            resultado = backtest(serie[inicio:], umbral[inicio:], CONFIANZA)
            resultado["veredicto"] = "OK" if resultado["p_valor"] >= 0.05 else "RECHAZADO"
            filas.append({"metal": metal, "metodo": nombre, **resultado})

    tabla = pd.DataFrame(filas)
    print(f"Backtesting del VaR al {CONFIANZA:.0%} a 1 día (ventana de {VENTANA} días)\n")
    print(tabla.to_string(index=False))