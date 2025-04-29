import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import sqlite3

# Set page configuration
st.set_page_config(
    page_title="Morbidade Psiquiátrica no Brasil",
    page_icon="🏥",
    layout="wide"
)

# Title and description
st.title("Perfil de Morbimortalidade Psiquiátrica no Brasil")
st.markdown("""
Este dashboard analisa o perfil de internações hospitalares por transtornos mentais e comportamentais
no Brasil, utilizando dados do Sistema de Informações Hospitalares (SIH).
""")

# Função para obter dados populacionais do banco SQLite
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
    
    try:
        conn = sqlite3.connect('populacao.db')
        df_populacao = pd.read_sql_query(query, conn)
        conn.close()
        
        return df_populacao
    except Exception as e:
        st.warning(f"Erro ao consultar o banco de dados de população: {e}")
        return pd.DataFrame(columns=['ano', 'tam_pop'])

# Função para verificar disponibilidade do banco de dados de população
def check_population_data():
    try:
        # Testar conexão com o banco de dados
        conn = sqlite3.connect('populacao.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='populacao'")
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        st.warning(f"Aviso: Banco de dados de população não disponível: {e}")
        return False

# Função para calcular taxa por 100.000 habitantes usando o mesmo método do app_taxa_mortalidade.py
def calcular_taxa_por_100k_habitantes(df, codigo_municipio=None, estado=None, raca=None, faixa_etaria=None, sexo=None, usar_raca_cor2=False):
    # Converter sexo para formato esperado pelo banco de dados
    sexo_db = None
    if sexo == "Masculino":
        sexo_db = "M"
    elif sexo == "Feminino":
        sexo_db = "F"
    
    # Obter dados populacionais filtrados
    df_populacao = get_population_data(codigo_municipio=codigo_municipio, 
                                       estado=estado, 
                                       raca=raca, 
                                       faixa_etaria=faixa_etaria, 
                                       sexo=sexo_db,
                                       usar_raca_cor2=usar_raca_cor2)
    
    # Agrupar dados por ano
    contagens_por_ano = df.groupby('ANO_CMPT', observed=True).size().reset_index(name='numero_casos')
    contagens_por_ano = contagens_por_ano.rename(columns={'ANO_CMPT': 'ano'})
    
    # Mesclar com os dados populacionais
    df_completo = pd.merge(contagens_por_ano, df_populacao, on='ano', how='left')
    
    # Calcular a taxa por 100.000 habitantes
    df_completo['taxa_por_100k'] = (df_completo['numero_casos'] / df_completo['tam_pop']) * 100000
    
    return df_completo

# Função para carregar dados populacionais
@st.cache_data
def load_population_data():
    try:
        # Tentar carregar dados populacionais do IBGE
        arquivo_populacao = 'data/populacao_ibge.csv'
        if not os.path.exists(arquivo_populacao):
            raise FileNotFoundError(f"Arquivo de dados populacionais não encontrado: {arquivo_populacao}")
            
        pop_df = pd.read_csv(arquivo_populacao, low_memory=False)
        
        # Criar dicionários para acesso rápido
        # Estrutura esperada: ano -> UF -> população
        pop_estado_dict = {}
        # Estrutura esperada: ano -> município -> população
        pop_municipio_dict = {}
        
        # Populações totais por ano
        pop_ano_dict = {}
        
        # Preencher os dicionários (ajuste as colunas conforme seu arquivo)
        for _, row in pop_df.iterrows():
            ano = int(row['ANO'])
            uf = str(row['UF'])
            municipio = str(row['MUNICIPIO'])
            populacao = int(row['POPULACAO'])
            
            # Populações por estado
            if ano not in pop_estado_dict:
                pop_estado_dict[ano] = {}
            if uf not in pop_estado_dict[ano]:
                pop_estado_dict[ano][uf] = 0
            pop_estado_dict[ano][uf] += populacao
            
            # Populações por município
            if ano not in pop_municipio_dict:
                pop_municipio_dict[ano] = {}
            pop_municipio_dict[ano][municipio] = populacao
            
            # Populações totais por ano
            if ano not in pop_ano_dict:
                pop_ano_dict[ano] = 0
            pop_ano_dict[ano] += populacao
            
        return True, pop_estado_dict, pop_municipio_dict, pop_ano_dict, pop_df
    except FileNotFoundError as e:
        st.warning(f"Aviso: {str(e)}. \nAs taxas por 100.000 habitantes não serão calculadas. \nPara habilitar esta funcionalidade, crie um arquivo CSV com dados populacionais em 'data/populacao_ibge.csv' contendo as colunas: ANO, UF, MUNICIPIO, POPULACAO.")
        return False, {}, {}, {}, pd.DataFrame()
    except Exception as e:
        st.warning(f"Erro ao carregar dados populacionais: {e}. As taxas por 100.000 habitantes não serão calculadas.")
        return False, {}, {}, {}, pd.DataFrame()

# Função para exibir resumo dos filtros aplicados
def mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2=False, diag_grupo=None, diag_categoria=None, diag_subcategoria=None):
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

