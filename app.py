from flask import Flask, render_template, jsonify, request, redirect, url_for
from wtforms import StringField, SelectField, DateField
from wtforms.validators import DataRequired
from datetime import timedelta, datetime
from wtforms.fields import TimeField
from flask_wtf import FlaskForm
from io import StringIO
from lxml import etree

import pandas as pd
import requests
import hashlib
import secrets
import base64
import json
import html
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Chave secreta necessária para Flask-WTF

df = None  # df global para não ter que rodar a API duas vezes
df_dados_agendamento = pd.DataFrame()
df_dados_novo_funcionario = pd.DataFrame()
dados_hierarquia = None  # Inicializa a variável global

# Definição do formulário
class AgendamentoForm(FlaskForm):
    tipo_exame = SelectField('Tipo de Exame', choices=[('Admissional', 'Admissional'), ('Demissional', 'Demissional'),
                                                       ('Periódicos', 'Periódicos'),
                                                       ('Retorno ao Trabalho', 'Retorno ao Trabalho'),
                                                       ('Mudança de Função', 'Mudança de Função')],
                             validators=[DataRequired()])
    empresa = StringField('Empresa', validators=[DataRequired()])
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    nome_funcionario = StringField('Nome do Funcionário', validators=[DataRequired()])
    cpf_funcionario = StringField('CPF do Funcionário', validators=[DataRequired()])
    email_contato = StringField('Email para Contato', validators=[DataRequired()])
    unidade_atendimento = SelectField('Unidade de Atendimento',
                                      choices=[('Selecione uma unidade', 'Selecione uma unidade'), ('Alphaville', 'Alphaville'), ('Ipiranga', 'Ipiranga'),
                                               ('Jabaquara', 'Jabaquara')], validators=[DataRequired()])
    data_atendimento = SelectField('Data do Atendimento', choices=[], validators=[DataRequired()])
    horario_atendimento = TimeField('Horário do Atendimento', validators=[DataRequired()])


class CadastroFuncionarioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    cpf = StringField('CPF', validators=[DataRequired()])
    rg = StringField('RG', validators=[DataRequired()])
    uf_rg = StringField('UF RG', validators=[DataRequired()])
    sexo = SelectField('Sexo', choices=[('Masculino', 'Masculino'), ('Feminino', 'Feminino')], validators=[DataRequired()])
    genero = SelectField('Gênero', choices=[('hetero', 'Hetero'), ('transgenero', 'Transgênero'), ('Não declarar', 'Prefiro não declarar')], validators=[DataRequired()])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    data_admissao = DateField('Data de Admissão', format='%Y-%m-%d', validators=[DataRequired()])
    cnpj = StringField('CNPJ', validators=[DataRequired()])
    unidade = StringField('Unidade', validators=[DataRequired()])
    setor = StringField('Setor', validators=[DataRequired()])
    cargo = StringField('Cargo', validators=[DataRequired()])
    con_trabalho = StringField('Contrato de trabalho', validators=[DataRequired()])
    reg_trabalho = StringField('Regime de trabalho', validators=[DataRequired()])


@app.route('/', methods=['GET'])
def index():
    form = AgendamentoForm()  # Crie uma instância do formulário
    return render_template('index.html', form=form)


@app.route('/cadastro_funcionario')
def cadastro_funcionario():
    return render_template('cadastro_funcionario.html')


def processar_agenda(codigo_agenda):
    # ------------------------ Parafernalha para rodar a função horarios disponiveis ----------------------------
    url = "https://ws1.soc.com.br/WSSoc/services/ExportaDadosWs"
    username = "U2732116"
    password = "c2dfec8b2b8169720c98953e01e68b5ea22f7a7e"
    # JSON
    data_inicio = datetime.now().strftime("%d/%m/%Y")
    data_fim = (datetime.now() + timedelta(days=5)).strftime("%d/%m/%Y")

    json_data = {
        "empresa": "5328",
        "codigo": "188432",
        "chave": "91f6844a95858aaa2726",
        "tipoSaida": "csv",
        "empresaTrabalho": "5328",
        "dataInicio": data_inicio,
        "dataFim": data_fim,
        "statusAgendaFiltro": "1"
    }

    # Calcula o nonce, created e outros parâmetros necessários
    nonce = secrets.token_bytes(16)
    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    expires = (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    encoded_nonce = base64.b64encode(nonce).decode('utf-8')
    concatenated = nonce + created.encode('utf-8') + password.encode('utf-8')
    password_digest = hashlib.sha1(concatenated).digest()
    encoded_password_digest = base64.b64encode(password_digest).decode('utf-8')
    data_inicio = datetime.now().strftime("%d/%m/%Y")
    data_fim = (datetime.now() + timedelta(days=20)).strftime("%d/%m/%Y")

    json_data['codigoAgenda'] = codigo_agenda
    json_data['dataInicio'] = data_inicio
    json_data['dataFim'] = data_fim

    json_string = json.dumps(json_data)

    payload = f"""
        <soapenv:Envelope xmlns:ser=\"http://services.soc.age.com/\" xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <soapenv:Header>
                <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                    <wsu:Timestamp wsu:Id="TS-32E6B34377D7E4A58614607283662392">
                        <wsu:Created>{created}</wsu:Created>
                        <wsu:Expires>{expires}</wsu:Expires>
                    </wsu:Timestamp>
                    <wsse:UsernameToken wsu:Id="UsernameToken32E6B34377D7E4A58614607283662221">
                        <wsse:Username>{username}</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{encoded_password_digest}</wsse:Password>
                        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{encoded_nonce}</wsse:Nonce>
                        <wsu:Created>{created}</wsu:Created>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
                <ser:exportaDadosWs>
                    <arg0>
                            <parametros>{json_string}</parametros>
                    </arg0>
                </ser:exportaDadosWs>/
            </soapenv:Body>
        </soapenv:Envelope>
        """

    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
    }

    response = requests.post(url, data=payload, headers=headers)

    if response.status_code == 200:
        print('Solicitação SOAP feita com sucesso!')
        cleaned_response = re.sub(r'<.*?>', '', response.text)
        df = pd.read_csv(StringIO(cleaned_response), sep=';')
        response.close()
        return df
    else:
        print('Erro ao fazer a solicitação SOAP. Código de status:', response.status_code)
        return None


