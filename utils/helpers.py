import streamlit as st
import pandas as pd
import numpy as np

# Função para exibir resumo dos filtros aplicados
def mostrar_filtros_aplicados(year_range, estado_nome, codigo_municipio, sexo, faixa_etaria, raca, municipios_dict, 
                              ano_idsc=None, usar_raca_cor2=False, diag_grupo=None, diag_categoria=None, diag_subcategoria=None, 
                              grupo_cir=None):
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
    
    # Adicionar informação sobre o grupo CIR
    if grupo_cir:
        filtros_texto += f" | **Grupo CIR:** {grupo_cir}"
    
    # Adicionar informação sobre o ano do IDSC
    if ano_idsc:
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

# Dicionário de estados para uso geral
def get_estados_dict():
    return {
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