# -*- coding: utf-8 -*-
# Adam – CLI Multiversal com Estética Cósmica 🌌

import os
import json
import re
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

ARQUIVO_MEMORIA = "adam_memoria.json"
CKPT            = "insepa_xy.pt"

# ────────────────────────────────────────────────────────────────────────────────
# Mensagens e prompts cósmicos
# ────────────────────────────────────────────────────────────────────────────────
def mensagem_cosmica():
    print("❌ Não encontrei correspondências com este universo. Tente outro!")
    print()
    print("Por hoje é só.")
    print("✨ Mas não desanime: como o cosmos, estamos sempre em expansão!")
    print()

def entrada_usuario(modo="default"):
    if modo == "inicial":
        return input("👤 Digite sua mensagem com emoji:\n ")
    elif modo == "playlist":
        return input("Digite Enter ou uma Nova Mensagem com emoji ")
    else:
        return input("💬 Digite sua mensagem e emoji\n↳ ")

# ────────────────────────────────────────────────────────────────────────────────
# Utilitários de tokenização e parsing
# ────────────────────────────────────────────────────────────────────────────────
def garantir_pontuacao(txt: str) -> str:
    txt = txt.strip()
    return txt if txt and txt[-1] in ".!?" else (txt + "." if txt else txt)

def tokenizar(txt: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", txt, re.UNICODE)

def parse_text_reaction(raw: str, blocos: list[dict]) -> tuple[str, str]:
    s = raw.strip()
    reactions = sorted(
        {b["entrada"]["reacao"] for b in blocos if b.get("entrada", {}).get("reacao")},
        key=len, reverse=True
    )
    for rea in reactions:
        if s.endswith(rea):
            txt = s[:-len(rea)].rstrip()
            return garantir_pontuacao(txt), rea
    return garantir_pontuacao(s), ""

def _saida_tokens_legacy_or_insepa(saida: dict) -> tuple[list[str], list[str], list[str]]:
    t = saida.get("tokens", {})
    if "S" in t or "RS" in t or "CS" in t:
        S  = t.get("S", [])
        RS = t.get("RS", [])
        CS = t.get("CS", [])
    else:
        S  = t.get("E", [])
        RS = t.get("RE", [])
        CS = t.get("CE", [])
    return S, RS, CS

def xy_from_block_many(b: dict) -> list[tuple[list[float], list[float]]]:
    Ein  = [float(v) for v in b["entrada"]["tokens"].get("E", [])]
    REin = [float(v) for v in b["entrada"]["tokens"].get("RE", [])]
    CEin = [float(v) for v in b["entrada"]["tokens"].get("CE", [])]
    X    = Ein + REin + CEin

    pares = []
    if "saidas" in b and b["saidas"]:
        for saida in b["saidas"]:
            S, RS, CS = _saida_tokens_legacy_or_insepa(saida)
            Y = [float(v) for v in (S + RS + CS)]
            pares.append((X, Y))
    elif "saida" in b and b["saida"]:
        S, RS, CS = _saida_tokens_legacy_or_insepa(b["saida"])
        Y = [float(v) for v in (S + RS + CS)]
        pares.append((X, Y))
    return pares

# ────────────────────────────────────────────────────────────────────────────────
# Dataset e modelo
# ────────────────────────────────────────────────────────────────────────────────
class InsepaXY(Dataset):
    def __init__(self, memoria: dict, dominio: str):
        blocos = memoria["maes"][dominio]["blocos"]
        self.pares = []
        for b in blocos:
            self.pares.extend(xy_from_block_many(b))
        if not self.pares:
            raise ValueError("Nenhum par (X,Y) encontrado. Verifique se há saídas nos blocos.")
        self.max_x = max(len(x) for x, _ in self.pares)
        self.max_y = max(len(y) for _, y in self.pares)

    def __len__(self) -> int:
        return len(self.pares)

    def __getitem__(self, idx: int):
        x, y = self.pares[idx]
        x_pad = x + [0.0] * (self.max_x - len(x))
        y_pad = y + [0.0] * (self.max_y - len(y))
        return torch.tensor(x_pad, dtype=torch.float32), torch.tensor(y_pad, dtype=torch.float32)

class InsepaReg(nn.Module):
    def __init__(self, xin: int, yout: int, hidden: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(xin, hidden),
            nn.ReLU(),
            nn.Linear(hidden, yout)
        )
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

# ────────────────────────────────────────────────────────────────────────────────
# Treino
# ────────────────────────────────────────────────────────────────────────────────
def train(memoria: dict, dominio: str) -> None:
    torch.manual_seed(42)
    ds     = InsepaXY(memoria, dominio)
    loader = DataLoader(ds, batch_size=2, shuffle=True)
    model  = InsepaReg(ds.max_x, ds.max_y)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn   = nn.MSELoss()

    print(f"🚀 Treinando domínio {dominio} ({len(ds)} pares X→Y)...")
    epochs = 100
    for ep in range(1, epochs + 1):
        total_loss = 0.0
        model.train()
        for X, Y in loader:
            optimizer.zero_grad()
            pred = model(X)
            loss = loss_fn(pred, Y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if ep == 1 or ep % 10 == 0 or ep == epochs:
            avg = total_loss / max(1, len(loader))
            print(f" Ep {ep:03d}/{epochs}  loss={avg:.4f}")

    torch.save((model.state_dict(), ds.max_x, ds.max_y), CKPT)
    print(f"✅ Treino concluído. Checkpoint salvo em '{CKPT}'\n")

# ────────────────────────────────────────────────────────────────────────────────
# Inferência (playlist interativa com escadinha de blocos)
# ────────────────────────────────────────────────────────────────────────────────
def _montar_X_do_bloco(b: dict) -> list[float]:
    Ein  = [float(v) for v in b["entrada"]["tokens"].get("E", [])]
    REin = [float(v) for v in b["entrada"]["tokens"].get("RE", [])]
    CEin = [float(v) for v in b["entrada"]["tokens"].get("CE", [])]
    return Ein + REin + CEin

def _montar_Y_da_saida(saida: dict) -> list[float]:
    S, RS, CS = _saida_tokens_legacy_or_insepa(saida)
    return [float(v) for v in (S + RS + CS)]

def _escolher_saida_por_modelo(model, max_x, max_y, bloco) -> dict:
    X = _montar_X_do_bloco(bloco)
    X_pad = X + [0.0] * (max_x - len(X))
    with torch.no_grad():
        y_hat = model(torch.tensor([X_pad], dtype=torch.float32))[0].numpy()

    saidas = bloco.get("saidas") or ([bloco["saida"]] if "saida" in bloco else [])
    if not saidas:
        return None

    melhor, best_idx = float("inf"), None
    for i, s in enumerate(saidas):
        Y = _montar_Y_da_saida(s)
        Y_pad = Y + [0.0] * (max_y - len(Y))
        dist = sum((float(yh) - float(yr)) ** 2 for yh, yr in zip(y_hat, Y_pad))
        if dist < melhor:
            melhor, best_idx = dist, i
    return saidas[best_idx]

def _variacoes_da_saida(saida: dict) -> list[str]:
    if "textos" in saida and saida["textos"]:
        variacoes = saida["textos"][:]
    elif "texto" in saida:
        variacoes = [saida["texto"]]
    else:
        variacoes = ["[Sem texto registrado nesta saída]"]
    if saida.get("reacao"):
        variacoes = [f"{v} {saida['reacao']}" for v in variacoes]
    return variacoes

def infer(memoria: dict, dominio: str) -> None:
    if not os.path.exists(CKPT):
        print("⚠️ Checkpoint não encontrado. Treinando antes de inferir.")
        train(memoria, dominio)

    state, max_x, max_y = torch.load(CKPT)
    blocos = memoria["maes"][dominio]["blocos"]
    if not blocos:
        print("⚠️ Nenhum bloco encontrado para inferência.")
        return

    model = InsepaReg(max_x, max_y)
    model.load_state_dict(state)
    model.eval()

    raw = entrada_usuario("inicial")
    txt, rea = parse_text_reaction(raw, blocos)

    bloco_atual = next(
        (b for b in blocos
         if b.get("entrada", {}).get("texto") == txt
         and b.get("entrada", {}).get("reacao", "") == rea),
        None
    )
    if bloco_atual is None:
        mensagem_cosmica()
        return

    while True:
        saida_escolhida = _escolher_saida_por_modelo(model, max_x, max_y, bloco_atual)
        if not saida_escolhida:
            print("⚠️ Não há interação disponível.")
            return

        variacoes = _variacoes_da_saida(saida_escolhida)
        idx = 0

        while True:
            if idx < len(variacoes):
                print(f"\n🤖 {variacoes[idx]}")
                idx += 1
            else:
                mensagem_cosmica()
                break

            entrada = entrada_usuario("playlist")
            if entrada.strip():
                novo_txt, novo_rea = parse_text_reaction(entrada, blocos)
                bloco_novo = next(
                    (b for b in blocos
                     if b.get("entrada", {}).get("texto") == novo_txt
                     and b.get("entrada", {}).get("reacao", "") == novo_rea),
                    None
                )
                if bloco_novo:
                    bloco_atual = bloco_novo
                    break
                else:
                    mensagem_cosmica()
        if idx >= len(variacoes) and not entrada.strip():
            break

# ────────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(ARQUIVO_MEMORIA):
        with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
            json.dump({"maes": {}}, f, ensure_ascii=False, indent=2)

    memoria = json.load(open(ARQUIVO_MEMORIA, "r", encoding="utf-8"))
    dominio = input("Domínio (índice-mãe): ").strip()

    print("\n1) Treinar rede neural   2) Inferir com rede neural")
    op = input("Opção: ").strip()
    if op == "1":
        train(memoria, dominio)
    else:
        infer(memoria, dominio)
