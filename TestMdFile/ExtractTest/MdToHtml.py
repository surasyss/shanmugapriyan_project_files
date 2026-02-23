import markdown
from pathlib import Path


file_path = Path("C:\\Users\\priya\\Desktop\\0125_Android\\TestMdFile\\Result\\textbook.md")

file_path_html = Path("C:\\Users\\priya\\Desktop\\0125_Android\\TestMdFile\\Result\\output.html")

# Read the markdown file
with open(file_path, "r", encoding="utf-8") as md_file:
        md_text = md_file.read()

# Convert to HTML
html_content = markdown.markdown(md_text)
# print(html_content)

# Save as an HTML file
with open(file_path_html, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

print("Markdown converted to HTML successfully!")