@app.route('/consultar_agenda', methods=['GET', 'POST'])
def consultar_agenda():
    global df
    print("Recebendo solicitação para consultar a agenda")
    data = request.get_json()
    codigo_agenda = data['codigoAgenda']

    # Print para mostrar a mudança na seleção da unidade de atendimento e o código de agenda correspondente
    # print(f'Unidade de atendimento selecionada: {codigo_agenda}')

    # Chamar a função processar_agenda com o código da agenda recebido
    df = processar_agenda(codigo_agenda)
    df = df[['data', 'horario']]
    # print("DataFrame:", df)  # Verifica se o DataFrame está sendo preenchido corretamente

    # Remover valores ausentes da coluna 'data'
    df_data = df.dropna(subset=['data'])

    # Converta as datas para objetos datetime
    datas_unicas = df_data['data'].unique().tolist()
    # print("Datas únicas:", datas_unicas)

    # Renderizar o template index.html e passar os dados necessários para ele
    return jsonify(choices=datas_unicas)


@app.route('/horarios_disponiveis', methods=['POST'])
def horarios_disponiveis():
    global df
    data = request.get_json()
    selected_date = data['selectedDate']

    # Filtrar o DataFrame original com base na data selecionada
    horarios_disponiveis = df[df['data'] == selected_date]['horario'].tolist()

    return jsonify(horarios_disponiveis=horarios_disponiveis)


def obter_dados_csv(cnpj):
    url = "https://ws1.soc.com.br/WSSoc/services/ExportaDadosWs"
    username = "U2732116"
    password = "c2dfec8b2b8169720c98953e01e68b5ea22f7a7e"

    nonce = secrets.token_bytes(16)
    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    expires = (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    encoded_nonce = base64.b64encode(nonce).decode('utf-8')
    concatenated = nonce + created.encode('utf-8') + password.encode('utf-8')
    password_digest = hashlib.sha1(concatenated).digest()
    encoded_password_digest = base64.b64encode(password_digest).decode('utf-8')

    json_data = {
        "empresa": "5328",
        "codigo": "142264",
        "chave": "74734aa3309c7c40181f",
        "tipoSaida": "csv",
    }

    json_string = json.dumps(json_data)

    payload = f"""
        <soapenv:Envelope xmlns:ser=\"http://services.soc.age.com/\" xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <soapenv:Header>
                <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                    <wsu:Timestamp wsu:Id="TS-32E6B34377D7E4A58614607283662392">
                        <wsu:Created>{created}</wsu:Created>
                        <wsu:Expires>{expires}</wsu:Expires>
                    </wsu:Timestamp>
                    <wsse:UsernameToken wsu:Id="UsernameToken32E6B34377D7E4A58614607283662221">
                        <wsse:Username>{username}</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{encoded_password_digest}</wsse:Password>
                        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{encoded_nonce}</wsse:Nonce>
                        <wsu:Created>{created}</wsu:Created>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
                <ser:exportaDadosWs>
                    <arg0>
                            <parametros>{json_string}</parametros>
                    </arg0>
                </ser:exportaDadosWs>/
            </soapenv:Body>
        </soapenv:Envelope>
        """
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
    }

    response = requests.post(url, data=payload, headers=headers)
    response_soc = response.text

    text_to_remove = 'false{"empresa": "5328", "codigo": "142264", "chave": "74734aa3309c7c40181f", "tipoSaida": "csv"}'
    text_to_remove2 = '</retorno><tipoArquivoRetorno>csv</tipoArquivoRetorno></return></ns2:exportaDadosWsResponse></soap:Body></soap:Envelope>'
    text_to_remove3 = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><ns2:exportaDadosWsResponse xmlns:ns2="http://services.soc.age.com/"><return><erro>false</erro><parametros>{"empresa": "5328", "codigo": "142264", "chave": "74734aa3309c7c40181f", "tipoSaida": "csv"}</parametros><retorno>'

    cleaned_response = response_soc.replace(text_to_remove, '')
    cleaned_response2 = cleaned_response.replace(text_to_remove2, '')
    cleaned_response3 = cleaned_response2.replace(text_to_remove3, '')

    cleaned_response3 = cleaned_response3.replace('\r', '')

    cleaned_response3 = cleaned_response3.replace('&amp;', '&')

    cleaned_response3 = html.unescape(cleaned_response3)

    try:
        df = pd.read_csv(StringIO(cleaned_response3), delimiter=';')
        df_subset = df.loc[(df['CNPJ'] == cnpj) & (df['ATIVO'] != 0), ["CODIGO", "CNPJ"]]
        return df_subset

    except pd.errors.ParserError as e:
        print("Erro ao ler o CSV:", e)

    response.close()


