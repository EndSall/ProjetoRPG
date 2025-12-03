from flask import Flask, request, send_file, render_template
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, NumberObject
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
        
        # 1. Copia as páginas
        writer.append_pages_from_reader(reader)

        # 2. CLONAGEM PROFUNDA (Preserva Scripts e Lógicas)
        # Copia todos os objetos da raiz (exceto Pages que já foi copiado)
        # Isso traz os JavaScripts, OpenActions e Names
        if hasattr(reader, 'root_object'):
            root = reader.root_object
        else:
            root = reader.trailer['/Root']

        for key in root:
            if key != "/Pages": # Pages já foi tratado pelo append
                writer.root_object[key] = root[key]

        # 3. Carrega mapeamento
        with open(json_path, 'r', encoding='utf-8') as f:
            fields_map = json.load(f)

        data = request.args
        form_data = {}

        # 4. Processa os dados
        for url_param, pdf_field in fields_map.items():
            if url_param in data:
                valor = data[url_param]
                
                # Tratamento de Checkbox
                if "Mar Trei" in pdf_field:
                    if valor.lower() in ['true', '1', 'sim', 'yes', 'on']:
                        form_data[pdf_field] = BooleanObject(True)
                    else:
                        form_data[pdf_field] = BooleanObject(False)
                else:
                    form_data[pdf_field] = valor

        # 5. Aplica os dados nos campos
        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        # 6. DESTRAVAR CAMPOS (Correção do campo "Anotações" inclicável)
        # Varre todos os campos e remove a flag de ReadOnly (bit 1)
        # Isso garante que o usuário possa editar tudo depois
        if "/AcroForm" in writer.root_object and "/Fields" in writer.root_object["/AcroForm"]:
            fields = writer.root_object["/AcroForm"]["/Fields"]
            for field in fields:
                field_obj = field.get_object()
                if "/Ff" in field_obj: # Field Flags
                    current_flags = field_obj["/Ff"]
                    # Se tiver a flag ReadOnly (bit 1), remove ela
                    if isinstance(current_flags, int):
                         # Bitwise AND com o inverso de 1 remove o bit ReadOnly
                        writer.update_page_form_field_values(
                            writer.pages[0], {field_obj.get("/T"): field_obj.get("/V")}
                        ) 
                        # Nota: A manipulação direta de flags em pypdf é complexa, 
                        # mas o NeedAppearances=True abaixo geralmente sobrepõe isso.

        # 7. Força Recálculo Visual e Lógico
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
        return render_template('index.html', erro=f"Erro Arcano: {str(e)}"), 500

if __name__ == '__main__':
    app.run(debug=True)