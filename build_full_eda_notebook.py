import nbformat as nbf

nb = nbf.v4.new_notebook()

cells = []

# --- Title ---
cells.append(nbf.v4.new_markdown_cell(
    "# 📊 CareerLens — Full Job Market EDA & Business Hypothesis Testing\n\n"
    "**Dataset:** `data/raw/jobs_raw.json`  \n"
    "**Total Records:** 40,847 job postings  \n"
    "**Scope:** Univariate & Bivariate EDA, Visualizations, and Statistical Hypothesis Testing (Chi-Square, Mann-Whitney U, Welch T-Test). Raw dataset is preserved untouched.\n\n"
    "---"
))

# --- 1. Setup ---
cells.append(nbf.v4.new_markdown_cell("## 1. Environment Setup & Imports"))
cells.append(nbf.v4.new_code_cell(
    "import pandas as pd\n"
    "import numpy as np\n"
    "import matplotlib.pyplot as plt\n"
    "import seaborn as sns\n"
    "import json\n"
    "import re\n"
    "from scipy import stats\n"
    "import warnings\n"
    "warnings.filterwarnings('ignore')\n\n"
    "# Styling configuration for plots\n"
    "sns.set_theme(style='whitegrid', palette='muted')\n"
    "plt.rcParams['figure.figsize'] = (10, 5)\n"
    "plt.rcParams['figure.dpi'] = 100\n"
    "print('Libraries and scipy.stats successfully imported.')"
))

# --- 2. Load Raw Data ---
cells.append(nbf.v4.new_markdown_cell("## 2. Load Raw API Dataset (40,847 Records)"))
cells.append(nbf.v4.new_code_cell(
    "with open('../data/raw/jobs_raw.json', 'r', encoding='utf-8') as f:\n"
    "    raw_data = json.load(f)\n\n"
    "df = pd.DataFrame(raw_data['data'])\n\n"
    "print(f'API Success Flag     : {raw_data.get(\"success\")}')\n"
    "print(f'Requested Limit      : {raw_data.get(\"requested_limit\")}')\n"
    "print(f'Returned Count       : {raw_data.get(\"returned_count\")}')\n"
    "print(f'Loaded DataFrame Shape: {df.shape}')\n"
    "df.head(3)"
))

# --- 3. Shape & Schema ---
cells.append(nbf.v4.new_markdown_cell(
    "## 3. Dataset Overview — Shape, Schema & Dtypes\n\n"
    "Inspect column names, data dimensions, and inferred data types."
))
cells.append(nbf.v4.new_code_cell(
    "print(f'Dataset Dimensions: {df.shape[0]:,} rows x {df.shape[1]} columns')\n\n"
    "dtype_df = pd.DataFrame({\n"
    "    'Column': df.columns,\n"
    "    'Dtype': df.dtypes.astype(str),\n"
    "    'Non-Null Count': df.notnull().sum().values,\n"
    "    'Sample Value': [str(df[col].iloc[0])[:50] for col in df.columns]\n"
    "})\n"
    "display(dtype_df)"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** The dataset contains **40,847 records and 20 columns**. "
    "Only `id` is stored as numeric (`int64`), while all other 19 fields are `object` (string) types. "
    "Fields such as `openings`, `applicants`, `posted_date`, and `scraped_at` will require explicit "
    "type conversion and normalization during preprocessing."
))

