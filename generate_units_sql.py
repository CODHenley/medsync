import pandas as pd
import re

path = '/Users/meganhenley/Library/Application Support/Claude/local-agent-mode-sessions/88cdf951-7dc8-44fe-9a81-ad8b77317c6c/6393dd95-bb27-4d4b-a297-f518f5b3dd5b/local_a8d02c6f-2d38-47f7-b343-a3228587787b/uploads/Demand_Forecasting_Spreadsheet_2026_v4 (2).xlsx'

df = pd.read_excel(path, sheet_name='Product List', header=0)
df = df[['Product Name', 'Default Package Size', 'Dispensing Unit']].dropna(subset=['Product Name'])

def esc(s):
    return str(s).replace("'", "''")

lines = [
    "-- Auto-generated: update products with dispensing_unit and package_size",
    "-- Review before running. Names must match your Supabase products table exactly.",
    ""
]

for _, row in df.iterrows():
    name = str(row['Product Name']).strip()
    pkg_size = row['Default Package Size']
    unit = str(row['Dispensing Unit']).strip()

    try:
        pkg_size = float(pkg_size)
    except (ValueError, TypeError):
        pkg_size = 1.0

    lines.append(
        f"UPDATE products SET dispensing_unit = '{esc(unit)}', package_size = {pkg_size} "
        f"WHERE name = '{esc(name)}';"
    )

lines.append("")
lines.append("-- Verify: check how many rows were updated")
lines.append("SELECT COUNT(*) FROM products WHERE dispensing_unit IS NOT NULL;")

out_path = '/Users/meganhenley/Downloads/medsync_deploy/update_product_units.sql'
with open(out_path, 'w') as f:
    f.write('\n'.join(lines))

print(f"Generated {len(df)} UPDATE statements → update_product_units.sql")
print("Review the file, then paste into Supabase SQL Editor and run.")
