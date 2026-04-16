import json, os

arquivos = [f for f in os.listdir(".") if f.endswith(".json") and f != "testes.json"]

with open(arquivos[0], "r", encoding="utf-8") as f:
    dados = json.load(f)                        # carrega o JSON

primeira_data = list(dados.keys())[1]           # pega a primeira data disponível
primeiro_dia  = dados[primeira_data]            # pega o dicionário desse dia

print(f"Data: {primeira_data}")
print(f"Chaves do dia: {primeiro_dia.keys()}")  # deve mostrar 'status' e 'registros'
print(f"Status: {primeiro_dia.get('status')}")

registros = primeiro_dia.get("registros", [])
print(f"Quantidade de registros nesse dia: {len(registros)}")

if len(registros) > 0:
    print(f"\nChaves do primeiro registro: {registros[0].keys()}")
    print(f"\nPrimeiro registro completo:")
    print(json.dumps(registros[0], ensure_ascii=False, indent=2))
    # ensure_ascii=False → mostra caracteres PT corretamente
    # indent=2 → formata o JSON de forma legível