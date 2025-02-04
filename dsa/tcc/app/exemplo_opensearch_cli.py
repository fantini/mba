# pip install opensearch-py

# %% Imports
from opensearchpy import OpenSearch
import time
import os
import warnings
import urllib3

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

interval = 5

# %% Loop de consulta
while True:
    try:
        # Executa a consulta
        response = client.search(index=index_name, body=query)

        # Processa os resultados
        hits = response.get("hits", {})
        aggs = response.get("aggregations", {})

        if hits["total"]["value"]:
            print("Total de documentos:", hits["total"]["value"])
            print("Média de latência:", aggs["latency"]["value"])
        else:
            print("Nenhum novo documento encontrado.")

    except Exception as e:
        print(f"Erro ao consultar o OpenSearch: {e}")

    # Aguarda o próximo intervalo
    time.sleep(interval)
# %%
