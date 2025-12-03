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
    return render_template('index.html')

@app.route('/ficha/<sistema>', methods=['GET'])
def gerar_ficha_generica(sistema):
    try:
        # Definição de caminhos
        pdf_path = f"{sistema}.pdf"
        json_path = f"{sistema}.json"

        # Verificações de arquivo
        if not os.path.exists(pdf_path):
            return render_template('index.html', erro=f"Sistema '{sistema}' não encontrado. PDF ausente."), 404
        
        if not os.path.exists(json_path):
            return render_template('index.html', erro=f"Mapa JSON '{sistema}' não encontrado."), 404

        # Carrega o PDF
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        # --- CORREÇÃO DE COMPATIBILIDADE (O PULO DO GATO) ---
        # Tenta pegar o Catálogo (Root) de forma universal
        catalog = None
        try:
            # Tentativa 1: Método moderno
            if hasattr(reader, 'root_object'):
                catalog = reader.root_object
            # Tentativa 2: Método clássico (acesso direto ao trailer)
            elif hasattr(reader, 'trailer'):
                catalog = reader.trailer['/Root']
        except Exception as e:
            print(f"Aviso: Falha ao ler root do original: {e}")

        # Se conseguiu ler o catálogo original e ele tem formulário, copia para o novo
        if catalog and "/AcroForm" in catalog:
            # Garante acesso ao root do Writer também
            if hasattr(writer, 'root_object'):
                writer.root_object[NameObject("/AcroForm")] = catalog["/AcroForm"]
            else:
                # Fallback para versões internas/antigas
                writer._root_object[NameObject("/AcroForm")] = catalog["/AcroForm"]
        # -----------------------------------------------------

        # Carrega o mapa JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            fields_map = json.load(f)

        data = request.args
        form_data = {}

        # Mapeia URL -> PDF
        for url_param, pdf_field in fields_map.items():
            if url_param in data:
                form_data[pdf_field] = data[url_param]

        # Aplica os dados
        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        # Força a atualização visual (NeedAppearances)
        # Usa a mesma lógica blindada para pegar o root do writer
        try:
            writer_root = writer.root_object if hasattr(writer, 'root_object') else writer._root_object
            
            if "/AcroForm" in writer_root:
                writer_root["/AcroForm"].update({
                    NameObject("/NeedAppearances"): BooleanObject(True)
                })
        except Exception as e:
            print(f"Aviso: Não foi possível atualizar NeedAppearances: {e}")

        # Salva e Envia
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
        # Mostra o erro detalhado na tela bonita
        return render_template('index.html', erro=f"Erro Arcano (Motor): {str(e)}"), 500

if __name__ == '__main__':
    app.run(debug=True)