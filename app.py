import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.backtest import (
    VENTANA,
    backtest,
    var_ewma,
    var_fhs,
    var_historico_movil,
    var_parametrico_movil,
    volatilidad_ewma,
)
from src.coberturas import curva_cobertura, resumen_riesgo, simular_cobertura
from src.correlaciones import correlacion_movil, efecto_diversificacion, matriz_correlaciones
from src.data import descargar_precios
from src.riesgo import calcular_rentabilidades, quitar_rolls, volatilidad_anual, volatilidad_movil
from src.var import expected_shortfall, perdida_en_dinero, var_historico, var_parametrico

METALES = ["Cobre", "Aluminio", "Acero"]
COLORES = {"Cobre": "#2a78d6", "Aluminio": "#eb6834", "Acero": "#1baf7a"}
COLORES_PAREJAS = {"Cobre-Aluminio": "#eda100", "Cobre-Acero": "#e87ba4", "Aluminio-Acero": "#008300"}
GRIS = "#898781"
ROJO_ALERTA = "#d03b3b"

st.set_page_config(page_title="Riesgo de precio de metales", page_icon="📈", layout="wide")


# ---------------------------------------------------------------------------
# Datos (se guardan en caché 1 hora para no pedirlos a Yahoo en cada clic)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Descargando precios de Yahoo Finance...")
def cargar_rentabilidades() -> pd.DataFrame:
    precios = descargar_precios("2020-01-01")
    return quitar_rolls(calcular_rentabilidades(precios))


@st.cache_data(show_spinner="Simulando 100.000 escenarios...")
def cargar_curva(rent: pd.Series, valor: float, horizonte: int, vol_base: float, coste: float) -> pd.DataFrame:
    return curva_cobertura(rent, valor, horizonte=horizonte, vol_base_anual=vol_base, coste_pct=coste)


def riesgo_fhs_manana(rent: pd.Series, confianza: float) -> tuple[float, float]:
    """VaR y Expected Shortfall (como rentabilidades) para el próximo día de mercado, con FHS.

    Mismo método que var_fhs, pero usando todos los datos hasta hoy.
    """
    siguiente = pd.DatetimeIndex(rent.index)[-1] + pd.offsets.BDay(1)
    ampliada = pd.concat([rent, pd.Series([np.nan], index=[siguiente])])
    volatilidad = volatilidad_ewma(ampliada)
    # Los últimos 250 días "filtrados" (divididos por su volatilidad de entonces)
    filtradas = (rent / volatilidad[rent.index]).dropna().iloc[-VENTANA:]
    umbral = filtradas.quantile(1 - confianza)
    peores = filtradas[filtradas <= umbral]
    vol_manana = float(volatilidad.iloc[-1])
    return float(umbral) * vol_manana, float(peores.mean()) * vol_manana


def estilo(fig: go.Figure, titulo: str, eje_y: str) -> go.Figure:
    """Aspecto común de todos los gráficos."""
    fig.update_layout(
        title=titulo,
        yaxis_title=eje_y,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=60, b=10),
        height=420,
    )
    return fig


# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------
st.title("📈 Riesgo de precio de metales industriales")
st.markdown(
    "Volatilidad, Value at Risk, correlaciones y simulación de coberturas para **cobre, aluminio y acero**, "
    "con datos diarios de futuros de COMEX desde 2020. "
    "[Código y metodología en GitHub](https://github.com/Unaiic98/metal-risk-dashboard)"
)

try:
    rent = cargar_rentabilidades()
except ValueError as error:
    st.error(f"No se han podido cargar los datos: {error}. Vuelve a intentarlo en unos minutos.")
    st.stop()

ultimo_dia = pd.DatetimeIndex(rent.index)[-1].date()
st.caption(
    f"Datos hasta el {ultimo_dia:%d/%m/%Y} (último cierre). Fuente: Yahoo Finance. "
    "Proyecto educativo: no es una recomendación de inversión."
)