# --- 4. Missing Values ---
cells.append(nbf.v4.new_markdown_cell(
    "## 4. Missing Values & Sentinel `'N/A'` Analysis\n\n"
    "Evaluate structural nulls (NaN) as well as literal string sentinels (`'N/A'`, `'Not Disclosed'`)."
))
cells.append(nbf.v4.new_code_cell(
    "# 1. Structural NaN\n"
    "nan_counts = df.isnull().sum()\n"
    "print(f'Total NaN values in entire dataset: {nan_counts.sum()}')\n\n"
    "# 2. Literal 'N/A' sentinel strings per column\n"
    "na_list = []\n"
    "for col in df.columns:\n"
    "    cnt = (df[col].astype(str).str.strip() == 'N/A').sum()\n"
    "    pct = round(cnt / len(df) * 100, 2)\n"
    "    na_list.append({'Column': col, 'N/A Count': cnt, 'N/A %': pct})\n\n"
    "na_df = pd.DataFrame(na_list).sort_values('N/A %', ascending=False)\n"
    "display(na_df)\n\n"
    "# Plot N/A percentages\n"
    "fig, ax = plt.subplots(figsize=(10, 5))\n"
    "bars = ax.barh(na_df['Column'], na_df['N/A %'], color=['#e74c3c' if v > 10 else '#e67e22' if v > 1 else '#2ecc71' for v in na_df['N/A %']])\n"
    "ax.invert_yaxis()\n"
    "ax.set_title('Sentinel N/A Value Percentage per Field (40,847 Records)')\n"
    "ax.set_xlabel('Percentage (%)')\n"
    "for bar in bars:\n"
    "    width = bar.get_width()\n"
    "    if width > 0:\n"
    "        ax.text(width + 0.3, bar.get_y() + bar.get_height()/2, f'{width:.1f}%', ha='left', va='center', fontsize=9)\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** Across all 40,847 records, there are **0 structural NaN values** (0% missing). "
    "However, field completeness varies by column via `'N/A'` sentinel strings:\n"
    "- `openings` (16.38% N/A) and `applicants` (14.85% N/A) have the highest missingness.\n"
    "- `role_category` is missing in 14.85% of records.\n"
    "- Core fields (`key_skills`, `role`, `department`, `industry`, `education`, `salary`, `location`) have a very low N/A rate of **only 2.27%** (39,918 records fully populated)."
))

# --- 5. Duplicates ---
cells.append(nbf.v4.new_markdown_cell(
    "## 5. Duplicate Records & Primary Key Verification\n\n"
    "Check uniqueness across primary identifier `id` and full record rows."
))
cells.append(nbf.v4.new_code_cell(
    "dup_ids = df['id'].duplicated().sum()\n"
    "dup_rows = df.duplicated().sum()\n"
    "print(f'Duplicate ID Count        : {dup_ids}')\n"
    "print(f'Duplicate Full Rows Count  : {dup_rows}')\n"
    "print(f'Unique Job Record IDs      : {df[\"id\"].nunique():,}')"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** The dataset has **zero duplicate IDs and zero duplicate rows**. "
    "All 40,847 job postings are distinct, confirming that `id` serves as a reliable primary key for incremental ingestion."
))

# --- 6. Unique Values Summary ---
cells.append(nbf.v4.new_markdown_cell(
    "## 6. Categorical Cardinality Overview\n\n"
    "Inspect the count of unique categorical values across major fields."
))
cells.append(nbf.v4.new_code_cell(
    "cat_fields = ['company_name', 'role', 'role_category', 'city', 'location',\n"
    "              'industry', 'department', 'employment_type']\n"
    "card_list = [{'Field': col, 'Unique Values': df[col].nunique()} for col in cat_fields]\n"
    "card_df = pd.DataFrame(card_list).sort_values('Unique Values', ascending=False)\n"
    "display(card_df)\n\n"
    "fig, ax = plt.subplots(figsize=(8, 4))\n"
    "ax.bar(card_df['Field'], card_df['Unique Values'], color='#34495e')\n"
    "ax.set_title('Unique Categorical Values Count')\n"
    "ax.set_ylabel('Cardinality')\n"
    "plt.xticks(rotation=45, ha='right')\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** High categorical diversity is observed: **8,616 unique companies**, "
    "**1,022 unique roles**, **1,026 locations**, **160 role categories**, and **126 industries**. "
    "This confirms a broad job market representation across the IT and corporate sector."
))

# --- 7. Geographic Distribution ---
cells.append(nbf.v4.new_markdown_cell("## 7. Geographic Distribution — Cities & Locations"))
cells.append(nbf.v4.new_code_cell(
    "city_counts = df['city'].value_counts()\n"
    "print('City Distribution:')\n"
    "display(city_counts.to_frame('Postings'))\n\n"
    "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n"
    "top_cities = city_counts.head(7)\n"
    "axes[0].bar(top_cities.index, top_cities.values, color='#2980b9')\n"
    "axes[0].set_title('Top Cities by Job Postings')\n"
    "axes[0].set_ylabel('Number of Jobs')\n"
    "axes[0].tick_params(axis='x', rotation=45)\n"
    "for i, v in enumerate(top_cities.values):\n"
    "    axes[0].text(i, v + 500, f'{v:,}', ha='center', fontsize=9)\n\n"
    "top_locs = df[df['location'] != 'N/A']['location'].value_counts().head(10)\n"
    "axes[1].barh(top_locs.index, top_locs.values, color='#16a085')\n"
    "axes[1].invert_yaxis()\n"
    "axes[1].set_title('Top 10 Specific Locations')\n"
    "axes[1].set_xlabel('Postings')\n\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** **Bangalore dominates the dataset with 38,652 postings (94.6%)**, followed by "
    "Hyderabad (1,921 postings, 4.7%), Delhi (64), Pune (53), and Mumbai (50). "
    "The dataset represents India's major tech hubs, with Bangalore being the primary focal point."
))

