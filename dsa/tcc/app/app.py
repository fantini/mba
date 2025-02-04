# %% Imports
import threading
from opensearchpy import OpenSearch
import time
import os
import warnings
import rrcf
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from matplotlib.animation import FuncAnimation



# %% Configuracao do RRCF
num_trees = 100
shingle_size = 100
tree_size = 500
threshold = 60
index_reset_threshold = 1_000_000

points_buffer = deque(maxlen=tree_size)
data_window = deque(maxlen=tree_size + shingle_size)
anomaly_scores = deque(maxlen=tree_size)
global_index = 0
forest = [rrcf.RCTree() for _ in range(num_trees)]

# %% Configuracao do grafico
fig, ax1 = plt.subplots()
ax1.set_title("Detecção de Anomalias com RRCF")
ax1.set_xlabel("Amostra")
ax1.set_ylabel("Data", color="blue")
line, = ax1.plot([], [], label="Dados", color="blue")
anomaly_points, = ax1.plot([], [], 'ro', label="Anomalias")  # Vermelho para anomalias
line_codisp, = ax1.plot([], [], label="CoDisp", color="red")


# %% Configuracao do client
warnings.filterwarnings("ignore")

client = OpenSearch(
    hosts=[{"host": os.environ.get("OS_HOST"), "port": os.environ.get("OS_PORT")}],
    http_auth=(os.environ.get("OS_USER"), os.environ.get("OS_PASSWORD")),
    http_compress=True,
    use_ssl=True,
    verify_certs=False
)

# %% Consultaqu
index_name = "kong-stream-v1"

query = {
    "size": 500, 
    "_source": "false",
    "fields": ["latencies.kong"],
    "query": {
        "range": {
            "@timestamp": {
                "gt": "now-5s"
            }
        }
    },
    "sort": [
        {
            "@timestamp": {
                "order": "asc"
            }
        }
    ]
}

interval = 5

def reset_forest():
    """Reinicia a floresta e os índices para evitar crescimento excessivo."""
    global forest, global_index, points_buffer, anomaly_scores
    print("🔄 Reiniciando a floresta para evitar crescimento excessivo...")

    # Criar uma nova floresta limpa
    forest = [rrcf.RCTree() for _ in range(num_trees)]
    global_index = 0  # Reiniciar contador de índices
    points_buffer.clear()  # Esvaziar buffer de pontos
    anomaly_scores.clear()  # Esvaziar os scores

def fetch_data():
    try:
        response = client.search(index=index_name, body=query)
        hits = response.get("hits", {})
        points = []
        if hits["hits"]:
            for point in hits["hits"]:
                points.append(point["fields"]["latencies.kong"][0])
        return points
    except Exception as e:
         print(f"Erro ao consultar o OpenSearch: {e}")
         return []

def update_forest(point):
    global global_index

    if point is None:
        return None  # Ignorar se não há um shingle formado
    
    if global_index >= index_reset_threshold:
        reset_forest()

    point = np.array(point)  # Converter para array NumPy
    points_buffer.append(point)  # Adicionar ao buffer limitado

    if len(points_buffer) >= tree_size:
        old_index = global_index - tree_size
        for tree in forest:
            if old_index in tree.leaves:
                tree.forget_point(old_index)

    # Inserir o ponto na floresta e calcular a pontuação média
    avg_codisp = 0
    for tree in forest:
        tree.insert_point(point, index=global_index)
        avg_codisp += tree.codisp(global_index)
    
    avg_codisp /= num_trees
    anomaly_scores.append(avg_codisp)
    print(avg_codisp)
    # Exibir alerta caso seja uma anomalia
    # if avg_codisp > THRESHOLD:
    #     print(f"⚠️ Anomalia detectada! Pontuação: {avg_codisp:.2f}")

    global_index +=1

    return avg_codisp

def update_graph(frame):
    """Atualiza o gráfico em tempo real."""
    if len(points_buffer) == 0 or len(anomaly_scores) == 0:
        return line, anomaly_points, line_codisp
    
    min_length = min(len(points_buffer), len(anomaly_scores))

    x_data = np.arange(min_length)  # Índices das amostras
    y_data = [p[-1] for p in points_buffer][-min_length:]  # Pegando o último valor de cada shingle
    codisp_data = np.array(list(anomaly_scores)[-min_length:])

    # Identificar anomalias
    anomaly_x = [x_data[i] for i in range(len(anomaly_scores)) if anomaly_scores[i] > threshold]
    anomaly_y = [y_data[i] for i in range(len(anomaly_scores)) if anomaly_scores[i] > threshold]

    line.set_data(x_data, y_data)
    anomaly_points.set_data(anomaly_x, anomaly_y)
    line_codisp.set_data(x_data, codisp_data)

    ax1.relim()
    ax1.autoscale_view()

    return line, anomaly_points, line_codisp

def fetch_and_process():
    while True:
        new_data = fetch_data()

        if new_data:
            data_window.extend(new_data)
            shingled_data = list(rrcf.shingle(data_window, size=shingle_size))
            for shingle in shingled_data:
                update_forest(shingle)
            print("Total de documentos:", len(data_window))
        else:
            print("Nenhum novo documento encontrado.")

        # Aguarda o próximo intervalo
        time.sleep(interval)

# %% Loop de consulta
data_thread = threading.Thread(target=fetch_and_process, daemon=True)
data_thread.start()

ani = FuncAnimation(fig, update_graph, interval=1000)

plt.legend()
plt.show()

# %%
