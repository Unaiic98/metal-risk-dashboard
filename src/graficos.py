import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from src.backtest import VENTANA, var_fhs
from src.correlaciones import correlacion_movil
from src.data import descargar_precios
from src.riesgo import calcular_rentabilidades, quitar_rolls, volatilidad_movil

# Un color fijo por metal: el cobre siempre azul, en todos los gráficos
COLORES = {"Cobre": "#2a78d6", "Aluminio": "#eb6834", "Acero": "#1baf7a"}
GRIS = "#898781"  # para datos secundarios
ROJO_ALERTA = "#d03b3b"  # solo para avisos (excepciones del VaR), nunca para un metal
# Las parejas son algo distinto de los metales, así que llevan otros colores
COLORES_PAREJAS = {"Cobre-Aluminio": "#eda100", "Cobre-Acero": "#e87ba4", "Aluminio-Acero": "#008300"}


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


def grafico_backtest(rent: pd.Series, umbral_var: pd.Series, metal: str) -> Figure:
    """Rentabilidades diarias frente al VaR previsto, marcando los días en que se superó."""
    validos = rent.notna() & umbral_var.notna()
    real = rent[validos] * 100
    previsto = umbral_var[validos] * 100
    excepcion = real < previsto

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.scatter(real.index, real, s=8, color=GRIS, alpha=0.5, label="Rentabilidad diaria")
    ax.plot(previsto.index, previsto, color=COLORES[metal], linewidth=1.5, label="VaR 99% previsto (FHS)")
    ax.scatter(
        real.index[excepcion],
        real[excepcion],
        s=40,
        color=ROJO_ALERTA,
        marker="x",
        label=f"Excepción ({int(excepcion.sum())} días)",
    )

    ax.set_title(f"{metal}: backtesting del VaR al 99% a 1 día")
    ax.set_ylabel("Rentabilidad diaria (%)")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def grafico_correlacion_movil(movil: pd.DataFrame) -> Figure:
    """Gráfico de líneas de la correlación móvil de cada pareja de metales."""
    fig, ax = plt.subplots(figsize=(11, 5))
    for pareja in movil.columns:
        ax.plot(movil.index, movil[pareja], label=pareja, color=COLORES_PAREJAS[pareja], linewidth=1.5)
    ax.axhline(0, color=GRIS, linewidth=1)
    ax.set_ylim(-1, 1)
    ax.set_title("Correlación móvil entre metales (ventana de 3 meses)")
    ax.set_ylabel("Correlación")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    precios = descargar_precios("2020-01-01")
    rent = quitar_rolls(calcular_rentabilidades(precios))
    vol_movil = volatilidad_movil(rent)

    fig = grafico_volatilidad_movil(vol_movil)
    fig.savefig("volatilidad_movil.png", dpi=150)

    # Mismo periodo que la tabla del backtest: a partir del día 250
    inicio = rent.index[VENTANA]
    cobre = rent["Cobre"]
    fig_bt = grafico_backtest(cobre[inicio:], var_fhs(cobre)[inicio:], "Cobre")
    fig_bt.savefig("backtest_cobre.png", dpi=150)

    fig_corr = grafico_correlacion_movil(correlacion_movil(rent))
    fig_corr.savefig("correlacion_movil.png", dpi=150)

    plt.show()