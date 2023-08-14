import pandas as pd

class Presupuesto():
    def __init__(self):
        self.presupuesto = None
        self.verify = None
    
    def set_presupuesto(self, presupuesto):
        self.presupuesto = presupuesto

    def verify_presupuesto_excel(self):
        '''
        Procesos para verificar que el archivo .xlsx cumpla
        las condiciones de actualización
        '''
        if not isinstance(self.presupuesto, type(None)):
            verify_process = {
                    "verify": True,
                    "message": 'Presupuesto validado',
                }
            #Verificar len():
            if len(self.presupuesto.columns) != 2:
                verify_process['verify'] = False
                verify_process['message'] = 'El archivo .xlsx no cumple la condición: Tamaño de Columnas (2)'
            elif not 'mes' in self.presupuesto and not 'presupuesto' in self.presupuesto:
                verify_process['verify'] = False
                verify_process['message'] = 'El archivo .xlsx no cumple la condición: Columnas (mes, presupuesto)'
            try:
                self.presupuesto['mes'] = self.presupuesto['mes'].astype('str').astype("int64")
                self.presupuesto['presupuesto'] = self.presupuesto['presupuesto'].astype('str').astype("float")
            except Exception as e:
                print(e)
                verify_process['verify'] = False
                verify_process['message'] = 'El archivo no tiene el formato correcto'
            return [verify_process['message'], verify_process['verify']]
        return ['Presupuesto no seteado. ', False]
    
    def get_presupuesto(self):
        '''
        Transforma el excel (DataFrame) en un arreglo procesable
        '''
        _presupuesto = []
        if type(self.presupuesto) == pd.core.frame.DataFrame:
            for data in self.presupuesto.to_numpy():
                _presupuesto.append(data)
            return _presupuesto
        return self.presupuesto