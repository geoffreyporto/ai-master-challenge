# Features Engineering

**Aqui 20 features** en un primer modelo de churn. Todas deben calcularse **antes de la fecha de corte `t0`**, idealmente sobre una ventana móvil de 90 días, para evitar leakage.

| **#** | **Feature** | **Fuente** | **Justificación** |
| --- | --- | --- | --- |
| 1 | `tenure_days` | Accounts | Fue la señal predictiva más estable en el cribado temporal: las cuentas que churnearon tenían menor antigüedad mediana. |
| 2 | `active_mrr` | Subscriptions | Es esencial para priorizar riesgo financiero, incluso si no es el predictor más fuerte de churn por logo. |
| 3 | `plan_tier` | Accounts / Subscriptions | Captura diferencias estructurales entre Basic, Pro y Enterprise. |
| 4 | `active_subscriptions` | Subscriptions | Mide complejidad/penetración de la relación comercial por cuenta. |
| 5 | `annual_share` | Subscriptions | Proporción de contratos anuales activos; refleja distinta oportunidad mecánica de churn frente a planes mensuales. |
| 6 | `auto_renew_share` | Subscriptions | Señal comercial relevante antes de la renovación. |
| 7 | `upgrade_share` | Subscriptions | Una expansión previa puede indicar valor percibido; debe medirse antes de `t0`. |
| 8 | `downgrade_share` | Subscriptions | Suele ser una señal temprana de contracción o posible churn, aunque debe validarse temporalmente. |
| 9 | `active_seats` | Subscriptions | Aproxima tamaño, adopción comercial y exposición de valor. |
| 10 | `usage_total_90d` | Feature usage | Volumen de uso reciente del producto. Conviene normalizarlo también por asiento activo. |
| 11 | `usage_trend_ratio_90d` | Feature usage | Relación entre uso de los últimos 45 días y los primeros 45 días de la ventana; detecta cambios de tendencia. |
| 12 | `days_since_last_usage` | Feature usage | Señal de inactividad reciente. Debe calcularse por cuenta con base en la última actividad observada. |
| 13 | `feature_breadth_90d` | Feature usage | Número de funcionalidades distintas utilizadas; aproxima profundidad de adopción. |
| 14 | `usage_duration_90d` | Feature usage | Tiempo total de uso; complementa los conteos de eventos. |
| 15 | `errors_per_100_uses_90d` | Feature usage | La tasa de errores es más comparable que el número bruto de errores. Fue una de las señales de uso más útiles en el cribado. |
| 16 | `beta_usage_share_90d` | Feature usage | Proporción de uso en funcionalidades beta; puede capturar exposición a inestabilidad o adopción avanzada. |
| 17 | `tickets_90d` | Support tickets | Volumen de fricción reciente con soporte. Es una señal predictiva, no una prueba de causalidad. |
| 18 | `escalation_rate_90d` | Support tickets | Proporción de tickets escalados; aproxima gravedad o complejidad de incidencias. |
| 19 | `response_time_p90_90d` | Support tickets | Percentil 90 del tiempo de primera respuesta; representa mala experiencia en la cola de servicio. |
| 20 | `satisfaction_missing_share_90d` | Support tickets | La falta de respuesta a encuestas de satisfacción puede ser una señal informativa; no se debe reemplazar por cero. |

## **Features contextuales que incluiría como controles**

Además de las 20 anteriores, mantendría estas variables como **controles de segmentación** y para evaluar estabilidad entre entornos:

- `industry`
- `country`
- `referral_source`
- `is_trial`
- `seats` declarado a nivel de cuenta
- `high_priority_ticket_share_90d`
- `resolution_time_mean_90d`
- `satisfaction_mean_90d`

No necesariamente todas mejorarán el score en un holdout futuro, pero ayudan a detectar si un modelo funciona de forma desigual por industria, canal, país o cohorte.

## **Tres features derivadas especialmente recomendadas**

Para una siguiente iteración, añadiría estas tres variables compuestas, porque suelen ser más accionables que los valores aislados:

Python

```
usage_per_active_seat_90d = usage_total_90d /max(active_seats,1)

support_friction_index = (
    zscore(tickets_90d)
    + zscore(escalation_rate_90d)
    + zscore(response_time_p90_90d)
    + zscore(high_priority_ticket_share_90d)
)

commercial_contraction_flag =int(
    downgrade_share >0 or auto_renew_share <1
)
```

## **Exclusiones obligatorias por leakage**

No incluiría como features predictivas:

- `churn_date`
- `reason_code`
- `refund_amount_usd`
- `feedback_text`
- `churn_event_id`
- Campos de `churn_events` que describen el evento una vez producido
- Cualquier dato registrado después de `t0`

## **Resultado del cribado inicial**

Hice un cribado temporal con snapshots mensuales por `account_id`, features de 90 días y churn en los 30 días posteriores. En el holdout más reciente, las señales con mayor importancia predictiva fueron:

1. `tenure_days`
2. `errors_per_100_uses_90d`
3. `usage_trend_ratio_90d`
4. `plan_tier`
5. `annual_share`
6. `active_seats`
7. `satisfaction_missing_share_90d`
8. `auto_renew_share`
9. `industry`

El desempeño prospectivo todavía es modesto —PR-AUC de **0,144** y ROC-AUC de **0,604**—, lo que refuerza que estas features son un **punto de partida**, no una lista definitiva. La mayor mejora probablemente vendrá de una definición más precisa de churn/renovación, normalización por cuenta activa y mejores features de cambio temporal, no simplemente de un modelo más complejo.