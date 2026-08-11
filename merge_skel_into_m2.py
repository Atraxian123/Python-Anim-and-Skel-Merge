#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
merge_skel_into_m2.py — folds a .skel's bones, sequences, global_loops and
attachments directly into a chunked .m2's embedded MD20 header, producing a
self-contained .m2 that needs no external .skel (matches the layout of an
old-style, pre-.skel M2 like cupid.m2 -- verified byte-for-byte identical
struct layouts for M2Sequence and M2CompBone against that real file).

Strategy: the target .m2's bones/sequences/global_loops/attachments arrays
are assumed EMPTY (count=0, offset=0) -- true for any model that currently
depends on an external SKID/.skel. Because they're empty, nothing already
in the MD20 data section points near/after them, so we don't need to shift
or renumber any of the model's existing data (vertices, textures, views,
etc.) -- we simply append the new arrays at the end of the MD20 blob and
point the header fields at them, then delete the SKID chunk.

Internal offsets:
  - write_skb1()/our own write_ska1() each produce a SELF-CONTAINED blob
    whose internal pointers (ots/okf/descriptor tables) are relative to
    byte 0 of THAT blob. Once such a blob is appended at absolute position
    X within MD20, every one of those internal pointers must be rebased by
    +X (M2Array offsets in a model file are always relative to the start
    of the MD20 data, never to some inner sub-blob). rebase_skb1()/
    rebase_ska1() do exactly that, in place, using write_skb1/write_ska1's
    own (deterministic, since we control the writer) header to locate every
    offset field that needs patching.
  - write_sks1()'s sequences (M2Sequence records) do NOT need any rebasing:
    the only "index-like" fields inside a sequence record (variationNext /
    aliasNext) are relative indices into the sequences array itself, not
    byte offsets into the file.

Usage:
    python3 merge_skel_into_m2.py model.m2 skeleton.skel out.m2
