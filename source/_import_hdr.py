# -*- coding: utf-8 -*-
"""把 F:/hdr 的素材按分类导入 D:/zcy/ai_ty/素材库/（HDRI 环境贴图 + 参考图）"""
import os, shutil, sys

SRC = 'F:/hdr'
DST = 'D:/zcy/ai_ty/素材库'
LIMIT = 90 * 1024 * 1024  # 90MB：GitHub API 单文件上限 100MB 留余量

# 素材计划：{cat, name, files: [src文件名...]}
# .tx 与源文件同组；>90MB 的文件不纳入（记录在 skipped）
PLAN = [
    ('HDRI', '15_beerse_living', ['15_beerse_living.hdr']),
    ('HDRI', 'Glazed_Patio', ['Glazed Patio.exr', 'Glazed Patio.tx']),
    ('HDRI', 'HighwayOverpass', ['HighwayOverpass.hdr', 'HighwayOverpass.tx']),
    ('HDRI', 'Panorama', ['Panorama.exr']),
    ('HDRI', 'Studio_06', ['Studio 06.exr']),
    ('HDRI', 'Studio_Black_Soft', ['Studio Black Soft.exr']),
    ('HDRI', 'Studio_Tomoco', ['Studio Tomoco.exr']),
    ('HDRI', 'studio_0.5_Utility_sRGB', ['studio_0.5 Utility - Linear - sRGB .exr']),
    ('HDRI', 'autumn_field_puresky_4k', ['autumn_field_puresky_4k.exr']),
    ('HDRI', 'belfast_sunset_4k', ['belfast_sunset_4k.exr']),
    ('HDRI', 'belfast_sunset_puresky_4k', ['belfast_sunset_puresky_4k.exr']),
    ('HDRI', 'boma_4k', ['boma_4k.exr']),
    ('HDRI', 'carb_01_L', ['carb_01_L.hdr', 'carb_01_L.tx']),
    ('HDRI', 'christmas_photo_studio_01_4k', ['christmas_photo_studio_01_4k.exr']),
    ('HDRI', 'circus_arena_4k', ['circus_arena_4k.exr']),
    ('HDRI', 'country_club_4k', ['country_club_4k.exr']),
    ('HDRI', 'industrial_sunset_02_puresky_4k', ['industrial_sunset_02_puresky_4k.exr']),
    ('HDRI', 'kloppenheim_02_puresky_4k', ['kloppenheim_02_puresky_4k.exr', 'kloppenheim_02_puresky_4k_1.tx']),
    ('HDRI', 'kloppenheim_06_puresky_4k', ['kloppenheim_06_puresky_4k.exr']),
    ('HDRI', 'lenong_2_4k', ['lenong_2_4k.exr']),
    ('HDRI', 'lonely_road_afternoon_puresky_4k', ['lonely_road_afternoon_puresky_4k.exr']),
    ('HDRI', 'mirrored_hall_4k', ['mirrored_hall_4k.exr']),
    ('HDRI', 'night', ['night.exr']),
    ('HDRI', 'outdoor_chapel_4k', ['outdoor_chapel_4k.exr']),
    ('HDRI', 'pillars_4k', ['pillars_4k.exr']),
    ('HDRI', 'pretville_cinema_4k', ['pretville_cinema_4k.exr']),
    ('HDRI', 'qwantani_dusk_1_puresky_4k', ['qwantani_dusk_1_puresky_4k.exr']),
    ('HDRI', 'qwantani_dusk_2_puresky_4k', ['qwantani_dusk_2_puresky_4k.exr']),
    ('HDRI', 'rosendal_park_sunset_puresky_4k', ['rosendal_park_sunset_puresky_4k.exr']),
    ('HDRI', 'school_hall_4k', ['school_hall_4k.exr']),
    ('HDRI', 'signal_hill_sunrise_4k', ['signal_hill_sunrise_4k.exr']),
    ('HDRI', 'studio_small_09_4k', ['studio_small_09_4k.exr']),
    ('HDRI', 'syferfontein_18d_clear_puresky_4k', ['syferfontein_18d_clear_puresky_4k.exr']),
    ('HDRI', 'syferfontein_1d_clear_puresky_4k', ['syferfontein_1d_clear_puresky_4k.exr']),
    ('HDRI', 'the_sky_is_on_fire_4k', ['the_sky_is_on_fire_4k.exr', 'the_sky_is_on_fire_4k_Utility - Linear - Rec.709_ACEScg.exr.tx']),
    ('HDRI', 'venice_sunset_4k', ['venice_sunset_4k.exr']),
    ('HDRI', 'wasteland_clouds_puresky_4k', ['wasteland_clouds_puresky_4k.exr']),
    ('HDRI', 'aces_p', ['aces/p.exr']),
    ('参考图', 'OIP_C', ['OIP-C (1).jpg', 'OIP-C.jpg']),
    ('参考图', 'main_参考图', ['main.jpg', 'main.webp']),
]

