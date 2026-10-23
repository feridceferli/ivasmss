"""Idempotently connect the safe WhatsApp test commands to IVASMS main.py."""
from pathlib import Path
import sys

IMPORT = 'from whatsapp_safe import register_whatsapp_handlers'
CALL = '    register_whatsapp_handlers(app, is_admin)'
ENV_FIELDS = '''\n# WhatsApp Business Cloud API (admin-only opt-in test)\nWA_ACCESS_TOKEN=\nWA_PHONE_NUMBER_ID=\nWA_TEST_RECIPIENT=\nWA_GRAPH_VERSION=v25.0\n'''


def patch_bot(root: Path):
    root = root.resolve()
    main = root / 'main.py'
    module = root / 'whatsapp_safe.py'
    if not main.is_file():
        raise FileNotFoundError(f'Botun main.py faylı tapılmadı: {main}')
    if not module.is_file():
        raise FileNotFoundError(f'whatsapp_safe.py faylını botun əsas qovluğuna köçür: {module}')

    original = main.read_text(encoding='utf-8')
    result = original
    if IMPORT not in result:
        anchor = '# ==================== CONFIG SECTION ===================='
        if anchor not in result:
            raise ValueError('main.py formatı dəyişib: import üçün təhlükəsiz yer tapılmadı.')
        result = result.replace(anchor, f'{IMPORT}\n\n{anchor}', 1)
    if CALL not in result:
        anchor = 'def register_handlers(app):\n'
        if anchor not in result:
            raise ValueError('main.py formatı dəyişib: register_handlers tapılmadı.')
        result = result.replace(anchor, anchor + CALL + '\n', 1)
    # Write only validated Python. Do not touch other Telegram handlers.
    compile(result, str(main), 'exec')
    if result != original:
        backup = root / 'main.py.before_whatsapp_safe.bak'
        if not backup.exists():
            backup.write_text(original, encoding='utf-8')
        main.write_text(result, encoding='utf-8')

    example = root / '.env.example'
    old_env = example.read_text(encoding='utf-8') if example.exists() else ''
    if 'WA_ACCESS_TOKEN=' not in old_env:
        example.write_text(old_env.rstrip() + '\n' + ENV_FIELDS, encoding='utf-8')
    return result != original


if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    try:
        changed = patch_bot(root)
    except (FileNotFoundError, ValueError, SyntaxError) as exc:
        print(f'Xəta: {exc}', file=sys.stderr)
        sys.exit(1)
    print('✅ Təhlükəsiz WhatsApp bağlantısı quraşdırıldı.' if changed else '✅ WhatsApp bağlantısı artıq quraşdırılıb.')
