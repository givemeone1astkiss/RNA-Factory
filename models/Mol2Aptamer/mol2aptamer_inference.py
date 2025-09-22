#!/usr/bin/env python3
"""
Mol2Aptamer推理脚本
基于原始笔记本文件中的推理代码，严格使用原始实现
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from tokenizers import Tokenizer
import RNA
import os
import argparse


class Mol2Aptamer(nn.Module):
    """Mol2Aptamer模型定义 - 来自原始笔记本"""
    def __init__(self, smiles_vocab_size, rna_vocab_size, d_model=256, nhead=8, num_encoder_layers=2, num_decoder_layers=3):
        super().__init__()
        self.d_model = d_model  # 显式保存模型维度，便于验证
        
        # Encoder：2层 TransformerEncoder（d_model=256）
        self.encoder = nn.TransformerEncoder(
            encoder_layer=nn.TransformerEncoderLayer(
                d_model=d_model,       # 注意力层期望的维度=256
                nhead=nhead,
                dim_feedforward=2048,
                batch_first=True
            ),
            num_layers=num_encoder_layers
        )
        
        # Decoder：3层 TransformerDecoder（d_model=256）
        self.decoder = nn.TransformerDecoder(
            decoder_layer=nn.TransformerDecoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=2048,
                batch_first=True
            ),
            num_layers=num_decoder_layers
        )
        
        # 嵌入层：明确设置输出维度=d_model=256
        self.smiles_embedding = nn.Embedding(smiles_vocab_size, d_model)  # 输出 (seq_len, 256)
        self.rna_embedding = nn.Embedding(rna_vocab_size, d_model)
        self.pos_embedding = nn.Embedding(512, d_model)  # 位置编码维度也=256
        
        # 输出层
        self.fc_out = nn.Linear(d_model, rna_vocab_size)

    def forward(self, smiles_ids, rna_inp):
        batch_size, seq_len_smi = smiles_ids.shape
        batch_size, seq_len_rna = rna_inp.shape
        device = smiles_ids.device
        
        # 验证嵌入层输出维度（确保=256）
        smiles_emb = self.smiles_embedding(smiles_ids)
        assert smiles_emb.shape[-1] == self.d_model, \
            f"嵌入层输出维度错误：期望 {self.d_model}，实际 {smiles_emb.shape[-1]}"
        
        # 叠加位置编码（维度需与嵌入层一致）
        smiles_pos = torch.arange(seq_len_smi, device=device).unsqueeze(0).repeat(batch_size, 1)
        smiles_emb += self.pos_embedding(smiles_pos)
        assert smiles_emb.shape[-1] == self.d_model, \
            f"位置编码后维度错误：期望 {self.d_model}，实际 {smiles_emb.shape[-1]}"
        
        # Encoder前向（输入维度=256，匹配注意力层期望）
        memory = self.encoder(smiles_emb)
        
        # RNA嵌入与位置编码（同样验证维度）
        rna_emb = self.rna_embedding(rna_inp)
        assert rna_emb.shape[-1] == self.d_model, \
            f"RNA嵌入层输出维度错误：期望 {self.d_model}，实际 {rna_emb.shape[-1]}"
        rna_pos = torch.arange(seq_len_rna, device=device).unsqueeze(0).repeat(batch_size, 1)
        rna_emb += self.pos_embedding(rna_pos)
        
        # Decoder前向
        tgt_mask = nn.Transformer.generate_square_subsequent_mask(seq_len_rna, device=device)
        decoder_out = self.decoder(tgt=rna_emb, memory=memory, tgt_mask=tgt_mask)
        
        # 输出层
        logits = self.fc_out(decoder_out)
        return logits


def generate_aptamers(
    model, smiles, smiles_tokenizer, rna_tokenizer,
    max_len=80, num_return=5,
    strategy="topk", top_k=10, top_p=0.9, temperature=0.8,
    device=None
):
    """
    生成Aptamer序列的推理函数 - 来自原始笔记本
    支持多种采样策略
    """
    if device is None:
        device = next(model.parameters()).device
    
    model.eval()
    model.to(device)
    
    # 验证特殊token
    required_tokens = ["<pad>", "<bos>", "<eos>", "<unk>"]
    for token in required_tokens:
        token_id = rna_tokenizer.token_to_id(token)
        if token_id is None:
            raise ValueError(f"RNA tokenizer missing required token: {token}")
    
    bos_id = rna_tokenizer.token_to_id("<bos>")
    eos_id = rna_tokenizer.token_to_id("<eos>")
    pad_id = rna_tokenizer.token_to_id("<pad>")
    unk_id = rna_tokenizer.token_to_id("<unk>")
    smiles_pad_id = smiles_tokenizer.token_to_id("<pad>")
    if smiles_pad_id is None:
        raise ValueError("SMILES tokenizer missing <pad> token")
    
    # 编码SMILES
    try:
        smi_encoded = smiles_tokenizer.encode(smiles)
        max_smi_len = 128  # 与训练时一致
        # 补全/截断SMILES到max_smi_len
        smi_ids = smi_encoded.ids[:max_smi_len]
        smi_ids += [smiles_pad_id] * (max_smi_len - len(smi_ids))
        # 转换为张量：(batch_size=1, seq_len=128)
        smi_ids = torch.tensor(smi_ids, dtype=torch.long).unsqueeze(0).to(device)
        assert smi_ids.shape == (1, max_smi_len), \
            f"SMILES张量形状错误：期望 (1, {max_smi_len})，实际 {smi_ids.shape}"
    except Exception as e:
        raise ValueError(f"Failed to encode SMILES: {str(e)}")
    
    results = []
    with torch.no_grad():
        # 验证Encoder输入维度（嵌入层输出应为256）
        smiles_emb = model.smiles_embedding(smi_ids)
        assert smiles_emb.shape == (1, max_smi_len, model.d_model), \
            f"SMILES嵌入后形状错误：期望 (1, {max_smi_len}, {model.d_model})，实际 {smiles_emb.shape}"
        
        # 预计算Encoder输出
        memory = model.encoder(smiles_emb)
        
        for _ in range(num_return):
            generated = [bos_id]
            has_unk = False
            
            for _ in range(max_len - 1):
                # RNA输入张量：(1, current_len)
                rna_inp = torch.tensor([generated], dtype=torch.long).to(device)
                
                # 模型前向传播
                logits = model(smi_ids, rna_inp)[:, -1, :]  # (1, rna_vocab_size)
                
                # 温度调节
                logits = logits / temperature
                
                # 采样策略
                if strategy == "greedy":
                    next_id = torch.argmax(logits, dim=-1).item()
                elif strategy == "topk":
                    topk_probs, topk_ids = torch.topk(logits, k=top_k)
                    topk_probs = F.softmax(topk_probs, dim=-1)
                    idx = torch.multinomial(topk_probs, 1).item()
                    next_id = topk_ids[0, idx].item()
                elif strategy == "topp":
                    sorted_logits, sorted_ids = torch.sort(logits, descending=True)
                    sorted_probs = F.softmax(sorted_logits, dim=-1)
                    cum_probs = torch.cumsum(sorted_probs, dim=-1)
                    cutoff = max(1, torch.sum(cum_probs <= top_p).item())
                    filtered_probs = sorted_probs[:, :cutoff]
                    filtered_ids = sorted_ids[:, :cutoff]
                    idx = torch.multinomial(filtered_probs, 1).item()
                    next_id = filtered_ids[0, idx].item()
                else:
                    raise ValueError(f"Unknown strategy: {strategy}")
                
                # 检查是否生成未知token
                if next_id == unk_id:
                    has_unk = True
                
                # 检查是否达到终止符
                if next_id == eos_id:
                    break
                
                generated.append(next_id)
            
            # 后处理
            filtered_ids = [id for id in generated if id not in [bos_id, eos_id, pad_id, unk_id]]
            try:
                # 使用分词器原生解码方法，确保BPE合并规则正确应用
                seq = rna_tokenizer.decode(filtered_ids, skip_special_tokens=True)
                
                # 过滤包含未知token或空的序列
                if seq and not has_unk and seq not in results:
                    results.append(seq)
            except Exception as e:
                print(f"Warning: Failed to decode sequence: {str(e)}")
    
    # 补全候选数量
    while len(results) < num_return:
        results.append(results[-1] if results else "")
    return results[:num_return]


def filter_by_rnafold(sequences, min_length=20, max_length=80, max_homopolymer=6, max_candidates=5):
    """
    过滤函数（RNAfold计算ΔG）- 来自原始笔记本
    sequences: list of str
    返回过滤+排序后的序列
    """
    results = []
    for seq in sequences:
        # 长度限制
        if len(seq) < min_length or len(seq) > max_length:
            continue
        # 去掉长同聚核苷酸 (AAAAAAA)
        if any(base*max_homopolymer in seq for base in "ACGU"):
            continue
        # 用 RNAfold 预测 ΔG
        structure, mfe = RNA.fold(seq)
        results.append((seq, mfe))

    # 按 ΔG 从低到高排序（越低越稳定）
    results = sorted(results, key=lambda x: x[1])
    return results[:max_candidates]


def generate_and_filter(
    model, smiles, smiles_tokenizer, rna_tokenizer,
    num_generate=50, return_top=5,
    strategy="topk", top_k=10, top_p=0.9, temperature=0.8,
    device=None
):
    """
    生成并过滤候选序列 - 来自原始笔记本
    """
    if device is None:
        device = next(model.parameters()).device
    
    # Step1: 生成候选
    candidates = generate_aptamers(
        model, smiles, smiles_tokenizer, rna_tokenizer,
        max_len=80, num_return=num_generate,
        strategy=strategy, top_k=top_k, top_p=top_p, temperature=temperature,
        device=device
    )

    # Step2: 过滤 & 打分
    filtered = filter_by_rnafold(candidates, max_candidates=return_top)

    return filtered


def load_model_and_tokenizers(model_path, smiles_tokenizer_path, rna_tokenizer_path, device):
    """加载模型和分词器"""
    # 加载分词器
    smiles_tokenizer = Tokenizer.from_file(smiles_tokenizer_path)
    rna_tokenizer = Tokenizer.from_file(rna_tokenizer_path)
    
    # 词汇表大小
    smiles_vocab_size = len(smiles_tokenizer.get_vocab())
    rna_vocab_size = len(rna_tokenizer.get_vocab())
    
    # 初始化模型
    model = Mol2Aptamer(
        smiles_vocab_size=smiles_vocab_size,
        rna_vocab_size=rna_vocab_size,
        d_model=256,          # 强制嵌入层输出维度=256
        nhead=8,
        num_encoder_layers=2,
        num_decoder_layers=3
    ).to(device)
    
    # 加载权重
    state_dict = torch.load(model_path, map_location=device)
    
    # 查看所有权重键，确认嵌入层键是否存在
    print("原始权重中的嵌入层相关键：")
    for key in state_dict.keys():
        if "embedding" in key:
            print(f"- {key}: 形状 {state_dict[key].shape}")
    print("-" * 50)
    
    # 过滤权重：保留所有与当前模型匹配的键
    filtered_state_dict = {}
    model_keys = set(model.state_dict().keys())
    for key, value in state_dict.items():
        if key in model_keys:
            # 额外验证嵌入层权重维度是否正确
            if "embedding.weight" in key:
                assert value.shape[-1] == model.d_model, \
                    f"{key} 维度错误：期望 {model.d_model}，实际 {value.shape[-1]}"
            filtered_state_dict[key] = value
        else:
            print(f"跳过冗余键：{key}")
    
    # 加载过滤后的权重
    model.load_state_dict(filtered_state_dict, strict=False)
    model.eval()
    print("权重加载成功！")
    
    return model, smiles_tokenizer, rna_tokenizer


def main():
    parser = argparse.ArgumentParser(description="Mol2Aptamer推理脚本")
    parser.add_argument("--smiles", type=str, default="C1=CC=C(C=C1)O", help="SMILES字符串")
    parser.add_argument("--num_sequences", type=int, default=5, help="生成的序列数量")
    parser.add_argument("--max_length", type=int, default=80, help="最大序列长度")
    parser.add_argument("--strategy", type=str, default="topk", choices=["greedy", "topk", "topp"], help="采样策略")
    parser.add_argument("--top_k", type=int, default=10, help="Top-K采样参数")
    parser.add_argument("--top_p", type=float, default=0.9, help="Top-P采样参数")
    parser.add_argument("--temperature", type=float, default=0.8, help="温度参数")
    parser.add_argument("--num_generate", type=int, default=50, help="生成候选数量")
    parser.add_argument("--return_top", type=int, default=5, help="返回top数量")
    
    args = parser.parse_args()
    
    # 设备选择
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # 路径设置
    base_path = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_path, "model_epoch_59.pth")
    smiles_tokenizer_path = os.path.join(base_path, "smiles_tokenizer.json")
    rna_tokenizer_path = os.path.join(base_path, "rna_tokenizer.json")
    
    # 加载模型和分词器
    model, smiles_tokenizer, rna_tokenizer = load_model_and_tokenizers(
        model_path, smiles_tokenizer_path, rna_tokenizer_path, device
    )
    
    # 生成前先验证模型嵌入层维度
    print(f"模型嵌入层输出维度：{model.d_model}")
    print(f"SMILES嵌入层权重形状：{model.smiles_embedding.weight.shape}")
    print(f"RNA嵌入层权重形状：{model.rna_embedding.weight.shape}")
    
    # 生成并过滤候选序列
    top_candidates = generate_and_filter(
        model, args.smiles, smiles_tokenizer, rna_tokenizer,
        num_generate=args.num_generate, return_top=args.return_top,
        strategy=args.strategy, top_k=args.top_k, top_p=args.top_p, temperature=args.temperature,
        device=device
    )
    
    # 输出结果
    print(f"\n输入SMILES: {args.smiles}")
    print("Top 适配体候选（按ΔG排序）：")
    for i, (seq, mfe) in enumerate(top_candidates, 1):
        print(f"{i}. {seq}   ΔG={mfe:.2f} kcal/mol")


if __name__ == "__main__":
    main()