# ---------------------------------------------------------------------------
# Controles (barra lateral)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Parámetros")
    metal = st.selectbox("Metal", METALES)
    confianza = st.radio("Nivel de confianza", [0.95, 0.99], index=1, format_func=lambda c: f"{c:.0%}", horizontal=True)
    posicion = st.number_input("Exposición (USD)", min_value=10_000, max_value=100_000_000, value=1_000_000, step=100_000)
    st.caption("Estos parámetros afectan a todas las pestañas. Los del simulador están en la pestaña Coberturas.")

serie = rent[metal]

tab_resumen, tab_vol, tab_var, tab_corr, tab_cob, tab_metodo = st.tabs(
    ["Resumen", "Volatilidad", "VaR y backtesting", "Correlaciones", "Coberturas", "Metodología"]
)

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
with tab_resumen:
    vol = volatilidad_anual(rent)[metal]
    vol_reciente = volatilidad_movil(rent)[metal].iloc[-1]
    umbral_var, umbral_es = riesgo_fhs_manana(serie, confianza)
    var_manana = perdida_en_dinero(umbral_var, posicion)
    es_manana = perdida_en_dinero(umbral_es, posicion)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volatilidad anual (2020–hoy)", f"{vol:.1%}")
    c2.metric("Volatilidad último mes", f"{vol_reciente:.1%}", delta=f"{vol_reciente - vol:+.1%}", delta_color="inverse")
    c3.metric(f"VaR {confianza:.0%} a 1 día (próximo día)", f"{var_manana:,.0f} USD")
    c4.metric(f"Expected Shortfall {confianza:.0%} (próximo día)", f"{es_manana:,.0f} USD")
    st.markdown(
        f"Con **{posicion:,.0f} USD** en {metal.lower()}, en el próximo día de mercado la pérdida solo debería superar "
        f"**{var_manana:,.0f} USD** con una probabilidad del {1 - confianza:.0%}; si la supera, la pérdida media "
        f"esperada es de **{es_manana:,.0f} USD**. Ambas cifras usan la simulación histórica filtrada, el único método "
        "que aprueba el backtesting en los tres metales, y se adaptan a la volatilidad reciente."
    )
    if metal == "Acero":
        st.warning(
            "El futuro de acero HRC tiene poca liquidez y se liquida con una media mensual: "
            "su riesgo diario probablemente está infravalorado."
        )

# ---------------------------------------------------------------------------
# Volatilidad
# ---------------------------------------------------------------------------
with tab_vol:
    movil = volatilidad_movil(rent)
    fig = go.Figure()
    for m in METALES:
        fig.add_trace(go.Scatter(x=movil.index, y=movil[m] * 100, name=m, line=dict(color=COLORES[m], width=1.8)))
    st.plotly_chart(estilo(fig, "Volatilidad anualizada móvil (ventana de 21 días)", "Volatilidad anual (%)"), width="stretch")
    st.markdown(
        "Se ven el COVID (2020), la invasión de Ucrania (marzo de 2022) y los aranceles de EE. UU. al cobre (2025). "
        "Los bloques rectangulares aparecen porque un día extremo infla la volatilidad exactamente durante 21 días."
    )

