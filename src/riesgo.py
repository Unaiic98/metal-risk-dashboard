import numpy as np
import pandas as pd

from src.data import descargar_precios

def calcular_rentabilidades(precios :pd.DataFrame)-> pd.DataFrame:
    "Rentabilidad logaritmica diaria de cada metal"
    ratio = precios /precios.shift(1)
    rentabilidades = pd.DataFrame(np.log(ratio))
    #quitar el primer dia porque no tiene dia anterior
    rentabilidades = rentabilidades.dropna()
    return rentabilidades


if __name__ == "__main__":
    precios = descargar_precios("2018-01-01")
    rent = calcular_rentabilidades(precios)
    print(rent.tail())
    print()
    print(rent.describe())
    print("\nFecha del peor día:")
    print(rent.idxmin())
    print("\nFecha del mejor día:")
    print(rent.idxmax())
    print("\n% de días con rentabilidad exactamente 0:")
    print((rent == 0).mean())

