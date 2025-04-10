# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('gradio_client')
datas += collect_data_files('gradio')


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'celery.app.amqp',
        'celery.app.log',
        'celery.worker.autoscale',
        'celery.worker.components',
        'celery.bin',
        'celery.utils',
        'celery.utils.dispatch',
        'celery.contrib.testing',
        'celery.utils.static',
        'celery.concurrency.prefork',
        'celery.app.events',
        'celery.events.state',
        'celery.app.control',
        'celery.backends.redis',
        'celery.backends',
        'celery.backends.database',
        'celery.worker',
        'celery.worker.consumer',
        'celery.app',
        'celery.loaders',
        'celery.loaders.app',
        'celery.security',
        'celery.concurrency',
        'celery.events',
        'celery.contrib',
        'celery.apps',
        'celery',
        'celery.fixups',
        'celery.fixups.django',
        'celery.apps.worker',
        'celery.worker.strategy',
        'kombu.transport.redis',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'scipy',
        'sklearn',
        'sqlite3',
        'torch',
        'tensorflow',
        'transformers',
    ],
    noarchive=False,
    optimize=0,
    module_collection_mode={
        'gradio': 'py',
    },
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='app',
)
