"""Rule-based scam detector for Brazilian job ads.

Each rule is a regex over the ad text. Codes:
  G* = strong scam signal, A* = warning, C = hiring company not identified.
The verdict is CONFIDENCIAL, SUSPEITA, ALERTA or ok (see `decide`).
Rules only point at evidence; a person still reads the ad before discarding it.
"""

import re
import unicodedata
from itertools import combinations

SIGNALS = [
    ("G1", (r"curso obrigat[óo]rio|taxa de (inscri|cadastro|admiss|matr[íi]cula|ades)|reembolso (via |por )?pix|"
            r"(pagar|pagamento|investimento|valor) (de |do |pelo |para o )?(curso|treinamento|certificad|kit|uniforme|exame)|"
            r"(curso|treinamento|kit|uniforme|exame)s? pagos?")),
    # WhatsApp/Telegram only count as the hiring contact ("chame no WhatsApp", a phone number right after);
    # "atendimento aos clientes pelo WhatsApp" is a work channel, not a red flag
    ("G2", (r"[\w.+-]+@(gmail|hotmail|outlook|yahoo|bol|uol|live|icloud)\.com(\.br)?|wa\.me/|t\.me/|"
            r"\((a|at|arroba)\s?\)\s?(hot\s?ma|g\s?ma\s?i|out\s?look|yah|bol\b|uol\b)|"  # disguised e-mail: "name(a )hotma il.c om"
            r"\b(cham\w*|envie|enviar|mande|mandar|fale|falar|responda|contato|d[úu]vidas|ligue|acesse|link|grupo)\s*"
            r"(:|no|pelo|via|por|ao|com|do)?\s*(whats ?app|telegram)|"
            r"whats ?app[^.\d_]{0,40}?\+?\(?\d[\d\s().-]{7,}")),  # "_" stops at the id at the end of job-board URLs
    ("G3", r"(envi\w+|mand\w+|encaminh\w+|anex\w+)[^.]{0,60}\b(rg|cpf|ctps|pis|dados banc[áa]rios|chave pix|foto (do|de) documento)\b"),
    ("G4", r"sem (necessidade de )?entrevista|aprovad[oa] sem|j[áa] (est[áa]|foi) aprovad|aprova[çc][ãa]o (imediata|garantida)"),
    ("A5", (r"(envi\w+|mand\w+|encaminh\w+) (o |seu )?(curr[íi]culo|cv)( \w+)? (para|no|pelo|via) (o )?(nosso )?(e-?mail|whats)|"
            r"(envi\w+|mand\w+|encaminh\w+) (o |seu )?(curr[íi]culo|cv)[^.]{0,40}?\(?\d{2}\)?\s?9?\d{4}[\s-]?\d{4}|"  # resume to a phone number
            r"bit\.ly|forms\.gle|docs\.google\.com/forms|linktr\.ee")),
    ("A6", (r"\(informe aqui|\[inserir|\[nome da empresa|\[(cidade|informar|local|obra|sal[áa]rio)[^\]]{0,15}\]|lorem ipsum|preencher aqui|xxxx|"
            r"\b(page|p[áa]gina) \d+ [^.]{0,60}\bv\d+\.\d+\b")),  # pasted internal document footer ("Page 1 ... SOP-001 v1.0")
]

# Plain-language meaning of each code, shown by the CLI, the API and the web page
SIGNAL_INFO = {
    "G1": "cobra curso, taxa, kit ou exame",
    "G2": "contato por e-mail gratuito, WhatsApp ou Telegram",
    "G3": "pede documentos ou dados bancários antes da contratação",
    "G4": "promete aprovação sem entrevista",
    "A1": "empresa confidencial com contratação urgente",
    "A2": "texto igual ao de outra vaga com cargo diferente",
    "A3": "salário alto para nível baixo",
    "A4": "descrição curta demais",
    "A5": "currículo por e-mail, WhatsApp, telefone ou link encurtado",
    "A6": "modelo de anúncio não preenchido",
    "C": "empresa contratante não identificada",
}

EXPERIENCE = (r"experi[êe]ncia desejada: (entre [1-9]|mais de)|experi[êe]ncia (m[íi]nima |comprovada |pr[ée]via )?de [1-9]\d? anos?\b|"
              r"\b[1-9]\d? anos? de experi[êe]ncia|\b(japon[êe]s|ingl[êe]s|espanhol|alem[ãa]o|franc[êe]s|mandarim) (avan[çc]ado|fluente|nativo)")


