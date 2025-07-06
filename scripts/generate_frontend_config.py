#!/usr/bin/env python3
"""Generate frontend configuration files from environment variables.

This script creates both ``supabase-config.js`` and ``api-config.js`` in the
``frontend/services`` directory. Values are taken from the environment to avoid
committing secrets or environment-specific URLs to the repository.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1] / 'frontend' / 'services'

SUPABASE_OUTPUT = BASE_DIR / 'supabase-config.js'
SUPABASE_TEMPLATE = BASE_DIR / 'supabase-config.template.js'
API_OUTPUT = BASE_DIR / 'api-config.js'
API_TEMPLATE = BASE_DIR / 'api-config.template.js'

supabase_url = os.environ.get('SUPABASE_URL')
supabase_anon_key = os.environ.get('SUPABASE_ANON_KEY')

if not supabase_url or not supabase_anon_key:
    raise SystemExit('SUPABASE_URL and SUPABASE_ANON_KEY must be set as environment variables')

with open(SUPABASE_TEMPLATE, 'r') as f:
    supabase_template = f.read()

supabase_content = supabase_template.replace('__SUPABASE_URL__', supabase_url).replace('__SUPABASE_ANON_KEY__', supabase_anon_key)
SUPABASE_OUTPUT.write_text(supabase_content)
print(f'Wrote {SUPABASE_OUTPUT}')

api_url = os.environ.get('API_URL')
if not api_url:
    raise SystemExit('API_URL must be set as an environment variable')

with open(API_TEMPLATE, 'r') as f:
    api_template = f.read()

api_content = api_template.replace('__API_URL__', api_url)
API_OUTPUT.write_text(api_content)
print(f'Wrote {API_OUTPUT}')
