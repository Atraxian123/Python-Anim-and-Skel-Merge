#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Compatibile con Python 2.6+ e Python 3.
from __future__ import print_function
"""
merge_skel.py — unisce uno "skeleton figlio" (.skel con chunk SKPD, che
contiene override di alcune animazioni) dentro lo "skeleton genitore"
(.skel referenziato da SKPD), producendo un unico .skel standalone.

COME FUNZIONA (verificato sui file forniti):
  - Genitore e figlio hanno la STESSA identica lista di ossa (stesso numero,
    stesso ordine, stessi key_bone_id/parent_bone/submesh_id).
  - Il genitore ha l'elenco COMPLETO delle animazioni (SKS1, es. 81 entry).
  - Il figlio ha solo un sottoinsieme di animazioni (es. 5) che sono delle
    RISCRITTURE (override) di animazioni già presenti nel genitore, individuate
    per coppia (animID, subAnimID).
  - Per ogni osso, l'array di "sotto-blocchi" di keyframe di ogni canale
    (translation/rotation/scaling) è allineato POSIZIONALMENTE con l'array
    delle animazioni in SKS1 (stessa lunghezza, stesso ordine).

Il merge quindi:
  1. Trova per ogni animazione del figlio l'indice corrispondente nell'array
     di animazioni del genitore (match su animID+subAnimID).
  2. Sostituisce il record dell'animazione (SKS1) a quell'indice.
  3. Per ogni osso e ogni canale, sostituisce il sotto-blocco di keyframe a
     quell'indice con quello del figlio.
  4. Se il figlio referenzia una Global Sequence con una durata non presente
     nel genitore, la aggiunge e rimappa l'indice.
  5. Riserializza SKB1/SKS1 da zero (offset interni ricalcolati), copiando
     invariati SKL1/SKA1/AFID/BFID dal genitore. Il chunk SKPD non viene
     scritto nell'output (il file risultante è uno skeleton "standalone",
     come il genitore).

LIMITI / cose da verificare a mano:
  - Se un'animazione del figlio NON esiste affatto nel genitore (nessun
    animID+subAnimID corrispondente), lo script solleva un errore invece di
    indovinare come "appenderla" — questo caso va deciso caso per caso
    (richiede anche estendere l'array di animazioni in SKS1, la Animation
    Lookup table, e i sotto-blocchi di TUTTE le altre ossa con un blocco
    vuoto). Se vi serve, ditemelo e lo aggiungo.
  - Assume che ogni traccia (translation/rotation/scaling) di ogni osso abbia
    lo stesso numero di sotto-blocchi del numero di animazioni del rispettivo
    file (vero per i file analizzati). Se nel vostro file non fosse così,
    lo script stampa un avviso invece di corrompere silenziosamente i dati.

Uso:
    python3 merge_skel.py centaur2_male.skel centaur2_female.skel merged.skel
"""

import struct
import sys


# ---------------------------------------------------------------------------
# Lettura chunk generica: magic(4) + size(uint32 LE) + payload
# ---------------------------------------------------------------------------

def read_chunks(data):
    chunks = {}
    off = 0
    while off < len(data):
        magic = data[off:off + 4].decode('ascii')
        size = struct.unpack_from('<I', data, off + 4)[0]
        chunks[magic] = data[off + 8:off + 8 + size]
        off += 8 + size
    return chunks


def make_chunk(magic, payload):
    assert len(magic) == 4
    return magic.encode('ascii') + struct.pack('<I', len(payload)) + payload


# ---------------------------------------------------------------------------
# SKB1 (ossa)
# ---------------------------------------------------------------------------

BONE_HDR_FMT = '<iIhHI'          # key_bone_id, flags, parent_bone, submesh_id, crc
BONE_HDR_SIZE = struct.calcsize(BONE_HDR_FMT)   # 16
TRACK_HDR_FMT = '<HhIiIi'        # interp, gseq, nTS, ofsTS, nKF, ofsKF
TRACK_HDR_SIZE = struct.calcsize(TRACK_HDR_FMT)  # 20
BONE_SIZE = BONE_HDR_SIZE + 3 * TRACK_HDR_SIZE + 12   # +pivot C3Vector


