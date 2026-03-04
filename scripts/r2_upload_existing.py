#!/usr/bin/env python3
"""One-time script to upload existing review files to R2."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import r2_storage

def main():
    if not r2_storage.is_configured():
        print('R2 not configured. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL')
        sys.exit(1)

    # Upload all review files for output_sosed
    review_dir = PROJECT_ROOT / 'output_sosed' / 'review'
    if not review_dir.exists():
        print(f'Review dir not found: {review_dir}')
        sys.exit(1)

    files = list(review_dir.rglob('*'))
    files = [f for f in files if f.is_file()]
    print(f'Found {len(files)} files to upload')

    uploaded = 0
    for f in sorted(files):
        r2_key = str(f.relative_to(PROJECT_ROOT))
        print(f'  {r2_key}', end=' ... ')
        if r2_storage.upload_file(f, r2_key):
            print('OK')
            uploaded += 1
        else:
            print('FAILED')

    # Also upload frames if they exist
    frames_dir = PROJECT_ROOT / 'output_sosed' / 'frames'
    if frames_dir.exists():
        for f in sorted(frames_dir.rglob('*')):
            if f.is_file():
                r2_key = str(f.relative_to(PROJECT_ROOT))
                print(f'  {r2_key}', end=' ... ')
                if r2_storage.upload_file(f, r2_key):
                    print('OK')
                    uploaded += 1
                else:
                    print('FAILED')

    print(f'\nDone: {uploaded}/{len(files)} uploaded')


if __name__ == '__main__':
    main()
