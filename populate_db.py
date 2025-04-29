import pandas as pd
import sqlite3
import random

# Carregar os dados da planilha
df = pd.read_excel('data/base_magda.xlsx')

# Conectar ao banco de dados
conn = sqlite3.connect('data/populacao.db')
cursor = conn.cursor()

# Verificar se a tabela já existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='populacao'")
if not cursor.fetchone():
    # Criar tabela se não existir
    cursor.execute('''
    CREATE TABLE populacao (
        ano INTEGER, 
        uf TEXT, 
        cod_municipio TEXT, 
        populacao INTEGER
    )
    ''')
else:
    # Limpar a tabela existente
    cursor.execute("DELETE FROM populacao")
    print("Tabela existente limpa para novos dados")

# Popular o banco de dados com municípios de cada grupo CIR
for grupo in range(1, 7):
    # Filtrar municípios por grupo
    grupo_df = df[df['Grupo_CIR'] == grupo]
    
    if not grupo_df.empty:
        # Para cada grupo, selecionar até 5 municípios aleatórios
        amostra = grupo_df.sample(min(5, len(grupo_df)))
        
        # Inserir dados no banco
        for _, row in amostra.iterrows():
            try:
                # Obter o código do estado (2 primeiros dígitos do código IBGE)
                uf = str(row['IBGE'])[:2]
                
                # Obter o código do município (IBGE completo)
                cod_municipio = str(row['IBGE'])
                
                # Gerar população aleatória baseada no grupo CIR
                # Grupos com números maiores tendem a ter municípios maiores
                base_pop = 50000 * grupo
                pop = random.randint(base_pop, base_pop + 100000)
                
                # Inserir no banco para o ano 2023
                cursor.execute('INSERT INTO populacao VALUES (?, ?, ?, ?)', 
                              (2023, uf, cod_municipio, pop))
                
                print(f"Adicionado município {cod_municipio} do Grupo CIR {grupo} com população {pop}")
            except Exception as e:
                print(f"Erro ao adicionar município {row['IBGE']} do Grupo CIR {grupo}: {e}")

# Adicionar também dados para o ano 2022 (para teste de filtros)
for grupo in range(1, 7):
    grupo_df = df[df['Grupo_CIR'] == grupo]
    
    if not grupo_df.empty:
        amostra = grupo_df.sample(min(3, len(grupo_df)))
        
        for _, row in amostra.iterrows():
            try:
                uf = str(row['IBGE'])[:2]
                cod_municipio = str(row['IBGE'])
                
                # Primeiro verificar se já existe registro para 2023
                cursor.execute("SELECT populacao FROM populacao WHERE ano=2023 AND cod_municipio=?", (cod_municipio,))
                result = cursor.fetchone()
                
                if result:
                    # Usar a população de 2023 como referência
                    pop_2023 = result[0]
                    # Reduzir a população em 2-5% para simular o ano anterior
                    pop_2022 = int(pop_2023 * random.uniform(0.95, 0.98))
                else:
                    # Gerar população aleatória
                    base_pop = 50000 * grupo
                    pop_2022 = random.randint(base_pop, base_pop + 100000)
                
                cursor.execute('INSERT INTO populacao VALUES (?, ?, ?, ?)', 
                              (2022, uf, cod_municipio, pop_2022))
                
                print(f"Adicionado município {cod_municipio} do Grupo CIR {grupo} para 2022 com população {pop_2022}")
            except Exception as e:
                print(f"Erro ao adicionar município {row['IBGE']} do Grupo CIR {grupo} para 2022: {e}")

# Confirmar alterações e fechar conexão
conn.commit()
conn.close()

print("Banco de dados populado com sucesso!") 