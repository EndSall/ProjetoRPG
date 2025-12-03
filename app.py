from flask import Flask, request, send_file, render_template
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
import io
import json
import os

# Define que a pasta de templates é a 'templates'
app = Flask(__name__, template_folder='templates')

@app.route('/')
def home():
    # Renderiza a página bonita
    return render_template('index.html')

@app.route('/ficha/<sistema>', methods=['GET'])
def gerar_ficha_generica(sistema):
    try:
        pdf_path = f"{sistema}.pdf"
        json_path = f"{sistema}.json"

        # ERRO BONITO: Se não achar o arquivo, renderiza a Home com msg de erro
        if not os.path.exists(pdf_path):
            return render_template('index.html', erro=f"Sistema '{sistema}' não encontrado. Falta o arquivo {pdf_path}."), 404
        
        if not os.path.exists(json_path):
            return render_template('index.html', erro=f"Mapa '{json_path}' não encontrado."), 404

        # ... (O CÓDIGO DO PYPDF CONTINUA IGUAL AQUI PARA BAIXO) ...
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        if "/AcroForm" in reader.root_object:
            writer.root_object[NameObject("/AcroForm")] = reader.root_object["/AcroForm"]

        with open(json_path, 'r', encoding='utf-8') as f:
            fields_map = json.load(f)

        data = request.args
        form_data = {}

        for url_param, pdf_field in fields_map.items():
            if url_param in data:
                form_data[pdf_field] = data[url_param]

        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        if "/AcroForm" in writer.root_object:
            writer.root_object["/AcroForm"].update({
                NameObject("/NeedAppearances"): BooleanObject(True)
            })

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
        # ERRO BONITO: Se der pau no código, mostra na tela estilizada
        return render_template('index.html', erro=f"Erro Arcano: {str(e)}"), 500

if __name__ == '__main__':
    app.run(debug=True)