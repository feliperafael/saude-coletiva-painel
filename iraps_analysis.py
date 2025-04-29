import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Importar funções auxiliares dos módulos utils
from utils.helpers import mostrar_filtros_aplicados, ajustar_dados_raca, load_municipalities, get_estados_dict
from utils.data_loaders import (load_health_data, load_idsc_data, load_cir_data, 
                               calcular_taxa_mortalidade_municipio, calcular_tempo_permanencia_municipio,
                               load_population_data, calcular_taxa_internacao_por_100k)

# Set page configuration
st.set_page_config(
    page_title="Análise de iRAPS",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Análise do Índice RAPS por Classificação CIR dos Municípios")
st.markdown("""
Este dashboard analisa o Índice RAPS (Rede de Atenção Psicossocial) em relação à Classificação CIR 
 dos municípios brasileiros, permitindo análises comparativas.
""")

# Load data
try:
    # Load main health data 
    df = load_health_data()
    
    # Load CIR classification data
    cir_result = load_cir_data()
    if cir_result is not None:
        cir_dict, cir_df = cir_result
    else:
        st.error("Não foi possível carregar os dados de CIR.")
        cir_dict, cir_df = {}, pd.DataFrame()
    
    # Load municipalities dictionary
    municipios_dict = load_municipalities()
    
    # Load CIR group data from base_magda.xlsx
    cir_numeric_df = pd.read_excel('data/base_magda.xlsx')
    
    # Display loading message
    with st.spinner('Carregando dados...'):
        data_load_state = st.success('Dados carregados com sucesso!')
        
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
    
    # Filtro por Estado
    estados = get_estados_dict()
    estado_nome = st.sidebar.selectbox("Estado:", list(estados.keys()))
    estado_codigo = estados[estado_nome]
    
    # Filtro por Município (se um estado estiver selecionado)
    codigo_municipio = None
    if estado_nome != "Todos":
        # Filtrar municípios pelo estado selecionado
        municipios_estado = {k: v for k, v in municipios_dict.items() if k.startswith(estado_codigo)}
        
        # Criar lista para o selectbox com o formato: "Nome do Município (Código)"
        municipios_lista = ["Todos"] + [f"{v} ({k})" for k, v in municipios_estado.items()]
        
        municipio_selecionado = st.sidebar.selectbox("Município:", municipios_lista)
        
        # Extrair o código do município, se selecionado
        if municipio_selecionado != "Todos":
            codigo_municipio = municipio_selecionado.split("(")[1].replace(")", "").strip()
    
    # Filtro por sexo
    sexo = st.sidebar.selectbox("Sexo:", ["Todos", "Masculino", "Feminino"])
    
    # Filtro por faixa etária
    faixas_etarias = ["Todas", "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", 
                       "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", 
                       "70-74", "75-79", "80-84", "85-89", "90+"]
    faixa_etaria = st.sidebar.selectbox("Faixa Etária:", faixas_etarias)
    
    # Filtro por raça/cor
    if usar_raca_cor2:
        racas = ["Todas", "Branca", "Negra", "Amarela", "Indígena", "Sem informação"]
    else:
        racas = ["Todas", "Branca", "Preta", "Parda", "Amarela", "Indígena", "Sem informação"]
    
    raca = st.sidebar.selectbox("Raça/Cor:", racas)
    
    # Filtro por Grupo CIR
    grupos_cir = ["Todos"] + sorted(cir_df['grupo_cir'].unique().tolist())
    grupo_cir_selecionado = st.sidebar.selectbox("Grupo CIR:", grupos_cir)
    
    # Diagnostic Group Filter using tree structure
    # Get unique diagnostic groups
    grupos_diagnosticos = ["Todos"] + sorted(df['def_diag_princ_grupo'].unique().tolist())
    diag_grupo = st.sidebar.selectbox("Grupo Diagnóstico:", grupos_diagnosticos)
    
    # Initialize category and subcategory filters
    diag_categoria = None
    diag_subcategoria = None
    
    # If a diagnostic group is selected, show categories
    if diag_grupo != "Todos":
        df_filtered_grupo = df[df['def_diag_princ_grupo'] == diag_grupo]
        categorias = ["Todas"] + sorted(df_filtered_grupo['def_diag_princ_cat'].unique().tolist())
        diag_categoria = st.sidebar.selectbox("Categoria Diagnóstica:", categorias)
        
        # If a category is selected, show subcategories
        if diag_categoria != "Todas":
            df_filtered_cat = df_filtered_grupo[df_filtered_grupo['def_diag_princ_cat'] == diag_categoria]
            subcategorias = ["Todas"] + sorted(df_filtered_cat['def_diag_princ_subcategoria'].unique().tolist())
            diag_subcategoria = st.sidebar.selectbox("Subcategoria Diagnóstica:", subcategorias)

    # Main content for iRAPS analysis
    st.header("Análise do Índice RAPS por Grupo CIR")
    
    # Filtrar dados conforme os filtros aplicados
    filtered_df = df.copy()
    
    # Filtrar por ano
    filtered_df = filtered_df[
        (filtered_df['ANO_CMPT'] >= year_range[0]) & 
        (filtered_df['ANO_CMPT'] <= year_range[1])
    ]
    
    # Filtrar por estado
    if estado_codigo:
        filtered_df = filtered_df[filtered_df['res_CODIGO_UF'].astype(str) == estado_codigo]
    
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
            '90+': (90, float('inf'))
        }
        age_min, age_max = age_ranges[faixa_etaria]
        filtered_df = filtered_df[(filtered_df['IDADE'] >= age_min) & (filtered_df['IDADE'] <= age_max)]
    
    # Filtrar por raça/cor
    if raca != "Todas":
        if usar_raca_cor2 and raca == "Negra":
            filtered_df = filtered_df[filtered_df['RACA_COR_DESC'].isin(["Preta", "Parda"])]
        else:
            filtered_df = filtered_df[filtered_df['RACA_COR_DESC'] == raca]
    
    # Filtrar por grupo CIR
    if grupo_cir_selecionado != "Todos":
        filtered_df = filtered_df[filtered_df['MUNIC_RES'].map(cir_dict) == grupo_cir_selecionado]
    
    # Filtrar por grupo diagnóstico
    if diag_grupo != "Todos":
        filtered_df = filtered_df[filtered_df['def_diag_princ_grupo'] == diag_grupo]
        
        # Filtrar por categoria diagnóstica
        if diag_categoria != "Todas":
            filtered_df = filtered_df[filtered_df['def_diag_princ_cat'] == diag_categoria]
            
            # Filtrar por subcategoria diagnóstica
            if diag_subcategoria != "Todas":
                filtered_df = filtered_df[filtered_df['def_diag_princ_subcategoria'] == diag_subcategoria]
    
    # Mostrar resumo dos filtros aplicados
    mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2, diag_grupo, diag_categoria, diag_subcategoria, grupo_cir_selecionado)
    
    # Verificar se temos dados filtrados disponíveis
    if filtered_df.empty:
        st.warning("Não há dados disponíveis para os critérios selecionados. Por favor, altere os filtros.")
    else:
        # Garantir que os tipos de dados sejam compatíveis para o merge
        filtered_df_copy = filtered_df.copy()
        filtered_df_copy['MUNIC_RES'] = filtered_df_copy['MUNIC_RES'].astype(str)
        cir_numeric_copy = cir_numeric_df.copy()
        cir_numeric_copy['IBGE'] = cir_numeric_copy['IBGE'].astype(str)
        
        # Merge com os dados de grupo CIR numérico
        filtered_df = filtered_df_copy.merge(cir_numeric_copy[['IBGE', 'Grupo_CIR']], 
                                            left_on='MUNIC_RES', 
                                            right_on='IBGE', 
                                            how='left')
        
        # Verificar se a coluna iRAPS existe no DataFrame base_magda
        if 'iRAPS' not in cir_numeric_df.columns:
            st.warning("A variável iRAPS não está disponível no conjunto de dados. Verifique se o arquivo base_magda.xlsx contém esta coluna.")
        else:
            st.subheader("Distribuição de iRAPS por Grupo CIR")
            
            # Agregar os dados por Grupo_CIR
            iraps_por_grupo = filtered_df.dropna(subset=['Grupo_CIR']).merge(
                cir_numeric_copy[['IBGE', 'iRAPS']], 
                left_on='MUNIC_RES',
                right_on='IBGE',
                how='left'
            )
            
            # Verificar se temos dados suficientes após a filtragem
            if iraps_por_grupo['iRAPS'].notna().sum() == 0:
                st.warning("Não há dados suficientes de iRAPS para os filtros selecionados.")
            else:
                # Gráfico de boxplot para visualizar a distribuição de iRAPS por grupo
                fig_box = px.box(
                    iraps_por_grupo, 
                    x='Grupo_CIR', 
                    y='iRAPS',
                    labels={'Grupo_CIR': 'Grupo CIR (Numérico)', 'iRAPS': 'Índice RAPS'},
                    title='Distribuição do Índice RAPS por Grupo CIR'
                )
                st.plotly_chart(fig_box, use_container_width=True)
                
                # Calcular a média de iRAPS por grupo
                iraps_medio = iraps_por_grupo.groupby('Grupo_CIR')['iRAPS'].mean().reset_index()
                
                # Gráfico de barras para a média de iRAPS por grupo
                fig_bar = px.bar(
                    iraps_medio, 
                    x='Grupo_CIR', 
                    y='iRAPS',
                    labels={'Grupo_CIR': 'Grupo CIR (Numérico)', 'iRAPS': 'Índice RAPS Médio'},
                    title='Índice RAPS Médio por Grupo CIR'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # Taxa de internações por 100k habitantes vs iRAPS
                st.subheader("Relação entre Taxa de Internações e iRAPS")
                
                # Obter dados de população com base nos filtros aplicados
                year_filter = year_range[0] if year_range[0] == year_range[1] else None
                state_code = estado_codigo if estado_nome != "Todos" else None
                mun_code = codigo_municipio if codigo_municipio else None
                
                # Carregar dados de população
                df_pop = load_population_data(year=year_filter, state_code=state_code, municipality_code=mun_code)
                
                # Se não houver dados de população específicos para o ano selecionado, use os dados disponíveis
                if df_pop.empty and year_filter:
                    df_pop = load_population_data(state_code=state_code, municipality_code=mun_code)
                    if not df_pop.empty:
                        st.info(f"Usando dados de população do ano {df_pop['ano'].iloc[0]} por falta de dados específicos para {year_filter}.")
                
                # Verificar se temos dados de população
                if df_pop.empty:
                    st.warning("Não há dados de população disponíveis para calcular a taxa por 100k habitantes.")
                else:
                    try:
                        # Calcular taxa de internações por 100k habitantes
                        taxa_internacao = calcular_taxa_internacao_por_100k(filtered_df_copy, df_pop)
                        
                        # Garantir que os tipos de dados sejam compatíveis
                        taxa_internacao['MUNIC_RES'] = taxa_internacao['MUNIC_RES'].astype(str)
                        
                        # Adicionar iRAPS aos dados de taxa
                        taxa_vs_iraps = taxa_internacao.merge(
                            cir_numeric_copy[['IBGE', 'iRAPS', 'Grupo_CIR']], 
                            left_on='MUNIC_RES',
                            right_on='IBGE',
                            how='left'
                        )
                        
                        # Verificar se temos dados suficientes após o merge
                        if taxa_vs_iraps['iRAPS'].notna().sum() == 0:
                            st.warning("Não há dados suficientes para análise de correlação entre taxa de internações e iRAPS.")
                        else:
                            # Convertemos Grupo_CIR para string para evitar erros de tipo no plotly
                            if 'Grupo_CIR' in taxa_vs_iraps.columns:
                                taxa_vs_iraps['Grupo_CIR'] = taxa_vs_iraps['Grupo_CIR'].astype(str)
                            
                            # Gráfico de dispersão relacionando taxa por 100k vs iRAPS
                            fig_scatter = px.scatter(
                                taxa_vs_iraps, 
                                x='iRAPS', 
                                y='taxa_por_100k',
                                color='Grupo_CIR',
                                size='populacao',
                                hover_name='cod_municipio',
                                labels={
                                    'iRAPS': 'Índice RAPS', 
                                    'taxa_por_100k': 'Taxa de Internações por 100k habitantes',
                                    'Grupo_CIR': 'Grupo CIR'
                                },
                                title='Relação entre Taxa de Internações e Índice RAPS'
                            )
                            st.plotly_chart(fig_scatter, use_container_width=True)
                            
                            # Calcular correlação entre taxa e iRAPS
                            corr = taxa_vs_iraps['iRAPS'].corr(taxa_vs_iraps['taxa_por_100k'])
                            st.metric("Correlação entre Taxa de Internações e iRAPS", f"{corr:.3f}")
                            
                            if corr < 0:
                                st.info("A correlação negativa indica que quanto maior o Índice RAPS, menor a taxa de internações por 100k habitantes.")
                            elif corr > 0:
                                st.info("A correlação positiva indica que quanto maior o Índice RAPS, maior a taxa de internações por 100k habitantes.")
                            else:
                                st.info("Não há correlação significativa entre o Índice RAPS e a taxa de internações.")
                    except Exception as e:
                        st.error(f"Erro ao calcular correlação: {e}")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}") 