# ---------------------------------------------------------------------------
# VaR y backtesting
# ---------------------------------------------------------------------------
with tab_var:
    st.subheader(f"VaR a 1 día al {confianza:.0%} con todos los datos (2020–hoy)")
    tabla_var = pd.DataFrame(
        {
            "Histórico": [var_historico(rent[m], posicion, confianza) for m in METALES],
            "Paramétrico (normal)": [var_parametrico(rent[m], posicion, confianza) for m in METALES],
            "Expected Shortfall": [expected_shortfall(rent[m], posicion, confianza) for m in METALES],
        },
        index=METALES,
    )
    st.dataframe(tabla_var.style.format("{:,.0f} USD"), width="stretch")

    st.subheader(f"Backtesting de {metal.lower()}: ¿cuántas veces se superó el VaR?")
    metodos = {
        "Histórico": var_historico_movil,
        "Paramétrico": var_parametrico_movil,
        "EWMA": var_ewma,
        "FHS": var_fhs,
    }
    inicio = rent.index[VENTANA]
    filas = []
    for nombre, funcion in metodos.items():
        resultado = backtest(serie[inicio:], funcion(serie, confianza)[inicio:], confianza)
        resultado["veredicto"] = "✅ OK" if resultado["p_valor"] >= 0.05 else "❌ Rechazado"
        filas.append({"método": nombre, **resultado})
    st.dataframe(pd.DataFrame(filas).set_index("método"), width="stretch")
    st.caption("Test de Kupiec: el modelo se rechaza si p < 0,05 (demasiadas o muy pocas excepciones para ser casualidad).")

    previsto = var_fhs(serie, confianza)[inicio:]
    real = serie[inicio:]
    validos = real.notna() & previsto.notna()
    excepcion = validos & (real < previsto)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=real.index, y=real * 100, mode="markers", name="Rentabilidad diaria", marker=dict(color=GRIS, size=4, opacity=0.5)))
    fig.add_trace(go.Scatter(x=previsto.index, y=previsto * 100, name=f"VaR {confianza:.0%} previsto (FHS)", line=dict(color=COLORES[metal], width=1.8)))
    fig.add_trace(
        go.Scatter(
            x=real.index[excepcion],
            y=real[excepcion] * 100,
            mode="markers",
            name=f"Excepción ({int(excepcion.sum())} días)",
            marker=dict(color=ROJO_ALERTA, size=9, symbol="x"),
        )
    )
    st.plotly_chart(estilo(fig, f"{metal}: rentabilidad diaria frente al VaR previsto", "Rentabilidad diaria (%)"), width="stretch")

# ---------------------------------------------------------------------------
# Correlaciones
# ---------------------------------------------------------------------------
with tab_corr:
    col_izq, col_der = st.columns([1, 2])
    with col_izq:
        st.subheader("Matriz de correlaciones")
        st.dataframe(matriz_correlaciones(rent)[METALES].loc[METALES].style.format("{:.2f}"), width="stretch")
        div = efecto_diversificacion(rent, {m: float(posicion) for m in METALES}, confianza)
        st.metric(
            f"VaR {confianza:.0%} de una cartera con {posicion:,.0f} USD en cada metal",
            f"{div['VaR_de_la_cartera']:,} USD",
            delta=f"-{div['reduccion_%']}% frente a la suma por separado",
            delta_color="off",
        )
    with col_der:
        corr = correlacion_movil(rent)
        fig = go.Figure()
        for pareja in corr.columns:
            fig.add_trace(go.Scatter(x=corr.index, y=corr[pareja], name=pareja, line=dict(color=COLORES_PAREJAS[pareja], width=1.8)))
        fig.update_yaxes(range=[-1, 1])
        st.plotly_chart(estilo(fig, "Correlación móvil (ventana de 3 meses)", "Correlación"), width="stretch")