def parse_track(data, base, pos, kind):
    interp, gseq, nts, ots, nkf, okf = struct.unpack_from(TRACK_HDR_FMT, data, pos)

    timestamps = []
    if nts:
        tbase = base + ots
        for i in range(nts):
            n, o = struct.unpack_from('<ii', data, tbase + i * 8)
            timestamps.append(list(struct.unpack_from('<%dI' % n, data, base + o)) if n else [])

    keyframes = []
    if nkf:
        kbase = base + okf
        for i in range(nkf):
            n, o = struct.unpack_from('<ii', data, kbase + i * 8)
            if n:
                if kind == 'rot':
                    vals = [struct.unpack_from('<4H', data, base + o + j * 8) for j in range(n)]
                else:
                    vals = [struct.unpack_from('<3f', data, base + o + j * 12) for j in range(n)]
            else:
                vals = []
            keyframes.append(vals)

    return {'interp': interp, 'gseq': gseq, 'timestamps': timestamps, 'keyframes': keyframes}


def parse_skb1(payload):
    nBones, ofsBones, nKeyBoneLookup, ofsKeyBoneLookup = struct.unpack_from('<4I', payload, 0)
    bones = []
    pos = ofsBones
    for i in range(nBones):
        key_bone_id, flags, parent_bone, submesh_id, crc = struct.unpack_from(BONE_HDR_FMT, payload, pos)
        p = pos + BONE_HDR_SIZE
        tr = parse_track(payload, 0, p, 'vec'); p += TRACK_HDR_SIZE
        rot = parse_track(payload, 0, p, 'rot'); p += TRACK_HDR_SIZE
        sc = parse_track(payload, 0, p, 'vec'); p += TRACK_HDR_SIZE
        pivot = struct.unpack_from('<3f', payload, p)
        bones.append({
            'key_bone_id': key_bone_id, 'flags': flags, 'parent_bone': parent_bone,
            'submesh_id': submesh_id, 'crc': crc,
            'translation': tr, 'rotation': rot, 'scaling': sc, 'pivot': pivot,
        })
        pos += BONE_SIZE

    keybonelookup = []
    if ofsKeyBoneLookup:
        keybonelookup = list(struct.unpack_from('<%dh' % nKeyBoneLookup, payload, ofsKeyBoneLookup))

    return {'bones': bones, 'keybonelookup': keybonelookup}


def write_skb1(skb1):
    bones = skb1['bones']
    n = len(bones)
    kbl = skb1['keybonelookup']

    ofsBones = 16
    ofsKeyBoneLookup = ofsBones + n * BONE_SIZE
    var_start = ofsKeyBoneLookup + 2 * len(kbl)
    if var_start % 4:
        var_start += 4 - (var_start % 4)   # padding ad allineamento 4 byte

    out = bytearray(var_start)
    struct.pack_into('<4I', out, 0, n, ofsBones, len(kbl), ofsKeyBoneLookup if kbl else 0)
    if kbl:
        struct.pack_into('<%dh' % len(kbl), out, ofsKeyBoneLookup, *kbl)

    def alloc(nbytes):
        off = len(out)
        out.extend(b'\x00' * nbytes)
        return off

    for bi, bone in enumerate(bones):
        bone_off = ofsBones + bi * BONE_SIZE
        struct.pack_into(BONE_HDR_FMT, out, bone_off,
                          bone['key_bone_id'], bone['flags'], bone['parent_bone'],
                          bone['submesh_id'], bone['crc'])
        tpos = bone_off + BONE_HDR_SIZE
        for kind, key in (('vec', 'translation'), ('rot', 'rotation'), ('vec', 'scaling')):
            track = bone[key]
            ts, kf = track['timestamps'], track['keyframes']

            if ts:
                desc_off = alloc(len(ts) * 8)
                for i, vals in enumerate(ts):
                    voff = alloc(len(vals) * 4) if vals else 0
                    if vals:
                        struct.pack_into('<%dI' % len(vals), out, voff, *vals)
                    struct.pack_into('<ii', out, desc_off + i * 8, len(vals), voff)
                ots, nts = desc_off, len(ts)
            else:
                ots, nts = 0, 0

            if kf:
                desc_off = alloc(len(kf) * 8)
                for i, vals in enumerate(kf):
                    if vals:
                        if kind == 'rot':
                            voff = alloc(len(vals) * 8)
                            for j, v in enumerate(vals):
                                struct.pack_into('<4H', out, voff + j * 8, *v)
                        else:
                            voff = alloc(len(vals) * 12)
                            for j, v in enumerate(vals):
                                struct.pack_into('<3f', out, voff + j * 12, *v)
                    else:
                        voff = 0
                    struct.pack_into('<ii', out, desc_off + i * 8, len(vals), voff)
                okf, nkf = desc_off, len(kf)
            else:
                okf, nkf = 0, 0

            struct.pack_into(TRACK_HDR_FMT, out, tpos, track['interp'], track['gseq'], nts, ots, nkf, okf)
            tpos += TRACK_HDR_SIZE

        struct.pack_into('<3f', out, tpos, *bone['pivot'])

    return bytes(out)


