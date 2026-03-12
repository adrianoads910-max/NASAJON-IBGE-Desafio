# Desafio Técnico - Integração IBGE (Nasajon)

Este repositório contém a solução desenvolvida para o desafio técnico de processamento de dados populacionais, integração com a API do IBGE e envio de estatísticas via Supabase.

## 🛠️ Tecnologias Utilizadas
- **Linguagem:** Python 3
- **Bibliotecas Embutidas:** `csv`, `json`, `unicodedata`, `difflib` (para evitar dependências pesadas e externas).
- **Bibliotecas Externas:** `requests` (para comunicação HTTP com Supabase e IBGE).

## 🧠 Notas Explicativas e Decisões Técnicas

Para garantir resiliência, performance e integridade dos dados, as seguintes decisões arquiteturais foram tomadas:

1. **Estratégia de Busca (In-Memory vs N+1):**
   Em vez de fazer uma requisição à API do IBGE para cada linha do CSV (o que geraria lentidão e possível bloqueio por *Rate Limit*), o script faz um único `GET` inicial para a rota `/api/v1/localidades/municipios`. Os ~5570 municípios são mapeados em um dicionário local na memória do Python, tornando a busca na etapa de processamento praticamente instantânea (O(1)).

2. **Resiliência no Consumo da API:**
   A API do IBGE pode apresentar inconsistências em sua árvore JSON (ex: ausência da chave `microrregiao` em atualizações recentes para alguns locais). Para evitar quebras (`KeyError`), a navegação pelos nós do JSON foi feita utilizando o método `.get()` do Python, garantindo que o programa continue rodando e aplique *fallbacks* (como buscar por `regiao-imediata`) caso a estrutura primária falhe.

3. **Normalização e *Fuzzy Matching*:**
   - **Normalização:** Utilizei `unicodedata` para remover acentos e converter tudo para minúsculas, garantindo que "São Paulo" e "Sao Paulo" dessem *match* exato.
   - **Fuzzy Matching:** Para lidar com erros de digitação severos presentes no input (ex: "Belo Horzionte", "Curitba"), implementei a biblioteca nativa `difflib`. Ela calcula a similaridade das strings e encontra a correspondência oficial correta sem a necessidade de bibliotecas complexas de NLP.

4. **Tratamento de Ambiguidade (Falsos Positivos):**
   Municípios como "Santo André" existem em mais de uma unidade federativa (SP e PB). Como o `input.csv` não fornece a UF para desempate, o script agrupa os resultados. Se houver mais de um match para o mesmo nome, o status é classificado rigorosamente como `AMBIGUO` para proteger o banco de dados de inserções incorretas. Nas estatísticas da API, esses casos foram contabilizados como não encontrados.

## 🚀 Como Executar

1. Clone o repositório.
2. Certifique-se de ter o Python 3 e a biblioteca `requests` instalados (`pip install requests`).
3. Insira suas credenciais válidas do Supabase nas variáveis `EMAIL_CANDIDATO` e `SENHA_CANDIDATO` dentro do `main.py`.
4. Execute o comando:
   ```bash
   python main.py