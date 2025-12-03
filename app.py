from flask import Flask, request, send_file, render_template
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
import io
import json
import os

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ficha/<sistema>', methods=['GET'])
def gerar_ficha_generica(sistema):
    try:
        pdf_path = os.path.join(base_dir, f"{sistema}.pdf")
        json_path = os.path.join(base_dir, f"{sistema}.json")

        if not os.path.exists(pdf_path):
            return render_template('index.html', erro=f"PDF '{sistema}' não encontrado."), 404
        
        if not os.path.exists(json_path):
            return render_template('index.html', erro=f"JSON '{sistema}' não encontrado."), 404

        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        # 1. CLONAGEM TOTAL (Traz Scripts e Estrutura)
        writer.append_pages_from_reader(reader)
        writer.clone_reader_document_root(reader)

        # 2. HACK DE PERMISSÕES (O Segredo para reativar os cálculos)
        # Remove a assinatura digital/travas que bloqueiam scripts após edição
        try:
            if hasattr(writer, 'root_object') and "/Perms" in writer.root_object:
                del writer.root_object["/Perms"]
            elif hasattr(writer, '_root_object') and "/Perms" in writer._root_object:
                del writer._root_object["/Perms"]
        except Exception as e:
            print(f"Aviso: Não foi possível remover /Perms: {e}")

        # 3. Carrega e Aplica Dados
        with open(json_path, 'r', encoding='utf-8') as f:
            fields_map = json.load(f)

        data = request.args
        form_data = {}

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

        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        # 4. FORÇA REATIVAR SCRIPTS VISUAIS
        # Isso diz ao PDF Reader: "Execute os scripts de formatação agora"
        try:
            root = writer.root_object if hasattr(writer, 'root_object') else writer._root_object
            if "/AcroForm" in root:
                root["/AcroForm"].update({
                    NameObject("/NeedAppearances"): BooleanObject(True)
                })
        except:
            pass

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