"""
from __future__ import print_function
import struct
import sys

import merge_skel as ms

# M2Attachment (WotLK+): id u32, bone u16, unknown u16, position vec3f,
# animate_attached M2Track<boolean> (interp u16, gseq i16, ts M2Array, kf M2Array)
ATT_HDR_FMT = '<IHH3f'
ATT_HDR_SIZE = struct.calcsize(ATT_HDR_FMT)          # 16
ATT_SIZE = ATT_HDR_SIZE + ms.TRACK_HDR_SIZE           # 16 + 20 = 36... see note below

# NOTE: real files show ATT_SIZE == 40, not 36. The extra 4 bytes come from
# struct alignment: C3Vector (position) starts right after id(4)+bone(2)+
# unknown(2)=8 bytes with no padding, but the compiler pads the *track*
# that follows to keep the whole struct 4-byte aligned to a total of 40.
# Rather than guess further we verified this directly against
# centaur2_male.skel's real SKA1 bytes (id/bone/unknown/position/track all
# decoded cleanly at stride 40), so we hardcode the verified stride here.
ATT_SIZE = 40


# ---------------------------------------------------------------------------
# M2 top-level (SFID/TXID/etc.) + MD21 chunk splitting
# ---------------------------------------------------------------------------

def load_m2_chunks(path):
    data = open(path, 'rb').read()
    chunks = []          # keep order: list of (magic, payload)
    off = 0
    while off < len(data):
        magic = data[off:off + 4].decode('ascii')
        size = struct.unpack_from('<I', data, off + 4)[0]
        payload = data[off + 8:off + 8 + size]
        chunks.append([magic, payload])
        off += 8 + size
    return chunks


def find_chunk(chunks, magic):
    for c in chunks:
        if c[0] == magic:
            return c
    return None


# ---------------------------------------------------------------------------
# SKA1 (attachments) writer + rebaser -- new, mirrors write_skb1()'s style
# ---------------------------------------------------------------------------

def parse_ska1(payload):
    nAtt, oAtt, nLookup, oLookup = struct.unpack_from('<4I', payload, 0)
    atts = []
    for i in range(nAtt):
        p = oAtt + i * ATT_SIZE
        aid, bone, unknown, px, py, pz = struct.unpack_from(ATT_HDR_FMT, payload, p)
        interp, gseq, nts, ots, nkf, okf = struct.unpack_from(ms.TRACK_HDR_FMT, payload, p + ATT_HDR_SIZE)
        ts = [list(struct.unpack_from('<%dI' % n, payload, o)) if n else []
              for n, o in (struct.unpack_from('<ii', payload, ots + j * 8) for j in range(nts))] if nts else []
        kf = [list(struct.unpack_from('<%dB' % n, payload, o)) if n else []
              for n, o in (struct.unpack_from('<ii', payload, okf + j * 8) for j in range(nkf))] if nkf else []
        atts.append({
            'id': aid, 'bone': bone, 'unknown': unknown, 'position': (px, py, pz),
            'interp': interp, 'gseq': gseq, 'timestamps': ts, 'keyframes': kf,
        })
    lookup = list(struct.unpack_from('<%dh' % nLookup, payload, oLookup)) if nLookup else []
    return {'attachments': atts, 'lookup': lookup}


def write_ska1(ska1):
    atts, lookup = ska1['attachments'], ska1['lookup']
    n = len(atts)
    HDR = 16
    oAtt = HDR
    oLookup = oAtt + n * ATT_SIZE

    out = bytearray(oLookup + 2 * len(lookup))
    struct.pack_into('<4I', out, 0, n, oAtt if n else 0, len(lookup), oLookup if lookup else 0)
    if lookup:
        struct.pack_into('<%dh' % len(lookup), out, oLookup, *lookup)

    def alloc(nbytes):
        off = len(out)
        out.extend(b'\x00' * nbytes)
        return off

    for ai, att in enumerate(atts):
        p = oAtt + ai * ATT_SIZE
        struct.pack_into(ATT_HDR_FMT, out, p, att['id'], att['bone'], att['unknown'], *att['position'])

        ts, kf = att['timestamps'], att['keyframes']
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
                voff = alloc(len(vals)) if vals else 0
                if vals:
                    struct.pack_into('<%dB' % len(vals), out, voff, *vals)
                struct.pack_into('<ii', out, desc_off + i * 8, len(vals), voff)
            okf, nkf = desc_off, len(kf)
        else:
            okf, nkf = 0, 0

        struct.pack_into(ms.TRACK_HDR_FMT, out, p + ATT_HDR_SIZE, att['interp'], att['gseq'], nts, ots, nkf, okf)

    return bytes(out)


def rebase_skb1(buf, base):
    """Patches every internal offset field of a write_skb1()-produced blob by +base, in place."""
    buf = bytearray(buf)
    # Python 2's struct.unpack_from() doesn't accept a bytearray (only str/buffer);
    # Python 3 has no such restriction. Reading from a fixed bytes snapshot works on
    # both, and is safe here because every read below happens strictly before any
    # write that could affect the same bytes (no read ever depends on our own
    # in-progress patches), so a snapshot never goes stale mid-function.
    ro = bytes(buf)
    n, ofsBones, nKBL, ofsKBL = struct.unpack_from('<4I', ro, 0)
    if n:
        struct.pack_into('<I', buf, 4, ofsBones + base)
    if nKBL:
        struct.pack_into('<I', buf, 12, ofsKBL + base)

    for bi in range(n):
        bone_off = ofsBones + bi * ms.BONE_SIZE
        tpos = bone_off + ms.BONE_HDR_SIZE
        for _ in range(3):
            interp, gseq, nts, ots, nkf, okf = struct.unpack_from(ms.TRACK_HDR_FMT, ro, tpos)
            if nts:
                for i in range(nts):
                    dpos = ots + i * 8
                    dn, do = struct.unpack_from('<ii', ro, dpos)
                    if dn:
                        struct.pack_into('<i', buf, dpos + 4, do + base)
                struct.pack_into('<i', buf, tpos + 8, ots + base)
            if nkf:
                for i in range(nkf):
                    dpos = okf + i * 8
                    dn, do = struct.unpack_from('<ii', ro, dpos)
                    if dn:
                        struct.pack_into('<i', buf, dpos + 4, do + base)
                struct.pack_into('<i', buf, tpos + 16, okf + base)
            tpos += ms.TRACK_HDR_SIZE
    return bytes(buf)


def rebase_ska1(buf, base):
    buf = bytearray(buf)
    ro = bytes(buf)  # see note in rebase_skb1() re: Python 2 struct.unpack_from()
    n, oAtt, nLookup, oLookup = struct.unpack_from('<4I', ro, 0)
    if n:
        struct.pack_into('<I', buf, 4, oAtt + base)
    if nLookup:
        struct.pack_into('<I', buf, 12, oLookup + base)

    for ai in range(n):
        tpos = oAtt + ai * ATT_SIZE + ATT_HDR_SIZE
        interp, gseq, nts, ots, nkf, okf = struct.unpack_from(ms.TRACK_HDR_FMT, ro, tpos)
        if nts:
            for i in range(nts):
                dpos = ots + i * 8
                dn, do = struct.unpack_from('<ii', ro, dpos)
                if dn:
                    struct.pack_into('<i', buf, dpos + 4, do + base)
            struct.pack_into('<i', buf, tpos + 8, ots + base)
        if nkf:
            for i in range(nkf):
                dpos = okf + i * 8
                dn, do = struct.unpack_from('<ii', ro, dpos)
                if dn:
                    struct.pack_into('<i', buf, dpos + 4, do + base)
            struct.pack_into('<i', buf, tpos + 16, okf + base)
    return bytes(buf)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

# M2Header field offsets (relative to MD20 magic), version 260+ layout
OFS_GLOBAL_LOOPS = 0x14
OFS_SEQUENCES = 0x1C
OFS_SEQ_LOOKUP = 0x24
OFS_BONES = 0x2C
OFS_BONE_LOOKUP = 0x34


def merge_skel_into_m2(m2_path, skel_path, out_path):
    m2_chunks = load_m2_chunks(m2_path)
    md21 = find_chunk(m2_chunks, 'MD21')
    if md21 is None:
        raise ValueError("%s has no MD21 chunk -- doesn't look like a chunked (Legion+) .m2" % m2_path)
    md20 = bytearray(md21[1])

    for field, name in ((OFS_GLOBAL_LOOPS, 'global_loops'), (OFS_SEQUENCES, 'sequences'),
                         (OFS_BONES, 'bones'), (OFS_BONE_LOOKUP, 'boneIndicesById')):
        c, o = struct.unpack_from('<II', md21[1], field)  # md21[1]: original bytes, not yet mutated
        if c or o:
            print("  [warn] %s: %s array is not empty (count=%d, offset=%d) -- "
                  "this tool assumes an empty array to safely append without "
                  "reshuffling existing data. Aborting to avoid corrupting it."
                  % (m2_path, name, c, o))
            raise ValueError("%s array not empty, refusing to overwrite" % name)

    skel_chunks = ms.load(skel_path)
    sks1 = ms.parse_sks1(skel_chunks['SKS1'])
    skb1 = ms.parse_skb1(skel_chunks['SKB1'])
    ska1 = parse_ska1(skel_chunks['SKA1']) if 'SKA1' in skel_chunks else {'attachments': [], 'lookup': []}

    unembedded = [a for a in sks1['anims'] if not (struct.unpack_from('<I', a['raw'], 0x0C)[0] & 0x20)]
    if unembedded:
        print("  [warn] %d of %d animations in %s are NOT flagged embedded (flags & 0x20 == 0). "
              "Once folded into the .m2 (no more .skel/AFID to fall back on), the client will look "
              "for old-style raw .anim files named after THIS .m2's filename for these -- run the "
              "'bake .anim into .skel' step first for a fully self-contained result if that's not "
              "what you want." % (len(unembedded), len(sks1['anims']), skel_path))
        for a in unembedded[:10]:
            print("    - animID=%d subID=%d" % (a['animID'], a['subID']))

    base = len(md20)

    # global_loops: reuse write_sks1's own layout, but we only actually want the
    # global_loops sub-array's bytes/offset -- simplest is to write the whole
    # SKS1-style blob (it has no internal offsets needing rebasing) and read its
    # own header back to find where each piece landed.
    sks1_blob = ms.write_sks1(sks1)
    nGS, oGS, nAnim, oAnim, nLookup, oLookup, _, _ = struct.unpack_from('<8I', sks1_blob, 0)
    seq_base = base
    md20 += sks1_blob

    bones_base = len(md20)
    skb1_raw = ms.write_skb1(skb1)
    n_b, ofsBones_l, nKBL_l, ofsKBL_l = struct.unpack_from('<4I', skb1_raw, 0)
    skb1_blob = rebase_skb1(skb1_raw, bones_base)
    md20 += skb1_blob

    att_base = len(md20)
    ska1_raw = write_ska1(ska1)
    nAtt_l, oAtt_l, nLookAtt_l, oLookAtt_l = struct.unpack_from('<4I', ska1_raw, 0)
    ska1_blob = rebase_ska1(ska1_raw, att_base)
    md20 += ska1_blob

    def set_arr(field, count, offset):
        struct.pack_into('<II', md20, field, count, offset if count else 0)

    set_arr(OFS_GLOBAL_LOOPS, nGS, seq_base + oGS if nGS else 0)
    set_arr(OFS_SEQUENCES, nAnim, seq_base + oAnim if nAnim else 0)
    set_arr(OFS_SEQ_LOOKUP, nLookup, seq_base + oLookup if nLookup else 0)
    set_arr(OFS_BONES, n_b, bones_base + ofsBones_l if n_b else 0)
    set_arr(OFS_BONE_LOOKUP, nKBL_l, bones_base + ofsKBL_l if nKBL_l else 0)

    OFS_ATTACHMENTS = 0xF0
    OFS_ATTACH_LOOKUP = 0xF8
    set_arr(OFS_ATTACHMENTS, nAtt_l, att_base + oAtt_l if nAtt_l else 0)
    set_arr(OFS_ATTACH_LOOKUP, nLookAtt_l, att_base + oLookAtt_l if nLookAtt_l else 0)

    print("  global_loops: %d entries at %d" % (nGS, seq_base + oGS if nGS else 0))
    print("  sequences: %d entries at %d" % (nAnim, seq_base + oAnim if nAnim else 0))
    print("  sequenceIdxHashById: %d entries at %d" % (nLookup, seq_base + oLookup if nLookup else 0))
    print("  bones: %d entries at %d" % (n_b, bones_base + ofsBones_l if n_b else 0))
    print("  boneIndicesById: %d entries at %d" % (nKBL_l, bones_base + ofsKBL_l if nKBL_l else 0))
    print("  attachments: %d entries at %d" % (nAtt_l, att_base + oAtt_l if nAtt_l else 0))
    print("  attachmentLookupTable: %d entries at %d" % (nLookAtt_l, att_base + oLookAtt_l if nLookAtt_l else 0))

    # rebuild the .m2: same top-level chunks, updated MD21 payload, SKID dropped
    out_chunks = []
    for magic, payload in m2_chunks:
        if magic == 'MD21':
            out_chunks.append(('MD21', bytes(md20)))
        elif magic == 'SKID':
            print("  removing SKID chunk (skeleton fileID) -- no longer needed")
            continue
        else:
            out_chunks.append((magic, payload))

    out_bytes = bytearray()
    for magic, payload in out_chunks:
        out_bytes += magic.encode('ascii')
        out_bytes += struct.pack('<I', len(payload))
        out_bytes += payload

    with open(out_path, 'wb') as f:
        f.write(out_bytes)
    print("Written: %s (%d bytes)" % (out_path, len(out_bytes)))


def main():
    if len(sys.argv) != 4:
        print("Uso: python3 merge_skel_into_m2.py <model.m2> <skeleton.skel> <out.m2>")
        sys.exit(1)
    merge_skel_into_m2(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == '__main__':
    main()
