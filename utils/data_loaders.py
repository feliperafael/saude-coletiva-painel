import streamlit as st
import pandas as pd
import openpyxl
import warnings
import sqlite3

# Load data from SIH
@st.cache_data
def load_health_data():
    try:
        df = pd.read_csv('data/sih_2000_2024.csv', low_memory=False)
        
        # Convert date columns if needed
        if 'dt_inter' in df.columns:
            df['dt_inter'] = pd.to_datetime(df['dt_inter'])
        
        # Filter for psychiatric conditions (Transtornos mentais e comportamentais)
        mental_health_df = df[df['def_diag_princ_cap'].str.contains('Transtornos mentais e comportamentais', na=False)]
        
        # Check if race column exists
        if 'RACA_COR' in mental_health_df.columns:
            # Map race/color codes to descriptions if needed
            race_mapping = {
                1: 'Branca',
                2: 'Preta',
                3: 'Parda',
                4: 'Amarela',
                5: 'Indígena',
                9: 'Sem informação'
            }
            mental_health_df['RACA_COR_DESC'] = mental_health_df['RACA_COR'].map(race_mapping)
        
        return mental_health_df
    except Exception as e:
        st.error(f"Erro ao carregar dados de saúde: {e}")
        return pd.DataFrame()

# Função para carregar os dados do IDSC
@st.cache_data
def load_idsc_data(year):
    try:
        file_path = f"data/Base_de_Dados_IDSC-BR_{year}.xlsx"
        sheet_name = f"IDSC-BR {year}"
        
        # Primeiro tente ler com pandas normalmente
        try:
            idsc_df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception as e:
            if "Bad CRC-32" in str(e):
                st.warning(f"Arquivo Excel corrompido. Tentando método alternativo de leitura...")
                # Tentar ler com engine diferente
                try:
                    idsc_df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                except Exception as inner_e:
                    # Se falhar, tentar método ainda mais robusto com xlrd
                    try:
                        import xlrd
                        idsc_df = pd.read_excel(file_path, sheet_name=0, engine='xlrd')
                    except Exception as xlrd_e:
                        st.error(f"Não foi possível ler o arquivo Excel: {e}. Detalhes: {xlrd_e}")
                        # Retornar dicionários vazios em caso de erro
                        return {}, pd.DataFrame(), {}, {}, {}, {}
            else:
                st.error(f"Erro ao ler arquivo Excel: {e}")
                # Retornar dicionários vazios em caso de erro
                return {}, pd.DataFrame(), {}, {}, {}, {}
        
        # Verificar se o DataFrame está vazio
        if idsc_df is None or idsc_df.empty:
            st.error(f"O arquivo IDSC para o ano {year} não contém dados válidos.")
            return {}, pd.DataFrame(), {}, {}, {}, {}
        
        # Verificar se a coluna COD_MUN existe
        if 'COD_MUN' not in idsc_df.columns:
            st.error(f"Coluna 'COD_MUN' não encontrada no arquivo IDSC {year}.")
            return {}, pd.DataFrame(), {}, {}, {}, {}
            
        # Ajustar o código do município removendo o último dígito para compatibilidade
        idsc_df['COD_MUN_AJUSTADO'] = idsc_df['COD_MUN'].astype(str).str[:-1]
        
        # Pegando a coluna correta do IDSC
        idsc_column = f"IDSC-BR {year}"
        
        # Verificar se a coluna IDSC existe
        if idsc_column not in idsc_df.columns:
            st.error(f"Coluna '{idsc_column}' não encontrada no arquivo IDSC {year}.")
            return {}, pd.DataFrame(), {}, {}, {}, {}
        
        # Criar um dicionário de códigos de municípios para valores IDSC
        idsc_dict = {}
        
        # Criar dicionários para os Goals individuais
        goal1_dict = {}
        goal3_dict = {}
        goal5_dict = {}
        goal10_dict = {}
        
        # Verificar se as colunas de Goals existem
        goal1_col = 'Goal 1 Score' if 'Goal 1 Score' in idsc_df.columns else None
        goal3_col = 'Goal 3 Score' if 'Goal 3 Score' in idsc_df.columns else None
        goal5_col = 'Goal 5 Score' if 'Goal 5 Score' in idsc_df.columns else None
        goal10_col = 'Goal 10 Score' if 'Goal 10 Score' in idsc_df.columns else None
        
        for _, row in idsc_df.iterrows():
            # Verificar se a linha tem todos os dados necessários
            if pd.isna(row['COD_MUN_AJUSTADO']) or pd.isna(row[idsc_column]):
                continue
                
            idsc_dict[row['COD_MUN_AJUSTADO']] = row[idsc_column]
            
            # Adicionar os Goals individuais, se existirem
            if goal1_col and not pd.isna(row.get(goal1_col, pd.NA)):
                goal1_dict[row['COD_MUN_AJUSTADO']] = row[goal1_col]
            if goal3_col and not pd.isna(row.get(goal3_col, pd.NA)):
                goal3_dict[row['COD_MUN_AJUSTADO']] = row[goal3_col]
            if goal5_col and not pd.isna(row.get(goal5_col, pd.NA)):
                goal5_dict[row['COD_MUN_AJUSTADO']] = row[goal5_col]
            if goal10_col and not pd.isna(row.get(goal10_col, pd.NA)):
                goal10_dict[row['COD_MUN_AJUSTADO']] = row[goal10_col]
        
        # Verificar se os dicionários não estão vazios
        if not idsc_dict:
            st.warning(f"Nenhum valor de IDSC encontrado para o ano {year}.")
        
        return idsc_dict, idsc_df, goal1_dict, goal3_dict, goal5_dict, goal10_dict
    except Exception as e:
        st.error(f"Erro ao carregar dados do IDSC: {e}")
        # Retornar dicionários vazios em caso de erro
        return {}, pd.DataFrame(), {}, {}, {}, {}

