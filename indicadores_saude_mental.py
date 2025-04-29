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
                               calcular_taxa_mortalidade_municipio, calcular_tempo_permanencia_municipio)

# Set page configuration
st.set_page_config(
    page_title="Indicadores de Saúde Mental",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Análise de Indicadores de Saúde Mental (iCAPS e iRAPS)")
st.markdown("""
Este dashboard explora as relações entre os indicadores de saúde mental iCAPS e iRAPS 
e outros indicadores de saúde, utilizando dados do Sistema de Informações Hospitalares (SIH).
""")

# Função para carregar dados do base_magda.xlsx
@st.cache_data
def load_magda_data():
    try:
        magda_df = pd.read_excel('data/base_magda.xlsx')
        return magda_df
    except Exception as e:
        st.error(f"Erro ao carregar dados da base magda: {e}")
        return pd.DataFrame()

# Load data
try:
    # Load main health data
    df = load_health_data()
    
    # Load base magda data
    magda_df = load_magda_data()
    
    # Garantir que a coluna IBGE seja string
    magda_df['IBGE'] = magda_df['IBGE'].astype(str)
    
    # Load CIR classification data
    cir_dict, cir_df = load_cir_data()
    
    # Load municipalities dictionary
    municipios_dict = load_municipalities()
    
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
    
    # Agregar dados por município
    # Calcular taxa de mortalidade
    taxa_mortalidade_municipio = calcular_taxa_mortalidade_municipio(filtered_df)
    
    # Calcular tempo médio de permanência
    tempo_permanencia_municipio = calcular_tempo_permanencia_municipio(filtered_df)
    
    # Número de internações
    internacoes_por_municipio = filtered_df.groupby('MUNIC_RES').size().reset_index(name='numero_internacoes')
    
    # Garantir que as colunas de chave sejam do mesmo tipo (string)
    internacoes_por_municipio['MUNIC_RES'] = internacoes_por_municipio['MUNIC_RES'].astype(str)
    magda_df['IBGE'] = magda_df['IBGE'].astype(str)
    
    # Integrar com dados de iCAPS e iRAPS
    # Mesclar com dados da base_magda
    dados_completos = internacoes_por_municipio.merge(
        magda_df[['IBGE', 'MUNICIPIO.x', 'iCAPS', 'iRAPS', 'Grupo_CIR']], 
        left_on='MUNIC_RES', 
        right_on='IBGE', 
        how='inner'
    )
    
    # Adicionar taxa de mortalidade
    dados_completos = dados_completos.merge(
        taxa_mortalidade_municipio[['MUNIC_RES', 'taxa_mortalidade']], 
        on='MUNIC_RES', 
        how='left'
    )
    
    # Adicionar tempo médio de permanência
    dados_completos = dados_completos.merge(
        tempo_permanencia_municipio[['MUNIC_RES', 'tempo_medio_permanencia']], 
        on='MUNIC_RES', 
        how='left'
    )
    
    # Mostrar resumo dos filtros aplicados
    mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, 
                             usar_raca_cor2=usar_raca_cor2, diag_grupo=diag_grupo, diag_categoria=diag_categoria, 
                             diag_subcategoria=diag_subcategoria, grupo_cir=grupo_cir_selecionado)
    
    # Criar abas para diferentes visualizações
    tabs = st.tabs(["Visão Geral", "iCAPS", "iRAPS", "Correlações", "Dados"])
    
    # Verificar se existem dados suficientes para análise
    if len(dados_completos) < 2:
        st.warning("Não há dados suficientes para análise com os filtros selecionados. Por favor, ajuste os filtros.")
    else:
        # Tab 1: Visão Geral
        with tabs[0]:
            st.header("Visão Geral dos Indicadores")
            
            # Estatísticas Resumidas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Municípios", len(dados_completos))
                
            with col2:
                st.metric("Média iCAPS", f"{dados_completos['iCAPS'].mean():.2f}")
                
            with col3:
                st.metric("Média iRAPS", f"{dados_completos['iRAPS'].mean():.2f}")
            
            # Distribuição dos indicadores por Grupo CIR
            st.subheader("Indicadores por Grupo CIR")
            
            # Verificar se existe a coluna Grupo_CIR nos dados
            if 'Grupo_CIR' in dados_completos.columns:
                # Calculando médias por grupo CIR
                grupo_cir_stats = dados_completos.groupby('Grupo_CIR').agg({
                    'iCAPS': 'mean',
                    'iRAPS': 'mean',
                    'taxa_mortalidade': 'mean',
                    'tempo_medio_permanencia': 'mean'
                }).reset_index()
                
                # Gráfico de barras para iCAPS por Grupo CIR
                fig = px.bar(
                    grupo_cir_stats,
                    x='Grupo_CIR',
                    y='iCAPS',
                    title='Média de iCAPS por Grupo CIR',
                    labels={'Grupo_CIR': 'Grupo CIR', 'iCAPS': 'iCAPS (média)'},
                    color='iCAPS'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Gráfico de barras para iRAPS por Grupo CIR
                fig = px.bar(
                    grupo_cir_stats,
                    x='Grupo_CIR',
                    y='iRAPS',
                    title='Média de iRAPS por Grupo CIR',
                    labels={'Grupo_CIR': 'Grupo CIR', 'iRAPS': 'iRAPS (média)'},
                    color='iRAPS'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Dados de Grupo CIR não disponíveis")
        
        # Tab 2: iCAPS
        with tabs[1]:
            st.header("Análise do Indicador iCAPS")
            
            # Histograma de iCAPS
            st.subheader("Distribuição do Indicador iCAPS")
            fig = px.histogram(
                dados_completos,
                x='iCAPS',
                nbins=20,
                title='Distribuição do Indicador iCAPS',
                labels={'iCAPS': 'iCAPS', 'count': 'Número de Municípios'},
                color_discrete_sequence=['#636EFA']
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # iCAPS vs Taxa de Mortalidade
            st.subheader("iCAPS vs Taxa de Mortalidade")
            fig = px.scatter(
                dados_completos,
                x='iCAPS',
                y='taxa_mortalidade',
                title='Relação entre iCAPS e Taxa de Mortalidade',
                labels={'iCAPS': 'iCAPS', 'taxa_mortalidade': 'Taxa de Mortalidade (%)'},
                hover_name='MUNICIPIO.x',
                color='Grupo_CIR' if 'Grupo_CIR' in dados_completos.columns else None,
                size='numero_internacoes',
                size_max=30
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # iCAPS vs Tempo de Permanência
            st.subheader("iCAPS vs Tempo Médio de Permanência")
            fig = px.scatter(
                dados_completos,
                x='iCAPS',
                y='tempo_medio_permanencia',
                title='Relação entre iCAPS e Tempo Médio de Permanência',
                labels={'iCAPS': 'iCAPS', 'tempo_medio_permanencia': 'Tempo Médio de Permanência (dias)'},
                hover_name='MUNICIPIO.x',
                color='Grupo_CIR' if 'Grupo_CIR' in dados_completos.columns else None,
                size='numero_internacoes',
                size_max=30
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
        
        # Tab 3: iRAPS
        with tabs[2]:
            st.header("Análise do Indicador iRAPS")
            
            # Histograma de iRAPS
            st.subheader("Distribuição do Indicador iRAPS")
            fig = px.histogram(
                dados_completos,
                x='iRAPS',
                nbins=20,
                title='Distribuição do Indicador iRAPS',
                labels={'iRAPS': 'iRAPS', 'count': 'Número de Municípios'},
                color_discrete_sequence=['#EF553B']
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # iRAPS vs Taxa de Mortalidade
            st.subheader("iRAPS vs Taxa de Mortalidade")
            fig = px.scatter(
                dados_completos,
                x='iRAPS',
                y='taxa_mortalidade',
                title='Relação entre iRAPS e Taxa de Mortalidade',
                labels={'iRAPS': 'iRAPS', 'taxa_mortalidade': 'Taxa de Mortalidade (%)'},
                hover_name='MUNICIPIO.x',
                color='Grupo_CIR' if 'Grupo_CIR' in dados_completos.columns else None,
                size='numero_internacoes',
                size_max=30
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # iRAPS vs Tempo de Permanência
            st.subheader("iRAPS vs Tempo Médio de Permanência")
            fig = px.scatter(
                dados_completos,
                x='iRAPS',
                y='tempo_medio_permanencia',
                title='Relação entre iRAPS e Tempo Médio de Permanência',
                labels={'iRAPS': 'iRAPS', 'tempo_medio_permanencia': 'Tempo Médio de Permanência (dias)'},
                hover_name='MUNICIPIO.x',
                color='Grupo_CIR' if 'Grupo_CIR' in dados_completos.columns else None,
                size='numero_internacoes',
                size_max=30
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
        
        # Tab 4: Correlações
        with tabs[3]:
            st.header("Correlações entre Indicadores")
            
            # Matriz de correlação
            st.subheader("Matriz de Correlação")
            
            # Selecionar colunas numéricas para a matriz de correlação
            colunas_numericas = ['iCAPS', 'iRAPS', 'taxa_mortalidade', 'tempo_medio_permanencia', 'numero_internacoes']
            corr_data = dados_completos[colunas_numericas].corr()
            
            # Gerar o mapa de calor
            fig = px.imshow(
                corr_data,
                text_auto=True,
                title='Matriz de Correlação entre Indicadores',
                color_continuous_scale='RdBu_r',
                labels=dict(x='Indicadores', y='Indicadores', color='Correlação')
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # Relação entre iCAPS e iRAPS
            st.subheader("Relação entre iCAPS e iRAPS")
            fig = px.scatter(
                dados_completos,
                x='iCAPS',
                y='iRAPS',
                title='Relação entre iCAPS e iRAPS',
                labels={'iCAPS': 'iCAPS', 'iRAPS': 'iRAPS'},
                hover_name='MUNICIPIO.x',
                color='Grupo_CIR' if 'Grupo_CIR' in dados_completos.columns else None,
                size='numero_internacoes',
                size_max=30,
                trendline='ols'  # adicionar linha de tendência
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # Calcular e mostrar a correlação estatística
            corr_icaps_iraps = dados_completos['iCAPS'].corr(dados_completos['iRAPS'])
            st.info(f"Correlação entre iCAPS e iRAPS: {corr_icaps_iraps:.4f}")
        
        # Tab 5: Dados Brutos
        with tabs[4]:
            st.header("Tabela de Dados")
            
            # Mostrar dados agregados
            st.dataframe(dados_completos)
            
            # Opção para download
            csv = dados_completos.to_csv(index=False)
            st.download_button(
                label="Download dos dados em CSV",
                data=csv,
                file_name="indicadores_saude_mental.csv",
                mime="text/csv"
            )

# Tratamento de exceções
except Exception as e:
    st.error(f"Erro ao processar dados: {e}")
    st.write("Detalhes do erro:", e)

# Rodapé com informações
st.markdown("---")
st.caption("Fonte: Sistema de Informações Hospitalares (SIH/SUS) e Base Magda")
st.caption("Dados de internações psiquiátricas no Brasil e indicadores iCAPS e iRAPS") 