import numpy as np
import pandas as pd

class Datasets():
    def __init__(self, dataset, config, advanced_config):
        self.dataset = dataset
        self.config = config
        self.advanced_config = advanced_config

    def export(self):
        '''
        Exporta el dataset en un excel
        '''
        try:
            print('Export dataset')
            id_pedido = np.array(['ID Pedido']) if self.config['type'] == "pedidos" else np.array(['ID Pedido', 'ID Bodega'])
            df = pd.DataFrame(self.dataset, columns=np.concatenate((id_pedido, self.advanced_config)))
            df = df.set_index('ID Pedido')
            return [df, True]
        except ValueError as e:
            print(f'Export dataset Error: {str(e)}')
            return [f'Export dataset Error: {str(e)}', False]

