"""All ads below are synthetic: names, phones, e-mails and companies are made up."""

import pytest

from detector_golpe.rules import analyze, batch_pairs, check, decide, job_from_dict

SCAM = ("Parabéns, você foi aprovada sem entrevista. Curso obrigatório com reembolso via PIX em 40 minutos. "
        "Envie RG e CPF para selecao.exemplo@hotmail.com e responda pelo Telegram.")
CLEAN = ("Projetista de armação de estruturas de concreto, atuação remota, PJ. Experiência com detalhamento 2D, "
         "normas ABNT, AutoCAD e Revit; TQS e Eberick são diferenciais. Projetos de terminais portuários. ") * 3
BASIC = "Escolaridade mínima: Ensino Médio. Home office. "


def codes(text):
    return {k for k, _ in check(text)}


def verdict(text):
    return decide(check(text))


def test_obvious_scam_and_clean_ad():
    assert {"G1", "G2", "G3", "G4"} <= codes(SCAM)
    assert verdict(SCAM) == "SUSPEITA"
    assert check(CLEAN) == []
    assert verdict(CLEAN) == "ok"


def test_decide_thresholds():
    assert decide([]) == "ok"
    assert decide([("A4", "")]) == "ALERTA"
    assert decide([("A1", ""), ("A4", "")]) == "SUSPEITA"
    assert decide([("G1", ""), ("C", "")]) == "CONFIDENCIAL"


@pytest.mark.parametrize("text", [
    "Chamar no Whatsapp: 1.1.9.0.0.0.0.0.0.0.0. ",
    "Dúvidas WhatsApp: (84)90000-0000 ",
    "Para o curso, acesse o link do Telegram. ",
    "Envie o seu currículo no whatsapp do time da seleção +55 11 4000-0000. ",
])
def test_whatsapp_or_telegram_as_hiring_contact(text):
    assert "G2" in codes(text + CLEAN)


@pytest.mark.parametrize("text", [
    "Atendimento aos clientes pelo WhatsApp e plataforma/app; contatos por telefone, WhatsApp e e-mail. ",
    "Facilidade com WhatsApp, Telegram, planilhas e sistemas. ",
    "https://www.exemplo.com.br/vaga-de-atendente-whatsapp-em-sao-paulo__10000000.aspx ",
    "O(a) colaborador(a) atuará com o(a) gestor(a) da área. ",
    "Envie dúvidas para contato@vagas.exemplo.com.br. ",
])
def test_whatsapp_as_work_tool_is_not_a_signal(text):
    assert check(text + CLEAN) == []


def test_disguised_free_mailbox():
    text = "Envie seu currículo atualizado para o nosso e-mail: lojaexemplo(a )hotma il.c om. " + CLEAN
    assert {"G2", "A5"} <= codes(text)
    assert verdict(text) == "SUSPEITA"


def test_resume_to_phone_number():
    assert "A5" in codes("Envie seu currículo em PDF para a recrutadora 11 990000000. " + CLEAN)
    assert "A5" not in codes("Envie seu currículo pela plataforma. Salário R$ 2.500,00 e 2 vagas. " + CLEAN)


def test_unfilled_template():
    assert "A6" in codes("Local: [cidade/obra] Salário: [informar] " + CLEAN)
    assert "A6" in codes("Record all assumptions. Page 1 EXEMPLO CONSTRUTORA EXC-SOP-001 v1.0 Prepare labor. " + CLEAN)


def test_confidential_with_urgent_hiring():
    block = ("Empresa | confidencial | CONTRATAÇÃO URGENTE | Salário: 2.300,00 Tipo de contratação: CLT "
             "Jornada: 8h às 17h Modalidade: 100% Home Office ")
    assert "A1" in codes(block)


