from flask import Flask, request, send_file
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
import io
import json
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Motor de Fichas RPG Online</h1><p>Use: /ficha/t20?nome=Valeros ou /ficha/dnd5e?nome=Aragorn</p>"

# A Mágica Acontece Aqui: <sistema> pega o que você digitar na URL (ex: t20, dnd, cthulhu)
@app.route('/ficha/<sistema>', methods=['GET'])
def gerar_ficha_generica(sistema):
    try:
        # 1. Definição Dinâmica de Arquivos
        # Se você acessar /ficha/t20, ele busca "t20.pdf" e "t20.json"
        pdf_path = f"{sistema}.pdf"
        json_path = f"{sistema}.json"

        # Verificação de Segurança: Os arquivos existem?
        if not os.path.exists(pdf_path):
            return f"Erro: Sistema '{sistema}' não encontrado. Verifique se o arquivo {pdf_path} existe.", 404
        
        if not os.path.exists(json_path):
            return f"Erro: Mapeamento do sistema '{sistema}' não encontrado ({json_path}).", 404

        # 2. Carrega o PDF e o Mapa JSON
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            fields_map = json.load(f)

        # 3. Processa os Dados da URL
        data = request.args
        form_data = {}

        # Loop Genérico: Varre o JSON e cruza com a URL
        for url_param, pdf_field in fields_map.items():
            if url_param in data:
                form_data[pdf_field] = data[url_param]

        # 4. Grava no PDF
        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        # Truque do Refresh Visual
        writer.root_object.get("/AcroForm").update({
            NameObject("/NeedAppearances"): BooleanObject(True)
        })

        # 5. Entrega
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        
        nome_arquivo = data.get('nome', 'Personagem')
        return send_file(
            output_stream,
            as_attachment=True,
            download_name=f"Ficha_{sistema}_{nome_arquivo}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        return f"Erro Interno no Motor: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)