"""Web page: paste one job ad and see which scam signals it shows."""

import streamlit as st

from detector_golpe.rules import analyze

EXAMPLES = {
    "Golpe típico": (
        "Parabéns, você foi aprovada sem entrevista para Auxiliar Administrativo home office. "
        "Para começar, faça o curso obrigatório de integração (R$ 49,90, com reembolso via PIX no primeiro salário). "
        "Envie RG, CPF e foto do documento para selecao.exemplo@hotmail.com e chame no WhatsApp (84) 90000-0000."
    ),
    "Vaga normal": (
        "Desenvolvedor Python Júnior na Exemplo Tecnologia, 100% remoto, CLT. "
        "Você vai manter APIs em FastAPI, escrever testes com pytest e automatizar rotinas internas. "
        "Requisitos: Python, Git, SQL básico e vontade de aprender. Diferenciais: Docker e experiência com APIs REST. "
        "Benefícios: vale-refeição, plano de saúde, auxílio home office e horário flexível. "
        "Etapas: inscrição pela página de carreiras da empresa, teste técnico on-line, entrevista com o time e proposta."
    ),
}

VERDICTS = {
    "SUSPEITA": (st.error, "Suspeita de golpe", "Tem pelo menos um sinal forte (G) ou dois alertas (A). Não envie dinheiro nem documentos."),
    "CONFIDENCIAL": (st.warning, "Empresa não identificada", "Confirme a vaga no site oficial da empresa antes de se candidatar."),
    "ALERTA": (st.warning, "Atenção", "Há um sinal de alerta. Leia o anúncio com cuidado."),
    "ok": (st.success, "Nenhum sinal encontrado", "Isso não garante que a vaga é real: confira a empresa mesmo assim."),
}

st.set_page_config(page_title="Detector de golpe em vagas", page_icon=":material/shield:")
st.title("Detector de golpe em vagas")
st.caption("Cole o texto de um anúncio de emprego. As regras apontam sinais comuns de golpe; quem decide é você.")

example = st.segmented_control("Carregar exemplo", list(EXAMPLES))
text = st.text_area("Texto do anúncio", value=EXAMPLES.get(example, ""), height=220, key=f"ad_{example}",
                    placeholder="Cole aqui a descrição completa da vaga")

if text.strip():
    result = analyze([("vaga", "", text)])[0]
    show, title, body = VERDICTS[result["verdict"]]
    show(body, title=title)
    for s in result["signals"]:
        st.markdown(f"**{s['code']}** · {s['meaning']}  \n:gray[detalhe:] `{s['match']}`")  # code span: no autolink

st.divider()
st.caption("Regras abertas, sem IA: [código no GitHub](https://github.com/ibsondiniz/detector-golpe-vagas). "
           "A comparação entre vagas (A2) funciona na API e na linha de comando, que analisam várias vagas de uma vez.")
