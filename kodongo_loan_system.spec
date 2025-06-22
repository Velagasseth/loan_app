# kodongo_loan_system.spec

block_cipher = None

a = Analysis(
    ['login_app.py'],  # Your main entry point
    pathex=[],  # Add any additional paths if needed
# Add this to your .spec file:
binaries=[
],
    hiddenimports=[
        # Core dependencies
        'pandas', 'numpy',
        'sqlite3', 'hashlib', 're', 'datetime',

        # UI components
        'customtkinter',
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox',

        # Additional packages
        'fpdf', 'openpyxl', 'PIL', 'PIL._imaging',
        'setuptools', 'pkg_resources',

        # Windows compatibility (will be ignored on Linux build)
        'ctypes', 'ctypes.windll',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],  # Explicitly empty to avoid hook errors
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='KodongoLoanSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compression
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='32bit',  # Force 32-bit for maximum compatibility
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',)

