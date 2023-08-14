import pandas as pd

class LP():
    def __init__(self):
        self.lp = None
        self.context = None
        self.verify = None

    def set_lp(self, lp):
        self.lp = lp

    def set_context(self, context):
        self.context = context

    def verify_lp_excel(self):
        '''
        Procesos para verificar que el archivo .xlsx cumpla
        las condiciones de actualización
        '''
        if not isinstance(self.lp, type(None)) and self.context != None:
            verify_process = {
                    "verify": True,
                    "message": 'Lista de precios validada',
                }
            if self.context == 'Pedidos':
                print('Pedidos')
                #Verificar len():
                if len(self.lp.columns) != 3:
                    verify_process['verify'] = False
                    verify_process['message'] = 'El archivo .xlsx no cumple la condición: Tamaño de Columnas (3)'
                elif not 'nombre' in self.lp and not 'precio' in self.lp and not 'kg' in self.lp:
                    verify_process['verify'] = False
                    verify_process['message'] = 'El archivo .xlsx no cumple la condición: Columnas (nombre, precio, kg)'
                try:
                    self.lp['precio'] = self.lp['precio'].astype('str').astype("int64")
                except Exception as e:
                    print(e)
                    verify_process['verify'] = False
                    verify_process['message'] = 'El archivo no tiene el formato correcto'
                return [verify_process['message'], verify_process['verify']]
            elif self.context == "Bodegas":
                print('Bodegas')
                #Verificar len():
                if len(self.lp.columns) != 2:
                    verify_process['verify'] = False
                    verify_process['message'] = 'El archivo .xlsx no cumple la condición: Tamaño de Columnas (2)'
                elif not 'nombre' in self.lp and not 'precio' in self.lp and not 'kg' in self.lp:
                    verify_process['verify'] = False
                    verify_process['message'] = 'El archivo .xlsx no cumple la condición: Columnas (nombre, kg)'
                return [verify_process['message'], verify_process['verify']]
        return ['Lista de Precios o contexto no seteado. ', False]

    def is_number(self, number):
        if (isinstance(number, int)):
            return True
        if (isinstance(number, float)):
            return True
        return False
        
    def get_lp(self):
        '''
        Transforma el excel (DataFrame) en un arreglo procesable
        '''
        _lp = []
        if type(self.lp) == pd.core.frame.DataFrame:
            for data in self.lp.to_numpy():
                _lp.append(data)
            return _lp
        return self.lp