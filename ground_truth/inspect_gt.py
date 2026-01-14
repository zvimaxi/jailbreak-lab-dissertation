import json

path = "data/ground_truth_cards.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Issuer:", data.get("issuer"))
print("\nCards:")
for c in data.get("cards", []):
    print("-", c["card_name"])
    pcts = c.get("percentages_found_on_page", [])
    print("  % found on page (sample):", pcts[:10])

pdf = data.get("pdf_terms", {})
lines = pdf.get("extracted_lines", [])
print(f"\nPDF extracted lines: {len(lines)}")
for row in lines[:15]:
    print("•", row)