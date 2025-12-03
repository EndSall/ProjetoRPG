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
        
        # 2. Copia as Páginas (Base Visual)
        # Isso garante que a estrutura de páginas do Writer fique correta
        writer.append_pages_from_reader(reader)

        # 3. TRANSPLANTE DE "ÓRGÃOS VITAIS" (Sem quebrar a estrutura)
        # Tenta localizar a Raiz do PDF original de forma segura
        reader_root = None
        if hasattr(reader, 'root_object'):
            reader_root = reader.root_object
        elif hasattr(reader, 'trailer'):
            reader_root = reader.trailer['/Root']

        if reader_root:
            # Pega a Raiz do Novo PDF para injetar os órgãos
            # Tenta acessar _root_object (interno) ou root_object (novo)
            writer_root = getattr(writer, 'root_object', None) or getattr(writer, '_root_object', None)

            if writer_root:
                # A. Copia o Formulário (/AcroForm) - Campos
                if "/AcroForm" in reader_root:
                    writer_root[NameObject("/AcroForm")] = reader_root["/AcroForm"]

                # B. Copia os Scripts (/Names) - Onde vive o JavaScript
                if "/Names" in reader_root:
                    writer_root[NameObject("/Names")] = reader_root["/Names"]

                # C. Copia Ações de Abertura (/OpenAction) - Scripts de inicialização
                if "/OpenAction" in reader_root:
                    writer_root[NameObject("/OpenAction")] = reader_root["/OpenAction"]

                # D. Hack de Permissões:
                # Nós propositalmente NÃO copiamos a chave "/Perms". 
                # Ao deixar ela de fora, removemos a trava de segurança!
        
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

        # 7. Força Recálculo Visual (NeedAppearances)
        try:
            writer_root = getattr(writer, 'root_object', None) or getattr(writer, '_root_object', None)
            if writer_root and "/AcroForm" in writer_root:
                writer_root["/AcroForm"].update({
                    NameObject("/NeedAppearances"): BooleanObject(True)
                })
        except:
            pass

        # 8. Envia
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
        return render_template('index.html', erro=f"Erro Arcano: {str(e)}"), 500

if __name__ == '__main__':
    app.run(debug=True)