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

# Parâmetros do RRCF
NUM_TREES = 40
SHINGLE_SIZE = 16
TREE_SIZE = 256

# Parâmetros do OpenSearch
OS_HOST = os.environ.get("OS_HOST")
OS_PORT = os.environ.get("OS_PORT")
OS_USER = os.environ.get("OS_USER")
OS_PASSWORD = os.environ.get("OS_PASSWORD")
INDEX_NAME = "kong-stream-v1"

# Parâmetros da consulta
QUERY_INTERVAL = 5  # segundos

# Limiar de anomalia (CoDisp)
THRESHOLD = 10


# %% Funções auxiliares
def create_os_client():
    """Cria um cliente OpenSearch."""
    client = OpenSearch(
        hosts=[{"host": OS_HOST, "port": OS_PORT}],
        http_auth=(OS_USER, OS_PASSWORD),
        use_ssl=True,
        verify_certs=False,
        http_compress=True,
    )
    return client


def fetch_data(client):
    """Busca dados do OpenSearch."""
    query = {
        "size": 0,
        "query": {
            "range": {
                "@timestamp": {"gt": f"now-{QUERY_INTERVAL}s"}
            }
        },
        "aggs": {
            "latency": {"avg": {"field": "latencies.kong"}}
        },
    }
    try:
        response = client.search(index=INDEX_NAME, body=query)
        aggr = response.get("aggregations", {})
        if aggr and aggr.get("latency"):
            return aggr["latency"]["value"]
        return None  # Retorna None se não houver dados
    except Exception as e:
        print(f"Erro ao consultar o OpenSearch: {e}")
        return None



def detect_anomalies(data_point, forest, shingle_size, tree_size, global_index):
    """Detecta anomalias usando RRCF."""


    points_buffer.append(data_point)


    if len(points_buffer) < tree_size:
        return 0, [] # Retorna 0 e lista vazia se o buffer não estiver cheio


    if len(forest[0].leaves) > tree_size:
        old_index = global_index - tree_size
        for tree in forest:
            if old_index in tree.leaves:
                tree.forget_point(old_index)

    avg_codisp = 0
    codisp_values = []
    for tree in forest:
        tree.insert_point(data_point, index=global_index)
        codisp = tree.codisp(global_index)
        codisp_values.append(codisp)
        avg_codisp += codisp

    avg_codisp /= len(forest)


    return avg_codisp, codisp_values


# %% Fluxo principal

# Inicialização
client = create_os_client()
forest = [rrcf.RCTree() for _ in range(NUM_TREES)]
shingle = deque(maxlen=SHINGLE_SIZE)
points_buffer = deque(maxlen=TREE_SIZE + SHINGLE_SIZE)

global_index = 0

# Loop principal
while True:
    data_point = fetch_data(client)

    if data_point is not None:
        shingle.append(data_point)
        if len(shingle) == SHINGLE_SIZE:
            data_point_shingle = np.array(list(shingle))
            score, codisp_values = detect_anomalies(
                data_point_shingle, forest, SHINGLE_SIZE, TREE_SIZE, global_index
            )

            print(f"Data point: {data_point}, CoDisp: {score}, CoDisp values: {codisp_values}")

            if score > THRESHOLD:
                print(f"⚠️ Anomalia detectada! Pontuação: {score:.2f}")
            global_index += 1

    else:
        print("Nenhum dado encontrado.")
        
    time.sleep(QUERY_INTERVAL)

