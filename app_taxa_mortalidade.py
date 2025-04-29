import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

import sqlite3
import pandas as pd

#  alterar preto e pardo para negro 
# gerar banco de dados de taxas de mortalidade por transtornos mentais
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



def calcular_taxa_mortalidade(codigo_municipio: str = None, estado: str = None, raca: str = None, faixa_etaria: str = None, sexo: str = None, causabas_grupo: str = None, causabas_categoria: str = None, causabas_subcategoria: str = None, usar_raca_cor2: bool = False):
    df_populacao = get_population_data(codigo_municipio=codigo_municipio, estado=estado, raca=raca, faixa_etaria=faixa_etaria, sexo=sexo, usar_raca_cor2=usar_raca_cor2)
  
    df_teste = pd.read_csv('sim_limpo_e_alterado.csv')
  
    if raca:
        if usar_raca_cor2 and raca == "Negra":
            df_teste = df_teste[df_teste['def_raca_cor'].isin(["Parda", "Preta"])]
        else:
            df_teste = df_teste[df_teste['def_raca_cor'] == raca]
    if faixa_etaria:
        faixa_etaria_dict = {
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
        faixa_min, faixa_max = faixa_etaria_dict[faixa_etaria]      
        df_teste = df_teste[(df_teste['idade_obito_anos'] >= faixa_min) & (df_teste['idade_obito_anos'] <= faixa_max)]
      
    if sexo:
        if sexo == 'F':
            df_teste = df_teste[df_teste['def_sexo'] == 'Feminino']
        elif sexo == 'M':
            df_teste = df_teste[df_teste['def_sexo'] == 'Masculino']
    if codigo_municipio:
        df_teste = df_teste[df_teste['CODMUNRES'] == codigo_municipio]
    if estado:
        df_teste = df_teste[df_teste['CODMUNRES'].astype(str).str[:2] == estado]
    if causabas_grupo:
        df_teste = df_teste[df_teste['causabas_grupo'] == causabas_grupo]
    if causabas_categoria:
        df_teste = df_teste[df_teste['causabas_categoria'] == causabas_categoria]
    if causabas_subcategoria:
        df_teste = df_teste[df_teste['causabas_subcategoria'] == causabas_subcategoria]
  
    mortes_por_ano = df_teste.groupby('ano_obito')['ano_obito'].count()

    taxa_mortalidade = pd.DataFrame()
    taxa_mortalidade['ano'] = df_populacao['ano']
    taxa_mortalidade['numero_mortes'] = taxa_mortalidade['ano'].map(mortes_por_ano).fillna(0).astype(int)
   
    taxa_mortalidade = pd.merge(taxa_mortalidade, df_populacao, on='ano', how='left')
    
    taxa_mortalidade['taxa_mortalidade'] = (taxa_mortalidade['numero_mortes'] / taxa_mortalidade['tam_pop']) * 100000
    
    return taxa_mortalidade

def gerar_grafico_taxa_mortalidade(df, titulo):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['ano'],
        y=df['taxa_mortalidade'],
        mode='lines+markers',
        name='Taxa de Mortalidade',
        line=dict(color='red', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=titulo,
        xaxis_title='Ano',
        yaxis_title='Taxa de Mortalidade (por 100.000 habitantes)',
        showlegend=True,
        template='plotly_white'
    )
    
    return fig

st.set_page_config(page_title="Mortalidade por Transtornos Mentais (CID-10 Capítulo V)", layout="wide")

st.title("Análise de Mortalidade por Transtornos Mentais (CID-10 Capítulo V)")

# Sidebar para filtros
st.sidebar.header("Filtros")

# Carregar dados para os filtros
@st.cache_data
def load_data():
    return pd.read_csv('sim_limpo_e_alterado.csv')

df = load_data()

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

# Filtro de Raça/Cor
if usar_raca_cor2:
    # Obtém as opções únicas de raça/cor do dataframe
    racas_originais = sorted(df['def_raca_cor'].unique().tolist())
    # Cria nova lista substituindo "Preta" e "Parda" por "Negra"
    racas_modificadas = ["Todas"]
    negra_added = False
    for raca in racas_originais:
        if raca in ["Preta", "Parda"]:
            if not negra_added:
                racas_modificadas.append("Negra")
                negra_added = True
        else:
            racas_modificadas.append(raca)
    
    raca_options = racas_modificadas
else:
    raca_options = ["Todas"] + sorted(df['def_raca_cor'].unique().tolist())

raca = st.sidebar.selectbox(
    "Raça/Cor",
    options=raca_options,
    index=0
)
raca = None if raca == "Todas" else raca

# Filtros
codigo_municipio_options = ["Todos"]
if estado:
    # Filtra municípios pelo estado selecionado
    codigos_filtrados = [str(cod) for cod in sorted(df['CODMUNRES'].unique()) if str(cod).startswith(estado)]
    codigo_municipio_options += codigos_filtrados
else:
    codigo_municipio_options += [str(cod) for cod in sorted(df['CODMUNRES'].unique())]

codigo_municipio_option = st.sidebar.selectbox(
    "Código do Município",
    options=codigo_municipio_options,
    index=0
)

codigo_municipio = None if codigo_municipio_option == "Todos" else int(codigo_municipio_option)

faixa_etaria_options = [
    "Todas",
    '0-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39',
    '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74',
    '75-79', '80-84', '85-89', '90-94', '95-99', '100+'
]
faixa_etaria = st.sidebar.selectbox(
    "Faixa Etária",
    options=faixa_etaria_options,
    index=0
)
faixa_etaria = None if faixa_etaria == "Todas" else faixa_etaria

sexo_options = ["Todos", 'M', 'F']
sexo = st.sidebar.selectbox(
    "Sexo",
    options=sexo_options,
    index=0
)
sexo = None if sexo == "Todos" else sexo

# Novos filtros para causabas - implementação hierárquica
causabas_grupo_options = ["Todos"] + sorted([str(x) for x in df['causabas_grupo'].dropna().unique().tolist() if x is not None])
causabas_grupo = st.sidebar.selectbox(
    "Grupo da Causa Base",
    options=causabas_grupo_options,
    index=0
)
causabas_grupo = None if causabas_grupo == "Todos" else causabas_grupo

# Filtra as categorias com base no grupo selecionado
if causabas_grupo is None:
    # Se nenhum grupo for selecionado, não podemos selecionar categoria
    st.sidebar.text("Selecione um Grupo da Causa Base para filtrar por categoria")
    causabas_categoria = None
    causabas_categoria_disabled = True
else:
    # Se um grupo for selecionado, mostra as categorias correspondentes
    categorias_filtradas = sorted([str(x) for x in df[df['causabas_grupo'] == causabas_grupo]['causabas_categoria'].dropna().unique().tolist() if x is not None])
    causabas_categoria_options = ["Todas"] + categorias_filtradas
    causabas_categoria = st.sidebar.selectbox(
        "Categoria da Causa Base",
        options=causabas_categoria_options,
        index=0
    )
    causabas_categoria = None if causabas_categoria == "Todas" else causabas_categoria
    causabas_categoria_disabled = False

# Filtra as subcategorias com base na categoria selecionada
if causabas_categoria is None:
    # Se nenhuma categoria for selecionada, não podemos selecionar subcategoria
    if causabas_grupo is not None:
        st.sidebar.text("Selecione uma Categoria da Causa Base para filtrar por subcategoria")
    else:
        st.sidebar.text("Selecione Grupo e Categoria para filtrar por subcategoria")
    causabas_subcategoria = None
    causabas_subcategoria_disabled = True
else:
    # Se uma categoria for selecionada, mostra as subcategorias correspondentes
    subcategorias_filtradas = sorted([str(x) for x in df[df['causabas_categoria'] == causabas_categoria]['causabas_subcategoria'].dropna().unique().tolist() if x is not None])
    causabas_subcategoria_options = ["Todas"] + subcategorias_filtradas
    causabas_subcategoria = st.sidebar.selectbox(
        "Subcategoria da Causa Base",
        options=causabas_subcategoria_options,
        index=0
    )
    causabas_subcategoria = None if causabas_subcategoria == "Todas" else causabas_subcategoria
    causabas_subcategoria_disabled = False

# Calcular taxa de mortalidade
taxa_mortalidade = calcular_taxa_mortalidade(
    codigo_municipio=codigo_municipio,
    estado=estado,
    raca=raca,
    faixa_etaria=faixa_etaria,
    sexo=sexo,
    causabas_grupo=causabas_grupo,
    causabas_categoria=causabas_categoria,
    causabas_subcategoria=causabas_subcategoria,
    usar_raca_cor2=usar_raca_cor2
)

# Determinar título baseado nos filtros selecionados
titulo = "Taxa de Mortalidade por Transtornos Mentais (CID-10 Capítulo V) por 100.000 habitantes"
if estado_nome != "Todos":
    titulo += f" - {estado_nome}"
if raca:
    titulo += f" - Raça/Cor: {raca}"
if faixa_etaria:
    titulo += f" - Faixa Etária: {faixa_etaria}"
if sexo:
    titulo += f" - Sexo: {sexo}"
if codigo_municipio:
    titulo += f" - Município: {codigo_municipio}"
if causabas_grupo:
    titulo += f" - Grupo: {causabas_grupo}"
if causabas_categoria:
    titulo += f" - Categoria: {causabas_categoria}"
if causabas_subcategoria:
    titulo += f" - Subcategoria: {causabas_subcategoria}"

# Gerar gráfico
fig = gerar_grafico_taxa_mortalidade(
    taxa_mortalidade,
    titulo
)

# Exibir gráfico
st.plotly_chart(fig, use_container_width=True)

# Exibir dados brutos
st.subheader("Dados Brutos")
st.dataframe(taxa_mortalidade) 