def test_high_pay_for_basic_level():
    assert "A3" in codes(BASIC + "R$ 3.800,00 a R$ 4.500,00 " + CLEAN)
    assert "A3" in codes("Ensino fundamental completo. Home office. R$ 3.200,00 " + CLEAN)
    assert "A3" not in codes(BASIC + "R$ 100,00 a R$ 4.000,00 " + CLEAN)  # wide range: the floor counts
    assert "A3" not in codes(BASIC + "R$ 203.157,00 " + CLEAN)  # typo for R$ 2.031,57
    assert "A3" not in codes(BASIC + "R$ 4.200,00 a R$ 4.800,00 Experiência desejada: Entre 3 e 5 anos " + CLEAN)
    assert "A3" not in codes("Ensino médio completo. Home office. Salário: R$ 5.000,00. Japonês avançado; "
                             "Experiência de 1 ano em Contact Center. " + CLEAN)


def test_removed_ad_page_is_not_short_description():
    assert check("Esta vaga não está mais disponível") == []
    assert check("Ops! Esta vaga não está mais disponível. Vagas publicadas recentemente | Analista | Empresa | "
                 "confidencial | Home office") == []


@pytest.mark.parametrize("text", [
    "Empresa | confidencial | ",
    "Vagas Confidenciais ",
    "Empresa: Confidencial ",
    "Empresa: Confidential Company ",
    "Analista de Sistemas Jr Confidencial Júnior/ Trainee Analista de Sistemas Jr ",
    "A agência em parceria com empresa consolidada seleciona ANALISTA. ",
    "Técnico de Automação. Em parceria com uma multinacional, buscamos técnico. ",
    "Estamos auxiliando nosso cliente a encontrar uma pessoa Analista de Dados. ",
    "Processo seletivo para nosso cliente parceiro. ",
    "Nosso Cliente Escritório de advocacia empresarial busca Advogado. ",
    "Nosso cliente, localizado na cidade de Exemplo/SC, está em busca de assistente. ",
    "Nosso Cliente é uma empresa que atua no mercado de produtos digitais. ",
    "Selecionando um profissional para atuar nas rotinas de DP de uma empresa cliente. ",
    "Empresa: Cliente Analista de Suporte N1/N2 ",
    "Tenho uma oportunidade para Engenheiro de Obras (PJ) em empresa do segmento de HVAC. ",
    "Sobre a Empresa: Atuação em uma loja do segmento de açaí, localizada no centro. ",
    "A consultoria seleciona para empresa de grande porte do segmento industrial. ",
    "A consultoria está assessorando uma empresa nacional na busca de engenheiro. ",
    "A empresa contratante atua no segmento de varejo. ",
])
def test_hiring_company_not_identified(text):
    assert verdict(text + CLEAN) == "CONFIDENCIAL"


@pytest.mark.parametrize("text", [
    "Tratamos seus dados de forma confidencial. ",
    "Tratamos seus dados de forma confidencial, técnico. ",
    "Handle confidential information with care. ",
    "Dúvidas, entre em contato pelo (Informação Confidencial). ",
    "Atendimento ao cliente e suporte. ",
    "Resolver chamados e dar retorno para o cliente. ",
    "Queremos entregar a melhor experiência ao nosso cliente, hoje somos uma das maiores empresas do Nordeste. ",
    "Além de ser nosso cliente, você tem a chance de fazer parte do time. ",
    "Saber ouvir o cliente final (nosso cliente ou time de ops). ",
    "Nosso cliente é a nossa prioridade. ",
    "Experiência em empresas do segmento de construção civil e como gerente de loja no ramo de alimentos. ",
    "Os prestadores de serviço devem observar o horário de funcionamento do prédio da contratante. ",
    "EXEMPLOTEC PJ/FREELANCER - TEMPORÁRIO. Valor: R$ 2600,00. Cliente:* Confidencial. ",
])
def test_ordinary_wording_is_not_a_hidden_company(text):
    assert verdict(text + CLEAN) == "ok"


def test_batch_same_text_different_titles():
    assert batch_pairs([("1", "Auxiliar Administrativo", CLEAN), ("2", "Assistente Financeiro", CLEAN + " x"),
                        ("3", "Vendas", SCAM)]) == {("1", "2")}


