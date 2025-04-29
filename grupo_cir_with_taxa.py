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
    page_title="Análise por Classificação CIR",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Análise de Indicadores por Classificação CIR dos Municípios")
st.markdown("""
Este dashboard analisa indicadores de saúde mental em relação à Classificação CIR 
dos municípios brasileiros, permitindo análises comparativas por grupos de municípios.
""")

# Função para exibir resumo dos filtros aplicados
def mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, usar_raca_cor2=False, diag_grupo=None, diag_categoria=None, diag_subcategoria=None, proc_grupo=None):
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
    
    # Adicionar informação sobre o grupo de procedimento
    if proc_grupo:
        filtros_texto += f" | **Grupo de Procedimento:** {proc_grupo}"
    
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
            elif 'Taxa (%)' in df_ajustado.columns:
                # Calcular média ponderada baseada no tamanho dos grupos
                taxa_negra = df_ajustado.loc[mascara, 'Taxa (%)'].mean()
                
                # Remover linhas de Preta e Parda
                df_ajustado = df_ajustado[~mascara]
                
                # Adicionar linha para Negra
                nova_linha = pd.DataFrame({coluna_raca: ["Negra"], 'Taxa (%)': [taxa_negra]})
                df_ajustado = pd.concat([df_ajustado, nova_linha], ignore_index=True)
    
    return df_ajustado

