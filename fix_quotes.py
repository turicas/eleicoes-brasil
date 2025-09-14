import argparse
import io
import re
import sys
from pathlib import Path

from tqdm import tqdm

REGEXP_REPLACES = (
    (re.compile(r'([^;"])"([^;"])'), r'\1""\2'),
    (re.compile(r'([^;"])"([^;"])'), r'\1""\2'),  # Repeated so on '... "C" ...' the replace works for both quotes
    (re.compile(r'([^"])"";"([^"])'), r'\1""";"\2'),
    (re.compile('";";"'), '""";"'),
    (re.compile(r';""([^"]+)'), r';"""\1'),
)


def fix_line(text):
    finish = ""
    for endline in ("\r\n", "\n"):
        if text.endswith(endline):
            text = text[: -len(endline)]
            finish = endline
            break
    for regexp, replace in REGEXP_REPLACES:
        text = regexp.sub(replace, text)
    return text + finish


def test_fix_line_1_1():
    line = """
    "09/12/2020";"10.000 SANTINHOS "VEREADOR ELIETE DE RUI";"160,00"
    """.strip()
    expected = """
    "09/12/2020";"10.000 SANTINHOS ""VEREADOR ELIETE DE RUI";"160,00"
    """.strip()
    assert fix_line(line + "\n") == expected + "\n"


def test_fix_line_1_2():
    line = """
    "13/11/2020";"ABRACADEIRA (100PCS) BFH0312/3046 4·8X200MM PRETO | ABRACADEIRA NYLON 4;8X500MM PR 100 PCS - KALA | ALCOOL 70% ALVO 5L | ALCOOL LIQ MEGA 70 INPM HOSPITALAR PROFISSIONAL | COLHER DE PEDREIRO CANTO VIVO 7" C/CB. DE MADEIRA | CONE DE SINALIZAÇÃO FLEXIVE...";"1459,90"
    """.strip()
    expected = """
    "13/11/2020";"ABRACADEIRA (100PCS) BFH0312/3046 4·8X200MM PRETO | ABRACADEIRA NYLON 4;8X500MM PR 100 PCS - KALA | ALCOOL 70% ALVO 5L | ALCOOL LIQ MEGA 70 INPM HOSPITALAR PROFISSIONAL | COLHER DE PEDREIRO CANTO VIVO 7"" C/CB. DE MADEIRA | CONE DE SINALIZAÇÃO FLEXIVE...";"1459,90"
    """.strip()
    assert fix_line(line + "\n") == expected + "\n"


