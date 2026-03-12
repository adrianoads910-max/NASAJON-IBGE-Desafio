import urllib3
import csv
import json
import requests
import unicodedata
import difflib


SUPABASE_URL = "https://mynxlubykylncinttggu.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15bnhsdWJ5a3lsbmNpbnR0Z2d1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUxODg2NzAsImV4cCI6MjA4MDc2NDY3MH0."
    "Z-zqiD6_tjnF2WLU167z7jT5NzZaG72dWH0dpQW1N-Y"
)
EDGE_FUNCTION_URL = "https://mynxlubykylncinttggu.functions.supabase.co/ibge-submit"

EMAIL_CANDIDATO = "adrianoads910@gmail.com"
SENHA_CANDIDATO = "80AKms27@"


def normalize_string(s: str) -> str:
    s = str(s).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def get_access_token() -> str:
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY
    }
    payload = {
        "email": EMAIL_CANDIDATO,
        "password": SENHA_CANDIDATO
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("    Login realizado com sucesso!")
        return response.json().get("access_token")
    else:
        print(f"    Erro no login: {response.text}")
        exit(1)

def fetch_ibge_data() -> dict:
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()
        
        ibge_dict = {}
        for mun in data:
            try:
                nome_oficial = mun.get('nome', '')
                id_ibge = mun.get('id', '')
                micro = mun.get('microrregiao', {})
                meso = micro.get('mesorregiao', {})
                uf_dict = meso.get('UF', {})
                regiao_dict = uf_dict.get('regiao', {})
                
                uf = uf_dict.get('sigla', '')
                regiao = regiao_dict.get('nome', '')
                
                if not uf:
                    uf = mun.get('regiao-imediata', {}).get('regiao-intermediaria', {}).get('UF', {}).get('sigla', '')
                    regiao = mun.get('regiao-imediata', {}).get('regiao-intermediaria', {}).get('UF', {}).get('regiao', {}).get('nome', '')

                nome_norm = normalize_string(nome_oficial)
                
                if nome_norm not in ibge_dict:
                    ibge_dict[nome_norm] = []
                    
                ibge_dict[nome_norm].append({
                    "municipio_ibge": nome_oficial,
                    "uf": uf,
                    "regiao": regiao,
                    "id_ibge": id_ibge
                })
            except Exception as e_mun:
                print(f"    [Aviso] Falha ao processar dados de {mun.get('nome')}: {e_mun}")
                continue
                
        print(f"    {len(data)} municípios carregados na memória.")
        return ibge_dict
        
    except Exception as e:
        print(f"    ERRO_API ao buscar IBGE: {e}")
        import traceback
        traceback.print_exc() 
        return None

def process_data(ibge_dict: dict):
    
    stats = {
        "total_municipios": 0,
        "total_ok": 0,
        "total_nao_encontrado": 0,
        "total_erro_api": 0 if ibge_dict else 1,
        "pop_total_ok": 0,
        "medias_por_regiao": {}
    }
    
    regioes_pop = {}
    resultados = []
    
    try:
        with open('input.csv', mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                mun_input = row['municipio']
                pop_input = int(row['populacao'])
                stats["total_municipios"] += 1
                
                status = "NAO_ENCONTRADO"
                ibge_info = {"municipio_ibge": "", "uf": "", "regiao": "", "id_ibge": ""}
                
                if ibge_dict:
                    norm_input = normalize_string(mun_input)
                    
                   
                    matches = []
                    if norm_input in ibge_dict:
                        matches = ibge_dict[norm_input]
                    else:
                     
                        close_matches = difflib.get_close_matches(norm_input, ibge_dict.keys(), n=1, cutoff=0.8)
                        if close_matches:
                            matches = ibge_dict[close_matches[0]]
                    
                    if len(matches) == 1:
                        status = "OK"
                        ibge_info = matches[0]
                    elif len(matches) > 1:
                        status = "AMBIGUO" 
                    else:
                        status = "NAO_ENCONTRADO"
                else:
                    status = "ERRO_API"
            
                if status == "OK":
                    stats["total_ok"] += 1
                    stats["pop_total_ok"] += pop_input
                    
                    regiao = ibge_info['regiao']
                    if regiao not in regioes_pop:
                        regioes_pop[regiao] = []
                    regioes_pop[regiao].append(pop_input)
                elif status in ["NAO_ENCONTRADO", "AMBIGUO"]:
                    stats["total_nao_encontrado"] += 1
                    
                resultados.append({
                    "municipio_input": mun_input,
                    "populacao_input": pop_input,
                    "municipio_ibge": ibge_info["municipio_ibge"],
                    "uf": ibge_info["uf"],
                    "regiao": ibge_info["regiao"],
                    "id_ibge": ibge_info["id_ibge"],
                    "status": status
                })
    except FileNotFoundError:
        print("    Erro: Arquivo input.csv não encontrado.")
        exit(1)


    for regiao, pops in regioes_pop.items():
        stats["medias_por_regiao"][regiao] = round(sum(pops) / len(pops), 2)
        
 
    with open('resultado.csv', mode='w', encoding='utf-8', newline='') as outfile:
        fieldnames = ["municipio_input", "populacao_input", "municipio_ibge", "uf", "regiao", "id_ibge", "status"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(resultados)
        
    print("    resultado.csv gerado com sucesso!")
    return stats

def submit_results(token: str, stats: dict):
    print("Enviando resultados para Edge Function...")
    payload = {"stats": stats}
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(EDGE_FUNCTION_URL, headers=headers, json=payload)
    
    print("\n--- RESPOSTA DA API ---")
    print(f"Status Code: {response.status_code}")
    try:
        resp_json = response.json()
        print(json.dumps(resp_json, indent=2, ensure_ascii=False))
        print(f"\n✅ SCORE FINAL: {resp_json.get('score', 'N/A')}")
    except json.JSONDecodeError:
        print(response.text)


if __name__ == "__main__":
    token = get_access_token()
    ibge_data = fetch_ibge_data()
    estatisticas = process_data(ibge_data)
    submit_results(token, estatisticas)