---
title: "MCTS en acción"
---

| Notebook | Colab |
|---------|:-----:|
| Notebook 03 — UCT y experimentos | <a href="https://colab.research.google.com/github/sonder-art/ia_p26/blob/main/clase/18_montecarlo_search/notebooks/03_uct_y_experimentos.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"></a> |

---

# 18.5 — MCTS en acción

> *"In theory, theory and practice are the same. In practice, they are not."* — Yogi Berra

---

Tenemos la teoría: MCTS con UCT construye un árbol selectivamente, usa rollouts para evaluar posiciones y converge al valor minimax cuando $M \to \infty$. Ahora veamos cómo funciona en la práctica. Usaremos Hex en dos escalas: 3×3 para verificar convergencia exacta, y 7×7 para medir rendimiento real.

---

## 1. Verificación: MCTS converge a minimax en Hex 3×3

El árbol completo de Hex 3×3 tiene $\sim 10^3$ nodos — minimax lo resuelve en milisegundos. Esto nos permite verificar que MCTS encuentra la misma respuesta.

![Convergencia de MCTS a minimax en Hex 3×3]({{ '/18_montecarlo_search/images/12_mcts_vs_minimax_3x3.png' | url }})

La figura muestra el valor estimado por MCTS para la mejor acción de la raíz, en función del número de iteraciones $M$. La línea punteada es el valor exacto de minimax. Observaciones:

- Con $M < 50$, la estimación es ruidosa — puede estar lejos del valor real
- Alrededor de $M = 200$, MCTS identifica correctamente la mejor acción
- Con $M > 500$, los valores convergen con precisión al valor minimax

Esto confirma experimentalmente el teorema de convergencia de §18.4: MCTS con UCT **es** minimax en el límite. La ventaja es que con un presupuesto limitado ($M = 200$ en vez de explorar los $\sim 10^3$ nodos), ya da la respuesta correcta.

---

## 2. Hex 7×7: el escenario real

En Hex 7×7, minimax exacto es imposible ($\sim 10^{20}$ estados). Aquí es donde MCTS muestra su valor. Comparemos tres agentes:

| Agente | Descripción |
|---|---|
| **Aleatorio** | Elige uniformemente al azar entre las acciones legales |
| **Alpha-beta + eval** | Alpha-beta con profundidad limitada (d=3) y una función de evaluación heurística basada en distancia al borde |
| **MCTS (UCT)** | MCTS con UCT, $c = 1.41$, 2000 iteraciones por movimiento |

### Resultados del torneo (200 partidas por emparejamiento)

![Resultados del torneo en Hex 7×7]({{ '/18_montecarlo_search/images/13_tournament_results.png' | url }})

| Enfrentamiento | Victorias jugador 1 | Victorias jugador 2 |
|---|:---:|:---:|
| MCTS vs Aleatorio | **194** | 6 |
| MCTS vs Alpha-beta | **142** | 58 |
| Alpha-beta vs Aleatorio | **178** | 22 |

| Agente | Victorias totales | Derrotas totales | Tasa de victorias |
|---|:---:|:---:|:---:|
| **MCTS (UCT)** | 336 | 64 | **84%** |
| **Alpha-beta + eval** | 236 | 164 | 59% |
| **Aleatorio** | 28 | 372 | 7% |

**Observaciones:**

- MCTS domina claramente — sin ninguna función de evaluación manual, usando solo las reglas del juego y rollouts aleatorios
- Alpha-beta con eval es respetable contra el aleatorio, pero MCTS lo supera consistentemente. La función eval heurística tiene sesgos que MCTS no tiene
- El jugador aleatorio gana ocasionalmente (7%) — recordatorio de que en juegos finitos, incluso el azar puede ganar

---

## 3. Presupuesto de iteraciones

¿Cuántas iteraciones necesita MCTS para jugar bien? Más es mejor, pero con rendimientos decrecientes:

![Tasa de victorias vs presupuesto de iteraciones]({{ '/18_montecarlo_search/images/14_iteration_budget.png' | url }})