# Load data
try:
    # Load main health data 
    df = load_health_data()
    
    # Load CIR classification data
    cir_result = load_cir_data()
    if cir_result:
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

    # Tab 1: Overview
    with st.expander("Visão Geral"):
        st.header("Visão Geral dos Indicadores por Grupo CIR")
        
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
        
        # Merge this data with the main dataframe to use numeric CIR groups
        filtered_df = filtered_df.merge(cir_numeric_df[['IBGE', 'Grupo_CIR']], left_on='MUNIC_RES', right_on='IBGE', how='left')
        
        # Verificar se existem dados após a filtragem
        if filtered_df.empty:
            st.warning("Não há dados disponíveis para os critérios selecionados. Por favor, altere os filtros.")
        else:
            # Update visualizations to use numeric CIR groups
            # Visualização: Taxa de Mortalidade por Grupo CIR
            st.subheader("Taxa de Mortalidade por Grupo CIR (Numérico)")
            
            # Verificar se a coluna Grupo_CIR existe no DataFrame
            if 'Grupo_CIR' not in filtered_df.columns:
                st.warning("A coluna 'Grupo_CIR' não está disponível no conjunto de dados. Verifique se o arquivo base_magda.xlsx está corretamente configurado.")
            else:
                mortalidade_por_grupo = calcular_taxa_mortalidade_municipio(filtered_df)
                
                # Verificar se Grupo_CIR existe no DataFrame resultante
                if 'Grupo_CIR' not in mortalidade_por_grupo.columns:
                    # Tentar fazer merge novamente
                    mortalidade_por_grupo = mortalidade_por_grupo.merge(
                        filtered_df[['MUNIC_RES', 'Grupo_CIR']].drop_duplicates(), 
                        on='MUNIC_RES', 
                        how='left'
                    )
                
                mortalidade_por_grupo = mortalidade_por_grupo.groupby('Grupo_CIR').agg({'taxa_mortalidade': 'mean'}).reset_index()
                
                fig = px.bar(
                    mortalidade_por_grupo, 
                    x='Grupo_CIR', 
                    y='taxa_mortalidade',
                    labels={'taxa_mortalidade': 'Taxa de Mortalidade (%)', 'Grupo_CIR': 'Grupo CIR (Numérico)'},
                    title='Taxa de Mortalidade Média por Grupo CIR (Numérico)'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Visualização: Número de Internações por Grupo CIR
            st.subheader("Número de Internações por Grupo CIR (Numérico)")
            
            # Verificar se a coluna Grupo_CIR existe no DataFrame
            if 'Grupo_CIR' not in filtered_df.columns:
                st.warning("A coluna 'Grupo_CIR' não está disponível para a visualização de número de internações.")
            else:
                internacoes_por_grupo = filtered_df.groupby('Grupo_CIR').size().reset_index(name='Contagem')
                internacoes_por_grupo.columns = ['Grupo CIR (Numérico)', 'Número de Internações']
                
                fig = px.bar(
                    internacoes_por_grupo, 
                    x='Grupo CIR (Numérico)', 
                    y='Número de Internações',
                    labels={'Número de Internações': 'Número de Internações', 'Grupo CIR (Numérico)': 'Grupo CIR (Numérico)'},
                    title='Número de Internações por Grupo CIR (Numérico)'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Visualização: Tempo Médio de Permanência por Grupo CIR
            st.subheader("Tempo Médio de Permanência por Grupo CIR (Numérico)")
            
            # Verificar se a coluna Grupo_CIR existe no DataFrame
            if 'Grupo_CIR' not in filtered_df.columns:
                st.warning("A coluna 'Grupo_CIR' não está disponível para a visualização de tempo médio de permanência.")
            else:
                permanencia_por_grupo = calcular_tempo_permanencia_municipio(filtered_df)
                
                # Verificar se Grupo_CIR existe no DataFrame resultante
                if 'Grupo_CIR' not in permanencia_por_grupo.columns:
                    # Tentar fazer merge novamente
                    permanencia_por_grupo = permanencia_por_grupo.merge(
                        filtered_df[['MUNIC_RES', 'Grupo_CIR']].drop_duplicates(), 
                        on='MUNIC_RES', 
                        how='left'
                    )
                
                permanencia_por_grupo = permanencia_por_grupo.groupby('Grupo_CIR').agg({'tempo_medio_permanencia': 'mean'}).reset_index()
                
                fig = px.bar(
                    permanencia_por_grupo, 
                    x='Grupo_CIR', 
                    y='tempo_medio_permanencia',
                    labels={'tempo_medio_permanencia': 'Tempo Médio de Permanência (dias)', 'Grupo_CIR': 'Grupo CIR (Numérico)'},
                    title='Tempo Médio de Permanência por Grupo CIR (Numérico)'
                )
                st.plotly_chart(fig, use_container_width=True)
                
            # Visualização: Taxa de Internações por 100k Habitantes por Grupo CIR
            st.subheader("Taxa de Internações por 100k Habitantes por Grupo CIR (Numérico)")
            
            # Verificar se a coluna Grupo_CIR existe no DataFrame
            if 'Grupo_CIR' not in filtered_df.columns:
                st.warning("A coluna 'Grupo_CIR' não está disponível para a visualização de taxa de internações por 100k habitantes.")
            else:
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
                
                # Verificar se há dados de população
                if df_pop.empty:
                    st.warning("Não há dados de população disponíveis para calcular a taxa por 100k habitantes.")
                else:
                    # Calcular taxa de internações por 100k habitantes
                    taxa_internacao = calcular_taxa_internacao_por_100k(filtered_df, df_pop)
                    
                    # Verificar se Grupo_CIR existe no DataFrame resultante
                    if 'Grupo_CIR' not in taxa_internacao.columns:
                        # Tentar fazer merge novamente
                        taxa_internacao = taxa_internacao.merge(
                            filtered_df[['MUNIC_RES', 'Grupo_CIR']].drop_duplicates(), 
                            on='MUNIC_RES', 
                            how='left'
                        )
                    
                    # Agrupar por Grupo_CIR
                    taxa_por_grupo = taxa_internacao.groupby('Grupo_CIR').agg({'taxa_por_100k': 'mean'}).reset_index()
                    
                    # Criar gráfico
                    fig = px.bar(
                        taxa_por_grupo, 
                        x='Grupo_CIR', 
                        y='taxa_por_100k',
                        labels={'taxa_por_100k': 'Taxa por 100k habitantes', 'Grupo_CIR': 'Grupo CIR (Numérico)'},
                        title='Taxa de Internações por 100k Habitantes por Grupo CIR (Numérico)'
                    )
                    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}") 