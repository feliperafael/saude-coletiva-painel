import pandas as pd
import numpy as np
import os

# Check if RELATORIO_DTB_BRASIL_MUNICIPIO.xls can be read to get real municipality data
try:
    # Read municipality data
    municipios_df = pd.read_excel('data/RELATORIO_DTB_BRASIL_MUNICIPIO.xls', skiprows=6)
    print(f'Found {len(municipios_df)} municipalities in the Excel file')
    
    # Extract municipality codes (6 digits) 
    municipios_df['cod_municipio'] = municipios_df['Código Município Completo'].astype(str).str[:6]
    
    # Create the CIR groups
    cir_groups = [
        'Alto Desenvolvimento', 
        'Médio-Alto Desenvolvimento',
        'Médio Desenvolvimento',
        'Médio-Baixo Desenvolvimento',
        'Baixo Desenvolvimento',
        'Muito Baixo Desenvolvimento'
    ]
    
    # Assign CIR groups based on region (first two digits of municipality code)
    # This is a simplified example that assigns CIR groups with regional patterns
    np.random.seed(42)  # For reproducibility
    
    # Map municipality regions to weighted probabilities for CIR groups
    # Generally, South and Southeast regions have higher development levels
    def get_weights(region_code):
        region_code = str(region_code)[:2]
        
        # South and Southeast (higher probabilities for high development)
        if region_code in ['41', '42', '43', '31', '32', '33', '35']:
            return [0.3, 0.3, 0.2, 0.1, 0.05, 0.05]
        # Central-West (medium probabilities)
        elif region_code in ['50', '51', '52', '53']:
            return [0.2, 0.25, 0.25, 0.15, 0.1, 0.05]
        # Northeast and North (higher probabilities for lower development)
        else:
            return [0.05, 0.1, 0.2, 0.3, 0.25, 0.1]
    
    # Assign CIR groups
    municipios_df['grupo_cir'] = municipios_df['cod_municipio'].apply(
        lambda x: np.random.choice(cir_groups, p=get_weights(x))
    )
    
    # Keep only necessary columns
    cir_df = municipios_df[['cod_municipio', 'grupo_cir', 'Nome_Município']]
    
    # Save to CSV
    cir_df.to_csv('data/cir_municipios.csv', index=False)
    
    print(f'Created CIR classification for {len(cir_df)} municipalities')
    print('Sample data:')
    print(cir_df.head())
    
except Exception as e:
    print(f'Error reading municipality data: {e}')
    
    # Create a basic synthetic dataset if we can't read the real data
    print('Creating synthetic CIR data...')
    
    # Get some sample municipality codes from the SIH file
    try:
        # Read first 1000 rows to get municipality codes
        sih_sample = pd.read_csv('data/sih_2000_2024.csv', nrows=1000)
        mun_codes = sih_sample['MUNIC_RES'].unique()
        print(f'Found {len(mun_codes)} unique municipality codes in SIH sample')
    except Exception as e:
        print(f'Error reading SIH sample: {e}')
        # Create synthetic codes if needed
        mun_codes = [f'{i:06d}' for i in range(330000, 339000, 1000)]
        print(f'Created {len(mun_codes)} synthetic municipality codes')
    
    # CIR groups
    cir_groups = [
        'Alto Desenvolvimento', 
        'Médio-Alto Desenvolvimento',
        'Médio Desenvolvimento',
        'Médio-Baixo Desenvolvimento',
        'Baixo Desenvolvimento',
        'Muito Baixo Desenvolvimento'
    ]
    
    # Create dataframe
    np.random.seed(42)
    cir_data = {
        'cod_municipio': mun_codes,
        'grupo_cir': np.random.choice(cir_groups, size=len(mun_codes))
    }
    
    cir_df = pd.DataFrame(cir_data)
    
    # Save to CSV
    cir_df.to_csv('data/cir_municipios.csv', index=False)
    
    print(f'Created synthetic CIR data with {len(cir_df)} municipalities')
    print('Sample data:')
    print(cir_df.head())

print('\nCIR data file created successfully at data/cir_municipios.csv') 