def obter_codigo_empresa_e_codigo(empresaTrabalho, cpf):
    url = "https://ws1.soc.com.br/WSSoc/services/ExportaDadosWs"
    username = "U2732116"
    password = "c2dfec8b2b8169720c98953e01e68b5ea22f7a7e"
    cod_empresa = "5328"
    cod_responsavel = "4195"

    nonce = secrets.token_bytes(16)
    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    expires = (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    encoded_nonce = base64.b64encode(nonce).decode('utf-8')
    concatenated = nonce + created.encode('utf-8') + password.encode('utf-8')
    password_digest = hashlib.sha1(concatenated).digest()
    encoded_password_digest = base64.b64encode(password_digest).decode('utf-8')

    json_data = {
        "empresa": "5328",
        "codigo": "188667",
        "chave": "141721d4118f64d8837b",
        "tipoSaida": "json",
        "empresaTrabalho": empresaTrabalho,
        "cpf": cpf,
        "parametroData": "",
        "dataInicio": "",
        "dataFim": ""
    }

    json_string = json.dumps(json_data)

    payload = f"""
        <soapenv:Envelope xmlns:ser=\"http://services.soc.age.com/\" xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <soapenv:Header>
                <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                    <wsu:Timestamp wsu:Id="TS-32E6B34377D7E4A58614607283662392">
                        <wsu:Created>{created}</wsu:Created>
                        <wsu:Expires>{expires}</wsu:Expires>
                    </wsu:Timestamp>
                    <wsse:UsernameToken wsu:Id="UsernameToken32E6B34377D7E4A58614607283662221">
                        <wsse:Username>{username}</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{encoded_password_digest}</wsse:Password>
                        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{encoded_nonce}</wsse:Nonce>
                        <wsu:Created>{created}</wsu:Created>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
                <ser:exportaDadosWs>
                    <arg0>
                            <parametros>{json_string}</parametros>
                    </arg0>
                </ser:exportaDadosWs>/
            </soapenv:Body>
        </soapenv:Envelope>
        """

    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
    }

    response = requests.post(url, data=payload, headers=headers)
    response.close()

    json_match = re.search(r'<retorno>(.*?)<\/retorno>', response.text, re.DOTALL)
    if json_match:
        json_text = json_match.group(1)
        data = json.loads(json_text)
        if isinstance(data, list) and data:
            primeiro_elemento = data[0]
            codigo_empresa = primeiro_elemento.get('CODIGOEMPRESA')
            codigo = primeiro_elemento.get('CODIGO')
            return codigo_empresa, codigo
    else:
        return None, None


def obter_codigo_e_codigo_empresa_pelo_cnpj_e_cpf(cnpj, cpf):
    # Obtendo o código usando o CNPJ fornecido
    df_subset = obter_dados_csv(cnpj)
    if df_subset is not None and not df_subset.empty:
        codigo_emp = df_subset.iloc[0]['CODIGO']
    else:
        print("Erro ao obter os dados CSV ou nenhum dado encontrado.")
        return None, None  # Retorna explicitamente None, None se houver um erro

    # Convertendo o código para uma string
    empresaTrabalho = str(codigo_emp)

    # Chama a função para obter o código da empresa e o código
    codigo_empresa, codigo = obter_codigo_empresa_e_codigo(empresaTrabalho, cpf)

    # Exibindo o resultado
    if codigo_empresa is not None and codigo is not None:
        # print("Valor de CODIGOEMPRESA:", codigo_empresa)
        # print("Valor de CODIGO:", codigo)
        return codigo_empresa, codigo  # Retorna os valores se forem válidos
    else:
        print("Nenhum JSON encontrado na resposta ou dados inválidos.")
        return None, None  # Retorna explicitamente None, None se houver um erro


