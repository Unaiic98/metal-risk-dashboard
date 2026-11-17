# Metal Risk Dashboard

Panel de riesgo de precio de metales (cobre, aluminio y acero) en Python.

- Descarga de precios de futuros (Yahoo Finance)
- Rentabilidades logarítmicas diarias
- Volatilidad, VaR y correlaciones (en desarrollo)
- Simulador de coberturas (en desarrollo)

## Datos y limitaciones

- **Fuente:** futuros continuos de Yahoo Finance (`HG=F` cobre, `ALI=F` aluminio, `HRC=F` acero).
  Yahoo no conserva contratos vencidos, por lo que no es posible construir una serie ajustada por *roll*.
- **Acero (HRC):** el futuro continuo cambia de contrato el último miércoles de cada mes.
  36 de los 37 saltos diarios superiores al 8% caen ese día, así que se excluye la rentabilidad del acero en esas fechas.
  Esto reduce la volatilidad diaria medida del 1,98% al 0,79%.
- **Acero y aluminio:** tienen poca liquidez (25% y 17% de días con rentabilidad 0, frente al 0,5% del cobre)
  y el HRC se liquida por media mensual, por lo que su riesgo puede estar **infravalorado**.
- **Cobre:** los extremos (+12% el 08-07-2025, −25% el 31-07-2025) son reales: corresponden a los anuncios de aranceles de EE. UU.