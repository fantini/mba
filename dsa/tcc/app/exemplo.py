# %% Imports

import numpy as np
import rrcf
import matplotlib.pyplot as plt

# %% Gerando dados sintéticos

np.random.seed(42)
data = np.random.normal(loc=50, scale=5, size=100)
data[20] = 70
data[55] = 30
data[85] = 75

points = data.reshape(-1, 1)

# %% Criando a RRCF com 50 arvores

forest = rrcf.RCTree()

# %% Adicionando os pontos na floresta e coletando os scores (CoDis)

anomaly_scores = []
for i, point in enumerate(points):
    forest.insert_point(point, index=i)
    anomaly_scores.append(forest.codisp(i))

# %% Plotando os resultados

plt.figure(figsize=(10, 5))
plt.plot(data, label="Temperatura", marker="o")
plt.scatter(range(len(data)), data, c=anomaly_scores, cmap="coolwarm", edgecolors="black")
plt.colorbar(label="Score de Anomalia (CoDis)")
plt.axhline(y=50, color="gray", linestyle="--", label="Média Esperada")
plt.xlabel("Tempo")
plt.ylabel("Temperatura (°C)")
plt.title("Detecção de Anomalias com RRCF")
plt.legend()
plt.show()


# %%
