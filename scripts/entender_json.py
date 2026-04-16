import os
import json

# Pega o primeiro arquivo JSON que achar na pasta para fazer o Raio-X
arquivos_json = [f for f in os.listdir('.') if f.endswith('.json')]
arquivo_alvo = arquivos_json[0]

print(f"Fazendo Raio-X profundo no arquivo: {arquivo_alvo}")
print("=" * 70)

# A nossa função detetive recursiva
def procurar_lista_profunda(dados, caminho_atual=""):
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            # Anota o caminho por onde estamos passando
            caminho_novo = f"{caminho_atual} -> ['{chave}']" if caminho_atual else f"Raiz -> ['{chave}']"
            
            if isinstance(valor, list):
                print(f"🎯 ACHOU! Lista encontrada no caminho: {caminho_novo}")
                print(f"   -> Quantidade de documentos aqui: {len(valor)}")
                if len(valor) > 0 and isinstance(valor[0], dict):
                    print(f"   -> Chaves do 1º documento: {list(valor[0].keys())}\n")
            
            elif isinstance(valor, dict):
                # Se achou outra caixa, entra nela e procura de novo (Recursão)
                procurar_lista_profunda(valor, caminho_novo)

# Abre o arquivo e solta o detetive
try:
    with open(arquivo_alvo, "r", encoding="utf-8") as f:
        conteudo = json.load(f)
    procurar_lista_profunda(conteudo)
    
except Exception as e:
    print(f"Erro ao ler o arquivo: {e}")

print("=" * 70)