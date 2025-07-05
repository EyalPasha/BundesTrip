#!/usr/bin/env python3
"""Generate frontend/services/supabase-config.js from environment variables."""
import os
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parents[1] / 'frontend' / 'services' / 'supabase-config.js'
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'frontend' / 'services' / 'supabase-config.template.js'

supabase_url = os.environ.get('SUPABASE_URL')
supabase_anon_key = os.environ.get('SUPABASE_ANON_KEY')

if not supabase_url or not supabase_anon_key:
    raise SystemExit('SUPABASE_URL and SUPABASE_ANON_KEY must be set as environment variables')

with open(TEMPLATE_PATH, 'r') as f:
    template = f.read()

content = template.replace('__SUPABASE_URL__', supabase_url).replace('__SUPABASE_ANON_KEY__', supabase_anon_key)

OUTPUT_PATH.write_text(content)
print(f'Wrote {OUTPUT_PATH}')