# Load the data
try:
    df = load_data()
    # Carregar dicionário de municípios
    municipios_dict = load_municipalities()
    
    # Display loading message while processing
    with st.spinner('Carregando dados...'):
        data_load_state = st.success('Dados carregados com sucesso!')
    
    # Verificar disponibilidade do banco de dados de população
    dados_populacionais_disponiveis = check_population_data()
    
    # Mostrar instruções para habilitar cálculos de taxa por 100k apenas se os dados não estiverem disponíveis
    if not dados_populacionais_disponiveis:
        st.info("""
        ### Como habilitar taxas por 100.000 habitantes
        
        Para visualizar gráficos de taxa por 100.000 habitantes, é necessário ter um banco de dados SQLite com informações populacionais.
        
        O arquivo `populacao.db` deve conter uma tabela chamada `populacao` com as seguintes colunas:
        - ano: Ano de referência
        - codigo_municipio: Código do município (6 dígitos)
        - sexo: Sexo ('M' ou 'F')
        - raca: Raça/Cor (Branca, Preta, Parda, Amarela, Indígena)
        - faixa_etaria: Faixa etária no mesmo formato dos filtros
        - populacao: Número de habitantes
        
        Consulte o arquivo `app_taxa_mortalidade.py` para mais detalhes sobre a estrutura do banco de dados.
        """)
    else:
        st.success("Banco de dados de população encontrado! Gráficos de taxa por 100.000 habitantes estão disponíveis.")
    
    # Sidebar filters
    st.sidebar.header("Filtros")
    
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
    
    # Dicionário de estados - usando o mesmo do app_taxa_suicidio
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
    elif 'NACIONAL' in df.columns:  # Verifica se existe outra coluna que possa representar raça/etnia
        raca_options = ["Todas"] + sorted([str(x) for x in df['NACIONAL'].dropna().unique()])
        raca = st.sidebar.selectbox(
            "Nacionalidade/Etnia",
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
    
    # Filtrar por município
    if codigo_municipio:
        filtered_df = filtered_df[filtered_df['MUNIC_RES'].astype(str) == codigo_municipio]
    
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
    elif 'NACIONAL' in df.columns and raca != "Todas":
        filtered_df = filtered_df[filtered_df['NACIONAL'].astype(str) == raca]
    
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
    
    # Pré-calcular as taxas por 100.000 habitantes uma única vez se os dados populacionais estiverem disponíveis
    taxas_por_100k_df = None
    if dados_populacionais_disponiveis:
        # Converter sexo para formato esperado pelo banco de dados
        sexo_filtro = None
        if sexo == "Masculino":
            sexo_filtro = "M"
        elif sexo == "Feminino":
            sexo_filtro = "F"
        
        # Converter raça para formato esperado pelo banco de dados
        raca_filtro = raca if raca != "Todas" else None
        
        # Calcular taxas por 100.000 habitantes uma única vez
        taxas_por_100k_df = calcular_taxa_por_100k_habitantes(
            filtered_df,
            codigo_municipio=codigo_municipio,
            estado=estado,
            raca=raca_filtro,
            faixa_etaria=faixa_etaria if faixa_etaria != "Todas" else None,
            sexo=sexo_filtro,
            usar_raca_cor2=usar_raca_cor2
        )
    
    # Main dashboard content
    tabs = st.tabs([
        "Visão Geral", 
        "Tempo de Permanência", 
        "Morbidade", 
        "Regime de Internação",
        "Características Demográficas",
        "Distribuição Geográfica"
    ])
    
    # Tab 1: Overview
    with tabs[0]:
        st.header("Visão Geral das Internações Psiquiátricas")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_internments = len(filtered_df)
            st.metric("Total de Internações", f"{total_internments:,}".replace(",", "."))
        
        with col2:
            mortality_rate = (filtered_df['MORTE'] == 1).mean() * 100
            st.metric("Taxa de Mortalidade", f"{mortality_rate:.2f}%")
        
        with col3:
            mean_stay = filtered_df['DIAS_PERM'].mean()
            st.metric("Média de Permanência (dias)", f"{mean_stay:.1f}")
        
        # Trend over time
        st.subheader("Evolução Temporal das Internações")
        yearly_counts = filtered_df.groupby('ANO_CMPT', observed=True).size().reset_index(name='count')
        
        fig = px.line(
            yearly_counts, 
            x='ANO_CMPT', 
            y='count',
            labels={'ANO_CMPT': 'Ano', 'count': 'Número de Internações'},
            title='Internações Psiquiátricas por Ano'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar taxa por 100.000 habitantes se dados populacionais disponíveis
        if dados_populacionais_disponiveis and taxas_por_100k_df is not None:
            st.subheader("Taxa de Internações por 100.000 Habitantes")
            
            fig = px.line(
                taxas_por_100k_df,
                x='ano',
                y='taxa_por_100k',
                labels={'ano': 'Ano', 'taxa_por_100k': 'Taxa por 100.000 Habitantes'},
                title='Taxa de Internações por 100.000 Habitantes',
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados populacionais não disponíveis para calcular taxas por 100.000 habitantes.")
        
        # Diagnostic groups distribution
        st.subheader("Distribuição por Grupos Diagnósticos")
        diag_group_counts = filtered_df['def_diag_princ_grupo'].value_counts().reset_index()
        diag_group_counts.columns = ['Grupo Diagnóstico', 'Contagem']
        
        fig = px.pie(
            diag_group_counts, 
            values='Contagem', 
            names='Grupo Diagnóstico',
            title='Distribuição das Internações por Grupo Diagnóstico'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: Length of Stay
    with tabs[1]:
        st.header("Tempo de Permanência")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Distribution of length of stay
        st.subheader("Distribuição do Tempo de Permanência")
        
        # Prepare bins for histogram
        max_days = min(filtered_df['DIAS_PERM'].max(), 50)  # Cap at 50 days for better visualization
        
        fig = px.histogram(
            filtered_df, 
            x='DIAS_PERM',
            nbins=120,
            range_x=[0, max_days],
            labels={'DIAS_PERM': 'Dias de Permanência', 'count': 'Frequência'},
            title='Distribuição dos Dias de Permanência'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Length of stay by diagnostic group
        st.subheader("Tempo Médio de Permanência por Grupo Diagnóstico")
        
        stay_by_diag = filtered_df.groupby('def_diag_princ_grupo', observed=True)['DIAS_PERM'].mean().reset_index()
        stay_by_diag.columns = ['Grupo Diagnóstico', 'Média de Dias']
        stay_by_diag = stay_by_diag.sort_values('Média de Dias', ascending=False)
        
        fig = px.bar(
            stay_by_diag, 
            x='Grupo Diagnóstico', 
            y='Média de Dias',
            labels={'Grupo Diagnóstico': 'Grupo Diagnóstico', 'Média de Dias': 'Média de Dias de Permanência'},
            title='Tempo Médio de Permanência por Grupo Diagnóstico'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar gráfico de Evolução Temporal do Tempo de Permanência
        st.subheader("Evolução Temporal do Tempo de Permanência")
        
        stay_by_year = filtered_df.groupby('ANO_CMPT', observed=True)['DIAS_PERM'].mean().reset_index()
        stay_by_year.columns = ['Ano', 'Média de Dias']
        
        fig = px.line(
            stay_by_year, 
            x='Ano', 
            y='Média de Dias',
            labels={'Ano': 'Ano', 'Média de Dias': 'Média de Dias de Permanência'},
            title='Evolução Temporal do Tempo Médio de Permanência',
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar gráfico de Tempo de Permanência por Raça/Cor
        st.subheader("Tempo Médio de Permanência por Raça/Cor")
        
        # Verificar qual campo de raça/cor está disponível
        if 'RACA_COR_DESC' in filtered_df.columns:
            raca_column = 'RACA_COR_DESC'
        elif 'def_raca_cor' in filtered_df.columns:
            raca_column = 'def_raca_cor'
        else:
            st.info("Dados de raça/cor não disponíveis para análise de tempo de permanência.")
            raca_column = None
        
        if raca_column:
            # Se estiver usando Raça/Cor 2 e a classificação for RACA_COR_DESC ou def_raca_cor
            if usar_raca_cor2:
                # Criar cópia para não afetar o dataframe original
                df_raca_perm = filtered_df.copy()
                
                # Substituir Preta e Parda por Negra
                df_raca_perm.loc[df_raca_perm[raca_column].isin(['Preta', 'Parda']), raca_column] = 'Negra'
                
                # Calcular média de permanência por raça/cor
                stay_by_race = df_raca_perm.groupby(raca_column, observed=True)['DIAS_PERM'].mean().reset_index()
            else:
                # Usar dataframe original com classificação tradicional
                stay_by_race = filtered_df.groupby(raca_column, observed=True)['DIAS_PERM'].mean().reset_index()
            
            stay_by_race.columns = ['Raça/Cor', 'Média de Dias']
            stay_by_race = stay_by_race.sort_values('Média de Dias', ascending=False)
            
            fig = px.bar(
                stay_by_race, 
                x='Raça/Cor', 
                y='Média de Dias',
                labels={'Raça/Cor': 'Raça/Cor', 'Média de Dias': 'Média de Dias de Permanência'},
                title='Tempo Médio de Permanência por Raça/Cor',
                color='Média de Dias',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Adicionar boxplot para mostrar a distribuição completa
            st.subheader("Distribuição do Tempo de Permanência por Raça/Cor")
            
            if usar_raca_cor2:
                fig = px.box(
                    df_raca_perm,
                    x=raca_column,
                    y='DIAS_PERM',
                    labels={raca_column: 'Raça/Cor', 'DIAS_PERM': 'Dias de Permanência'},
                    title='Distribuição do Tempo de Permanência por Raça/Cor',
                    color=raca_column
                )
            else:
                fig = px.box(
                    filtered_df,
                    x=raca_column,
                    y='DIAS_PERM',
                    labels={raca_column: 'Raça/Cor', 'DIAS_PERM': 'Dias de Permanência'},
                    title='Distribuição do Tempo de Permanência por Raça/Cor',
                    color=raca_column
                )
            
            # Limitar o eixo Y para melhor visualização
            fig.update_layout(yaxis_range=[0, min(filtered_df['DIAS_PERM'].quantile(0.95), 50)])
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 3: Morbidity
    with tabs[2]:
        st.header("Morbidade")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Mortality rate by diagnostic group
        st.subheader("Taxa de Mortalidade por Grupo Diagnóstico")
        
        mortality_by_diag = filtered_df.groupby('def_diag_princ_grupo', observed=True)['MORTE'].mean().reset_index()
        mortality_by_diag['Taxa de Mortalidade (%)'] = mortality_by_diag['MORTE'] * 100
        mortality_by_diag = mortality_by_diag.sort_values('Taxa de Mortalidade (%)', ascending=False)
        
        fig = px.bar(
            mortality_by_diag, 
            x='def_diag_princ_grupo', 
            y='Taxa de Mortalidade (%)',
            labels={'def_diag_princ_grupo': 'Grupo Diagnóstico', 'Taxa de Mortalidade (%)': 'Taxa de Mortalidade (%)'},
            title='Taxa de Mortalidade por Grupo Diagnóstico'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar gráfico de Evolução Temporal da Taxa de Mortalidade
        st.subheader("Evolução Temporal da Taxa de Mortalidade")
        
        mort_by_year = filtered_df.groupby('ANO_CMPT', observed=True)['MORTE'].mean().reset_index()
        mort_by_year['Taxa de Mortalidade (%)'] = mort_by_year['MORTE'] * 100
        
        fig = px.line(
            mort_by_year, 
            x='ANO_CMPT', 
            y='Taxa de Mortalidade (%)',
            labels={'ANO_CMPT': 'Ano', 'Taxa de Mortalidade (%)': 'Taxa de Mortalidade (%)'},
            title='Evolução da Taxa de Mortalidade ao Longo dos Anos',
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar gráfico de Principais Categorias Diagnósticas
        st.subheader("Principais Categorias Diagnósticas")
        
        # Obter as 10 categorias de diagnóstico mais comuns
        if 'def_diag_princ_cat' in filtered_df.columns:
            top_categories = filtered_df['def_diag_princ_cat'].value_counts().nlargest(10).reset_index()
            top_categories.columns = ['Categoria Diagnóstica', 'Contagem']
            
            fig = px.bar(
                top_categories, 
                y='Categoria Diagnóstica', 
                x='Contagem',
                labels={'Categoria Diagnóstica': 'Categoria Diagnóstica', 'Contagem': 'Número de Internações'},
                title='Top 10 Categorias Diagnósticas',
                orientation='h'
            )
            st.plotly_chart(fig, use_container_width=True)
        
    # Tab 4: Hospitalization Regime
    with tabs[3]:
        st.header("Regime de Internação e Caráter de Atendimento")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Distribution by hospitalization regime
        st.subheader("Distribuição por Regime de Internação")
        
        regime_counts = filtered_df['def_regime'].value_counts().reset_index()
        regime_counts.columns = ['Regime', 'Contagem']
        
        fig = px.pie(
            regime_counts, 
            values='Contagem', 
            names='Regime',
            title='Distribuição das Internações por Regime'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar gráfico de evolução temporal por regime de internação
        st.subheader("Evolução Temporal por Regime de Internação")
        
        # Agrupar dados por ano e regime
        regime_by_year = filtered_df.groupby(['ANO_CMPT', 'def_regime'], observed=True).size().reset_index(name='Contagem')
        
        # Criar gráfico de linha
        fig = px.line(
            regime_by_year,
            x='ANO_CMPT',
            y='Contagem',
            color='def_regime',
            labels={'ANO_CMPT': 'Ano', 'Contagem': 'Número de Internações', 'def_regime': 'Regime de Internação'},
            title='Número de Internações por Regime ao Longo dos Anos',
            markers=True
        )
        
        # Melhorar aparência do gráfico
        fig.update_layout(
            xaxis_title='Ano',
            yaxis_title='Número de Internações',
            legend_title='Regime de Internação',
            hovermode='x unified',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 5: Demographic Characteristics
    with tabs[4]:
        st.header("Características Demográficas")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Sex distribution
            st.subheader("Distribuição por Sexo")
            
            # Convert numerical sex to categorical
            filtered_df.loc[:, 'Sexo'] = filtered_df['SEXO'].map({1: 'Masculino', 3: 'Feminino', 0: 'Não informado'})
            sex_counts = filtered_df['Sexo'].value_counts().reset_index()
            sex_counts.columns = ['Sexo', 'Contagem']
            
            fig = px.pie(
                sex_counts, 
                values='Contagem', 
                names='Sexo',
                title='Distribuição das Internações por Sexo'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Age distribution
            st.subheader("Distribuição por Idade")
            
            # Create age groups
            age_bins = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, float('inf')]
            age_labels = ['0-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '85-89', '90-94', '95-99', '100+']
            
            filtered_df.loc[:, 'Faixa Etária'] = pd.cut(filtered_df['IDADE'], bins=age_bins, labels=age_labels, right=False)
            age_counts = filtered_df['Faixa Etária'].value_counts().reset_index()
            age_counts.columns = ['Faixa Etária', 'Contagem']
            age_counts = age_counts.sort_values('Faixa Etária')
            
            fig = px.bar(
                age_counts, 
                x='Faixa Etária', 
                y='Contagem',
                labels={'Faixa Etária': 'Faixa Etária', 'Contagem': 'Número de Internações'},
                title='Distribuição das Internações por Faixa Etária'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Race/Color distribution
        st.subheader("Distribuição por Raça/Cor")
        
        # Check if race data is available
        if 'RACA_COR' in filtered_df.columns:
            if 'RACA_COR_DESC' in filtered_df.columns:
                # Criar uma distribuição de raça que reflita a classificação escolhida
                if usar_raca_cor2:
                    # Criar cópia para não afetar o dataframe original
                    df_raca = filtered_df.copy()
                    
                    # Substituir Preta e Parda por Negra
                    df_raca.loc[df_raca['RACA_COR_DESC'].isin(['Preta', 'Parda']), 'RACA_COR_DESC'] = 'Negra'
                    
                    race_counts = df_raca['RACA_COR_DESC'].value_counts().reset_index()
                    race_counts.columns = ['Raça/Cor', 'Contagem']
                else:
                    race_counts = filtered_df['RACA_COR_DESC'].value_counts().reset_index()
                    race_counts.columns = ['Raça/Cor', 'Contagem']
            
            # Create race distribution visualization
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    race_counts, 
                    values='Contagem', 
                    names='Raça/Cor',
                    title='Distribuição das Internações por Raça/Cor'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    race_counts, 
                    y='Raça/Cor', 
                    x='Contagem',
                    labels={'Raça/Cor': 'Raça/Cor', 'Contagem': 'Número de Internações'},
                    title='Número de Internações por Raça/Cor',
                    orientation='h'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Race by diagnosis group
            st.subheader("Distribuição Racial por Grupo Diagnóstico")
            
            # Create a cross-tabulation between race and diagnosis group
            if usar_raca_cor2:
                # Usar o dataframe ajustado
                race_diag_pivot = pd.crosstab(
                    df_raca['RACA_COR_DESC'], 
                    df_raca['def_diag_princ_grupo'],
                    normalize='columns'  # Normalize to get proportions within each diagnosis group
                )
            else:
                race_diag_pivot = pd.crosstab(
                    filtered_df['RACA_COR_DESC'], 
                    filtered_df['def_diag_princ_grupo'],
                    normalize='columns'  # Normalize to get proportions within each diagnosis group
                )
            
            fig = px.imshow(
                race_diag_pivot,
                labels=dict(x="Grupo Diagnóstico", y="Raça/Cor", color="Proporção"),
                title="Distribuição de Raça/Cor por Grupo Diagnóstico (%)",
                color_continuous_scale='Viridis',
                aspect="auto"
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add absolute counts table
            if usar_raca_cor2:
                race_diag_abs = pd.crosstab(
                    df_raca['RACA_COR_DESC'], 
                    df_raca['def_diag_princ_grupo']
                )
            else:
                race_diag_abs = pd.crosstab(
                    filtered_df['RACA_COR_DESC'], 
                    filtered_df['def_diag_princ_grupo']
                )
            
            st.subheader("Tabela de Contagem: Raça/Cor por Grupo Diagnóstico")
            st.dataframe(race_diag_abs, use_container_width=True)
        
        elif 'def_raca_cor' in filtered_df.columns:
            # Caso semelhante para def_raca_cor
            if usar_raca_cor2:
                df_raca = filtered_df.copy()
                df_raca.loc[df_raca['def_raca_cor'].isin(['Preta', 'Parda']), 'def_raca_cor'] = 'Negra'
                race_counts = df_raca['def_raca_cor'].value_counts().reset_index()
                race_counts.columns = ['Raça/Cor', 'Contagem']
            else:
                race_counts = filtered_df['def_raca_cor'].value_counts().reset_index()
                race_counts.columns = ['Raça/Cor', 'Contagem']
                
            # Create race distribution visualization
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    race_counts, 
                    values='Contagem', 
                    names='Raça/Cor',
                    title='Distribuição das Internações por Raça/Cor'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    race_counts, 
                    y='Raça/Cor', 
                    x='Contagem',
                    labels={'Raça/Cor': 'Raça/Cor', 'Contagem': 'Número de Internações'},
                    title='Número de Internações por Raça/Cor',
                    orientation='h'
                )
                st.plotly_chart(fig, use_container_width=True)

        # Mortality by race (if available)
        if 'RACA_COR_DESC' in filtered_df.columns:
            st.subheader("Taxa de Mortalidade por Raça/Cor")
            
            # Usar o mesmo dataframe ajustado que já foi criado anteriormente
            if usar_raca_cor2:
                # Verificando se df_raca já foi criado
                df_raca = filtered_df.copy()
                df_raca.loc[df_raca['RACA_COR_DESC'].isin(['Preta', 'Parda']), 'RACA_COR_DESC'] = 'Negra'
                mort_by_race = df_raca.groupby('RACA_COR_DESC', observed=True)['MORTE'].mean().reset_index()
            else:
                mort_by_race = filtered_df.groupby('RACA_COR_DESC', observed=True)['MORTE'].mean().reset_index()
            
            mort_by_race['Taxa de Mortalidade (%)'] = mort_by_race['MORTE'] * 100
            
            fig = px.bar(
                mort_by_race,
                x='RACA_COR_DESC',
                y='Taxa de Mortalidade (%)',
                title='Taxa de Mortalidade por Raça/Cor',
                color='RACA_COR_DESC'
            )
            st.plotly_chart(fig, use_container_width=True)
        elif 'def_raca_cor' in filtered_df.columns:
            st.subheader("Taxa de Mortalidade por Raça/Cor")
            
            if usar_raca_cor2:
                df_raca = filtered_df.copy()
                df_raca.loc[df_raca['def_raca_cor'].isin(['Preta', 'Parda']), 'def_raca_cor'] = 'Negra'
                mort_by_race = df_raca.groupby('def_raca_cor', observed=True)['MORTE'].mean().reset_index()
            else:
                mort_by_race = filtered_df.groupby('def_raca_cor', observed=True)['MORTE'].mean().reset_index()
            
            mort_by_race['Taxa de Mortalidade (%)'] = mort_by_race['MORTE'] * 100
            
            fig = px.bar(
                mort_by_race,
                x='def_raca_cor',
                y='Taxa de Mortalidade (%)',
                title='Taxa de Mortalidade por Raça/Cor',
                color='def_raca_cor'
            )
            st.plotly_chart(fig, use_container_width=True)

        # Demographic analysis by diagnostic groups
        st.subheader("Análise Demográfica por Grupos Diagnósticos")
        
        # Sex by diagnostic group
        sex_by_diag = filtered_df.groupby(['def_diag_princ_grupo', 'Sexo'], observed=True).size().reset_index(name='Contagem')
        
        fig = px.bar(
            sex_by_diag, 
            x='def_diag_princ_grupo', 
            y='Contagem',
            color='Sexo',
            barmode='group',
            labels={'def_diag_princ_grupo': 'Grupo Diagnóstico', 'Contagem': 'Número de Internações', 'Sexo': 'Sexo'},
            title='Distribuição das Internações por Sexo e Grupo Diagnóstico'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Age by diagnostic group (heatmap)
        st.subheader("Distribuição de Idade por Grupo Diagnóstico")
        
        age_diag_pivot = pd.crosstab(
            filtered_df['Faixa Etária'], 
            filtered_df['def_diag_princ_grupo']
        )
        
        fig = px.imshow(
            age_diag_pivot,
            labels=dict(x="Grupo Diagnóstico", y="Faixa Etária", color="Contagem"),
            title="Distribuição de Faixas Etárias por Grupo Diagnóstico",
            aspect="auto"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # New analysis: Mortality by demographic groups
        st.subheader("Taxa de Mortalidade por Características Demográficas")
        
        # Mortality by sex
        mort_by_sex = filtered_df.groupby('Sexo', observed=True)['MORTE'].mean().reset_index()
        mort_by_sex['Taxa de Mortalidade (%)'] = mort_by_sex['MORTE'] * 100
        
        fig = px.bar(
            mort_by_sex,
            x='Sexo',
            y='Taxa de Mortalidade (%)',
            title='Taxa de Mortalidade por Sexo',
            color='Sexo'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Mortality by age group
        mort_by_age = filtered_df.groupby('Faixa Etária', observed=True)['MORTE'].mean().reset_index()
        mort_by_age['Taxa de Mortalidade (%)'] = mort_by_age['MORTE'] * 100
        mort_by_age = mort_by_age.sort_values('Faixa Etária')
        
        fig = px.bar(
            mort_by_age,
            x='Faixa Etária',
            y='Taxa de Mortalidade (%)',
            title='Taxa de Mortalidade por Faixa Etária',
            color='Faixa Etária'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 6: Geographic Distribution
    with tabs[5]:
        st.header("Distribuição Geográfica")
        
        # Exibir resumo dos filtros aplicados
        mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria)
        
        # Hospitalizations by state
        st.subheader("Internações por Estado")
        
        # Dictionary to map state codes to names
        state_names = {
            "12": "Acre",
            "27": "Alagoas",
            "16": "Amapá",
            "13": "Amazonas",
            "29": "Bahia",
            "23": "Ceará",
            "53": "Distrito Federal",
            "32": "Espírito Santo",
            "52": "Goiás",
            "21": "Maranhão",
            "51": "Mato Grosso",
            "50": "Mato Grosso do Sul",
            "31": "Minas Gerais",
            "15": "Pará",
            "25": "Paraíba",
            "41": "Paraná",
            "26": "Pernambuco",
            "22": "Piauí",
            "33": "Rio de Janeiro",
            "24": "Rio Grande do Norte",
            "43": "Rio Grande do Sul",
            "11": "Rondônia",
            "14": "Roraima",
            "42": "Santa Catarina",
            "35": "São Paulo",
            "28": "Sergipe",
            "17": "Tocantins"
        }
        
        state_counts = filtered_df['res_CODIGO_UF'].astype(str).value_counts().reset_index()
        state_counts.columns = ['UF', 'Contagem']
        # Add state names
        state_counts['Nome Estado'] = state_counts['UF'].map(state_names)
        state_counts = state_counts.sort_values('Contagem', ascending=False)
        
        # Use state names for display if available
        if state_counts['Nome Estado'].notna().all():
            fig = px.bar(
                state_counts, 
                x='Nome Estado', 
                y='Contagem',
                labels={'Nome Estado': 'Estado', 'Contagem': 'Número de Internações'},
                title='Distribuição das Internações por Estado',
                color='Contagem'
            )
        else:
            fig = px.bar(
                state_counts, 
                x='UF', 
                y='Contagem',
                labels={'UF': 'UF', 'Contagem': 'Número de Internações'},
                title='Distribuição das Internações por Estado',
                color='Contagem'
            )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar taxa por 100.000 habitantes para estados
        if dados_populacionais_disponiveis:
            st.subheader("Taxa de Internações por 100.000 Habitantes por Estado")
            
            # Preparar DataFrame com taxas por estado
            taxas_estados = []
            
            # Para cada estado, obter a taxa do DataFrame pré-calculado
            for _, row in state_counts.iterrows():
                estado_uf = row['UF']
                
                # Filtrar dados para o estado atual
                df_estado = filtered_df[filtered_df['res_CODIGO_UF'].astype(str) == estado_uf]
                
                if len(df_estado) > 0:
                    # Calcular taxa para este estado usando a função
                    df_taxa_estado = calcular_taxa_por_100k_habitantes(
                        df_estado,
                        estado=estado_uf,
                        raca=raca_filtro,
                        faixa_etaria=faixa_etaria if faixa_etaria != "Todas" else None,
                        sexo=sexo_filtro,
                        usar_raca_cor2=usar_raca_cor2
                    )
                    
                    # Calcular média da taxa para o período
                    if not df_taxa_estado.empty and 'taxa_por_100k' in df_taxa_estado.columns:
                        taxa_media = df_taxa_estado['taxa_por_100k'].mean()
                        
                        # Adicionar à lista de taxas
                        taxas_estados.append({
                            'UF': estado_uf,
                            'Nome Estado': row['Nome Estado'],
                            'taxa_por_100k': taxa_media,
                            'Contagem': row['Contagem']
                        })
            
            # Criar DataFrame com as taxas
            if taxas_estados:
                state_rates = pd.DataFrame(taxas_estados)
                
                # Ordenar por taxa
                state_rates = state_rates.sort_values('taxa_por_100k', ascending=False)
                
                # Criar gráfico
                if 'Nome Estado' in state_rates.columns and state_rates['Nome Estado'].notna().all():
                    fig = px.bar(
                        state_rates, 
                        x='Nome Estado', 
                        y='taxa_por_100k',
                        labels={'Nome Estado': 'Estado', 'taxa_por_100k': 'Taxa por 100.000 habitantes'},
                        title='Taxa de Internações por 100.000 Habitantes por Estado',
                        color='taxa_por_100k',
                        color_continuous_scale=px.colors.sequential.Viridis
                    )
                else:
                    fig = px.bar(
                        state_rates, 
                        x='UF', 
                        y='taxa_por_100k',
                        labels={'UF': 'UF', 'taxa_por_100k': 'Taxa por 100.000 habitantes'},
                        title='Taxa de Internações por 100.000 Habitantes por Estado',
                        color='taxa_por_100k',
                        color_continuous_scale=px.colors.sequential.Viridis
                    )
                
                fig.update_layout(xaxis_tickangle=-45, yaxis_title="Taxa por 100.000 habitantes")
                st.plotly_chart(fig, use_container_width=True)
                
                # Exibir tabela com os dados
                st.write("Dados de taxa por 100.000 habitantes por estado:")
                st.dataframe(state_rates)
                
                # Remover o mapa choropleth das taxas por estado que não está funcionando corretamente
            else:
                st.warning("Não foi possível calcular taxas por 100.000 habitantes por estado. Verifique se os dados populacionais para os filtros selecionados estão disponíveis no banco de dados.")
        
        # Top municipalities
        st.subheader("Municípios com Maior Número de Internações")
        
        top_cities = filtered_df['MUNIC_RES'].astype(str).value_counts().head(20).reset_index()
        top_cities.columns = ['Código do Município', 'Contagem']
        
        # Add municipality names when available using municipios_dict directly
        top_cities['Nome do Município'] = top_cities['Código do Município'].map(municipios_dict)
        
        # Replace NaN with "Município " + code
        top_cities['Nome do Município'] = top_cities['Nome do Município'].fillna(
            'Município ' + top_cities['Código do Município']
        )
        
        fig = px.bar(
            top_cities, 
            x='Nome do Município', 
            y='Contagem',
            labels={'Nome do Município': 'Município', 'Contagem': 'Número de Internações'},
            title='Top 20 Municípios por Número de Internações',
            color='Contagem'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Show table with municipality codes and names
        st.subheader("Tabela de Municípios")
        st.dataframe(top_cities)
        
        # Adicionar taxa por 100.000 habitantes para municípios
        if dados_populacionais_disponiveis:
            st.subheader("Taxa de Internações por 100.000 Habitantes por Município")
            
            # Preparar DataFrame com taxas por município
            taxas_municipios = []
            
            # Para cada município, calcular a taxa - usar top_cities ao invés de city_counts que não existe
            for _, row in top_cities.head(100).iterrows():
                codigo_mun = row['Código do Município']
                
                # Filtrar dados para o município atual
                df_municipio = filtered_df[filtered_df['MUNIC_RES'].astype(str) == codigo_mun]
                
                if len(df_municipio) > 0:
                    # Calcular taxa para este município
                    df_taxa_municipio = calcular_taxa_por_100k_habitantes(
                        df_municipio,
                        codigo_municipio=codigo_mun,
                        raca=raca_filtro,
                        faixa_etaria=faixa_etaria if faixa_etaria != "Todas" else None,
                        sexo=sexo_filtro,
                        usar_raca_cor2=usar_raca_cor2
                    )
                    
                    # Calcular média da taxa para o período
                    if not df_taxa_municipio.empty and 'taxa_por_100k' in df_taxa_municipio.columns:
                        taxa_media = df_taxa_municipio['taxa_por_100k'].mean()
                        
                        # Adicionar à lista de taxas
                        taxas_municipios.append({
                            'MUNIC_RES': codigo_mun,
                            'Nome do Município': row['Nome do Município'],
                            'taxa_por_100k': taxa_media,
                            'Contagem': row['Contagem']
                        })
        
        # Criar DataFrame com as taxas
        if taxas_municipios:
            city_rates = pd.DataFrame(taxas_municipios)
            
            # Ordenar por taxa
            city_rates = city_rates.sort_values('taxa_por_100k', ascending=False).head(20)
            
            # Criar gráfico
            fig = px.bar(
                city_rates,
                x='Nome do Município',
                y='taxa_por_100k',
                labels={'Nome do Município': 'Município', 'taxa_por_100k': 'Taxa por 100.000 habitantes'},
                title='Top 20 Municípios por Taxa de Internações por 100.000 Habitantes',
                color='taxa_por_100k',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            fig.update_layout(xaxis_tickangle=-45, yaxis_title="Taxa por 100.000 habitantes")
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar tabela com taxas
            st.subheader("Tabela de Municípios - Taxa por 100.000 Habitantes")
            st.dataframe(city_rates)
        else:
            st.warning("Não foi possível calcular taxas por 100.000 habitantes por município. Verifique se os dados populacionais para os filtros selecionados estão disponíveis no banco de dados.")
        
        # Distribution of psychiatric hospitalization rates across municipalities
        if 'res_LATITUDE' in filtered_df.columns and 'res_LONGITUDE' in filtered_df.columns:
            st.subheader("Distribuição Geográfica das Internações")
            
            # Get coordinates for each municipality and count of cases
            geo_data = filtered_df.groupby(['MUNIC_RES', 'res_LATITUDE', 'res_LONGITUDE'], observed=True).size().reset_index(name='Contagem')
            
            # Add municipality names using municipios_dict directly
            geo_data['Nome do Município'] = geo_data['MUNIC_RES'].astype(str).map(municipios_dict)
            geo_data['Nome do Município'] = geo_data['Nome do Município'].fillna('Município ' + geo_data['MUNIC_RES'].astype(str))
            
            # Remove rows with missing coordinates
            geo_data = geo_data.dropna(subset=['res_LATITUDE', 'res_LONGITUDE'])
            
            fig = px.density_mapbox(
                geo_data,
                lat="res_LATITUDE",
                lon="res_LONGITUDE",
                z="Contagem",
                radius=8,
                hover_name="Nome do Município",
                hover_data=["MUNIC_RES", "Contagem"],
                zoom=3,
                mapbox_style="carto-positron",
                title="Distribuição Geográfica das Internações Psiquiátricas",
                width=800,
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Remover todo o bloco do mapa de calor com taxas por 100.000 habitantes
        
        # Add analysis of hospitalization by region if possible
        if 'res_CODIGO_UF' in filtered_df.columns:
            # Adicionar linha divisória para melhorar a visualização
            st.markdown("---")
            st.header("Análise por Região do Brasil")
            
            # Map states to regions
            region_map = {
                # Norte
                "11": "Norte", "12": "Norte", "13": "Norte", "14": "Norte", 
                "15": "Norte", "16": "Norte", "17": "Norte",
                # Nordeste
                "21": "Nordeste", "22": "Nordeste", "23": "Nordeste", "24": "Nordeste",
                "25": "Nordeste", "26": "Nordeste", "27": "Nordeste", "28": "Nordeste", "29": "Nordeste",
                # Sudeste
                "31": "Sudeste", "32": "Sudeste", "33": "Sudeste", "35": "Sudeste",
                # Sul
                "41": "Sul", "42": "Sul", "43": "Sul",
                # Centro-Oeste
                "50": "Centro-Oeste", "51": "Centro-Oeste", "52": "Centro-Oeste", "53": "Centro-Oeste"
            }
            
            # Create region column - use loc to avoid SettingWithCopyWarning
            filtered_df.loc[:, 'Região'] = filtered_df['res_CODIGO_UF'].astype(str).str[:2].map(region_map)
            
            region_counts = filtered_df['Região'].value_counts().reset_index()
            region_counts.columns = ['Região', 'Contagem']
            
            fig = px.pie(
                region_counts, 
                values='Contagem', 
                names='Região',
                title='Distribuição das Internações por Região',
                color='Região',
                color_discrete_map={
                    'Norte': '#636EFA', 
                    'Nordeste': '#EF553B', 
                    'Sudeste': '#00CC96', 
                    'Sul': '#AB63FA', 
                    'Centro-Oeste': '#FFA15A'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Hospitalization trends by region over time
            region_year_counts = filtered_df.groupby(['ANO_CMPT', 'Região'], observed=True).size().reset_index(name='Contagem')
            
            fig = px.line(
                region_year_counts, 
                x='ANO_CMPT', 
                y='Contagem', 
                color='Região',
                labels={'ANO_CMPT': 'Ano', 'Contagem': 'Número de Internações', 'Região': 'Região'},
                title='Evolução das Internações por Região ao Longo dos Anos',
                color_discrete_map={
                    'Norte': '#636EFA', 
                    'Nordeste': '#EF553B', 
                    'Sudeste': '#00CC96', 
                    'Sul': '#AB63FA', 
                    'Centro-Oeste': '#FFA15A'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Adicionar taxa por 100.000 habitantes por região ao longo do tempo
            if dados_populacionais_disponiveis:
                st.markdown("---")
                st.header("Evolução da Taxa de Internações por 100.000 Habitantes por Região")
                st.markdown("""
                Este gráfico mostra a evolução das taxas de internação psiquiátrica por 100.000 habitantes 
                para cada região do Brasil ao longo dos anos, permitindo comparar tendências regionais 
                independentemente do tamanho da população.
                """)
                
                # Preparar mapeamento de UFs por região
                regiao_ufs = {
                    'Norte': ['11', '12', '13', '14', '15', '16', '17'],
                    'Nordeste': ['21', '22', '23', '24', '25', '26', '27', '28', '29'],
                    'Sudeste': ['31', '32', '33', '35'],
                    'Sul': ['41', '42', '43'],
                    'Centro-Oeste': ['50', '51', '52', '53']
                }
                
                # Converter sexo para formato esperado pelo banco de dados
                sexo_filtro = None
                if sexo == "Masculino":
                    sexo_filtro = "M"
                elif sexo == "Feminino":
                    sexo_filtro = "F"
                
                # Converter raça para formato esperado pelo banco de dados
                raca_filtro = raca if raca != "Todas" else None
                
                # Preparar DataFrame para armazenar taxas por região e ano
                taxas_regiao_ano = []
                
                # Para cada combinação de região e ano, calcular a taxa
                for regiao, ufs in regiao_ufs.items():
                    # Filtrar dados para a região atual
                    df_regiao = filtered_df[filtered_df['res_CODIGO_UF'].astype(str).str[:2].isin(ufs)]
                    
                    if len(df_regiao) > 0:
                        # Agrupar por ano
                        anos = df_regiao['ANO_CMPT'].unique()
                        
                        for ano in anos:
                            # Filtrar para o ano atual
                            df_ano = df_regiao[df_regiao['ANO_CMPT'] == ano]
                            
                            # Contar casos neste ano para esta região
                            casos = len(df_ano)
                            
                            # Consultar população para esta região e ano
                            pop_total = 0
                            for uf in ufs:
                                # Consultar população de cada estado da região
                                df_pop_uf = get_population_data(
                                    estado=uf,
                                    raca=raca_filtro,
                                    sexo=sexo_filtro,
                                    faixa_etaria=faixa_etaria if faixa_etaria != "Todas" else None,
                                    usar_raca_cor2=usar_raca_cor2
                                )
                                
                                # Somar população do ano específico
                                pop_uf_ano = df_pop_uf[df_pop_uf['ano'] == ano]['tam_pop'].sum()
                                pop_total += pop_uf_ano
                            
                            # Calcular taxa se houver população
                            if pop_total > 0:
                                taxa = (casos / pop_total) * 100000
                                
                                # Adicionar à lista
                                taxas_regiao_ano.append({
                                    'Região': regiao,
                                    'ano': ano,
                                    'casos': casos,
                                    'populacao': pop_total,
                                    'taxa_por_100k': taxa
                                })
                
                # Criar DataFrame com as taxas
                if taxas_regiao_ano:
                    df_taxas_regiao = pd.DataFrame(taxas_regiao_ano)
                    
                    # Criar gráfico
                    fig = px.line(
                        df_taxas_regiao,
                        x='ano',
                        y='taxa_por_100k',
                        color='Região',
                        labels={'ano': 'Ano', 'taxa_por_100k': 'Taxa por 100.000 habitantes', 'Região': 'Região'},
                        title='Evolução da Taxa de Internações por 100.000 Habitantes por Região',
                        color_discrete_map={
                            'Norte': '#636EFA', 
                            'Nordeste': '#EF553B', 
                            'Sudeste': '#00CC96', 
                            'Sul': '#AB63FA', 
                            'Centro-Oeste': '#FFA15A'
                        },
                        markers=True
                    )
                    
                    # Melhorar aparência do gráfico
                    fig.update_layout(
                        xaxis_title='Ano',
                        yaxis_title='Taxa por 100.000 habitantes',
                        legend_title='Região',
                        hovermode='x unified',
                        template='plotly_white',
                        height=600,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(t=70)
                    )
                    
                    # Adicionar linha de tendência para cada região
                    for regiao in df_taxas_regiao['Região'].unique():
                        df_regiao = df_taxas_regiao[df_taxas_regiao['Região'] == regiao]
                        
                        # Ordenar por ano para garantir a tendência correta
                        df_regiao = df_regiao.sort_values('ano')
                        
                        # Adicionar linha de tendência apenas se houver dados suficientes
                        if len(df_regiao) >= 3:
                            fig.add_traces(
                                px.scatter(
                                    df_regiao, x='ano', y='taxa_por_100k', trendline='ols'
                                ).data[1]
                            )
                    
                    # Adicionar anotação explicativa
                    fig.add_annotation(
                        text="Linhas tracejadas representam tendências lineares",
                        xref="paper", yref="paper",
                        x=0.5, y=-0.1, 
                        showarrow=False,
                        font=dict(size=10, color="gray")
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar tabela com dados em um expander
                    with st.expander("Ver dados de taxa por 100.000 habitantes por região e ano"):
                        st.dataframe(df_taxas_regiao.sort_values(['Região', 'ano']))
                else:
                    st.warning("Não foi possível calcular taxas por 100.000 habitantes por região. Verifique se os dados populacionais para os filtros selecionados estão disponíveis no banco de dados.")

except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
    st.write("Verifique se o arquivo 'data/sih_2000_2024.csv' existe e está acessível.")

# Show data credits and information
st.markdown("---")
st.caption("Fonte: Sistema de Informações Hospitalares (SIH/SUS)")
st.caption("Dados de internações psiquiátricas no Brasil, período 2000-2024.") 

# Função para criar arquivo de exemplo de dados populacionais
def criar_arquivo_populacao_exemplo():
    try:
        # Criar diretório de dados se não existir
        if not os.path.exists('data'):
            os.makedirs('data')
        
        # Definir UFs e população aproximada
        populacao_uf = {
            '11': 1800000,    # Rondônia
            '12': 900000,     # Acre  
            '13': 4200000,    # Amazonas
            '14': 650000,     # Roraima
            '15': 8700000,    # Pará
            '16': 860000,     # Amapá
            '17': 1600000,    # Tocantins
            '21': 7100000,    # Maranhão
            '22': 3300000,    # Piauí
            '23': 9100000,    # Ceará
            '24': 3500000,    # Rio Grande do Norte
            '25': 4000000,    # Paraíba
            '26': 9600000,    # Pernambuco
            '27': 3300000,    # Alagoas
            '28': 2300000,    # Sergipe
            '29': 14900000,   # Bahia
            '31': 21200000,   # Minas Gerais
            '32': 4000000,    # Espírito Santo
            '33': 17400000,   # Rio de Janeiro
            '35': 46200000,   # São Paulo
            '41': 11500000,   # Paraná
            '42': 7200000,    # Santa Catarina
            '43': 11400000,   # Rio Grande do Sul
            '50': 2800000,    # Mato Grosso do Sul
            '51': 3500000,    # Mato Grosso
            '52': 7200000,    # Goiás
            '53': 3100000     # Distrito Federal
        }
        
        # Criar dataframe vazio
        dados = []
        
        # Dados para anos entre 2000 e 2023
        anos = range(2000, 2024)
        
        # Taxa de crescimento anual aproximada
        taxa_crescimento = 0.01
        
        # Para cada UF, criar uma entrada por ano
        for uf, pop_base in populacao_uf.items():
            for i, ano in enumerate(anos):
                # Simular crescimento populacional ao longo dos anos
                pop_estimada = int(pop_base * (1 + taxa_crescimento) ** i)
                
                # Adicionar um registro para o estado todo
                dados.append({
                    'ANO': ano,
                    'UF': uf,
                    'MUNICIPIO': uf + '0000',  # Código fictício para o estado todo
                    'POPULACAO': pop_estimada
                })
                
                # Adicionar alguns municípios fictícios para cada estado
                for j in range(1, 6):  # 5 municípios por estado
                    municipio_cod = uf + str(j).zfill(4)  # Ex: 350001, 350002, etc.
                    pop_municipio = int(pop_estimada * (0.05 + j * 0.03))  # Distribuição simples
                    
                    dados.append({
                        'ANO': ano,
                        'UF': uf,
                        'MUNICIPIO': municipio_cod,
                        'POPULACAO': pop_municipio
                    })
        
        # Criar DataFrame e salvar em CSV
        df_pop = pd.DataFrame(dados)
        df_pop.to_csv('data/populacao_ibge.csv', index=False)
        
        return True, "Arquivo de exemplo de dados populacionais criado com sucesso em 'data/populacao_ibge.csv'."
    except Exception as e:
        return False, f"Erro ao criar arquivo de exemplo: {str(e)}"