# Função para carregar dados de CIR (Classificação dos Municípios)
@st.cache_data
def load_cir_data():
    try:
        # Ajuste o caminho conforme necessário
        file_path = "data/cir_municipios.csv"
        cir_df = pd.read_csv(file_path)
        
        # Criar um dicionário de códigos de municípios para grupos CIR
        cir_dict = {}
        
        # Verificar as colunas necessárias
        if 'cod_municipio' in cir_df.columns and 'grupo_cir' in cir_df.columns:
            for _, row in cir_df.iterrows():
                cir_dict[str(row['cod_municipio'])] = row['grupo_cir']
        
        return (cir_dict, cir_df)
    except Exception as e:
        st.warning(f"Erro ao carregar dados de CIR: {e}")
        return ({}, pd.DataFrame())

# Função para carregar dados de população do banco populacao.db
@st.cache_data
def load_population_data(year=None, state_code=None, municipality_code=None):
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect('data/populacao.db')
        
        # Construir a query SQL com base nos filtros
        query = "SELECT * FROM populacao"
        params = []
        
        # Adicionar filtros à query
        where_clauses = []
        
        if year:
            where_clauses.append("ano = ?")
            params.append(year)
            
        if state_code:
            where_clauses.append("uf = ?")
            params.append(state_code)
            
        if municipality_code:
            where_clauses.append("cod_municipio = ?")
            params.append(municipality_code)
            
        # Adicionar cláusulas WHERE à query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        # Executar a query
        df_pop = pd.read_sql_query(query, conn, params=params)
        
        # Fechar a conexão
        conn.close()
        
        return df_pop
    except Exception as e:
        st.error(f"Erro ao carregar dados de população: {e}")
        # Criar um DataFrame vazio com as colunas esperadas
        return pd.DataFrame(columns=['ano', 'uf', 'cod_municipio', 'populacao'])

# Função para calcular a taxa de internações por 100k habitantes
def calcular_taxa_internacao_por_100k(df_filtered, df_pop):
    # Verificar quais colunas precisam ser preservadas
    colunas_extras = ['Grupo_CIR'] if 'Grupo_CIR' in df_filtered.columns else []
    
    # Garantir que MUNIC_RES seja tratado como string para evitar problemas de tipo no merge
    df_filtered = df_filtered.copy()
    df_filtered['MUNIC_RES'] = df_filtered['MUNIC_RES'].astype(str)
    
    # Construir o dicionário de agregação para colunas extras
    extra_aggs = {}
    for col in colunas_extras:
        extra_aggs[col] = (col, 'first')
    
    # Contar internações por município
    internacoes_por_municipio = df_filtered.groupby('MUNIC_RES').agg(
        total_internacoes=('MUNIC_RES', 'count'),
        **extra_aggs
    ).reset_index()
    
    # Garantir que cod_municipio também seja string
    df_pop = df_pop.copy()
    df_pop['cod_municipio'] = df_pop['cod_municipio'].astype(str)
    
    # Mesclar com dados de população
    df_resultado = pd.merge(
        internacoes_por_municipio,
        df_pop[['cod_municipio', 'populacao']],
        left_on='MUNIC_RES',
        right_on='cod_municipio',
        how='left'
    )
    
    # Calcular taxa por 100k habitantes
    df_resultado['taxa_por_100k'] = (df_resultado['total_internacoes'] / df_resultado['populacao']) * 100000
    
    return df_resultado

# Função para calcular a taxa de mortalidade por município
def calcular_taxa_mortalidade_municipio(df_filtered):
    # Verificar quais colunas precisam ser preservadas
    colunas_extras = ['Grupo_CIR'] if 'Grupo_CIR' in df_filtered.columns else []
    
    # Construir o dicionário de agregação para colunas extras
    extra_aggs = {}
    for col in colunas_extras:
        extra_aggs[col] = (col, 'first')
    
    # Usar count para contar o número de internações
    mortalidade_por_municipio = df_filtered.groupby('MUNIC_RES').agg(
        total_internacoes=('MUNIC_RES', 'count'),
        total_mortes=('MORTE', 'sum'),
        **extra_aggs
    ).reset_index()
    
    # Calcular taxa de mortalidade
    mortalidade_por_municipio['taxa_mortalidade'] = (mortalidade_por_municipio['total_mortes'] / 
                                                    mortalidade_por_municipio['total_internacoes']) * 100
    
    return mortalidade_por_municipio

# Função para calcular o tempo médio de permanência por município
def calcular_tempo_permanencia_municipio(df_filtered):
    # Verificar quais colunas precisam ser preservadas
    colunas_extras = ['Grupo_CIR'] if 'Grupo_CIR' in df_filtered.columns else []
    
    # Construir o dicionário de agregação para colunas extras
    extra_aggs = {}
    for col in colunas_extras:
        extra_aggs[col] = (col, 'first')
    
    # Usar Pandas agg com dicionário de agregação mais claro
    permanencia_por_municipio = df_filtered.groupby('MUNIC_RES').agg(
        total_internacoes=('MUNIC_RES', 'count'),
        tempo_medio_permanencia=('DIAS_PERM', 'mean'),
        **extra_aggs
    ).reset_index()
    
    return permanencia_por_municipio 