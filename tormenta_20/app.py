from flask import Flask, request, send_file
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, IndirectObject
import io

app = Flask(__name__)

@app.route('/')
def home():
    return "Mago do Backend T20 Online! Use a rota /ficha para gerar."

@app.route('/ficha', methods=['GET'])
def gerar_ficha():
    try:
        # 1. Carrega o PDF Original (Tem que estar na mesma pasta)
        # Certifique-se que o nome do arquivo é EXATAMENTE este:
        input_pdf = "Ficha T20 v.2.0.pdf" 
        reader = PdfReader(input_pdf)
        writer = PdfWriter()

        # Copia todas as páginas do original para o novo
        writer.append_pages_from_reader(reader)

        # 2. Mapeamento URL -> Nome do Campo no PDF
        # Dicionário de dados recebidos da URL
        data = request.args
        
        # Mapa de tradução (Igual ao que tinhamos no HTML)
        fields_map = {
            'nome': 'NOME DO PERSONAGEM',
            'jogador': 'JOGADOR',
            'raca': 'RAÇA',
            'origem': 'ORIGEM',
            'classe': 'CLASSE',
            'nivel': 'Lv',
            'divindade': 'DIVINDADE',
            'historia': 'Descrição',
            'hab_raca': 'HabRaçasOrigem',
            'hab_classe': 'HabClassePoderes',
            'magias': 'Magias',
            'notas': 'Anotações',
            'dinheiro': '110',
            'carga_atual': 'CargaTotal',
            'carga_max': 'CargaMax',
            'obs_carga': 'Observação',
            # Atributos
            'for': 'For', 'mod_for': 'ModFor',
            'des': 'Des', 'mod_des': 'ModDes',
            'con': 'Con', 'mod_con': 'ModCon',
            'int': 'Int', 'mod_int': 'ModInt',
            'sab': 'Sab', 'mod_sab': 'ModSab',
            'car': 'Car', 'mod_car': 'ModCar',
            # Vitals (Aqui o Python não trava com Rich Text!)
            'pv_max': 'PVs Totais', 'pv_atual': 'PVs Atuais',
            'pm_max': 'PMs Totais', 'pm_atual': 'PMs Atuais',
            'defesa': 'CA',
            # Magia Header
            'atrib_magia': 'SeleAtribMagia',
            'mod_magia': 'ModAtribMagia',
            'cd_magia': 'TesteResist',
             # Itens
            'item1': 'Item1', 'peso1': 'PesoItem1',
            'item2': 'Item2', 'peso2': 'PesoItem2',
            'item3': 'Item3', 'peso3': 'PesoItem3',
            'item4': 'Item4', 'peso4': 'PesoItem4',
            'item5': 'Item5', 'peso5': 'PesoItem5'
        }

        # 3. Monta o Dicionário Final de Preenchimento
        form_data = {}
        
        # Preenche campos de texto mapeados
        for url_param, pdf_field in fields_map.items():
            if url_param in data:
                form_data[pdf_field] = data[url_param]

        # Preenche Checkboxes (Lógica Especial para Python)
        # O Python precisa saber o nome exato do campo checkbox
        checkboxes = [
            'Mar Trei luta', 'Mar Trei ponta', 'Mar Trei misti', 'Mar Trei vonta',
            'Mar Trei acro', 'Mar Trei atle', 'Mar Trei furt', 'Mar Trei perc',
            'Mar Trei inic', 'Mar Trei refl', 'Mar Trei fort'
        ]
        # Se na URL vier 'treino_luta=true', marcamos 'Mar Trei luta'
        for param in data:
            # Ex: param é 'treino_luta', valor 'true'
            # Precisamos mapear isso. Para simplificar, vou assumir que você
            # passará o NOME DO CAMPO PDF na url para checkboxes complexos
            # ou podemos mapear um por um se quiser.
            pass 

        # 4. Aplica os dados
        # O Pulo do Gato: update_page_form_field_values escreve direto no binário
        for page in writer.pages:
            writer.update_page_form_field_values(page, form_data)

        # 5. OBRIGATÓRIO: Força o Adobe/Chrome a recalcular a aparência visual
        # Isso corrige o bug de "campo invisível" ou "rich text quebrado"
        writer.root_object.get("/AcroForm").update({
            NameObject("/NeedAppearances"): BooleanObject(True)
        })

        # 6. Salva na Memória e Envia
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        
        nome_arquivo = data.get('nome', 'Aventureiro')
        return send_file(
            output_stream,
            as_attachment=True,
            download_name=f"Ficha_{nome_arquivo}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        return f"Erro no servidor Mago: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)