import PyPDF2
import re

def clean_text(text):
    # Remove some weird line breaks
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # Add proper headings
    text = re.sub(r'(LEVEL \d+ — [A-Za-z0-9_ \-&]+)', r'\n\n# \1\n\n', text)
    text = re.sub(r'(TIER \d+ — [A-Za-z0-9_ \-&]+)', r'\n\n# \1\n\n', text)
    text = re.sub(r'(PROMPT \d+: [A-Za-z0-9_ \-&]+)', r'\n\n## \1\n\n', text)
    text = re.sub(r'(PART \d+: [A-Za-z0-9_ \-&]+)', r'\n\n# \1\n\n', text)
    # Add subheadings for CREATE, COMMANDS, etc.
    text = re.sub(r'(Create [a-zA-Z0-9_\/]+\.[a-z]+)', r'\n### \1\n', text)
    text = re.sub(r'(COMMANDS:)', r'\n### \1\n', text)
    text = re.sub(r'(FREE DATA SOURCES:)', r'\n### \1\n', text)
    text = re.sub(r'(FREE DATA:)', r'\n### \1\n', text)
    text = re.sub(r'(KEY METRICS:)', r'\n### \1\n', text)
    text = re.sub(r'(DEBATE PROCESS:)', r'\n### \1\n', text)
    
    # Format code blocks loosely
    text = re.sub(r'(def [a-zA-Z0-9_]+\([^)]*\):)', r'\n```python\n\1\n```\n', text)
    
    return text

print("Extracting PDF text...")
pdf_path = "c:/Users/thwin/Desktop/ShufaClaw/crypto agent master prompts.pdf"
reader = PyPDF2.PdfReader(pdf_path)
raw_text = "".join([page.extract_text() for page in reader.pages])

print("Formatting text...")
cleaned = clean_text(raw_text)

with open('crypto_agent_master_prompts.md', 'w', encoding='utf-8') as f:
    f.write(cleaned)
print("Conversion complete: crypto_agent_master_prompts.md")