# swatch 缩略图映射：swatch文件名 -> 素材名
SWATCH_MAP = {
    'belfast_sunset_4k.exr_hcm.swatch': 'belfast_sunset_4k',
    'carb_01_L.hdr_hcm.swatch': 'carb_01_L',
    'Glazed Patio.exr_hcm.swatch': 'Glazed_Patio',
    'kloppenheim_02_puresky_4k_1.exr_hcm.swatch': 'kloppenheim_02_puresky_4k',
    'OIP-C (1).jpg_hcm.swatch': 'OIP_C',
    'Panorama.exr_hcm.swatch': 'Panorama',
    'qwantani_dusk_1_puresky_4k.exr_hcm.swatch': 'qwantani_dusk_1_puresky_4k',
    'studio_small_09_4k.exr_hcm.swatch': 'studio_small_09_4k',
}

skipped = []
total_in = 0
for cat, name, files in PLAN:
    out_dir = os.path.join(DST, cat, name)
    os.makedirs(out_dir, exist_ok=True)
    desc_parts = []
    for fn in files:
        src = os.path.join(SRC, fn)
        if not os.path.exists(src):
            print(f'  MISSING: {fn}')
            continue
        size = os.path.getsize(src)
        if size > LIMIT:
            skipped.append((fn, size))
            continue
        shutil.copy2(src, os.path.join(out_dir, os.path.basename(fn)))
        total_in += size
        desc_parts.append(f'{fn}: {size/1024/1024:.1f} MB')
    with open(os.path.join(out_dir, '说明.txt'), 'w', encoding='utf-8') as f:
        f.write(f'{cat}素材「{name}」\n')
        f.write('文件：\n' + '\n'.join('  - ' + p for p in desc_parts) + '\n')
        f.write('来源: F:/hdr\n导入日期: 2026-09-21\n')

# 参考图 jpg 直接用 PIL 生成缩略图
try:
    from PIL import Image
    for jpg, asset in [('OIP-C (1).jpg', 'OIP_C')]:
        src = os.path.join(SRC, jpg)
        if os.path.exists(src):
            im = Image.open(src).convert('RGBA')
            im.thumbnail((400, 300))
            im.save(os.path.join(DST, '参考图', asset, '缩略图.png'))
            print(f'  thumb(PIL): {asset}')
except Exception as e:
    print(f'  PIL thumb fail: {e}')

# swatch 缩略图用 Maya MImage 解码（FOR4 CIMG 是 Maya 私有格式）
swatch_dir = os.path.join(SRC, '.mayaSwatches')
done_sw = 0
try:
    import maya.standalone
    maya.standalone.initialize(name='python')
    import maya.OpenMaya as om
    for sw, asset in SWATCH_MAP.items():
        sp = os.path.join(swatch_dir, sw)
        out = os.path.join(DST, 'HDRI', asset, '缩略图.png')
        if not os.path.exists(sp) or not os.path.isdir(os.path.dirname(out)):
            continue
        try:
            img = om.MImage()
            img.readFromFile(sp)
            img.writeToFile(out, 'png')
            done_sw += 1
            print(f'  thumb(swatch): {asset}')
        except Exception as e:
            print(f'  swatch fail {asset}: {e}')
except Exception as e:
    print(f'  MImage init fail: {e}')

print(f'\n导入完成: {len(PLAN)} 个素材, 共 {total_in/1024/1024/1024:.2f} GB')
if skipped:
    print(f'\n跳过 {len(skipped)} 个文件 (>90MB 或不存在):')
    for fn, size in skipped:
        print(f'  - {fn}: {size/1024/1024:.1f} MB')
print(f'缩略图: {done_sw} 个 swatch + PIL 参考图')