# ---------------------------------------------------------------------------
# Coberturas
# ---------------------------------------------------------------------------
with tab_cob:
    # Los controles del simulador van aquí, al lado de los resultados que cambian
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        tipo = st.radio("La empresa...", ["Tiene stock (pierde si baja)", "Tiene que comprar (pierde si sube)"])
        horizonte = st.slider("Plazo (días de mercado)", 5, 63, 21)
    with col_b:
        cobertura = st.slider("% cubierto con futuros", 0, 150, 100, step=10)
        vol_base = st.slider("Riesgo de base (% anual)", 0.0, 20.0, 5.0, step=0.5)
    with col_c:
        coste = st.slider("Coste de la cobertura (% de lo cubierto)", 0.0, 1.0, 0.1, step=0.05)
    st.divider()

    valor = float(posicion) if tipo.startswith("Tiene stock") else -float(posicion)
    sin = simular_cobertura(serie, valor, horizonte, 0.0, vol_base / 100, coste / 100)
    con = simular_cobertura(serie, valor, horizonte, cobertura / 100, vol_base / 100, coste / 100)
    r_sin, r_con = resumen_riesgo(sin, confianza), resumen_riesgo(con, confianza)

    accion = "vende" if valor > 0 else "compra"
    st.markdown(
        f"La empresa {accion} futuros de {metal.lower()} por el **{cobertura}%** de su exposición "
        f"de **{posicion:,.0f} USD** durante **{horizonte} días**."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric(f"VaR {confianza:.0%} sin cubrir", f"{r_sin['VaR']:,.0f} USD")
    c2.metric(
        f"VaR {confianza:.0%} con cobertura",
        f"{r_con['VaR']:,.0f} USD",
        delta=f"{r_con['VaR'] / r_sin['VaR'] - 1:+.0%}",
        delta_color="inverse",
    )
    c3.metric("Resultado medio con cobertura", f"{r_con['resultado_medio']:,.0f} USD", delta=f"{r_con['resultado_medio'] - r_sin['resultado_medio']:+,.0f} USD frente a no cubrir")

    col_izq, col_der = st.columns(2)
    with col_izq:
        # Se agrupan los 100.000 escenarios en 80 intervalos aquí, para no enviarlos todos al navegador
        bordes = np.linspace(min(sin.min(), con.min()), max(sin.max(), con.max()), 81) / 1000
        centros = (bordes[:-1] + bordes[1:]) / 2
        fig = go.Figure()
        fig.add_trace(go.Bar(x=centros, y=np.histogram(sin / 1000, bordes)[0], name="Sin cubrir", marker_color=GRIS, opacity=0.6))
        fig.add_trace(go.Bar(x=centros, y=np.histogram(con / 1000, bordes)[0], name=f"{cobertura}% cubierto", marker_color=COLORES[metal], opacity=0.7))
        fig.update_layout(barmode="overlay", bargap=0, xaxis_title="Ganancia o pérdida (miles de USD)")
        fig = estilo(fig, "Distribución de resultados (100.000 escenarios)", "Escenarios")
        fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, width="stretch")
    with col_der:
        curva = cargar_curva(serie, valor, horizonte, vol_base / 100, coste / 100)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=curva.index, y=curva["VaR"] / 1000, name="VaR 99%", mode="lines+markers", line=dict(color=COLORES[metal], width=2)))
        fig.add_vline(x=cobertura, line_dash="dash", line_color=GRIS)
        fig.update_layout(xaxis_title="% cubierto con futuros", yaxis_rangemode="tozero")
        st.plotly_chart(estilo(fig, "VaR al 99% según el % cubierto", "VaR (miles de USD)"), width="stretch")

    st.info(
        "Cubrir el 100% no elimina el riesgo: queda el **riesgo de base** (el precio de la empresa no se mueve "
        "exactamente como el futuro) y el coste. Cubrir más del 100% vuelve a aumentar el riesgo. "
        "Y la cobertura no aumenta el beneficio esperado: renuncia a las subidas a cambio de no sufrir las caídas. "
        "El simulador no incluye las llamadas de margen de los futuros."
    )

# ---------------------------------------------------------------------------
# Metodología
# ---------------------------------------------------------------------------
with tab_metodo:
    st.markdown(
        """
**Datos.** Futuros continuos de COMEX en Yahoo Finance: cobre (`HG=F`, USD/libra), aluminio (`ALI=F`, USD/tonelada métrica)
y acero HRC (`HRC=F`, USD/tonelada corta), desde enero de 2020. Se usan rentabilidades logarítmicas diarias.

**Cambios de contrato.** El futuro continuo empalma un contrato con el siguiente al vencer, y ese salto aparecía como
rentabilidad. En el acero, 33 de los 34 movimientos diarios superiores al 8% caían en el día de cambio de contrato
(el contrato deja de negociarse el día hábil anterior al último miércoles del mes). Esos días se excluyen en el acero y el aluminio.

**VaR.** Se comparan cuatro métodos: histórico, paramétrico (normal), EWMA y simulación histórica filtrada (FHS).
Se validan con un backtesting sin información futura y el test de Kupiec. La FHS es el único que aprueba en los tres metales.

**Coberturas.** Monte Carlo con 100.000 escenarios: meses reales del pasado elegidos al azar más un riesgo de base simulado.

**Limitaciones.** Yahoo no conserva los contratos vencidos; el acero y el aluminio tienen poca liquidez y su riesgo puede
estar infravalorado; el riesgo de base es un supuesto; COMEX es una referencia estadounidense (en Europa se usa la LME).
"""
    )
