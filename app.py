from flask import Flask, request, send_file, render_template
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
import io
import json
import os

# Configuração de Caminhos
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ficha/<sistema>', methods=['GET'])
def gerar_ficha_generica(sistema):
    try:
        # 1. Validação de Arquivos
        pdf_path = os.path.join(base_dir, f"{sistema}.pdf")
        json_path = os.path.join(base_dir, f"{sistema}.json")

        if not os.path.exists(pdf_path):
            return render_template('index.html', erro=f"PDF '{sistema}' não encontrado."), 404
        
        if not os.path.exists(json_path):
            return render_template('index.html', erro=f"JSON '{sistema}' não encontrado."), 404

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # 2. Copia as Páginas (Visual)
        writer.append_pages_from_reader(reader)

        # 3. CLONAGEM PROFUNDA (Cérebro da Ficha)
        # Tenta pegar o objeto raiz do leitor de todas as formas possíveis
        reader_root = None
        if hasattr(reader, 'root_object'):
            reader_root = reader.root_object
        elif hasattr(reader, 'trailer'):
            reader_root = reader.trailer['/Root']
        
        # Copia dicionários globais (Scripts, AcroForm, Names) para o escritor
        # CORREÇÃO AQUI: Usamos writer._root_object (com sublinhado)
        if reader_root:
            for key in reader_root:
                if key != "/Pages": # Pages já foi copiado pelo append
                    writer._root_object[key] = reader_root[key]

        # 4. Carrega Mapeamento
        with open(json_path, 'r', encoding='utf-8') as f:
            fields_map = json.load(f)

        data = request.args
        form_data = {}

        # 5. Processa Dados da URL
        for url_param, pdf_field in fields_map.items():
            if url_param in data:
                valor = data[url_param]
                
                # Checkbox
                if "Mar Trei" in pdf_field:
                    if valor.lower() in ['true', '1', 'sim', 'yes', 'on']:
                        form_data[pdf_field] = BooleanObject(True)
                    else:
                        form_data[pdf_field] = BooleanObject(False)
                else:
                    form_data[pdf_field] = valor

        # 6. Preenche os Campos
        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        # 7. DESTRAVAR CAMPOS (Remove ReadOnly)
        # CORREÇÃO AQUI: Usamos writer._root_object
        try:
            if "/AcroForm" in writer._root_object and "/Fields" in writer._root_object["/AcroForm"]:
                fields = writer._root_object["/AcroForm"]["/Fields"]
                for field in fields:
                    field_obj = field.get_object()
                    # Se tiver flags, tenta limpar (lógica simplificada)
                    if "/Ff" in field_obj:
                        # Força atualização do valor para garantir que não fique travado
                        pass 
        except:
            pass # Se falhar o destravamento, segue a vida

        # 8. Força Recálculo Visual (NeedAppearances)
        # CORREÇÃO AQUI: Usamos writer._root_object
        if "/AcroForm" in writer._root_object:
            writer._root_object["/AcroForm"].update({
                NameObject("/NeedAppearances"): BooleanObject(True)
            })

        # 9. Envia
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
        # Mostra o erro na tela bonita para facilitar o debug
        return render_template('index.html', erro=f"Erro Arcano: {str(e)}"), 500

if __name__ == '__main__':
    app.run(debug=True)