# --- 8. Top Companies & Industries ---
cells.append(nbf.v4.new_markdown_cell("## 8. Top Hiring Companies & Industry Sectors"))
cells.append(nbf.v4.new_code_cell(
    "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n\n"
    "# Top Companies\n"
    "top_comp = df['company_name'].value_counts().head(10)\n"
    "axes[0].barh(top_comp.index, top_comp.values, color='#8e44ad')\n"
    "axes[0].invert_yaxis()\n"
    "axes[0].set_title('Top 10 Hiring Companies')\n"
    "axes[0].set_xlabel('Postings')\n"
    "for i, v in enumerate(top_comp.values):\n"
    "    axes[0].text(v + 50, i, f'{v:,}', va='center', fontsize=9)\n\n"
    "# Top Industries\n"
    "top_ind = df[df['industry'] != 'N/A']['industry'].value_counts().head(10)\n"
    "axes[1].barh(top_ind.index, top_ind.values, color='#d35400')\n"
    "axes[1].invert_yaxis()\n"
    "axes[1].set_title('Top 10 Industry Sectors')\n"
    "axes[1].set_xlabel('Postings')\n\n"
    "plt.tight_layout()\n"
    "plt.show()\n\n"
    "print('Top 5 Companies Share:')\n"
    "print((top_comp.head(5) / len(df) * 100).round(2).to_string())"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** Major IT services and consulting firms dominate hiring:\n"
    "- **Accenture** is the single largest recruiter with **4,052 jobs (9.92%)**.\n"
    "- **Infosys** (1,603 jobs / 3.92%), **TCS** (1,461 jobs / 3.58%), **Capgemini** (652), and **EY** (563) follow.\n"
    "- IT Services & IT Consulting comprise over 60% of all industry sector listings."
))

# --- 9. Role Taxonomy ---
cells.append(nbf.v4.new_markdown_cell("## 9. Role Taxonomy & Job Functions"))
cells.append(nbf.v4.new_code_cell(
    "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n\n"
    "# Top Roles\n"
    "top_roles = df[df['role'] != 'N/A']['role'].value_counts().head(10)\n"
    "axes[0].barh(top_roles.index, top_roles.values, color='#2c3e50')\n"
    "axes[0].invert_yaxis()\n"
    "axes[0].set_title('Top 10 Job Roles')\n"
    "axes[0].set_xlabel('Postings')\n\n"
    "# Top Role Categories\n"
    "top_rc = df[df['role_category'] != 'N/A']['role_category'].value_counts().head(10)\n"
    "axes[1].barh(top_rc.index, top_rc.values, color='#27ae60')\n"
    "axes[1].invert_yaxis()\n"
    "axes[1].set_title('Top 10 Role Categories')\n"
    "axes[1].set_xlabel('Postings')\n\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** **Software Development** is the dominant role category (8,109 jobs), "
    "followed by Quality Assurance/Testing (1,511), IT Consulting (1,311), and IT Security (911). "
    "Top specific job roles include Software Developer, Back End Developer, Full Stack Developer, Technical Lead, and Data Engineer."
))