# ---------------------------------------------------------------------------
# SKS1 (sequenze/animazioni)
# ---------------------------------------------------------------------------

ANIM_SIZE = 64


def parse_sks1(payload):
    nGS, oGS, nAnim, oAnim, nLookup, oLookup, u1, u2 = struct.unpack_from('<8I', payload, 0)
    gseqs = list(struct.unpack_from('<%dI' % nGS, payload, oGS)) if nGS else []
    anims = []
    for i in range(nAnim):
        raw = payload[oAnim + i * ANIM_SIZE: oAnim + (i + 1) * ANIM_SIZE]
        animID, subID = struct.unpack_from('<HH', raw, 0)
        anims.append({'animID': animID, 'subID': subID, 'raw': raw})
    lookup = list(struct.unpack_from('<%dh' % nLookup, payload, oLookup)) if nLookup else []
    return {'gseqs': gseqs, 'anims': anims, 'lookup': lookup, 'u1': u1, 'u2': u2}


def write_sks1(sks1):
    gseqs, anims, lookup = sks1['gseqs'], sks1['anims'], sks1['lookup']
    HDR = 32
    oGS = HDR
    oAnim = oGS + 4 * len(gseqs)
    oLookup = oAnim + ANIM_SIZE * len(anims)
    total = oLookup + 2 * len(lookup)

    out = bytearray(total)
    struct.pack_into('<8I', out, 0, len(gseqs), oGS if gseqs else 0,
                      len(anims), oAnim if anims else 0,
                      len(lookup), oLookup if lookup else 0,
                      sks1['u1'], sks1['u2'])
    if gseqs:
        struct.pack_into('<%dI' % len(gseqs), out, oGS, *gseqs)
    for i, a in enumerate(anims):
        out[oAnim + i * ANIM_SIZE: oAnim + (i + 1) * ANIM_SIZE] = a['raw']
    if lookup:
        struct.pack_into('<%dh' % len(lookup), out, oLookup, *lookup)
    return bytes(out)


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge(parent_skb1, parent_sks1, daughter_skb1, daughter_sks1):
    p_bones, d_bones = parent_skb1['bones'], daughter_skb1['bones']
    if len(p_bones) != len(d_bones):
        raise ValueError(
            "Le due skeleton hanno un numero diverso di ossa "
            "(%d vs %d): questo script gestisce solo "
            "il caso 'stessa gerarchia, animazioni diverse'."
            % (len(p_bones), len(d_bones))
        )

    # 1) Global sequences: mappa indice-figlio -> indice-genitore (aggiungendo se serve)
    merged_gseqs = list(parent_sks1['gseqs'])
    gseq_map = {-1: -1}
    for idx, val in enumerate(daughter_sks1['gseqs']):
        if val in merged_gseqs:
            gseq_map[idx] = merged_gseqs.index(val)
        else:
            merged_gseqs.append(val)
            gseq_map[idx] = len(merged_gseqs) - 1

    # 2) Trova a quale indice del genitore corrisponde ogni animazione del figlio
    match = {}
    for di, da in enumerate(daughter_sks1['anims']):
        pi = next((k for k, pa in enumerate(parent_sks1['anims'])
                   if pa['animID'] == da['animID'] and pa['subID'] == da['subID']), None)
        if pi is None:
            raise ValueError(
                "L'animazione della figlia animID=%d subID=%d "
                "non esiste nel genitore: servirebbe la logica di 'append', non ancora "
                "implementata. Ditemi se vi serve e la aggiungo."
                % (da['animID'], da['subID'])
            )
        match[di] = pi
        print("  override: animID=%d subID=%d -> indice genitore %d" % (da['animID'], da['subID'], pi))

    # 3) Sostituisci i record delle animazioni
    merged_anims = list(parent_sks1['anims'])
    for di, pi in match.items():
        merged_anims[pi] = daughter_sks1['anims'][di]

    # 4) Sostituisci i sotto-blocchi di keyframe, osso per osso
    merged_bones = []
    for bi, (pb, db) in enumerate(zip(p_bones, d_bones)):
        nb = dict(pb)
        for comp in ('translation', 'rotation', 'scaling'):
            pt, dt = pb[comp], db[comp]
            new_ts = list(pt['timestamps'])
            new_kf = list(pt['keyframes'])
            new_interp, new_gseq = pt['interp'], pt['gseq']

            if len(pt['timestamps']) not in (0, len(parent_sks1['anims'])):
                print("  [avviso] osso %d %s: %d blocchi != %d animazioni del genitore"
                      % (bi, comp, len(pt['timestamps']), len(parent_sks1['anims'])))

            for di, pi in match.items():
                if di < len(dt['timestamps']) and pi < len(new_ts):
                    new_ts[pi] = dt['timestamps'][di]
                if di < len(dt['keyframes']) and pi < len(new_kf):
                    new_kf[pi] = dt['keyframes'][di]
                if dt['gseq'] != -1:
                    new_interp = dt['interp']
                    new_gseq = gseq_map.get(dt['gseq'], dt['gseq'])

            nb[comp] = {'interp': new_interp, 'gseq': new_gseq,
                        'timestamps': new_ts, 'keyframes': new_kf}
        merged_bones.append(nb)

    merged_skb1 = {'bones': merged_bones, 'keybonelookup': parent_skb1['keybonelookup']}
    merged_sks1 = {'gseqs': merged_gseqs, 'anims': merged_anims,
                    'lookup': parent_sks1['lookup'],
                    'u1': parent_sks1['u1'], 'u2': parent_sks1['u2']}
    return merged_skb1, merged_sks1


