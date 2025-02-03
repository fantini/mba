# pip install opensearch-py

# %% Imports
from opensearchpy import OpenSearch
import time

# %% Configuracao do client
client = OpenSearch(
    http_compress=True,
    use_ssl=True,
    verify_certs=False
)

# %% Consulta
index_name = "kong-stream-v1"

query = {
    "size": 10000,
    "sort": [{"@timestamp": {"order": "desc"}}],
    "query": {
        "range": {
            "@timestamp": {
                "gt": "now-5s",
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
        hits = response.get("hits", {}).get("hits", [])

        if hits:
            print("Novos documentos encontrados:", len(hits))
            for hit in hits:
                print(hit["_source"]["latencies.kong"])
        else:
            print("Nenhum novo documento encontrado.")

    except Exception as e:
        print(f"Erro ao consultar o OpenSearch: {e}")

    # Aguarda o próximo intervalo
    time.sleep(interval)
# %%