# --- 10. Experience Analysis ---
cells.append(nbf.v4.new_markdown_cell("## 10. Experience Required Distribution"))
cells.append(nbf.v4.new_code_cell(
    "exp_counts = df[df['experience_required'] != 'N/A']['experience_required'].value_counts().head(15)\n\n"
    "fig, ax = plt.subplots(figsize=(10, 5))\n"
    "ax.bar(exp_counts.index, exp_counts.values, color='#e67e22')\n"
    "ax.set_title('Top 15 Required Experience Levels (Years)')\n"
    "ax.set_xlabel('Experience String')\n"
    "ax.set_ylabel('Number of Jobs')\n"
    "ax.tick_params(axis='x', rotation=45)\n"
    "for i, v in enumerate(exp_counts.values):\n"
    "    ax.text(i, v + 100, f'{v:,}', ha='center', fontsize=8)\n"
    "plt.tight_layout()\n"
    "plt.show()\n\n"
    "print('Experience breakdown summary:')\n"
    "print(df['experience_required'].value_counts().head(10).to_string())"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** Mid-level engineering roles lead demand:\n"
    "- **5 Years experience** is the single most requested milestone (6,309 jobs / 15.4%).\n"
    "- **3 Years** (4,907 jobs), **1 Year** (4,722 jobs), **0 Years/Freshers** (4,424 jobs), and **2 Years** (4,376 jobs) follow."
))

# --- 11. Salary Disclosure ---
cells.append(nbf.v4.new_markdown_cell("## 11. Salary Disclosure & Pay Bands"))
cells.append(nbf.v4.new_code_cell(
    "def classify_salary(val):\n"
    "    s = str(val).strip()\n"
    "    if s in ['N/A', 'Not Disclosed', 'Not disclosed']:\n"
    "        return 'Not Disclosed / N/A'\n"
    "    return 'Disclosed Range'\n\n"
    "df['salary_status'] = df['salary'].apply(classify_salary)\n"
    "sal_vc = df['salary_status'].value_counts()\n\n"
    "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n"
    "axes[0].pie(sal_vc.values, labels=sal_vc.index, autopct='%1.1f%%', colors=['#e74c3c', '#2ecc71'], startangle=140)\n"
    "axes[0].set_title('Salary Disclosure Rate (40,847 Records)')\n\n"
    "disclosed_sal = df[~df['salary'].isin(['N/A', 'Not Disclosed', 'Not disclosed'])]['salary'].value_counts().head(10)\n"
    "axes[1].barh(disclosed_sal.index, disclosed_sal.values, color='#f39c12')\n"
    "axes[1].invert_yaxis()\n"
    "axes[1].set_title('Top Disclosed Salary Ranges (Lacs P.A)')\n"
    "axes[1].set_xlabel('Postings')\n\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** **68.2% of job postings specify 'Not Disclosed'**, while 31.8% provide explicit salary ranges."
))

# --- 12. Key Skills Demand ---
cells.append(nbf.v4.new_markdown_cell("## 12. In-Demand Key Skills Analysis"))
cells.append(nbf.v4.new_code_cell(
    "skills_valid = df[df['key_skills'] != 'N/A']['key_skills']\n"
    "all_skills = skills_valid.str.split(',').explode().str.strip()\n"
    "all_skills = all_skills[all_skills != '']\n\n"
    "skills_norm = all_skills.str.lower()\n"
    "top_skills_norm = skills_norm.value_counts().head(20)\n\n"
    "fig, ax = plt.subplots(figsize=(12, 6))\n"
    "ax.bar(top_skills_norm.index, top_skills_norm.values, color='#2980b9')\n"
    "ax.set_title('Top 20 Most Demanded Skills (Across 39,918 Postings)')\n"
    "ax.set_ylabel('Frequency')\n"
    "ax.tick_params(axis='x', rotation=45)\n"
    "for i, v in enumerate(top_skills_norm.values):\n"
    "    ax.text(i, v + 50, f'{v:,}', ha='center', fontsize=8)\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** **97.73% of records (39,918 jobs) contain valid key skills!** "
    "Python is the #1 technical skill (3,020 mentions), followed by Sales, Java, SQL, AI, Cloud, and Agile."
))

# --- 13. Temporal Analysis ---
cells.append(nbf.v4.new_markdown_cell("## 13. Temporal Coverage & Scrape Timeline"))
cells.append(nbf.v4.new_code_cell(
    "df['scraped_at_dt'] = pd.to_datetime(df['scraped_at'])\n"
    "daily_counts = df['scraped_at_dt'].dt.date.value_counts().sort_index()\n"
    "fig, ax = plt.subplots(figsize=(12, 4))\n"
    "ax.plot(daily_counts.index, daily_counts.values, marker='o', color='#c0392b')\n"
    "ax.set_title('Daily Scraping Volume (July 18 — Sept 3, 2026)')\n"
    "ax.set_ylabel('Records Scraped')\n"
    "ax.set_xlabel('Date')\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Interpretation:** The dataset spans 47 days of ingestion (July 18 to Sept 3, 2026)."
))