def test_batch_same_role_is_not_a_pair():
    assert batch_pairs([("1", "Projetista (SP)", CLEAN), ("2", "Projetista (RJ)", CLEAN)]) == set()
    assert batch_pairs([("1", "Orçamentista - Inglês Necessário", CLEAN), ("2", "Orçamentista Inglês Necessário", CLEAN)]) == set()
    assert batch_pairs([("1", "Gerente de Restaurante | Shopping Norte", CLEAN),
                        ("2", "Gerente de Restaurante | Shopping Sul - Natal/RN", CLEAN)]) == set()
    assert batch_pairs([("1", "Analista de Engenharia Residencial Aurora", CLEAN), ("2", "Analista de Engenharia Residencial Brisa", CLEAN),
                        ("3", "Auxiliar de laboratorio", CLEAN), ("4", "Pessoa Auxiliar de Laboratório", CLEAN)]) == {
        ("1", "3"), ("1", "4"), ("2", "3"), ("2", "4")}


def test_batch_confidential_template():
    block = ("Empresa | confidencial | CONTRATAÇÃO URGENTE | Salário: 2.300,00 Tipo de contratação: CLT "
             "Jornada: 8h às 17h Modalidade: 100% Home Office ")
    assert batch_pairs([("1", "Auxiliar Administrativo", block + "arquivo"), ("2", "Auxiliar Financeiro", block + "contas")]) == {("1", "2")}


def test_batch_remote_hours_template():
    hours = "Jornada: Segunda a sexta-feira, das 08h às 17h, com 1 hora de intervalo. Home office. "
    assert batch_pairs([("1", "Auxiliar Administrativo", hours + CLEAN),
                        ("2", "Assistente Comercial", hours + "Vendas. " + CLEAN[:200])]) == {("1", "2")}
    onsite = hours.replace("Home office", "Presencial")
    assert batch_pairs([("1", "Auxiliar Administrativo", onsite + CLEAN),
                        ("2", "Assistente Comercial", onsite + "Vendas internas, prospecção e atendimento a clientes "
                                                               "por telefone e e-mail. " * 3)]) == set()


def test_batch_dates():
    # same text on different dates = company boilerplate; same date = batch
    assert batch_pairs([("1", "Analista de Automação", "Local: · remoto · 2026-08-26 " + CLEAN),
                        ("2", "Analista de IA e Analytics", "Local: · remoto · 2026-09-18 " + CLEAN)]) == set()
    assert batch_pairs([("1", "Analista de Sistemas", "Publicada em 19/10/2026. " + CLEAN),
                        ("2", "Desenvolvedor de Sistemas", "Local: · remoto · 2026-10-19 " + CLEAN)]) == {("1", "2")}


def test_batch_ignores_removed_ad_pages():
    gone = "Ops! Esta vaga não está mais disponível. Vagas publicadas recentemente para você se candidatar hoje mesmo. "
    assert not batch_pairs([("a", "Analista Fiscal", "a " + gone), ("b", "Assistente Financeiro", "b " + gone)])


def test_analyze_adds_batch_signal_and_meanings():
    res = analyze([("1", "Auxiliar Administrativo", CLEAN), ("2", "Assistente Financeiro", CLEAN + " x")])
    assert [r["verdict"] for r in res] == ["ALERTA", "ALERTA"]
    assert res[0]["signals"][0] == {"code": "A2", "match": "texto igual a 2",
                                    "meaning": "texto igual ao de outra vaga com cargo diferente"}


def test_job_from_dict_reads_gupy_fields():
    i, title, text = job_from_dict({"id": 42, "name": "Dev Python", "careerPageName": "Exemplo SA",
                                    "description": "Vaga remota. Vagas similares: outra coisa"})
    assert (i, title) == ("42", "Dev Python")
    assert text.startswith("Empresa: Exemplo SA ") and "outra coisa" not in text
