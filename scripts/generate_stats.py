import os
import json
import urllib.request
import urllib.error

TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "RaiyanRafid")

LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "PHP": "#4F5D95",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Vue": "#41b883",
    "Dart": "#00B4AB",
    "Ruby": "#701516",
    "Kotlin": "#A97BFF",
    "Swift": "#F05138"
}

def fetch_languages_graphql(token):
    query = """
    query {
      viewer {
        repositories(first: 100, ownerAffiliations: [OWNER], isFork: false) {
          nodes {
            name
            isPrivate
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Stats-Script"
        }
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
    
    if "errors" in data:
        raise RuntimeError(str(data["errors"]))
    
    lang_totals = {}
    repos = data.get("data", {}).get("viewer", {}).get("repositories", {}).get("nodes", [])
    for repo in repos:
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            size = edge["size"]
            color = edge["node"]["color"] or LANG_COLORS.get(name, "#8b949e")
            if name not in lang_totals:
                lang_totals[name] = {"size": 0, "color": color}
            lang_totals[name]["size"] += size
    return lang_totals

def fetch_languages_rest():
    req = urllib.request.Request(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100",
        headers={"User-Agent": "GitHub-Stats-Script"}
    )
    with urllib.request.urlopen(req) as res:
        repos = json.loads(res.read().decode("utf-8"))
    
    lang_totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        lang_url = repo.get("languages_url")
        if not lang_url:
            continue
        try:
            l_req = urllib.request.Request(lang_url, headers={"User-Agent": "GitHub-Stats-Script"})
            with urllib.request.urlopen(l_req) as l_res:
                langs = json.loads(l_res.read().decode("utf-8"))
                for name, size in langs.items():
                    if name not in lang_totals:
                        lang_totals[name] = {"size": 0, "color": LANG_COLORS.get(name, "#8b949e")}
                    lang_totals[name]["size"] += size
        except Exception:
            pass
    return lang_totals

def generate_svg(lang_totals, output_path):
    total_size = sum(item["size"] for item in lang_totals.values())
    if total_size == 0:
        return
    
    # Sort descending
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1]["size"], reverse=True)
    
    # Group small languages into Others if more than 6
    primary_langs = []
    other_size = 0
    for name, data in sorted_langs:
        pct = (data["size"] / total_size) * 100
        if len(primary_langs) < 6 and pct >= 0.5:
            primary_langs.append((name, data["size"], pct, data["color"]))
        else:
            other_size += data["size"]
    
    if other_size > 0:
        other_pct = (other_size / total_size) * 100
        primary_langs.append(("Other", other_size, other_pct, "#8b949e"))
    
    # SVG Dimensions
    card_width = 495
    row_count = (len(primary_langs) + 1) // 2
    card_height = 95 + (row_count * 25)
    
    # Build progress bar segments
    bar_x = 25
    bar_y = 55
    bar_width = card_width - 50
    bar_height = 8
    
    svg_segments = []
    current_x = 0
    for name, size, pct, color in primary_langs:
        seg_w = (pct / 100.0) * bar_width
        svg_segments.append(
            f'<rect x="{bar_x + current_x:.2f}" y="{bar_y}" width="{seg_w:.2f}" height="{bar_height}" fill="{color}" />'
        )
        current_x += seg_w
    
    # Build legend
    legend_items = []
    for i, (name, size, pct, color) in enumerate(primary_langs):
        col = i % 2
        row = i // 2
        lx = 25 + (col * 240)
        ly = 85 + (row * 24)
        legend_items.append(f'''
        <g transform="translate({lx}, {ly})">
          <circle cx="5" cy="5" r="4.5" fill="{color}" />
          <text x="16" y="9" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="12px" font-weight="500">
            {name} <tspan fill="#8b949e" font-size="11px">({pct:.1f}%)</tspan>
          </text>
        </g>
        ''')
    
    svg_content = f'''<svg width="{card_width}" height="{card_height}" viewBox="0 0 {card_width} {card_height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{
      font: 600 16px 'Segoe UI', Ubuntu, sans-serif;
      fill: #70a5fd;
    }}
  </style>
  <rect x="0.5" y="0.5" rx="6" width="{card_width - 1}" height="{card_height - 1}" fill="#1a1b27" stroke="#30363d" />
  <text x="25" y="35" class="header">My Programming Languages (Public &amp; Private)</text>
  <g clip-path="url(#bar-clip)">
    <clipPath id="bar-clip">
      <rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="4" />
    </clipPath>
    {''.join(svg_segments)}
  </g>
  {''.join(legend_items)}
</svg>
'''
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Successfully generated {output_path}")

def main():
    lang_totals = {}
    if TOKEN:
        try:
            print("Fetching repositories via GitHub GraphQL API...")
            lang_totals = fetch_languages_graphql(TOKEN)
            print(f"GraphQL fetched {len(lang_totals)} languages across public & private repos.")
        except Exception as e:
            print(f"GraphQL failed ({e}), falling back to REST...")
            lang_totals = fetch_languages_rest()
    else:
        print("No token found. Fetching public repositories via REST API...")
        lang_totals = fetch_languages_rest()
    
    generate_svg(lang_totals, "assets/top-langs.svg")

if __name__ == "__main__":
    main()