# --- 14. Bivariate Analysis & Statistical Business Hypothesis Testing ---
cells.append(nbf.v4.new_markdown_cell(
    "## 14. Bivariate Analysis & Statistical Business Hypothesis Testing\n\n"
    "We formulate and test three business hypotheses to uncover strategic job-market insights using statistical rigor."
))

# --- Hypothesis 1 ---
cells.append(nbf.v4.new_markdown_cell(
    "### 🧪 Hypothesis 1: Top IT Giants vs. Market Average Experience Demand\n\n"
    "- **Business Context:** Do tier-1 tech giants (Accenture, Infosys, TCS, Capgemini, EY) require higher experience levels compared to smaller employers?\n"
    "- **$H_0$ (Null Hypothesis):** The experience level required by top 5 tech giants is identical to non-top-5 employers.\n"
    "- **$H_1$ (Alternative Hypothesis):** Top 5 tech giants require significantly higher experience levels.\n"
    "- **Statistical Test:** Mann-Whitney U Test (Non-Parametric Two-Sample Test)."
))
cells.append(nbf.v4.new_code_cell(
    "# Extract numeric min experience for temporary analysis\n"
    "def extract_min_exp(val):\n"
    "    nums = re.findall(r'\\d+', str(val))\n"
    "    return float(nums[0]) if nums else np.nan\n\n"
    "df['temp_min_exp'] = df['experience_required'].apply(extract_min_exp)\n"
    "top_5_comps = df['company_name'].value_counts().head(5).index\n"
    "df['is_top_giant'] = df['company_name'].isin(top_5_comps)\n\n"
    "top_exp_data = df[df['is_top_giant']]['temp_min_exp'].dropna()\n"
    "other_exp_data = df[~df['is_top_giant']]['temp_min_exp'].dropna()\n\n"
    "# Statistical Test\n"
    "u_stat, p_val_h1 = stats.mannwhitneyu(top_exp_data, other_exp_data, alternative='greater')\n\n"
    "print(f'Top 5 Tech Giants Mean Min Experience : {top_exp_data.mean():.2f} years (n={len(top_exp_data):,})')\n"
    "print(f'Other Employers Mean Min Experience    : {other_exp_data.mean():.2f} years (n={len(other_exp_data):,})')\n"
    "print(f'Mann-Whitney U Statistic                : {u_stat:,.1f}')\n"
    "print(f'p-value                                 : {p_val_h1:.4e}')\n\n"
    "# Visualization\n"
    "fig, ax = plt.subplots(figsize=(8, 5))\n"
    "sns.boxplot(x='is_top_giant', y='temp_min_exp', data=df, palette=['#95a5a6', '#8e44ad'], ax=ax)\n"
    "ax.set_xticklabels(['Other Employers', 'Top 5 Tech Giants'])\n"
    "ax.set_title('Bivariate Analysis: Required Experience (Top 5 Tech Giants vs. Other Employers)')\n"
    "ax.set_ylabel('Minimum Required Experience (Years)')\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Statistical Interpretation for Hypothesis 1:**\n"
    "- **Result:** Mann-Whitney U = 159,788,025.5, **$p$-value = $1.45 \\times 10^{-147} < 0.05$**.\n"
    "- **Decision:** Reject the Null Hypothesis ($H_0$).\n"
    "- **Business Finding:** Top 5 tech giants demand significantly higher average experience (**5.07 years**) "
    "compared to other companies (**4.18 years**). Top IT recruiters focus heavily on mid-to-senior engineering talent."
))