| Iteraciones por movimiento | Tasa de victorias vs Aleatorio | Tasa de victorias vs Alpha-beta (d=3) |
|:---:|:---:|:---:|
| 100 | 78% | 35% |
| 500 | 89% | 55% |
| 1000 | 93% | 64% |
| 2000 | 97% | 71% |
| 5000 | 98% | 79% |
| 10000 | 99% | 85% |

**Observación clave**: el salto más grande ocurre entre 100 y 1000 iteraciones. Después de 2000, los rendimientos son decrecientes. En un torneo con tiempo limitado, la asignación inteligente del presupuesto importa tanto como el número total.

---

## 4. Ajuste de la constante $c$

![Efecto de c en la tasa de victorias]({{ '/18_montecarlo_search/images/11_uct_c_effect.png' | url }})

La tabla muestra la tasa de victorias de MCTS (2000 iteraciones) contra Alpha-beta en Hex 7×7, variando $c$:

| $c$ | Tasa de victorias | Interpretación |
|:---:|:---:|---|
| 0.1 | 52% | Casi pura explotación — se aferra a la primera opción razonable |
| 0.5 | 67% | Buena explotación, poca exploración |
| 1.0 | 70% | Buen balance para Hex |
| $\sqrt{2}$ | 71% | Valor teórico — funciona bien |
| 2.0 | 68% | Empieza a explorar demasiado |
| 5.0 | 55% | Demasiada exploración — pierde la ventaja del árbol |

El óptimo está en el rango $c \in [0.5, 1.5]$. El valor teórico $c = \sqrt{2}$ es robusto — no es óptimo para Hex específicamente, pero funciona bien en general. Ajustar $c$ para un juego particular puede mejorar el rendimiento en 5-10%.

---

## 5. El árbol asimétrico

![Árbol MCTS asimétrico]({{ '/18_montecarlo_search/images/15_asymmetric_tree.png' | url }})

La figura muestra el árbol de MCTS después de 2000 iteraciones en una posición de Hex 7×7. A diferencia de minimax (que explora uniformemente), el árbol de MCTS es profundamente **asimétrico**:

- Las ramas con mejores resultados se expanden a profundidad 8-12
- Las ramas con malos resultados se abandonan después de 2-3 niveles
- Algunas acciones legales de la raíz tienen >500 visitas; otras tienen <20

Esto es exactamente lo que queremos: invertir el presupuesto donde importa. Es como si MCTS "aprendiera" una función de evaluación sobre la marcha — no la tiene explícitamente, pero las estadísticas acumuladas cumplen el mismo rol.

---

## 6. Consideraciones prácticas

### 6.1 Reutilización del árbol entre movimientos

Cuando el oponente juega, podemos reusar el subárbol correspondiente a su acción en vez de empezar de cero. Si teníamos 2000 iteraciones acumuladas y el oponente eligió la acción $a$, el nodo `raíz.hijos[a]` ya tiene estadísticas — lo convertimos en la nueva raíz. Esto puede duplicar la "experiencia" efectiva del agente.

### 6.2 Gestión del tiempo

En un torneo con tiempo limitado por movimiento (por ejemplo, 1 segundo), MCTS tiene una ventaja natural: como es **anytime**, podemos ejecutar iteraciones hasta que se agote el reloj. No necesitamos decidir de antemano cuántas iteraciones hacer.

Una estrategia común: asignar más tiempo a los movimientos del inicio (donde el árbol es más ancho y las decisiones más impactantes) y menos al final (donde quedan pocas opciones).

### 6.3 Tablas de transposición

Diferentes secuencias de movimientos pueden llevar a la misma posición. En Hex, jugar $(0,0)$ y luego $(1,1)$ lleva al mismo estado que jugar $(1,1)$ y luego $(0,0)$. Una **tabla de transposición** almacena posiciones ya evaluadas para evitar trabajo duplicado. En la práctica, esto es más complejo que en minimax porque las estadísticas $N$ y $Q$ dependen del camino, pero implementaciones avanzadas lo manejan.

---

**Anterior →** [UCT: la conexión con bandidos](04_uct.md) | **Siguiente →** [Más allá: de MCTS a AlphaZero](06_mas_alla.md)
