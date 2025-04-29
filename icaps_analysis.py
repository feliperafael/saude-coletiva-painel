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
    page_title="Análise de iCAPS",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Análise de Índices iCAPS e iRAPS")
st.markdown("""
Este dashboard analisa o Índice CAPS (Centros de Atenção Psicossocial) e o Índice RAPS (Rede de Atenção Psicossocial)
calculados a partir do número total de internações e da taxa de internações por 100 mil habitantes.
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

    # Main content for analysis
    st.header("Análise dos Índices iCAPS e iRAPS")
    
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
        # Criar uma cópia do DataFrame filtrado para usar nos cálculos
        filtered_df_copy = filtered_df.copy()
        filtered_df_copy['MUNIC_RES'] = filtered_df_copy['MUNIC_RES'].astype(str)
        
        # Cálculo do número total de internações
        st.subheader("Número Total de Internações")
        total_internacoes = len(filtered_df_copy)
        st.metric("Total de Internações", f"{total_internacoes:,}".replace(",", "."))
        
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
                
                # Verificar se a coluna 'nome_municipio' existe no DataFrame
                if 'nome_municipio' not in taxa_internacao.columns:
                    # Adicionar nomes dos municípios para melhor visualização
                    taxa_internacao['nome_municipio'] = taxa_internacao['cod_municipio'].map(
                        lambda x: next((v for k, v in municipios_dict.items() if k == x), "Desconhecido")
                    )
                
                # Carregar ou calcular índices iCAPS e iRAPS
                try:
                    # Criar DataFrame para armazenar os índices por município
                    indices_df = pd.DataFrame()
                    indices_df['MUNIC_RES'] = taxa_internacao['cod_municipio']
                    indices_df['nome_municipio'] = taxa_internacao['nome_municipio']
                    
                    # Carregar os índices iCAPS e iRAPS do arquivo Excel
                    try:
                        st.info("Carregando índices iCAPS e iRAPS do arquivo base_magda.xlsx...")
                        # Carregar dados do Excel
                        base_magda = pd.read_excel("data/base_magda.xlsx")
                        
                        # Exibir informações sobre as colunas disponíveis para debug
                        st.write("Colunas disponíveis no arquivo:", list(base_magda.columns))
                        
                        # Adicionar informação importante sobre a diferença entre códigos
                        st.warning("""
                        **Atenção**: O arquivo base_magda.xlsx utiliza o código IBGE dos municípios, 
                        enquanto a base de internações utiliza o código MUNIC_RES (código do CNES). 
                        Estes códigos podem ser diferentes, o que pode causar problemas no mapeamento.
                        
                        Se muitos municípios ficarem sem dados, pode ser necessário criar uma tabela de 
                        correspondência entre os códigos IBGE e MUNIC_RES.
                        """)
                        
                        # Verificar se as colunas necessárias existem
                        colunas_necessarias = ['IBGE', 'iCAPS', 'iRAPS']
                        print("Colunas disponíveis:", base_magda.columns)
                        if not all(coluna in base_magda.columns for coluna in colunas_necessarias):
                            st.warning(f"O arquivo base_magda.xlsx não contém todas as colunas necessárias: {colunas_necessarias}")
                            # Se não encontrar as colunas exatas, procurar por correspondências aproximadas
                            colunas_disponiveis = base_magda.columns.tolist()
                            
                            # Mapear colunas disponíveis para as necessárias
                            col_map = {}
                            for col_necessaria in colunas_necessarias:
                                # Procurar correspondência exata primeiro
                                if col_necessaria in colunas_disponiveis:
                                    col_map[col_necessaria] = col_necessaria
                                # Procurar correspondência case-insensitive
                                elif any(col.upper() == col_necessaria.upper() for col in colunas_disponiveis):
                                    col_map[col_necessaria] = next(col for col in colunas_disponiveis if col.upper() == col_necessaria.upper())
                            
                            # Se ainda não tiver encontrado a coluna do município, procurar por alternativas
                            if 'IBGE' not in col_map:
                                possiveis_colunas_municipio = ['MUNICIPIO_IBGE', 'COD_IBGE', 'CODIGO_IBGE', 'MUNIC_RES', 'CODMUN', 'CODIBGE']
                                for possivel in possiveis_colunas_municipio:
                                    if possivel in colunas_disponiveis:
                                        col_map['IBGE'] = possivel
                                        break
                                    elif any(col.upper() == possivel.upper() for col in colunas_disponiveis):
                                        col_map['IBGE'] = next(col for col in colunas_disponiveis if col.upper() == possivel.upper())
                                        break
                            
                            # Verificar se conseguimos mapear todas as colunas
                            if len(col_map) < len(colunas_necessarias):
                                st.error(f"Não foi possível encontrar todas as colunas necessárias no arquivo. Colunas encontradas: {col_map}")
                                raise ValueError("Colunas necessárias não encontradas no arquivo base_magda.xlsx")
                            
                            # Renomear as colunas encontradas para os nomes esperados
                            base_magda = base_magda.rename(columns={col_map[col_necessaria]: col_necessaria for col_necessaria in colunas_necessarias})
                        
                        # Garantir que o código do município seja uma string para o merge
                        base_magda['IBGE'] = base_magda['IBGE'].astype(str)
                        
                        # Mesclar os dados de índices com os dados de municípios
                        indices_df = indices_df.merge(
                            base_magda[['IBGE', 'iCAPS', 'iRAPS']],
                            left_on='MUNIC_RES',
                            right_on='IBGE',
                            how='left'
                        )
                        
                        # Verificar se há valores NaN após o merge
                        if indices_df['iCAPS'].isna().any() or indices_df['iRAPS'].isna().any():
                            num_nan = indices_df['iCAPS'].isna().sum()
                            st.warning(f"Não foram encontrados índices para {num_nan} municípios no arquivo base_magda.xlsx. Isso pode ocorrer se o código IBGE não corresponder ao MUNIC_RES.")
                            
                            # Informar ao usuário sobre os municípios sem correspondência
                            if num_nan < 20:  # Limitar para não sobrecarregar a interface
                                municipios_sem_dados = indices_df[indices_df['iCAPS'].isna()]['nome_municipio'].tolist()
                                st.warning(f"Municípios sem dados de índices: {', '.join(municipios_sem_dados)}")
                            
                            # Informações sobre os formatos de códigos
                            st.info("""
                            Nota sobre o mapeamento de códigos: 
                            - Na base de internações, o código do município é o MUNIC_RES (código CNES) 
                            - No arquivo base_magda.xlsx, o código é o IBGE
                            - Se o código MUNIC_RES for diferente do IBGE, pode haver falhas no mapeamento
                            """)
                        
                        st.success(f"Índices carregados para {len(indices_df) - indices_df['iCAPS'].isna().sum()} municípios")
                        
                    except FileNotFoundError:
                        st.error("Arquivo data/base_magda.xlsx não encontrado. Usando valores simulados para demonstração.")
                        # Gerar valores simulados como fallback
                        np.random.seed(42)  # Para reprodutibilidade
                        indices_df['iCAPS'] = np.random.uniform(0, 1, size=len(indices_df))
                        indices_df['iRAPS'] = np.random.uniform(0, 1, size=len(indices_df))
                    except Exception as e:
                        st.error(f"Erro ao carregar os índices do arquivo: {e}. Usando valores simulados.")
                        # Gerar valores simulados como fallback
                        np.random.seed(42)  # Para reprodutibilidade
                        indices_df['iCAPS'] = np.random.uniform(0, 1, size=len(indices_df))
                        indices_df['iRAPS'] = np.random.uniform(0, 1, size=len(indices_df))
                    
                    # Mesclar os índices com os dados de taxa de internação
                    dados_completos = taxa_internacao.merge(
                        indices_df,
                        left_on='cod_municipio',
                        right_on='MUNIC_RES',
                        how='inner'
                    )
                    
                    # Verificar se temos dados após o merge
                    if not dados_completos.empty:
                        # Unificar nome do município (caso tenha duplicatas após o merge)
                        if 'nome_municipio_x' in dados_completos.columns:
                            dados_completos = dados_completos.rename(columns={'nome_municipio_x': 'nome_municipio'})
                            if 'nome_municipio_y' in dados_completos.columns:
                                dados_completos = dados_completos.drop(columns=['nome_municipio_y'])
                        
                        # Preparar dados para visualização
                        dados_viz = dados_completos.copy()
                        
                        # Lidar com valores NaN na coluna de população
                        if 'populacao' in dados_viz.columns:
                            # Substituir valores NaN na população pela mediana ou por um valor fixo
                            mediana_pop = dados_viz['populacao'].median()
                            # Verificar se a mediana também é NaN
                            if pd.isna(mediana_pop):
                                # Se a mediana for NaN, usar um valor fixo
                                dados_viz['populacao_para_grafico'] = 5000  # Valor padrão
                            else:
                                # Substituir NaNs pela mediana
                                dados_viz['populacao_para_grafico'] = dados_viz['populacao'].fillna(mediana_pop)
                        else:
                            # Se não existir a coluna população, criar uma com valor fixo
                            dados_viz['populacao_para_grafico'] = 5000  # Valor padrão
                        
                        # Criar layout de duas colunas para os gráficos
                        st.header("Relação entre Índices de Saúde Mental e Taxa de Internações")
                        st.markdown("""
                        Os gráficos abaixo mostram a relação entre os índices de desenvolvimento de saúde mental 
                        dos municípios (iCAPS e iRAPS) e a taxa de internações psiquiátricas por 100 mil habitantes.
                        """)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Gráfico de dispersão entre iCAPS e Taxa por 100k
                            st.subheader("iCAPS vs Taxa de Internações por 100k")
                            
                            # Tratar valores NaN nas colunas usadas no gráfico
                            grafico_df = dados_viz.copy()
                            grafico_df = grafico_df.dropna(subset=['iCAPS', 'taxa_por_100k'])
                            
                            if len(grafico_df) > 0:
                                fig_icaps_taxa = px.scatter(
                                    grafico_df,
                                    x='iCAPS',
                                    y='taxa_por_100k',
                                    hover_name='nome_municipio',
                                    size='populacao_para_grafico',
                                    labels={
                                        'iCAPS': 'Índice iCAPS',
                                        'taxa_por_100k': 'Taxa de Internações por 100k habitantes'
                                    },
                                    title='Índice iCAPS vs Taxa de Internações Psiquiátricas por 100k',
                                    render_mode='webgl'  # Melhora performance para muitos pontos
                                )
                                st.plotly_chart(fig_icaps_taxa, use_container_width=True)
                                
                                # Calcular correlação (apenas para valores não-NaN)
                                corr_icaps = grafico_df['iCAPS'].corr(grafico_df['taxa_por_100k'])
                                st.metric("Correlação entre iCAPS e Taxa por 100k", f"{corr_icaps:.3f}")
                                
                                # Interpretação da correlação
                                if corr_icaps < -0.5:
                                    st.info("""
                                    Há uma forte correlação negativa entre o índice iCAPS e a taxa de internações. 
                                    Isso sugere que municípios com melhor desenvolvimento de saúde mental (maior iCAPS) 
                                    tendem a ter menos internações psiquiátricas.
                                    """)
                                elif corr_icaps > 0.5:
                                    st.info("""
                                    Há uma forte correlação positiva entre o índice iCAPS e a taxa de internações. 
                                    Isso pode indicar que municípios com maior iCAPS estão identificando e tratando 
                                    mais casos que necessitam internação.
                                    """)
                                else:
                                    st.info("""
                                    Não há uma correlação forte entre o índice iCAPS e a taxa de internações.
                                    Outros fatores podem estar influenciando a relação entre o desenvolvimento 
                                    da saúde mental e as internações psiquiátricas.
                                    """)
                            else:
                                st.warning("Não há dados suficientes para plotar o gráfico de iCAPS vs Taxa.")
                        
                        with col2:
                            # Gráfico de dispersão entre iRAPS e Taxa por 100k
                            st.subheader("iRAPS vs Taxa de Internações por 100k")
                            
                            # Tratar valores NaN nas colunas usadas no gráfico
                            grafico_df = dados_viz.copy()
                            grafico_df = grafico_df.dropna(subset=['iRAPS', 'taxa_por_100k'])
                            
                            if len(grafico_df) > 0:
                                fig_iraps_taxa = px.scatter(
                                    grafico_df,
                                    x='iRAPS',
                                    y='taxa_por_100k',
                                    hover_name='nome_municipio',
                                    size='populacao_para_grafico',
                                    labels={
                                        'iRAPS': 'Índice iRAPS',
                                        'taxa_por_100k': 'Taxa de Internações por 100k habitantes'
                                    },
                                    title='Índice iRAPS vs Taxa de Internações Psiquiátricas por 100k',
                                    render_mode='webgl'  # Melhora performance para muitos pontos
                                )
                                st.plotly_chart(fig_iraps_taxa, use_container_width=True)
                                
                                # Calcular correlação (apenas para valores não-NaN)
                                corr_iraps = grafico_df['iRAPS'].corr(grafico_df['taxa_por_100k'])
                                st.metric("Correlação entre iRAPS e Taxa por 100k", f"{corr_iraps:.3f}")
                                
                                # Interpretação da correlação
                                if corr_iraps < -0.5:
                                    st.info("""
                                    Há uma forte correlação negativa entre o índice iRAPS e a taxa de internações. 
                                    Isso sugere que municípios com melhor estrutura de Rede de Atenção Psicossocial (maior iRAPS) 
                                    tendem a ter menos internações psiquiátricas.
                                    """)
                                elif corr_iraps > 0.5:
                                    st.info("""
                                    Há uma forte correlação positiva entre o índice iRAPS e a taxa de internações. 
                                    Isso pode indicar que municípios com maior iRAPS estão identificando e tratando 
                                    mais casos que necessitam internação.
                                    """)
                                else:
                                    st.info("""
                                    Não há uma correlação forte entre o índice iRAPS e a taxa de internações.
                                    Outros fatores podem estar influenciando a relação entre a estrutura da 
                                    rede de atenção psicossocial e as internações psiquiátricas.
                                    """)
                            else:
                                st.warning("Não há dados suficientes para plotar o gráfico de iRAPS vs Taxa.")
                        
                        # Exibir tabela com todos os dados
                        st.subheader("Dados Completos por Município")
                        tabela_dados = dados_viz[['nome_municipio', 'iCAPS', 'iRAPS', 'taxa_por_100k', 'populacao']]
                        tabela_dados = tabela_dados.rename(columns={
                            'nome_municipio': 'Município',
                            'iCAPS': 'Índice iCAPS',
                            'iRAPS': 'Índice iRAPS',
                            'taxa_por_100k': 'Taxa de Internações por 100k',
                            'populacao': 'População'
                        })
                        
                        # Exibir tabela com todos os dados
                        st.dataframe(tabela_dados.sort_values(by='Índice iCAPS', ascending=False),
                                     use_container_width=True)
                
                except Exception as e:
                    st.error(f"Erro ao processar os índices de saúde mental: {e}")
                    st.warning("""
                    Para visualizar corretamente os índices iCAPS e iRAPS, é necessário fornecer a fonte de dados 
                    desses índices ou a fórmula para calculá-los.
                    """)
            except Exception as e:
                st.error(f"Erro ao calcular taxas de internação: {e}")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}") 