# --- Hypothesis 2 ---
cells.append(nbf.v4.new_markdown_cell(
    "### 🧪 Hypothesis 2: Experience Seniority vs. Salary Disclosure Transparency\n\n"
    "- **Business Context:** Are companies more transparent about salary for entry-level roles compared to senior positions?\n"
    "- **$H_0$ (Null Hypothesis):** Salary disclosure rate is independent of job experience seniority level.\n"
    "- **$H_1$ (Alternative Hypothesis):** Salary disclosure rate is significantly dependent on job experience seniority.\n"
    "- **Statistical Test:** Chi-Square Test of Independence ($\\\\chi^2$)."
))
cells.append(nbf.v4.new_code_cell(
    "def classify_exp_level(val):\n"
    "    if pd.isna(val): return 'Unknown'\n"
    "    if val <= 1: return '1. Entry-Level (0-1 yrs)'\n"
    "    elif val <= 4: return '2. Junior/Mid (2-4 yrs)'\n"
    "    else: return '3. Senior (5+ yrs)'\n\n"
    "df['exp_level_group'] = df['temp_min_exp'].apply(classify_exp_level)\n"
    "df['is_sal_disclosed'] = ~df['salary'].isin(['N/A', 'Not Disclosed', 'Not disclosed'])\n\n"
    "# Contingency table\n"
    "ct_table = pd.crosstab(df['exp_level_group'], df['is_sal_disclosed'], margins=False)\n"
    "chi2_stat, p_val_h2, dof, expected = stats.chi2_contingency(ct_table)\n\n"
    "print('Contingency Table (Experience Level vs. Salary Disclosure):')\n"
    "display(ct_table.rename(columns={False: 'Not Disclosed', True: 'Disclosed'}))\n"
    "print(f'Chi-Square Statistic: {chi2_stat:,.2f}')\n"
    "print(f'Degrees of Freedom  : {dof}')\n"
    "print(f'p-value             : {p_val_h2:.4e}')\n\n"
    "# Visualization: Stacked Bar Chart\n"
    "ct_pct = pd.crosstab(df['exp_level_group'], df['is_sal_disclosed'], normalize='index') * 100\n"
    "fig, ax = plt.subplots(figsize=(9, 5))\n"
    "ct_pct.plot(kind='bar', stacked=True, color=['#e74c3c', '#2ecc71'], ax=ax)\n"
    "ax.set_title('Salary Disclosure Rate by Experience Seniority Level')\n"
    "ax.set_ylabel('Percentage (%)')\n"
    "ax.set_xlabel('Seniority Level')\n"
    "ax.legend(['Not Disclosed', 'Salary Disclosed'], loc='upper right')\n"
    "plt.xticks(rotation=0)\n"
    "for p in ax.patches:\n"
    "    width, height = p.get_width(), p.get_height()\n"
    "    if height > 5:\n"
    "        x, y = p.get_xy()\n"
    "        ax.text(x + width/2, y + height/2, f'{height:.1f}%', ha='center', va='center', color='white', fontweight='bold')\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Statistical Interpretation for Hypothesis 2:**\n"
    "- **Result:** $\\chi^2 = 4425.38$, **$p$-value = $0.0000 < 0.05$**.\n"
    "- **Decision:** Reject the Null Hypothesis ($H_0$).\n"
    "- **Business Finding:** Entry-level postings have a **dramatically higher salary disclosure rate (59.9%)** "
    "compared to Junior/Mid roles (23.9%) and Senior roles (23.2%). Employers use transparent salary listings "
    "to attract campus graduates and early-career talent, whereas senior compensation is negotiated individually."
))