def high_pay_low_level(t):
    """A3: basic schooling + remote + pay above R$ 3,000.
    For a range ("R$ 100,00 a R$ 4.000,00") the floor counts, not the ceiling.
    Ads that ask for years of experience or an advanced language are skipped."""
    if re.search(EXPERIENCE, t, re.IGNORECASE):
        return False
    vals = [float(v.replace(".", "").replace(",", ".")) for v in re.findall(r"R\$\s?([\d.]+,\d{2})(?:\s*a\s*R\$\s?[\d.]+,\d{2})?", t)]
    vals = [v for v in vals if v <= 50000]  # "R$ 203.157,00" is a typo for R$ 2.031,57
    return (bool(vals) and max(vals) > 3000
            and re.search(r"escolaridade m[íi]nima: ensino (fundamental|m[ée]dio)|ensino (fundamental|m[ée]dio) complet", t, re.IGNORECASE)
            and re.search(r"home ?office|remot", t, re.IGNORECASE))


CUT = r"Denunciar vaga|Vagas similares|Vagas semelhantes|Outras vagas|Vagas publicadas recentemente"  # rest of the page lists other ads
TEMPLATE = r"sal[áa]rio: .{0,60}tipo de contrata[çc][ãa]o: .{0,60}jornada: "
TEMPLATE2 = r"jornada: segunda a sexta-feira, das 0?8h [àa]s 17h,? com 1 hora de intervalo"
STOPWORDS = {"de", "da", "do", "das", "dos", "e", "em", "para", "com", "a", "o", "pessoa", "vaga"}
OFFLINE = r"indispon[íi]vel|n[ãa]o est[áa] mais dispon[íi]vel|sem dados:"  # "ad removed" page: short text is not A4
# company described only by its industry, or a recruiter speaking for a hidden client
HIDDEN = (r"\b(empresa|ind[úu]stria|rede|loja)( de (grande|m[ée]dio|pequeno) porte)? (do|de) (segmento|ramo|setor)\b|\bempresa no ramo\b|"
          r"assessorando uma empresa|contratante atua no (segmento|ramo|setor)")


def flat(t):
    """Collapse whitespace and the " | " separators saved pages use between fields."""
    return re.sub(r"[\s|]+", " ", t)


def title_words(title):
    """Words of the job title up to the first " - " or " | ", without accents or stopwords."""
    c = unicodedata.normalize("NFKD", re.split(r"\s[-–|]\s", title)[0].lower()).encode("ascii", "ignore").decode()
    return [w for w in re.sub(r"\(.*?\)|https?://\S*?/vaga-de-|__\d+\.aspx|[^\w ]", " ", c).split() if w not in STOPWORDS]


def check(text):
    """Signals found in one ad, as (code, matched text or note)."""
    t = flat(re.split(CUT, text)[0])
    s = [(k, m.group(0)[:60]) for k, p in SIGNALS for m in [re.search(p, t, re.IGNORECASE)] if m]
    if re.search("empresa confidencial", t, re.IGNORECASE) and re.search(r"contrata[çc][ãa]o urgente", t, re.IGNORECASE):
        s.append(("A1", "Empresa confidencial + CONTRATAÇÃO URGENTE"))
    if high_pay_low_level(t):
        s.append(("A3", "salário > R$ 3.000, ensino médio, remoto"))
    if len(re.sub(r"\s+", " ", t)) < 400 and not re.search(OFFLINE, t, re.IGNORECASE):
        s.append(("A4", "descrição curta"))
    if re.search(r"empresa:? confidencial|vagas confidenciais|confidential company|empresa:? confidential\b|"
                 r"\bconfidencial (j[úu]nior|pleno|s[êe]nior|trainee|auxiliar|operacional|t[ée]cnico|est[áa]gio|supervis|ger[êe]ncia|especialista)",
                 t, re.IGNORECASE):
        s.append(("C", "empresa confidencial: confirme a vaga no site oficial da empresa"))
    elif re.search(r"empresa parceira|em parceria com (uma )?(empresa|multinacional)|(para|auxiliando|assessorando|representando) (o )?nosso cliente\b|"
                   r"\b(de|para|em) uma empresa cliente\b|empresa: cliente\b|"
                   r"\bnosso cliente,? (é )?(localizad|uma?\b|empresa|escrit[óo]rio|ind[úu]stria|atua|busca|procura|est[áa] (em busca|contratando|selecionando))",
                   t, re.IGNORECASE):  # "para o cliente" and "ao nosso cliente" are customer service, not a recruiter
        s.append(("C", "consultoria sem nomear a contratante: confirme no site oficial"))
    elif re.search(HIDDEN, t, re.IGNORECASE):
        s.append(("C", "empresa descrita só pelo ramo: confirme a contratante no site oficial"))
    return s


