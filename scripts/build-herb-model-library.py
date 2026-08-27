from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from herb_model_catalog import HERB_MODELS, HERB_MODEL_REVISION, public_herb_model_catalog  # noqa: E402


def parse_mtl(path: Path) -> dict[str, Path]:
    textures: dict[str, Path] = {}
    material = ""
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line.startswith("newmtl "):
            material = line[7:].strip()
        elif material and line.startswith("map_Kd "):
            relative = line[7:].strip().replace("\\", "/")
            textures[material] = path.parent / relative
    return textures


def parse_obj(path: Path) -> tuple[list[str], list[str], list[str], list[tuple[str, list[str]]]]:
    vertices: list[str] = []
    texcoords: list[str] = []
    normals: list[str] = []
    faces: list[tuple[str, list[str]]] = []
    material = ""
    with path.open("r", encoding="utf-8", errors="ignore") as source:
        for raw_line in source:
            line = raw_line.strip()
            if line.startswith("v "):
                vertices.append(line)
            elif line.startswith("vt "):
                texcoords.append(line)
            elif line.startswith("vn "):
                normals.append(line)
            elif line.startswith("usemtl "):
                material = line[7:].strip()
            elif line.startswith("f ") and material:
                faces.append((material, line[2:].split()))
    return vertices, texcoords, normals, faces


def resolve_index(raw: str, length: int) -> int:
    value = int(raw)
    return value if value > 0 else length + value + 1


def split_face_token(token: str, lengths: tuple[int, int, int]) -> tuple[int, int | None, int | None]:
    parts = token.split("/")
    vertex = resolve_index(parts[0], lengths[0])
    texcoord = resolve_index(parts[1], lengths[1]) if len(parts) > 1 and parts[1] else None
    normal = resolve_index(parts[2], lengths[2]) if len(parts) > 2 and parts[2] else None
    return vertex, texcoord, normal


def write_herb_obj(
    output: Path,
    herb_id: str,
    materials: list[str],
    vertices: list[str],
    texcoords: list[str],
    normals: list[str],
    faces: list[tuple[str, list[str]]],
) -> dict[str, int]:
    selected = [(material, tokens) for material, tokens in faces if material in materials]
    if not selected:
        raise RuntimeError(f"No OBJ faces found for {herb_id}")

    parsed = [
        (material, [split_face_token(token, (len(vertices), len(texcoords), len(normals))) for token in tokens])
        for material, tokens in selected
    ]
    used_v = sorted({item[0] for _, face in parsed for item in face})
    used_vt = sorted({item[1] for _, face in parsed for item in face if item[1] is not None})
    used_vn = sorted({item[2] for _, face in parsed for item in face if item[2] is not None})
    v_map = {old: new for new, old in enumerate(used_v, start=1)}
    vt_map = {old: new for new, old in enumerate(used_vt, start=1)}
    vn_map = {old: new for new, old in enumerate(used_vn, start=1)}

    lines = [f"# {HERB_MODEL_REVISION}", f"o {herb_id}"]
    lines.extend(vertices[index - 1] for index in used_v)
    lines.extend(texcoords[index - 1] for index in used_vt)
    lines.extend(normals[index - 1] for index in used_vn)
    current_material = ""
    for material, face in parsed:
        if material != current_material:
            lines.append(f"usemtl {material}")
            lines.append("s 1")
            current_material = material
        tokens = []
        for vertex, texcoord, normal in face:
            if normal is not None:
                tokens.append(f"{v_map[vertex]}/{vt_map[texcoord] if texcoord is not None else ''}/{vn_map[normal]}")
            elif texcoord is not None:
                tokens.append(f"{v_map[vertex]}/{vt_map[texcoord]}")
            else:
                tokens.append(str(v_map[vertex]))
        lines.append("f " + " ".join(tokens))
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return {"vertices": len(used_v), "faces": len(selected)}


def convert_texture(source: Path, output: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        image.save(output, "WEBP", quality=78, method=6)


def build(source_dir: Path, output_dir: Path) -> dict[str, object]:
    obj_path = source_dir / "中药材.obj"
    mtl_path = source_dir / "中药材.mtl"
    if not obj_path.is_file() or not mtl_path.is_file():
        raise FileNotFoundError("Expected 中药材.obj and 中药材.mtl in the source directory")

    model_dir = output_dir / "models"
    texture_dir = output_dir / "textures"
    model_dir.mkdir(parents=True, exist_ok=True)
    texture_dir.mkdir(parents=True, exist_ok=True)
    source_textures = parse_mtl(mtl_path)
    vertices, texcoords, normals, faces = parse_obj(obj_path)
    material_names = {material for material, _ in faces}
    stats: dict[str, dict[str, int]] = {}

    for herb in HERB_MODELS:
        materials = list(herb["materials"])
        missing = [material for material in materials if material not in material_names]
        if missing:
            raise RuntimeError(f"Missing OBJ materials for {herb['id']}: {missing}")
        stats[herb["id"]] = write_herb_obj(
            model_dir / f"{herb['id']}.obj",
            herb["id"],
            materials,
            vertices,
            texcoords,
            normals,
            faces,
        )
        for material in materials:
            convert_texture(source_textures[material], texture_dir / f"{material}.webp")

    catalog = {
        "revision": HERB_MODEL_REVISION,
        "count": len(HERB_MODELS),
        "items": public_herb_model_catalog(),
        "build": stats,
    }
    (output_dir / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Split the supplied monolithic TCM model into per-herb web assets.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "img" / "herb-models")
    args = parser.parse_args()
    catalog = build(args.source.resolve(), args.output.resolve())
    model_bytes = sum(path.stat().st_size for path in (args.output / "models").glob("*.obj"))
    texture_bytes = sum(path.stat().st_size for path in (args.output / "textures").glob("*.webp"))
    print(json.dumps({"count": catalog["count"], "modelBytes": model_bytes, "textureBytes": texture_bytes}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