def test_fix_line_1_3():
    line = """
    "DT_GERACAO";"HH_GERACAO";"ANO_ELEICAO";"CD_TIPO_ELEICAO";"NM_TIPO_ELEICAO";"CD_ELEICAO";"DS_ELEICAO";"DT_ELEICAO";"ST_TURNO";"TP_PRESTACAO_CONTAS";"DT_PRESTACAO_CONTAS";"SQ_PRESTADOR_CONTAS";"SG_UF";"SG_UE";"NM_UE";"NR_CNPJ_PRESTADOR_CONTA";"CD_CARGO";"DS_CARGO";"SQ_CANDIDATO";"NR_CANDIDATO";"NM_CANDIDATO";"NR_CPF_CANDIDATO";"NR_CPF_VICE_CANDIDATO";"NR_PARTIDO";"SG_PARTIDO";"NM_PARTIDO";"CD_TIPO_FORNECEDOR";"DS_TIPO_FORNECEDOR";"CD_CNAE_FORNECEDOR";"DS_CNAE_FORNECEDOR";"NR_CPF_CNPJ_FORNECEDOR";"NM_FORNECEDOR";"NM_FORNECEDOR_RFB";"CD_ESFERA_PART_FORNECEDOR";"DS_ESFERA_PART_FORNECEDOR";"SG_UF_FORNECEDOR";"CD_MUNICIPIO_FORNECEDOR";"NM_MUNICIPIO_FORNECEDOR";"SQ_CANDIDATO_FORNECEDOR";"NR_CANDIDATO_FORNECEDOR";"CD_CARGO_FORNECEDOR";"DS_CARGO_FORNECEDOR";"NR_PARTIDO_FORNECEDOR";"SG_PARTIDO_FORNECEDOR";"NM_PARTIDO_FORNECEDOR";"DS_TIPO_DOCUMENTO";"NR_DOCUMENTO";"CD_ORIGEM_DESPESA";"DS_ORIGEM_DESPESA";"SQ_DESPESA";"DT_DESPESA";"DS_DESPESA";"VR_DESPESA_CONTRATADA"
    """.strip()
    expected = """
    "DT_GERACAO";"HH_GERACAO";"ANO_ELEICAO";"CD_TIPO_ELEICAO";"NM_TIPO_ELEICAO";"CD_ELEICAO";"DS_ELEICAO";"DT_ELEICAO";"ST_TURNO";"TP_PRESTACAO_CONTAS";"DT_PRESTACAO_CONTAS";"SQ_PRESTADOR_CONTAS";"SG_UF";"SG_UE";"NM_UE";"NR_CNPJ_PRESTADOR_CONTA";"CD_CARGO";"DS_CARGO";"SQ_CANDIDATO";"NR_CANDIDATO";"NM_CANDIDATO";"NR_CPF_CANDIDATO";"NR_CPF_VICE_CANDIDATO";"NR_PARTIDO";"SG_PARTIDO";"NM_PARTIDO";"CD_TIPO_FORNECEDOR";"DS_TIPO_FORNECEDOR";"CD_CNAE_FORNECEDOR";"DS_CNAE_FORNECEDOR";"NR_CPF_CNPJ_FORNECEDOR";"NM_FORNECEDOR";"NM_FORNECEDOR_RFB";"CD_ESFERA_PART_FORNECEDOR";"DS_ESFERA_PART_FORNECEDOR";"SG_UF_FORNECEDOR";"CD_MUNICIPIO_FORNECEDOR";"NM_MUNICIPIO_FORNECEDOR";"SQ_CANDIDATO_FORNECEDOR";"NR_CANDIDATO_FORNECEDOR";"CD_CARGO_FORNECEDOR";"DS_CARGO_FORNECEDOR";"NR_PARTIDO_FORNECEDOR";"SG_PARTIDO_FORNECEDOR";"NM_PARTIDO_FORNECEDOR";"DS_TIPO_DOCUMENTO";"NR_DOCUMENTO";"CD_ORIGEM_DESPESA";"DS_ORIGEM_DESPESA";"SQ_DESPESA";"DT_DESPESA";"DS_DESPESA";"VR_DESPESA_CONTRATADA"
    """.strip()
    assert fix_line(line + "\n") == expected + "\n"


def test_fix_line_1_4():
    line = """
    "09/04/2023";"10:01:10";"2018";"2";"Ordinária";"297";"Eleições Gerais Estaduais 2018";"07/10/2018";"1";"Final";"06/11/2018";"422659836";"RO";"Outro";"850035";"2";"Fundo Especial de Financiamento de Campanha";"20120000";"Serviços prestados por terceiros";"1";"Financeiro";"0";"Cheque";"22431982";"14475480";"03/10/2018";"SERVIÇO COMO COLABORADOR | VALE TRANSPORTE";"1000,00"
    """.strip()
    expected = """
    "09/04/2023";"10:01:10";"2018";"2";"Ordinária";"297";"Eleições Gerais Estaduais 2018";"07/10/2018";"1";"Final";"06/11/2018";"422659836";"RO";"Outro";"850035";"2";"Fundo Especial de Financiamento de Campanha";"20120000";"Serviços prestados por terceiros";"1";"Financeiro";"0";"Cheque";"22431982";"14475480";"03/10/2018";"SERVIÇO COMO COLABORADOR | VALE TRANSPORTE";"1000,00"
    """.strip()
    assert fix_line(line + "\n") == expected + "\n"