def decide(signals):
    """CONFIDENCIAL first: without an official page confirming the ad, it is dropped.
    Any G signal or two A signals = SUSPEITA; one A = ALERTA."""
    g, a, c = (sum(k[0] == x for k, _ in signals) for x in "GAC")
    return "CONFIDENCIAL" if c else "SUSPEITA" if g or a >= 2 else "ALERTA" if a else "ok"


def pub_date(t):
    """Publication date near the start of the ad, as yyyy-mm-dd, or None."""
    m = re.search(r"\b(20\d\d)-(\d\d)-(\d\d)\b|\b(\d\d)/(\d\d)/(20\d\d)\b", t[:300])
    return m and (f"{m[1]}-{m[2]}-{m[3]}" if m[1] else f"{m[6]}-{m[5]}-{m[4]}")


def batch_pairs(jobs):
    """A2: pairs of ads with different titles and near-identical text (word 5-grams, Jaccard > 0.6),
    or "empresa confidencial" ads sharing the same Salary / Contract / Hours block.
    Same title = the same ad posted twice. Same text on different dates = the company's boilerplate.
    `jobs` is a list of (id, title, text)."""
    jobs = [j for j in jobs if not (len(flat(j[2])) < 800 and re.search(OFFLINE, j[2], re.IGNORECASE))]  # every "ad removed" page looks alike
    sh = {i: {tuple(w[k:k + 5]) for k in range(len(w) - 4)} for i, _, t in jobs for w in [re.findall(r"\w+", t.lower())]}
    words = {i: title_words(c) for i, c, _ in jobs}
    day = {i: pub_date(t) for i, _, t in jobs}
    template = {i for i, _, t in jobs for p in [flat(t)]
                if (re.search(TEMPLATE, p, re.IGNORECASE) and re.search("empresa confidencial", p, re.IGNORECASE))
                or (re.search(TEMPLATE2, p, re.IGNORECASE) and re.search(r"home ?office|remot", p, re.IGNORECASE))}

    def same_text(x, y):
        return (sh[x] and sh[y] and len(sh[x] & sh[y]) / len(sh[x] | sh[y]) > 0.6
                and not (day[x] and day[y] and day[x] != day[y]))

    def same_role(x, y):  # same ad on another board, or the same role at another branch
        return set(words[x]) <= set(words[y]) or set(words[y]) <= set(words[x]) or words[x][:2] == words[y][:2]

    # ponytail: O(n²) pairs, fine for a daily batch of a few hundred ads
    return {(x, y) for x, y in combinations(sh, 2)
            if ({x, y} <= template and words[x] != words[y]) or (same_text(x, y) and not same_role(x, y))}


def job_from_dict(o):
    """(id, title, text) from a job dict; every string field joins the text (works with Gupy API items)."""
    company = o.get("company") or o.get("careerPageName") or o.get("org") or ""
    text = f"Empresa: {company} " + " ".join(re.split(CUT, v)[0] for v in o.values() if isinstance(v, str))
    return str(o.get("id") or o.get("url")), str(o.get("title") or o.get("name") or ""), text


def analyze(jobs):
    """Verdict and signals for each (id, title, text), including A2 across the whole batch."""
    pairs = batch_pairs(jobs)
    out = []
    for i, title, t in jobs:
        s = check(t) + [("A2", f"texto igual a {y if x == i else x}") for x, y in sorted(pairs) if i in (x, y)][:1]
        out.append({"id": i, "title": title, "verdict": decide(s),
                    "signals": [{"code": k, "match": m, "meaning": SIGNAL_INFO[k]} for k, m in s]})
    return out
