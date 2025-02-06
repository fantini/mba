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

# %% Parametro de configuracao

# Parametros do RRCF
RRCF_NUM_TREES = 40
RRCF_SHINGLE_SIZE = 4
RRCF_TREE_SIZE = 256
RRCF_THRESHOLD = 10
RRCF_INDEX_RESET_THRESHOLD = 1_000_000

# Parametros do OpenSearch
OS_HOST = os.environ.get("OS_HOST")
OS_PORT = os.environ.get("OS_PORT")
OS_USER = os.environ.get("OS_USER")
OS_PASSWORD = os.environ.get("OS_PASSWORD")
OS_INDEX_NAME = "kong-stream-v1"
OS_SEARCH_INTERVAL = 5

# %% Funcoes auxiliares
def create_os_client():
    warnings.filterwarnings("ignore")
    client = OpenSearch(
        hosts=[{"host": OS_HOST, "port": OS_PORT}],
        http_auth=(OS_USER, OS_PASSWORD),
        use_ssl=True,
        verify_certs=False,
        http_compress=True,
    )
    return client

def reset_forest():
    """Reinicia a floresta e os índices para evitar crescimento excessivo."""
    global forest, global_index, points_buffer, anomaly_scores
    print("🔄 Reiniciando a floresta para evitar crescimento excessivo...")

    # Criar uma nova floresta limpa
    forest = [rrcf.RCTree() for _ in range(RRCF_NUM_TREES)]
    global_index = 0  # Reiniciar contador de índices
    points_buffer.clear()  # Esvaziar buffer de pontos
    anomaly_scores.clear()  # Esvaziar os scores

def fetch_data():
    query = {
        "size": 0,
        "query": {
            "range": {
                "@timestamp": {
                    "gt": "now-5s"
                }
            }
        },
        "aggs": {
            "latency": {
                "avg": {
                    "field": "latencies.kong"
                }
            }
        }
    }
    try:
        response = create_os_client().search(index=OS_INDEX_NAME, body=query)
        aggr = response.get("aggregations", {})
        if aggr["latency"]:
            return aggr["latency"]["value"]
    except Exception as e:
         print(f"Erro ao consultar o OpenSearch: {e}")
         return []

def update_forest(point):
    global global_index

    if point is None:
        return None  # Ignorar se não há um shingle formado
    
    if global_index >= RRCF_INDEX_RESET_THRESHOLD:
        reset_forest()

    point = np.array(point)  # Converter para array NumPy
    points_buffer.append(point)  # Adicionar ao buffer limitado

    if len(points_buffer) >= RRCF_TREE_SIZE:
        old_index = global_index - RRCF_TREE_SIZE
        for tree in forest:
            if old_index in tree.leaves:
                tree.forget_point(old_index)

    # Inserir o ponto na floresta e calcular a pontuação média
    avg_codisp = 0
    codisp_values = []
    for tree in forest:
        tree.insert_point(point, index=global_index)
        codisp = tree.codisp(global_index)
        codisp_values.append(codisp)
        avg_codisp += codisp
    
    avg_codisp /= RRCF_NUM_TREES
    anomaly_scores.append(avg_codisp)
    print(f"{point} - {avg_codisp} - {codisp_values}")
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
    anomaly_x = [x_data[i] for i in range(len(anomaly_scores)) if anomaly_scores[i] > RRCF_THRESHOLD]
    anomaly_y = [y_data[i] for i in range(len(anomaly_scores)) if anomaly_scores[i] > RRCF_THRESHOLD]

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
            data_window.append(new_data)
            if len(data_window) >= RRCF_SHINGLE_SIZE:                
                shingled_data = list(rrcf.shingle(data_window, size=RRCF_SHINGLE_SIZE))
                for shingle in shingled_data:
                    update_forest(shingle)
            print("Total de documentos:", len(data_window))
        else:
            print("Nenhum novo documento encontrado.")

        # Aguarda o próximo intervalo
        time.sleep(OS_SEARCH_INTERVAL)

def create_graphic():
    ani = FuncAnimation(fig, update_graph, interval=1000)
    plt.legend()
    plt.show()

# %% Inicializacao
points_buffer = deque(maxlen=RRCF_TREE_SIZE)
data_window = deque(maxlen=RRCF_TREE_SIZE + RRCF_SHINGLE_SIZE)
anomaly_scores = deque(maxlen=RRCF_TREE_SIZE)
global_index = 0
forest = [rrcf.RCTree() for _ in range(RRCF_NUM_TREES)]

# %% Inicializacao do grafico
fig, ax1 = plt.subplots()
ax1.set_title("Detecção de Anomalias com RRCF")
ax1.set_xlabel("Amostra")
ax1.set_ylabel("Data", color="blue")
line, = ax1.plot([], [], label="Dados", color="blue")
anomaly_points, = ax1.plot([], [], 'ro', label="Anomalias")  # Vermelho para anomalias
line_codisp, = ax1.plot([], [], label="CoDisp", color="red")


# %% _Main_
data_thread = threading.Thread(target=fetch_and_process, daemon=True)
data_thread.start()
create_graphic()

