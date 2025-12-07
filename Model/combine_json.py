import json

files = ["data/synthetic_freshman.json", "data/synthetic_sophomores.json", "data/synthetic_juniors.json", "data/synthetic_seniors.json"]

combined = []
for f in files:
    with open(f, "r") as infile:
        combined.extend(json.load(infile))

with open("data/synthetic_courses.json", "w") as outfile:
    json.dump(combined, outfile, indent=2)

print("Done! combined.json saved.")