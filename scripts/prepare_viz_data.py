#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prepare data for the PhenoBench / PhenoKG interactive visualization sections
embedded in the PhenoLIP project page (index.html).

Outputs (relative to phenolip-webpage/):
  resources/data/phenobench_stats.json     - benchmark statistics
  resources/data/phenobench_samples.json   - curated image+caption+phenotype samples
  resources/phenobench_samples/*.jpg        - thumbnailed sample images
  resources/data/phenokg_graph.json         - compact HPO is_a tree (adjacency + names + counts)
  resources/data/phenokg_stats.json         - top-level system distribution + graph stats

Run with the project conda python:
  ~/miniconda3/envs/mm/bin/python PhenoLIP_Project/phenolip-webpage/scripts/prepare_viz_data.py
"""
import csv
import json
import ast
import os
import sys
from collections import Counter, defaultdict, deque

ROOT = "/mnt/petrelfs/liangcheng/RareVisual"
WEB = os.path.join(ROOT, "PhenoLIP_Project", "phenolip-webpage")
CSV_PATH = os.path.join(ROOT, "code_stage6/open_clip/data/testdata.csv")
HPO_PATH = os.path.join(ROOT, "data/hpo/hp.json")

DATA_OUT = os.path.join(WEB, "resources", "data")
IMG_OUT = os.path.join(WEB, "resources", "phenobench_samples")
os.makedirs(DATA_OUT, exist_ok=True)
os.makedirs(IMG_OUT, exist_ok=True)

csv.field_size_limit(10 ** 7)

PHENO_ABNORMALITY = "HP:0000118"  # root of "Phenotypic abnormality" subtree


def norm_id(uri):
    """http://purl.obolibrary.org/obo/HP_0000118 -> HP:0000118"""
    if not uri:
        return ""
    tail = uri.rsplit("/", 1)[-1]
    return tail.replace("HP_", "HP:")


# --------------------------------------------------------------------------- #
# 1. Parse PhenoBench testdata.csv
# --------------------------------------------------------------------------- #
def parse_phenobench():
    rows = []
    pheno_counter = Counter()
    caplen = []
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            cap = (row.get("caption") or "").strip()
            ip = (row.get("image_path") or "").strip()
            fm = row.get("full_matches") or ""
            try:
                matches = ast.literal_eval(fm) if fm else []
            except Exception:
                matches = []
            names = []
            for m in matches:
                if isinstance(m, (list, tuple)) and m:
                    names.append(str(m[0]))
            for nm in names:
                pheno_counter[nm] += 1
            caplen.append(len(cap.split()))
            rows.append({"image_path": ip, "caption": cap, "phenotypes": names})
    return rows, pheno_counter, caplen


def caption_len_histogram(caplen):
    bins = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50),
            (50, 70), (70, 100), (100, 150), (150, 10 ** 9)]
    labels = ["0-10", "10-20", "20-30", "30-40", "40-50",
              "50-70", "70-100", "100-150", "150+"]
    counts = [0] * len(bins)
    for n in caplen:
        for i, (lo, hi) in enumerate(bins):
            if lo <= n < hi:
                counts[i] += 1
                break
    return [{"range": l, "count": c} for l, c in zip(labels, counts)]


def build_phenobench_stats(rows, pheno_counter, caplen):
    stats = {
        "total_pairs": len(rows),
        "unique_phenotypes": len(pheno_counter),
        "avg_caption_words": round(sum(caplen) / max(len(caplen), 1), 1),
        "max_caption_words": max(caplen) if caplen else 0,
        "singleton_phenotypes": sum(1 for v in pheno_counter.values() if v == 1),
        "top_phenotypes": [{"name": n, "count": c}
                           for n, c in pheno_counter.most_common(25)],
        "caption_len_hist": caption_len_histogram(caplen),
    }
    return stats


def curate_samples(rows, pheno_counter, per_pheno=4, n_featured=48,
                   thumb_px=260, quality=80):
    """For every phenotype, keep up to `per_pheno` representative samples so the
    gallery can show the samples behind any clicked PhenoKG node. Thumbnails are
    de-duplicated by source path (stable hashed filename) into
    resources/phenobench_samples/.

    Returns (featured, by_phenotype):
      featured      : list of one sample per top phenotype (default gallery view)
      by_phenotype  : {phenotype_name: [ {image, caption, phenotypes}, ... ]}
    """
    import hashlib
    import glob
    try:
        from PIL import Image
        have_pil = True
    except Exception as e:
        print("WARN: Pillow not available (%s); copying originals instead" % e)
        have_pil = False
    import shutil

    # clear stale thumbnails so we don't leave orphans
    for old in glob.glob(os.path.join(IMG_OUT, "*.jpg")):
        try:
            os.remove(old)
        except Exception:
            pass

    # rows grouped by each phenotype tag (not just the primary one)
    by_tag = defaultdict(list)
    for r in rows:
        for ph in r["phenotypes"]:
            by_tag[ph].append(r)

    # pick up to `per_pheno` rows per phenotype (existing image, sane caption len)
    selected = {}   # phenotype -> [rows]
    needed = {}     # src_path -> out_filename
    for ph, lst in by_tag.items():
        lst = sorted(lst, key=lambda r: (not os.path.exists(r["image_path"]),
                                         abs(len(r["caption"].split()) - 28)))
        keep = []
        for r in lst:
            if not os.path.exists(r["image_path"]):
                continue
            keep.append(r)
            h = hashlib.md5(r["image_path"].encode("utf-8")).hexdigest()[:12]
            needed[r["image_path"]] = "img_" + h + ".jpg"
            if len(keep) >= per_pheno:
                break
        if keep:
            selected[ph] = keep

    # thumbnail every needed source image once
    done, fail = 0, 0
    for src, out_name in needed.items():
        out_path = os.path.join(IMG_OUT, out_name)
        try:
            if have_pil:
                im = Image.open(src).convert("RGB")
                w, h = im.size
                scale = min(1.0, thumb_px / float(max(w, h)))
                if scale < 1.0:
                    im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))))
                im.save(out_path, "JPEG", quality=quality)
            else:
                shutil.copyfile(src, out_path)
            done += 1
        except Exception as e:
            fail += 1
            print("WARN: failed to process %s (%s)" % (src, e))

    def to_entry(r):
        return {
            "image": "resources/phenobench_samples/" + needed[r["image_path"]],
            "caption": r["caption"],
            "phenotypes": r["phenotypes"][:6],
        }

    by_phenotype = {}
    for ph, keep in selected.items():
        keep = [r for r in keep if r["image_path"] in needed
                and os.path.exists(os.path.join(IMG_OUT, needed[r["image_path"]]))]
        if keep:
            by_phenotype[ph] = [to_entry(r) for r in keep]

    # featured gallery: one sample per top phenotype (for the default view)
    featured = []
    for ph, _ in pheno_counter.most_common():
        if ph in by_phenotype:
            e = dict(by_phenotype[ph][0])
            e["primary"] = ph
            featured.append(e)
        if len(featured) >= n_featured:
            break

    print("PhenoBench: %d thumbnails (%d failed), %d phenotypes indexed, %d featured"
          % (done, fail, len(by_phenotype), len(featured)))
    return featured, by_phenotype


# --------------------------------------------------------------------------- #
# 2. Parse HPO graph -> PhenoKG compact tree
# --------------------------------------------------------------------------- #
def parse_hpo():
    with open(HPO_PATH) as f:
        data = json.load(f)
    graph = data["graphs"][0]

    id_to_name = {}
    deprecated = set()
    for node in graph.get("nodes", []):
        nid = norm_id(node.get("id", ""))
        lbl = node.get("lbl", "")
        if not nid.startswith("HP:"):
            continue
        if lbl:
            id_to_name[nid] = lbl
        meta = node.get("meta", {}) or {}
        if meta.get("deprecated"):
            deprecated.add(nid)

    children = defaultdict(set)   # parent -> children
    parents = defaultdict(set)    # child -> parents
    for edge in graph.get("edges", []):
        if edge.get("pred") == "is_a":
            c = norm_id(edge.get("sub", ""))
            p = norm_id(edge.get("obj", ""))
            if c.startswith("HP:") and p.startswith("HP:"):
                children[p].add(c)
                parents[c].add(p)
    return id_to_name, children, parents, deprecated


def descendants(root, children):
    seen = set()
    dq = deque([root])
    while dq:
        n = dq.popleft()
        for c in children.get(n, ()):
            if c not in seen:
                seen.add(c)
                dq.append(c)
    return seen


def build_phenokg(id_to_name, children, parents, pheno_counter):
    # phenotype-name -> HPO id (case-insensitive) for mapping PhenoBench counts
    name_to_id = {v.lower(): k for k, v in id_to_name.items()}
    img_count = defaultdict(int)
    matched_pb = 0
    for name, cnt in pheno_counter.items():
        hid = name_to_id.get(name.lower())
        if hid:
            img_count[hid] += cnt
            matched_pb += 1

    # restrict to "Phenotypic abnormality" subtree
    keep = descendants(PHENO_ABNORMALITY, children)
    keep.add(PHENO_ABNORMALITY)

    # subtree image counts (sum over descendants incl self)
    sub_img = {}

    def subtree_img(n, memo):
        if n in memo:
            return memo[n]
        total = img_count.get(n, 0)
        for c in children.get(n, ()):
            if c in keep:
                total += subtree_img(c, memo)
        memo[n] = total
        return total

    memo = {}
    for n in keep:
        subtree_img(n, memo)
    sub_img = memo

    # compact adjacency for frontend (only kept nodes)
    nodes = {}
    for n in keep:
        ch = sorted([c for c in children.get(n, ()) if c in keep])
        nodes[n] = {
            "name": id_to_name.get(n, n),
            "children": ch,
            "img": img_count.get(n, 0),          # direct PhenoBench images
            "sub_img": sub_img.get(n, 0),         # subtree PhenoBench images
            "n_desc": 0,                          # filled below
        }
    # descendant counts
    for n in keep:
        nodes[n]["n_desc"] = len(descendants(n, children) & keep)

    graph_out = {
        "root": PHENO_ABNORMALITY,
        "nodes": nodes,
    }

    # top-level systems = direct children of HP:0000118
    systems = []
    for s in sorted(children.get(PHENO_ABNORMALITY, ()),
                    key=lambda x: -nodes.get(x, {}).get("n_desc", 0)):
        if s not in keep:
            continue
        systems.append({
            "id": s,
            "name": id_to_name.get(s, s),
            "n_desc": nodes[s]["n_desc"],
            "sub_img": nodes[s]["sub_img"],
        })

    # graph-level depth (within phenotypic abnormality subtree)
    depth = {PHENO_ABNORMALITY: 0}
    dq = deque([PHENO_ABNORMALITY])
    maxd = 0
    while dq:
        n = dq.popleft()
        for c in children.get(n, ()):
            if c in keep and c not in depth:
                depth[c] = depth[n] + 1
                maxd = max(maxd, depth[c])
                dq.append(c)

    stats = {
        "kg_pairs": "524K+",
        "kg_phenotypes": "3,000+",
        "hpo_nodes_total": len(id_to_name),
        "phenotype_abnormality_nodes": len(keep),
        "is_a_edges": sum(len(v) for v in children.values()),
        "max_depth": maxd,
        "phenobench_mapped_phenotypes": matched_pb,
        "systems": systems,
    }
    return graph_out, stats


# --------------------------------------------------------------------------- #
def main():
    print("== PhenoBench ==")
    rows, pheno_counter, caplen = parse_phenobench()
    pb_stats = build_phenobench_stats(rows, pheno_counter, caplen)
    with open(os.path.join(DATA_OUT, "phenobench_stats.json"), "w") as f:
        json.dump(pb_stats, f, ensure_ascii=False, indent=1)
    print("  total_pairs=%d unique_phenotypes=%d"
          % (pb_stats["total_pairs"], pb_stats["unique_phenotypes"]))

    featured, by_pheno = curate_samples(rows, pheno_counter,
                                        per_pheno=4, n_featured=48)
    with open(os.path.join(DATA_OUT, "phenobench_featured.json"), "w") as f:
        json.dump(featured, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA_OUT, "phenobench_by_phenotype.json"), "w") as f:
        json.dump(by_pheno, f, ensure_ascii=False)

    print("== PhenoKG ==")
    id_to_name, children, parents, deprecated = parse_hpo()
    print("  HPO nodes=%d is_a edges=%d"
          % (len(id_to_name), sum(len(v) for v in children.values())))
    graph_out, kg_stats = build_phenokg(id_to_name, children, parents, pheno_counter)
    with open(os.path.join(DATA_OUT, "phenokg_graph.json"), "w") as f:
        json.dump(graph_out, f, ensure_ascii=False)
    with open(os.path.join(DATA_OUT, "phenokg_stats.json"), "w") as f:
        json.dump(kg_stats, f, ensure_ascii=False, indent=1)
    print("  phenotypic-abnormality nodes=%d max_depth=%d systems=%d"
          % (kg_stats["phenotype_abnormality_nodes"],
             kg_stats["max_depth"], len(kg_stats["systems"])))

    # drop the obsolete single-sample file if present
    old = os.path.join(DATA_OUT, "phenobench_samples.json")
    if os.path.exists(old):
        os.remove(old)

    # report sizes
    for fn in ["phenobench_stats.json", "phenobench_featured.json",
               "phenobench_by_phenotype.json", "phenokg_graph.json",
               "phenokg_stats.json"]:
        p = os.path.join(DATA_OUT, fn)
        if os.path.exists(p):
            print("  %-30s %8.1f KB" % (fn, os.path.getsize(p) / 1024.0))
    import subprocess
    try:
        sz = subprocess.check_output(["du", "-sh", IMG_OUT]).decode().split()[0]
        print("  thumbnails dir total            %s" % sz)
    except Exception:
        pass


if __name__ == "__main__":
    main()
