from __future__ import annotations

import hashlib
from typing import Any


HERB_MODEL_REVISION = "tcm-herb-models-v1"


HERB_MODELS: tuple[dict[str, Any], ...] = (
    {
        "id": "ginseng",
        "name": "人参",
        "pinyin": "renshen",
        "category": "根及根茎类",
        "medicinalPart": "干燥根和根茎",
        "features": ["主根呈纺锤形或圆柱形", "表面黄白色并见纵皱纹", "根茎部常见芦头与凹窝状茎痕"],
        "materials": ["01_Ginseng"],
    },
    {
        "id": "eucommia",
        "name": "杜仲",
        "pinyin": "duzhong",
        "category": "皮类",
        "medicinalPart": "干燥树皮",
        "features": ["呈板片状或两边稍内卷", "外表面灰棕色、内表面紫褐色", "折断时可见细密银白色弹性胶丝"],
        "materials": ["EucommiaBark"],
    },
    {
        "id": "angelica",
        "name": "当归",
        "pinyin": "danggui",
        "category": "根及根茎类",
        "medicinalPart": "干燥根",
        "features": ["根头、主根和支根层次较明显", "表面黄棕色并有纵皱纹", "断面黄白或淡黄棕色并具浓郁香气"],
        "materials": ["Angelica_Low"],
    },
    {
        "id": "forsythia",
        "name": "连翘",
        "pinyin": "lianqiao",
        "category": "果实种子类",
        "medicinalPart": "干燥果实",
        "features": ["呈长卵形至卵形", "表面有不规则纵皱纹和多数突起小斑点", "顶端常开裂成两瓣"],
        "materials": ["10_ForsythiaFruit_A_Low", "10_ForsythiaFruit_B_Low", "10_ForsythiaFruit_C_Low"],
    },
    {
        "id": "gardenia",
        "name": "栀子",
        "pinyin": "zhizi",
        "category": "果实种子类",
        "medicinalPart": "干燥成熟果实",
        "features": ["呈长卵圆形或椭圆形", "表面红黄色至棕红色", "具六条翅状纵棱，顶端残存萼片"],
        "materials": ["11_CapeJasmineFruit_A", "11_CapeJasmineFruit_B", "11_CapeJasmineFruit_Inside", "11_CapeJasmineFruit_Shield"],
    },
    {
        "id": "scrophularia",
        "name": "玄参",
        "pinyin": "xuanshen",
        "category": "根及根茎类",
        "medicinalPart": "干燥根",
        "features": ["呈类圆柱形并略弯曲", "表面灰黄色至灰褐色且有纵沟", "质坚实，断面黑色并微有光泽"],
        "materials": ["15_ScrophulariaRoot"],
    },
    {
        "id": "inula",
        "name": "旋覆花",
        "pinyin": "xuanfuhua",
        "category": "花类",
        "medicinalPart": "干燥头状花序",
        "features": ["花序呈扁球形或类球形", "总苞片多层、覆瓦状排列", "舌状花黄色并位于外围"],
        "materials": ["22_InulaFlower_Low", "22_InulaFlowerB_Low"],
    },
    {
        "id": "amomum",
        "name": "砂仁",
        "pinyin": "sharen",
        "category": "果实种子类",
        "medicinalPart": "干燥成熟果实",
        "features": ["果实呈椭圆形或卵圆形", "表面棕褐色并有密生刺状突起", "果皮内分三室，种子团具浓烈芳香"],
        "materials": ["35_AmomumFruit_Full_Low", "35_AmomumFruit_core.002", "35_AmomumFruit_shield.001"],
    },
    {
        "id": "poria",
        "name": "茯苓",
        "pinyin": "fuling",
        "category": "菌藻类",
        "medicinalPart": "干燥菌核",
        "features": ["完整菌核形状不一，切片多为块片状", "外皮棕褐至黑褐色", "内部白色或淡粉红色，质细腻"],
        "materials": ["36_Poria_Low.001"],
    },
    {
        "id": "cinnamon",
        "name": "肉桂",
        "pinyin": "rougui",
        "category": "皮类",
        "medicinalPart": "干燥树皮",
        "features": ["呈槽状或卷筒状", "外表面灰棕色，内表面红棕色", "断面颗粒性，气香浓烈、味甜辣"],
        "materials": ["37_Cinnamon_A_Low", "37_Cinnamon_B_Low", "37_Cinnamon_C_Low.001"],
    },
    {
        "id": "tangerine-peel",
        "name": "陈皮",
        "pinyin": "chenpi",
        "category": "果实种子类",
        "medicinalPart": "干燥成熟果皮",
        "features": ["常剥成数瓣并呈不规则片状", "外表面橙红或红棕色，密布凹下油点", "内表面黄白色并呈海绵状"],
        "materials": ["TangerinePeel.001"],
    },
    {
        "id": "chuanxiong",
        "name": "川芎",
        "pinyin": "chuanxiong",
        "category": "根及根茎类",
        "medicinalPart": "干燥根茎",
        "features": ["呈不规则结节状拳形团块", "表面黄褐色并有隆起轮节", "断面黄白色，可见波状环纹和油点"],
        "materials": ["41_ChuanxiongRhizome"],
    },
    {
        "id": "red-sage",
        "name": "丹参",
        "pinyin": "danshen",
        "category": "根及根茎类",
        "medicinalPart": "干燥根和根茎",
        "features": ["根呈长圆柱形并常有分枝", "表面棕红或暗棕红色，具纵皱纹", "老根外皮疏松呈鳞片状，断面黄白或棕色"],
        "materials": ["42_RedSageRoot_A", "42_RedSageRoot_B", "42_RedSageRoot_C"],
    },
    {
        "id": "notoginseng",
        "name": "三七",
        "pinyin": "sanqi",
        "category": "根及根茎类",
        "medicinalPart": "干燥根和根茎",
        "features": ["主根呈类圆锥形或圆柱形", "表面灰黄或灰褐色，有断续纵皱纹", "顶端可见茎痕，质坚实"],
        "materials": ["44_Notoginseng_Low"],
    },
    {
        "id": "ox-gallstone",
        "name": "牛黄",
        "pinyin": "niuhuang",
        "category": "动物类",
        "medicinalPart": "牛的干燥胆结石",
        "features": ["多呈卵形、类球形或不规则形", "表面黄红至棕黄色，细腻而略有光泽", "断面可见紧密细致的同心层纹"],
        "materials": ["45_OxGallstone_Low"],
    },
    {
        "id": "hawthorn",
        "name": "山楂",
        "pinyin": "shanzha",
        "category": "果实种子类",
        "medicinalPart": "干燥成熟果实",
        "features": ["多加工成圆形横切片", "外皮红色并有细皱纹与灰白小斑点", "果肉深黄至浅棕色，内有硬核"],
        "materials": ["48_HawthornFruit_A_Low", "48_HawthornFruit_B_Low", "Default_OBJ.001"],
    },
    {
        "id": "pumpkin-seed",
        "name": "南瓜子",
        "pinyin": "nanguazi",
        "category": "果实种子类",
        "medicinalPart": "干燥成熟种子",
        "features": ["呈扁椭圆形，一端稍尖", "表面黄白或淡黄绿色", "边缘可见浅色隆起种脊"],
        "materials": ["Material", "Material.001"],
    },
    {
        "id": "dendrobium",
        "name": "石斛",
        "pinyin": "shihu",
        "category": "茎木类",
        "medicinalPart": "新鲜或干燥茎",
        "features": ["茎呈圆柱形或扁圆柱形", "表面黄绿色至金黄色，有纵沟", "节部明显，质实而易折断"],
        "materials": ["HerbaDendrobii_Low_B.001", "HerbaDendrobii_Low_C.001"],
    },
    {
        "id": "pilose-antler",
        "name": "鹿茸",
        "pinyin": "lurong",
        "category": "动物类",
        "medicinalPart": "未骨化密生茸毛的幼角",
        "features": ["呈圆柱状分枝", "外皮红棕或棕色并密生细茸毛", "锯口外围骨质、中部可见蜂窝状细孔"],
        "materials": ["Low.001"],
    },
    {
        "id": "prunella",
        "name": "夏枯草",
        "pinyin": "xiakucao",
        "category": "全草及其他类",
        "medicinalPart": "干燥果穗",
        "features": ["果穗呈圆柱形或略扁", "表面淡棕至棕红色", "宿萼呈覆瓦状排列，先端有短尖"],
        "materials": ["PrunellaVulgaris.001", "PrunellaVulgaris_Long.001"],
    },
)


def public_herb_model_catalog() -> list[dict[str, Any]]:
    catalog = []
    for herb in HERB_MODELS:
        item = {key: value for key, value in herb.items() if key != "materials"}
        item.update(
            {
                "modelUrl": f"/herb-models/models/{herb['id']}.obj",
                "materialTextures": {
                    material: f"/herb-models/textures/{material}.webp"
                    for material in herb["materials"]
                },
            }
        )
        catalog.append(item)
    return catalog


def find_herb_model(herb_id: object) -> dict[str, Any] | None:
    target = str(herb_id or "").strip().lower()
    return next((dict(item) for item in HERB_MODELS if item["id"] == target), None)


def select_learning_path_herb(profile_id: object, stage_id: object, node_id: object = "") -> dict[str, Any]:
    seed = f"{HERB_MODEL_REVISION}:{profile_id}:{stage_id}:{node_id}".encode("utf-8")
    index = int.from_bytes(hashlib.sha256(seed).digest()[:8], "big") % len(HERB_MODELS)
    return dict(HERB_MODELS[index])
