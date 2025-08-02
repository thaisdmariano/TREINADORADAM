import streamlit as st
import json
import os
import re
import readline

SUB_FILE = "adam_memoria.json"
INC_FILE = "inconsciente.json"

# ————— Helpers JSON —————
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def reindex_maes(maes_dict):
    """
    Reatribui IDs de 0..n-1 às mães,
    mantendo a ordem numérica original.
    Garante ao menos a mãe '0' existe.
    """
    items = sorted(maes_dict.items(), key=lambda x: int(x[0]))
    new_maes = {str(i): m for i, (_, m) in enumerate(items)}
    if not new_maes:
        new_maes["0"] = {"nome": "Interações", "ultimo_child": "0.0", "blocos": []}
    return new_maes

def segment_text(text):
    parts = re.split(r'(?<=[.?!])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]

def calcular_alnulu(texto):
    mapa = {
        'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7,'H':8,'I':9,
        'J':-10,'K':11,'L':12,'M':-13,'N':14,'O':15,'P':16,
        'Q':17,'R':18,'S':19,'T':20,'U':21,'V':-22,'W':23,
        'X':24,'Y':-25,'Z':26,'.':2,'!':3,'?':4,',':1,';':1,':':1,'-':1,
        '0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9
    }
    equiv = {
        'Á':'A','À':'A','Â':'A','Ã':'A','Ä':'A',
        'É':'E','Ê':'E','È':'E',
        'Í':'I','Ì':'I','Î':'I',
        'Ó':'O','Ò':'O','Ô':'O','Õ':'O','Ö':'O',
        'Ú':'U','Ù':'U','Û':'U','Ü':'U','Ç':'C','Ñ':'N'
    }
    total = 0
    for c in texto.upper():
        c = equiv.get(c, c)
        total += mapa.get(c, 0)
    return total

def get_last_index(mae):
    last = 0
    for bloco in mae["blocos"]:
        for part in ("entrada","saida"):
            tokens = bloco.get(part, {}).get("tokens", {}).get("TOTAL", [])
            for tok in tokens:
                idx = int(tok.split(".")[1])
                last = max(last, idx)
    return last

def generate_tokens(mae_id, start, e_cnt, re_cnt, ce_cnt):
    fmt = lambda i: f"{mae_id}.{i}"
    E   = [fmt(start + i) for i in range(e_cnt)]
    RE  = [fmt(start + e_cnt + i) for i in range(re_cnt)]
    CE  = [fmt(start + e_cnt + re_cnt + i) for i in range(ce_cnt)]
    TOTAL = E + RE + CE
    last_idx = start + e_cnt + re_cnt + ce_cnt - 1
    return {"E": E, "RE": RE, "CE": CE, "TOTAL": TOTAL}, last_idx

def create_entrada_block(data, mae_id, texto, re_ent, ctx_ent):
    mae     = data["maes"][mae_id]
    aln_ent = calcular_alnulu(texto)
    last0   = get_last_index(mae)

    e_cnt  = len(re.findall(r'\S+', texto))
    re_cnt = len(re.findall(r'\S+', re_ent))
    ce_cnt = len(re.findall(r'\S+', ctx_ent))

    toks, _   = generate_tokens(mae_id, last0 + 1, e_cnt, re_cnt, ce_cnt)
    fim_ent   = toks["TOTAL"][-1]

    bloco = {
        "bloco_id": len(mae["blocos"]) + 1,
        "entrada": {
            "texto": texto,
            "reacao": re_ent,
            "contexto": ctx_ent,
            "tokens": toks,
            "fim": fim_ent,
            "alnulu": aln_ent
        },
        "saida": {}
    }
    return bloco, fim_ent

def add_saida_to_block(data, mae_id, bloco, last_idx, seg, re_sai, ctx_sai):
    aln_sai = calcular_alnulu(seg)

    s_cnt  = len(re.findall(r'\S+', seg))
    rs_cnt = len(re.findall(r'\S+', re_sai))
    cs_cnt = len(re.findall(r'\S+', ctx_sai))

    toks_s, _ = generate_tokens(mae_id, last_idx + 1, s_cnt, rs_cnt, cs_cnt)
    fim_sai   = toks_s["TOTAL"][-1]

    bloco["saida"] = {
        "texto": seg,
        "reacao": re_sai,
        "contexto": ctx_sai,
        "tokens": toks_s,
        "fim": fim_sai,
        "alnulu": aln_sai
    }
    return fim_sai

# ————— App —————
st.set_page_config(page_title="Subconscious Manager")
st.title("🧠 Subconscious Manager")

# Carrega dados e garante estrutura base
subcon = load_json(SUB_FILE, {"maes": {"0": {"nome": "Interações", "ultimo_child": "0.0", "blocos": []}}})
subcon["maes"] = reindex_maes(subcon["maes"])
inconsc = load_json(INC_FILE, [])

menu = st.sidebar.radio("Navegação", [
    "Mães",
    "Inconsciente",
    "Processar Texto",
    "Blocos"
])

# --------------------------------------------------
# Aba Mães
# --------------------------------------------------
if menu == "Mães":
    st.header("Mães Cadastradas")
    for mid in sorted(subcon["maes"].keys(), key=int):
        m = subcon["maes"][mid]
        st.write(f"ID {mid}: {m['nome']} (ultimo_child={m['ultimo_child']})")

    with st.form("add_mae"):
        nome   = st.text_input("Nome da nova mãe")
        submit = st.form_submit_button("Adicionar Mãe")
    if submit and nome.strip():
        ids = list(map(int, subcon["maes"].keys()))
        novo = str(max(ids) + 1)
        subcon["maes"][novo] = {"nome": nome.strip(), "ultimo_child": "0.0", "blocos": []}
        subcon["maes"] = reindex_maes(subcon["maes"])
        save_json(SUB_FILE, subcon)
        st.success(f"Mãe '{nome}' adicionada com ID={novo}")

    with st.form("remove_mae"):
        escolha = st.selectbox(
            "Selecionar mãe para remover",
            sorted(subcon["maes"].keys(), key=int),
            format_func=lambda x: f"{x} - {subcon['maes'][x]['nome']}"
        )
        ok = st.form_submit_button("Remover Mãe")
    if ok:
        nome = subcon["maes"].pop(escolha)["nome"]
        subcon["maes"] = reindex_maes(subcon["maes"])
        save_json(SUB_FILE, subcon)
        st.success(f"Mãe '{nome}' removida")

    with st.form("edit_mae"):
        escolha_e = st.selectbox(
            "Selecionar mãe para editar",
            sorted(subcon["maes"].keys(), key=int),
            format_func=lambda x: f"{x} - {subcon['maes'][x]['nome']}"
        )
        novo_nome = st.text_input("Novo nome", subcon["maes"][escolha_e]["nome"])
        editar = st.form_submit_button("Atualizar Nome")
    if editar and novo_nome.strip():
        subcon["maes"][escolha_e]["nome"] = novo_nome.strip()
        save_json(SUB_FILE, subcon)
        st.success(f"Nome da mãe ID {escolha_e} atualizado")

# --------------------------------------------------
# Aba Inconsciente (com múltiplos arquivos .txt)
# --------------------------------------------------
elif menu == "Inconsciente":
    st.header("Inconsciente")

    st.subheader("Listar Textos")
    if inconsc:
        for i, t in enumerate(inconsc, 1):
            excerpt = t[:100] + ("..." if len(t) > 100 else "")
            st.write(f"{i}. {excerpt}")
    else:
        st.info("Nenhum texto no inconsciente.")

    st.subheader("Adicionar Texto")
    with st.form("add_texto"):
        novo      = st.text_area("Inserir novo texto", height=200)
        txt_files = st.file_uploader(
            "Ou faça upload de arquivos .txt",
            type=["txt"],
            accept_multiple_files=True
        )
        add = st.form_submit_button("Adicionar Texto")
    if add:
        if txt_files:
            for file in txt_files:
                content = file.read().decode("utf-8")
                inconsc.append(content)
            st.success(f"{len(txt_files)} texto(s) adicionado(s) ao Inconsciente")
        elif novo.strip():
            inconsc.append(novo)
            st.success("Texto adicionado ao Inconsciente")
        else:
            st.warning("Nada para adicionar.")
        save_json(INC_FILE, inconsc)

    if inconsc:
        with st.form("edit_texto"):
            idx      = st.number_input(
                "ID do texto a editar",
                min_value=1,
                max_value=len(inconsc),
                value=1
            )
            old      = inconsc[int(idx) - 1]
            upd      = st.text_area("Novo conteúdo", old, height=200)
            edit_btn = st.form_submit_button("Editar Texto")
        if edit_btn:
            inconsc[int(idx) - 1] = upd
            save_json(INC_FILE, inconsc)
            st.success(f"Texto #{idx} atualizado")

        with st.form("remove_texto"):
            rid     = st.number_input(
                "ID do texto a remover",
                min_value=1,
                max_value=len(inconsc),
                value=1
            )
            rem_btn = st.form_submit_button("Remover Texto")
        if rem_btn:
            removed = inconsc.pop(int(rid) - 1)
            save_json(INC_FILE, inconsc)
            st.success(f"Texto removido: {removed}")
    else:
        st.info("Sem textos para editar ou remover nesta seção.")

# --------------------------------------------------
# Aba Processar Texto
# --------------------------------------------------
elif menu == "Processar Texto":
    st.header("Processar Texto")

    mae_ids = sorted(subcon["maes"].keys(), key=int)
    mae_id = st.selectbox(
        "Selecionar mãe",
        mae_ids,
        format_func=lambda x: f"{x} - {subcon['maes'][x]['nome']}"
    )

    opt = ["Último salvo"] + [
        f"{i+1}. {t[:30]}{'...' if len(t) > 30 else ''}"
        for i, t in enumerate(inconsc)
    ]
    escolha = st.selectbox("Selecione texto", opt)
    if escolha == "Último salvo" and inconsc:
        texto = inconsc[-1]
    elif not escolha.startswith("Último"):
        texto = inconsc[int(escolha.split(".")[0]) - 1]
    else:
        texto = st.text_area("Digite texto para processar", "")

    if st.button("Segmentar"):
        st.session_state["sugestoes"]  = segment_text(texto)
        st.session_state["texto_base"] = texto
        st.session_state["mae_id"]     = mae_id

    if "sugestoes" in st.session_state:
        for idx, seg in enumerate(st.session_state["sugestoes"], 1):
            st.subheader(f"Trecho {idx}")
            st.write(seg)

            action = st.radio("Ação", ["Ignorar", "Entrada", "Saída"], key=f"act{idx}")

            if action == "Entrada":
                seg2   = st.text_input("Texto (entrada)", seg, key=f"inp_ent{idx}")
                re_ent = st.text_input("Reação (entrada)", "", key=f"reac_ent{idx}")
                ctx_ent= st.text_input("Contexto (entrada)", "", key=f"ctx_ent{idx}")
                if st.button("Salvar Entrada", key=f"save_ent{idx}"):
                    bloco, ultimo = create_entrada_block(
                        subcon,
                        st.session_state["mae_id"],
                        seg2,
                        re_ent,
                        ctx_ent
                    )
                    subcon["maes"][mae_id]["blocos"].append(bloco)
                    subcon["maes"][mae_id]["ultimo_child"] = ultimo
                    save_json(SUB_FILE, subcon)
                    st.success(f"Entrada do bloco #{bloco['bloco_id']} salva")

            elif action == "Saída":
                seg2   = st.text_input("Texto (saída)", seg, key=f"inp_sai{idx}")
                re_sai = st.text_input("Reação (saída)", "", key=f"reac_sai{idx}")
                ctx_sai= st.text_input("Contexto (saída)", "", key=f"ctx_sai{idx}")

                blocos    = subcon["maes"][mae_id]["blocos"]
                pendentes = [b["bloco_id"] for b in blocos if not b["saida"]]
                if pendentes:
                    alvo = st.selectbox("Bloco para completar (saída)", pendentes, key=f"target{idx}")
                    if st.button("Salvar Saída", key=f"save_sai{idx}"):
                        bloco_obj = next(b for b in blocos if b["bloco_id"] == alvo)
                        last_idx  = get_last_index(subcon["maes"][mae_id])
                        ultimo    = add_saida_to_block(
                            subcon, mae_id, bloco_obj, last_idx,
                            seg2, re_sai, ctx_sai
                        )
                        subcon["maes"][mae_id]["ultimo_child"] = ultimo
                        save_json(SUB_FILE, subcon)
                        st.success(f"Saída adicionada ao bloco #{alvo}")
                else:
                    st.warning("Não há blocos pendentes de saída.")

# --------------------------------------------------
# Aba Blocos
# --------------------------------------------------
elif menu == "Blocos":
    st.header("Gerenciar Blocos")

    mae_ids = sorted(subcon["maes"].keys(), key=int)
    mae_id = st.selectbox(
        "Escolha mãe",
        mae_ids,
        format_func=lambda x: f"{x} - {subcon['maes'][x]['nome']}"
    )
    blocos = subcon["maes"][mae_id]["blocos"]

    if not blocos:
        st.info("Nenhum bloco cadastrado.")
    else:
        for b in blocos:
            st.write(f"#{b['bloco_id']} → ENTRADA: {b['entrada']['texto']} | SAÍDA: {b['saida'].get('texto','')}")

        bid   = st.number_input("ID do bloco para editar", min_value=1, max_value=len(blocos), value=1)
        campo = st.radio("Campo", ["entrada.texto","entrada.reacao","entrada.contexto","saida.texto"], index=0)
        novo  = st.text_input("Novo valor")
        if st.button("Atualizar Bloco"):
            part, key = campo.split(".")
            subcon["maes"][mae_id]["blocos"][bid-1][part][key] = novo
            save_json(SUB_FILE, subcon)
            st.success("Bloco atualizado")

        rem = st.number_input("ID do bloco para remover", min_value=1, max_value=len(blocos), value=1, key="rem")
        if st.button("Remover Bloco"):
            subcon["maes"][mae_id]["blocos"].pop(rem-1)
            for i, b in enumerate(subcon["maes"][mae_id]["blocos"], 1):
                b["bloco_id"] = i
            save_json(SUB_FILE, subcon)
            st.success(f"Bloco #{rem} removido")

        seq = st.text_input("Intervalo p/ remover (ex: 2-5)")
        if st.button("Remover Sequência"):
            m = re.match(r"(\d+)-(\d+)", seq)
            if m:
                start, end = map(int, m.groups())
                subcon["maes"][mae_id]["blocos"] = [
                    b for b in subcon["maes"][mae_id]["blocos"]
                    if not (start <= b["bloco_id"] <= end)
                ]
                for i, b in enumerate(subcon["maes"][mae_id]["blocos"], 1):
                    b["bloco_id"] = i
                save_json(SUB_FILE, subcon)
                st.success(f"Blocos {start} a {end} removidos")
            else:
                st.error("Formato inválido")

st.sidebar.markdown("---")
st.sidebar.write("❤️ Desenvolvido com Streamlit")

# --------------------------------------------------
# Persistir JSONs a cada rerun
save_json(SUB_FILE,  subcon)
save_json(INC_FILE, inconsc)
