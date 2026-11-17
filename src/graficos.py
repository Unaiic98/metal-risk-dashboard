import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from src.data import descargar_precios
from src.riesgo import calcular_rentabilidades, quitar_rolls_acero, volatilidad_movil

# Un color fijo por metal: el cobre siempre azul, en todos los gráficos
COLORES = {"Cobre": "#2a78d6", "Aluminio": "#eb6834", "Acero": "#1baf7a"}


def grafico_volatilidad_movil(vol_movil: pd.DataFrame) -> Figure:
    """Gráfico de líneas de la volatilidad anualizada móvil de cada metal."""
    fig, ax = plt.subplots(figsize=(11, 5))

    for metal in ["Cobre", "Aluminio", "Acero"]:
        ax.plot(
            vol_movil.index,
            vol_movil[metal] * 100,
            label=metal,
            color=COLORES[metal],
            linewidth=1.5,
        )

    ax.set_title("Volatilidad anualizada móvil (ventana de 21 días)")
    ax.set_ylabel("Volatilidad anual (%)")
    ax.grid(alpha=0.3)
    ax.legend()
    # Quitar los bordes de arriba y derecha: no aportan nada
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    precios = descargar_precios("2018-01-01")
    rent = quitar_rolls_acero(calcular_rentabilidades(precios))
    vol_movil = volatilidad_movil(rent)

    fig = grafico_volatilidad_movil(vol_movil)
    fig.savefig("volatilidad_movil.png", dpi=150)
    plt.show()