def test_fix_line_1_5():
    line = """
    "09/04/2023";"10:01:10";"2018";"2";"Ordinária";"297";"Eleições Gerais Estaduais 2018";"07/10/2018";"1";"Final";"18/11/2018";"424376175";"MG";"Nota Fiscal";"900265";"1";"Outros Recursos";"20130000";"Publicidade por jornais e revistas";"1";"Financeiro";"0";"Cheque";"23969555";"16113052";"19/10/2018";"ANÚNCIO FORMATO A4 JORNAL "TÁ NA CARA"";"400,00"
    """.strip()
    expected = '''
    "09/04/2023";"10:01:10";"2018";"2";"Ordinária";"297";"Eleições Gerais Estaduais 2018";"07/10/2018";"1";"Final";"18/11/2018";"424376175";"MG";"Nota Fiscal";"900265";"1";"Outros Recursos";"20130000";"Publicidade por jornais e revistas";"1";"Financeiro";"0";"Cheque";"23969555";"16113052";"19/10/2018";"ANÚNCIO FORMATO A4 JORNAL ""TÁ NA CARA""";"400,00"
    '''.strip()
    assert fix_line(line + "\n") == expected + "\n"


def test_fix_line_1_6():
    line = """
    "09/04/2023";"10:01:10";"2018";"2";"Ordinria";"297";"Eleies Gerais Estaduais 2018";"07/10/2018";"1";"Final";"19/11/2018";"420248423";"RO";"Nota Fiscal";"850033";"2";"Fundo Especial de Financiamento de Campanha";"20100000";"Combustveis e lubrificantes";"1";"Financeiro";"0";"Cheque";"24008896";"16157885";"14/09/2018";"GASOLINA TIPO "C" ONU 1203 CL 3 EMB II";"1452,00"
    """.strip()
    expected = """
    "09/04/2023";"10:01:10";"2018";"2";"Ordinria";"297";"Eleies Gerais Estaduais 2018";"07/10/2018";"1";"Final";"19/11/2018";"420248423";"RO";"Nota Fiscal";"850033";"2";"Fundo Especial de Financiamento de Campanha";"20100000";"Combustveis e lubrificantes";"1";"Financeiro";"0";"Cheque";"24008896";"16157885";"14/09/2018";"GASOLINA TIPO ""C"" ONU 1203 CL 3 EMB II";"1452,00"
    """.strip()
    assert fix_line(line + "\n") == expected + "\n"


def test_fix_line_2():
    line = """
    "09/12/2020";"10.000 SANTINHOS VEREADOR ELIETE DE RUI";";"160,00"
    """.strip()
    expected = '''
    "09/12/2020";"10.000 SANTINHOS VEREADOR ELIETE DE RUI""";"160,00"
    '''.strip()
    assert fix_line(line + "\n") == expected + "\n"


def test_fix_line_3():
    line = """
    "12/11/2020";""TSERVIÇO DE CABO ELEITORAL";"250,00"
    """.strip()
    expected = '''
    "12/11/2020";"""TSERVIÇO DE CABO ELEITORAL";"250,00"
    '''.strip()
    assert fix_line(line + "\n") == expected + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-encoding", "-e", default="utf-8")
    parser.add_argument("--output-encoding", "-E", default="utf-8")
    parser.add_argument("input_filename")
    parser.add_argument("output_filename")
    args = parser.parse_args()

    input_filename = args.input_filename
    input_encoding = args.input_encoding
    if input_filename == "-":
        input_fobj = io.TextIOWrapper(sys.stdin.buffer, encoding=input_encoding)
    else:
        input_fobj = open(input_filename, encoding=input_encoding)
    output_filename = args.output_filename
    output_encoding = args.output_encoding
    if output_filename == "-":
        output_fobj = io.TextIOWrapper(sys.stdout.buffer, encoding=output_encoding)
    else:
        output_fobj = open(output_filename, encoding=output_encoding, mode="w")
    input_filename_str = "stdin" if input_filename == "-" else Path(input_filename).name
    output_filename_str = "stdout" if output_filename == "-" else Path(output_filename).name
    progress = tqdm(
        desc=f"Fixing quotes: {input_filename_str} -> {output_filename_str}", unit_scale=True, dynamic_ncols=True
    )
    while True:
        text = input_fobj.readline()
        if not text:
            break
        progress.update()
        output_fobj.write(fix_line(text))
    input_fobj.close()
    output_fobj.close()
    progress.close()
