import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sqlite3
import openpyxl
import os
import warnings

# Set page configuration
st.set_page_config(
    page_title="Relação IDSC e Indicadores Psiquiátricos",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Relação entre IDSC e Indicadores de Saúde Mental")
st.markdown("""
Este dashboard analisa a relação entre o Índice de Desenvolvimento Sustentável das Cidades (IDSC) 
e diversos indicadores de saúde mental, como taxa de mortalidade, tempo de permanência hospitalar e 
número de internações psiquiátricas no Brasil.
""")

# Função para exibir resumo dos filtros aplicados
def mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, 
                              ano_idsc, usar_raca_cor2=False, diag_grupo=None, diag_categoria=None, diag_subcategoria=None):
    st.subheader("Filtros Aplicados")
    
    filtros_texto = f"**Período:** {year_range[0]} a {year_range[1]}"
    
    if estado_nome != "Todos":
        filtros_texto += f" | **Estado:** {estado_nome}"
    else:
        filtros_texto += " | **Estado:** Todos"
        
    if codigo_municipio:
        nome_municipio = municipios_dict.get(codigo_municipio, "")
        if nome_municipio:
            filtros_texto += f" | **Município:** {nome_municipio} ({codigo_municipio})"
        else:
            filtros_texto += f" | **Município:** {codigo_municipio}"
    else:
        filtros_texto += " | **Município:** Todos"
        
    if sexo != "Todos":
        filtros_texto += f" | **Sexo:** {sexo}"
    else:
        filtros_texto += " | **Sexo:** Todos"
        
    if faixa_etaria != "Todas":
        filtros_texto += f" | **Faixa Etária:** {faixa_etaria}"
    else:
        filtros_texto += " | **Faixa Etária:** Todas"
        
    if raca != "Todas":
        filtros_texto += f" | **Raça/Cor:** {raca}"
    else:
        filtros_texto += " | **Raça/Cor:** Todas"
    
    if usar_raca_cor2:
        filtros_texto += " | **Classificação Racial:** Raça/Cor 2 (Preta + Parda = Negra)"
    else:
        filtros_texto += " | **Classificação Racial:** Tradicional"
    
    # Adicionar informações sobre os filtros diagnósticos
    if diag_grupo:
        filtros_texto += f" | **Grupo Diagnóstico:** {diag_grupo}"
        
        if diag_categoria:
            filtros_texto += f" | **Categoria Diagnóstica:** {diag_categoria}"
            
            if diag_subcategoria:
                filtros_texto += f" | **Subcategoria:** {diag_subcategoria}"
    
    # Adicionar informação sobre o ano do IDSC
    filtros_texto += f" | **Ano IDSC:** {ano_idsc}"
    
    st.markdown(filtros_texto)
    
    # Adicionar linha divisória para melhor visualização
    st.markdown("---")

# Função para ajustar dados de raça/cor para visualizações
def ajustar_dados_raca(df, coluna_raca, usar_raca_cor2=False):
    if not usar_raca_cor2:
        return df
    
    # Criar cópia para não modificar o original
    df_ajustado = df.copy()
    
    # Verificar se a coluna existe
    if coluna_raca not in df_ajustado.columns:
        return df_ajustado
    
    # Para gráficos de contagem/distribuição
    if coluna_raca in df_ajustado.columns and usar_raca_cor2:
        # Substituir "Preta" e "Parda" por "Negra"
        mascara = df_ajustado[coluna_raca].isin(["Preta", "Parda"])
        
        if mascara.any():
            # Somar contagens de Preta e Parda
            if 'Contagem' in df_ajustado.columns:
                contagem_negra = df_ajustado.loc[mascara, 'Contagem'].sum()
                
                # Remover linhas de Preta e Parda
                df_ajustado = df_ajustado[~mascara]
                
                # Adicionar linha para Negra
                nova_linha = pd.DataFrame({coluna_raca: ["Negra"], 'Contagem': [contagem_negra]})
                df_ajustado = pd.concat([df_ajustado, nova_linha], ignore_index=True)
            
            # Se for taxa de mortalidade ou outra métrica
            elif 'Taxa de Mortalidade (%)' in df_ajustado.columns:
                # Calcular média ponderada baseada no tamanho dos grupos
                # Isso é uma aproximação, idealmente recalcularíamos do zero
                taxa_negra = df_ajustado.loc[mascara, 'Taxa de Mortalidade (%)'].mean()
                
                # Remover linhas de Preta e Parda
                df_ajustado = df_ajustado[~mascara]
                
                # Adicionar linha para Negra
                nova_linha = pd.DataFrame({coluna_raca: ["Negra"], 'Taxa de Mortalidade (%)': [taxa_negra]})
                df_ajustado = pd.concat([df_ajustado, nova_linha], ignore_index=True)
    
    return df_ajustado

# Função para carregar os dados do IDSC
@st.cache_data
def load_idsc_data(year):
    try:
        file_path = f"data/Base_de_Dados_IDSC-BR_{year}.xlsx"
        sheet_name = f"IDSC-BR {year}"
        
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            st.error(f"Arquivo do IDSC para o ano {year} não encontrado: {file_path}")
            return {}, pd.DataFrame(), {}, {}, {}, {}
        
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

# Carregar dados dos municípios
@st.cache_data
def load_municipalities():
    try:
        # Lê o arquivo Excel pulando as 6 primeiras linhas
        municipios_df = pd.read_excel('data/RELATORIO_DTB_BRASIL_MUNICIPIO.xls', skiprows=6)
        
        # Extrair os 6 primeiros caracteres do código do município
        municipios_df['cod_6digitos'] = municipios_df['Código Município Completo'].astype(str).str[:6]
        
        # Criar um dicionário de códigos para nomes
        municipios_dict = dict(zip(municipios_df['cod_6digitos'], municipios_df['Nome_Município']))
        
        return municipios_dict
    except Exception as e:
        st.warning(f"Erro ao carregar dados de municípios: {e}")
        return {}

# Load data
@st.cache_data
def load_data():
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

# Função para obter dados de população do banco de dados
def get_population_data(codigo_municipio=None, estado=None, raca=None, sexo=None, faixa_etaria=None, usar_raca_cor2=False):
    if raca:
        raca = raca.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    
    query = "SELECT ano, SUM(populacao) as tam_pop FROM populacao WHERE 1=1"
    
    if codigo_municipio:
        query += f" AND codigo_municipio = '{codigo_municipio}'"
    if estado:
        query += f" AND SUBSTR(codigo_municipio, 1, 2) = '{estado}'"
    if raca:
        if usar_raca_cor2 and raca == "Negra":
            query += f" AND (raca = 'Preta' OR raca = 'Parda')"
        else:
            query += f" AND raca = '{raca}'"
    if sexo:
        query += f" AND sexo = '{sexo}'"
    if faixa_etaria:
        query += f" AND faixa_etaria = '{faixa_etaria}'"
    
    query += " and ano < 2024 GROUP BY ano"
    
    conn = sqlite3.connect('populacao.db')
    df_populacao = pd.read_sql_query(query, conn)
    conn.close()
    
    return df_populacao

# Função para calcular a taxa de mortalidade por município por 100.000 habitantes
def calcular_taxa_mortalidade_municipio(df_filtered, usar_raca_cor2=False, estado=None, sexo=None, faixa_etaria=None, raca=None):
    # Agrupar por município e calcular taxa de mortalidade
    mortalidade_por_municipio = df_filtered.groupby('MUNIC_RES').agg(
        total_internacoes=('MUNIC_RES', 'size'),
        total_mortes=('MORTE', 'sum')
    ).reset_index()
    
    # Calcular taxa de mortalidade percentual
    mortalidade_por_municipio['taxa_mortalidade'] = (mortalidade_por_municipio['total_mortes'] / 
                                                    mortalidade_por_municipio['total_internacoes']) * 100
    
    # Converter sexo para formato compatível com banco de dados
    sexo_db = None
    if sexo == "Masculino":
        sexo_db = "M"
    elif sexo == "Feminino":
        sexo_db = "F"
    
    # Obter dados de população para cada município
    mortalidade_por_municipio['MUNIC_RES_STR'] = mortalidade_por_municipio['MUNIC_RES'].astype(str)
    
    # Aplicar os dados de população e calcular taxas por 100k
    for idx, row in mortalidade_por_municipio.iterrows():
        codigo_municipio = row['MUNIC_RES_STR']
        # Buscar população para este município específico
        df_pop = get_population_data(
            codigo_municipio=codigo_municipio,
            estado=estado,
            raca=raca,
            sexo=sexo_db,
            faixa_etaria=faixa_etaria,
            usar_raca_cor2=usar_raca_cor2
        )
        
        # Se encontrou dados de população, calcular a taxa
        if not df_pop.empty:
            # Usar o ano mais recente disponível
            pop_recente = df_pop.iloc[-1]['tam_pop']
            
            # Calcular taxa por 100.000 habitantes
            if pop_recente > 0:
                mortalidade_por_municipio.at[idx, 'populacao'] = pop_recente
                mortalidade_por_municipio.at[idx, 'taxa_internacoes_100k'] = (row['total_internacoes'] / pop_recente) * 100000
                mortalidade_por_municipio.at[idx, 'taxa_mortalidade_100k'] = (row['total_mortes'] / pop_recente) * 100000
    
    return mortalidade_por_municipio

# Função para calcular o tempo médio de permanência por município
def calcular_tempo_permanencia_municipio(df_filtered, usar_raca_cor2=False, estado=None, sexo=None, faixa_etaria=None, raca=None):
    # Agrupar por município e calcular tempo médio de permanência
    permanencia_por_municipio = df_filtered.groupby('MUNIC_RES').agg(
        total_internacoes=('MUNIC_RES', 'size'),
        tempo_medio_permanencia=('DIAS_PERM', 'mean')
    ).reset_index()
    
    # Converter sexo para formato compatível com banco de dados
    sexo_db = None
    if sexo == "Masculino":
        sexo_db = "M"
    elif sexo == "Feminino":
        sexo_db = "F"
    
    # Obter dados de população para cada município
    permanencia_por_municipio['MUNIC_RES_STR'] = permanencia_por_municipio['MUNIC_RES'].astype(str)
    
    # Aplicar os dados de população e calcular taxas por 100k
    for idx, row in permanencia_por_municipio.iterrows():
        codigo_municipio = row['MUNIC_RES_STR']
        # Buscar população para este município específico
        df_pop = get_population_data(
            codigo_municipio=codigo_municipio,
            estado=estado,
            raca=raca,
            sexo=sexo_db,
            faixa_etaria=faixa_etaria,
            usar_raca_cor2=usar_raca_cor2
        )
        
        # Se encontrou dados de população, calcular a taxa
        if not df_pop.empty:
            # Usar o ano mais recente disponível
            pop_recente = df_pop.iloc[-1]['tam_pop']
            
            # Calcular taxa por 100.000 habitantes
            if pop_recente > 0:
                permanencia_por_municipio.at[idx, 'populacao'] = pop_recente
                permanencia_por_municipio.at[idx, 'taxa_internacoes_100k'] = (row['total_internacoes'] / pop_recente) * 100000
    
    return permanencia_por_municipio

