from flask import Flask, request, send_file
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
import io
import json
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Motor de Fichas RPG Online</h1><p>Status: Operacional</p>"

@app.route('/ficha/<sistema>', methods=['GET'])
def gerar_ficha_generica(sistema):
    try:
        # 1. Definição de Caminhos
        # O Render roda na raiz da pasta definida (tormenta_20), então os arquivos estão locais
        pdf_path = f"{sistema}.pdf"
        json_path = f"{sistema}.json"

        # Verificação de segurança
        if not os.path.exists(pdf_path):
            return f"Erro: Arquivo PDF '{pdf_path}' não encontrado no servidor.", 404
        
        if not os.path.exists(json_path):
            return f"Erro: Arquivo JSON '{json_path}' não encontrado.", 404

        # 2. Carrega PDF e JSON
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Copia as páginas
        writer.append_pages_from_reader(reader)
        
        # --- A CORREÇÃO MÁGICA ESTÁ AQUI ---
        # Verifica se o original tem formulário e copia a estrutura para o novo
        if "/AcroForm" in reader.root_object:
            # Copia a referência do AcroForm do original para o writer
            writer.root_object[NameObject("/AcroForm")] = reader.root_object["/AcroForm"]
        # -----------------------------------

        # Carrega o mapa de campos
        with open(json_path, 'r', encoding='utf-8') as f:
            fields_map = json.load(f)

        # 3. Processa os Dados da URL
        data = request.args
        form_data = {}

        # Mapeia URL -> PDF
        for url_param, pdf_field in fields_map.items():
            if url_param in data:
                form_data[pdf_field] = data[url_param]

        # 4. Aplica os dados nas páginas
        # Agora que copiamos o AcroForm ali em cima, isso vai funcionar
        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        # 5. Força a atualização visual (NeedAppearances)
        # Só executa se o AcroForm existir (segurança extra)
        if "/AcroForm" in writer.root_object:
            writer.root_object["/AcroForm"].update({
                NameObject("/NeedAppearances"): BooleanObject(True)
            })

        # 6. Salva e Envia
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
        # Mostra o erro real para facilitar o debug
        return f"Erro Interno no Motor: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)