# ---------------------------------------------------------------------------
# I/O file .skel completo
# ---------------------------------------------------------------------------

def load(path):
    data = open(path, 'rb').read()
    return read_chunks(data)


def main():
    if len(sys.argv) != 4:
        print("Uso: python3 merge_skel.py <genitore.skel> <figlia.skel> <output.skel>")
        sys.exit(1)

    parent_path, daughter_path, out_path = sys.argv[1:4]

    parent_chunks = load(parent_path)
    daughter_chunks = load(daughter_path)

    if 'SKPD' not in daughter_chunks:
        print("[avviso] il secondo file non ha un chunk SKPD: sei sicuro sia la skeleton figlia?")

    parent_skb1 = parse_skb1(parent_chunks['SKB1'])
    parent_sks1 = parse_sks1(parent_chunks['SKS1'])
    daughter_skb1 = parse_skb1(daughter_chunks['SKB1'])
    daughter_sks1 = parse_sks1(daughter_chunks['SKS1'])

    print("Genitore: %d ossa, %d animazioni" % (len(parent_skb1['bones']), len(parent_sks1['anims'])))
    print("Figlia:   %d ossa, %d animazioni" % (len(daughter_skb1['bones']), len(daughter_sks1['anims'])))
    print("Merge in corso...")

    merged_skb1, merged_sks1 = merge(parent_skb1, parent_sks1, daughter_skb1, daughter_sks1)

    out_chunks = []
    out_chunks.append(make_chunk('SKL1', parent_chunks['SKL1']))          # invariato
    out_chunks.append(make_chunk('SKS1', write_sks1(merged_sks1)))
    out_chunks.append(make_chunk('SKB1', write_skb1(merged_skb1)))
    if 'SKA1' in parent_chunks:
        out_chunks.append(make_chunk('SKA1', parent_chunks['SKA1']))      # invariato
    if 'AFID' in parent_chunks:
        out_chunks.append(make_chunk('AFID', parent_chunks['AFID']))      # invariato
    if 'BFID' in parent_chunks:
        out_chunks.append(make_chunk('BFID', parent_chunks['BFID']))      # invariato
    # NB: il chunk SKPD non viene riscritto: il file risultante è uno
    # skeleton standalone (come il genitore), non serve più il riferimento.

    with open(out_path, 'wb') as f:
        f.write(b''.join(out_chunks))

    print("Scritto: %s" % out_path)


if __name__ == '__main__':
    main()