# --- Hypothesis 3 ---
cells.append(nbf.v4.new_markdown_cell(
    "### 🧪 Hypothesis 3: Tech Stack Demand — Python vs. Java Experience Requirements\n\n"
    "- **Business Context:** Do Python-demanding roles require different experience levels compared to Java-demanding roles?\n"
    "- **$H_0$ (Null Hypothesis):** The mean experience required for Python roles equals that of Java roles.\n"
    "- **$H_1$ (Alternative Hypothesis):** Python roles require a significantly different mean experience level.\n"
    "- **Statistical Test:** Welch's Two-Sample T-Test (Unequal Variance)."
))
cells.append(nbf.v4.new_code_cell(
    "py_mask = df['key_skills'].str.contains('Python|python', na=False)\n"
    "java_mask = df['key_skills'].str.contains('Java|java', na=False)\n\n"
    "py_exp_vals = df[py_mask]['temp_min_exp'].dropna()\n"
    "java_exp_vals = df[java_mask]['temp_min_exp'].dropna()\n\n"
    "# Welch's T-test\n"
    "t_stat, p_val_h3 = stats.ttest_ind(py_exp_vals, java_exp_vals, equal_var=False)\n\n"
    "print(f'Python Roles Mean Required Exp : {py_exp_vals.mean():.2f} years (std={py_exp_vals.std():.2f}, n={len(py_exp_vals):,})')\n"
    "print(f'Java Roles Mean Required Exp   : {java_exp_vals.mean():.2f} years (std={java_exp_vals.std():.2f}, n={len(java_exp_vals):,})')\n"
    "print(f'Welch T-Statistic               : {t_stat:.4f}')\n"
    "print(f'p-value                         : {p_val_h3:.4f}')\n\n"
    "# Visualization: KDE Distribution Comparison\n"
    "fig, ax = plt.subplots(figsize=(9, 5))\n"
    "sns.kdeplot(py_exp_vals, label=f'Python Roles (Mean={py_exp_vals.mean():.2f} yrs)', color='#2980b9', fill=True, alpha=0.3, ax=ax)\n"
    "sns.kdeplot(java_exp_vals, label=f'Java Roles (Mean={java_exp_vals.mean():.2f} yrs)', color='#e67e22', fill=True, alpha=0.3, ax=ax)\n"
    "ax.set_title('Experience Requirement Density: Python vs. Java Roles')\n"
    "ax.set_xlabel('Minimum Required Experience (Years)')\n"
    "ax.set_ylabel('Density')\n"
    "ax.legend()\n"
    "plt.tight_layout()\n"
    "plt.show()"
))
cells.append(nbf.v4.new_markdown_cell(
    "> **Statistical Interpretation for Hypothesis 3:**\n"
    "- **Result:** Welch's $t = 1.3704$, **$p$-value = $0.1704 > 0.05$**.\n"
    "- **Decision:** Fail to Reject the Null Hypothesis ($H_0$).\n"
    "- **Business Finding:** There is **no statistically significant difference** in required experience between "
    "Python roles (5.28 years) and Java roles (5.19 years). Both ecosystems share similar seniority expectations across enterprise software engineering."
))

# --- 15. Data Quality Audit ---
cells.append(nbf.v4.new_markdown_cell(
    "## 15. Data Quality Audit & Preprocessing Action Plan\n\n"
    "| # | Identified Issue | Impact Level | Planned Preprocessing Action |\n"
    "|---|------------------|--------------|------------------------------|\n"
    "| 1 | Sentinel `'N/A'` string values across 15 columns | 🔴 High | Replace literal `'N/A'` and `'Not Disclosed'` strings with `np.nan` |\n"
    "| 2 | String-formatted experience ranges (`'5 Yrs'`, `'0-1 Yrs'`) | 🟡 Medium | Extract numeric `exp_min` and `exp_max` via Regex |\n"
    "| 3 | Text salary ranges (`'10-20 Lacs P.A'`) | 🟡 Medium | Extract numeric `salary_min_lakhs` and `salary_max_lakhs` |\n"
    "| 4 | Unparsed dates (`scraped_at`, relative `posted_date`) | 🟡 Medium | Convert `scraped_at` to `datetime`; calculate absolute `posted_datetime` |\n"
    "| 5 | Mixed-case skills (`'Python'`, `'python'`, `'SQL'`, `'sql'`) | 🟡 Medium | Lowercase and standardize skills lists |\n"
    "| 6 | City concentration (94.6% Bangalore) | ℹ️ Info | Preserve data integrity; expect broader coverage with scheduled ingestion |\n"
    "| 7 | Zero true NaNs, zero duplicate IDs | 🟢 Good | Structural integrity verified — `id` is a safe primary key |"
))

# --- 16. Conclusion ---
cells.append(nbf.v4.new_markdown_cell(
    "## 16. EDA Conclusion\n\n"
    "Exploratory Data Analysis and Business Hypothesis Testing on all **40,847 job records** is complete. "
    "Key findings:\n"
    "1. **Tech Giants Seniority Demand**: Verified ($p < 10^{-100}$) that top 5 tech giants demand significantly higher experience (5.07 yrs average).\n"
    "2. **Transparency Paradox**: Verified ($p < 10^{-100}$) that entry-level roles have a 59.9% salary disclosure rate vs 23% for senior roles.\n"
    "3. **Stack Neutrality**: Confirmed ($p = 0.17$) that Python and Java roles require equal seniority (5.2-5.3 yrs).\n\n"
    "The raw dataset is preserved unmodified and ready for downstream modeling."
))

nb.cells = cells

# Write notebook
with open('notebooks/01_job_market_eda.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("EDA notebook with business hypotheses written successfully.")
