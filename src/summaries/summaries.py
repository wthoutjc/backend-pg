from flask import Blueprint, request, jsonify, make_response

# Auth
from flask_jwt_extended import jwt_required

# Tools
from datetime import timedelta
import datetime                # Manejo de fechas
import json                    # Estructura json
from io import BytesIO
import pandas as pd                 # Manejo de DataFrames
import base64

# Dataset
from datasets.datasets import Datasets

class SummariesAPI:
    def __init__(self, controller) -> None:
        self.controller = controller
        self.db = self.controller.get_db()

        self.summaries = Blueprint('summaries', __name__)

        @self.summaries.route('/download-summary', methods=['POST'])
        @jwt_required()
        def download_summary():
            print('download_summary')
            if request.method == 'POST':
                data_raw = request.data.decode("utf-8")
                json_data = json.loads(data_raw)

                config = json_data['config']
                advanced_config = json_data['advancedConfig']

                data, success = self.db.consultar_resumen_exportacion(config, advanced_config)
                if success:
                    dataset = Datasets(data, config, advanced_config)
                    df, success_ = dataset.export()

                    output = BytesIO()
                    if config['fileExtension'] == 'xlsx' and success_:
                        writer = pd.ExcelWriter(output, engine='xlsxwriter')
                        df.to_excel(writer, sheet_name="Sheet1")
                        writer.save()
                        output.seek(0)
                        file = base64.b64encode(output.read()).decode()
                        return make_response(jsonify({"message": file, "ok": True}), 200)
                    elif config['fileExtension'] == 'csv' and success_:
                        file_csv = df.to_csv(index=False, encoding='utf-8')
                        file = base64.b64encode(file_csv.encode()).decode()
                        return make_response(jsonify({"message": file, "ok": True}), 200)
                    else:
                        return make_response(jsonify({"message": df, "ok": False}), 500)
                return make_response(jsonify({"message": data, "ok": False}), 500)
            return make_response(jsonify({"error": "Método no permitido", "ok": False}), 405)

        @self.summaries.route('/summaryyear')
        @jwt_required()
        def get_summary_year():
            print('get_summary_year')
            [summary_year, summary_year_sellers,
                summary_year_each_month, summary_outstanding], success = self.db.ventas_pesos_kilos_anio()
            if success:
                return make_response(jsonify({
                    "summaryYear": summary_year,
                    "summaryYearSellers": summary_year_sellers,
                    "summaryYearEachMonth": summary_year_each_month,
                    "summaryOutstanding":summary_outstanding,
                    "ok": True
                }), 200)
            return make_response(jsonify({"error": "Falló alguna de las consultas", "ok": False}), 500)


        @self.summaries.route('/summarymonth')
        @jwt_required()
        def get_summary_month():
            print('get_summary_month')
            mes = int(request.args.get(
                'mes', datetime.datetime.now().strftime('%m')))

            [ventas_resumen, ventas_vendedor_resumen_mes, ventas_vendedor_resumen_bimester,
                ventas_resumen_bimester], success = self.db.ventas_pesos_kilos_mes(mes)

            if success:
                return make_response(jsonify({
                    "summaryMonth": ventas_resumen, 
                    "summaryBimester": ventas_resumen_bimester, 
                    "summaryMonthSeller": ventas_vendedor_resumen_mes, 
                    "summaryBimesterSeller": ventas_vendedor_resumen_bimester, 
                    "ok": True}), 200)
            return make_response(jsonify({"error": ventas_resumen, "ok": False}), 500)