# Função para carregar municípios
def carregar_dicionario_municipios():
    try:
        # Tentar ler o arquivo Excel com os nomes dos municípios
        df_mun = pd.read_excel('data/municipios.xlsx')
        
        # Criar um dicionário código -> nome
        municipios_dict = dict(zip(df_mun['Código'].astype(str), df_mun['Nome']))
        return municipios_dict
    except Exception as e:
        warnings.warn(f"Erro ao carregar dados de municípios: {e}")
        return {}

# Carregar dados
try:
    df = load_data()
    # Carregar dicionário de municípios
    municipios_dict = load_municipalities()
    
    # Display loading message while processing
    with st.spinner('Carregando dados...'):
        data_load_state = st.success('Dados carregados com sucesso!')
    
    # Sidebar filters
    st.sidebar.header("Filtros")
    
    # Filtro para o ano do IDSC
    anos_idsc = [2022, 2023, 2024]
    ano_idsc = st.sidebar.selectbox(
        "Ano de referência do IDSC:",
        options=anos_idsc,
        index=2  # Default para 2024
    )
    
    # Carregar dados do IDSC para o ano selecionado
    idsc_dict, idsc_df, goal1_dict, goal3_dict, goal5_dict, goal10_dict = load_idsc_data(ano_idsc)
    
    # Filter by year range
    years = sorted(df['ANO_CMPT'].unique())
    year_range = st.sidebar.slider(
        "Período de análise:",
        min_value=int(min(years)),
        max_value=int(max(years)),
        value=(int(min(years)), int(max(years)))
    )
    
    # Opção para escolher entre Raça/Cor tradicional ou Raça/Cor 2
    usar_raca_cor2 = st.sidebar.radio(
        "Escolher tipo de classificação racial",
        ["Raça/Cor (tradicional)", "Raça/Cor 2 (Preta + Parda = Negra)"],
        index=0
    ) == "Raça/Cor 2 (Preta + Parda = Negra)"
    
    # Dicionário de estados
    estados = {
        "Todos": None,
        "Acre (AC)": "12",
        "Alagoas (AL)": "27",
        "Amapá (AP)": "16",
        "Amazonas (AM)": "13",
        "Bahia (BA)": "29",
        "Ceará (CE)": "23",
        "Distrito Federal (DF)": "53",
        "Espírito Santo (ES)": "32",
        "Goiás (GO)": "52",
        "Maranhão (MA)": "21",
        "Mato Grosso (MT)": "51",
        "Mato Grosso do Sul (MS)": "50",
        "Minas Gerais (MG)": "31",
        "Pará (PA)": "15",
        "Paraíba (PB)": "25",
        "Paraná (PR)": "41",
        "Pernambuco (PE)": "26",
        "Piauí (PI)": "22",
        "Rio de Janeiro (RJ)": "33",
        "Rio Grande do Norte (RN)": "24",
        "Rio Grande do Sul (RS)": "43",
        "Rondônia (RO)": "11",
        "Roraima (RR)": "14",
        "Santa Catarina (SC)": "42",
        "São Paulo (SP)": "35",
        "Sergipe (SE)": "28",
        "Tocantins (TO)": "17"
    }
    
    # Filtro de Estado
    estado_nome = st.sidebar.selectbox(
        "Estado",
        options=list(estados.keys()),
        index=0
    )
    estado = estados[estado_nome]
    
    # Filtro de Município
    codigo_municipio_options = ["Todos"]
    if estado:
        # Filtra municípios pelo estado selecionado
        codigos_filtrados = [str(cod) for cod in sorted(df['MUNIC_RES'].unique()) if str(cod).startswith(estado)]
        codigo_municipio_options += codigos_filtrados
    else:
        codigo_municipio_options += [str(cod) for cod in sorted(df['MUNIC_RES'].unique())]
    
    # Adiciona nomes dos municípios aos códigos
    codigo_municipio_display = ["Todos"]
    for codigo in codigo_municipio_options[1:]:  # Pula o "Todos"
        nome_municipio = municipios_dict.get(codigo, "")
        if nome_municipio:
            codigo_municipio_display.append(f"{codigo} - {nome_municipio}")
        else:
            codigo_municipio_display.append(codigo)
    
    # Usar os códigos com nomes para display
    codigo_municipio_option_display = st.sidebar.selectbox(
        "Município",
        options=codigo_municipio_display,
        index=0
    )
    
    # Extrair apenas o código do município selecionado
    if codigo_municipio_option_display == "Todos":
        codigo_municipio_option = "Todos"
    else:
        codigo_municipio_option = codigo_municipio_option_display.split(" - ")[0]
    
    codigo_municipio = None if codigo_municipio_option == "Todos" else codigo_municipio_option
    
    # Filtro por sexo
    sexo_options = ["Todos", "Masculino", "Feminino"]
    sexo = st.sidebar.selectbox(
        "Sexo",
        options=sexo_options,
        index=0
    )
    
    # Filtro por faixa etária
    faixa_etaria_options = [
        "Todas",
        '0-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '85-89', '90-94', '95-99', '100+'
    ]
    faixa_etaria = st.sidebar.selectbox(
        "Faixa Etária",
        options=faixa_etaria_options,
        index=0
    )
    
    # Filtro por raça/cor - modificado para suportar Raça/Cor 2
    if 'RACA_COR' in df.columns:
        if usar_raca_cor2:
            # Para Raça/Cor 2, combinar Preta e Parda em Negra
            if 'RACA_COR_DESC' in df.columns:
                race_values = df['RACA_COR_DESC'].dropna().unique()
                raca_options = ["Todas"]
                negra_added = False
                
                for raca_value in sorted(race_values):
                    if raca_value in ["Preta", "Parda"]:
                        if not negra_added:
                            raca_options.append("Negra")
                            negra_added = True
                    else:
                        raca_options.append(raca_value)
            else:
                # Se não houver descrições, usar códigos mapeados
                raca_options = ["Todas", "Negra", "Branca", "Amarela", "Indígena", "Sem informação"]
        else:
            # Para Raça/Cor tradicional, usar todas as opções originais
            if 'RACA_COR_DESC' in df.columns:
                raca_options = ["Todas"] + sorted(df['RACA_COR_DESC'].dropna().unique().tolist())
            else:
                # Se não houver descrição, usar os códigos mapeados
                race_mapping = {
                    1: 'Branca',
                    2: 'Preta',
                    3: 'Parda',
                    4: 'Amarela',
                    5: 'Indígena',
                    9: 'Sem informação'
                }
                raca_options = ["Todas"] + [race_mapping.get(code, str(code)) for code in sorted(df['RACA_COR'].dropna().unique())]
        
        raca = st.sidebar.selectbox(
            "Raça/Cor",
            options=raca_options,
            index=0
        )
    elif 'def_raca_cor' in df.columns:
        if usar_raca_cor2:
            # Obtém as opções únicas de raça/cor do dataframe
            racas_originais = sorted(df['def_raca_cor'].unique().tolist())
            # Cria nova lista substituindo "Preta" e "Parda" por "Negra"
            racas_modificadas = ["Todas"]
            negra_added = False
            for raca_value in racas_originais:
                if raca_value in ["Preta", "Parda"]:
                    if not negra_added:
                        racas_modificadas.append("Negra")
                        negra_added = True
                else:
                    racas_modificadas.append(raca_value)
            
            raca_options = racas_modificadas
        else:
            raca_options = ["Todas"] + sorted(df['def_raca_cor'].dropna().unique().tolist())
        
        raca = st.sidebar.selectbox(
            "Raça/Cor",
            options=raca_options,
            index=0
        )
    else:
        raca = "Todas"  # Valor padrão se não existir informação racial
        
    # Filtro por grupo diagnóstico em árvore (hierárquico)
    # Grupo Diagnóstico
    diag_grupo_options = ["Todos"] + sorted(df['def_diag_princ_grupo'].dropna().unique().tolist())
    diag_grupo = st.sidebar.selectbox(
        "Grupo Diagnóstico",
        options=diag_grupo_options,
        index=0
    )
    diag_grupo = None if diag_grupo == "Todos" else diag_grupo
    
    # Filtro por Categoria - depende do Grupo selecionado
    if diag_grupo is None:
        # Se nenhum grupo for selecionado, não pode selecionar categoria
        st.sidebar.text("Selecione um Grupo Diagnóstico para filtrar por categoria")
        diag_categoria = None
    else:
        # Se um grupo for selecionado, mostra as categorias correspondentes
        if 'def_diag_princ_cat' in df.columns:
            categorias_filtradas = sorted(df[df['def_diag_princ_grupo'] == diag_grupo]['def_diag_princ_cat'].dropna().unique().tolist())
            diag_categoria_options = ["Todas"] + categorias_filtradas
            diag_categoria = st.sidebar.selectbox(
                "Categoria Diagnóstica",
                options=diag_categoria_options,
                index=0
            )
            diag_categoria = None if diag_categoria == "Todas" else diag_categoria
        else:
            st.sidebar.text("Dados de categorias diagnósticas não disponíveis")
            diag_categoria = None
    
    # Filtro por Subcategoria - depende da Categoria selecionada
    if diag_categoria is None:
        # Se nenhuma categoria for selecionada, não pode selecionar subcategoria
        if diag_grupo is not None:
            st.sidebar.text("Selecione uma Categoria Diagnóstica para filtrar por subcategoria")
        else:
            st.sidebar.text("Selecione Grupo e Categoria para filtrar por subcategoria")
        diag_subcategoria = None
    else:
        # Se uma categoria for selecionada, mostra as subcategorias correspondentes
        if 'def_diag_princ_subcat' in df.columns:
            subcategorias_filtradas = sorted(df[df['def_diag_princ_cat'] == diag_categoria]['def_diag_princ_subcat'].dropna().unique().tolist())
            diag_subcategoria_options = ["Todas"] + subcategorias_filtradas
            diag_subcategoria = st.sidebar.selectbox(
                "Subcategoria Diagnóstica",
                options=diag_subcategoria_options,
                index=0
            )
            diag_subcategoria = None if diag_subcategoria == "Todas" else diag_subcategoria
        else:
            st.sidebar.text("Dados de subcategorias diagnósticas não disponíveis")
            diag_subcategoria = None
    
    # Aplicar filtros
    filtered_df = df.copy()
    
    # Filtrar por ano
    filtered_df = filtered_df[
        (filtered_df['ANO_CMPT'] >= year_range[0]) & 
        (filtered_df['ANO_CMPT'] <= year_range[1])
    ]
    
    # Filtrar por estado
    if estado:
        filtered_df = filtered_df[filtered_df['res_CODIGO_UF'].astype(str) == estado]
    
    # Filtrar por município - NÃO APLICAR este filtro para análise IDSC x indicadores
    # if codigo_municipio:
    #    filtered_df = filtered_df[filtered_df['MUNIC_RES'].astype(str) == codigo_municipio]
    
    # Filtrar por sexo
    if sexo != "Todos":
        if sexo == "Masculino":
            filtered_df = filtered_df[filtered_df['SEXO'] == 1]
        elif sexo == "Feminino":
            filtered_df = filtered_df[filtered_df['SEXO'] == 3]
    
    # Filtrar por faixa etária
    if faixa_etaria != "Todas":
        age_ranges = {
            '0-4': (0, 4),
            '5-9': (5, 9),
            '10-14': (10, 14),
            '15-19': (15, 19),
            '20-24': (20, 24),
            '25-29': (25, 29),
            '30-34': (30, 34),
            '35-39': (35, 39),
            '40-44': (40, 44),
            '45-49': (45, 49),
            '50-54': (50, 54),
            '55-59': (55, 59),
            '60-64': (60, 64),
            '65-69': (65, 69),
            '70-74': (70, 74),
            '75-79': (75, 79),
            '80-84': (80, 84),
            '85-89': (85, 89),
            '90-94': (90, 94),
            '95-99': (95, 99),
            '100+': (100, float('inf'))
        }
        age_min, age_max = age_ranges[faixa_etaria]
        filtered_df = filtered_df[(filtered_df['IDADE'] >= age_min) & (filtered_df['IDADE'] <= age_max)]
    
    # Filtrar por raça/cor considerando a opção Raça/Cor 2
    if 'RACA_COR' in df.columns and raca != "Todas":
        if raca == "Negra" and usar_raca_cor2:
            # Para Negra em Raça/Cor 2, incluir Preta e Parda
            if 'RACA_COR_DESC' in df.columns:
                filtered_df = filtered_df[filtered_df['RACA_COR_DESC'].isin(["Preta", "Parda"])]
            else:
                # Se não houver descrições, usar códigos 2 (Preta) e 3 (Parda)
                filtered_df = filtered_df[filtered_df['RACA_COR'].isin([2, 3])]
        else:
            # Para outras raças ou modo tradicional
            if 'RACA_COR_DESC' in df.columns:
                filtered_df = filtered_df[filtered_df['RACA_COR_DESC'] == raca]
            else:
                # Encontrar o código correspondente à descrição
                race_mapping_inv = {
                    'Branca': 1,
                    'Preta': 2,
                    'Parda': 3,
                    'Amarela': 4,
                    'Indígena': 5,
                    'Sem informação': 9
                }
                race_code = race_mapping_inv.get(raca)
                if race_code:
                    filtered_df = filtered_df[filtered_df['RACA_COR'] == race_code]
                else:
                    # Tentar converter diretamente se não for um dos valores mapeados
                    try:
                        race_code = int(raca)
                        filtered_df = filtered_df[filtered_df['RACA_COR'] == race_code]
                    except:
                        pass
    elif 'def_raca_cor' in df.columns and raca != "Todas":
        if raca == "Negra" and usar_raca_cor2:
            filtered_df = filtered_df[filtered_df['def_raca_cor'].isin(["Preta", "Parda"])]
        else:
            filtered_df = filtered_df[filtered_df['def_raca_cor'] == raca]
    
    # Filtrar por grupo diagnóstico
    if diag_grupo is not None:
        filtered_df = filtered_df[filtered_df['def_diag_princ_grupo'] == diag_grupo]
    
    # Filtrar por categoria diagnóstica
    if diag_categoria is not None:
        filtered_df = filtered_df[filtered_df['def_diag_princ_cat'] == diag_categoria]
    
    # Filtrar por subcategoria diagnóstica
    if diag_subcategoria is not None:
        filtered_df = filtered_df[filtered_df['def_diag_princ_subcat'] == diag_subcategoria]
    
    # Implement a safer approach to working with filtered data
    # Create a copy right after filtering to avoid SettingWithCopyWarning
    filtered_df = filtered_df.copy()
    
    # Calcular indicadores por município
    # Calcular indicadores por município com taxas por 100.000 habitantes
    taxa_mortalidade_df = calcular_taxa_mortalidade_municipio(filtered_df, usar_raca_cor2, estado, sexo, faixa_etaria, raca)
    tempo_permanencia_df = calcular_tempo_permanencia_municipio(filtered_df, usar_raca_cor2, estado, sexo, faixa_etaria, raca)
    
    # Contar internações por município
    internacoes_por_municipio = filtered_df.groupby('MUNIC_RES').size().reset_index(name='total_internacoes')
    
    # Adicionar dados de população e calcular taxa por 100.000 habitantes
    # Converter sexo para formato compatível com banco de dados
    sexo_db = None
    if sexo == "Masculino":
        sexo_db = "M"
    elif sexo == "Feminino":
        sexo_db = "F"

    # Obter dados de população para cada município
    internacoes_por_municipio['MUNIC_RES_STR'] = internacoes_por_municipio['MUNIC_RES'].astype(str)

    # Aplicar os dados de população e calcular taxas por 100k
    for idx, row in internacoes_por_municipio.iterrows():
        codigo_municipio = row['MUNIC_RES_STR']
        # Buscar população para este município específico
        df_pop = get_population_data(
            codigo_municipio=codigo_municipio,
            estado=estado,
            raca=raca,
            sexo=sexo_db,
            faixa_etaria=faixa_etaria,
            usar_raca_cor2=usar_raca_cor2
        )
        
        # Se encontrou dados de população, calcular a taxa
        if not df_pop.empty:
            # Usar o ano mais recente disponível
            pop_recente = df_pop.iloc[-1]['tam_pop']
            
            # Calcular taxa por 100.000 habitantes
            if pop_recente > 0:
                internacoes_por_municipio.at[idx, 'populacao'] = pop_recente
                internacoes_por_municipio.at[idx, 'taxa_internacoes_100k'] = (row['total_internacoes'] / pop_recente) * 100000
    
    # Adicionar valores IDSC aos dataframes de indicadores
    for df_indicador in [taxa_mortalidade_df, tempo_permanencia_df, internacoes_por_municipio]:
        df_indicador['MUNIC_RES_STR'] = df_indicador['MUNIC_RES'].astype(str)
        df_indicador['IDSC'] = df_indicador['MUNIC_RES_STR'].map(idsc_dict)
        df_indicador['Goal_1'] = df_indicador['MUNIC_RES_STR'].map(goal1_dict)
        df_indicador['Goal_3'] = df_indicador['MUNIC_RES_STR'].map(goal3_dict)
        df_indicador['Goal_5'] = df_indicador['MUNIC_RES_STR'].map(goal5_dict)
        df_indicador['Goal_10'] = df_indicador['MUNIC_RES_STR'].map(goal10_dict)
        df_indicador['Nome_Municipio'] = df_indicador['MUNIC_RES_STR'].map(municipios_dict)
        
        # Remover municípios sem IDSC
        df_indicador.dropna(subset=['IDSC'], inplace=True)

    # Main dashboard content with tabs
    tabs = st.tabs([
        "Taxa de Mortalidade x IDSC", 
        "Tempo de Permanência x IDSC", 
        "Internações x IDSC",
        "Taxa de Mortalidade x Goals",
        "Tempo de Permanência x Goals",
        "Internações x Goals"
    ])
    
    # Adicionar descrição dos Goals
    goal_descriptions = {
        "Goal 1": "Erradicação da Pobreza",
        "Goal 3": "Saúde e Bem-Estar",
        "Goal 5": "Igualdade de Gênero",
        "Goal 10": "Redução das Desigualdades"
    }
    
    # Tab 1: Taxa de Mortalidade x IDSC
    with tabs[0]:
        st.header("Relação entre Taxa de Mortalidade e IDSC")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, 
                                 municipios_dict, ano_idsc, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Verificar se há dados suficientes e se existem dados de taxa por 100k
        if len(taxa_mortalidade_df) < 5:
            st.warning("Dados insuficientes para análise. Tente ajustar os filtros.")
        elif 'taxa_mortalidade_100k' in taxa_mortalidade_df.columns and taxa_mortalidade_df['taxa_mortalidade_100k'].notna().sum() > 5:
            # Usar taxas por 100.000 habitantes
            st.success("Usando taxas por 100.000 habitantes para normalizar o efeito do tamanho da população.")
            
            # Remover outliers extremos (opcional)
            q_low = taxa_mortalidade_df['taxa_mortalidade_100k'].quantile(0.01)
            q_high = taxa_mortalidade_df['taxa_mortalidade_100k'].quantile(0.99)
            taxa_mortalidade_filtered = taxa_mortalidade_df[
                (taxa_mortalidade_df['taxa_mortalidade_100k'] >= q_low) & 
                (taxa_mortalidade_df['taxa_mortalidade_100k'] <= q_high) &
                (taxa_mortalidade_df['taxa_mortalidade_100k'].notna())
            ]
            
            # Usar taxa_internacoes_100k para o tamanho dos pontos, se disponível
            size_var = 'taxa_internacoes_100k' if 'taxa_internacoes_100k' in taxa_mortalidade_filtered.columns else 'total_internacoes'
            
            # Criar gráfico de dispersão
            fig = px.scatter(
                taxa_mortalidade_filtered,
                x='IDSC',
                y='taxa_mortalidade_100k',
                size=size_var,
                hover_name='Nome_Municipio',
                hover_data=['MUNIC_RES_STR', 'populacao', 'total_mortes', 'total_internacoes', 'taxa_mortalidade_100k', 'taxa_internacoes_100k'],
                title=f'Taxa de Mortalidade por 100.000 habitantes e IDSC ({ano_idsc})',
                labels={
                    'IDSC': f'IDSC-BR {ano_idsc}',
                    'taxa_mortalidade_100k': 'Taxa de Mortalidade (por 100.000 hab.)',
                    'taxa_internacoes_100k': 'Taxa de Internações (por 100.000 hab.)',
                    'total_internacoes': 'Total de Internações'
                },
                color='taxa_mortalidade_100k',
                color_continuous_scale=px.colors.sequential.Reds
            )
            
            # Adicionar linha de tendência
            fig.update_layout(
                xaxis_title=f'IDSC-BR {ano_idsc}',
                yaxis_title='Taxa de Mortalidade (por 100.000 hab.)',
                height=600
            )
            
            # Adicionar linha de tendência
            try:
                import numpy as np
                from scipy import stats
                
                # Calcular linha de tendência
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    taxa_mortalidade_filtered['IDSC'],
                    taxa_mortalidade_filtered['taxa_mortalidade_100k']
                )
                
                x_range = np.linspace(
                    taxa_mortalidade_filtered['IDSC'].min(),
                    taxa_mortalidade_filtered['IDSC'].max(),
                    100
                )
                y_range = slope * x_range + intercept
                
                fig.add_traces(
                    go.Scatter(
                        x=x_range, 
                        y=y_range, 
                        mode='lines', 
                        name=f'Tendência (R²={r_value**2:.3f})',
                        line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                    )
                )
                
                # Adicionar texto com coeficiente de correlação
                st.metric(
                    "Coeficiente de Correlação (R)",
                    f"{r_value:.3f}",
                    delta=f"R² = {r_value**2:.3f}"
                )
                
                if abs(r_value) < 0.3:
                    st.info("Correlação fraca entre IDSC e Taxa de Mortalidade por 100.000 habitantes")
                elif abs(r_value) < 0.7:
                    st.info("Correlação moderada entre IDSC e Taxa de Mortalidade por 100.000 habitantes")
                else:
                    st.info("Correlação forte entre IDSC e Taxa de Mortalidade por 100.000 habitantes")
                
                if p_value < 0.05:
                    st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                    de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                    de que existe uma relação linear entre o IDSC e a taxa de mortalidade por 100.000 habitantes.
                    """)
                else:
                    st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                    da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                    uma relação linear entre o IDSC e a taxa de mortalidade por 100.000 habitantes.
                    """)
                
                # Explicação sobre o coeficiente de correlação
                st.markdown(f"""
                **Sobre o coeficiente de correlação (R):**
                - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                que é previsível a partir da variável independente
                """)
            except Exception as e:
                st.warning(f"Não foi possível calcular a linha de tendência: {e}")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar dados em uma tabela
            st.subheader("Dados da Análise")
            display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'populacao', 'total_internacoes', 'taxa_internacoes_100k', 'total_mortes', 'taxa_mortalidade_100k', 'IDSC']
            st.dataframe(taxa_mortalidade_filtered[display_cols].sort_values('taxa_mortalidade_100k', ascending=False), use_container_width=True)
        else:
            # Fallback para o método original se não houver dados de população suficientes
            st.warning("Dados de população insuficientes para calcular taxas por 100.000 habitantes. Usando valores absolutos.")
            
            # Remover outliers extremos (opcional)
            q_low = taxa_mortalidade_df['taxa_mortalidade'].quantile(0.01)
            q_high = taxa_mortalidade_df['taxa_mortalidade'].quantile(0.99)
            taxa_mortalidade_filtered = taxa_mortalidade_df[
                (taxa_mortalidade_df['taxa_mortalidade'] >= q_low) & 
                (taxa_mortalidade_df['taxa_mortalidade'] <= q_high)
            ]
            
            # Criar gráfico de dispersão
            fig = px.scatter(
                taxa_mortalidade_filtered,
                x='IDSC',
                y='taxa_mortalidade',
                size='total_internacoes',
                hover_name='Nome_Municipio',
                hover_data=['MUNIC_RES_STR', 'total_mortes', 'total_internacoes'],
                title=f'Taxa de Mortalidade por IDSC ({ano_idsc})',
                labels={
                    'IDSC': f'IDSC-BR {ano_idsc}',
                    'taxa_mortalidade': 'Taxa de Mortalidade (%)',
                    'total_internacoes': 'Total de Internações'
                },
                color='taxa_mortalidade',
                color_continuous_scale=px.colors.sequential.Reds
            )
            
            # Adicionar linha de tendência
            fig.update_layout(
                xaxis_title=f'IDSC-BR {ano_idsc}',
                yaxis_title='Taxa de Mortalidade (%)',
                height=600
            )
            
            # Adicionar linha de tendência
            try:
                import numpy as np
                from scipy import stats
                
                # Calcular linha de tendência
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    taxa_mortalidade_filtered['IDSC'],
                    taxa_mortalidade_filtered['taxa_mortalidade']
                )
                
                x_range = np.linspace(
                    taxa_mortalidade_filtered['IDSC'].min(),
                    taxa_mortalidade_filtered['IDSC'].max(),
                    100
                )
                y_range = slope * x_range + intercept
                
                fig.add_traces(
                    go.Scatter(
                        x=x_range, 
                        y=y_range, 
                        mode='lines', 
                        name=f'Tendência (R²={r_value**2:.3f})',
                        line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                    )
                )
                
                # Adicionar texto com coeficiente de correlação
                st.metric(
                    "Coeficiente de Correlação (R)",
                    f"{r_value:.3f}",
                    delta=f"R² = {r_value**2:.3f}"
                )
                
                if abs(r_value) < 0.3:
                    st.info("Correlação fraca entre IDSC e Taxa de Mortalidade")
                elif abs(r_value) < 0.7:
                    st.info("Correlação moderada entre IDSC e Taxa de Mortalidade")
                else:
                    st.info("Correlação forte entre IDSC e Taxa de Mortalidade")
                
                if p_value < 0.05:
                    st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                    de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                    de que existe uma relação linear entre o IDSC e a taxa de mortalidade.
                    """)
                else:
                    st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                    da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                    uma relação linear entre o IDSC e a taxa de mortalidade.
                    """)
                
                # Explicação sobre o coeficiente de correlação
                st.markdown(f"""
                **Sobre o coeficiente de correlação (R):**
                - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                que é previsível a partir da variável independente
                """)
            except Exception as e:
                st.warning(f"Não foi possível calcular a linha de tendência: {e}")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar dados em uma tabela
            st.subheader("Dados da Análise")
            display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'total_internacoes', 'total_mortes', 'taxa_mortalidade', 'IDSC']
            st.dataframe(taxa_mortalidade_filtered[display_cols].sort_values('taxa_mortalidade', ascending=False), use_container_width=True)
    
    # Tab 2: Tempo de Permanência x IDSC
    with tabs[1]:
        st.header("Relação entre Tempo de Permanência e IDSC")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, 
                                 municipios_dict, ano_idsc, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Verificar se há dados suficientes e se existem dados de taxa por 100k
        if len(tempo_permanencia_df) < 5:
            st.warning("Dados insuficientes para análise. Tente ajustar os filtros.")
        elif 'taxa_internacoes_100k' in tempo_permanencia_df.columns and tempo_permanencia_df['taxa_internacoes_100k'].notna().sum() > 5:
            # Usar taxas por 100.000 habitantes
            st.success("Usando taxas por 100.000 habitantes para normalizar o efeito do tamanho da população.")
            
            # Remover outliers extremos (opcional)
            q_low = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.01)
            q_high = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.99)
            tempo_permanencia_filtered = tempo_permanencia_df[
                (tempo_permanencia_df['tempo_medio_permanencia'] >= q_low) & 
                (tempo_permanencia_df['tempo_medio_permanencia'] <= q_high) &
                (tempo_permanencia_df['taxa_internacoes_100k'].notna())
            ]
            
            # Criar gráfico de dispersão
            fig = px.scatter(
                tempo_permanencia_filtered,
                x='IDSC',
                y='tempo_medio_permanencia',
                size='taxa_internacoes_100k',
                hover_name='Nome_Municipio',
                hover_data=['MUNIC_RES_STR', 'populacao', 'total_internacoes', 'taxa_internacoes_100k'],
                title=f'Tempo Médio de Permanência por IDSC ({ano_idsc})',
                labels={
                    'IDSC': f'IDSC-BR {ano_idsc}',
                    'tempo_medio_permanencia': 'Tempo Médio de Permanência (dias)',
                    'taxa_internacoes_100k': 'Taxa de Internações (por 100.000 hab.)'
                },
                color='tempo_medio_permanencia',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            # Configurar layout
            fig.update_layout(
                xaxis_title=f'IDSC-BR {ano_idsc}',
                yaxis_title='Tempo Médio de Permanência (dias)',
                height=600
            )
            
            # Adicionar linha de tendência
            try:
                import numpy as np
                from scipy import stats
                
                # Calcular linha de tendência
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    tempo_permanencia_filtered['IDSC'],
                    tempo_permanencia_filtered['tempo_medio_permanencia']
                )
                
                x_range = np.linspace(
                    tempo_permanencia_filtered['IDSC'].min(),
                    tempo_permanencia_filtered['IDSC'].max(),
                    100
                )
                y_range = slope * x_range + intercept
                
                fig.add_traces(
                    go.Scatter(
                        x=x_range, 
                        y=y_range, 
                        mode='lines', 
                        name=f'Tendência (R²={r_value**2:.3f})',
                        line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                    )
                )
                
                # Adicionar texto com coeficiente de correlação
                st.metric(
                    "Coeficiente de Correlação (R)",
                    f"{r_value:.3f}",
                    delta=f"R² = {r_value**2:.3f}"
                )
                
                if abs(r_value) < 0.3:
                    st.info("Correlação fraca entre IDSC e Tempo de Permanência")
                elif abs(r_value) < 0.7:
                    st.info("Correlação moderada entre IDSC e Tempo de Permanência")
                else:
                    st.info("Correlação forte entre IDSC e Tempo de Permanência")
                
                if p_value < 0.05:
                    st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                    de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                    de que existe uma relação linear entre o IDSC e o tempo médio de permanência.
                    """)
                else:
                    st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                    da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                    uma relação linear entre o IDSC e o tempo médio de permanência.
                    """)
                
                # Explicação sobre o coeficiente de correlação
                st.markdown(f"""
                **Sobre o coeficiente de correlação (R):**
                - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                que é previsível a partir da variável independente
                """)
            except Exception as e:
                st.warning(f"Não foi possível calcular a linha de tendência: {e}")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar dados em uma tabela
            st.subheader("Dados da Análise")
            display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'populacao', 'total_internacoes', 'taxa_internacoes_100k', 'tempo_medio_permanencia', 'IDSC']
            st.dataframe(tempo_permanencia_filtered[display_cols].sort_values('tempo_medio_permanencia', ascending=False), use_container_width=True)
        else:
            # Fallback para o método original se não houver dados de população suficientes
            st.warning("Dados de população insuficientes para calcular taxas por 100.000 habitantes. Usando valores absolutos.")
            
            # Remover outliers extremos (opcional)
            q_low = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.01)
            q_high = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.99)
            tempo_permanencia_filtered = tempo_permanencia_df[
                (tempo_permanencia_df['tempo_medio_permanencia'] >= q_low) & 
                (tempo_permanencia_df['tempo_medio_permanencia'] <= q_high)
            ]
            
            # Criar gráfico de dispersão
            fig = px.scatter(
                tempo_permanencia_filtered,
                x='IDSC',
                y='tempo_medio_permanencia',
                size='total_internacoes',
                hover_name='Nome_Municipio',
                hover_data=['MUNIC_RES_STR', 'total_internacoes'],
                title=f'Tempo Médio de Permanência por IDSC ({ano_idsc})',
                labels={
                    'IDSC': f'IDSC-BR {ano_idsc}',
                    'tempo_medio_permanencia': 'Tempo Médio de Permanência (dias)',
                    'total_internacoes': 'Total de Internações'
                },
                color='tempo_medio_permanencia',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            # Configurar layout
            fig.update_layout(
                xaxis_title=f'IDSC-BR {ano_idsc}',
                yaxis_title='Tempo Médio de Permanência (dias)',
                height=600
            )
            
            # Adicionar linha de tendência
            try:
                import numpy as np
                from scipy import stats
                
                # Calcular linha de tendência
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    tempo_permanencia_filtered['IDSC'],
                    tempo_permanencia_filtered['tempo_medio_permanencia']
                )
                
                x_range = np.linspace(
                    tempo_permanencia_filtered['IDSC'].min(),
                    tempo_permanencia_filtered['IDSC'].max(),
                    100
                )
                y_range = slope * x_range + intercept
                
                fig.add_traces(
                    go.Scatter(
                        x=x_range, 
                        y=y_range, 
                        mode='lines', 
                        name=f'Tendência (R²={r_value**2:.3f})',
                        line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                    )
                )
                
                # Adicionar texto com coeficiente de correlação
                st.metric(
                    "Coeficiente de Correlação (R)",
                    f"{r_value:.3f}",
                    delta=f"R² = {r_value**2:.3f}"
                )
                
                if abs(r_value) < 0.3:
                    st.info("Correlação fraca entre IDSC e Tempo de Permanência")
                elif abs(r_value) < 0.7:
                    st.info("Correlação moderada entre IDSC e Tempo de Permanência")
                else:
                    st.info("Correlação forte entre IDSC e Tempo de Permanência")
                
                if p_value < 0.05:
                    st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                    de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                    de que existe uma relação linear entre o IDSC e o tempo médio de permanência.
                    """)
                else:
                    st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                    da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                    uma relação linear entre o IDSC e o tempo médio de permanência.
                    """)
                
                # Explicação sobre o coeficiente de correlação
                st.markdown(f"""
                **Sobre o coeficiente de correlação (R):**
                - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                que é previsível a partir da variável independente
                """)
            except Exception as e:
                st.warning(f"Não foi possível calcular a linha de tendência: {e}")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar dados em uma tabela
            st.subheader("Dados da Análise")
            display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'total_internacoes', 'tempo_medio_permanencia', 'IDSC']
            st.dataframe(tempo_permanencia_filtered[display_cols].sort_values('tempo_medio_permanencia', ascending=False), use_container_width=True)

    # Tab 3: Internações x IDSC
    with tabs[2]:
        st.header("Relação entre Internações e IDSC")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, 
                                 municipios_dict, ano_idsc, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Verificar se há dados suficientes e se existem dados de taxa por 100k
        if len(internacoes_por_municipio) < 5:
            st.warning("Dados insuficientes para análise. Tente ajustar os filtros.")
        elif 'taxa_internacoes_100k' in internacoes_por_municipio.columns and internacoes_por_municipio['taxa_internacoes_100k'].notna().sum() > 5:
            # Usar taxas por 100.000 habitantes
            st.success("Usando taxas por 100.000 habitantes para normalizar o efeito do tamanho da população.")
            
            # Remover outliers extremos (opcional)
            q_low = internacoes_por_municipio['taxa_internacoes_100k'].quantile(0.01)
            q_high = internacoes_por_municipio['taxa_internacoes_100k'].quantile(0.99)
            internacoes_filtered = internacoes_por_municipio[
                (internacoes_por_municipio['taxa_internacoes_100k'] >= q_low) & 
                (internacoes_por_municipio['taxa_internacoes_100k'] <= q_high) &
                (internacoes_por_municipio['taxa_internacoes_100k'].notna())
            ]
            
            # Criar gráfico de dispersão
            fig = px.scatter(
                internacoes_filtered,
                x='IDSC',
                y='taxa_internacoes_100k',
                size='taxa_internacoes_100k',
                hover_name='Nome_Municipio',
                hover_data=['MUNIC_RES_STR', 'populacao', 'total_internacoes', 'taxa_internacoes_100k'],
                title=f'Taxa de Internações por 100.000 habitantes e IDSC ({ano_idsc})',
                labels={
                    'IDSC': f'IDSC-BR {ano_idsc}',
                    'taxa_internacoes_100k': 'Taxa de Internações (por 100.000 hab.)'
                },
                color='taxa_internacoes_100k',
                color_continuous_scale=px.colors.sequential.Blues
            )
            
            # Configurar layout
            fig.update_layout(
                xaxis_title=f'IDSC-BR {ano_idsc}',
                yaxis_title='Taxa de Internações (por 100.000 hab.)',
                height=600
            )
            
            # Adicionar linha de tendência
            try:
                import numpy as np
                from scipy import stats
                
                # Calcular linha de tendência
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    internacoes_filtered['IDSC'],
                    internacoes_filtered['taxa_internacoes_100k']
                )
                
                x_range = np.linspace(
                    internacoes_filtered['IDSC'].min(),
                    internacoes_filtered['IDSC'].max(),
                    100
                )
                y_range = slope * x_range + intercept
                
                fig.add_traces(
                    go.Scatter(
                        x=x_range, 
                        y=y_range, 
                        mode='lines', 
                        name=f'Tendência (R²={r_value**2:.3f})',
                        line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                    )
                )
                
                # Adicionar texto com coeficiente de correlação
                st.metric(
                    "Coeficiente de Correlação (R)",
                    f"{r_value:.3f}",
                    delta=f"R² = {r_value**2:.3f}"
                )
                
                if abs(r_value) < 0.3:
                    st.info("Correlação fraca entre IDSC e Taxa de Internações por 100.000 habitantes")
                elif abs(r_value) < 0.7:
                    st.info("Correlação moderada entre IDSC e Taxa de Internações por 100.000 habitantes")
                else:
                    st.info("Correlação forte entre IDSC e Taxa de Internações por 100.000 habitantes")
                
                if p_value < 0.05:
                    st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                    de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                    de que existe uma relação linear entre o IDSC e a taxa de internações por 100.000 habitantes.
                    """)
                else:
                    st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                    da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                    uma relação linear entre o IDSC e a taxa de internações por 100.000 habitantes.
                    """)
                
                # Explicação sobre o coeficiente de correlação
                st.markdown(f"""
                **Sobre o coeficiente de correlação (R):**
                - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                que é previsível a partir da variável independente
                """)
            except Exception as e:
                st.warning(f"Não foi possível calcular a linha de tendência: {e}")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar dados em uma tabela
            st.subheader("Dados da Análise")
            display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'populacao', 'total_internacoes', 'taxa_internacoes_100k', 'IDSC']
            st.dataframe(internacoes_filtered[display_cols].sort_values('taxa_internacoes_100k', ascending=False), use_container_width=True)
        else:
            # Fallback para o método original se não houver dados de população suficientes
            st.warning("Dados de população insuficientes para calcular taxas por 100.000 habitantes. Usando valores absolutos.")
            
            # Remover outliers extremos (opcional)
            q_low = internacoes_por_municipio['total_internacoes'].quantile(0.01)
            q_high = internacoes_por_municipio['total_internacoes'].quantile(0.99)
            internacoes_filtered = internacoes_por_municipio[
                (internacoes_por_municipio['total_internacoes'] >= q_low) & 
                (internacoes_por_municipio['total_internacoes'] <= q_high)
            ]
            
            # Criar gráfico de dispersão
            fig = px.scatter(
                internacoes_filtered,
                x='IDSC',
                y='total_internacoes',
                size='total_internacoes',
                hover_name='Nome_Municipio',
                hover_data=['MUNIC_RES_STR'],
                title=f'Número de Internações por IDSC ({ano_idsc})',
                labels={
                    'IDSC': f'IDSC-BR {ano_idsc}',
                    'total_internacoes': 'Número de Internações'
                },
                color='total_internacoes',
                color_continuous_scale=px.colors.sequential.Blues
            )
            
            # Configurar layout
            fig.update_layout(
                xaxis_title=f'IDSC-BR {ano_idsc}',
                yaxis_title='Número de Internações',
                height=600
            )
            
            # Adicionar linha de tendência
            try:
                import numpy as np
                from scipy import stats
                
                # Calcular linha de tendência
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    internacoes_filtered['IDSC'],
                    internacoes_filtered['total_internacoes']
                )
                
                x_range = np.linspace(
                    internacoes_filtered['IDSC'].min(),
                    internacoes_filtered['IDSC'].max(),
                    100
                )
                y_range = slope * x_range + intercept
                
                fig.add_traces(
                    go.Scatter(
                        x=x_range, 
                        y=y_range, 
                        mode='lines', 
                        name=f'Tendência (R²={r_value**2:.3f})',
                        line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                    )
                )
                
                # Adicionar texto com coeficiente de correlação
                st.metric(
                    "Coeficiente de Correlação (R)",
                    f"{r_value:.3f}",
                    delta=f"R² = {r_value**2:.3f}"
                )
                
                if abs(r_value) < 0.3:
                    st.info("Correlação fraca entre IDSC e Número de Internações")
                elif abs(r_value) < 0.7:
                    st.info("Correlação moderada entre IDSC e Número de Internações")
                else:
                    st.info("Correlação forte entre IDSC e Número de Internações")
                
                if p_value < 0.05:
                    st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                    de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                    de que existe uma relação linear entre o IDSC e o número de internações.
                    """)
                else:
                    st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                    st.markdown("""
                    **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                    da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                    uma relação linear entre o IDSC e o número de internações.
                    """)
                
                # Explicação sobre o coeficiente de correlação
                st.markdown(f"""
                **Sobre o coeficiente de correlação (R):**
                - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                que é previsível a partir da variável independente
                """)
            except Exception as e:
                st.warning(f"Não foi possível calcular a linha de tendência: {e}")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar dados em uma tabela
            st.subheader("Dados da Análise")
            display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'total_internacoes', 'IDSC']
            st.dataframe(internacoes_filtered[display_cols].sort_values('total_internacoes', ascending=False), use_container_width=True)

    # Tab 4: Taxa de Mortalidade x Goals
    with tabs[3]:
        st.header("Relação entre Taxa de Mortalidade e Goals")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, 
                                 municipios_dict, ano_idsc, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Verificar se há dados de Goals disponíveis
        goal_options = {}
        if goal1_dict:
            goal_options["Goal 1"] = {"column": "Goal_1", "description": goal_descriptions["Goal 1"]}
        if goal3_dict:
            goal_options["Goal 3"] = {"column": "Goal_3", "description": goal_descriptions["Goal 3"]}
        if goal5_dict:
            goal_options["Goal 5"] = {"column": "Goal_5", "description": goal_descriptions["Goal 5"]}
        if goal10_dict:
            goal_options["Goal 10"] = {"column": "Goal_10", "description": goal_descriptions["Goal 10"]}
        
        if not goal_options:
            st.warning(f"Não foram encontrados dados de Goals para o ano {ano_idsc}. Por favor, selecione outro ano ou verifique os dados.")
        else:
            # Seletor de Goal
            selected_goal = st.selectbox(
                "Selecione o Goal para análise:",
                options=list(goal_options.keys()),
                format_func=lambda x: f"{x} - {goal_options[x]['description']}",
                index=0,
                key="taxa_mortalidade_goal"
            )
            
            # Obter a coluna correspondente ao Goal selecionado
            goal_column = goal_options[selected_goal]["column"]
            
            # Verificar se há dados suficientes
            if len(taxa_mortalidade_df) < 5:
                st.warning("Dados insuficientes para análise. Tente ajustar os filtros.")
            # Verificar se existem dados de taxa por 100k
            elif 'taxa_mortalidade_100k' in taxa_mortalidade_df.columns and taxa_mortalidade_df['taxa_mortalidade_100k'].notna().sum() > 5:
                # Usar taxas por 100.000 habitantes
                st.success("Usando taxas por 100.000 habitantes para normalizar o efeito do tamanho da população.")
                
                # Remover outliers extremos (opcional)
                q_low = taxa_mortalidade_df['taxa_mortalidade_100k'].quantile(0.01)
                q_high = taxa_mortalidade_df['taxa_mortalidade_100k'].quantile(0.99)
                taxa_mortalidade_filtered = taxa_mortalidade_df[
                    (taxa_mortalidade_df['taxa_mortalidade_100k'] >= q_low) & 
                    (taxa_mortalidade_df['taxa_mortalidade_100k'] <= q_high) &
                    (taxa_mortalidade_df['taxa_mortalidade_100k'].notna())
                ]
                
                # Filtrar municípios sem o Goal selecionado
                taxa_mortalidade_filtered = taxa_mortalidade_filtered.dropna(subset=[goal_column])
                
                if len(taxa_mortalidade_filtered) < 5:
                    st.warning(f"Dados insuficientes para o {selected_goal}. Tente outro Goal ou ajuste os filtros.")
                else:
                    # Usar taxa_internacoes_100k para o tamanho dos pontos, se disponível
                    size_var = 'taxa_internacoes_100k' if 'taxa_internacoes_100k' in taxa_mortalidade_filtered.columns else 'total_internacoes'
                    
                    # Criar gráfico de dispersão
                    fig = px.scatter(
                        taxa_mortalidade_filtered,
                        x=goal_column,
                        y='taxa_mortalidade_100k',
                        size=size_var,
                        hover_name='Nome_Municipio',
                        hover_data=['MUNIC_RES_STR', 'populacao', 'total_mortes', 'total_internacoes', 'taxa_mortalidade_100k', 'taxa_internacoes_100k'],
                        title=f'Taxa de Mortalidade por 100.000 habitantes e {selected_goal} ({ano_idsc})',
                        labels={
                            goal_column: selected_goal,
                            'taxa_mortalidade_100k': 'Taxa de Mortalidade (por 100.000 hab.)',
                            'taxa_internacoes_100k': 'Taxa de Internações (por 100.000 hab.)',
                            'total_internacoes': 'Total de Internações'
                        },
                        color='taxa_mortalidade_100k',
                        color_continuous_scale=px.colors.sequential.Reds
                    )
                    
                    # Adicionar linha de tendência
                    fig.update_layout(
                        xaxis_title=f'{selected_goal}',
                        yaxis_title='Taxa de Mortalidade (por 100.000 hab.)',
                        height=600
                    )
                    
                    # Adicionar informação sobre o Goal
                    st.markdown(f"**{selected_goal}**: {goal_options[selected_goal]['description']}")
                    
                    # Adicionar linha de tendência
                    try:
                        import numpy as np
                        from scipy import stats
                        
                        # Calcular linha de tendência
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            taxa_mortalidade_filtered[goal_column],
                            taxa_mortalidade_filtered['taxa_mortalidade_100k']
                        )
                        
                        x_range = np.linspace(
                            taxa_mortalidade_filtered[goal_column].min(),
                            taxa_mortalidade_filtered[goal_column].max(),
                            100
                        )
                        y_range = slope * x_range + intercept
                        
                        fig.add_traces(
                            go.Scatter(
                                x=x_range, 
                                y=y_range, 
                                mode='lines', 
                                name=f'Tendência (R²={r_value**2:.3f})',
                                line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                            )
                        )
                        
                        # Adicionar texto com coeficiente de correlação
                        st.metric(
                            "Coeficiente de Correlação (R)",
                            f"{r_value:.3f}",
                            delta=f"R² = {r_value**2:.3f}"
                        )
                        
                        if abs(r_value) < 0.3:
                            st.info(f"Correlação fraca entre {selected_goal} e Taxa de Mortalidade por 100.000 habitantes")
                        elif abs(r_value) < 0.7:
                            st.info(f"Correlação moderada entre {selected_goal} e Taxa de Mortalidade por 100.000 habitantes")
                        else:
                            st.info(f"Correlação forte entre {selected_goal} e Taxa de Mortalidade por 100.000 habitantes")
                        
                        if p_value < 0.05:
                            st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                            de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                            de que existe uma relação linear entre o {selected_goal} e a taxa de mortalidade por 100.000 habitantes.
                            """)
                        else:
                            st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                            da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                            uma relação linear entre o {selected_goal} e a taxa de mortalidade por 100.000 habitantes.
                            """)
                        
                        # Explicação sobre o coeficiente de correlação
                        st.markdown(f"""
                        **Sobre o coeficiente de correlação (R):**
                        - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                        - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                        que é previsível a partir da variável independente
                        """)
                    except Exception as e:
                        st.warning(f"Não foi possível calcular a linha de tendência: {e}")
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar dados em uma tabela
                    st.subheader("Dados da Análise")
                    display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'populacao', 'total_internacoes', 'taxa_internacoes_100k', 'total_mortes', 'taxa_mortalidade_100k', goal_column]
                    st.dataframe(taxa_mortalidade_filtered[display_cols].sort_values('taxa_mortalidade_100k', ascending=False), use_container_width=True)
            else:
                # Fallback para o método original se não houver dados de população suficientes
                st.warning("Dados de população insuficientes para calcular taxas por 100.000 habitantes. Usando valores absolutos.")
                
                # Remover outliers extremos (opcional)
                q_low = taxa_mortalidade_df['taxa_mortalidade'].quantile(0.01)
                q_high = taxa_mortalidade_df['taxa_mortalidade'].quantile(0.99)
                taxa_mortalidade_filtered = taxa_mortalidade_df[
                    (taxa_mortalidade_df['taxa_mortalidade'] >= q_low) & 
                    (taxa_mortalidade_df['taxa_mortalidade'] <= q_high)
                ]
                
                # Filtrar municípios sem o Goal selecionado
                taxa_mortalidade_filtered = taxa_mortalidade_filtered.dropna(subset=[goal_column])
                
                if len(taxa_mortalidade_filtered) < 5:
                    st.warning(f"Dados insuficientes para o {selected_goal}. Tente outro Goal ou ajuste os filtros.")
                else:
                    # Criar gráfico de dispersão
                    fig = px.scatter(
                        taxa_mortalidade_filtered,
                        x=goal_column,
                        y='taxa_mortalidade',
                        size='total_internacoes',
                        hover_name='Nome_Municipio',
                        hover_data=['MUNIC_RES_STR', 'total_mortes', 'total_internacoes'],
                        title=f'Taxa de Mortalidade por {selected_goal} ({ano_idsc})',
                        labels={
                            goal_column: selected_goal,
                            'taxa_mortalidade': 'Taxa de Mortalidade (%)',
                            'total_internacoes': 'Total de Internações'
                        },
                        color='taxa_mortalidade',
                        color_continuous_scale=px.colors.sequential.Reds
                    )
                    
                    # Adicionar linha de tendência
                    fig.update_layout(
                        xaxis_title=f'{selected_goal}',
                        yaxis_title='Taxa de Mortalidade (%)',
                        height=600
                    )
                    
                    # Adicionar informação sobre o Goal
                    st.markdown(f"**{selected_goal}**: {goal_options[selected_goal]['description']}")
                    
                    # Adicionar linha de tendência
                    try:
                        import numpy as np
                        from scipy import stats
                        
                        # Calcular linha de tendência
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            taxa_mortalidade_filtered[goal_column],
                            taxa_mortalidade_filtered['taxa_mortalidade']
                        )
                        
                        x_range = np.linspace(
                            taxa_mortalidade_filtered[goal_column].min(),
                            taxa_mortalidade_filtered[goal_column].max(),
                            100
                        )
                        y_range = slope * x_range + intercept
                        
                        fig.add_traces(
                            go.Scatter(
                                x=x_range, 
                                y=y_range, 
                                mode='lines', 
                                name=f'Tendência (R²={r_value**2:.3f})',
                                line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                            )
                        )
                        
                        # Adicionar texto com coeficiente de correlação
                        st.metric(
                            "Coeficiente de Correlação (R)",
                            f"{r_value:.3f}",
                            delta=f"R² = {r_value**2:.3f}"
                        )
                        
                        if abs(r_value) < 0.3:
                            st.info(f"Correlação fraca entre {selected_goal} e Taxa de Mortalidade")
                        elif abs(r_value) < 0.7:
                            st.info(f"Correlação moderada entre {selected_goal} e Taxa de Mortalidade")
                        else:
                            st.info(f"Correlação forte entre {selected_goal} e Taxa de Mortalidade")
                        
                        if p_value < 0.05:
                            st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                            de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                            de que existe uma relação linear entre o {selected_goal} e a taxa de mortalidade.
                            """)
                        else:
                            st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                            da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                            uma relação linear entre o {selected_goal} e a taxa de mortalidade.
                            """)
                        
                        # Explicação sobre o coeficiente de correlação
                        st.markdown(f"""
                        **Sobre o coeficiente de correlação (R):**
                        - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                        - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                        que é previsível a partir da variável independente
                        """)
                    except Exception as e:
                        st.warning(f"Não foi possível calcular a linha de tendência: {e}")
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar dados em uma tabela
                    st.subheader("Dados da Análise")
                    display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'total_internacoes', 'total_mortes', 'taxa_mortalidade', goal_column]
                    st.dataframe(taxa_mortalidade_filtered[display_cols].sort_values('taxa_mortalidade', ascending=False), use_container_width=True)

    # Tab 5: Tempo de Permanência x Goals
    with tabs[4]:
        st.header("Relação entre Tempo de Permanência e Goals")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, 
                                 municipios_dict, ano_idsc, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Verificar se há dados de Goals disponíveis
        if not goal_options:
            st.warning(f"Não foram encontrados dados de Goals para o ano {ano_idsc}. Por favor, selecione outro ano ou verifique os dados.")
        else:
            # Seletor de Goal
            selected_goal = st.selectbox(
                "Selecione o Goal para análise:",
                options=list(goal_options.keys()),
                format_func=lambda x: f"{x} - {goal_options[x]['description']}",
                index=0,
                key="tempo_permanencia_goal"
            )
            
            # Obter a coluna correspondente ao Goal selecionado
            goal_column = goal_options[selected_goal]["column"]
            
            # Verificar se há dados suficientes
            if len(tempo_permanencia_df) < 5:
                st.warning("Dados insuficientes para análise. Tente ajustar os filtros.")
            # Verificar se existem dados de taxa por 100k
            elif 'taxa_internacoes_100k' in tempo_permanencia_df.columns and tempo_permanencia_df['taxa_internacoes_100k'].notna().sum() > 5:
                # Usar taxas por 100.000 habitantes
                st.success("Usando taxas por 100.000 habitantes para normalizar o efeito do tamanho da população.")
                
                # Remover outliers extremos (opcional)
                q_low = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.01)
                q_high = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.99)
                tempo_permanencia_filtered = tempo_permanencia_df[
                    (tempo_permanencia_df['tempo_medio_permanencia'] >= q_low) & 
                    (tempo_permanencia_df['tempo_medio_permanencia'] <= q_high) &
                    (tempo_permanencia_df['taxa_internacoes_100k'].notna())
                ]
                
                # Filtrar municípios sem o Goal selecionado
                tempo_permanencia_filtered = tempo_permanencia_filtered.dropna(subset=[goal_column])
                
                if len(tempo_permanencia_filtered) < 5:
                    st.warning(f"Dados insuficientes para o {selected_goal}. Tente outro Goal ou ajuste os filtros.")
                else:
                    # Criar gráfico de dispersão
                    fig = px.scatter(
                        tempo_permanencia_filtered,
                        x=goal_column,
                        y='tempo_medio_permanencia',
                        size='taxa_internacoes_100k',
                        hover_name='Nome_Municipio',
                        hover_data=['MUNIC_RES_STR', 'populacao', 'total_internacoes', 'taxa_internacoes_100k'],
                        title=f'Tempo Médio de Permanência e {selected_goal} ({ano_idsc}) - Normalizado por 100.000 hab.',
                        labels={
                            goal_column: selected_goal,
                            'tempo_medio_permanencia': 'Tempo Médio de Permanência (dias)',
                            'taxa_internacoes_100k': 'Taxa de Internações (por 100.000 hab.)'
                        },
                        color='tempo_medio_permanencia',
                        color_continuous_scale=px.colors.sequential.Viridis
                    )
                    
                    # Configurar layout
                    fig.update_layout(
                        xaxis_title=f'{selected_goal}',
                        yaxis_title='Tempo Médio de Permanência (dias)',
                        height=600
                    )
                    
                    # Adicionar informação sobre o Goal
                    st.markdown(f"**{selected_goal}**: {goal_options[selected_goal]['description']}")
                    
                    # Adicionar linha de tendência
                    try:
                        import numpy as np
                        from scipy import stats
                        
                        # Calcular linha de tendência
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            tempo_permanencia_filtered[goal_column],
                            tempo_permanencia_filtered['tempo_medio_permanencia']
                        )
                        
                        x_range = np.linspace(
                            tempo_permanencia_filtered[goal_column].min(),
                            tempo_permanencia_filtered[goal_column].max(),
                            100
                        )
                        y_range = slope * x_range + intercept
                        
                        fig.add_traces(
                            go.Scatter(
                                x=x_range, 
                                y=y_range, 
                                mode='lines', 
                                name=f'Tendência (R²={r_value**2:.3f})',
                                line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                            )
                        )
                        
                        # Adicionar texto com coeficiente de correlação
                        st.metric(
                            "Coeficiente de Correlação (R)",
                            f"{r_value:.3f}",
                            delta=f"R² = {r_value**2:.3f}"
                        )
                        
                        if abs(r_value) < 0.3:
                            st.info(f"Correlação fraca entre {selected_goal} e Tempo de Permanência")
                        elif abs(r_value) < 0.7:
                            st.info(f"Correlação moderada entre {selected_goal} e Tempo de Permanência")
                        else:
                            st.info(f"Correlação forte entre {selected_goal} e Tempo de Permanência")
                        
                        if p_value < 0.05:
                            st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                            de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                            de que existe uma relação linear entre o {selected_goal} e o tempo médio de permanência.
                            """)
                        else:
                            st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                            da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                            uma relação linear entre o {selected_goal} e o tempo médio de permanência.
                            """)
                        
                        # Explicação sobre o coeficiente de correlação
                        st.markdown(f"""
                        **Sobre o coeficiente de correlação (R):**
                        - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                        - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                        que é previsível a partir da variável independente
                        """)
                    except Exception as e:
                        st.warning(f"Não foi possível calcular a linha de tendência: {e}")
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar dados em uma tabela
                    st.subheader("Dados da Análise")
                    display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'populacao', 'total_internacoes', 'taxa_internacoes_100k', 'tempo_medio_permanencia', goal_column]
                    st.dataframe(tempo_permanencia_filtered[display_cols].sort_values('tempo_medio_permanencia', ascending=False), use_container_width=True)
            else:
                # Fallback para o método original se não houver dados de população suficientes
                st.warning("Dados de população insuficientes para calcular taxas por 100.000 habitantes. Usando valores absolutos.")
                
                # Remover outliers extremos (opcional)
                q_low = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.01)
                q_high = tempo_permanencia_df['tempo_medio_permanencia'].quantile(0.99)
                tempo_permanencia_filtered = tempo_permanencia_df[
                    (tempo_permanencia_df['tempo_medio_permanencia'] >= q_low) & 
                    (tempo_permanencia_df['tempo_medio_permanencia'] <= q_high)
                ]
                
                # Filtrar municípios sem o Goal selecionado
                tempo_permanencia_filtered = tempo_permanencia_filtered.dropna(subset=[goal_column])
                
                if len(tempo_permanencia_filtered) < 5:
                    st.warning(f"Dados insuficientes para o {selected_goal}. Tente outro Goal ou ajuste os filtros.")
                else:
                    # Criar gráfico de dispersão
                    fig = px.scatter(
                        tempo_permanencia_filtered,
                        x=goal_column,
                        y='tempo_medio_permanencia',
                        size='total_internacoes',
                        hover_name='Nome_Municipio',
                        hover_data=['MUNIC_RES_STR', 'total_internacoes'],
                        title=f'Tempo Médio de Permanência por {selected_goal} ({ano_idsc})',
                        labels={
                            goal_column: selected_goal,
                            'tempo_medio_permanencia': 'Tempo Médio de Permanência (dias)',
                            'total_internacoes': 'Total de Internações'
                        },
                        color='tempo_medio_permanencia',
                        color_continuous_scale=px.colors.sequential.Viridis
                    )
                    
                    # Configurar layout
                    fig.update_layout(
                        xaxis_title=f'{selected_goal}',
                        yaxis_title='Tempo Médio de Permanência (dias)',
                        height=600
                    )
                    
                    # Adicionar informação sobre o Goal
                    st.markdown(f"**{selected_goal}**: {goal_options[selected_goal]['description']}")
                    
                    # Adicionar linha de tendência
                    try:
                        import numpy as np
                        from scipy import stats
                        
                        # Calcular linha de tendência
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            tempo_permanencia_filtered[goal_column],
                            tempo_permanencia_filtered['tempo_medio_permanencia']
                        )
                        
                        x_range = np.linspace(
                            tempo_permanencia_filtered[goal_column].min(),
                            tempo_permanencia_filtered[goal_column].max(),
                            100
                        )
                        y_range = slope * x_range + intercept
                        
                        fig.add_traces(
                            go.Scatter(
                                x=x_range, 
                                y=y_range, 
                                mode='lines', 
                                name=f'Tendência (R²={r_value**2:.3f})',
                                line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                            )
                        )
                        
                        # Adicionar texto com coeficiente de correlação
                        st.metric(
                            "Coeficiente de Correlação (R)",
                            f"{r_value:.3f}",
                            delta=f"R² = {r_value**2:.3f}"
                        )
                        
                        if abs(r_value) < 0.3:
                            st.info(f"Correlação fraca entre {selected_goal} e Tempo de Permanência")
                        elif abs(r_value) < 0.7:
                            st.info(f"Correlação moderada entre {selected_goal} e Tempo de Permanência")
                        else:
                            st.info(f"Correlação forte entre {selected_goal} e Tempo de Permanência")
                        
                        if p_value < 0.05:
                            st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                            de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                            de que existe uma relação linear entre o {selected_goal} e o tempo médio de permanência.
                            """)
                        else:
                            st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                            da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                            uma relação linear entre o {selected_goal} e o tempo médio de permanência.
                            """)
                        
                        # Explicação sobre o coeficiente de correlação
                        st.markdown(f"""
                        **Sobre o coeficiente de correlação (R):**
                        - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                        - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                        que é previsível a partir da variável independente
                        """)
                    except Exception as e:
                        st.warning(f"Não foi possível calcular a linha de tendência: {e}")
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar dados em uma tabela
                    st.subheader("Dados da Análise")
                    display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'total_internacoes', 'tempo_medio_permanencia', goal_column]
                    st.dataframe(tempo_permanencia_filtered[display_cols].sort_values('tempo_medio_permanencia', ascending=False), use_container_width=True)

    # Tab 6: Internações x Goals
    with tabs[5]:
        st.header("Relação entre Internações e Goals")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, 
                                 municipios_dict, ano_idsc, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Verificar se há dados de Goals disponíveis
        if not goal_options:
            st.warning(f"Não foram encontrados dados de Goals para o ano {ano_idsc}. Por favor, selecione outro ano ou verifique os dados.")
        else:
            # Seletor de Goal
            selected_goal = st.selectbox(
                "Selecione o Goal para análise:",
                options=list(goal_options.keys()),
                format_func=lambda x: f"{x} - {goal_options[x]['description']}",
                index=0,
                key="internacoes_goal"
            )
            
            # Obter a coluna correspondente ao Goal selecionado
            goal_column = goal_options[selected_goal]["column"]
            
            # Verificar se há dados suficientes
            if len(internacoes_por_municipio) < 5:
                st.warning("Dados insuficientes para análise. Tente ajustar os filtros.")
            # Verificar se existem dados de taxa por 100k
            elif 'taxa_internacoes_100k' in internacoes_por_municipio.columns and internacoes_por_municipio['taxa_internacoes_100k'].notna().sum() > 5:
                # Usar taxas por 100.000 habitantes
                st.success("Usando taxas por 100.000 habitantes para normalizar o efeito do tamanho da população.")
                
                # Remover outliers extremos (opcional)
                q_low = internacoes_por_municipio['taxa_internacoes_100k'].quantile(0.01)
                q_high = internacoes_por_municipio['taxa_internacoes_100k'].quantile(0.99)
                internacoes_filtered = internacoes_por_municipio[
                    (internacoes_por_municipio['taxa_internacoes_100k'] >= q_low) & 
                    (internacoes_por_municipio['taxa_internacoes_100k'] <= q_high) &
                    (internacoes_por_municipio['taxa_internacoes_100k'].notna())
                ]
                
                # Filtrar municípios sem o Goal selecionado
                internacoes_filtered = internacoes_filtered.dropna(subset=[goal_column])
                
                if len(internacoes_filtered) < 5:
                    st.warning(f"Dados insuficientes para o {selected_goal}. Tente outro Goal ou ajuste os filtros.")
                else:
                    # Criar gráfico de dispersão
                    fig = px.scatter(
                        internacoes_filtered,
                        x=goal_column,
                        y='taxa_internacoes_100k',
                        size='taxa_internacoes_100k',
                        hover_name='Nome_Municipio',
                        hover_data=['MUNIC_RES_STR', 'populacao', 'total_internacoes', 'taxa_internacoes_100k'],
                        title=f'Taxa de Internações por 100.000 habitantes e {selected_goal} ({ano_idsc})',
                        labels={
                            goal_column: selected_goal,
                            'taxa_internacoes_100k': 'Taxa de Internações (por 100.000 hab.)'
                        },
                        color='taxa_internacoes_100k',
                        color_continuous_scale=px.colors.sequential.Blues
                    )
                    
                    # Configurar layout
                    fig.update_layout(
                        xaxis_title=f'{selected_goal}',
                        yaxis_title='Taxa de Internações (por 100.000 hab.)',
                        height=600
                    )
                    
                    # Adicionar informação sobre o Goal
                    st.markdown(f"**{selected_goal}**: {goal_options[selected_goal]['description']}")
                    
                    # Adicionar linha de tendência
                    try:
                        import numpy as np
                        from scipy import stats
                        
                        # Calcular linha de tendência
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            internacoes_filtered[goal_column],
                            internacoes_filtered['taxa_internacoes_100k']
                        )
                        
                        x_range = np.linspace(
                            internacoes_filtered[goal_column].min(),
                            internacoes_filtered[goal_column].max(),
                            100
                        )
                        y_range = slope * x_range + intercept
                        
                        fig.add_traces(
                            go.Scatter(
                                x=x_range, 
                                y=y_range, 
                                mode='lines', 
                                name=f'Tendência (R²={r_value**2:.3f})',
                                line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                            )
                        )
                        
                        # Adicionar texto com coeficiente de correlação
                        st.metric(
                            "Coeficiente de Correlação (R)",
                            f"{r_value:.3f}",
                            delta=f"R² = {r_value**2:.3f}"
                        )
                        
                        if abs(r_value) < 0.3:
                            st.info(f"Correlação fraca entre {selected_goal} e Taxa de Internações por 100.000 habitantes")
                        elif abs(r_value) < 0.7:
                            st.info(f"Correlação moderada entre {selected_goal} e Taxa de Internações por 100.000 habitantes")
                        else:
                            st.info(f"Correlação forte entre {selected_goal} e Taxa de Internações por 100.000 habitantes")
                        
                        if p_value < 0.05:
                            st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                            de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                            de que existe uma relação linear entre o {selected_goal} e a taxa de internações por 100.000 habitantes.
                            """)
                        else:
                            st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                            da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                            uma relação linear entre o {selected_goal} e a taxa de internações por 100.000 habitantes.
                            """)
                        
                        # Explicação sobre o coeficiente de correlação
                        st.markdown(f"""
                        **Sobre o coeficiente de correlação (R):**
                        - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                        - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                        que é previsível a partir da variável independente
                        """)
                    except Exception as e:
                        st.warning(f"Não foi possível calcular a linha de tendência: {e}")
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar dados em uma tabela
                    st.subheader("Dados da Análise")
                    display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'populacao', 'total_internacoes', 'taxa_internacoes_100k', goal_column]
                    st.dataframe(internacoes_filtered[display_cols].sort_values('taxa_internacoes_100k', ascending=False), use_container_width=True)
            else:
                # Fallback para o método original se não houver dados de população suficientes
                st.warning("Dados de população insuficientes para calcular taxas por 100.000 habitantes. Usando valores absolutos.")
                
                # Remover outliers extremos (opcional)
                q_low = internacoes_por_municipio['total_internacoes'].quantile(0.01)
                q_high = internacoes_por_municipio['total_internacoes'].quantile(0.99)
                internacoes_filtered = internacoes_por_municipio[
                    (internacoes_por_municipio['total_internacoes'] >= q_low) & 
                    (internacoes_por_municipio['total_internacoes'] <= q_high)
                ]
                
                # Filtrar municípios sem o Goal selecionado
                internacoes_filtered = internacoes_filtered.dropna(subset=[goal_column])
                
                if len(internacoes_filtered) < 5:
                    st.warning(f"Dados insuficientes para o {selected_goal}. Tente outro Goal ou ajuste os filtros.")
                else:
                    # Criar gráfico de dispersão
                    fig = px.scatter(
                        internacoes_filtered,
                        x=goal_column,
                        y='total_internacoes',
                        size='total_internacoes',
                        hover_name='Nome_Municipio',
                        hover_data=['MUNIC_RES_STR'],
                        title=f'Número de Internações por {selected_goal} ({ano_idsc})',
                        labels={
                            goal_column: selected_goal,
                            'total_internacoes': 'Número de Internações'
                        },
                        color='total_internacoes',
                        color_continuous_scale=px.colors.sequential.Blues
                    )
                    
                    # Configurar layout
                    fig.update_layout(
                        xaxis_title=f'{selected_goal}',
                        yaxis_title='Número de Internações',
                        height=600
                    )
                    
                    # Adicionar informação sobre o Goal
                    st.markdown(f"**{selected_goal}**: {goal_options[selected_goal]['description']}")
                    
                    # Adicionar linha de tendência
                    try:
                        import numpy as np
                        from scipy import stats
                        
                        # Calcular linha de tendência
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            internacoes_filtered[goal_column],
                            internacoes_filtered['total_internacoes']
                        )
                        
                        x_range = np.linspace(
                            internacoes_filtered[goal_column].min(),
                            internacoes_filtered[goal_column].max(),
                            100
                        )
                        y_range = slope * x_range + intercept
                        
                        fig.add_traces(
                            go.Scatter(
                                x=x_range, 
                                y=y_range, 
                                mode='lines', 
                                name=f'Tendência (R²={r_value**2:.3f})',
                                line=dict(dash='dash', color='rgba(0,0,0,0.6)')
                            )
                        )
                        
                        # Adicionar texto com coeficiente de correlação
                        st.metric(
                            "Coeficiente de Correlação (R)",
                            f"{r_value:.3f}",
                            delta=f"R² = {r_value**2:.3f}"
                        )
                        
                        if abs(r_value) < 0.3:
                            st.info(f"Correlação fraca entre {selected_goal} e Número de Internações")
                        elif abs(r_value) < 0.7:
                            st.info(f"Correlação moderada entre {selected_goal} e Número de Internações")
                        else:
                            st.info(f"Correlação forte entre {selected_goal} e Número de Internações")
                        
                        if p_value < 0.05:
                            st.success(f"Correlação estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value < 0.05 indica que podemos rejeitar a hipótese nula de que a inclinação da reta
                            de regressão é zero (ou seja, não há relação linear entre as variáveis). Há evidência estatística 
                            de que existe uma relação linear entre o {selected_goal} e o número de internações.
                            """)
                        else:
                            st.warning(f"Correlação não estatisticamente significativa (p={p_value:.4f})")
                            st.markdown(f"""
                            **O que significa:** O p-value >= 0.05 indica que não podemos rejeitar a hipótese nula de que a inclinação 
                            da reta de regressão é zero. Não há evidência estatística suficiente para afirmar que existe
                            uma relação linear entre o {selected_goal} e o número de internações.
                            """)
                        
                        # Explicação sobre o coeficiente de correlação
                        st.markdown(f"""
                        **Sobre o coeficiente de correlação (R):**
                        - O valor de R ({r_value:.3f}) indica a força e direção da relação linear entre as variáveis
                        - R² ({r_value**2:.3f}) é o coeficiente de determinação, que representa a proporção da variância na variável dependente 
                        que é previsível a partir da variável independente
                        """)
                    except Exception as e:
                        st.warning(f"Não foi possível calcular a linha de tendência: {e}")
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar dados em uma tabela
                    st.subheader("Dados da Análise")
                    display_cols = ['MUNIC_RES_STR', 'Nome_Municipio', 'total_internacoes', goal_column]
                    st.dataframe(internacoes_filtered[display_cols].sort_values('total_internacoes', ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")

# Executar o aplicativo
if __name__ == "__main__":
    pass  # O código principal já foi executado acima 