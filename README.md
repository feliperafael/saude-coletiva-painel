# Atlas Nacional de Saúde Mental

Este projeto consiste em um conjunto de painéis interativos desenvolvidos em Streamlit para análise e visualização de dados relacionados à saúde mental no Brasil. O objetivo é criar um atlas nacional que permita a análise das morbidades de internações psiquiátricas, taxas de mortalidade e outros indicadores relevantes, organizados por sexo, idade e cor/raça.

## Configuração Inicial

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/saude-coletiva.git
cd saude-coletiva
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure o acesso ao Hugging Face
1. Crie uma conta no [Hugging Face](https://huggingface.co)
2. Acesse suas [configurações de token](https://huggingface.co/settings/tokens)
3. Crie um novo token de acesso
4. Crie um arquivo `.env` na raiz do projeto com suas credenciais:
```bash
HF_USERNAME=seu_usuario
HF_TOKEN=seu_token
```

### 4. Baixe os dados
Execute o script para baixar os dados do Hugging Face:
```bash
python scripts/hf_data_manager.py --repo-id "feliperafael/saude-coletiva" --action download
```
Os arquivos serão baixados automaticamente para a pasta `data/` do projeto.

## Estrutura do Projeto

O projeto é composto por vários painéis interativos, cada um focado em um aspecto específico da análise de saúde mental:

1. **Indicadores de Saúde Mental** (`indicadores_saude_mental.py`)
   - Análise dos indicadores iCAPS e iRAPS
   - Visualização de correlações entre indicadores
   - Distribuição geográfica dos indicadores

2. **Morbidade de Internações** (`morbidade_internacoes.py`)
   - Análise detalhada das causas de internação
   - Distribuição por faixa etária
   - Análise por sexo e raça/cor

3. **Taxa de Mortalidade** (`app_taxa_mortalidade.py`)
   - Análise das taxas de mortalidade
   - Comparação entre diferentes grupos populacionais
   - Evolução temporal

4. **Análise iCAPS** (`icaps_analysis.py`)
   - Foco específico no indicador iCAPS
   - Correlações com outros indicadores
   - Distribuição geográfica

5. **Análise iRAPS** (`iraps_analysis.py`)
   - Foco específico no indicador iRAPS
   - Análise de tendências
   - Comparação com outros indicadores

6. **Grupo CIR** (`grupo_cir.py` e `grupo_cir_with_taxa.py`)
   - Análise por grupos CIR
   - Correlação com taxas de mortalidade
   - Distribuição geográfica

7. **Relação IDSC** (`relacao_idsc.py`)
   - Análise da relação com o IDSC
   - Correlações e tendências
   - Visualizações específicas

## Requisitos

Para executar o projeto, você precisará ter instalado:

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Docker (opcional, para ambiente isolado)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/feliperafael/saude-coletiva-painel.git
cd saude-coletiva-painel
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Certifique-se de que os arquivos de dados necessários estão na pasta `data/`:
   - `base_magda.xlsx`
   - `sim_limpo_e_alterado.csv`
   - `populacao.db`

## Como Executar

### Opção 1: Execução Local

Cada painel pode ser executado individualmente usando o comando:

```bash
streamlit run [NOME_DO_ARQUIVO].py
```

Por exemplo, para executar o painel de Indicadores de Saúde Mental:

```bash
streamlit run indicadores_saude_mental.py
```

### Opção 2: Execução com Docker

1. Construa a imagem:
```bash
docker compose build
```

2. Execute o container:
```bash
docker compose up
```

## Estrutura de Dados

O projeto utiliza várias fontes de dados:

1. **Dados de Internação** (`sim_limpo_e_alterado.csv`)
   - Informações sobre internações psiquiátricas
   - Dados demográficos dos pacientes
   - Diagnósticos e procedimentos

2. **Base Magda** (`base_magda.xlsx`)
   - Indicadores iCAPS e iRAPS
   - Informações municipais
   - Classificação CIR

3. **Banco de Dados de População** (`populacao.db`)
   - Dados populacionais
   - Projeções e estimativas
   - Informações demográficas

## Visualizações

O projeto inclui várias visualizações interativas:

1. **Gráficos de Distribuição**
   - Histogramas
   - Box plots
   - Gráficos de densidade

2. **Visualizações Geográficas**
   - Mapas de calor
   - Distribuição por município
   - Agrupamentos regionais

3. **Análises Temporais**
   - Séries temporais
   - Tendências
   - Evolução dos indicadores

4. **Correlações**
   - Matrizes de correlação
   - Gráficos de dispersão
   - Análises de regressão

### Exemplos de Visualizações

#### 1. Análise de Morbidade
![Distribuição por Faixa Etária](prints/morbidade_internacoes_02.jpeg)
*Distribuição de internações por faixa etária*

![Análise por Sexo](prints/morbidade_internacoes_03.jpeg)
*Distribuição de internações por sexo*

![Análise por Raça/Cor](prints/morbidade_internacoes_04.jpeg)
*Distribuição de internações por raça/cor*

#### 2. Taxa de Mortalidade
![Evolução Temporal](prints/app_taxa_mortalidade_01.jpeg)
*Evolução temporal da taxa de mortalidade*

#### 3. Relação IDSC
![Correlação 1](prints/relacao_idsc_01.jpeg)
*Análise de correlação entre indicadores*

![Correlação 2](prints/relacao_idsc_02.jpeg)
*Análise detalhada de correlações*

#### 4. Análise Detalhada
![Distribuição Geográfica](prints/morbidade_internacoes_05.jpeg)
*Distribuição geográfica das internações*

![Análise Temporal](prints/morbidade_internacoes_06.jpeg)
*Análise temporal das internações*

## Segurança

1. **Credenciais e Tokens**
   - Nunca comite credenciais ou tokens no código
   - Utilize variáveis de ambiente para armazenar informações sensíveis
   - Para tokens do Hugging Face, utilize o arquivo `.env` ou variáveis de ambiente do sistema

2. **Dados Sensíveis**
   - Os dados de saúde são sensíveis e devem ser tratados com cuidado
   - Siga as diretrizes da LGPD para o tratamento de dados pessoais
   - Mantenha os dados anonimizados quando possível

3. **Ambiente de Desenvolvimento**
   - Utilize ambientes virtuais para isolar as dependências
   - Mantenha as dependências atualizadas
   - Siga as boas práticas de segurança do Python

## Contribuições

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.

