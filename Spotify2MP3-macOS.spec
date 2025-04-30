# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['spotify2media.py'],
    pathex=[],
    binaries=[],
    datas=[('ffmpeg/ffmpeg', 'ffmpeg'), ('yt-dlp/yt-dlp', 'yt-dlp'), ('config.json', '.'), ('icon.icns', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Spotify2MP3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Spotify2MP3',
)
app = BUNDLE(
    coll,
    name='Spotify2MP3.app',
    icon='icon.icns',
    bundle_identifier=None,
)
