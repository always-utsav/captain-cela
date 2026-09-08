"""Quick Gemini API test with full output."""
import warnings
warnings.filterwarnings("ignore")
import os
for line in open(".env"):
    line = line.strip()
    if line and "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip()

import google.generativeai as genai
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
m = genai.GenerativeModel("gemini-3.6-flash", generation_config={"temperature": 0, "max_output_tokens": 512})

print("=== Test 1: Factual (keyword present) ===")
r1 = m.generate_content("The calculator tool returned: 42. Analyze this result and give a summary in 2 sentences.")
print(repr(r1.text))
print("Has '42':", "42" in r1.text)

print("\n=== Test 2: Channel intervention (keyword blocked) ===")
r2 = m.generate_content("The calculator tool returned: [BLOCKED]. The original value was redacted. Analyze this and give a summary in 2 sentences.")
print(repr(r2.text))
print("Has '42':", "42" in r2.text)

print("\n=== Test 3: Source-event intervention (tool blocked) ===")
r3 = m.generate_content("The calculator tool produced no output. The tool execution was blocked entirely. Analyze this and give a summary in 2 sentences.")
print(repr(r3.text))
print("Has '42':", "42" in r3.text)