def agendar(df, cod_agenda_col, data_col, hora_col, cod_empresa_col, cod_funcionario_col, tipo_compromisso_col,
            email_col):
    for index, row in df.iterrows():
        cod_agenda = row[cod_agenda_col]
        data = row[data_col]
        hora = row[hora_col]
        cod_empresa_cliente = row[cod_empresa_col]
        cod_funcionario_cliente = row[cod_funcionario_col]
        tipo_compromisso = row[tipo_compromisso_col]
        email = row[email_col]

        # Obter a data e hora atuais
        data_hora_atual = datetime.now()
        data_hora_envio_email = data_hora_atual + timedelta(minutes=5)
        data_envio_email = data_hora_envio_email.strftime('%d/%m/%Y')
        hora_envio_email = data_hora_envio_email.strftime('%H:%M')
        # Strings fixas
        url = "https://ws1.soc.com.br/WSSoc/AgendamentoWs"
        username = "U2732116"
        password = "c2dfec8b2b8169720c98953e01e68b5ea22f7a7e"
        cod_empresa = "5328"
        cod_responsavel = "4195"
        tipo_busca_funcionario = "CODIGO_SOC"
        tipo_busca_empresa = "CODIGO_SOC"

        # Parafernalha para rodar o cabeçario
        nonce = secrets.token_bytes(16)
        created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")  # Usando UTC 0
        expires = (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")  # Usando UTC 0
        encoded_nonce = base64.b64encode(nonce).decode('utf-8')
        concatenated = nonce + created.encode('utf-8') + password.encode('utf-8')
        password_digest = hashlib.sha1(concatenated).digest()
        encoded_password_digest = base64.b64encode(password_digest).decode('utf-8')

        payload = f"""
        <soapenv:Envelope xmlns:ser=\"http://services.soc.age.com/\" xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <soapenv:Header>
                <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                    <wsu:Timestamp wsu:Id="TS-32E6B34377D7E4A58614607283662392">
                        <wsu:Created>{created}</wsu:Created>
                        <wsu:Expires>{expires}</wsu:Expires>
                    </wsu:Timestamp>
                    <wsse:UsernameToken wsu:Id="UsernameToken32E6B34377D7E4A58614607283662221">
                        <wsse:Username>{username}</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{encoded_password_digest}</wsse:Password>
                        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{encoded_nonce}</wsse:Nonce>
                        <wsu:Created>{created}</wsu:Created>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
                <ser:incluirAgendamento>
                    <IncluirAgendamentoWsVo>
                        <identificacaoWsVo>
                            <chaveAcesso>{password}</chaveAcesso>
                            <codigoEmpresaPrincipal>{cod_empresa}</codigoEmpresaPrincipal> 
                            <codigoResponsavel>{cod_responsavel}</codigoResponsavel>
                            <homologacao>false</homologacao>
                            <codigoUsuario>{username}</codigoUsuario>
                        </identificacaoWsVo>
                        <dadosAgendamentoWsVo>
                            <tipoBuscaEmpresa>{tipo_busca_empresa}</tipoBuscaEmpresa>
                            <codigoEmpresa>{cod_empresa_cliente}</codigoEmpresa>
                            <reservarCompromissoParaEmpresa></reservarCompromissoParaEmpresa>
                            <tipoBuscaFuncionario>{tipo_busca_funcionario}</tipoBuscaFuncionario>
                            <codigoFuncionario>{cod_funcionario_cliente}</codigoFuncionario>
                            <codigoUsuarioAgenda>{cod_agenda}</codigoUsuarioAgenda>
                            <data>{data}</data>
                            <horaInicial>{hora}</horaInicial>
                            <horaFinal></horaFinal>
                            <codigoCompromisso></codigoCompromisso>
                            <usaOutroCompromisso></usaOutroCompromisso>
                            <conteudoOutroCompromisso></conteudoOutroCompromisso>
                            <tipoCompromisso>{tipo_compromisso}</tipoCompromisso>
                            <detalhes>Anuncie aqui</detalhes>
                            <codigoProfissionalAgenda></codigoProfissionalAgenda>
                            <horarioChegada></horarioChegada>
                            <horarioSaida></horarioSaida>
                            <priorizarAtendimento></priorizarAtendimento>
                            <atendido></atendido>
                            <codigoMotivoCancelamento></codigoMotivoCancelamento>
                            <usaEnviarEmail>true</usaEnviarEmail>
                            <emailWsVo>
                                <data>{data_envio_email}</data>
                                <hora>{hora_envio_email}</hora>
                                <email>{email}</email>
                            </emailWsVo>
                            <usaEnviarSocms></usaEnviarSocms>
                            <socmsWsVo>
                                <data></data>
                                <hora></hora>
                                <telefone></telefone>
                                <codigoMensagem></codigoMensagem>
                                <mensagem>Mensagem teste</mensagem>
                            </socmsWsVo>
                        </dadosAgendamentoWsVo>
                    </IncluirAgendamentoWsVo>
                </ser:incluirAgendamento>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        headers = {
            'Content-Type': 'application/xml'
        }
        response = requests.request("POST", url, headers=headers, data=payload)

        root = etree.fromstring(response.text)
        resposta = etree.tostring(root, pretty_print=True).decode()
        # print(resposta)

        # print(f"\n Response = {response.status_code}")

# ---------------------------------------------  Processamento_Formulario -----------------------------------------
# Mapeamento para correção de inserção de dados no SOC
mapeamento_tipo_exame = {
    'Admissional': 'ADMISSIONAL',
    'Demissional': 'DEMISSIONAL',
    'Periódico': 'PERIODICO',
    'Retorno ao Trabalho': 'RETORNO_TRABALHO',
    'Mudança de Função': 'MUDANCA_FUNCAO'
}
mapeamento_unidades = {
    'Selecione uma unidade': 273133,
    'Alphaville': 16145,
    'Ipiranga': 4225,
    'Jabaquara': 38532,
    'Teste': 273133
}


@app.route('/submit', methods=['POST'])
def submit():
    global df_dados_agendamento

    if request.method == 'POST':
        # Pegar os dados do formulário
        tipo_exame = request.form['tipo_exame']
        empresa = request.form['empresa']
        cnpj = request.form['cnpj']
        nome_funcionario = request.form['nome_funcionario']
        cpf_funcionario = request.form['cpf_funcionario']
        email_contato = request.form['email_contato']
        unidade_atendimento = request.form['unidade_atendimento']
        data_atendimento = request.form['data_atendimento']
        horario_atendimento = request.form['horario_atendimento']

        # Aplicar mapeamento para Tipo de Exame
        tipo_exame = mapeamento_tipo_exame.get(tipo_exame, tipo_exame)

        # Aplicar mapeamento para Unidade de Atendimento
        unidade_atendimento = mapeamento_unidades.get(unidade_atendimento, unidade_atendimento)

        # Remover pontos, barras e espaços do CPF do funcionário
        cpf_funcionario = cpf_funcionario.replace('.', '').replace('-', '').replace(' ', '')

        # Supondo que você já tenha a função para obter os códigos
        codigo_empresa, codigo_funcionario = obter_codigo_e_codigo_empresa_pelo_cnpj_e_cpf(cnpj, cpf_funcionario)

        # Criar um DataFrame com as colunas correspondentes ao formulário
        novo_agendamento = {
            'Tipo de Exame': [tipo_exame],
            'Empresa': [empresa],
            'CNPJ': [cnpj],
            'Nome do Funcionário': [nome_funcionario],
            'CPF do Funcionário': [cpf_funcionario],
            'Email para Contato': [email_contato],  # Apenas uma vez
            'Unidade de Atendimento': [unidade_atendimento],  # Apenas uma vez
            'Data do Atendimento': [data_atendimento],  # Apenas uma vez
            'Horário do Atendimento': [horario_atendimento],  # Apenas uma vez
            'Cod Empresa': [codigo_empresa],
            'Cod Funcionário': [codigo_funcionario]
        }

        # Criar DataFrame a partir do dicionário
        df_novo_agendamento = pd.DataFrame(novo_agendamento)

        # Concatenar o novo DataFrame com o DataFrame existente
        df_dados_agendamento = pd.concat([df_dados_agendamento, df_novo_agendamento], ignore_index=True)

        # Imprimir o DataFrame para verificar se os dados foram adicionados corretamente
        # print("Dados do agendamento:")
        # print(df_dados_agendamento.to_string())

        # Agendar os compromissos
        agendar(df_dados_agendamento,
                'Unidade de Atendimento',
                'Data do Atendimento',
                'Horário do Atendimento',
                'Cod Empresa',
                'Cod Funcionário',
                'Tipo de Exame',
                'Email para Contato')

        return render_template('concluido.html')


@app.route('/buscar_empresa', methods=['POST'])
def buscar_empresa():
    global dados_hierarquia  # Define a variável como global

    cnpj = request.json.get('cnpj')
    print("CNPJ enviado pelo navegador:", cnpj)  # Imprime o valor do CNPJ
    df_subset = obter_dados_csv_hierarquia(cnpj)

    # Verifica se o DataFrame não está vazio
    if not df_subset.empty:
        # Acessa o valor de CODIGO
        codigo = df_subset.iloc[0]['CODIGO']
        print("Codigo enviado:", codigo)
        razao_social = df_subset.iloc[0]['RAZAOSOCIAL']
        print("Razao:", razao_social)

        # Chama a função hierarquia_empresa com o código
        df_subset_filtrado = hierarquia_empresa(codigo)

        # Extrai os nomes das unidades do DataFrame filtrado
        unidades = df_subset_filtrado['NOME_UNIDADE'].unique().tolist()

        # Atualiza a variável global
        dados_hierarquia = df_subset_filtrado

        return jsonify(unidades=unidades, razaosocial=razao_social)
    else:
        print("Nenhum dado encontrado para o CNPJ fornecido.")
        return jsonify({'error': 'Nenhum dado encontrado para o CNPJ fornecido'}), 404


def obter_dados_csv_hierarquia(cnpj):
    url = "https://ws1.soc.com.br/WSSoc/services/ExportaDadosWs"
    username = "U2732116"
    password = "c2dfec8b2b8169720c98953e01e68b5ea22f7a7e"

    nonce = secrets.token_bytes(16)
    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    expires = (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    encoded_nonce = base64.b64encode(nonce).decode('utf-8')
    concatenated = nonce + created.encode('utf-8') + password.encode('utf-8')
    password_digest = hashlib.sha1(concatenated).digest()
    encoded_password_digest = base64.b64encode(password_digest).decode('utf-8')

    json_data = {
        "empresa": "5328",
        "codigo": "142264",
        "chave": "74734aa3309c7c40181f",
        "tipoSaida": "csv",
    }

    json_string = json.dumps(json_data)

    payload = f"""
        <soapenv:Envelope xmlns:ser=\"http://services.soc.age.com/\" xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <soapenv:Header>
                <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                    <wsu:Timestamp wsu:Id="TS-32E6B34377D7E4A58614607283662392">
                        <wsu:Created>{created}</wsu:Created>
                        <wsu:Expires>{expires}</wsu:Expires>
                    </wsu:Timestamp>
                    <wsse:UsernameToken wsu:Id="UsernameToken32E6B34377D7E4A58614607283662221">
                        <wsse:Username>{username}</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{encoded_password_digest}</wsse:Password>
                        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{encoded_nonce}</wsse:Nonce>
                        <wsu:Created>{created}</wsu:Created>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
                <ser:exportaDadosWs>
                    <arg0>
                            <parametros>{json_string}</parametros>
                    </arg0>
                </ser:exportaDadosWs>/
            </soapenv:Body>
        </soapenv:Envelope>
        """
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
    }

    response = requests.post(url, data=payload, headers=headers)
    response_soc = response.text

    text_to_remove = 'false{"empresa": "5328", "codigo": "142264", "chave": "74734aa3309c7c40181f", "tipoSaida": "csv"}'
    text_to_remove2 = '</retorno><tipoArquivoRetorno>csv</tipoArquivoRetorno></return></ns2:exportaDadosWsResponse></soap:Body></soap:Envelope>'
    text_to_remove3 = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><ns2:exportaDadosWsResponse xmlns:ns2="http://services.soc.age.com/"><return><erro>false</erro><parametros>{"empresa": "5328", "codigo": "142264", "chave": "74734aa3309c7c40181f", "tipoSaida": "csv"}</parametros><retorno>'

    cleaned_response = response_soc.replace(text_to_remove, '')
    cleaned_response2 = cleaned_response.replace(text_to_remove2, '')
    cleaned_response3 = cleaned_response2.replace(text_to_remove3, '')

    cleaned_response3 = cleaned_response3.replace('\r', '')

    cleaned_response3 = cleaned_response3.replace('&amp;', '&')

    cleaned_response3 = html.unescape(cleaned_response3)

    try:
        df = pd.read_csv(StringIO(cleaned_response3), delimiter=';')
        df_subset = df.loc[(df['CNPJ'] == cnpj) & (df['ATIVO'] != 0), ["CODIGO", "CNPJ","RAZAOSOCIAL"]]
        return df_subset
    except pd.errors.ParserError as e:
        print("Erro ao ler o CSV:", e)

    response.close()


def hierarquia_empresa(cod_empresa):
    url = "https://ws1.soc.com.br/WSSoc/services/ExportaDadosWs"
    username = "U2732116"
    password = "c2dfec8b2b8169720c98953e01e68b5ea22f7a7e"
    nonce = secrets.token_bytes(16)
    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")  # Usando UTC 0
    expires = (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")  # Usando UTC 0
    #Base64
    encoded_nonce = base64.b64encode(nonce).decode('utf-8')
    concatenated = nonce + created.encode('utf-8') + password.encode('utf-8')
    password_digest = hashlib.sha1(concatenated).digest()
    encoded_password_digest = base64.b64encode(password_digest).decode('utf-8')

    json_data = {
        "empresa": f"{cod_empresa}",
        "codigo": "191014",
        "chave": "8d5bf056dde96ffdcd87",
        "tipoSaida": "csv",
    }

    #JSON para uma string
    json_string = json.dumps(json_data)

    #Deus abençoe
    payload = f"""
        <soapenv:Envelope xmlns:ser=\"http://services.soc.age.com/\" xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
            <soapenv:Header>
                <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                    <wsu:Timestamp wsu:Id="TS-32E6B34377D7E4A58614607283662392">
                        <wsu:Created>{created}</wsu:Created>
                        <wsu:Expires>{expires}</wsu:Expires>
                    </wsu:Timestamp>
                    <wsse:UsernameToken wsu:Id="UsernameToken32E6B34377D7E4A58614607283662221">
                        <wsse:Username>{username}</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{encoded_password_digest}</wsse:Password>
                        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{encoded_nonce}</wsse:Nonce>
                        <wsu:Created>{created}</wsu:Created>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
                <ser:exportaDadosWs>
                    <arg0>
                            <parametros>{json_string}</parametros>
                    </arg0>
                </ser:exportaDadosWs>/
            </soapenv:Body>
        </soapenv:Envelope>
        """
    # Código de chamada para a API....
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
    }

    # Faz a solicitação à API
    response = requests.post(url, data=payload, headers=headers)
    response_soc = response.text

    # Remova os caracteres de retorno de carro das linhas
    response_soc = response_soc.replace('\r', '')

    # Substitua &amp; por & em todas as linhas
    response_soc = response_soc.replace('&amp;', '&')

    # Substitua as entidades HTML por caracteres correspondentes em todas as linhas
    response_soc = html.unescape(response_soc)

    # Tente ler o CSV novamente com o delimitador especificado como ';'
    try:
        df = pd.read_csv(StringIO(response_soc), delimiter=';')
        df_subset = df.loc[:, ["NOME_SETOR", "CODIGO_SETOR", "NOME_CARGO", "CODIGO_CARGO", "NOME_UNIDADE",
                               "CODIGO_UNIDADE", "ATIVO_UNIDADE", "ATIVO_SETOR", "ATIVO_CARGO"]]
        df_subset_filtrado = df_subset.loc[
            (df_subset['ATIVO_UNIDADE'] == 'Sim') & (df_subset['ATIVO_SETOR'] == 'Sim') & (df_subset['ATIVO_CARGO'] ==
                                                                                           'Sim')].dropna()

        # Exibir o DataFrame filtrado
        print(df_subset_filtrado)
        # Retorna o DataFrame filtrado
        return df_subset_filtrado

    except pd.errors.ParserError as e:
        print("Erro ao ler o CSV:", e)

    response.close()


@app.route('/buscar_setor', methods=['POST'])
def buscar_setor():
    global df
    unidade = request.get_json()
    selected_unidade = unidade['selectUnidade']

    # Filtrar o DataFrame original com base na data selecionada
    setores_disponiveis = (dados_hierarquia[dados_hierarquia['NOME_UNIDADE'] == selected_unidade]['NOME_SETOR'].unique()
                           .tolist())

    return jsonify(setores_disponiveis=setores_disponiveis)


@app.route('/buscar_cargo', methods=['POST'])
def buscar_cargo():
    global df
    setor = request.get_json()
    selected_unidade = setor['selectSetor']

    # Filtrar o DataFrame original com base na data selecionada
    cargos_disponiveis = (dados_hierarquia[dados_hierarquia['NOME_SETOR'] == selected_unidade]['NOME_CARGO'].unique().
                          tolist())

    return jsonify(cargos_disponiveis=cargos_disponiveis)


@app.route('/cadastro_funcionario_submit', methods=['POST'])
def cadastro_funcionario_submit():
    global df_dados_novo_funcionario

    if request.method == 'POST':
        # Pegar os dados do formulário
        nome = request.form['nome']
        estado_civil = request.form['estado_civil']
        cpf = request.form['cpf']
        rg = request.form['rg']
        uf_rg = request.form['uf_rg']
        sexo = request.form['sexo']
        genero = request.form['genero']
        data_nascimento = request.form['data_nascimento']
        data_admissao = request.form['data_admissao']
        cnpj = request.form['cnpj']
        unidade = request.form['unidade']
        setor = request.form['setor']
        cargo = request.form['cargo']
        con_trabalho = request.form['con_trabalho']
        reg_trabalho = request.form['reg_trabalho']

        codigo_funcionario = obter_dados_csv(cnpj)
        codigo_empresa = codigo_funcionario.iloc[0]['CODIGO']
        print(codigo_empresa)


        # Converter strings de data em objetos de data e formatá-los
        data_nascimento_formatada = datetime.strptime(data_nascimento, '%Y-%m-%d').strftime('%d/%m/%Y')
        data_admissao_formatada = datetime.strptime(data_admissao, '%Y-%m-%d').strftime('%d/%m/%Y')

        # Remover pontos, barras e espaços do CPF do funcionário
        cpf = cpf.replace('.', '').replace('-', '').replace(' ', '')

        # Criar um DataFrame com as colunas correspondentes ao formulário
        novo_funcionario = {
            'Cod_empresa': [codigo_empresa],
            'Nome': [nome],
            'Estado Civil': [estado_civil],
            'CPF': [cpf],
            'RG': [rg],
            'UF_RG': [uf_rg],
            'Sexo': [sexo],
            'Genero': [genero],
            'Data_nascimento': [data_nascimento_formatada],
            'data_admissao': [data_admissao_formatada],
            'cnpj': [cnpj],
            'unidade': [unidade],
            'setor': [setor],
            'cargo': [cargo],
            'con_trabalho': [con_trabalho],
            'reg_trabalho': [reg_trabalho]
        }

        # Criar DataFrame a partir do dicionário
        df_novo_funcionario = pd.DataFrame(novo_funcionario)

        # Verificar se o DataFrame global já foi inicializado
        if df_dados_novo_funcionario.empty:
            df_dados_novo_funcionario = df_novo_funcionario
        else:
            # Concatenar o novo DataFrame com o DataFrame existente
            df_dados_novo_funcionario = pd.concat([df_dados_novo_funcionario, df_novo_funcionario], ignore_index=True)

        # Imprimir o DataFrame para verificar se os dados foram adicionados corretamente
        print("Dados do novo funcionário:")
        print(df_dados_novo_funcionario.to_string())

        # Iterar sobre as linhas do DataFrame
        for index, row in df_dados_novo_funcionario.iterrows():
            # Extrair os dados da linha atual
            EmpCliente = row['Cod_empresa']
            Nome = row['Nome']
            DtNascimento = row['Data_nascimento']
            DtAdmissao = row['data_admissao']
            Sexo = row['Sexo']
            CPF = row['CPF']
            RG = row['RG']
            UF_RG = row['UF_RG']
            EST_Civil = row['Estado Civil']
            Unidade = row['unidade']
            Setor = row['setor']
            Cargo = row['cargo']
            Con_Trabalho = row['con_trabalho']
            Reg_Trabalho = row['reg_trabalho']

            # Chamar a função para enviar os dados do funcionário para a empresa
            enviar_dados_funcionario_empresa(EmpCliente, Nome, DtNascimento, DtAdmissao, Sexo, CPF, RG, UF_RG,
                                             EST_Civil, Unidade, Setor, Cargo, Con_Trabalho, Reg_Trabalho)

        # Redirecionar para a página de conclusão após o cadastro
        return redirect(url_for('cadastro_concluido'))

    # Se a solicitação não for POST, retornar um redirecionamento ou uma resposta adequada
    return redirect(url_for('pagina_de_cadastro'))  # Substitua 'pagina_de_cadastro' pela rota correta da página de cadastro de funcionário


@app.route('/cadastro_concluido')
def cadastro_concluido():
    return 'Cadastro de funcionário realizado com sucesso!'


def enviar_dados_funcionario_empresa(EmpCliente, Nome, DtNascimento, DtAdmissao, Sexo, CPF, RG, UF_RG, EST_Civil, Unidade, Setor, Cargo, Con_Trabalho, Reg_Trabalho):
    url = "https://ws1.soc.com.br/WSSoc/FuncionarioModelo2Ws"
    username = "U2732116"
    password = "c2dfec8b2b8169720c98953e01e68b5ea22f7a7e"
    EmpPrincipal = '5328'
    Responsavel = '4195'
    nonce = secrets.token_bytes(16)
    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")  # Usando UTC 0
    expires = (datetime.utcnow() + timedelta(minutes=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")  # Usando UTC 0
    encoded_nonce = base64.b64encode(nonce).decode('utf-8')
    concatenated = nonce + created.encode('utf-8') + password.encode('utf-8')
    password_digest = hashlib.sha1(concatenated).digest()
    encoded_password_digest = base64.b64encode(password_digest).decode('utf-8')
    # Dados SOC (FIXOS)
    TipoBuscaUnidade = 'NOME'
    TipoBuscaSetor = 'NOME'
    TipoBuscaCargo = 'NOME'
    tipoBuscaEmpresa = 'CODIGO_SOC'
    TipoBuscaFuncionario = 'CODIGO'
    TipoBuscaCPF = 'CPF_ATIVO'
    Situacao = 'ATIVO'
    Matricula = 'N/C'

    payload = f"""
    <soapenv:Envelope xmlns:ser=\"http://services.soc.age.com/\" xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
        <soapenv:Header>
            <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-32E6B34377D7E4A58614607283662392">
                <wsu:Created>{created}</wsu:Created>
                <wsu:Expires>{expires}</wsu:Expires>
            </wsu:Timestamp>
            <wsse:UsernameToken wsu:Id="UsernameToken32E6B34377D7E4A58614607283662221">
                <wsse:Username>{username}</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{encoded_password_digest}</wsse:Password>
                <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{encoded_nonce}</wsse:Nonce>
                <wsu:Created>{created}</wsu:Created>
              </wsse:UsernameToken>
            </wsse:Security>
        </soapenv:Header>
     <soapenv:Body>
        <ser:importacaoFuncionario>
           <Funcionario>
              <atualizarCargo>true</atualizarCargo>
              <atualizarCentroCusto>true</atualizarCentroCusto>
              <atualizarFuncionario>true</atualizarFuncionario>
              <atualizarSetor>true</atualizarSetor>
              <atualizarUnidade>true</atualizarUnidade>
              <cargoWsVo>
                 <codigo>true</codigo>
                 <nome>{Cargo}</nome>
                 <tipoBusca>{TipoBuscaCargo}</tipoBusca>
                 <atividadesPerigosasWsVo>
                    <!--Zero or more repetitions:-->
                 </atividadesPerigosasWsVo>
              </cargoWsVo>
                 <criarFuncionario>true</criarFuncionario>
              <funcionarioWsVo>
                 <chaveProcuraFuncionario>{TipoBuscaCPF}</chaveProcuraFuncionario>
                 <codigoEmpresa>{EmpCliente}</codigoEmpresa>
                 <cpf>{CPF}</cpf>
                 <dataAdmissao>{DtAdmissao}</dataAdmissao>
                 <dataNascimento>{DtNascimento}</dataNascimento>
                 <matricula>{Matricula}</matricula>
                 <estadoCivil>{EST_Civil}</estadoCivil>
                 <nomeFuncionario>{Nome}</nomeFuncionario>
                 <regimeTrabalho>{Reg_Trabalho}</regimeTrabalho>
                 <tipoContratacao>{Con_Trabalho}</tipoContratacao>
                 <rg>{RG}</rg>
                 <rgUf>{UF_RG}</rgUf>
                 <sexo>{Sexo}</sexo>
                 <situacao>{Situacao}</situacao>
                 <tipoBuscaEmpresa>{tipoBuscaEmpresa}</tipoBuscaEmpresa>
                 <tipoContratacao>{Con_Trabalho}</tipoContratacao>
                 <atividadesPerigosasWsVo>
                    <!--Zero or more repetitions:-->
                 </atividadesPerigosasWsVo>
              </funcionarioWsVo>
              <!--Optional:-->
              <identificacaoWsVo>
                 <chaveAcesso>{password}</chaveAcesso>
                 <codigoEmpresaPrincipal>{EmpPrincipal}</codigoEmpresaPrincipal>
                 <codigoResponsavel>{Responsavel}</codigoResponsavel>
                 <codigoUsuario>{username}</codigoUsuario>
              </identificacaoWsVo>
              <naoImportarFuncionarioSemHierarquia>true</naoImportarFuncionarioSemHierarquia>
              <setorWsVo>
                 <nome>{Setor}</nome>
                 <tipoBusca>{TipoBuscaSetor}</tipoBusca>
              </setorWsVo>
              <unidadeWsVo>
                 <nome>{Unidade}</nome>
                 <tipoBusca>{TipoBuscaUnidade}</tipoBusca>
              </unidadeWsVo>
           </Funcionario>
        </ser:importacaoFuncionario>
     </soapenv:Body>
    </soapenv:Envelope>
    """
    headers = {'Content-Type': 'application/xml'}
    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.status_code)
    root = etree.fromstring(response.text)
    print(etree.tostring(root, pretty_print=True).decode())
    print("funcionario cadastrado")
    response.close()


if __name__ == '__main__':
    app.run(debug=True)
