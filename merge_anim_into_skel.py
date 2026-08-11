#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
merge_anim_into_skel.py — embeds one or more external chunked .anim files
(AFM2/AFSB) into a .skel, producing a .skel that no longer needs those
external .anim files for the animations that got embedded.

Mechanism (verified byte-for-byte against centaur2_male.skel +
centaur2_male0060-00.anim):

  For an animation NOT embedded in the .skel (M2Sequence.flags & 0x20 == 0,
  meaning the client loads it from a .anim file), SKB1 already contains
  correct-looking (count, offset) descriptor pairs for every bone's
  translation/rotation/scaling sub-block at that animation's index -- but
  the "offset" is relative to the *external* .anim file's AFSB chunk
  payload, not to SKB1's own payload.

  So embedding == re-reading those already-correct (count, offset) pairs
  against the external AFSB buffer instead of SKB1's own bytes, splicing
  the resulting real values into the in-memory bone tracks, then setting
  flags |= 0x20 on the SKS1 record and dropping the AFID entry. No changes
  to write_skb1()/write_sks1() are needed -- they already just serialize
  whatever is in the parsed dict.

Usage:
    python3 merge_anim_into_skel.py parent.skel out.skel anim1.anim [anim2.anim ...]
"""
from __future__ import print_function
import struct
import sys

import merge_skel as ms  # reuse chunk I/O + SKB1/SKS1 parse/write from the existing tool

SKS1_FLAGS_OFFSET = 0x0C
SKS1_EMBEDDED_FLAG = 0x20
SKS1_ALIAS_FLAG = 0x40  # M2Sequence.flags: this record is an alias of another (no own track data)


def anim_id_subid_from_filename(path):
    """
    Parses "...NNNN-SS.anim" per the documented naming convention
    ("%s%04d-%02d.anim" % (model_filename_without_extension, anim.id, anim.sub_anim_id)).
    AFM2's own payload does NOT start with a plain id/subID pair (verified:
    doesn't match AFID's expected values), so the filename is the reliable
    source -- and it's already cross-checked against AFID's fileID mapping
    in the .skel for this specific case (centaur2_male / animID 60).
    """
    import os
    stem = os.path.splitext(os.path.basename(path))[0]
    tail = stem[-7:]  # "NNNN-SS"
    if len(tail) != 7 or tail[4] != '-':
        raise ValueError(
            "%s: filename doesn't end in the expected NNNN-SS.anim pattern; "
            "can't determine animID/subID from it." % path
        )
    anim_id = int(tail[0:4])
    sub_id = int(tail[5:7])
    return anim_id, sub_id


def load_anim_afsb(path):
    """Returns (animID, subID, afsb_payload_bytes) for a chunked .anim file."""
    data = open(path, 'rb').read()
    off = 0
    chunks = {}
    while off < len(data):
        magic = data[off:off + 4].decode('ascii')
        size = struct.unpack_from('<I', data, off + 4)[0]
        chunks[magic] = data[off + 8:off + 8 + size]
        off += 8 + size

    if 'AFM2' not in chunks or 'AFSB' not in chunks:
        raise ValueError(
            "%s doesn't look like a chunked (.skel-based) .anim file "
            "(missing AFM2/AFSB chunks) -- it may be the older raw/legacy "
            "format instead, which this tool doesn't handle." % path
        )

    anim_id, sub_id = anim_id_subid_from_filename(path)
    return anim_id, sub_id, chunks['AFSB']


def reread_track_from_external(track, afsb, kind):
    """
    Re-derive a bone-track's timestamps/keyframes lists by re-reading the
    SAME (count, offset) pairs already present in `track`, but sourced from
    the external `afsb` buffer instead of the local SKB1 payload.
    NOTE: only the entries the caller tells us to re-source get touched;
    this function operates on a single already-sliced-out (n,o) pair set,
    see merge_anim_for_index() below for how it's actually driven.
    """
    raise NotImplementedError("see merge_anim_for_index")


def merge_anim_for_index(skb1, anim_index, afsb):
    """
    For every bone in skb1, re-read the translation/rotation/scaling
    sub-block at anim_index from `afsb` instead of trusting whatever was
    already parsed from the local SKB1 payload (which is garbage for
    externally-stored anims -- same offset, wrong buffer).
    """
    for bone in skb1['bones']:
        for comp, kind in (('translation', 'vec'), ('rotation', 'rot'), ('scaling', 'vec')):
            track = bone[comp]
            ts_list = track['timestamps']
            kf_list = track['keyframes']
            if anim_index >= len(ts_list):
                continue  # this bone's array is shorter than expected; leave alone

            n_ts = len(ts_list[anim_index]) if ts_list[anim_index] is not None else None
            # we don't have the raw (n,o) anymore post-parse, so re-derive using
            # the *values already read* only for their lengths, then re-fetch
            # from the correct buffer using the ORIGINAL offsets recomputed
            # from scratch -- see merge_skel_anim() which does this properly
            # by re-parsing SKB1 with raw offsets retained.
            pass  # placeholder -- real logic lives in merge_skel_anim() below


def parse_skb1_with_raw_offsets(payload):
    """
    Like ms.parse_skb1, but also keeps the raw (n, o) descriptor pairs
    per bone/channel/anim-index around, so we can re-fetch their VALUES
    from a different buffer (an external AFSB) when needed.
    """
    nBones, ofsBones, nKeyBoneLookup, ofsKeyBoneLookup = struct.unpack_from('<4I', payload, 0)
    bones = []
    pos = ofsBones
    for i in range(nBones):
        key_bone_id, flags, parent_bone, submesh_id, crc = struct.unpack_from(
            ms.BONE_HDR_FMT, payload, pos)
        p = pos + ms.BONE_HDR_SIZE
        comps = {}
        for comp, kind in (('translation', 'vec'), ('rotation', 'rot'), ('scaling', 'vec')):
            interp, gseq, nts, ots, nkf, okf = struct.unpack_from(ms.TRACK_HDR_FMT, payload, p)
            ts_pairs = [struct.unpack_from('<ii', payload, ots + j * 8) for j in range(nts)] if nts else []
            kf_pairs = [struct.unpack_from('<ii', payload, okf + j * 8) for j in range(nkf)] if nkf else []
            comps[comp] = {
                'interp': interp, 'gseq': gseq,
                'ts_pairs': ts_pairs, 'kf_pairs': kf_pairs,   # raw (n, o) pairs, per anim-index
                'kind': kind,
            }
            p += ms.TRACK_HDR_SIZE
        pivot = struct.unpack_from('<3f', payload, p)
        bones.append({
            'key_bone_id': key_bone_id, 'flags': flags, 'parent_bone': parent_bone,
            'submesh_id': submesh_id, 'crc': crc, 'pivot': pivot, 'comps': comps,
        })
        pos += ms.BONE_SIZE

    keybonelookup = []
    if ofsKeyBoneLookup:
        keybonelookup = list(struct.unpack_from('<%dh' % nKeyBoneLookup, payload, ofsKeyBoneLookup))

    return {'bones': bones, 'keybonelookup': keybonelookup}


def build_skb1_for_write(raw_skb1, local_payload, overrides):
    """
    Turn the raw-offset representation back into ms.write_skb1()'s expected
    shape: real timestamp/keyframe VALUE lists per bone/comp/anim-index.
    `overrides` is {anim_index: afsb_bytes} -- for those anim indices, the
    (n, o) pairs are resolved against afsb_bytes instead of local_payload.
    """
    bones_out = []
    for bone in raw_skb1['bones']:
        nb = {
            'key_bone_id': bone['key_bone_id'], 'flags': bone['flags'],
            'parent_bone': bone['parent_bone'], 'submesh_id': bone['submesh_id'],
            'crc': bone['crc'], 'pivot': bone['pivot'],
        }
        for comp, cdata in bone['comps'].items():
            kind = cdata['kind']
            ts_out, kf_out = [], []
            for idx, (n, o) in enumerate(cdata['ts_pairs']):
                buf = overrides.get(idx, local_payload)
                if n and 0 <= o and o + n * 4 <= len(buf):
                    ts_out.append(list(struct.unpack_from('<%dI' % n, buf, o)))
                else:
                    ts_out.append([] if n == 0 else None)  # None flags a bad/unreachable read
            for idx, (n, o) in enumerate(cdata['kf_pairs']):
                buf = overrides.get(idx, local_payload)
                if n and 0 <= o:
                    if kind == 'rot':
                        need = o + n * 8
                        if need <= len(buf):
                            kf_out.append([struct.unpack_from('<4H', buf, o + j * 8) for j in range(n)])
                        else:
                            kf_out.append(None)
                    else:
                        need = o + n * 12
                        if need <= len(buf):
                            kf_out.append([struct.unpack_from('<3f', buf, o + j * 12) for j in range(n)])
                        else:
                            kf_out.append(None)
                else:
                    kf_out.append([] if n == 0 else None)
            nb[comp] = {'interp': cdata['interp'], 'gseq': cdata['gseq'],
                        'timestamps': ts_out, 'keyframes': kf_out}
        bones_out.append(nb)
    return {'bones': bones_out, 'keybonelookup': raw_skb1['keybonelookup']}


SKS1_ALIASNEXT_OFFSET = 0x3E  # M2Sequence: uint16, direct index into the sequences array


def resolve_sequence_aliases(sks1, merged_skb1):
    """
    For every SKS1 entry marked as an alias (flags & 0x40) that isn't itself
    already embedded, follow the aliasNext chain (a direct array index, not
    an animID -- verified against real data: e.g. index 26 -> aliasNext 25,
    and index 25 is the real animID=60 entry with matching duration) to find
    a target that DOES have real embedded data (flags & 0x20). If one is
    found, copy that target's actual bone-track data (every bone, every
    channel) into the alias's own index slot, and set the alias's own
    flags |= 0x20.

    This matters because not every tool that reads a .skel implements the
    "flags & 0x20 unset + flags & 0x40 set -> follow aliasNext instead"
    fallback the game client uses (e.g. some importers just check flags &
    0x20 directly and go looking for an external .anim file that, for a
    pure alias, never existed in the first place). Giving the alias its own
    real copy of the data sidesteps that entirely, at the cost of a small
    amount of duplicated data.

    Only ever copies data pulled from a genuinely-embedded source -- never
    invents or forces anything, so this is safe to run unconditionally.
    """
    n = len(sks1['anims'])

    def flags_of(i):
        return struct.unpack_from('<I', sks1['anims'][i]['raw'], SKS1_FLAGS_OFFSET)[0]

    resolved, unresolved = [], []

    for idx in range(n):
        flags = flags_of(idx)
        if not (flags & SKS1_ALIAS_FLAG) or (flags & SKS1_EMBEDDED_FLAG):
            continue  # not an alias, or already has its own real/embedded data

        visited = set()
        cur = idx
        target = None
        for _ in range(32):  # generous hop limit; real chains seen so far are 1-2 hops
            nxt = struct.unpack_from('<H', sks1['anims'][cur]['raw'], SKS1_ALIASNEXT_OFFSET)[0]
            if nxt >= n or nxt in visited:
                break
            visited.add(nxt)
            if flags_of(nxt) & SKS1_EMBEDDED_FLAG:
                target = nxt
                break
            if not (flags_of(nxt) & SKS1_ALIAS_FLAG):
                break  # dead end: points at a non-alias entry with no data of its own either
            cur = nxt

        if target is None:
            unresolved.append(idx)
            continue

        for bone in merged_skb1['bones']:
            for comp in ('translation', 'rotation', 'scaling'):
                ts_list = bone[comp]['timestamps']
                kf_list = bone[comp]['keyframes']
                if idx < len(ts_list) and target < len(ts_list):
                    ts_list[idx] = list(ts_list[target])
                    kf_list[idx] = list(kf_list[target])

        a = sks1['anims'][idx]
        new_raw = bytearray(a['raw'])
        struct.pack_into('<I', new_raw, SKS1_FLAGS_OFFSET, flags | SKS1_EMBEDDED_FLAG)
        sks1['anims'][idx] = dict(a)
        sks1['anims'][idx]['raw'] = bytes(new_raw)
        resolved.append((idx, a['animID'], a['subID'], target,
                          sks1['anims'][target]['animID'] if target is not None else None))

    if resolved:
        print("  [alias-resolve] copied real track data into %d alias entries so they no longer "
              "need external .anim resolution:" % len(resolved))
        for idx, animid, subid, target, target_animid in resolved:
            print("    - index %d (animID=%d subID=%d) <- real data from index %d (animID=%d)"
                  % (idx, animid, subid, target, target_animid))
    if unresolved:
        print("  [alias-resolve] %d alias entries could not be resolved (their chain doesn't "
              "lead to any entry with real embedded data -- likely still needs its own .anim "
              "baked in, or baking the animation it ultimately points to will fix this too): %s"
              % (len(unresolved), unresolved))


def merge_skel_anim(skel_path, out_path, anim_paths, force_all_embedded=False):
    skel_chunks = ms.load(skel_path)
    skb1_payload = skel_chunks['SKB1']
    sks1 = ms.parse_sks1(skel_chunks['SKS1'])
    raw_skb1 = parse_skb1_with_raw_offsets(skb1_payload)

    overrides = {}          # anim_index -> afsb bytes
    embedded_animid_subid = set()

    for anim_path in anim_paths:
        anim_id, sub_id, afsb = load_anim_afsb(anim_path)
        matches = [i for i, a in enumerate(sks1['anims'])
                   if a['animID'] == anim_id and a['subID'] == sub_id]
        if not matches:
            raise ValueError(
                "%s: animID=%d subID=%d has no matching entry in the parent "
                ".skel's SKS1 -- can't merge an animation the skeleton "
                "doesn't know about." % (anim_path, anim_id, sub_id)
            )

        # If several entries share this (animID, subID) -- one real, plus one or
        # more aliases (flags & 0x40, no track data of their own, just point at
        # the real entry via aliasNext) -- the real track data only needs to be
        # spliced into ONE of them. Prefer a non-alias entry as that "primary"
        # if one exists among the matches; otherwise fall back to the first.
        def _flags_of(i):
            return struct.unpack_from('<I', sks1['anims'][i]['raw'], SKS1_FLAGS_OFFSET)[0]

        non_alias = [i for i in matches if not (_flags_of(i) & SKS1_ALIAS_FLAG)]
        primary_idx = non_alias[0] if non_alias else matches[0]

        print("  embedding animID=%d subID=%d -> SKS1 index %d (from %s)"
              % (anim_id, sub_id, primary_idx, anim_path))
        overrides[primary_idx] = afsb
        embedded_animid_subid.add((anim_id, sub_id))

        if len(matches) > 1:
            print("  %d other SKS1 entries share animID=%d subID=%d (aliases) -- "
                  "flagging them embedded too, without duplicating track data, "
                  "so the client doesn't look for an external .anim for them either: %s"
                  % (len(matches) - 1, anim_id, sub_id, [i for i in matches if i != primary_idx]))

        # flip the embedded flag (flags |= 0x20) on EVERY matching SKS1 record,
        # not just the one that got real track data -- an alias entry has no
        # track data of its own by design (it defers to aliasNext), but per the
        # file format's own rule ("no flag 0x20 == externally stored"), it still
        # needs flag 0x20 set once its target is embedded, or the client has no
        # way to know an external .anim isn't needed for it too.
        for idx in matches:
            raw = sks1['anims'][idx]['raw']
            flags = struct.unpack_from('<I', raw, SKS1_FLAGS_OFFSET)[0]
            if flags & SKS1_EMBEDDED_FLAG:
                print("  [info] animID=%d subID=%d (index %d) already has the "
                      "embedded flag set -- leaving as-is." % (anim_id, sub_id, idx))
                continue
            new_flags = flags | SKS1_EMBEDDED_FLAG
            new_raw = bytearray(raw)
            struct.pack_into('<I', new_raw, SKS1_FLAGS_OFFSET, new_flags)
            sks1['anims'][idx] = dict(sks1['anims'][idx])
            sks1['anims'][idx]['raw'] = bytes(new_raw)

    if force_all_embedded:
        forced = 0
        skipped_aliases = 0
        for idx, a in enumerate(sks1['anims']):
            raw = a['raw']
            flags = struct.unpack_from('<I', raw, SKS1_FLAGS_OFFSET)[0]
            if flags & SKS1_EMBEDDED_FLAG:
                continue
            if flags & SKS1_ALIAS_FLAG:
                # Genuine alias (flags & 0x40): has no track data of its own by
                # design -- its bone-track slots hold placeholder/sentinel
                # values (e.g. timestamp 0xFFFFFFFF), not real keyframes.
                # Forcing 0x20 here tells the client this record has real
                # embedded data, so it plays the sentinel placeholder directly
                # instead of following aliasNext to the real animation --
                # confirmed cause of animations running far longer than they
                # should (the sentinel timestamp is effectively "almost never
                # ends"). Leave these exactly as they were.
                skipped_aliases += 1
                continue
            new_raw = bytearray(raw)
            struct.pack_into('<I', new_raw, SKS1_FLAGS_OFFSET, flags | SKS1_EMBEDDED_FLAG)
            sks1['anims'][idx] = dict(a)
            sks1['anims'][idx]['raw'] = bytes(new_raw)
            forced += 1
        if forced:
            print("  [force-embedded] set flag 0x20 on %d additional SKS1 entries that had no "
                  "baked .anim data of their own (their track arrays are left exactly as they "
                  "were -- only the flag changes). Use this only if the normal alias handling "
                  "didn't fix playback; forcing the flag on a sequence that has neither real "
                  "embedded data nor a valid alias chain to one that does will make the client "
                  "think it has data when it doesn't, which can look wrong or worse than leaving "
                  "it flagged external." % forced)
        if skipped_aliases:
            print("  [force-embedded] left %d genuine alias entries (flags & 0x40) untouched -- "
                  "they have no track data of their own by design and forcing the embedded flag "
                  "on them causes the client to play placeholder/sentinel data instead of "
                  "following the alias chain." % skipped_aliases)

    merged_skb1 = build_skb1_for_write(raw_skb1, skb1_payload, overrides)

    # sanity: make sure nothing came back as None (== couldn't be read, would corrupt output)
    bad = 0
    for bi, bone in enumerate(merged_skb1['bones']):
        for comp in ('translation', 'rotation', 'scaling'):
            for kind, lst in (('ts', bone[comp]['timestamps']), ('kf', bone[comp]['keyframes'])):
                for i, v in enumerate(lst):
                    if v is None:
                        bad += 1
                        if bad <= 10:
                            print("  [warn] bone %d %s %s index %d: offset out of range, "
                                  "left empty instead of corrupting" % (bi, comp, kind, i))
                        lst[i] = []
    if bad:
        print("  [warn] %d sub-blocks could not be resolved (see above) -- "
              "output written anyway but review those bones/animations." % bad)

    resolve_sequence_aliases(sks1, merged_skb1)

    out_chunks = [ms.make_chunk('SKL1', skel_chunks['SKL1'])]
    out_chunks.append(ms.make_chunk('SKS1', ms.write_sks1(sks1)))
    out_chunks.append(ms.make_chunk('SKB1', ms.write_skb1(merged_skb1)))
    if 'SKA1' in skel_chunks:
        out_chunks.append(ms.make_chunk('SKA1', skel_chunks['SKA1']))

    # drop the now-embedded entries from AFID; keep the rest
    if 'AFID' in skel_chunks:
        afid = skel_chunks['AFID']
        n = len(afid) // 8
        kept = bytearray()
        for i in range(n):
            aid, sid, fid = struct.unpack_from('<HHI', afid, i * 8)
            if (aid, sid) in embedded_animid_subid:
                print("  removing AFID entry animID=%d subID=%d (fileID %d) -- now embedded"
                      % (aid, sid, fid))
                continue
            kept += afid[i * 8:i * 8 + 8]
        if kept:
            out_chunks.append(ms.make_chunk('AFID', bytes(kept)))

    if 'BFID' in skel_chunks:
        out_chunks.append(ms.make_chunk('BFID', skel_chunks['BFID']))

    result = b''.join(out_chunks)
    with open(out_path, 'wb') as f:
        f.write(result)
    print("Written: %s (%d bytes)" % (out_path, len(result)))
    return sks1, merged_skb1, embedded_animid_subid


def main():
    if len(sys.argv) < 4:
        print("Uso: python3 merge_anim_into_skel.py [--force-all-embedded] <parent.skel> <out.skel> <anim1.anim> [anim2.anim ...]")
        print("  --force-all-embedded: dopo l'incorporazione normale, forza il flag 0x20 (embedded)")
        print("                        su TUTTE le animazioni dello .skel, incluse quelle senza")
        print("                        un .anim incorporato o una catena alias valida. Da usare")
        print("                        solo se il comportamento normale non risolve i problemi di")
        print("                        riproduzione -- vedi l'avviso stampato quando viene usato.")
        sys.exit(1)
    args = sys.argv[1:]
    force_all_embedded = '--force-all-embedded' in args
    if force_all_embedded:
        args = [a for a in args if a != '--force-all-embedded']
    skel_path, out_path = args[0], args[1]
    anim_paths = args[2:]
    merge_skel_anim(skel_path, out_path, anim_paths, force_all_embedded=force_all_embedded)


if __name__ == '__main__':
    main()
