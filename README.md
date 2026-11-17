# Metal Risk Dashboard

Panel de riesgo de precio de metales industriales (cobre, aluminio y acero) en Python,
pensado para empresas que compran o venden metal y quieren medir y cubrir su exposición al precio.

![Volatilidad anualizada móvil](volatilidad_movil.png)

## Qué hace

- Descarga precios diarios de futuros desde 2020 (Yahoo Finance)
-  Calcula rentabilidades logarítmicas diarias
-  Detecta y excluye los días de cambio de contrato (*roll*) de los futuros continuos
-  Volatilidad anualizada histórica y móvil
-  Value at Risk (histórico, paramétrico y Monte Carlo)
-  Correlaciones entre metales
- Simulador de coberturas con futuros
-  Aplicación web en Streamlit



## Estructura

```
src/
├── data.py       # Descarga y limpieza de precios
├── riesgo.py     # Rentabilidades, detección de rolls y volatilidad
└── graficos.py   # Gráficos
```

## Cómo ejecutarlo

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m src.riesgo            # resultados en la terminal
python -m src.graficos          # gráfico de volatilidad
```

## Resultados (enero 2020 – noviembre 2026)

| Metal | Contrato | Volatilidad anual | Máximo de la volatilidad móvil (21 días) |
|---|---|---|---|
| Cobre | `HG=F` (USD/libra) | 27,2% | 101,9% (julio 2025, aranceles de EE. UU.) |
| Aluminio | `ALI=F` (USD/tonelada métrica) | 23,0% | 53,6% (marzo 2022) |
| Acero | `HRC=F` (USD/tonelada corta) | 12,9% | 48,7% (marzo 2022) |

## Datos y limitaciones

**Cambios de contrato (*rolls*).** Un futuro continuo empalma un contrato con el siguiente cuando el primero vence.
El salto de precio entre ambos aparece en la serie como si fuera una rentabilidad, pero no es un movimiento del mercado.

- **Acero:** según el [reglamento de CME](https://www.cmegroup.com/content/dam/cmegroup/rulebook/COMEX/9/920.pdf),
  el contrato deja de negociarse el día hábil anterior al último miércoles del mes.
  Desde 2020, **33 de los 34 movimientos diarios superiores al 8%** caen justo en el día de cambio de contrato
  (por ejemplo, el 30-03-2022 el precio pasó de 1.122 a 1.535 USD, un +37%, por el cambio de contrato).
  En los días de cambio, el movimiento medio es del 7,23%, frente al 0,47% del resto (15 veces mayor).
  Al excluirlos, la volatilidad anual medida pasa del **34,0% al 12,9%**.
- **Aluminio:** el [contrato](https://www.cmegroup.com/markets/metals/base/aluminum.contractSpecs.html) vence el
  antepenúltimo día hábil del mes. El efecto es menor (movimiento medio del 1,40% en días de cambio frente al 1,10%),
  pero se aplica la misma corrección por coherencia. La volatilidad pasa del 23,5% al 23,0%.
- **Cobre:** no se observa efecto de cambio de contrato (1,02% frente a 1,22%), así que no se corrige.

**Limitaciones conocidas.**

- Yahoo Finance no conserva los contratos ya vencidos, por lo que no es posible construir una serie
  ajustada contrato a contrato. Los días de cambio se excluyen en lugar de ajustarse.
- El aluminio y el acero de COMEX tienen poca liquidez, y el acero HRC se liquida con una media mensual de un índice.
  Ambos factores suavizan los precios diarios, por lo que **su riesgo puede estar infravalorado**.
- Los datos de 2018–2019 del aluminio presentan largos periodos sin movimiento de precio y se descartan:
  el análisis empieza en 2020.
- Los futuros de COMEX son una referencia estadounidense; en Europa la referencia habitual es la London Metal Exchange (LME).

**Los extremos del cobre son reales**, no errores de datos:

- 04-04-2025: −8,9%, tras los aranceles recíprocos de EE. UU. y la respuesta de China.
- 08-07-2025: +13,3%, tras el anuncio de un arancel del 50% al cobre.
- 31-07-2025: −22,3%, la mayor caída diaria registrada en COMEX, al excluirse el cobre refinado de ese arancel.

*Nota: los porcentajes de este apartado son variaciones de precio simples; internamente el análisis usa rentabilidades logarítmicas.*
