---
language: pt
tags:
- health
- brazil
- public-health
- healthcare
- epidemiology
license: cc-by-4.0
datasets:
- saude-coletiva
---

# Dataset de Saúde Coletiva

Este dataset contém informações sobre saúde pública no Brasil, incluindo dados de mortalidade, internações hospitalares e indicadores de saúde.

## Conteúdo do Dataset

O dataset contém os seguintes arquivos:

1. `sih_2000_2024.csv` - Sistema de Informações Hospitalares (SIH) contendo dados de internações hospitalares de 2000 a 2024
2. `sim_limpo_e_alterado.csv` - Sistema de Informações sobre Mortalidade (SIM) processado
3. `sim_95_columns_versao_final.csv` - Versão final do SIM com 95 colunas
4. `populacao.db` - Banco de dados com informações populacionais
5. `cir_municipios.csv` - Dados dos municípios brasileiros
6. `base_magda.xlsx` - Base de dados complementar
7. `Base_de_Dados_IDSC-BR_2022.xlsx`, `Base_de_Dados_IDSC-BR_2023.xlsx`, `Base_de_Dados_IDSC-BR_2024.xlsx` - Indicadores de Desenvolvimento Sustentável das Cidades - Brasil
8. `RELATORIO_DTB_BRASIL_MUNICIPIO.xls` - Divisão Territorial Brasileira

## Estrutura dos Dados

### SIH (Sistema de Informações Hospitalares)
- Período: 2000-2024
- Principais variáveis:
  - Dados demográficos (idade, sexo, raça/cor)
  - Informações de internação (data, procedimentos, diagnósticos)
  - Dados financeiros (valores totais, valores por serviço)
  - Informações de UTI
  - Dados geográficos (município de residência, coordenadas)

### SIM (Sistema de Informações sobre Mortalidade)
- Principais variáveis:
  - Causas de óbito
  - Dados demográficos
  - Local de ocorrência
  - Características do óbito

## Fonte dos Dados

Os dados são provenientes de sistemas oficiais do Ministério da Saúde do Brasil:
- Sistema de Informações Hospitalares (SIH)
- Sistema de Informações sobre Mortalidade (SIM)
- Indicadores de Desenvolvimento Sustentável das Cidades - Brasil (IDSC-BR)

## Uso Pretendido

Este dataset pode ser utilizado para:
- Análises epidemiológicas
- Estudos de saúde pública
- Pesquisas em políticas de saúde
- Desenvolvimento de indicadores de saúde
- Análises espaciais de saúde

## Limitações

- Os dados estão sujeitos às limitações dos sistemas de informação em saúde
- Alguns registros podem conter informações incompletas
- As variáveis podem ter diferentes níveis de completude ao longo do tempo

## Citação

Se você utilizar este dataset em sua pesquisa, por favor cite:

```
@dataset{saude_coletiva_2024,
  author = {Felipe Rafael},
  title = {Dataset de Saúde Coletiva},
  year = {2024},
  publisher = {HuggingFace},
  url = {https://huggingface.co/datasets/feliperafael/saude-coletiva}
}
```

## Licença

Este dataset está licenciado sob a licença Creative Commons Attribution 4.0 International (CC BY 4.0). 