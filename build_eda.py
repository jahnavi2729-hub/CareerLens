import nbformat as nbf

nb = nbf.v4.new_notebook()

nb.cells = [
    nbf.v4.new_markdown_cell("# Job Market EDA\n\nExploratory Data Analysis for CareerLens. We analyze the raw job data extracted from the Job Market API."),
    nbf.v4.new_code_cell("import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport json\nimport warnings\nwarnings.filterwarnings('ignore')\n\n# Configure visualizations\nsns.set_theme(style='whitegrid')\nplt.rcParams['figure.figsize'] = (10, 6)"),
    
    nbf.v4.new_markdown_cell("## 1. Data Loading"),
    nbf.v4.new_code_cell("with open('../data/raw/jobs_raw.json', 'r', encoding='utf-8') as f:\n    raw_data = json.load(f)\n    \n# The data is inside the 'data' key\ndf = pd.DataFrame(raw_data['data'])\ndf.head()"),
    
    nbf.v4.new_markdown_cell("## 2. Basic Dataset Overview\nCheck shape, columns, and data types."),
    nbf.v4.new_code_cell("print(f'Shape of dataset: {df.shape}')\nprint('\\nColumns:', df.columns.tolist())\nprint('\\nData Types:')\ndisplay(df.dtypes)"),
    
    nbf.v4.new_markdown_cell("## 3. Data Quality: Missing Values & Duplicates\nIdentify how much data is missing and if there are duplicate records."),
    nbf.v4.new_code_cell("missing_data = df.isnull().sum()\nmissing_percent = (missing_data / len(df)) * 100\nmissing_df = pd.DataFrame({'Missing Values': missing_data, 'Percentage': missing_percent})\ndisplay(missing_df.sort_values(by='Percentage', ascending=False))\n\nduplicates = df.duplicated(subset=['hash_id']).sum() if 'hash_id' in df.columns else df.duplicated().sum()\nprint(f'\\nNumber of duplicate records: {duplicates}')"),
    
    nbf.v4.new_markdown_cell("## 4. Unique Values & Categorical Distribution\nAnalyze unique companies, roles, and cities."),
    nbf.v4.new_code_cell("print(f\"Unique Companies: {df['company_name'].nunique()}\")\nprint(f\"Unique Roles: {df['role'].nunique()}\")\nprint(f\"Unique Cities: {df['city'].nunique()}\")\nprint(f\"Unique Locations: {df['location'].nunique()}\")\n\n# Top 10 hiring companies\nplt.figure(figsize=(10,5))\ndf['company_name'].value_counts().head(10).plot(kind='barh', color='skyblue')\nplt.title('Top 10 Hiring Companies')\nplt.xlabel('Number of Openings (Postings)')\nplt.gca().invert_yaxis()\nplt.show()"),
    
    nbf.v4.new_markdown_cell("## 5. Experience and Salary Analysis"),
    nbf.v4.new_code_cell("print('Experience Required samples:')\ndisplay(df['experience_required'].value_counts().head(10))\n\nprint('\\nSalary info samples:')\ndisplay(df['salary'].value_counts().head(10))\n\n# Availability of salary info\nsalary_provided = df['salary'].apply(lambda x: 'Not Disclosed' if pd.isna(x) or 'Not Disclosed' in str(x) else 'Disclosed')\nplt.figure(figsize=(6,4))\nsns.countplot(x=salary_provided)\nplt.title('Salary Disclosure Rate')\nplt.show()"),
    
    nbf.v4.new_markdown_cell("## 6. Skills and Job Description Availability\nAnalyze how many jobs have skills listed and complete descriptions."),
    nbf.v4.new_code_cell("df['has_jd'] = df['job_description'].notnull() & (df['job_description'] != '')\ndf['has_skills'] = df['key_skills'].notnull() & (df['key_skills'] != '')\n\nprint(f\"Jobs with a description: {df['has_jd'].mean() * 100:.2f}%\")\nprint(f\"Jobs with key skills: {df['has_skills'].mean() * 100:.2f}%\")\n\n# Extract and count top skills\nall_skills = df['key_skills'].dropna().str.split(',').explode().str.strip()\nplt.figure(figsize=(10,6))\nall_skills.value_counts().head(15).plot(kind='bar')\nplt.title('Top 15 Most Demanded Skills')\nplt.xticks(rotation=45, ha='right')\nplt.ylabel('Frequency')\nplt.show()"),
]

with open('notebooks/01_job_market_eda.ipynb', 'w') as f:
    nbf.write(nb, f)
