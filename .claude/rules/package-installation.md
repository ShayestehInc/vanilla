# INstalling package rules
- DO NOT use pip install x
- DO NOT do pip freeze > requirements.txt
- Instead, check pypi website, pick the best version of the package, add it to requirements.txt (like x~=1.0.1) and then run pip install -r requirements.txt