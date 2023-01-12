#===================================================================================================================

# Local Windowed Attention Trasformer Module
# Version 1.0

# Source code courtesy of lucidrains
# https://github.com/lucidrains/local-attention
# Code retrieved on 12/11/2022

# Project Los Angeles
# Tegridy Code 2022

#===================================================================================================================

# Critical dependencies

# !pip install torch
# !pip install einops

#===================================================================================================================

import math

import torch
from torch import nn, einsum
import torch.nn.functional as F

from einops import rearrange, repeat, pack, unpack

#===================================================================================================================

class SinusoidalEmbeddings(nn.Module):
    def __init__(self, dim):
        super().__init__()
        inv_freq = 1. / (10000 ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer('inv_freq', inv_freq)

    def forward(self, x):
        n = x.shape[-2]
        t = torch.arange(n, device = x.device).type_as(self.inv_freq)
        freqs = torch.einsum('i , j -> i j', t, self.inv_freq)
        return torch.cat((freqs, freqs), dim=-1)

def rotate_half(x):
    x = rearrange(x, 'b ... (r d) -> b (...) r d', r = 2)
    x1, x2 = x.unbind(dim = -2)
    return torch.cat((-x2, x1), dim = -1)

def apply_rotary_pos_emb(q, k, freqs):
    q, k = map(lambda t: (t * freqs.cos()) + (rotate_half(t) * freqs.sin()), (q, k))
    return q, k

#===================================================================================================================

# constant

TOKEN_SELF_ATTN_VALUE = -5e4

# helper functions

def exists(val):
    return val is not None

def default(value, d):
    return d if not exists(value) else value

def to(t):
    return {'device': t.device, 'dtype': t.dtype}

def max_neg_value(tensor):
    return -torch.finfo(tensor.dtype).max

def l2norm(tensor):
    dtype = tensor.dtype
    normed = F.normalize(tensor, dim = -1)
    return normed.type(dtype)

def pad_to_multiple(tensor, multiple, dim=-1, value=0):
    seqlen = tensor.shape[dim]
    m = seqlen / multiple
    if m.is_integer():
        return False, tensor
    remainder = math.ceil(m) * multiple - seqlen
    pad_offset = (0,) * (-1 - dim) * 2
    return True, F.pad(tensor, (*pad_offset, 0, remainder), value = value)

def look_around(x, backward = 1, forward = 0, pad_value = -1, dim = 2):
    t = x.shape[1]
    dims = (len(x.shape) - dim) * (0, 0)
    padded_x = F.pad(x, (*dims, backward, forward), value = pad_value)
    tensors = [padded_x[:, ind:(ind + t), ...] for ind in range(forward + backward + 1)]
    return torch.cat(tensors, dim = dim)

# main class

class LocalAttention(nn.Module):
    def __init__(
        self,
        window_size,
        causal = False,
        look_backward = 1,
        look_forward = None,
        dropout = 0.,
        shared_qk = False,
        rel_pos_emb_config = None,
        dim = None,
        autopad = False,
        exact_windowsize = False
    ):
        super().__init__()
        look_forward = default(look_forward, 0 if causal else 1)
        assert not (causal and look_forward > 0), 'you cannot look forward if causal'

        self.window_size = window_size
        self.autopad = autopad
        self.exact_windowsize = exact_windowsize

        self.causal = causal

        self.look_backward = look_backward
        self.look_forward = look_forward

        self.dropout = nn.Dropout(dropout)

        self.shared_qk = shared_qk

        # relative positions

        self.rel_pos = None
        if exists(rel_pos_emb_config) or exists(dim):  # backwards compatible with old `rel_pos_emb_config` deprecated argument
            if exists(rel_pos_emb_config):
                dim = rel_pos_emb_config[0]
            self.rel_pos = SinusoidalEmbeddings(dim)

    def forward(self, q, k, v, mask = None, input_mask = None):
        mask = default(mask, input_mask)

        shape, autopad, pad_value, window_size, causal, look_backward, look_forward, shared_qk = q.shape, self.autopad, -1, self.window_size, self.causal, self.look_backward, self.look_forward, self.shared_qk

        # https://github.com/arogozhnikov/einops/blob/master/docs/4-pack-and-unpack.ipynb
        (q, packed_shape), (k, _), (v, _) = map(lambda t: pack([t], '* n d'), (q, k, v))

        # rotary embeddings

        if exists(self.rel_pos):
            pos_emb = self.rel_pos(q)
            q, k = apply_rotary_pos_emb(q, k, pos_emb)

        # auto padding

        if autopad:
            orig_seq_len = q.shape[1]
            (needed_pad, q), (_, k), (_, v) = map(lambda t: pad_to_multiple(t, self.window_size, dim = -2), (q, k, v))

        b, n, dim_head, device, dtype = *q.shape, q.device, q.dtype
        scale = dim_head ** -0.5

        assert (n % window_size) == 0, f'sequence length {t} must be divisible by window size {window_size} for local attention'

        windows = n // window_size

        if shared_qk:
            k = l2norm(k)

        seq = torch.arange(n, device = device)
        b_t = rearrange(seq, '(w n) -> 1 w n', w = windows, n = window_size)

        bq, bk, bv = map(lambda t: rearrange(t, 'b (w n) d -> b w n d', w = windows), (q, k, v))

        look_around_kwargs = dict(
            backward =  look_backward,
            forward =  look_forward,
            pad_value = pad_value
        )

        bk = look_around(bk, **look_around_kwargs)
        bv = look_around(bv, **look_around_kwargs)

        bq_t = b_t
        bq_k = look_around(b_t, **look_around_kwargs)

        bq_t = rearrange(bq_t, '... i -> ... i 1')
        bq_k = rearrange(bq_k, '... j -> ... 1 j')

        sim = einsum('b h i e, b h j e -> b h i j', bq, bk) * scale

        mask_value = max_neg_value(sim)

        if shared_qk:
            self_mask = bq_t == bq_k
            sim = sim.masked_fill(self_mask, TOKEN_SELF_ATTN_VALUE)
            del self_mask

        if causal:
            causal_mask = bq_t < bq_k

            if self.exact_windowsize:
                max_causal_window_size = (self.window_size * self.look_backward)
                causal_mask = causal_mask | (bq_t > (bq_k + max_causal_window_size))

            sim = sim.masked_fill(causal_mask, mask_value)
            del causal_mask

        # mask out padding value

        if autopad and needed_pad:
            pad_mask = bq_k == pad_value
            sim = sim.masked_fill(pad_mask, mask_value)
            del pad_mask

        if exists(mask):
            batch = mask.shape[0]
            assert (b % batch) == 0

            h = b // mask.shape[0]

            if autopad:
                _, mask = pad_to_multiple(mask, window_size, dim = -1, value = False)

            mask = rearrange(mask, '... (w n) -> (...) w n', w = windows, n = window_size)
            mask = look_around(mask, **{**look_around_kwargs, 'pad_value': False})
            mask = rearrange(mask, '... j -> ... 1 j')
            mask = repeat(mask, 'b ... -> (b h) ...', h = h)
            sim = sim.masked_fill(~mask, mask_value)
            del mask

        # attention

        attn = sim.softmax(dim = -1)
        attn = self.dropout(attn)

        # aggregation

        out = einsum('b h i j, b h j e -> b h i e', attn, bv)
        out = rearrange(out, 'b w n d -> b (w n) d')

        if autopad:
            out = out[:, :orig_seq_len, :]

        out, *_ = unpack(out, packed_shape, '* n d')
        return out

#===================================================================================================================

# helper function

def exists(val):
    return val is not None

def eval_decorator(fn):
    def inner(model, *args, **kwargs):
        was_training = model.training
        model.eval()
        out = fn(model, *args, **kwargs)
        model.train(was_training)
        return out
    return inner

# sampling functions

def top_k(logits, thres = 0.9):
    k = int((1 - thres) * logits.shape[-1])
    val, ind = torch.topk(logits, k)
    probs = torch.full_like(logits, float('-inf'))
    probs.scatter_(1, ind, val)
    return probs

# multi-head attention

class LocalMHA(nn.Module):
    def __init__(
        self,
        *,
        dim,
        window_size,
        dim_head = 64,
        heads = 8,
        dropout = 0.,
        causal = False,
        prenorm = False,
        **kwargs
    ):
        super().__init__()        
        inner_dim = dim_head * heads

        self.norm = nn.LayerNorm(dim) if prenorm else None

        self.heads = heads
        self.to_qkv = nn.Linear(dim, inner_dim * 3, bias = False)

        self.attn_fn = LocalAttention(
            dim = dim_head,
            window_size = window_size,
            causal = causal,
            autopad = True,
            exact_windowsize = True,
            **kwargs
        )

        self.to_out = nn.Linear(inner_dim, dim, bias = False)

    def forward(self, x, mask = None):
        if exists(self.norm):
            x = self.norm(x)

        q, k, v = self.to_qkv(x).chunk(3, dim = -1)
        q, k, v = map(lambda t: rearrange(t, 'b n (h d) -> b h n d', h = self.heads), (q, k, v)) 

        out = self.attn_fn(q, k, v, mask = mask)

        out = rearrange(out, 'b h n d -> b n (h d)')
        return self.to_out(out)

# feedforward

class GEGLU(nn.Module):
    def forward(self, x):
        x, gate = x.chunk(2, dim = -1)
        return x * F.gelu(gate)

def FeedForward(dim, mult = 4, dropout = 0.):
    inner_dim = int(dim * mult * 2 / 3)

    return nn.Sequential(
        nn.LayerNorm(dim),
        nn.Linear(dim, inner_dim * 2, bias = False),
        GEGLU(),
        nn.Dropout(dropout),
        nn.Linear(inner_dim, dim, bias = False)
    )

# main transformer class

class LocalTransformer(nn.Module):
    def __init__(
        self,
        *,
        num_tokens,
        max_seq_len,
        dim,
        depth,
        causal = True,
        local_attn_window_size = 512,
        dim_head = 64,
        heads = 8,
        ff_mult = 4,
        attn_dropout = 0.,
        ff_dropout = 0.,
        ignore_index = -1,
        **kwargs
    ):
        super().__init__()
        self.token_emb = nn.Embedding(num_tokens, dim)
        self.pos_emb = nn.Embedding(max_seq_len, dim)
        self.token_pad = num_tokens
        self.max_seq_len = max_seq_len
        self.layers = nn.ModuleList([])

        for _ in range(depth):
            self.layers.append(nn.ModuleList([
                LocalMHA(dim = dim, dim_head = dim_head, heads = heads, dropout = attn_dropout, causal = causal, window_size = local_attn_window_size, prenorm = True, **kwargs),
                FeedForward(dim = dim, mult = ff_mult, dropout = ff_dropout)
            ]))

        self.ignore_index = ignore_index
        self.to_logits = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, num_tokens, bias = False)
        )

    @torch.no_grad()
    @eval_decorator
    def generate(
        self,
        prime,
        seq_len,
        temperature = 0.8,
        filter_thres = 0.9,
        min_stop_token = 0,
        return_prime = False,
        verbose = True,
        **kwargs
    ):
        n, device = prime.shape[1], prime.device

        out = prime

        if verbose:
          print("Generating sequence of max length:", seq_len)

        for s in range(seq_len):
             
            logits = self.forward(out[:, -self.max_seq_len:], return_loss=False, **kwargs)
            filtered_logits = top_k(logits[:, -1], thres = filter_thres)
            probs = F.softmax(filtered_logits / temperature, dim = -1)
            sampled = torch.multinomial(probs, 1)
            out = torch.cat((out, sampled), dim = -1)

            if verbose:
              if s % 32 == 0:
                print(s, '/', seq_len)

            if min_stop_token > 0:
              for sa in sampled:
                  if sa >= min_stop_token:
                    stop = True
                    break
                  else:
                    stop = False
              if stop:
                    if verbose: 
                      print('Model called the end of sequence at:', s, '/', seq_len)
                    break
               
        if return_prime:
          return out[:, :]
        
        else:
          return out[:, n:]

    def compute_accuracy(self, logits, labels): 
        out = torch.argmax(logits, dim=-1) 
        out = out.flatten()
        labels = labels.flatten() 

        mask = (labels != self.token_pad)

        out = out[mask]
        labels = labels[mask]

        num_right = (out == labels)
        num_right = torch.sum(num_right).type(torch.float32)

        acc = num_right / len(labels)
        
        return acc
    
    def choose_best_acc(self, outy):
    
        losses_accs = []

        for i in range(len(outy)):

            out1 = outy[i].tolist()
            out2 = torch.LongTensor([out1]).cuda()
            with torch.no_grad():
                val_loss, val_acc = self.forward(out2, return_loss = True)
                losses_accs.append([i, val_loss.tolist(), val_acc.tolist()])

        losses_accs.sort(key=lambda x: x[2], reverse=True)

        return losses_accs

    def forward(self, x, mask = None, return_loss = True):
        if return_loss:
            x, labels = x[:, :-1], x[:, 1:]

        n, device = x.shape[1], x.device
        x = self.token_emb(x)

        assert n <= self.max_seq_len
        x = x + self.pos_emb(torch.arange(n, device = device))

        for attn, ff in self.layers:
            x = attn(x, mask = mask) + x
            x = ff(x) + x

        logits = self.to_logits(x)

        if not return_loss:
            return logits

        acc = self.compute_accuracy(logits, labels)

        logits = rearrange(logits, 'b n c -> b c n')
        loss = F.cross_entropy(logits, labels, ignore_index = self.ignore_index)
        
        return loss, acc

#===================================================================================================================