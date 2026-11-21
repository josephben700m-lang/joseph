"""
AI-Powered Promotion Interview Chatbot for Nigerian Universities
Stack: Python, Streamlit, SQLite, Pandas, FPDF
Run:   streamlit run app.py
"""

import json
import os
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF

DB_NAME = "nsuk_interviews.db"
ROLE_TYPE = "Staff Promotion"
MIN_CHARS = 15
QUESTION_WEIGHT = 20
UNIVERSITY = "Nasarawa State University, Keffi"
# Change this before real use. You can also set it with:  set ADMIN_PASSWORD=yourpass
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# ---------------------------------------------------------------- questions
QUESTIONS = [
    {
        "area": "Professional and Institutional Contribution",
        "text": (
            "Describe your major contributions to teaching, research, and "
            "administration in this institution since your last promotion."
        ),
        "keywords": [
            "teaching", "research", "supervision", "students", "curriculum",
            "publications", "committee", "administration", "pedagogy",
            "lectures", "grants", "department", "innovation", "mentoring",
            "assessment", "courses", "development", "contribution",
        ],
    },
    {
        "area": "Leadership and Administrative Competence",
        "text": (
            "Tell us about a time you led a team or handled a difficult "
            "administrative challenge. How did you resolve it?"
        ),
        "keywords": [
            "leadership", "team", "decision", "conflict", "resolve",
            "delegate", "planning", "coordination", "communication",
            "responsibility", "management", "strategy", "resources",
            "stakeholders", "outcome", "policy", "accountability", "problem",
        ],
    },
    {
        "area": "Vision and Institutional Development",
        "text": (
            "If promoted, how would you help improve academic standards, "
            "research output, mentorship, and the reputation of the university?"
        ),
        "keywords": [
            "vision", "standards", "research", "mentorship", "strategy",
            "reputation", "ranking", "collaboration", "funding", "quality",
            "innovation", "students", "staff", "partnership", "technology",
            "improvement", "growth", "goals",
        ],
    },
    {
        "area": "Ethics and Professional Conduct",
        "text": (
            "How do you uphold professional ethics, integrity, and "
            "accountability in your work? Give an example."
        ),
        "keywords": [
            "ethics", "integrity", "honesty", "transparency", "regulations",
            "compliance", "accountability", "confidentiality", "fairness",
            "plagiarism", "misconduct", "policy", "code", "conduct",
            "responsibility", "discipline", "respect", "rules",
        ],
    },
    {
        "area": "Professional Development and Service",
        "text": (
            "Describe your professional development activities, such as "
            "certifications, publications, workshops, awards, and community "
            "service."
        ),
        "keywords": [
            "certification", "workshop", "seminar", "conference", "training",
            "publication", "journal", "award", "community", "service",
            "membership", "fellowship", "professional", "skills", "learning",
            "volunteer", "outreach", "development",
        ],
    },
]

VERDICTS = [
    (80, "Highly Approved for Immediate Promotion"),
    (60, "Recommended for Promotion"),
    (45, "Retained (Pending Next Evaluation Cycle)"),
    (0, "Promotion Denied (Developmental Track Suggested)"),
]


# ------------------------------------------------------------------ scoring
def score_response(response: str, keywords: list, weight: int = QUESTION_WEIGHT) -> float:
    """Rule-based score: keyword ratio (60%) + response length (40%)."""
    if not response or len(response.strip()) < MIN_CHARS:
        return 0.0
    text = response.lower()
    matched = sum(1 for k in keywords if k in text)
    keyword_ratio = min(matched / max(len(keywords) * 0.35, 1), 1.0)
    length_score = min(len(text.split()) / 50, 1.0)
    return round((keyword_ratio * 0.60 + length_score * 0.40) * weight, 1)


def get_verdict(total: float) -> str:
    for threshold, verdict in VERDICTS:
        if total >= threshold:
            return verdict
    return VERDICTS[-1][1]


# ----------------------------------------------------------------- database
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS portal_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_type TEXT,
                full_name TEXT,
                identifier TEXT,
                department_course TEXT,
                experience_score INTEGER,
                email TEXT,
                phone TEXT,
                responses TEXT,
                total_score REAL,
                verdict TEXT,
                interview_date TEXT
            )
            """
        )


def save_record(bio: dict, responses: list, total: float, verdict: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            INSERT INTO portal_records
            (role_type, full_name, identifier, department_course,
             experience_score, email, phone, responses, total_score,
             verdict, interview_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ROLE_TYPE, bio["name"], bio["staff_id"], bio["department"],
                bio["experience"], bio["email"], bio["phone"],
                json.dumps(responses), total, verdict,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )


def load_records() -> pd.DataFrame:
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(
            "SELECT id, full_name, identifier, department_course, "
            "total_score, verdict, interview_date FROM portal_records "
            "ORDER BY id DESC",
            conn,
        )


def load_all_records() -> pd.DataFrame:
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query("SELECT * FROM portal_records ORDER BY id DESC", conn)


def delete_record(record_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM portal_records WHERE id = ?", (record_id,))


# ---------------------------------------------------------------------- PDF
def _safe(text: str) -> str:
    """FPDF core fonts only support latin-1."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _mc(pdf, w, h, txt, **kw):
    """multi_cell that always starts at the left margin (fixes fpdf2 cursor bug)."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(w, h, txt, **kw)


def build_pdf(bio: dict, responses: list, total: float, verdict: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 15)
    _mc(pdf, 0, 8, "Staff Promotion Interview Assessment Report", align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    for label, value in [
        ("Name", bio["name"]),
        ("Staff ID", bio["staff_id"]),
        ("Department", bio["department"]),
        ("Years of experience", bio["experience"]),
        ("Email", bio["email"]),
        ("Phone", bio["phone"]),
        ("Date", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]:
        _mc(pdf, 0, 6, _safe(f"{label}: {value}"))
    pdf.ln(4)

    for i, r in enumerate(responses, start=1):
        pdf.set_font("Helvetica", "B", 11)
        _mc(pdf, 0, 6, _safe(f"Q{i}. {r['area']} ({r['score']}/{QUESTION_WEIGHT})"))
        pdf.set_font("Helvetica", "", 10)
        _mc(pdf, 0, 5, _safe(r["answer"]))
        pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    _mc(pdf, 0, 7, _safe(f"Total score: {total} / 100"))
    _mc(pdf, 0, 7, _safe(f"Preliminary verdict: {verdict}"))
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    _mc(pdf, 
        0, 5,
        "This is a preliminary, system-generated assessment based on keyword "
        "and response-length scoring. It is not an official promotion "
        "decision. Final decisions rest with the authorised university "
        "authorities.",
    )

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)


# ---------------------------------------------------------------------- CSS
GREEN, GREEN_DARK, GREEN_LIGHT = "#00a572", "#00734f", "#1db37f"
BTN, BTN_HOVER, MINT = "#17c08b", "#0fa874", "#cdeae0"
TITLE_BLUE, GOLD, INK, MUTED = "#1a237e", "#f5a623", "#1f2433", "#5b6b8c"
LOGO_B64 = "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dnYcPXpsYGBgyZJl058DwI033kiafGvBRc3wFQvFp55+ajI9ceFFF42Pjx89ehQAjhw6/PCDDyqAUrEIAP19fUNDA32DQy+++MKBA/sWLVpy7PDhB375q0Qseuedd5ZL5YP79nnSTaczTLC3bNx4yaVvGRsdfvihh5HUxz76sVKptHv37sxkuu/Y8d27dhWK+WPHjgAyANizd8/P77sftPrIRz9qGMAYFouF//2//798Nr2gp/tzn/vcJz7xiVRq4qVt25ORYLpQXrp3L2jV13f84YceXLVq5cJFS44cPrJjz+66cHiyWHx518srVq48dODg4SPHgqFAJpNRSgNAqVTas2d3NpuR0hs4cWxi0cJsNv3iiy986QtfeOftd3ie09d3PBINiawYGRlmBOOjYwMnTmgl+44fU9IdHRvds2fP6Njk0NBgqVg4fuTIkYMHtdb79+y95z33FPPFf/zHf+zs6HzyiSf+4s///Ac//OHE2NhEKpUaG3v++RfGJjPR4AnXcf7oj/+kWq584+tfN0xzdGSkXC0jr/m40/+tVKpDQ0PTzobv0ZbL5VRqct26dclkcsZG02+51cbp2+BcJBJ1k6ktpVJlWiL929u4ceOePXu+/73v3nDjjfFE3P9KMGhPTqZ2v7ynWq5YpmmaJiDu3bvn8NHj83vnSylz2czBgwc7OzuvvebqVWvWKSl937xUKh8+dMitOlqqRCJx5VVX5HK51GR6+/Ztl1xyqW1ZhXLl4MGD+Vw2HAwFA4FSoVgsFCqVysTEhGWYkViMtB4aHimWShOplL8liFitVh559OErN15+9113f/1b354/f/769ReODA1u2vTkpUuW3/6uOwu5PGk9PJ5+ctOTF19y2T3vfU82mxkeGrz6hutvfutbS6XS8mXLbr3tlo1XXNnZ0WHZlq9mhDAQGQITXABRLBLJ53Lf/8GP1q5d09TYyDgTQniel0wkF6y7gDRt37q1vqG+e15XPJ4QjF9zzTXd3T033nhzKBSsVivXX3NN7+Il999/fy6b27l9x5NPPvm3f/PXS5csCQaDAOApFY3FVqxc9Qd/9If/8dWvEME997z3Xe+686EHH/r6177GGaurq7/0sst8TeErQv+9bdu9vQsNw/QjLSJgDEfHRje/+OI1114XDAa11oyh70yfJ1eSnSNxRN9k+5F7IBAsFIqTk5Ozj2Ps8OGD3/v+d7OZDE4JMXIArYv5/MCJvmw2Y9k2Ahw5cqjiOF0dHaVSqVIpVyqVVCq1cNHiK6+8smf+fAAIhoJC8PHx8Wq5rKQ0THPhwkUrV65sa2szTROAQqGIbRjj4xOTqclQIBAJhgcHB1zXDQaDJ471cW40NDRUq+VyqYSIKIzp9eWcNzc1Dw8Pl0qlD3/4w9dce91VV1/zh3/4h0KIO+68/V133z0wOBiPJwKmeeDAwdb2tjvvevfb3/H2aDz2vz73P9/7Ox/KpNPRSOTSSy+77LLLly9fEbDtmVYCADQhERiG6XnuwPDw5GTK32HGWNWpRiKRNesuQMTnX3j++PHjq1evWbBggeu47e3tV1511YpVqzo6O5XWbe3tF154YVNLCwEEg4FoNHzixLGLL97wkY9+FLjIFwvhSGT5qtWf/uyfL1m2tLm19f/7y79atnJlOBKeTE9+9/vfr29suPXW26bRA/+/mWzG87wNGy5OJuv8kNx/SoeHBp944rFUKkVEWmsAItJTcRGeW5N9riTylMDS/7/juo7jnIzWpnYlmUz09vZatj0DM1LBUFArtemppw4dPBQMBknr0dGxeCS4bMni4aGhxqamtWvXvrRl+6f/7H985zvfZYyVS8VwKNSUTEjPS6fThmHkcrn//M//+Nu//Xx/f9/atWvLlbJScsH8eUrKiYmJQCBQ31C/bds2y7LWrFmzc9cuRGxta52cnDSEEIJHIhHPrV2tYZhLly7ZsWPH7//+H3zxi18cHR0BgGrV0Zo4FwBw8MjhhQsXLl64YHJy0nGrvk5SpMuOAwBKqhdfeuk973v/Rz78ocMHDzPk09YDAIh8OIYprQ3BowGrr69///59HEEI4TquZVvd3T1Sys2bNx89enTdugvWr78glUr99Cc/efvbb/+7v/0bx3HrGxrvu/+Bz372My++9GIikbjxxhuXLl363e99/1N/8Ps/+8V9vqrzpDcNTUwhV9De0dHe1ZHO5WOxeH1D45SE1V4HDxwcGhqaN687HA7PNM2lYrGvr9913WkZnQne/XbqyFflYvr3sHTZijvvvIshVspl/1f5XG7lytVXX331o48+uvfAwVgs5j+gSxcvWrFyxeHDh8fHxm6+5bZ//dd/0Vp97/vff+Thhze/9GIimbzowvXNzS2VarVcLiGi53qZdCZZV79ixYp9e/cW8vnLN27s7Ogs5HOBQKC1ve3Bhx5SWq1eveqBX/7CcSrd87ozk5NNjQ3rVq9uaWw6fvy467oAEA5H/+Zv/+Ezn/0z15OPPfLowf37tdZOtQJEwLBarezbt29+7/z169cRULlc1kSu62qicrWqlETOE4nEBevWXXzxJVYgoElPr4DWGgBN0xRCpFKp5tbWT3/6v0+mJr/33e9YlmVZlud6pmnW1SUdz921Z09/f/+KFSt6euZ7nmxqadlw0YYLLliPSISYzefzhUJTXYMwjO6Fi7/whS/cePPNJ/qHHn/8ca2kaZpaa9JaSk8ppYk8z9Naz+/tvfmWmzs7O4Kh0Ez4yX/f39c3OjqaSMT9S/X3i4jC4UjXvG7LsqbE9LyoxvMS2cx8GcZJO4gzkLnGxqZYNL5165aG+saFixcCQLlcXrBgwcIFCzY99VQ2mzMNo1ypeK43NDr+7LPPF0qlaCx29TXXvff970tNTrzwwosPPHB/XV19Ppvt6x8gosnJyfHx8UQice3V1wTsRyPhCOd8y5Ytjz/+eKmQy+aywyMj8+bPn9+74InHnrBNe/HixX//9393xRVXtLe1nTh+7MSxY9nJ9JHDh55++tmmptam5mbHcfr6+u++5576hoY/+OSnhgYGGWOGIRhjlmUhwpEjRzKp1L79+xFgcnISNFmmxRkzDYMjCMFXrlz53ve+b8Nb3gIAvqHwg9lAIGAaRrFYZAxLpXJDQ/PH7/3Ef//jP3p+y44VK1cZhqG0EkKEwkEmeCabO3r0aCwWr1SrpjCvvfra229/19Lly/P5bCGfu+TSSxctWvTMk5uCwWAqNTGZSf+v//2/RsfHCvm8VtLHwpExwYBzxjnzkfNkMrlixcqtW7cbhjmNnOsptVQqlsqlsg+ATOcsELGxqfktb7ksFovNkMjz+DpfEhkKBKWS/o3hNOqrNefccZwXX3xx2dLlvkQCgOe6hmEsXbq0b6B/fHz85V278vlC38DQfff9IpaIcyEGBweVUr29vY2NTZs3b37u+eeGB4YGBwYSicS+ffv6+/tDodCadWv37N07Pja2a9eu559//vEnHietlFR79u1bvHz58mXL6+qSDY0N3d09wWCot3dhKBS8//7nd+zYNdA/UCgXmWFcdNGGpubm1PjEjW+9/i/+x1/ccvMtoXBIawIATaCUQkRPyqNHjz6we3epVOzs7Ny7d+/8nl7LsrTWmjQAElGpVDrR179wSVppFQgELMsK2HYgGJyYmNi5a+eRI0ci4UgsFuvr64tGY/UNDaaf+NHaT7HYth1PJACgv7+/Uq0ahqGUzGWyx48dX7JsWSqVzucLV1xx5YoVK77z7W8T0KOPPPzJT967ZcuWNavXbN26DRnz00IzrHZNTyslK5Wq57k+VExEM2NmzvmsLI5/TDAYXL16dSQSmf7k/Jnscy+R09caDoerTtVxnEAgwKZuw5dIAhoeGm5tafOPrFYrE6kUcnHxpZcdPHJk8+aXfvzjH8cS8b/6q//NGfvsZ//0lltvXbVq1Yc+9KFgKHzvxz9+0YUbvvud7910081/+zd/t2nTEzt37Ny5a6dt247j9C5eODIyet999/34xz++cP36T37yky+++MLe/Qe2bt+xZtUqFAwFjybi2Xyhe/6CYqXy0COPvGXjxuuuu/app5/+1re+9a477lx/4YVCGJFo9F//z//95S8emJhMtbS1AEDV9cZSadf1hocGd+7c+e4771y/fv0Tjz/x/DPPze/u5Zxls1nHcQBZPl/ctOmpXz70yKoVS6+7/oZ73vOecDgcDATm98z/53/+P4VCMZtJL1m2rG9gYHhspFytLFq8tGf+/Gw2l88XSqVSoVAkwvr6esPgnlJKS1tY4xMTTzzxxHd/+KPbbr1lzZo1IyOjnivDoWg8Hn/8scekUkrRJ+/95Atbtl284ULGWCGfF7UUEWYyuXQm68chWulKuZzNZKrV6qwMkPS8YNA2bWPWho6OjlYqlZ6eHj+KZ+y8u3nnBCE/JWPmC+Xw0LAm3dLaalmW/8m0RLqe+/yzz3W0ty9dvgwAJicnY7H4smXLFy1aFIvHbNvq7OhYd8EF73nPe9asWTswOHD77e+8+OINL7+8S0p1w3XXX375FcMjI/fcc8877ri9saGhXCkHAoE169YsW7asZ35PU3Oz57mI8IHf+eBdd7+ns6szl8t3tHesW3dBIV+4aMOGnvk9w8PDt9xycyQSHRoaueeee26+5bbGxvrJydTGyy/vmd8jDNHW1pKaGJ8Yn7jl1tve9vZ3JBKJUqmYL+SvvvqqumT98PDw733qUzfdchvnDAgXLOhNJONEdMUVlzc0NE1OpBzH4YIl47HFSxavXLkyFApzzuPx6NDQYNVx3vGOd9zxrjs96QHSZZdtTCaSsUSso6Ozt3dBIpHo6upavnwlaRKcXXjR+ssv32jb9uTkpFSKC9HV0dbb2xsIhtasWdu7sDcSCdsBu3fhwvXrLjh06HA4Ennv+96zZs3agf7+Bb29l2283Fe03d3zrrvuekSU0nOqFdM0N2y4uKtr3nSsTUTFQn5yciIRT3TN65622gCwb/++XDa3YMGC07XjeVKWSHQuoc7pO9m2ZWu+kF+2fHldfR1n3L96KaUQolgs/fuXvrhyxarrbrgOACYn09KTkXA4EAhksul0elIIEYvGE8mk63pDw0N1dYlgINA/MFDI5zs7uuLxxIkTJ6LRaCwR91x3Mp1ynWowGAqHw6ZplkqldDotpdfQ2BSLxpXWIyMjlmU11DeMjY6FwsFQODg0ONjU1EiEI8NjTU2NdsB2nPLIyGhjU7NvmwDg4IF96XRmzep1dtAGgEq5NDo6mkzWWaY9MjLS0FgfDIXLpUImnYvGYozBZDrV1NQUCIRyk5lCoaC1NC3TDgYj0SifStAfPLAvm80sWbIsGotnM+lSqdjS0sK4UcjnSqWiZVlSSsZEMlnvOk4ulwGEZDJJANlMplKpSOlFIhHTtHLZQjAUjMWjpVIpnZ6sq6uPRiI7duwIh0MLFy0BoMGBASF4c0sbAA0PDymlO9o7AUFKWSoWCoVCLJ7w79TfLynV0GD/+Ph4XV1dz/wFfr7Ut+D3/+L+SrVy5513ztzcN5NETl/lwQMHMplMR2dnU1OTEML/3M9lVyqVH//ohwvm92645OJprBUBkCEQaK0JiCFDRAKamRrQpGufz+CzaK0BARGBABkSke9F1T6pRbhQS9DSFJ0CgYj8A4jI/6Lvs/tXopVSWhuG4btiCASAtauh2tkQUPknx1NSqv75a39tBtSglCRSQphEPm7rA9QI4Lt6bBY04acVZrp0U/eO05wBKSXjnCF60uOM+xm/uRO9s7MZ0xoEHcfdv3+/bdtdXV2hUGgm6+AbX/t6pVL53U/cO/PDN2VkY5mWYRhSyplrUTPfDBobEvGoNYdTgsD4jI0BnLl8HPgsbxVgxvFY+9VJ9xxPPeDUM86AAnDWOQGIcT5FFCLGcEpYZ6sEztlZMwd46sHCX3BEfqpywTn9s1mw37TzM1Ospm/WEMZMxPvVgn+MAYBl8dTkREdHZzAYnKWgSqViuVI6XarffBJpGAYXQimlYfYjKxg1NMTy2YETBwt2UCC6pCUyREAi0uDT1WqboWvZKiKt6aTy0ADIEAlqagShphJrOVqqHYkAfgjsq0x/QzWpGtimCdlJbYQ4nX8CPznBkCFOcUmm1H/tDTJNqIERcgVMARJjJ3XvlEQiok/IQwJFGgg4Q0IGpIEAGDKaYqkA+jQvBv59+Y8PIlBtWQgQgRCnU3g0ZWIYgNIaARlDQgStARBqC+Rr8ZOMO58dB4CEoJWyRSKVHt+1d0s8GZ1e25OkSeUpJeENfJ03ibRMIYRSijTNeso5h4a6wEvPPL7lmb0dzaZlVEl5DBAAfOvo75+/Khqn0pR08rcnc5cEhOAvISPfuJ4CmLEZ32JTX555zpl/dA4VQlPieJq/RIgeiiozixLKBJ4QivHTaTA4RZLBKSuN5MsoIRD5coEMEJCmcrEE00JMePIip9/M5XvNfSTOdWMzDyCtw6HYWH9h+0uHVy1feRI1PxmJ82k/+I1RkudSIme6pIZhTHOtT1s/GbS0JaphK9fREAwZJSWrNQOHp/k9Mz/BU/hPOONDPOsBZzvn1I++H+d/ncEcX9FT59QADEgDr3K7wE1VqJaqLpmWYlwDMEAETbVnSiMyf2FmWds5eSrTP9CMN3jy7s8oFWc6Es/AHZw+QGtp247DiunCcNUpnu53moaptZrBQIPzHdmcLx05XaUw14JoS1DQkhTxOhplxKx4bhkZh5lxzJxiRCc1HKNTd89fsNoBdFIFIpztnDNRAqydc/rNLDUz6wCNrCJ0huuKVXHKjmNqlwsNDAAYaCBGAIAaiJ2aGXlFqinNJabnSzspJQOxaiAukUt9ijWbynSEQ8Jgcwr0m0BHzoqCZ2nNqVXWiGBbnLxitTAMToDhJDhFZIJOXXecSyBxamOnfzzTAXC6xJ66vTTjb8w87eyvTxlQNnU2NmV+NdlSB6X2XPIcDDloUO3bU9UROLV905b4t+qFJEk6jEmmkSvG+OmZjlA4ZBhizsD9PGVuxBu6AlNemWEwIk96ec60wQrESsjwjQrmTi7rtLSdZWk1nvQ4Z96IRBTM45yAu8QlcARuaPBvY0oiX0GhzKkOz3L4lIuM+pzBx0xqXkEuTEtwPsdlmIaJs4L987xP50si/RTtbNrSNBiIggiklKQVgvbdv1pUS2/c44Fn1B0nYwh2NnnSAISkkTSCTxnUU7c4rfFpbumbiv2nzvNqBHIarqJz9UgCaADNkJmGxZhx+uNhWrY4rbQN36QSOQvin4U6agKlgIhpYNqPNs/VszdtH5FeeVNezcadTaT9mkgGhECIyHzYZsa3zuC9EgOf54Bw1qAFXjESer3iOOVsa0Bkpmlzbpx0VaacLtM0Aaw3a6x9qsus9FTOY46YkDH/UfehRphR6nGuLfNv4mWdzffz1SjzUUycoXQRiGgGEk9nAibOqf19/YbCL74OBAPT/iIB+DCs53mc81PUyvmOa86fRHqep6ezebMfbwRkjHGo1bTjTHt9Dtxl/E0l+7UFIdPYHvPx+dnpn2m0/LSLpDlQqHNrBF7ZZ0E/QRUImEKYs8TO8zxEEIKdjMDPf3h2vshFruu6nuf3bJhTQzA6dVPetC861S87s8f2ii7da5Wn31A6cIaDikIY07H2tAvsw8l+qdcb9hLnTyLlGSWSgDRphVNJrVkY2Jvn5euMqVt4nV7Hf/FDSTTFDpn9eY3qOxMVejP7kZ7SpGdK5BRpxc+QaEJCDuj7k/6ivDZbOdtyIb0um/uqYaC5IzTm59L1mW3vKyqzV6vtZnAu9CsJGb16vBBrztPJo6elU2vNuZiKeGZ7kee+ecD5sNrTCs9xHM/1ZpKXZuBABKCRYY2VQ4D4JlOQPjVtNkh5BtGaSSqbQyBOq+t7fRHezPO8jlpBOoOKR8RpHfnG7NH58iMrlbJTdbjgpwFABECgJWd00mX+L7e+9HqCBDyXEk5z+IY0l385Rxrs3MB1s/7WjJ515+GO33irXa1WXc/1S+BOefp9Fph0OWpTcASg1+VInUSJX6+xPmWZp83263Mmpwg+Z9JeZ7UqNVFAmk3cpLkYmadoKpqOgudQw6+WCeHviPKI5BksHp7nB/IN0ZF+u8dpGukU8QUREEi7rgNApiHQtxZvvpjmVDeQXrMPOsuUn+ymiaABiTHFmGSchAE+BwVAEmhuoBlQyDUxQAHsbD7oq/UjEbXWnuvMosVM9+acJqXTG5JPO3860vE8zzTMuXZQe56LSIbJCdSZlAu90uN46vOL/0VB60nDiqcFZ6dGdWdRXTWOsgZSiIoxV0kNHJiolsoBBhFLKAK07EzRzRVyyXAoFLA0aU4KQZ3k451ZLs8mTIhK60rVkVLNulpfWOcicL15/Mjpm6lWq57nCUPMiLJnROLK5ZwMk5+pzodw9r85Qm2s5X3oN8fEX+kcc/0eT7YpRHqtrv908OFnrKjGLEZCLhnPVt1Jx5lU3tHJyVSpBMJQyLRhjxSru0+MT5TdgqKC62mf7fsbYUjkPwnlSlVKefpF+nVL/y+gP34BV60yQeupoLvW+0YplzOyTcHQPTemAP/rofZpNvvZo+YzGVO/sAKQE/JCVWaUK21zvFIJmJZmggCzZSdVdYsIKelWszlLUThRbzGmtAMo6QyQ0DQSNOfFEAFD0KSrTkUqt+Y4TBX0+CV7/49IpOM4gHOiJkik3WoFgUzT8MNJfCUBw7PAkdPkGjyPwjlX2FSDV4mQ6BS4brqZzql1W0wTAQFjAJpORlOnRH4AyFCYDsDRiVKGlwMWK3IqlD3LDAyMjo0V8xgPDVZKwlOtVqJLxjhy0kVtlglcqlHnTrnumkRy/8IIT3OLiKa6ZJ12b/8lEnn+IhtPnqFiiEBXKiUAZVkGAc2kLp/mW50NPqbTFvG1iqLPHtPENHGlURO+dvOHr4IdhkTgSgVccMMgOgMqoJEhZ8C9iioV3WxZpqVyglbWcyZyRYXGZKGSqbg8HCghTLoyX4ZqQQgZsSAMmp/JJHNhcGF4ijThdP3X6RbNj0RnOQA+VEJE/y/oSL9WcE6tQpoq5Txp1w4Ytdo9eMOjbUICIGQEpkYLwABUCA5AFWp8zdfhQ8/Q06dWtSqCqvQ4omUaDJg+7QlixJAEaSarWpaUnJQhBpCwNcJ4plIfLNc1c2mYJQ22q0xuM611VWlLKu2BrRg/3WYjAUrOPASSkpS2OGdzMTEZImntOBUlPZim1hMBok/d+n8kspmJGsxCd0mrUjGvlWNbnAEh0tRMhdfmNzI6WRADUPtx2mSfLQ9ECH5JqxJMJNBqEdGecMMSZjW4yvCTdDRTzuiUN6cuHzJkgBymmDEnu7vOCLSJCTDtoVR6aCyFVoC4UESAHIj5WCJqFjYjKiuL/fl4xWrVsbi0hQPS8XIlSJepanDPYkUFuXxJp51IibeKcKMVSA/2TwwNWMLkyGcuodJaMQah0NHx9IH+EW74paF6lsLDGrPTT4QqOM0ouU61Wi3/v6AjEc/ozxGoUjHHPcc0OJ6BPo1nhc59r4emhpNM1WLPdI58OIV8/HNWJR8Bkwq4iKARSWXdp17s37qrEgoFb70hsnppwi0XGVUR5ZkeEr9g+sxQ1Wkm0Qf3hOkS5nN50w7Wx6LCtLV0GQARcCaY4rnxHJV0UkR5GeOuEQdrouSUlGe4oOKshKQCBtpYrbjVrNfMwy2RQEhLbUAZyK1UyUZE5us2RVrYpoOif3QyVSzHbRs5Q9JAeo7HVBMBcYE13X2yJKOGmcip5qhvSomckVplyHDOfSPSpVI+qKuGMECeOeeLZ2F3IQEiciYEAEPgAMzHmBiwqRVVAFIrCSQR1CnqFRmwAJpNY2nzV48d3PKyeWKkE8gxA1VuhBZ0tDCa0CrH/XJCBDgN2sGzObRzRdmkOejGurohzzsyOERCNMaiID0feDBMgxw8cXCgNda6oKszNTQeFlaSW5ZXMoDbNoFJE8ViCZQRxWCBBaRutQOtlm1qp7e7faSYOj4wGO9I2EHLU47mqLnhMSOTL504MZioi87rbCHPVVrV+gvMXkwCJG7gdDfgmaCp53nuVPfhN8afPF+RDWPTXUpmW22tdbFU8FRVCAQgDXO4+n5fCPSro/UMXo/v5SESGoQBjSEFUZdiHsQkJiQkPayT0CCxXvM4YZjAJhA0tdiATCGX2gSzYaIUefi5wr9+3e1e8c77nn7oG9//lx0HGz//b2PpSoNiUQ2nGMGZJns6teZnazgBq0E/bM71ZABcK65kMhKKxRN5BUfGxyYKBRQCGPoYGSnITbiVtAoyKxGNt7c11McCYZTzGoP1iWC25PWPT4wVssrEZDLckwwtjsa6wuG6sNFQH0WtxwczqiwMFiRCxTnYwZFs6Uj/oCWgPhSwAVittYXPjtbTo14QkEgzRobNGddwmmWSUs7Skec70DnXOnJKfZim4EKcSUfm85lgpCxETOHMbMbJ5DLVnDEmTKY1KKXQb5/M/D4BDJiRK8DoRNmVhiImNWhFWoKnQEoGxJXr1cXV8iVW0FaeI7nf7oJZhhlGCI5m4JFnR7/909SRSchVvaNHDm19/ulDJyZ11XvoieM3XRltCCWc8rhp8VqgMzd7mmb8e6WwnhSBjjfUNTN++NgQx0x0QYvQqJBbjCMng5MAEMBMgSi9AIemWLhoiYznpapOdcIr2NKMioAQnfXRuiqnYp5FTcGJNHmuNoTFmKmQKcbKSp1I5cYLasWi1sbGOvLkTG9nylc8KVrI0QoKLmimjvR/ValUHKcycwNndiN/M/iRPr9Ma8MQhmmdIfpRxULOM6ucM4VzhH8EAMC0Zq4iV6IQpmUA6ApOud5KCyas4/3eAw+VHQ3ChooDSoNW4EmQEhiBrsDKJbBoYcgwDKdcZoIRcAJzZNTYvFse6su+sD2/7zDFo+y555/Z+uK2Q0cOmgIE4q8fHb54XUdnZwxBKq/IQE0lls+CQU2XFdJcfiQpxiUXk4Vs1TStZFSNpIbKhfpyqDEcN1hgLFtxhov1jdHGaEB5JdtCdF3lVDkn5cqqlCXQVdCKIzAg0qhBVl1XkxUSlUrFsO1wXWIglUkYbiBuVlEOZCbHnbKOB6uR8LBbFZVys2nbGknr0zlzmggYWLZAQ9dM0oxXpVJxnOqb3o90HdcQhm1bs6GQWtCqy+WSF65ynIKYa0g3nazoR6E1jKecQ8dkR2doYU9QuR4D5ZtvDZzz4GTW27W/YMV4pCFZKkeA++RZA5i2xSjqMnFBKAA9jUjIieyKazy/rfAP/14YTkM4geEo08CG+4cM0EETGGepSd03bBw5ga2NASaTQaEZKCJ1GlB+klgxo1ERzekMayLFuGdafcMjY5VipLnRrhf5rN43OanC0cZIuK8vlTo+evX8Ba3xOMlSOBqJsRAWoVQsQSCsOboCRNzymOcH0YViSVE8EotbtlmqOGY4GGttevHQwXYjubi1fbJQPJZOlQREGsLHyvlCaqKJ8/rOLkTUSp1W9oRaKwBm2UILCVCdlfB1Pc/1vFl+5Jum63OtwSGQ4zjBYDA01R10xgEagJOmcrHsxsqMTTVEwZMxhK8gEQQBDY7AY0/A5VcEli8Ll50cgcuw1ukMINjajjfdmuxecVOy9cJcyeR+Z0kQCCpij+eGH2OlZzlTnisZY4SmpMh4mvrGikXJq2CaxLWuyipduLppSW/k2ImBfQcrSOC68teP7n/uWbFikfjAu9sZjecmU5YFUxXZ+FrXhAhBcG2Y41k2mNPz6iUYRlUYfWWnPNy/kHd5QcHiIEI8logYVapWy4Zp1CcTESgYgaByyw5BICjQkeRoNFAIMx6ri8cTFVmtVKoqbJl1EZ40ZcRIk+7PZSc86QrBAE1mpIsggDQyZNqvT5tyjWjqgdGM82DEklTxIM8wgjPYBu6MKTBvDJfl3KM/pKhSqZim6XeuPk1lAAFJVyklGUgGNNfzhkQMUFYdGB6FfNFEbpHf/qmWVZFEOpkQzY2Vo0f79hy1JRhQawHFgRRXmcXthbULwgafULJC2lMsFIx2FQczJ4ZHC2WtVQUhZDBCUOuWh+6+Y+mhg4H7Hz66eVexUKTHn80JgsNHgVBcu7Gusc5QlZRA51UQjOY4AgE4MUFcuUZ6AEGVA83CtZgjeN6GEV0ShiviIutUCmWnTgRIS6fiCsaTsXhKoLC4oZhULpAGQoYinqxDJfKFMrNAMUpXi+NUhAa7EIDjpdyYdKsW85BlcxVRdnN9LBExmOKMa5qzDxwB59wOck9Vy7IQFpHZLYfe7DkbpVS5UuacB6bGKOFsBEVNFddIRD0XbIl+ysswwTABUGhtauIcOTDSBEoTB0967qEDfV//yfHDaQhw8PF4ZKAUeAC/+7bAht/v4MxT0uPcIhHPFM0d+7xDR3VzS2LJytXFXG731u0XrLTXr2QLWnLtiWg0Mo+JwUc2ZdEIXn3DYgO9r313d10y8LabWgqlPDAXax4GnRl4P00iEZEAFRqKWcC8NI2WynVmEFpABxlLhsacEpQqLQEr53ijk1keIAYsX8g7UA1F7FE3b1gyaBt56RAHDaCVCoVDlXFnvJRrbKsDIcaLE8fdiXJUTMqyky54hnAsrSSonOOecNx+sOdZQgrgkmAOChMRIEfbNhynUijlwrHWmeqQn0oif3NKpFaVcsW2A5HTrHaNf0CaIQhU6LtoRDP9TD8Xo4gTmopUuVqteoaiiKcjgFqiVgRScxNNrVypIBSEeJmbgSAojUDEuNLaKZTCQZshakLXs4OR1qJb9+CT+77x/YwLDX/4x5+684N3fP/L3zm0bfu7blt09aXh4uReJoyL1y3uG4JdL2dbunv++//4By2dP3jvLZOTqUolBkxgrZXo68kuMiKuIKAhHgEzAaYl8hIKrlPNT6oURMGYV59kGdOpqGK5rFzPUY4ZNm2DKrmyYzpGzEZPguYq7xZLRR1QwhLc5YiAjFU9t+CUMFSfr8rxYimUCDocwIWAwoDGeICaQsgJlJrrWULUpBiHQMgqlQuZTKo1NnPqEghhCOG9Ae7jefQjtdau45qWGQgG5sSGEHTABFMoIHeq8a2fFEYA0AoITWHGzEDYtDOOGtJoG6E2LFTzRVcIGQwlTbAYtzw5KRUKEwOBALcsUgoBkHGlFFpVIQSiwUVdorF+smA++uzx+x5K7zkib3vnins+9NEnH3v8sQcfft+76y5eDTZLVb0skGWIcmezbm2AoaGxxx95UBAfHtEAhsE9jzQxOoUlOYNqNNUniE6P82rNj4hQumHhttVDoCGWJo1Scs7cigYTKoYsMc+ORGOBkOUwR8qAEYg0RZVQqUMnUgFlJT3SOhAIlIflSJ/EOpFMhjWBMJhlYTQcDEEgJ5U2ASKsjB4gmAAovSBAZ2uku62ekSat8TRth+R3WQHLtsrVYjaXmSV0oXCE8Td5dazWulwpx+PxOfzIGvFOh0NkGZqUC6f4kUwRR25qsEcmdNVzhyd0xWPpgp7I8clcaOtLOp93enq8pibsbI8DC0lFUpJSCpTSSqHf2VFKz1UaDI1WKpvPDskd+4o//dXQUy/ByrW9d7/3rsn04D//zf832XfgL/9oaUMolc+kLQs16EpupC6qly4yt/9i4u/+8p/aGwOtTbyrM8rQJZJnDmro7OlE/0FD5dXHBEFE2dFcfgI9N2CYrg0UBPC8bLEk7MaQYZmkrWiIkeLBQMgGK2AL00OBIEkYKAxhChYIBixTVAUAkhAsEY0kMZaq5lVABhKmAo5KGkraWoUEdDTHWpvrGJRB61ncFz/V6tstQ7ByrpAv5GddfDQand0q500nkVLKXC5Xl6yzA4FZ7dGwxgjU0QjaFmjlU/pqNkJrRjxWdIJH+8svbR0anVQTWcgUYffBsfsf2lsuFH95f66vv9rbm1+8EO66vTFgt7hyt/Y971rWi/w6LE3AjXDJiby05eWnnu/fe5T3j4KH7IO/88ErLrv6Hz//38PG4Xe8P1EfZRYUPKww5ARaeZmWhuiGCxq37R9/erPb0eR84D0NyxfzSrHIuT5N5qYKCM/MP59CkgFJAcimunggqNNlL8R1WoNGDMWD0iAnXfCUJCIttZbKMgymdaZSmUAv3sWTwswbAqXruNJOQKslHKOarirQDkoKiFjEDoe9AJYylXLVs61IJKAKpQCwRJBbATcaZuGAcKSm010O8osdiTPkHDPFfC6XnfVQRSIRwzBqs9vejFa7FtmUy2zOIQa1BoQqHrPDIQBykNRUux/0lGWHW/cdwH/41+Ej/UqYUK5C1YX09pGXD46QhnQaXBcmdsLWvbBynXXR2s6KjHhUQNTTQS75GR3OAqFoulB3/8Owax/kHQWmeMftt91y242jw0fv+/6D77wx/q53LaXcUUlljqBBI5CWhUg4uGhBw/Il5a270jY31i5rbIznirm0EAqBgAHBVMT/6pMGCACKtI6GLMtEqZz6oMgxL601KXIc1y1pJIbIg3bQlF6lVDYTwTyVtw4ePYH5nKCK8rQgN1MFB8qCdg8eDUXbWyJ2sVyqj7Q3R0XQSQVcQxUrpUlHSLAdWR8KN9jCyUxycDj3QJ3kMyGiX3BHgIREWjMGhikK5VQmNzkrOZVIJKrV6ptVIqdj7Xw+fwZSHQIABx2L2kETgVwAPT31gxuhwTH3wSeyL+7w3vORu9dfvK5YrJoW1x45jkIGoSATBqs6upQv943u3/zVXccHlFTTFAEAAoFKglOQOl/URSdytN9Il5SrqS4R/fjvfjSVGv/Glz5/yTrzustbIoFyfjJHTPpdSH2kzmAyHIB4lMIBDBgiYCLDClNlLvhZEZ8z5gumgD0/N88sLpJhsyJiaY8mPaecK0tODIkBkNSlatkpOIqIQE94pX43OxHQLkfgzDANz/IIuUZrolIeo0rcsnkVUpPpgjIYAhIELVNZ4BQcnoNgTLTVJxnxqGl6XplqmZhTYH0GoACINCIxAaVKsVjK1343dWAsFgsEAkqpWYXObzKrnclkfFh1egZGDR1BBPDIcyIRM8gYaM8fVQCakDHTCO7dMvHi1lQ4Dm+96forr78zk5lEzjgQZxyAaamlJjtoKifzh5/83W//eEtvM0htIHJ/4xnTpDzBnY5ksKU5qQiYIMa154HSoqkh+uyTP93x0mP/9y9Xz29z0/37A6ZkM7j+DABBallxqlXSpEmWSzmKu4yhrxinu7fN7mT/ChXZ/tdIS5eBjgTMppB1Iu26uYpLbqApyATKCSW5l85lseCEG5MprzCkchQL8IhkgkAgIEJQcpMzZnlIo6wa0+V6hn19A/m0cGPgVr1A3BBxMz3iVnMAghraw7FgiFUqnnSmWlXP8CVOMc+ETLtu2XEqs6x2PB4vlUrlclkIwd+QEOfcW20pZT6f96ZSTzPTHIyBluViPh0OmiEulHamO+YgISEWSkwqIITvfPu7z7+0I51z/PFciMyP4kkTF0J7zv4Dx2IGlB1GTCAyAg3ABFelvJuMsA994JK33brmwN4+KbVWYNngebkH7/8mquGrLkvEQ0pQ1uDVM01O0JIAQSpVKFakJBBCgeagXhEcnx3mzGA1ITEAIJJEGLYDljZkDoQFIcv2XM91i54gxrkOWaUg73fSQ6rgRhkEDQLpKU97BGXypMwGSmBwAaWAYoZnConSJbcqlSaNoJE4B5BgeMwiIM+VWrKTTOZaqobwZH15rZyTa0+XXa9ysp0B1ay267pjY2OWZQWDwfM9OPZ8xdrFYvGkRJ6E/gEQKpVyOj1pGswyuNYOEtXotgRaUTTMAxaQhks2blxzwUbXlZxzv788ImhNRMQYV051fGRo78GjhEFCTlNT1RkHzyMgvmrFvM6Ops0vHdYaFEEgzKTnfONrP77+qtZbr11mmxnp5AU7pU5qmiiuNLrKzxhS1VNSI4AA8OaMsH1C16tJr01NECEgKYBMrYMakJlMo1IeMdJAdjjETSsTwdGx8qhXyilWLGmyGDOYJsnCjEleBZ3n6BZyIU8tjnbHg0ZFlxyZB8Zdz3MdHQpYobgbt4BL0lIBqVkUOZ9IWptb5YOPqAmkIsfTzgyrTaTBHwHT19ff2Nj4JpbISqVyevGv/yoWShPjYw0cbVOAKtcKARho0NJxlixuWb3SPXhssqen5+JLLi6VfFhxJkmKOONutRxL1FdcSHBrZppLKWaa6JF68pl9g8MT27cfqXgeMxDRANJHT0y+uJkWtIu2SDUY1XBayZbWgNwyrRAXgjNwXTkxka90miGbK3WueNSIAEqqkInNceHYIl+teMqxg4K0ZoYQ0UDRKGeFKkjlcs1MoTlq0lND5xAM7mioFNw8uRA0hbRKmUzGLYqwxZGq+aoJoqM+1GIFUHoINFevttNUBSpCT6OnwVOgZrjlhIDlcqmv7/jKlcvhDWlrcR7y2lqfPliJph68Qr44MjjUNE/blkFObS4NImjS0qss6G2+/JLQffc/86uf/CiXmxgYdhiv0adwijckBHMc9/CRw0GT+SPupmdYSYlWwJDgfefHzwMBQ2AMhGVLTyCjZIOxZUeaKvm1vc2tdaLqAmOIjKZC9Bp71XGoVASpQCpdLDlKCsZQqal8zSv0gZ6y3XNUx04VYCBqpZLhYCdT/V7JLVXRhkAoQAUtSbvkDpYnM8JRYcYCIpQIOZ5XLhZBAhRJmxpC3FOKB0EhS1WKgnS6VBivZESyIWiL1Fi5VHbr2puaYjEsV7DWZ+MUWB9nPOL+iFQCTSiZIOTahUrgJPkFAKBQyJ04fswfyf2mlEjGeTgcFnPAqgSAhUKhf2BgZbtnmMKpztxfInBBZ6MBpy6Bw4NHtm8Ljac5MgTSCOiLLmNgmoYrZblUMi1Da+1DGdOcAY02kel6nlLaMIyAaQkutNJKSwLwACSBaQQ5r5zShZSAAAxhFAuZ3XvS23dVB/OwZlFw+dLWeLzgVtOMEZ5usWsFU1PRdG3YzdnYrLUOClLWhYIF5AeO5KohsoOCo6EZgmVUmD6WGx1jxaqNxarHskVhiYBtu46HCTQskwS5UloGVlw5Uc7UJyIiEXSVVqQ5cOEKmZVGKw8Y6GqF7IwNBGc8JACgNblWkAsDSpVSIOBP8KwVnBSLpb6+vmrlTSuRiBgMBs8E9JfKxdHxUaUYCq6hNgzW3z7OFLgZctPtzXTbbZdesPFt/cMoOENQvguGjBVyuWKp5FTKe17elS5U2xqDfiw1NWkFNDEEbgdM0zI9V46OpzwCDhANCSNix0KsqVEEgwYgzpnj1UomYvaVlzWO5NKgVXtLxAgWKgWPmxzOKGN0VkjotNQiAZK2uQiSVlmFAm0hvKoensjkrCadiIxU85O2IosrSargSccTpkGKmIFaKVVWWmvirKjdgeJkT0eXZOGJQQw4TsAKhDgHLg3tkVJsRg3XWTvIAKHWIANBg5tQKBbqAv5451ok5zpOOp325Bs0r/Mcz/wCAIYYCoVOH4IyFdkUU6kxKRuAi1MGHQNwprWbb6irXrbBbm5ICBGvr1MMORJpYITguG5LS0tHR0elWNi3b++BQ8fK5bJhGEJwpXQtITQ1iTWXyXAhlq9YHAyGnUollxkv5ifCQehsNS0LQGs2U2z8ATRaWaa9cllHW2/HkcN7J0eHSeUJKuyVmwTQXB/M0QEQp7tOKTKVjpmszCUjqFacY8OVnmA23hquGKxqoGEzE5h2SUvtlSVIIoNAK5KEAeQGr2pvzJWVEFTJnHQoLl3msJCA+kYzZDLlqhpKNdd8z1MaaQBoUAq8QMgUBi+WC0pLwYyZ/agYY29YRf25l0ghRF1dnW3ZMFVcNGWUNQKrVIqTEynPiwFjtXKqKT+HMV3MTS7oSYZi8/70b7/21PZ/b2nnnmRSCU0CgHtK33nXXff+7seV61533fXZbPbHP/qR1tqyolqfEnkIYRRL2Z6ext/7vU9ddNHFBw/s++EPv/vUkw8Fg6qlJYrIgGB2fwd/vjxJIoejyxlxIIEeogYG/pyaMzoq9Noa1TNAcHWQQ2dToKALhZLkirsaBivVqpNXQRMtV3MmOOc255p7BVkql4iDCAhA4AYXjCvheRxc22BCiwQooUqFQkLx7taWiBmQnme+2q7P/qhoNxg2TRLFYk5KR5gnTZxl2/X19X7jxTcAJD8POpLzeDxuWdac9kt6nlMmf8TxadCyRnI4VRsSzm3XiIGB8ef2AgDYAFUABvCJT3wctHrn7e9C5TU1Nc2bN++973vfE48/PjA0EouEiTRyxpG5VXdoLPX+99190403/uAHP/juD34SDwfCkdC11990dN/OfYfSrpcAzjXVyshOsV9AWkvQCjRpDXpm/fcMhHxaJ9Yqwk/fJzxzC0JfdblOkGNXU92JlDdZcoOW5YadtO0hdx2uFRB5SjsKNQtZAVOIEgc7aFsx21Oe9DypNAfQFkTr6yq6wsKANqiKMsioC0dsQO16NB3yzVTxs3S2H9kQEapAyMIKpdOTruPapn/LDADC4XBXV5dt228+iaydkfNkMjldZDNT4ABAK5Iu0mk9hn2WmmFgtZKXBO+6rbOluf57P8ulStQ3kp7MwYLFS9atXb1r58tHjxzp7Zn37LPPuq77iU984sD+AweOnIhHg06l6rjSFMI0MRwKzeuaF4lEdu7Y6QEPB6xwJPTxj3/Iq4gdm39WKHvAmKY5axQIAAyDGYJNu5pEZytnwDPqxzMKJQKR9ixhJoPhwKTQlSoEmFEvJnkpl6GqlgCoPAUegQuOQxz81gCkpfKqnlQeaGYxhjY7NDAwyTwR5CCIEQQQTCI+lbjE2cPvztiTgUAHgkFZdsfGRqYLtP1Cvlg00tvb6zO53pQ6Ehmrr6+3pwjkMwIAfzkUEIFWMxaHTpoPIMEVo2puYnDt0rZly5ftPMj/7l82KQhdeMGar3z534n4v/6ff7z22uvuvffeQ4cOVatVIYQBIKCcCDoiwsvVqmZ8/bJVTzz+2EMPPXjb2972e5/61AMPPPDnf/7nkXCss2v+lqcgny8pqZGd2r2h5k0SAw0kIxFyEoSop1m6s+u1f5OF8nvLEAnSUYOHKgCeDEYDuWIlN5xTzYYwuEcaGZoBzquKV704R6daLblVLQEM0EDcMJTBnti8uRREUW9pxw1wqLe5oSRqnAuJPFPQTX5djWUZFekOTQ5W3bL/K59OGY3Fent7LdN8U+rIquN4nhePx207cMoNTPnYlunGosA5wVw9wvyKPgJXoDZZigu7LhoJGDpg8GjETqXG29p6Vq9cGbBtzrkQolKpAKJCiATkxvXhy9+ydNf+wg9/cTAcNofHMpl0Yf78+R1dnYYpiMB1FQESYaFYcT3NuAAiQsWmBI4IGEOtZS6fS8QrEROBJHia4zR6N1siGRADzYDOpH9qHa8IANgpnaERiBRJaIlF80i5SsUQhggFXcQceICIDBAwZNoRrWOIoWhoSOUnwGVhq+o6TJIEKioPw8IIiIrUqkKN4ci8WCLgKUaASDNK4c/Sr5Wm2yNYluE4TnZ02Icep+8nHI51dHa5nletVmcrmt9+iSyVSqViKRGLzfAjT9GFAVsl48A5gZ79EE+7ZxwVcu1WJh0wAoZoTAQPHcvt37P9prdePzSS/b3f+1SyLvnwI4+sWrmquanJNEgRRgLiqovrb7m+MRxQDz2u9+w5esvN17S09fzg+9//9a9/PTQyFAzYQpDr5A1BgjOsgW2nuFeaiINwPRgdz0hVDEe45zElsTaCaKqK99QY/fWrDQ3EFDUEQnnXK2eLrlsJJOKRkFmCHCEp0NqVWkqjpOqMQGMoVsyUc7rKg1B2iSMHg7lMRaNhw2CVUl44lIyYdXbYLDlsZhuQV6Eo/cvhnDvV4vi457rVmbbLsqxwODo5meKcT0vk+UsnnpuinulAtFgo5HI5OxDgBp9dAgUaQNs21CUZ5wRKnSm/hUAMNQMvaMuWBh4PBQbGiju2be3s7OztXTQwOHT06PHe3kWLlyw5evRAMTeOQJyouz1s0GRTvHj5haHRwXFP8rVrFiut9x04ErDttWtX9h3bf2DP/pANiUTIMlEp5c9H8Ft6aiKt0TAj3IxPZuXQqFt2LTvcyM2YJOaPcp+jPRq+zoFw/kQcoSGKIk7MlFoxVWZuBSQj5B4PatNWvDJeYQW3nhkxF1vAjpeYGimzihaMg+Auw7LrqqobUljHMAKMK82AkOi1tHWdniqEnucWizmtXZ9o4IscY8wwRKVSqVQqs7b7TaAj8/l8OpM2TNNPcJ/C20UNUA4GoLE+bAiCGf1OT07dmupd6H8s0DXtcsjyggDlQvXHP/rJhz7yyc2bXxoeGmacP7Hpsb/9679Q1Wp7DOriKhlD8FILu4z337Hm5Zf3ffVbP85mDvz7v39h/uKVA8cP/OqBn/3o+9/Y//LwDZcFknEDmfbdp9oIMgJNXJKpWMLTyeHx3PEhDIYtxRo1kqcKhnAYzs39wVNasEwPy56aJEsn5ZVOCXmRETGtghriyOMWUsLK2TJTKSgFjGE0ErStSM7Ntkai8+P1uiKXheuxwnYMj/FmDiYvF5TnKgZegIwEmnUhnjQtpjXCa5pHO315ujZIA9QUc8Wn9RIiM03TdV3XdWfFDOej3Yo4VzrSv6x0Oj04OOhfqCY6ZTYPKYBKwIb6+ojBibRCPD0IrekdImActKq6pcnbbkwWSvC9B0Ymc/sevP+bw/37cvk8Mjh65MDkaMnR8LYrmn73A92xULqUHzftWGdz6O532iNfTf/6vi2R8L+0drVmU+N7X96za+fABUsCd7+zJxqsSKciuB+LMgLTtKLcjkmyjvU7jz57+NdP5o8PUy6f/su/33v3OyJL5jd6lTSKEiM5qxwR6ZVzImd5cUCqOknb7m5pyVbHibNQNDQ5XDRAu17JZsby5sbeUMT0FDo6gLDAjrj18qDMZfKVallDCaKNsbgBoUJ1XjRRb9rgU65ej4T4JTd61lgTqk1kQ3889Zyx7G+1jsxls6OjI1OXTqdZqmKAeYlESIiy1npW/7tZxg8RtHI8mVm7IgSsbjxd2L6n+Ktfv/CTX7/gH2ADLOrAzubwnbc2XXlpuJw6IZ0yVElr98qLBdPNP3og99NvfzelIQDQVQ83Xhq+47b2Sy6wTZqQjssRAFBRwNXhkbFg3zCNpt29B1PPbMkcHYBYMua46of3DRfLsffe3rC8N4GclFviqOGMSmhuiOhk65hT18Q/WksZsM3GaDSu82RjVVjjuhAIGAFBoapaEIs1ckNnihYwWaomQtb8xvjgWKHgadsUjiGNACQCdj0YjaYdpJmdLfG1Pyo1pUgz5sHPrIV48+VsfJ5IJj05dUvTXbYQEQkBvJypnUQsxI2qJn3KntEMlTPVYR5RWqKczwx3tyX+6Hebv/3DkRe2OB4wqTVjLGDoFUvoA3c3rljoZYZ2WKJsCA1QsTmJcPima2MLF1ibnhk51qcRYeF8vO6q+nltWrv9TBQBSWvgiEyEBwfth5/NPropc6QPyi4EImLJykUbr7iyWi78+Pvf/d6vcoj4Rx9LttQHEJWmKjvjoMyaWZ458R1plkRONX+bmqjEEJXncQbdiXqTlY/n8ywAVtJsMo2WPIYrkgNwYAxAIDFFFmCcC2kJJyCyrFjw0sxq6EzWB0suenKqU83J6fOvTSABgOFJLi9Mjz4n9ka1EjhXElm783whNzEx7uvI6Uq86Zpst5hVshKNBjgnpeXZnzoEQlCACrBgcJzfEfvYBzredrOVL/GKq0yTx8JQH690NJUMmiBWmMo+KyDF0LNMb9n8QEtdc7lqE/KQXW2MVwye8niFaQIETcAY8qC9a6/3swcKo1lwwUiXvZZ48vZ3f+Rjn/i9fXt2fPM7PytC4dhgcdPz7o1X1DckQm7VYTPUOiFqQH0yiw2vdSg6IiGQSaxeWJPZAuSd5nobuKKKimEkqEDUemUQB2JaWUhRZuTKFeSsKRouTeSr2aLVEDe1X234ujWZ/2XGENkp8S4CgFKKc/7mq2oAgGq1WigUpqjJs3+bzUyUyrlQ0BQIpPWZZoLM+pyhVLLIkHq74gt7RLnCPIVcUMAkRqpayrmVgmHQjMbPmqgqHSW47GgKckMSkPSUWyk6bnGqhKvW+pxzkclmxsYkC2IwyCLK0MS2bNkFX/rKwEC/VEZL0hgek5uec656S6MZqpSLWX+OGYJGUKA9JJeBRFAIBs1OnM6kONBZzKhQEPIwVJQxh8C0M6VifkwWGUEyxE2htPRlhiNyTTJfdcquoVVdU4JCsTopyJVAhOy0SU/0mqWS1MwW2eTnGKWUtm3Phej9tkrktPBpNcfQsulHdzKdKuYzbUmD49lSH6c3+WYoiQrlbEmRACYYoHapVNQMPc6lEDgNUftNeBGQc611sVIsaWK+18CZ5pzhVC9yRNBAXsVZujR22aX07NZCIedEwlbFLXzn21//z29+HQHa6sIBC0+MkEU8WzI16qkUHWpADYJ4AA0OwtUgNHAidjo/jV4xqUjAJWBZN4mgY6tUXpE2LMG5h0jsFOki4gAh5A2WzYjMdLktnmwWAVaWM2fVTDeZe60BFwJyFGwKD/KFW0rlN7ubbgnxpujWN4PhM0eHUj9dh6VCoVIpCYOjYqRfbQ+dafPNBRjgnNRA/AxrTkBIDJTA2fdX84o0AgBjQFqXi/mNl65GwV/e93RpUtlCkvIaE6AVMASTlVBBGCFgepOpwXIeucEUcgJRoWARk1nWPoGQhlIJyQPJQBrkAnqvVQ4YALiyJZxAZZUzw/XJWFtdXaSoLAXa8zgwAI2MKSkNwRa1tvbY1mQuMzo0HLCi0ZhA5c7onvSa8UIEIESttSHMaCQohFHL8xAgQrVazWazkUhkrmZ3v/V+pNJKqTNSO5WUSkqcbhR5Ju4Cnj13TKdr35mqmiGcKalLc6DDDlepZb3B99wR+tYP8ocGVIABMhACKg5UgS65iL3lzrpF80ILOl1ySwa6CnhZmTrUXrAWvTBet3VYeobX1AIGz3A5ziHLa23U2ZkuoTZc4iQvpwZaMqUSaPSGkga3YgoNzphSSMTYjNZQmmLItSZb2NFkQwRMXvHwN5tU6qtTpck0rVgkyrmfwq5df7lcGh0dSSQS/giwN1nlFxHNMcZmhks41QwJf0NlfBZHCc8CzJza7B4QDEPlJk+Ywn77DaFq2di6E4MRrjQho2pZWsy79qrgDVfHWurQc8puxVWEDka8UNsEtWwejD423Lo7EzKDznyz0BS3kyY3EUmlESRDBjTnZFw/ITBrwiYhQ+k6BoM2O6Kkomq5NpTn1PvhmnTFoQpFGEvGksqTVJWMzYU6vYZxXQiEWpJpWIlEvWGYM5exWCz09/ctWNB7XpOH58tqM2RnbqVFpmlJ0yJyAM4y/+hksg7xFdTcaS2Mz562O/1nAlCmUQXUyZD1wXc3veudMalNKQlISa8EKp+MiQBz8ukUcqWZVcZYnrem+aIX+/lDB9hxbMoGurSXKw6d6PaMeXWhhBm0IWRBVkCZ0dz5ZarhP7OIR1TLcLkeOxVQJDoFtWUAwgcLqh6vfZXmTFi8Sg2JgMiYdKVhRGItLZZlT52VELFQyB85cnTDhkvglccy/9ZI5PR1GaZh2/asC536EWOxJJSi1eqwYFowOAtYUevf91rQDD2dh6S5T3h6pgUAOBIBafIMzMcDOhqqKu0T+glJIrkIZaQyQNWhQInVFe0F/dT76wPBF4aiY6Irh21VihLGXB3yUulUMdWRCPU0NsTwmHKO2wLYVFvhmbPIpvXkLDU25yzsk3WYc6CLJ1sQnZ7W88viXh0ChUisWnENw2pt7bAsn7dV483n84Vjx476hCB1cgzwm2RWQzAYjEWjZ5LXpqZmKNYXc/3BEDImQLlnXabZ3uSZFeeMCPPVxUuzeGUImnRZSYcg6w9anSIYIgEprTUPeXZbljr2Z5peGg88OdRyTC7UkS5J/jw5piHmevGSF6wq2yNjQbLSaLpSj3JwERWAAtJzuxkzSvn9/+lT882v0oWh1+0JISIyRqKQL4c0tjS1Wj6TcOrBLZVKQ0NDM5PabwarPbUY9XX1XV1dftnXqc8QAUAo2SGGk+PHCgkLRUBI9ark5jUEjK8Xt0IgRGBcAsiTDwOBBvDQdK2GvOgcli0H840vDgVeGg6O2T06sqCsAz5GTsAUERfMBTFR5dURTyut6+0ojwbFhKAMUoWdYTTYqdOMawmu1+nCzyHqr3LpBEczl84ZpmpoaDTNU0iQQgjbtn1XFd8sEjl98x2dnZwL31QxxqfADX+5BBodORk8dHi4I85E3FCv8bl+hRzPmZro0Rw1gWf3+NVU6EHIKhTKWwuPw8onj4mto5F+rzUdaC/zRlczwKnR1KABUJNwIKqQIwb2jA5NlqNL2hpb+dEgaa6lQGKgZhneWSabpjJ3PlNluv9gDdiZohFND3fHVzbrr8bdIYaco53NOpGwqkvUC2YQwXQdfF1d4wUXrA+Hw36G6U0mkfPn9yTiiWKxGMEoN8Spq88Rw+Mp2Lkrc/HyJJiGLkAt8p6eOfdf/MKpeUlMoqlAOCzshXsP5zsePsZ3ZpuPue0Z1uYZdcC4dMugy2gGEQWR8veKoUEUKktdUVzm84pGy7F4V6ItZgfJneBU4kwhaASNeEYdR/CGzkbwK7w42JW8JwUkgnUAoLXivFYUVl/fcOWVVyUSCQB4A1Lb59iPTCbrNMHRo0fndXfXN9TPxv6ApTPq8NGK6wEYptbA/qtF8CRGON22D1ETSrTLdscE6zmUbXzmuPnSUGCc1ZcC7ZI3KuLo5eqj3A6Gx9Ou5xEKQ5NGBNSugKplGhqSFcccyHqe61RkoC2RbA6GLRoBlRHoIcizQWA07YHgq0BU5/70FZk/px4gkCzyBGrT4kE/KuJcIOLo6Ei1Ulq+fJmvI99kEqm1Zoy7jrd9+/ZgKFTfUE+1TAJO51jsYDzWILgZApKnFPDPVcXyCtpshk1+VYfO4QWcLLGfEklGzJRkF7FuBBa8XFl9/z61f8KgSHeVNXoQIOUJqJAzMq+7tbWj4dntx9IlzY0oAAlUKLNh02mub0gV9Xg1AEb3qExkRkdS5VHWEWiw0QBiWECSQHrOZBMQ8NqEUpx9a0hnhGRx9oF41sWZcQAhMNCMlAjb9dFw3VRbtNpJd+/e7VQrCxb0IBNa00yJ/K1Gf2ZIJHMdd//+/UuXLpvifvrcZAQUANDbu/yW2+4IRQedYh9y7o+hQiCAN3iQzww7iQCAkrgG4ZLhQtS124a8pueG6h4dwgOlnpwZFTxW39ppFquT48MGlg1ImR6xipU0SyVWYbJq2yEER1CuPgSNMSy5XGnDobBLsSpEdVHA8eKSlsbWRFDrEaEnBFQYKlZTlnTywUR4Y402IDLtoVuG1sburvZeAj4zG3n40CHHqSC7bVrjvI7I6b/SagMA5zwcDvuoJNEMYjgiEczrXhK54daBl/8vK+fam2NKlhBfD6xA52Y1ZhTmIq8oU9pNWbNnd7Z5x0Ri+0Ty5VyTE2jzwOScN9eHHDZR54011VmjwzkqSsOx2yJuiGtFulTOjowMrl7UfMHKrr2H+0sZLkSLJAFgMB4v6bb+guNBOucVW6KhpBW19YjQExwlAM5qZUD4qqbR/iaLM5ORxBhTHlSybk/nyjUr18+UtlonNw2/Ec3tv1Ai/dsIR8Jr164NBgNSSs454klLoxTZwWhd67z7vt3flch1dy9VhQEgF/6rYpopfqsC7mHIteozrH13tu2hvratqeYUtDjhRsUCnueZJCvpwd5koaFRokq3mpSvFGVmT50Z7O5IFkvFI/lBK+pevHxxT2foxRdOFHIhM9EqFQGR1kxiY8UMHy+M5JzRsme7MbMxABHuai0BFACbyUunc/iovdIBRNo0jHxV9h0dXXHFTQs6V9Z6xXPuK8W2tg6l1NSQjTebRPpORjgcXr58+fj4+InjJxb0LpjpcPiTOj0yTwzKIFggEhrHQM+wE2+4SCrkEqwqRArYVLAX7RwPPrif7/aaR/nSEqtTYKIGZkDFnTx0cN+1t7Uub8BNDz100boNeYc/8/yOhpYFTZaXyo/OC4y85bqrGjrCL+zaX3QENyOy1toSFQhNpqSAEIGstg6PU6HkeE3QHrNMPSAoL5jLqAqvrWLrHDlaBEJYXlUePzzCNgQsaNDkaVKccSnl8PBwQ0O9H2W/MWHNudeRWmvTNLvmdW3dunVsbGz+gvlTgRuH2hwN4Dy0bMXFDaHBkmNrMBiy2qTEN9CBolqjQHK0KLJEJdQ7xnqfOBZ+6kSoz2tL8XllnpQYJEIATWgQBclxBZYaQ9m2wPGkpxe2dNZfEpx0nPHMgSSNXrgCVvWkXhrc8+yOUkr1QKhJQ4ChMbXIfsWi8IhymmsnUh0dybqRBc1tETqqq0dNVmWntmJ+HRrxdTzXpIFzwxA210FOYT9t7iuOUrG0ZcuWrq6u7u7uWsvqk13F3jwT3/1rNS2rUCgUi8WT7sjUQ0ZAthW96ubbT+z65cv7dy/pMAKWoT31xoKRCMikBs2ENJty0H6i1Lw7n3y0L7a3OI8SvS5YSJyDnuIcMmK2ZQe1W7DUxPyGUsTZ3mGV56/sPZYxHnn6kO0d39DdUY9Hf9lnHToadcNLwEaQGZ8RUdt5AI+0B7KKZpnFxt3S+IRUMrCwvikp8gwAqUqgoNa18Y15OFFws1JyQnbz9dfcMr97KdRacCvgUK1U9+/f39LSYtu2JnrD9ue8THwHgK6urnKlUiwWQ6GQ37AVAJGhJslEuHPRxh0vPHVsd9+i9jbDCFScKmfwhnmTiKSAl3mszJszrONIqeGlPuPFgeoQW8jDXUXH0EgMPARVm9zEAZQjlDRkOSaKbTFZH3Yi0I+unJ9YtKQx46bH4xSKUKHNDi6ti+RMg5mAStEUMsOAAJFIAzAAEyhohFtRGiOHjwQLaDQ3K85sI4tUBHQYIwJ9voWSCBB42Iod3T9qloMfe+ed8xtXkwZkDFADgFLSNM2TfUBnRDdvmonv064GEV162VsOHzq8ZctLa9eujUbjRMR8Ji0RYBAg7LKmQjXsQZgor/1s/znag7MRfhEYgCYoKVEI94wYq1/os3YOW8ey8aFK1GEh7eUMXaBauMMYIGOgeQh01ZB5Vi3GTapvb7T5mGmUQffZbunyhdwrNxqeKkwWVzev+szbrtChVYYFgtW4wwxBcOACuADBQHkwkckbqDKV0qOP04kjOwsjvK052VIHYVsh1wD+2OFXw9zRM4FVmEkDfoXn24dezZBoOLBzf+Z49Q/fXQ+AnvRM0+Cce55XdZ3ly1e0tDRDLe+P58pVeKPRHx+GDIfDVafy0EMPLl++3K8/94UVEQGYJly17qoQDYyktnMpw3aQyAXQJ9srIuA56UKGMFV+7NcNCk3ogaXj8wfd7kePhLaO1R1Nhc1o5/p1i2M20yWXNOeGjUYA0FQkpNaONvKFjBwfC6qCLKoIizFV1rqM5JIcSfBEtKMHYBFA2+gBfeL5Bw8dvz9fdEk6SkpSigEgY0LwWDRocNbe1vqeD76/w7LGIBFz3rJ/sMtBJ5ooJWNDbnlPOnvYozygw8Ej0Ih6Oq3o4+fnUD8hCZSR3vZVOlonWOBkGpNo7969Bw8euvTSSxoaGrRWjOFZudL4Wy2R/sufW5ZIJDOZTCQSm1b+U1x5tXDZW0x17Bff+tHl66OrV3QXU0cZ82p3ir/RLdLsfkM11UHEPBasiPoM6xh15z01EH34kJkVzRkdXhhrvHnj4kUGmAAEkC5DKuMUCtVyxStX3WK1WLHKofbGVW3B1nCHCY1uaajq5ARTwaDBeSA1qk/0pSpl79gAH9hXGBsoZTKFaqUkXcfviwoIjDHUNDw0EggEIihueeu14eamty7p3bikNw9QAG9UHtux3xwsuIlI3hJZUFlOZUR1kmFH51JrCGFC1diz/fjirnVXb7gzGkki1kAfxtjQ4MDLu16++eabLMuS0mVMnNOA6o2VSH9YrFJq7dp1ixYtfPzxxwqF4po1a6dcEQYAWhETpsPqDhxTy5bUg9muYRCwymiqme05ohtonxDEUIPwdKAEdSlz6X5v9YN7acuIXbB7ldFQzeUCyu1B3Q0MAMoleWL7zl1btx45djw9mfWk5IbV0tZyyYVLeyLLTQgDrDFDRWaVGQLjBgA+uelnn/q9fxIc7n7fPR+4597FS9ZYwlBaMsST1QtEnuc9+8wz//EfX/nHv/1fW1545qP33rt45cqwbYUAgIynjgcf2RUrFttXL1J15jCTFECF5D+lnEjjST01jROx0/BVfHXLQqZtOyXz+U1bEhevWdR+GQJTSk2nZGKxWGtLc81cIZ+rZggR3iQ5mxlPoYhG4zt27DAMc926C2a5m0p5LZ2rPvR7f7V/648ff3LPRcsTCFUtq+g3qf/Nb3bKFwMUrhYOC8tQ25hs2jxa/+RYYFu6YVw0k2g2malUIQg6DjQxOPzLn/58y1OPpdPpXD6fSac9T4ZC4eUrlq1IdpiZiS/9/ZePHTna3dP17ne/e+3aKwFg01MPPfzwr01hf/GLPybyJiZGH3/oiZ/++BdupQJInHEGKAyrWCxVPflnn/3M8mVLBvpODJ7oexaeGOw/FonHP/D+D912683o0YET7sHxBsJe1tfX3RhvigBnllLjHKocAdADPFfhDkdCkMLG8PyOZfPaliIIANBKIjLP8x566CEhxC233mpapp8ZfiNxkPMlkb6arFYrK1asKpXK+/btX7JkMUzlvhljUjrRaPcFV3xs60tP7ju094qLV8hiRumqEKjPSYbbJ1Egq2pDmo1Fe97hUuvOVGLzcGx7Jpq1OlW4xVMG08pgmAgFTMQnX3z+y1/8t75DBwRAIhp0HUeY5uUb1t/1nrtb29s2PbXpJz/40bG+oUgodPjgiXvuvqeza97mF3aNDRVWrOycP79zcjKz+cUtDz706137Ds55Rbfe/NYFvfP3790bsARJ94knnwaAiy+6FG+91WVyOFXKOkErOu9YxqmQWZCx5lC4IRC3aRTUhIEKQBOwc2AoNQsa0eyYkx8aveaKWy5ecY1SHueCgBhjpmlu3bJ10eJFnV2d8FpKI37bJZJzrrUOhcJ33PGun//8Zw888MCCBfNN05wR4nAiJGIdC67I2/mjA/mmqG2bYU1VNlf24pVKZueQSEJ0IVARybLRdczt/XV//Qsj9WO6pRRscVjMVQKBkXYSQauzqT7M2Y4XXxg4cbyzuUErZRjGpOMB8quvu+GWt99eKhW+8a1vKaVaG5NE9Pyzm7ZteXHNmnW33nrb73zwvU8/8/RNN940NJpqaUzG44nO1ibP8zjzacvMcV3DMJctW9bbO390bAwRXakMYcRDgYqkrp75gJD2KFN1KxKQN7qW1Vcay1THM4mwbEw0WiKIVQEu1hxKevXmcm4oW2MokBxMDR/ZN3b7FSvndy7XygUgxlFrVcgVuru7G5ua3njtOKcjcm7VZO1NZ2dnZ2dnLperjegif+CmAABA+/JrPxxsXPeVb+xOF6JWvN1159YBr14cCVCicNEuUSKN7YXY2j2lrh9tlc8MNxzHZeNiUYE1eRjWaGtioFRzItLb3hwGyKYmtOswAATUSjHGEsm6jnnzAEBKufWlzYMjE0pKreQf//GfrF279qmnNq1cuXLPnj3/8oUvFfIFAOCchUIh0qSkJE3+/Wbz5UQ89ju/88FcLnf/z35uGIZlWYxhR0fHhkve0tTeWgU4OizzLoBhuRipUFMZ5mVUz4lM887jgcFck2cuLENzVUcl2BoEwasFb3FGomVqdRhqQzt2zGyf376mKT4PAAiYUhqBHzp06Jvf/OaatWsu3rDBJ2698UIpzqdEIgB5nlywYAEi+9GPfnTbbbe1t7f7++RPJERg4Why5brrBg/uPjgwbphOwg4TZJFeZ1znz8t2NauKRMnuGoWeXSONzxy3d2ZiE2Z3xWySENI0paRBSrfa2ZlojUf6+4dLmbxAJKUQsFQqN7U033TLbUuXLXGc6ss7d05OpBhQteoA0Nq1F8yf35vLF3bu3PHQg78eGxtva6qL1yV65nXHYrGxsVHXdTlnWmvTtBzPC0eiV1519QMPPPDTn//CMAwiklKtWrvire9898KFvX0lZ3//ZEkCM0xFSMAJQxIgL7XnkRoxSzLYnojFzQFTDQHl8WQfFXx1j2itTZbWWnBhB+IvPvlyyO3+nTv+uDE+35MOZyaR9s1aJpttbm4Oh8Ond8s585nfJDpyqmgEY7F4c3PzxMTE4cOHS6XS9KRIREBkSha6F15814f/6PAg33uoGIo2a/K7jZ1ybTUe5VkHZRIwBaiASyOZF13HZc/myY6fHah7fGzheOSySqDHI7M2mJOAgeZaqkqpt7U+StWf/eDH/UePBSxLETHOJovlSCx293vf097eNToyfP/992uisG2GQqGOjs6HHnqoqan5M5/+7M9+9tMtW7e11MU9JTu7OhcuWhgIBKDGKQEAcF03aluLFy9uaG4+evTo8f4BALAsq1gqB0Phq667tq2u/vBkft/AUMlRXBikJIAiQkkBjzc75qK+Qs+OwfYj2QWTbocD9SRiGkxN7NXs3SmsNkIgxkAIDGbGZYi3rlv21kionrRiDDnnqVQqm81dfe3V087VK4HsbzarPe1QAkBLS8vHPvaxTCazdes2qHEyplngBkDSii8VoUUFp36yGPJ0gtDWMD1H8lWZbELwmChhNMU7x83lR+TiTf3JX+xmB8qdpejqNGst6YgHpkZOyBgQV46tnaSJKzpjvDT0k+987cihA7FYRAIRQwIIhULLli0DgF07d/7qgfsLhbzreW1tbW97+9ufeebZl1/evXHjZalUang8pbQmrZctXdbU1DQ2NialFEIwxgCwWCisWLH8xhtvVI5TKhb9e29qbhZCpFITPtgyUqwcHcmUXM1qwyRRI1douhQp64Rn9GR0z77B8P7hutFqT0HPr0KzBxEFNoE4u5LCGYgREpo8KMvmeF/p6rfc9q53/s4U7lGzk4888siuXbs2XLTBJ/vMKpJ8s/qRtS7zWhFpv+OKTwhCxJaWFs55Lpf2P5luxsK4UErZwdYb3/nHo/nYN3+4I1x/QSDcXq2epF/4kNDMfzUgHU9W5yOAq1jJ6h6PXPFUetlPDrU8NjzvkLckJ7okC1CtGRYDvyU9EnMLcVbduKJ7VZshHTU2PFj1PGEIrbVTddauXvmOd7zDH00wODjY39enpHRcVd/QcNNNN/f09Dz33LM/+uGPCvlCwBRaKyAwDWtkeHTPnr2e55mm6a9Hoeqtu2Dd5ZdvfOGF548eOyoYIuKypctWrloVj8c1QQH0pMKcxzzggGzmnQIggaFY2IWGjNd+JDN/29CCA6n5Zb5Qma2ODmjgdHZ2L9XovwTguVQf6bBk0xP3b4uJ5tWLL9MEWmsA5rlusZAPh4I93fOEEKf5nrVOB7OGVONUgu7scdV/uUQSADDGEVltwuPU51rrJUsWA9D999/HGBNC+FPhkQkEzZnVNf/CpRfcUZI9P/n10dG0GUu2SAlEtfXBM9RBEaIC7oFwIKiCnWM4/+mRlgdPtDw93nXIW5ILLXfNRqWIkTeTgCgQoFJMUuXGNW1uOvXYo08bggcNAUBKyrF07pKLLnzHO2+XUg0NDxw5cpgLwRgGbEtKXSyW3ve+94Uj4b/7+38oFguRoBUMBtevv3DDhovD4fB4OudTlbXWAMg5X7xkaUNT84MPPnzw4AHBQWvd27vguuuvu2jDRdw0BiQbK5pSBDQXNFfaWhFqFvRE66RccCzXe2C84/B4Mu00StHsYUSSqYGfPdYhAiSMhuuHjmUPbB1d1btxYfuFAm2G3E+tGaZ5//33hcOhiy66yBe76Y3TWpdK5fGJCUTknPva5LyqzHMskYz5CRs5NDQwPDzkK8JpTtrChYvi8cSmTU8dOHDA87zp22bcAADPy1711o+/631//simwR37s9po0hAhMOfsUoG1GQuokUsWLPKWMbH8GK57dqz1gT20K9OYsRaVrc4SJBwKaLRm7BkCAEkvxnBpQ/DCdmvni5u//u9fVJ4XDtlKSiJgnC9YtKi9c54QxgP33//CC89bliWlXL16VX19w89//vPOjo6VK1bsP3SoWq04npdIJt/61rdecMEFibqEJWo363keIq5ZuXzJ8pW5fHHbtm2jo2OBgM05J4Dly5ZffsVGK2DtHtP7B6quYZMwNfnDEaY9ZtTECIQCw6OAx+o91pGqtr7cFz0w0jTpLShRl8uaJEQ1iDNrSkRiTFtBETuwcyDVX/2LP/n7iy94q+uVAJAx5nnesWPHdu7cBQDxRLK2KVM9WxhjmUz62Wee6evrcxyn5l/OIAGdBa18fUCmOIfaUUrpj9XeuXPnM888HYlEr776mra2Nv8e/MfrggvWJxJ1X/y3L1x//Q033XKT1poIOGcAILgNYCxYfcOf/MU/b37i/z7x7ImN6zu1N6xlltdGAPsDXmfyV7jUVpUnstbS47j6kcPGc31iXMzPGO0uJD2yasNBZrhTgICIslJZ2Jq45ZIFbQAn9h48um9XQyxk22bVqVq2eemaVYsWL/J1xOYXX3x5555oJFh21U0339TV1fNP//SPv/rVL7PZjC2Qc54vlO1gIFGXfODXv3zk0UeDoQBHhojVajUeD7z//e9ff+GFfUePDA4NlspuZ1tTLJ7o6++/0HUXLV5WRr7z0NEdfeNVK65R6DOMDQNggEhEkoIVaFHI90yM5dz04pZwQyge0AOWGubMOQk2TBWRERFpEGCTDBzdP9HRtOKiy29uCHUDADJORJzzRx996LHHnvjA+z8wr7vb7+48vaG+Bg3Y5uBA//Zt25cuWXLNddc0NjYBgOd5vn0/HfKcOQb5/OrIOXV1raWD1lprwzAymcyTTz45NDS4cuXKcDj0xBNP+CbMhxKUUsFgaMWKFRdddOHgwMD2bdsYY5wz/7fITM9zudG0+MJ31rWuGR4zh9OGpyOMBTUxmHauADUwBcIhqwyRaqA9a/XszrX86kjiscH2Q3JpViyoGo0uBjRwOGWwFyARJzJAu+l0W8y8cF5g365du1960eSECFwY+XwZOb/nrruXL18lpZsanxgfHa24rlKq5HqBQODiiy9evXr1pk2bNj35RDwW5VwEA4FlS5fN7+195tlnt27baQdsv2V32VGZbHbt2nWhUGjXrl1OtQLIurq6rr/h+lKpMjKWMoTBgcazuYlCxeGmYoJgxlSfOeZPIQGTLF7lPZNq0bFsx/7R+uOpZE42a7NVQlRqU5MgYECMCImQAdMuGhgJG019B1JNse7rNr6blO15LmMGAKZSE9VqZeHC3uUrVoTD4Wnn3nf9hRBPP/3Uo48+8pa3vGX9+gsaGhr379t/3333pVIpwzD8tNzpNbK/YY7nN7fa5IP7nPOxsbHt27cPDQ22t7dfddU1V1xxhdb62WefzWQy/g0IIXzZvee97+2Z37N167bJyUn/637VIue21loqvuyCOxrmXbF9Tz5XDDKRIDKB+NQMAiJgHpiOqCtavUdo2XOZRQ/3Nz5+xBjWbRRbUKGopy0NgsCnCJxcIIbEpWN5hbaEWN8VjoK+7wc/2PbSC4l4jDFGmrSmcCiyatXa9o5Oz3EeffjhVCoVMJlhmot6ug4fPrJ///6bbrrJcao7d73sZ4EXLVpw/XXXL1q40KlWK1VXMM4Yc1wnGgosW7asoakpm5589tlntdKadENDw+3vuH3e/AUeMk2UBaygRdzSyOjsG0l+I36myZAUBLOhwlpPpOsOjNQfTbWNVOYX2UKXN0kwTmI+GrSEWKROls2jL6fa48uWdF4cFEnOTQDGGUeEnTt3JBL1H/zg70gp/UzVtOrRWk9OTm7esiWVTq9dd8Ftb3vbVddcxRk/cuTItm3bBgYGKpUK53xq714JmT8fEnna3yAAjUi+hiOin/3sZ/39/Tfc8NZVq9YQUWNj8+233/7www8/8sgjMzNavqeyYtXK7u7u5555fnJicrqOljFABMHDXUtubl9y60S+qX/czJVDgDEiAwmRQANKtMqYKFjzBtmKR4YWfv9gz1OTSyfMZRWjuaxshWatigbULHYCZ8DcUqiSvuOyebesbp0YKzzzzDP9Q4OWaSFiuVJpa2tevmzZkSNHAGBsbOyb3/x634kTRBiNxv/0z/4CkX3lK1+pVquMc09qpVTVcdZfeNEll1ySS2ekW2PTMcYy2eyixQs//elP9yzo3bx58wsvvDDVWww7OuetuXBDW3dnGfHlFEyUBRrGKdNuaDaQCKCn2gD53DqtNUqIl3nvmLdkz9i8HYNdQ87yMpvvYVSBoZEBcAacpAjbdalBZ9dzwzdf8aFrLrlLyioRCcEBKJUa7+8f9DxpGKYQYjrJ5uuIXDb361//es2aNb/zwQ9Pi8DFl17yyU9+cmho6Bvf+MahQ4emmYdz2tLXFwD9Jn4kai09T1pWYHR09Ac/+EF7e/u6devq6+that5EPB6/6667nnvuua9//esf/OAHfcTYB2CbmprkEvniCy8dPnTEtMxYPDbDIzEQWe+ytwI4T/7kf6IKXHrpiuzwTgbEOauSUaCYji0+UWl65BA+l244IhflWKMSIcWEJgHATlbkz8yG+yZbV4Nudm1r1NbOw488MjE2ajLyQ/p8qXrZZZe97W1v+/GPflAtl9ra2nbv3uU41YqnpJRve9vbGeOPPfZXDz/8cDqdqauLE6FSes3qtW2t7d/5zneymUw0ZCMyw2AVl6Kx6A033sQY279vz8HDh0O22dneEovFRsbHlqxYXdcYHypVH3np6ImxnBkIO0RzNN84Y5k0EXAFIQ0BDQFXhdz8mNs/6jY1dsU81CanIjmViGV3tHf9/PtPTxznf/Txv1q/4gbOhVTK81zTtMYnRv7jq/954YUXrVq1yhfBaY2jlEKAUrEoPa+zszMYDCqtp8JWxjm/8sorx8bGJicnv/jFL1522WUrVqzwE60+hwZ/s+IH/rnPfe71yaNSknNDCGPXrl1PPfUUY+z666/3k4S+y+w/Om1tbUqpAwcOGIYRi8UCgYDvozDGgsGgaZqDw8OO4zQ2Nsxolcmk51h2pLmtayJVOnDwUCaV6uluRcPMuWYlMC8bWLq72P3IsdjTg8kTan7J7vJEQqJBwAjZybJGnMnhI8YRquU6Xr1iQf1dq7vG+47/01/+r4mh/qBlMM4Y4+lc4crLN958883/8dWvbt6yrZDLHty/n7QOBEM93d0LFy5JJhOjoyO//OUvBwYGXLdaKlW75s2797990jTNv/iLv9i+fRuAVlJpIuR842Vvecftd0rPfeTBXz/25FNa6/fec89FF1504PDh3qUrF7Q0HcgXv//EriM5xaJ1bg3rPi0tN3eLvFqvXQJGyJGbUolSRToeKgyiCDNmRIMRdM2DO0ZGj6gr1rz7w+/6E0MEqtWSaQY4F4cOHnxq01NCGFdddVVDQ8O0RPp+pBDixIkTmzZtWrVqVXtbO+eccT59gJSyrq6uvb1dSjk0NDQ4OJjL5dra2nzHbCa6ct6t9uzer4hEVCgUfvrTnw4ODn784x9vamqaflD8bA1jTEp5ySWXvOMd73j44YcPHjyoVE0ctdbCEAsXL2xuaRobHzty6LBbdabvRBiWlA5R9Ja7/lrUXfHLxwYHxuyiasnxBcO45JBc+fPDjT8/3tkf2FgMLnDIVHo6702AutbYhpBqHe4IiQyGXqXUHLbeefnqhQF+cPv25558PDUxgYyXSuVKpdKUjAkhdu/eLTh/ee+++39xH0dWqTgXXrD2pptu+sd//Ic9e/a89a1vDQQC0Wi0rq5+/vzud9xxx+JlS1PpdDabDYUiLc2tlmkpRRetX3fjTTcDyCOHDgwODgrEqitvueW2q6+5dv++fcV8moAKCorEPTTgZOuSUztuIsHZAHACIE3oaVNinWv29OV7tg/MO5xenHa6JbaNjfLnHuu757b/9mf/7Z+UdrRy/caQ1Wr14YcfHhoc/vjHf7e+vsHzvJltcxGxVCpt3rLl2PHjixYvjsXj6GPLU8RWwzB8uezt7f3Qhz5k2/YPf/jDkZGRSqXiOM5MHXnemRYzy3V9XKC//8Rf//VfX3bZxquvvmZmzvD0b7W3t2/cuHFgYMC2A8uWLSU6Kd/Lly9DgM0vvUREi5csYZz54Rvnhk84f9d7P7ezt/27P/3rSzaubFl54Y5B/cxgcVtxfja0osKbNSCgorM+Wn4RsiEdA/W8ZGx+gu09uO/pR58UAklTqVzOFKsA8JEPvLe1teXLX/6y7yEVS8VQMFSWesWKlTfeeOO//du/maa49957P/zhD4fDofq6ZENjw7JVa2w7WJdMfuYzn+nvH8hm04cOHjh2/Pi1111/1TXXa6V+9tOfPv/cc0Hb9KQSthUIBWOxmDCMMuCgy8s8pAXH1zPD8KSV08A8NLUWyAPSjZ4YGYzrZO7gYTmSf/+df3D1Je8EAM4CritNk3ue9+3vfLuxofGKd11Zk4CpghPHcfwZSp/73OeSyeTHP/7xYDCoNZ2+pzOHH9x8883r168fGBj41a9+tWjRoquvvtq34D6ift79yGlXTwixfdu2bdu3rV69+uqrr25ubp6pHU/FzJlSyrKsDRs2bNr05NGjh+vqEs3NLZwxrTQg2Lbd29vrVCvbd2wvVyrrLliDyKcaBpF0vWRd48brPlgu5nYd2f/4yORQoONgKZ6zWqWVVCROapHTBzNNMToYotCSV3Lz6+1r17V2C/zsf3697/jxH/zgR1J6WnpSKtCqt7e3VCwxZFdfeWW+WBgaGuo7cUIeOa61CgWD9977uwsXLrz22usuv/xy0zKBG9N/qbG55fZ331XMZnK57MTE+Pj4+PwFvZFwRHmVXbt2DQyPtjQ1Ll22IpFMhsLh666/obG16VCJdg1UiyxAFpez+CM19xHnUpxzyi4jAAJTaQqYDQaqPVt2xQvuW9dd/bZr39cU6XLckiECpmml0+nt27abwtiwYUNTc9NMuNvfo2wms+mpp5qbmy+99NKWlpap4JXPFABfGU0j0PF4PB6PW5blOE4mk7nvvvtWrlzR0zN/Si4Z5+x8SeQ08uS53mB//7at25jgH/nIR2c+Xmeh6FmWtWjRooMH9+/e/bJt2/F4ApD8nEE0Fr3kLW9JpdMHDx+wA8bChYt8+0JEwjQdt2SZTTff+TfFn33zySe29Rum09DOjCRoD6lKjJ85gTY9lA0N5bJiZu3K+Ru7Y4VCcdOjj4cD9ttue5vWVC7l7UDQq5Yff/zxkeHhJUuWAMBkOk2EuVzh3e9aGwqH/v3LX2pvb29sbDxy5HC5XHal6ypXOlJ5LgCQJqW1T71zXZeINj3x+LPPPFUqlvbu3VusVJVSd733HsuyRkfHLr30Mh6wnz1e3HFkMk8GmZb28zNzzAbD0wEggNNDIO379UEhuOdkJrL2uLhw5bW3X3drQ7hVKW0IizFWLBZ3v/xy34kTN9xwQ1tHu08Hmd5Wzrl/wL59++699954PO44FcsyZ6oY390UQqTTadd1m5ub/VQwIs6bN2/evHl79ux5+OGHg0FbKS8ajTc1NU9/63VK5Nm7Z/iXrpQ6fuzYU5s2ze/tvWzjZf6vzj4xb7qIu6trHoDesWPnwYMHlyxZGolEfKvhn/nGG2989tlntmzZyrlYuHAR57XPLTPke/y33/pe2bTmn3/+TCFX5dwJ2pKQeUCacQB2xsb5DEhLE7ymAK5vjwS1/NkvfqWVKubTn/3vf1IulwqFotIqn8seOXwkk5607ADjLBgMAmBrR8cff/qzJ44fu/ueuzzHScTrBOdKK0VKAYEm1HAyEUwklfI8TynlOg4yZlmWZZoAYAcCF1144f6DhwcGhz764Q8DwGgm2zeZK7MICetMVOdXM5AGiQA0AxLKTVhGfngos3/fR66//GO3Xba4MWIgSlIGFwCwZcuW0ZGRC9df2NjUdHJTADSR3y5s6+Yt/QP9d9xxRyQaBQDTNGc9En5ODhG/8IUvOI7zl3/5l76o+NaZiJYuXdrT07N3756f/OQniUTdxz/+u7XI/bXAk69KR+pa8M+I6OWXXz544MCKVauWLF1iGIZPBJyeDzVLm56uL9vbO4nYpiee0FJffOklszyBNWvWRqPRw4eP5vOF5cuXhUKR2p9GpjUIIW5evzIUCP7w6d3PHt0Pkab6jkUZrcuSgFtTbN3ZKgQ5I0cGuL563YIbe5LVyfSPv/PtkcGBWMT+2U9/7HmulJqAPM91qlXXkQ7latT31qaPfuxj3T0LItHov/7bl1zH/bd/+ZcXNm+ZeXKLAWPIGGqgiksXr19719131zc0xmIxv2VhIpEYH0+ZpuiaN/+hR58YGx0jAAcgXXXzZUeG44ictD9kk84WSs4xhMKHErT2pMGxLRE88eKjwfzwn77n5jsuXriwKWoCuJ5nGobWetfOXZnJ9IIFCxYuWWSYxvQGaa39TkPDw8P5Qr6tva23t3cKvGM1xYwABI7jWLYFAF//+n/+zd/87cUbLvJPMj0n2H8sg8HgggULLMsaGBj47Gc+8/a3v/3Ciy6axixfjWf5yhI5nescHh4eGRlJpVKtbW0XbdiACJ5XNQzj7AH7dJtdRJRSCmF0d3f3z19wou8EIl508QY/7vYdlFgstnbtOiIYHRnasd1Z0LuwublleoEqnoybxtvXLgwzCBq46Whq/MjLgfZFIpTMVz1EATh7X/0Q262UkZcvXba8PWg+vHn/4b27cvlsMNBQLhdhaqoWYywWjweDwXg83tbWfqx/cN2qFbff/i4AqK9v9N9EwuEvf/U/OCjPdYulQj6fz2ayjlNFQKlVJV1YvWbNf/v9TyGIVGr8xIkTlUrlRF9/Ih7vWdDjOE5nd09Te0cVYNChVAkUMI0MgSGoswVldCaaLCEBSC9iCVtWRvbuipbH371x+e+9fX0TQEU6EoVpGOVS6cDBg/3HT8ybN2/RksWWZU2rACLijAFAOpPZuXNnIpn0PZYpeZ0KZDUhomVbnus+8sjDX/iXf+mZ13n33e/2z+Aro2neAhElEslEItnR2bVty7b+vn7btsORSE9PD7y6tryn4JFzaldfYlKp1ObNm8fGxxcvWrRu3TpEUMp3RObIws48ycx7808FAPO6542Ojm7ZuiWZTCaTSV/ifQiTMdba2qqUOnrkSCo1UV/fYNsWYxwADc61VgDY3VLf3tWRzxeOHT6klQ7aNnJGAApnjxIzSBmyaqrSqibjrtUtpfGhb3/1ay/v2q6kYxgmErAp1hzn3BAiGArPmzdv3bp1bc1NHZ2dixYtNExTSV0qF0dHhoFo2eJFPT3dTU1N8XgcEYqlkud5jHHOhPJkV1dXfX3Dvr17/u1f/+1v/uav//M///N73/3O9u3bq5VyLBrpXbx04ZLFVc63DJSfOZw+VtTSCALntWYer1goc+o0FiQS5AVBRnQJxo9Xjr78kZsu+8wHb04AAZFgQjDmOM7u3buPHDnS1dW1bPnyYCg4Ewz3/5vN5Q4ePJCeTC9evLitrW2KT3hqd2eGjuM88cQTf/3X//vA3r133/Xu973/feFIDKde01fLGAMCqWQoGLz8iisq5cpLL76Uy+fiiaRpmjMJimfyEs/mqSilfP7E4UOHNj25qbunZ8mypQ319T4ddUZXyDnYH9Mcz2nizyyDXiqV9u3b98QTj914440rVqw6tQ0LeJ47Ojq6a9fLAwMDN954Q1dXt/Q8H6f1FYUD0Jct/fLFw5//1k9KVrz3shuOlyGnTBDmVPTNkShIVZUeXdcd+sTNy26O2t/6xjc+9+lPlytFwVEIgwNjjAnDiEaj0WjUD9EQIBIJM4bCMHoXL3nnO29vbW157rnnX3zhhWq5EotGlJYEpImUUkopQOSMC2EyxqKxaDKRZMhL5WK5UiICzo14NB6NRULh4IaNVyzq6Tnmqe++cOK+PROHXbtkxujk+EQ2tSWnuZV4GhhMmikvAO68mDW87WnZv//PPnL3XVcsawwHDACn6gRsCwB++MMfOo6zfv367u5un308SxQKhcKzzz07MT527bXXNzQ0+AzIU3xHzwNEpdQvH7j/P/7jq5s3v1SXSCgpb7n55j/7i//Z0NyiNSEAslOGPflCDACVcrlQKJzoO/6Nb3zzmmuuefvb3+Gr0rPEOuLsxppzvunJJ08cPzFv3rzlK5Y3N5+MnmZcOp42rhCn47K5o3XPC4VCa9esKRRy27ZtLZUqGzZs8M/sL5ZhmB0dnQBo2+YDD9zf1dV9yy23+klIYRiKyGZsUTwU2bgy8P+3d93xUVVp+5zbpvdk0jOZ9IQUSgok1CC9WEERVCxYsazut+uqq7vWT5e17qqIDQsoUkSko4RAQiekkd57L9Nn7j3n++PMDJMC6lrW3c/zy48fyczcuXPnve/7nud93ucVBt/efaLo6y36rHmcJmTA6iQ8IgxpgDEFBBEFxwUrp2mlCgBS08c/8fyTMqmUYWgKABpSkKIoihZLJFKJGGNst9ttNqvLxbMsAwBmOVFUQqRaox7Pj1fr1bzLJZdJGZqmOZbhOLFILBGLWZaBFM3QNMOydrvdarEwDKdSKeUKGcOwNM0gHpnMJovV7BfsDyGAHF3b09fSZ4Yahaff6HIbGOzTDgsJYx4JIgooRJC1WcvyjhhZ0z03zb31ikk6MbQ5HS5IScSiru7uQwcPIoRSU1NjYmLI9tEbrImip8PhKCgoMA0Njh8/ISgoyDdDu2gfLEt2nzqtNjMzY86cOQaD4cnHH3/tzfVKpeaBhx/y8w9ACI2a8QixgAUsSKRSiVTKiRipVDza3C+1VxuTY4YFQbBYLE2NTYcPfxsSHHLtdde5+XYYf+dm3m15GDc11x/NOxoZFZ2ZOcVDBXff8S4Xz3EsAGDnzi87OjqmT5seExvr3Xd7+hUhAODNN//R0tKyatXNkZGR7hsdu88QsgwNwJt7jq/74HNnWBLwM9g5pVOstEOWBzRAWITtehrPTlAvTtWpKKyUStQiIPhU6zAAAgACAlgAGAKKsDC91XAMzBZe4AWRWCQWAQiAgADAQMAAIUKMxxgRvB+TtIymaexxn9izI6FpmqLoQZvNhXA7Bu/vLStscdC6QBvgAAQQEM2EsX2kD1gJAUYMEKSUAG2DnLlX5Rx0tlTcNj/zqRULAQA2j2tsbGw8eeJEU3PzNddcQxI4X+iRXGGzyXz27NmW1ubU1JSkpBTyWbzYodcqnE5HXV19d2dnWloaJ+YYhgMAbHzvvSf+8peO1pZ1f1936+1r5HI5YU65PSX2mUUKYW9vb1FRoVwui4iI9PfXe7JP+AMsEiMsCALDMnlH8v6+bt2fHvtTeno6+N4QvPcWrK+t/t/nn9u8adM996194aV1wCt7RsERcNLJEyfzjx278sorY+PjRuS/JHM4eeLEW2++9eCDD2ZMzhR498UlLSQOQWABPNve+cd179cOCPLo8QPyIBOtcEAGYQAxCpJzejkjBg4WOxmEAMKC24iAgIGABEQG1QtAABghjBDGAGGMMMIYQU8jCfaNndCNNmEek/lcGLvbL9xdP+5GIJL2Y4ApCADgMeYhw0POhikH5Fy0SKB+SFUDA4AFCXboaDvqbkIt1Uk67g83L54Zb0Q0xQIoOF0sxwIA/vToo1Kx9NHH/zR6HKBbLReAUydO5ubmXn3tNVFRUWBUX7ZXyqKtreWpJ5/cvXvP9u07pmRlOexOjmMRRp9/tvnWW1dPnzbtmeeenzx5CgAACZ5Y7G7WczuvI0eO7Ny58+GHHw4JCSEg6OU9JTPW9g5SkAIAhIeFLViwQCaXCwBDzyyTyx+OfBKapru6O7du3XrwwIGoqKicnBzfvg3oI8pAwkTq+FSWYXIPH+7o7Jg+Y4Y3shDLY1k2LT19zRr+3JmzTU1N8+bNV6gUBB6jaZrBgGGozNCg59Zcd7CofmdhQ0dNnT5pskYX2DNkQZA22R0Wu83l4hEQAEJIEAQMMQUBIngikcvwNDy4OV/Yo5FHucsnGLu9KPGf0ONCAQW8Fuh+5hjIok9GSAFIQTFHM7TwvaqGCGIAMYYA0Qhp5SLGam85dSRKK1k+f8rcxKAZidEQALvTSXEcxbEXLlzY/NlnsXFxkzMnE7Kj17Z8c609e/a0tbYtWbrEaDR6t5ujIWQAQEhIWPK4pPfe//Deu+9+9fVXZ8zMIeytpVcu/fzzz5VKBTFoXyeCAUYI0RQNITx06FBTU9Py5csDAgK8nTo/nPtDpuwCrNFqksYlHT9eYLVawsMN3+lvvZ0ZLqfjiy2fvfba6+2tLZmZmfoAfXFJyemTJxVyhZ+/vyAIFKTIu5B+FIlEEhIa0tnV2d7RbrVaZTKpVCqlKAphTFOUw+kUi0QRRuPAQH9vb5/DYevt7dXqdBzHAQxoCjoFBDEwBPiHhwUz2CXwzsaaaptpQKPVMAxrc/F2XkA0S34wKwKsGHBiwIogK6ZEEoqTQJEYiMUUJ4ESKZSQf6VQIoMSOSWRUBIJJZFSUgkllVFSGSWRuv8jldGe/1BSGS2T01IZJZVTF/8ohVIpJZXSUikllVISKSWRUGIRhhT6nmP3IAAI0wArGaASzLbGC/amsgmBiuuzEm+4IjM91B/xAgaQY5je3t7a2toLFy4MDQysWLnSYDA4HU6SJwOAvcOROjs7iouLmptbIiMj09PTSc3MN933Zk2dHR3FRYVms3lCaoqIYfbt3dPe0ZmcnBwUHIwx4DguISHRGBklk8lG0x4QQhjhocHBkydP6fX6nJwc0gr3fYo3l2CjQc8tRVFFheeHBgZDQ0PFEsnljZI4PIfNsufrr1575ZXKiqqw0ODu7q7Dh7/d8vnmY0ePxcbFpY4fT9O0d5o4uW8IrB8bG+tyOUtKziOE5AqFiBORPIGhacI8j46JCQ8PKy0rvXChjONEao2G4zgAIU1RmIJOASmlTFZ8RGJ05IWTx7rbW9Vanc3phIwIMGIXIW4BGmF3dwQCEGPo5ny4fzzT5pHnR8AII4wEjEgQR+7MEbl/vAsLCAkICQJGgvcXhASMBIwENHxdrLlfjm6NAcAUQBwNWYFnTD06ew9oLgmHQ8+tXb0qK0HOYAAAS9MAgP6BgQtlZWfPntXr9bfdfrtMKiUduj64DCUIQnd31/nz52pqambMmDFx4kSyjxxtjgCA5uamzZs/fX/DhqLCc4GBgclJ48oulB789shQf29GZoZcruB5HiHSCgpHgH0YY4ZmLBbLqRMn9f7+KSkpUql0hCL9v8KPhBQkdOhwQ3htTe3hw7lZWVkE5b5UQkkeqqurue/ee0tLy65cunjKlMllZRdYlrv66qvnzZ0XEBAok8s0Wi25Ft47xvupdDq/wAD/jo7O4pISlhP5+/mRr5B4ewihRCoJCQk1GiP27NldXFyUmTmZ7NwhADRFsZCiAAhQiGZNiJerlGfOlfR0dWpUKpVKabM5EIYYUh4OJYVJRIYQQDKcdaz+W/h9FRm9BuZzKDgMrB3rHS5VJ6QwooBAIxfrsgYpRJylr6sw3x8NrVmQ8cdVCyeE6zkIaIwgwBRF1dfXv/fee2q1eurUqfHx8QSb8wZowoABAFZWVp45c0YkEk2dOjU0NIxc/BFOSxAE8m3k5R1547XXamtrOtra9h848PFHHzU1NfM86u/rHTKZo2Ni/Pz8iaG7pxz7AJPEDIZMpiO5uQmJicZI4w/qc7i0RXounkQikUolA4MDtbU1SqVCrdYQzs6Yb0CiAM+75s6dd9uaOyIjInbt+mr8+Il/eebZ7KlTA4OD+/sH62prDQYD4QT55qY8L3Acq1JrOI7jeaG+vr6nu5skOk6nk6FpAWGKosRisUqlRggNDvaXlJRwHBcYGEiOIwgCQpilKI1cZggL9FNwgWrV+dOnOutroqMiaE5k47GAPdvpn3bB79IThd+zf5RMbEUiCms4HMjwdccO2KrO3D5/8o1ZcfOzUuL8dTRAPMYMTVMU9d677548fmLCxAmJiYlGo5HjOIEXvCVfT3coPHHiRHNzs1arjY9PCAkJpSjKxfMUTXuHlXhJPRBCJPAuF48EvuD4ibaunqSk+FtuvX36zBk0BHKlcsGCReOSkklaBYebgSAgItRbkH/syy+3Z2VNjYqO4kSin6iujd1G6XQ6I6Oi/PX6t99+U6tV+fnpRZwIY4xHqaUT3xkYFPzo40+Sv2z7fNOQ2RwdG2uMjAYA6AAoKS754IP3bRZzWmYmGeOAPVRvhnHXbMLCwkNDw745dKiktFStUcfExEqlUgAARQGMMRIEAQlTp06LiorcsGGDn5+/TCZnWTY4OJgEIAFhO8+Hy8X3zcmsHELO1upDJTV8Y6lLoufkelasdCHsaaH7znHR+DvMC/+QnfJ3tndios0DxSyNTP2WwfYAORPm7BwfLnpq1fwQMXBgwS4gMU0JTkd3by/vdJ05ddoQEbFo0SLCyaIp2jcpIt2h1dXV1dXVRqNx0qRJhMOPMWboYXOtCJOwvr726JEjaWlpyckpSUlJHZ1dn276LDTccP+DD4lE4qiYOJvVunLVTcQRjgCbEUIEPKqvr8s7kjtkMk2e4o5gLMv+lF0NxP9TFOXnp+vv73c4HAGBgZdJKL1/r66uemfDhpOnzsydP2/69BkAgOrqys82b9q2fWvh+cK4uPjomBjvcaDPexHnYYiIkEgkW7duk0gkBoPBu22iKIqmGYyRXK6ckjUFUtShg4fKK8rj4+NFIpEgCBQFOYYmgqYyFl+VPTEoLGDvngN2q12jknMMRSMEMIIXg+zlm1q+r8P7Mf2cEGMaCywQRMghQ1YttIPuRntTeQjjfHz1kr+svkYjojFGEAGOpgEAtbW1337zTW1N7apVq+YvXEBqoTRFu5E1eJEDtnv37lOnTi1YsCAlJYUEdPJtjqr0AoyEdze88+zTz8TFxk2YNAlCOH3GtNbmpo8+2XQ8Pz8rK2tKVlZcXDwxxNF7FBKszWbzKy//PTYu5t77HqBpGiHSZfaT9Nl4whCBDGma1mp1zc0tbW3ter1eLBZ7tyZjYkAkZR4cGty7d++EiRPmzJlrt1tefXndx59u4p324JCQefPmGY2Rvoz5ETZNUZRWq/X31586dbyoqGjSpDQIIcJYQAhSFLFOhmakMqlWq5VJZfv27R3o74uOjYGQAhi7XDxFQYqGDE0bgvzjI4KNgfrGCyW1xWf8tRqVSoUAtPECgDSgaDf18CcM5fB7i4IT7SKEOOzSy0RqYHfUF/cV5adouYeWz1ueHTs9JVrOMgLvomiGoqi+3p6PP/m4u7tn0qRJ0dFR0TExNE1jhD0ICcJIQBjRNGOz2davX48xnj17dnR0tJszhoYJogpIcNfYBP7555/LP3r0jtvvSByXeOJEQUVF1YQJE5OSkyvKLxw89O1VV14ZGRXFMMxo3UQS8VmWbWtp3b5te2RkVE5OjlKlwhhBiEfwwn6yzi9PmxnV399fV1cXHBIilUjG3M97UlwokUgMhnCHwz5t2vTAwIBPPvnow/ffb2puizYa5s2bNyltUlNz866vv1KrlRqNzrdI402QWZYNDAw0mYZaWlpcLgfGQKNRk/IAuSSE+ezn5xccHFxbW4ORMDg42NbWERoaSsRMEMI2l0vJsQmhgbHhQVKXiUFOs9nW2NYp8IJOH4AgEFw8Bcl8b7ILhz+NRV7uQTf5FmIMBUHMUEqOlgi2zooSW2N5Rog8O1x+3ZSkm3PGx/lrGIAApGiKbm5uvlB+oauro6en12iMzMzM0Ol0GGDe5YadyZgPSNEURTU0NJw4caKnpyc7Ozs5OZlk7SM8iLvORNNDQ4MbNrzz3LPPBgcGrb1/7ZYtW4rOF0/Jylar1UHBwZGRRp1WM236DI1W43K5GIrxkau5KOPdUN9w+uQpF++8+tpr1BqN0+lgGOrSkk0/3CJ9+RNe4rtWq2EYprioCAlIH6D3KICNmbBDALBMJp06bVpKSmrekcP3339/hCEiIS5mcHBw5vSZVqvtlVde3rRp86xZM6OjY0cHApKbC4IrOjo2OjoqLy/PZDLJZDKRSEx4o14iCUnJU1NTdTrNiROnSkpKdTqtRCJhWZahKY6hMcYCwnIWTh4XMyFtQktTS09rE41drOCkBJ6hIEVTyKsJCH9+i8REOQWIAC/FTtbWRw+2+wObva4okO976MalDyzPyYgKhQhREFIACi6X2WQ6knfk7Nkzen3AtdcuMxqNgsATBN+3hxMA6HDYBgeH8vPzGxsb7rjjjvDwcCKxNLonC1KQd/E0Q5vNptdff72yosJfr29qbDp06NCChQuvve663V9/Lbj4tIyMOXPn+fv7jyQqwIsBzW63HzhwwOGwX7d8mUwmQwjRNONjjj+FRY6OyORXpVIZHhq+fds2i9UcFx+PkCAIY3pK9zXiOBEAeOdXX+34ctcrL/89NSXl002b09Mzjh8vOHb02OrVty5cuEitVnsl/Eawm0hUl8nkRqMRAHjy5MmGhrrExHFkywV9FgCA40TGyKi4uLhXX32lvLw8Ozvba7KUZ1iLQkQnRQavmp5ic/Qf3LBBJGUNYcEChDwGPAYA0D9E5xsATF0Edy5d+xvR9goxggBxEKsoPkyMTNWFvccPpgRK/rjiioeXzZ4QFSynKQgA43EHJ4+fWPe3dYmJiUuWLImIcBf3SXoPPPUYjyCbcPjbb4qLikPDwnJycogS5DBbhABAgDAiGWd7R6vDbvPzD0jPyGhoqN9/8JuB/p633npz+Yob17/55mOPPREaFpY5OXNYqu1jYwRdt1gsu3fv1mq102fMUKvVw73S6GFkP9AiL9PYQIyGpmm5Qg4wqKysrG+sT05OIejMGCClW9wR8y4Xy7ITJ05Ytmx5X2//hx9tNJtMDfUNSUlJz7/4QlhYuNls6evtUygVowuVRGmNkJPlciVFQbPZdOjgQbFEGhwc7NsgTDylVCpVq1V2u12r1ZpMppMnTyoUCo1GAylKQMjh4hkI/WVinUIa7qdUyTh/P111XUNLTY1co1GrVTQAAs8D90UA8LutE36XU8QAYIghBTHEAkQCC7GcgyoRJQx29184a2utmRAgWjE7eXlm0vzMlHC1QkpDGkAKAKfTuXPnzrraOolIrFAosrKzgoKDCeXWS5UlPRWEpXX69Oncw4cCAgL0AYHx8fE6nc7LsRhNMhR4oba2duMH73/+xRc9XZ1XzJkbExtbdP58cUlZ2oTxx44e3bBhwxVzrliwaHFgYCAiM0uHsQrdW4Wenp5z5865XK6JEycGBARcVoYK/isWeenDXWwsxAAYI40Wq7XgeL5SodBoNGKxZHTrOHRP5wU0w4SGhqWnZzAsdyT38PYvd7a0tU2ZPPmBhx4cPyG1vLzik48/+ebQoda2Fp1O573JvF6FhG+EBLFYHBwcolGr9+3b53S5tFodw9Aikdh7qxAAH2M8bty4cePGVVVVVVRUYIxZluV5Xi6TsTQNAeR53uriQzXq2RnjdXq/vrZmp8MkAYK1t0ewDsklHMMyAqAEjIHHCf0Ii3Q/RgEkooCcQmL7oKurgept1bkGDBJHnBytmJP5+6U5sWFBDAAko+3r6+no6Gxubj59+rTD4Zg6beqU7CylUknCgpto4qHWUhRlNpva2tqOHc0zmU2LFi2OiDBKJBJB4EcwZL1fIk3TNENXVJS/9srL+w8eOnfqROr41KzsaRGG8OLz5zZ+9Gnekdy58+f/481/Go1G3w5az64cQ4qCEA4ODhYWFnZ1dWVnZxOeNQQAXrJl+1+yyO8EM0k+IgiC0WiMMBjffPMtjVoTYTQiAUHK81o8zCp9X15aVrxjx05/nd+fn3py4eLFBXl5v/vd7z7+eGN5WdmOL3fwvCslJVmhkAMAkYC8StgQQk/3GJbJFbNm5bS1tuQdyRWLRIGBATTNIIEn86q8HboYY4PBkDl5clVV1TfffGOz2cLDw0ljEE2SSwh5APwVkiWZSVMmxHZWVtQVn6WdZj+NEtOUAwMM3BDwxYA1urnMLYg7OlP0XH4IIcA0EBgkcLxNjSwKS5ezvkjUVTMnPujpu5fdOW9yQlgATVOEsksuV25u7r59+wVBWL58eVZWlkQi8YoyjNAwgRDyvKvo/Lmvdn6VlJS0/PoVIpEYDIfSRi+7zc6wDEPDA/v3dba2RBiNhecK4+Jip06fIRKLjp84fs2116xfv4ETiX3rMd4vVxAQRVMI8UdyD/f29KakpkZERIxZBBqOO3y/6te/JhfkpXaeOnUq99vDkZGR1y1fdhEOxSM9CEIYY0RRVHl56aEDh0JCwuYtmG+1mu+67fYvd++ZNS1r7dq1J0+d2btv34yZM15/4w2eRy4nL5GKfa4pAgAjBIjl9fT0tDQ39Pb2ni8qzs7Onjw5i7w7cQC++WhnV1dXZ6fZbD59+rSfn9+VV15JyAEOpwtAwLEMCczF9c013X15lT07j51v6LNL41JD4pIGbbzJ6XIKAEEGuK81xPCSLtHN/MGYwgAARCGBglgmYhQiBltMTaePgb7WzOSohZOTUgJFUf665IhQ35e3trcf3LcfAhBuMOj8dCqVigCxXgqPm8UjCC6eJ/2fu3fvrqurnTA+WSZTGCOjSYQZEwMh5USEhHNnzr355j9j42IeeuDBB+5fK5WI0jMy777r3uU3XP/ya69RNHXyxPHgoOCk5NTRh8IIC7zAcIzZZD5y5BubzRYfnxgTG+fbvvNj94T/soKvF4vfs3tPedmF1Injc2bPpiB0uVwsw44pYgMA4HknxIBmOQDA7l07b1q5asKkSc88/XTWtOl2i3lqdvaQ2XShooIwQz3NchBSXpo6xBjzvItlOQBAQ33doW++wQIfZjBOnjyZfB+E/UhIVgghEnFMJtOOHTukUqnBEN7e3p6ZOTkgIMDtMBxOjqEpmgYAnOu07DiQW987WNppruwwA7lOFR5JKf2HBNqOCX/MF7a8xPxUJLAAS2ggpXiOt3bV19h72uNDtGEyHMjyaSkJS3OmRAxHKepqaysrK3mELGYzTVHTpk0PDHLT9TFClMc1DrvTOjpPnznd3NwslUpyZs0KCzcAH6HR0YxVkva1t7Wvuf2O3fv2pCYlzp0zx+VyanVaP62upOzC0WP5c+bOffmVVz1cXSfBNHyLhKQq09zcVH6h3GweSkhIjI1z9zGDn2ju9r+ujeaZy8IvXLTQT6f76KOPdDpdYmIix3G+eNXILIFmMcbk0w4ODWEA7rz91qxp0x0Oe0VVJYZQ7+/PMNTgQF9ra1usp0LgezgIIctyGGNBQBHGyDvuiNz15c7tX2wL8NfHxMXSkJbIJMTtkQhO9gEKheLmm28GAOzfv2/Lls/FYklWVhYGQCaVikUcAMCFEI9xgr9k4k2LAAAvff7Va+9vkxriGbPE7HJASspI1TTNIQAFr/ba6B0MgBBCGmKGtyPzEHKZdFIIzc2W7qr06NSHVl83MUTvBAAD7AIQAsA7HU67w2q1lpaV7dy5c968eTfccIPnVhQAwBRFAR+JBOKurFYrxrikuOSLL764//7709LSvMY6Zr2OEKzccoEItrS26nU6LKBPP/1kyZIlX+740mKx7Dt4iHn51eLzJQ6bnWYZASHRCGgPAcKatVgsJ08et1isixYv9dPpvH7Us9/6d/jIYfRMjCGETqezvrZu40cbp2RnL1m82FeLY8zldLo4jv3mm4PLly275aZV69b9vbuv79FH//jhhx+vun75x59tvnPNHVXVNevfXh8XnzBmFdW37Gc2m7s7u3q6e06cPBEYGLjs+uVexzA6lzKbzX19vRUVFUVFJRqNeunSpXq9HgAgIB4j7OmuBH2DQ+0DQ4286LVPvz5w+gITFKWLipOo9XYELQJwIixgiCADCQkcCxTiGYw4hhIzFCc4BPNAW1UJaKufnBq/cn56dqS/v1Si16i44YjEuaLCnTt2ajWa65YtQ4KgVCpVKpVvluLB0d1bZmKRO7bv6Gxvj42Pj4yKDA4OvhQqPCKUtTQ3U5AKDg2prqxafcvNpqGBxx7706FDh97b+ElUZMQXW7aGhoebBociIo1u5Gb4dXPanZyYs1qtGz/8IDQsdOrU6Wq15ueYmPgvqvX55teEiufn78cLQlV1dWNjY1JSEiEBjclbwxgDgCkKKhQKjuP27t2zbceOPV/v3rJ1e1Zm5kMPPsi7nH/8wx/9A/x//8gj5eXlLMNIZbIRMwSAZ+qxIAhisVij1TAsQ6DaC2VlfX19QUFBJOjwPE++WhK5CHVIJBLTNK1RaxobG0vLShwOa3BQKOnBddidPC8o5FK9WmnQytRyUUK4X0JYkKW1vqHkrKm9WclRWqVcKhZDSAkAAoxlIspPTCuR1dlW03fhNGqpjFfS85PDlmZELUqLm50+Lt5PrZRKaM/JV1VV5ebmVlVVyWRykiwmJyerVCqxWCwIvKc8SwEAEcICLxCVOafDceRIbn7+MaVSGRIaEhsbFxYeRtM00TkhE9YukmQI+IYBTdNms+mll156443XDxzYj5Awc9YsnUZdVHSegvSsnBx/f38Awdw58yKjojRaLQFIhgdrAWPEcmxDff3+fftlctnkyZP1+gAIibQE/mlHef4rFjma8kMwl5iYGC8EqFKrJGIJGKtp3AtJyGTyiRMm1NbVHM492t/bExsV9eRTT6ZnZLz++uuD/QPXX79cqVK9++67nZ0dYeEGhUJBQsMItJIAUgJCSqXSaDSqVMozp88IguB0OG12m0KhYFnW2+VOkkue5zUaTVRUVGRUZG11TX1DPYSQY5m+/gGMgEIpZxgaAWB1OAFAyaGBM8dFJ0cZwEA7NHVrJYySY/t7e3q7Op0OB8UyFBCcvR32tlq5oy+EskUwtmQNtXBC9O2Lpl09KS4pPFDBuvupurt72tpaB/r6GxoaqmuqBYQy0tMnTpwYERGBMeZ5JwCY9Ij5iA5TFE07Hc66utqWlubKyoqenu7FixcnJCQqlAoyDmJ4qwAGXtUGDBwOR1NT097dX3/6ycdDQ0Mnjh8/c+7sVVcumZw1tbqq8p///OeSJUsWLFygUquzs6dCina6XMzwxgMCq1EUVVdXl3/0mMVmu+qqq/R6vU9NEv60Fgl/wtkk5CwbGho++OCDWbNm5eTkfA/ZfuSw2xsaG3p7eoMDAsMjowqOHb3ummvmz5+fNC7py51fVtZUJycn33//A1dfcy0AgBd4hmZ8kXzfjhh31Z8XzCbzli2fNzQ1rFlzJ0HUxk69MRAEAQPc3Nh06NCBlta2qdnT5sybA0YPHMDAhgQzxnX9rr0Fxe/v2Nvc0aeMStSERjAicXt1ubWuPDXOsGLhFfPSkwwqLKEgAynGXSV3v+nevQfyjuSGhgTPmjkzJi4W0jQ9LKkYNscdezrIKAiryivffe/dpJSkhYsWqFUahmEvWx9yA/wAANPQwCO/f+TggQOrVqxYsnjxq6+/fuhwbkF+fkxs/Nkzp15++WWHw3HrbbctWLCQomjvxmVYsHY5OZYTeOHPTzwRFhp25z13kWbLn2/E8Y/NI8eEhIpLinO/zQ0MDFh+/fVguMTbdx5n1/Ztt91+m0yhiggLqais6OwdeOGZv95yyy3FJaWRUVGR0dEIA4AxTVMU5b403vqUL1RRV1vX1dNls9rOny+MjYlZtHiJFwTxSi94uyJdTldDY73Vauvr6S0sLBRLuMVLloSHR7hf4nTSNIQ0CwBwANDQby6va3I5nSZGXHCuymrno8P8YgKVQSq5ITgoXCMbIS11LO/Ivv37ExLHxcUn0BSUSqRhYWFSmXQUrOPWo0cIUxRNsNivdu1sbmo2RkT6+/vpAwJ8waDR+A4GACPE8y6OE3lwR9uNN16/48td83JmxMXHl5SWqrWat95+Rx8QZLNampube3p6jMbI4ODgEV+H4OFQAgDOnjm9efOmKZOnpmekhXtogT+fRf7YPHI0gZym6YCAAKvF0traarFaGJpRqVTehrfRPRk8z5PQIAj8+cJzGz/8oKy0pLO3b9KElKnTpjY11C9bdq1Crnj0j4/yvCspKUkuV9A07eU4QR8ZF7eQBi8AjLV+utDQUJvV2tnR4XI5BgYG+/v7lUqlWCz2rXl4557odLrAwEARx9U3NEilEoxRfX1Dd3e3RCqVyeVkB2N38QAJgTJJfLD/uLDACSF+Og4l6hULMsZNizFE6rU6CUduOyfPV1ZUnisstFrMg4P9vb39AYGBGZkZBoPBz8+P5ViS5/gWYEhhEEKKoiiHw1laWlJWVmI2mQGA0TExk9LS1Go1KQCOWYlxR1iKomkGYNDa2ioIgkKhUCiVTQ0NeXnHKivKp8+Ycdc998bExkEAWZb18/MPDw9XKBQ+mehFz0JRVG9vX3V15YULpU6na9VNN/v7+zscju8pBPCLoj+XOSEiCYwRnjU7xxgZuXPXTovZQpiOhB8wOhFkGJak8xRFt7S21jY0qDWapVdOX7ly5eDg4JHcI5s3f/a1Yk99Q4PFaqtvqO/p6fHXByoUijEvDdFYI5RVjEHiuHGJ48bV1lZ9+MGHoaHhLMeFh4VxHEvs0st7B24dABAcGnLX3XcBAPKP5X399W59QCCEkI6NoSjAcSKxSOweGYawgBEFYXZKgq/Ld7lcTqeT53mLxVJUVFRQkD9p4oSlS5deMWc+Cabe9GtExPAahN1udzgc3d09J06caG1tefDBB/389MAjTzdipzgc9AA0hBjjvr6+4/kFhYWFKpVy9uxZCxcukovFq1bdKLj4yZMnT506AwAgCDyEbqH40dIjpBdvcHCwoqKiuLgwOiZm5apbAAAuF395WcZfXR454kohAfX09tTW1paWlgYFBS1evBgA4HA6OY4bk6JLVDTKyy+cOX1qyZIlgwMD6176W+G50+WVtdFRxocffuTa6284eGDfSy+9lJWdff/a+2Pj4kl7v3dw4qUTXL67uwdCePLkybKy0nHjEufOnSsWS4FHRc4NEvlA+haL2WQyURRdVVV17twZu92enp6WnTWV89TokCAgjBmaAj6M1KLCc/nHjpvMppTxqYmJiSzLSiRilUp9ma5Qr7gSAMDlcn777TcnT55OTU2dOHEix7F6fcD3dEhEGaa2pvrBhx4sLSpBvMvJ82FhYf98662Jk9L+8sRj77yzYebMmc88/3xsXCwAF/eII7bVxAFXVlYeOHAgKio6ISE+ICCAdJX8rMH6J0DIL+9EiefX6/Usy5J+uU8++WTJkiUqlcrF8zQFSTHQl4gOIVQqlZmZk6Ojo3U6vy+Ob/5o02YAwKSUlAceWHvNsuUOl2vb1m3nCotW3ngjCWEURSFPIBujVuFBJRmaIYpF8fHxIhEnEon27NnrcvHJycmJiYm++SWkIEaY4AAymZx8STzPOxw2kUiUd/RYZ2enVCqbOHGCwWAgVma2WI8fz29sqA83hGvV2tjYOAywwWjw5nwen0Ta9i7OjPGqLdA03dHRcfjwYZGIDQwMSEtLi4yMDAsL81rJpSrUXsUvYkatra2bN3+ad/jwVVdelZaRsX/v3j0HDm7/4ouMzMm33XbH4dzcto4Oq81C8JoR/hWhi/qOn3766UD/QGpKiiEignwKF88zP3Ow/nktknw2Yg0ajSYzM1OpVH711Vf79+8nl9uX+eabhpLvSafzI8nluPh4yLD/84f/uX7lKgDAGy88d+DggRnTp956220arR/JWcdsN/bFLBmPEA9pCY+NjbVYrNu3b+vs7CSJkUwmCw8PvygdRrvt2DuEmag0DQ0N5OUda2pqUigURmMEy7JdXV0IIYahu7u6GxoalErV+JQJaekBvlx/jxQgM4Ls54W7a2pqbDabIAhNTU1BQQHjx8+XSuUjaGaXT59IFk7TVElJ8RdbvpDL5I899lh8UnLapEkd7e25h789+u0303Jmr77tNrPVajBEEF3xETUO8i4EnyouLk5ISJg+Y4a30MAwzC9hjL7U9p91EfPief6RRx5+4onHfP94mVf19PQUFZ6vrqgaGhrEGDfX12VNyQwOCnhn/Vs2m4UcgaRu3sN4D+ju6scCQjxh8vkuhLHD6STjWO69995HH320rq7O94UXjzP8xTzP8zzvdDr7+vo2b9583XXXLlmyaPfuXYIguFwunhc8r0Cj33T4iZER5Bhj/Pjjj99+++01NTXk4Je/Jpe6vOQ/27dvi4kyquWy/Xv3YIzbWpuvXLwgRK/765NPEG0su902+uXE9DHG5iHztq3bn3rqqerqareS1tif4TKf7ydY//qEpR+0iEsICgqWSsWF5wqbmpuCg0NEIhHR4fFGbV8UUCqVBgQGav10IpGoqqrqr089dSzv6I0rb1y79gGRSOxyuViWgxC89dabTz75RF1d3YwZM4eTz711nYvZktdFkb2kVCrV6/Wpqalms+m9996tra0LCAhQKpVe38MLAvCMjfA6NpqmxWKxUqmMj0+YMiUzJSVZoVCSrgEAIAYIYEROwRtViSH6ztDdufPLnTu3Qwjj4uLT0tKio6M5jvNMMcIjfNiIXwkwTlIjiqIwBgQqYhiquampsrxCoVJNmzYVYLx+/dtKtermW26JjIqkqJHxhKSwxDtu27q9qrI6OCRkwsTx8fHxYw6F/UGdG7+6qD2a54sQSk5OjomJOrD/gMALBfn5gYEBqePHUxRFvJvvnB/vN+F0OFiOs5hMZ86cGTBbxCKRihB8MEaY7+nq2rrl87y8Yy677TGLae78hZmTJ4tEYlLd8gWJRhxZQAgjzLJMRkYGAKCxsV6tVslkstbW1traWpZlIiIigoKCOa98PJn96IlxDE0bDBczRUHgieQYMTmvEoZ3g0w+Gu9yVVVX93T3SKUSQRCUSpVIJEpLyxgBlFLD1UFH2BDDMKSQXXju3L79+3JycjIzJ5Pp8kZj5NIrlx7JPfLZpk1m0xBF0yaz+ZbVq2fMyoGQdrlchHvrzfKJgZaVlTY0NDqcDj+dX1LyOKVSAUY2WeOf0QB/FB6J/5Wbw9ct8TzPcaK4+PiQoODTJ09VVlaGG8JommEYd6bl3eVcdJYUmXIKnQ57Z3tbT28vzVDBwUFKpcpiHtr6xdatW76Ymj1l3pwrPtu0qaa2xhARERFhJL7MW+Mas4xJ6hMkNmk02szMyUlJSd3d3UePHm1oqJNIJEqlwuGwIySwDENRtNtBevI/4vYEjAGEFFH/pahhDHrg9qkII6vVarPZ2lubz549U3juvEQsueKKK6ZOmx4cHOIdCEx7Jr2N2JqR8/duXwAAAwMDEMK8vLxHHv6dyWSalDZJo9EAAGma9vf36+7ubm9tO3LkSHNry9KlV6266Wa9PpCcjBcvI8cxmUz9fb25h7+pqa5ZsWJFUnISx3Hkyvskr6NaZH5wL9fPh/7gH+uuLwpFC3jQNFhVWZl75HBUVNSCBQulUtmlSjtIQBhg09BAaWnpiy++WFBQcNddd/3lr39tqKu/ccWKs+eLrlm66MUXX4QA/P3VV2Vy+d/WveKLiRBj+Z5n6HA4TCaTy+Xo7+8/e/ZMWdmFjIyMhQsXicUSH9oBvqgO6oM9ea4k8rhGt4/p7+/fs2d3ZWXF+JTk9IxMkUgqkYgVCgUYpYQ99gV3C8C6iGu0Wm1/fvKJhQsWxURHXXXV0rILFY899uhTT/3Vy4QymQYrKiq6Ojs1Wm1MTKxO5+f9+L5EycHBwY0bN6qVivHjU4JCwv39/S9fmfwpBl//+/DIyxslQoiiaAiBw+EoKMjXaNStre09PV233HKr1/f4ot8XxVsBOHBg/+nTp1NTUlNTkz75+JOX1627ceVNFAUuXLiwYMGCoJAQvT5QpVLs+np3UGDQyhUrZErlRQIfwAAPl/f03F/krHxrIRaLuby8vKWlxWg0DgwMFBaeCw0NnTUzR+fn51sjQV70ynMEr3dxOByHDh1qbGw0Rhj99H5dnZ3GiIjEcUkXISFe8KjpXeLWx5DneZ53iSUSAEBbW+s776zPP5qv0/k9/cyzsXExX+7Yduddd4eHhW7c+FFCYuI769+uqal5/PEnNFrdsMMRFTN8MS/aunVbTXV1RkaGSqUcl5QgFsvAWJLP/5aozYBfdnnqZoDneZFINGtWDgCgoWFHZWXF8YLjoWGhAQEBXuV94GkfI7K/kKLmzp03d+48AEBB/tGdO7+0O+zXXXM1pOlvc9d+tmXLps2bIyOj19579z/fWh/k72c1DV0xf15kZDTh3HvKmCP1k7xJhfd+IHhkWlp6Wlo6AODgwQO1tbUUBdvaWgcGB512h0an1ev11HBuHPnNZrO1tbWRjXNXV1d9fX1EuCE9LX0sSIi+xE2LSGgFEDAsw7CMzWa7cOHCtm1bd+/aqVJrFy9e6LDb2tpar7r6mi1btuzft/8fb7weFx//ySefuFzOVTetUihVGECAkXc3Bt3QqaW7q0ssFldVVjrs9pzZOQAAhHied9I0e2mYCYJf2Gn9VMsXN/n+T3C5eEEQOjvbn/nr0/944x/t7e3DUInhWIMXksg7krtwwVw/neaRhx/qaG+12SxHcr91Oe0nj+dHhgWH6HWJsdHGsNDp2VPyDh92C4PzAlF19B7ke4IYLpeL53lB4IuLzj//7HMPrL1/69atXV1dLpdrNJJSUlLy0ksv/eEPf/j6668Juu50OMd+G4SxgMZ4CPEYC0R2WnAJGOOTJ05kZ02hKOr3Dz0oCEJBft4f//D7zz/bhLHwz3+8HhsVqVUqFDLJDTcsO5L7rSC4fME13wt+9uzZdevWffrpp02NjTzPY0RAKPLza1k/JfrznX2Mo5+AMIYQUBQlk8n9/fX6AH1ZWdnevXs1Gg3JbAQkYIQpH8V2slQqdVp6ekJC/MFDBzdv3gwBuOKKuRKp7KONHx44sP/W1asf+cOfFDLJzi93xsTGZk6ZAjCgaMrbU3cxHbw0uu7NZzx7DkoqlQYFBY9LGhccHNzQ0HDw4MGzp8+YzSanw1FaVrp37+6SkhKlUkF6c6Ojo5VKJfGFRDp/JJjimRTg9Z3uJ0AKYSwIyOmyP//sM1s+3yIISKVStLW0dLS2tre37dixLSg4+MYbV0qk8viERJN5qLKy8oH7H7zr7nvGT5hA0yzAACOMfMCdkuKi7du2WS2W6dNnREZGhhsM7jRmZKv/v38x/963JxFUEHiKohMSE0j61dvbW19f39/fr1AokpKSgEfayrfzVaPRaDSaxIQEnhfee2/DsaPHbrnl9tqamgMH9vv766++9ropU6c7LUOvv/5GZ1cnRVEYoWNH80qLi7U6XUbG5IhIo2+mP6bEuvdXL2iqUCgTx12sOqrVaoHnXQ5Xb2+vw2GXySRSqSIkJNSLChHseoxN9MUEjWj2Ii/3wmq1dfd0SyRivb/ebB7at3dPaemFvz7z7H33re1obd/46aet7S0PPvS7q665uqjo/IUL5cuWXb/qppvCwsJvuWU14xEexwjTDA0ADQA4d+5ca0uLQi5VKOWRUVHx8fHD+YG/FkP8tVikxwkxhLuAAcjOzs7Ozi4oKMjPz/f391coFFqtViaT+WY5HhqbwLDc3ffcO2vWjObmVpZltm3bmpuXnxQXp9ZqTUODW77YKvCCwWBASNi3d8/Tf/lreVlZ6vgJ2dmF16+8MS4uTiwWf58BFL53gle9KTk5OTk5GQAw2D/Q298Xp47Tav28FuyWbmOY74wqNITAg8WIxeL+/r53N6zX6/Vr1twplUhDQ8OaW9pkcnlYuCE5OVkqlYaGhi277rre/r4nnnh8cNCUkJCQM3tOdHQsEhC5sSmKAhTgXbzFaqFpOu/o0ZampnvuuWtmzhW+zJLvPLd/28K/yjU0NNTT01NeXr5mzZo333xzRErnLRF6sze73W6zWK9fvgwAEBUevuerHa+9vE4mlYYHBZWVFpeWlgTo9RQETz75xAfvbYg2RqSnTdyy5bNR+aKD5x0I8T/0bF0u1/es/hF3O2aB7rVXXz554nhrS3NSQqxSpXr37Tcxxvffc3dYcPALzz2PBFRVVXHTyhuD/P0SYyIjQgIXzb/i1MkCs9mEBESyUp538byTHK26quJ/X3hu48aN54uKOtrbXU4n/g9Zv1AV8fsvsvsRi8VSqVSr1TqdTqPR2NXVtX//folEQna4EEKB54mT8ZYfBAGpVKrY2FiEhWPHjn208SOGZv746B/nzpv7xZbPt23fcfsdtz311F8y0tMRzx85fFivD5gxY/qGDRs2bfrYZrMFBOhlMgVF0QC4JXU8uy63qY0I5b4R31P9Q5eqvGEMeN6JkEDTjDeRRQh3dXUdOnTg3Xffff/99woKCtLTJ02clC4Xi7795lBxUVGAvz9CeGBgQCqTz5g2PSAwoLa2ZsfOXcHBQddee+3Nq2/Nyp7OcZzL4eJ5nmEZAuFXVVXs2rWrvb01NjY+NDQsJSVFqVRSNC3wAqHb/TIUnl+kZvMLwkNkt8gwTGJiosFgqKmpKSoqkkgkDE0PDA7I5TJCciNYjpufwrIxsTEzZs6USCUNjU1isfTW1bfcs/Y+q9Xyzvq3rRbThx9uVGu0e/fsCQ0JoSE9KS0tOCT4rjVr9uzeq9Pq2js6qqurBJ4PCg4mMK2XKua1OW89yWt5Xvq3L6zr+wQvBclbS3S5XILAsywrCMLevXv+/ve/Hzn8rVqtTklJ0en8/fz9p06fKZOI8vMLCvILNBq1xWJBCC9ZuoTlREPmQYfd/tgTj6+5656ICKPL5cIIsyKWYRi7zd7c0tze3trV1VVSXBIebliwcFFISAixfgggRVFuFbdft0WCX78bJzVxnufPnDm77m9/W/e3F+vqqn3j4OjISDAXEhxra6uuu2ZpgE5dV1t9+syphLiY9Inj31+/XnDYz548EWOMyM5I/9v/vjB/3hwxx9171z3kIE6nc/iRL6JQI0aBjI7IIwlECBE0x2E3V5SX7Nu7Z/++PUNDA2bz0PPPP6vRqFbesNw61F949sxzzz79/nvv2qw2QRDeePVVnVIRHREWFxN5+22r7XYrGdvoyw9yz4vCGCO+orzs7+teWrfupaamBu85XAp6+06c7t+4GPDrXt7uHJqmY2Nj5DKp3W5pbGjc+eWuwKCgG264wSvI6wO/Q69DQggHBganpWds3f7VCy+8cNvtt1999dUb1q+HFKQ4UXFxsdPpHBoyqRSKp5/6S+c93VqdHxnGS9N0U2PjK6++bLfboqNjDOHhcfFxERGRMplidMMeRggOH5HrU8Z0sSzb19vz0t9eLC0uNpvNzY0tkKaX37D8tltvu+bqq4/n5xecPHXnnXfa7Y6omJi5c+eJJWIAwMqbbrJYzY89/oSfvzZ76lSy+fM2FZDBW+Qd9+zZffbM6czMjDlz54pE4qCgQG/lfbifhqNhhF/h+rVbpC+tQaFQxMXHAwDKL5Sp1U0Yo5MnT/T19cXGxkZFRXstmADXXjuWSmVLll5VW1tfWlry3rsberp7u/sHlSr1QG9P/rF8sYgLCQ2uq6vr7+9ffsOKiKgo70C/zs6OD99/X6tRO2baC8+exQDfd9/92VOnlZaWnD17pq29XSGXxkbFZU2bKpcrGurqzhcXNzY2WoZMIqlYo9GkpKSkpaWT795qtR48cOBcYUlMVMSMmTPzjh17++13/HX+v3vk9/Fxsbt275VLRKtW3Tx7zhVyuaKspDQgMNDP3+/Ou+8xmS0yuXz27CsoivbKltI0zXFcZ2fn0aN5UVFRUqlUq/MLCQ0f5ylR8rwLQup7zrH8LWr/qJoQiYrkV5Np8KOPPnzggbXbtm4ZGBjo7++32Wy+UdYbf8l/3vznP9LTJmg0qtTk1KqqqnNnTkeEBCXHx7z6txdfeObp6AjD3158yeV0IYTIS04cz/dTK+bOmv6P11556MH7p03N2rd3t8k0eNttq/10KpalNSrZxORxe/d8zbtc2z7fbDSEAQBCAvRajQoAcOOK670n09nZvvrmlQzDPLj2Hozxp59+wjLMtKlZDoftqScekzDMo//zcFtLc1lp8XPPPP3S/75YXVnt+0lH8HN7e3sHBgby8vJWrLh+8+ZPfR8iG6b/6MX8B908I8KiXC5fuvTKOXPmNTbUrn/7TQGBOXPmEFkm4GE0+gJvN910y8KFi1wuB8dJQkJDdmzd2tDanhATHRQcsmDhwrvuvYdhRQzL+GxNMMbY4XBotOpVWaseeOCBgMDgr3ft3P31V5OnTF5733111bXPPvvcxx9ujAg3qFRK3mlfds1Vb6/f8M2hg3esuaOmpsZ7qmKxOCEugQW4o6MDAJCcnBwRYRgcHHQ6HFOnTt097uvPNn++9YttGOAwg2HljTep1cOaxXzrSa2trZs2bWIYZvr06S+9tE6pVHpF6P5TneJ/VtS+DIGIpiiVSq1SAYlEbLHaEcKDg0Pbt28XED9+/PiY6Fgvf0wQBAChXCGXK+Teg0RHRa+5dXVHR8eOHTv27t2rDw666667FQqFt4HVYXewLMcwTOG5ora2rt//4Q8AgPz8fIvFPHfuvHnzlzTE1rz++j/Ony+srqoMCws1Go2NDfWffbapsb4uMTExe9o0jBEBkqQSyYQJE4KCAl1OJwDAZjVbrGany2l3ONIyMufOn//tt4cjjcbEpKTouNiM9Ay1Rk1Om8RoCOHQ4EDB8eNDQ0P+/vrU1FSxWBwVFeXRdeYJ/fHXvon+L7ZIMk0IY9KiilQqdU7ObABAVVV1bW2Nw25t9/fjXTwAMDAwUKPRuCncPE82QGSLkDph/J+f/Et+/rG8vCOHDx8eGBrMmZUTGRnlHn/rclZX1zhdfOK45IDAoN6+/q7ODoxRf1+vQqEi5q7R6WRyeW9Pl8VilkqlUqmspKT03fVvF5aWp02akJ2d7ZEK5xmWG5ecHBIWVlxS+s4/X88/cRxCOHPmTI4TKZWqpVddlZY+ec7cOb43DPAIKtXX11tMJhfvbG9rNVksRmPkrFmzvNsm37ay/471H/xh3CAfvBiqYmKiY2Kied7Z1NS0a9fXbW0dS5YszsjIIFtUhmGGlc5oOsxgWB4WvnzFCtPQQFtrR3BIMPBobvf29tTU1rKcePrMnGuXXUeqwB3tbTqdn8Ph7OnpAQAMDQ0NmU1SmSwoKEgqlfb19c2ZM+e+tWsf+Z8/tLW1NTU2uvfFLl5CM8GhYfGJCUcLTvzpsScARa28adUjjzyiVKoAAOkZmR7V1pFhuq+vb9eur+rraq+88sply5bJ5Epf4PMHTXf7zSJ/bnsEo3k65FtkWVFoaNjChQvtdodarX7jjTfa29tvuOGG9PR07/NJUwtN0xQNAYAqtVal1vqaAkXRfn7+iUnjgkNCCA1CEAStVpeWlvbq6//485//vH///pbW1uqaultvuWlCWobDbhsYMlkdjriExDVr1jz66KOff/75DStuDAgI9KZ3y69fkZo6MTQ4RCyTxsXFGQwRwDNab0SyiAX0yaZNZ86eWblq5YIFC02mIYMhQq5QAZ/+uP+OGP1f5SNHxHFvfgkAEInEsbFx5CGdTkcSsvz8fLPZHBoaGhsb6/UuPO/ieYGo0/puJuRyxRVz5hgjI8MMYQSUpiiKE4mmTpv+0IP3Hzt27NixYwDga6+56pbVq5UqtYmCk9LSlEolTTFXXXV1fUPDQH+/zWbFGLGMe7eUnZ19xRVzvG/hJT14P4LFYqmoqGhrbTOEh6uUSr1er9PqoqKivHedr67pf+v6pbsafmFIy+ufBEFYv359fX19enr6hAkT/Pz8aJoSiyUXBWoxwN8lzomQQKQ4Tp4oyM8v8PPTLV68WKvzxxgLvDM3N5eC1JQp2RKZ1GqzmoYGOU6kVCqJTLe349ZriN5zczqdNpvN6XR2d3cXFBQUnj135dVXz507Z4Th/rc6xf8XFjnm6uvrI/3/hYVnS0tL5XJ5dva0iRMnjgjll1Iec5utZx6j1WplGEYikXgfcjpdJLfzJVZSFPSMHLmoPOaVCSV/OXv27NGjR20225QpU1JTU50Oh1yhIAMlyJ0CAQT/b9Z/v0WSAq4vVlddXdnc3ExRNMtyAwMD3d3dISEhObNne1WZBUEg01jB8BEywNPrzXiORiQbR1jw6J5/L8TP+OxFTpwoOH/+fEBAUHBwiMVihhBGR0d75X4QEhAhFkEK/H9azH+9RXoZOoSUwDB0TExcTEwcAKCpqam5ubmtrU3Eidpb27q6OgGAcfFxMpkM0MMSAOAz0YihaQEh7FEHoHzs2GvBPo1mPg3jNM3zrsbGpoH+folEPDg40NraIhZLp0zJCgwM8AI6Xto5BS/a928+8tecJI6x1/4xHhRC6HI4y8rKXnnlFZFI9Mjvfx8fH+87NP1Sp+B7FmP2sl/cPmOMsQAppqO9dcuWLSdPnpw3d/5Nt9ziu9f+zsz4tzzy/9dyOV0V5eUsx2rUmm+++aattS05JTlrarZCofBNNN39Yp59Bhxupl6m14jm14qK8qN5ebzAp02aGBIa3tfXp/fX6z0jnn5bw6J2dXX1f6CPxN4uvh+5JSd9UhRFSSSScIMBUrCutraxqam3p1dWJ0MAi8VihmGCgoIiIiJ8AXaexGhIQQpijJEgYAgZmgYeItzg0FBDfX1Pdw/AuLevr7W1TRD41sCgiIjoCIPRZB6qrKhECBERgUvIQwII/99ZJPzggw9+uy99sUyGZSRiiUgsslqszc3NLS0tLMsmJSVlZmYGBARACEnHxdgHQdhitTgdTqfTWVNXe+L48bqaWqVcERUTrdVpIUXbbFaHzQ4whjQFKeq3yz6GRX722We/XQUwfFwIwzBEz83pdBJJMQihw+Gor68XBCErK2v27NlyuXw4IgQAAN1d3Xv37LlQViZVyENCQ0ScCPECBSAnFlEMDYkiMC+QcI8p+NtlHyNqX7yyv63hgBHLsnK5nGEYjLHNZhsYGFCr1RBCq9V6JDe3pqZGEPDCRQvi4uLOFxblHj4sl8uCgoIxBFo/P45jZRKpSqXmOA4hweXiBSRgjCmOoynKO6vmtzWGRV4qAP22vNAPEUjXarXx8fE0TZvN5tqamvOF5xHG45ISNVpNQ0N90fnzSoVCIpbGxMYkJo1DTt7ldLp4HgFMMYyYYSiPIQL4mzFeNmqfOnXqt6vwva6Ur0rvRfUyt41BAD24JfB9AqCGyWH+tr7bR15UhP9tff+rRjMcxwIAbXYbUXYUi8WkxYfg5G4jBgDA3yzyt6j9i0RzASOAgUQikcqkbjFBCEl/4G/X50dZ5OWnM/+2xozaHqwH/SAEB/7mL7/H+j+qmA1YmaebSwAAAABJRU5ErkJggg=="
LOGO_IMG = f"data:image/png;base64,{LOGO_B64}"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700;900&display=swap');
html, body, .stApp, button, input, textarea, label, p, span, div, li, td, th {{
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
}}
.stApp {{ background: #f3f5f9; color: {INK}; font-size: 1.1rem; }}
.stApp p, .stApp li {{ font-size: 1.1rem; color: {INK}; line-height: 1.6; }}
header[data-testid="stHeader"] {{ display: none; }}
.block-container {{ padding: 0 1.2rem 3rem; max-width: 1200px; }}

/* ---------- top header bar (like the portal) ---------- */
.st-key-topbar {{
    background: #ffffff; box-shadow: 0 4px 10px rgba(31,36,51,.18);
    margin: 0 -1.2rem 1.6rem; padding: .5rem 1.4rem; border-radius: 0 0 16px 16px;
}}
.st-key-topbar [data-testid="stHorizontalBlock"] {{ align-items: center; }}
.topbrand {{ display: flex; align-items: center; gap: .9rem; justify-content: flex-end; }}
.topbrand img {{ height: 52px; }}
.topbrand .nm {{ font-size: 1.5rem; font-weight: 700; color: {INK}; }}
.st-key-menu_toggle_main button {{
    background: transparent !important; color: {INK} !important; border: 0 !important;
    box-shadow: none !important; font-size: 2rem !important; padding: 0 .6rem !important;
    min-height: 3rem; }}
.st-key-menu_toggle_main button p {{ font-size: 2rem !important; color: {INK} !important; font-weight: 700; }}

/* ---------- welcome banner ---------- */
.hero {{
    background: linear-gradient(100deg, {GREEN_DARK} 0%, {GREEN_DARK} 45%, #1e8f69 45%, #1e8f69 100%);
    border-radius: 22px; padding: 2rem 2.2rem; margin-bottom: 1.6rem; color: #fff;
}}
.hero .uni {{ color: #bfeedd; font-weight: 500; letter-spacing: 3px; text-transform: uppercase; font-size: .9rem; }}
.hero h1 {{ color: #ffffff !important; font-size: 2.5rem; font-weight: 700; margin: .3rem 0 .5rem; line-height: 1.2; }}
.hero h1 span {{ color: {GOLD}; }}
.hero p {{ color: #ffffff !important; font-size: 1.25rem !important; margin: 0; }}

/* ---------- headings ---------- */
h1, h2, h3, h4 {{ color: {TITLE_BLUE} !important; font-weight: 900 !important; }}
h2, h3 {{ font-size: 1.9rem !important; margin-top: 1.2rem; }}

/* ---------- cards / steps / verdict ---------- */
.card {{ background: #ffffff; border: 1px solid #e6eaf3; border-radius: 22px;
    padding: 1.3rem 1.5rem; box-shadow: 0 3px 12px rgba(31,36,51,.07); margin-bottom: 1rem; }}
.card .lbl {{ color: {MUTED}; font-size: 1.05rem; font-weight: 500; }}
.card .big {{ font-size: 2.5rem; font-weight: 900; color: {INK}; line-height: 1.2; margin-top: .3rem; }}
.step {{ background: #ffffff; border: 1px solid #e6eaf3; border-radius: 18px; padding: 1.1rem 1.4rem;
    margin-bottom: .8rem; font-weight: 500; font-size: 1.25rem; color: {INK} !important;
    box-shadow: 0 2px 8px rgba(31,36,51,.06); display: flex; align-items: center; }}
.step b {{ background: {GREEN}; color: #fff; border-radius: 50%; width: 2.4rem; height: 2.4rem;
    display: inline-flex; align-items: center; justify-content: center; margin-right: 1rem;
    font-size: 1.2rem; font-weight: 700; flex: none; }}
.verdict {{ background: linear-gradient(100deg, {GREEN_DARK} 0%, #1e8f69 100%); color: #fff;
    border-radius: 22px; padding: 2rem; text-align: center; margin: 1.2rem 0; }}
.verdict .score {{ font-size: 4rem; font-weight: 900; color: {GOLD}; line-height: 1.1; }}
.verdict .v {{ font-size: 1.7rem; font-weight: 700; color: #ffffff; }}
.note {{ color: {MUTED} !important; font-size: 1rem !important; }}

/* ---------- chat ---------- */
div[data-testid="stChatMessage"] {{ background: #ffffff; border: 1px solid #e0e5f0;
    border-radius: 20px; box-shadow: 0 2px 8px rgba(31,36,51,.06); padding: 1rem 1.2rem; }}
div[data-testid="stChatMessage"] p {{ font-size: 1.15rem !important; color: {INK} !important; }}
div[data-testid="stChatInput"] textarea {{ font-size: 1.15rem !important; color: {INK} !important; }}

/* ---------- form fields (rounded, like the login form) ---------- */
.stTextInput label p, .stNumberInput label p, .stSelectbox label p, .stCheckbox label p {{
    font-size: 1.1rem !important; font-weight: 700 !important; color: {INK} !important; }}
.stTextInput input, .stNumberInput input {{ font-size: 1.15rem !important; color: {INK} !important;
    background: #ffffff !important; border: 1.5px solid #b9c0cf !important;
    border-radius: 16px !important; padding: .95rem 1.1rem !important; }}
.stTextInput input:focus, .stNumberInput input:focus {{ border-color: {GREEN} !important; box-shadow: 0 0 0 2px {MINT} !important; }}
div[data-baseweb="select"] > div {{ font-size: 1.1rem !important; border: 1.5px solid #b9c0cf !important;
    border-radius: 16px !important; color: {INK} !important; background: #ffffff !important; min-height: 3.2rem; }}
div[data-testid="stForm"] {{ background: #ffffff; border: 1px solid #e6eaf3; border-radius: 24px;
    padding: 1.6rem; box-shadow: 0 3px 12px rgba(31,36,51,.07); }}

/* ---------- green buttons ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    background: {BTN}; color: #ffffff !important; font-weight: 700; font-size: 1.15rem;
    border: 0; border-radius: 14px; padding: .85rem 1.8rem; min-height: 3.3rem; }}
.stButton > button p, .stDownloadButton > button p, .stFormSubmitButton > button p {{
    color: #ffffff !important; font-size: 1.15rem !important; font-weight: 700 !important; }}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
    background: {BTN_HOVER}; color: #ffffff !important; }}

/* ---------- tables / progress / expanders ---------- */
div[data-testid="stDataFrame"] {{ border: 1px solid #dfe5f1; border-radius: 16px; overflow: hidden; }}
div[data-testid="stProgress"] p {{ font-size: 1.15rem !important; font-weight: 700 !important; color: {INK} !important; }}
div[data-testid="stProgress"] div[role="progressbar"] > div {{ background-color: {GREEN} !important; }}
div[data-testid="stExpander"] {{ background: #ffffff; border: 1px solid #e0e5f0; border-radius: 16px; }}
div[data-testid="stExpander"] summary p {{ font-size: 1.1rem !important; font-weight: 700 !important; color: {INK} !important; }}
a {{ color: {GREEN} !important; }}
</style>
"""


def hero(title: str, subtitle: str):
    head, _, last = title.rpartition(" ")
    shown = f"{head} <span>{last}</span>" if head else f"<span>{title}</span>"
    st.markdown(
        f'<div class="hero"><div class="uni">{UNIVERSITY}</div>'
        f"<h1>{shown}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def card(label: str, value):
    st.markdown(
        f'<div class="card"><div class="lbl">{label}</div>'
        f'<div class="big">{value}</div></div>',
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------- pages
def reset_interview():
    for key in ("stage", "bio", "answers", "result"):
        st.session_state.pop(key, None)


def page_home():
    hero("Staff Promotion Interview Portal",
         "A structured, computer-assisted interview and assessment system "
         "for academic and non-academic staff.")

    c1, c2, c3 = st.columns(3)
    with c1:
        card("Questions", len(QUESTIONS))
    with c2:
        card("Marks per question", QUESTION_WEIGHT)
    with c3:
        card("Total marks", len(QUESTIONS) * QUESTION_WEIGHT)

    st.subheader("How it works")
    for i, text in enumerate([
        "Open <b>Interactive Chatbot</b> from the sidebar.",
        "Enter your staff biodata.",
        "Answer the five interview questions.",
        "Receive your preliminary score, verdict and PDF report.",
    ], start=1):
        st.markdown(f'<div class="step"><b>{i}</b>{text}</div>', unsafe_allow_html=True)

    st.markdown(
        '<p class="note">Verdicts are preliminary recommendations from keyword '
        "and response-length scoring. They are not official promotion "
        "decisions.</p>",
        unsafe_allow_html=True,
    )


def stage_biodata():
    st.subheader("Step 1: Staff biodata")
    with st.form("biodata"):
        name = st.text_input("Full name *")
        staff_id = st.text_input("Staff identification number *")
        department = st.text_input("Department")
        experience = st.number_input("Years of experience", 0, 50, 5)
        email = st.text_input("Email address *")
        phone = st.text_input("Phone number")
        submitted = st.form_submit_button("START INTERVIEW")

    if submitted:
        if not (name.strip() and staff_id.strip() and email.strip()):
            st.error("Full name, staff ID, and email are required.")
        elif "@" not in email:
            st.error("Enter a valid email address.")
        else:
            st.session_state.bio = {
                "name": name.strip(), "staff_id": staff_id.strip(),
                "department": department.strip(), "experience": int(experience),
                "email": email.strip(), "phone": phone.strip(),
            }
            st.session_state.answers = []
            st.session_state.stage = "interview"
            st.rerun()


def stage_interview():
    answers = st.session_state.answers
    bio = st.session_state.bio
    n = len(answers)

    st.progress(n / len(QUESTIONS), text=f"Question {min(n + 1, len(QUESTIONS))} of {len(QUESTIONS)}")

    with st.chat_message("assistant"):
        st.write(
            f"Welcome, **{bio['name']}**. I will ask you {len(QUESTIONS)} questions. "
            "Answer in full sentences and give specific examples."
        )

    for i, a in enumerate(answers):
        with st.chat_message("assistant"):
            st.write(f"**Question {i + 1}.** {QUESTIONS[i]['text']}")
        with st.chat_message("user"):
            st.write(a["answer"])
        with st.chat_message("assistant"):
            st.write(f"Score for this answer: **{a['score']} / {QUESTION_WEIGHT}**")

    if n < len(QUESTIONS):
        q = QUESTIONS[n]
        with st.chat_message("assistant"):
            st.write(f"**Question {n + 1} of {len(QUESTIONS)}.** {q['text']}")
        reply = st.chat_input("Type your answer here")
        if reply is not None:
            answers.append({
                "area": q["area"],
                "answer": reply.strip(),
                "score": score_response(reply, q["keywords"]),
            })
            st.rerun()
    else:
        total = round(sum(a["score"] for a in answers), 1)
        verdict = get_verdict(total)
        save_record(bio, answers, total, verdict)
        st.session_state.result = {"total": total, "verdict": verdict}
        st.session_state.stage = "result"
        st.rerun()


def stage_result():
    bio, answers = st.session_state.bio, st.session_state.answers
    total = st.session_state.result["total"]
    verdict = st.session_state.result["verdict"]

    st.markdown(
        f'<div class="verdict"><div class="score">{total} / 100</div>'
        f'<div class="v">{verdict}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="note">This is a preliminary system-generated result, not an '
        "official promotion decision.</p>",
        unsafe_allow_html=True,
    )

    df = pd.DataFrame(
        [{"Question": i + 1, "Area": a["area"], "Score": a["score"],
          "Out of": QUESTION_WEIGHT} for i, a in enumerate(answers)]
    )
    st.dataframe(df, hide_index=True)

    st.download_button(
        "DOWNLOAD PDF REPORT",
        data=build_pdf(bio, answers, total, verdict),
        file_name=f"promotion_report_{bio['staff_id']}.pdf",
        mime="application/pdf",
    )
    if st.button("START A NEW INTERVIEW"):
        reset_interview()
        st.rerun()


def page_chatbot():
    hero("Interactive Interview", "Answer each question as you would before a promotion panel.")
    stage = st.session_state.get("stage", "biodata")
    {"biodata": stage_biodata, "interview": stage_interview,
     "result": stage_result}[stage]()


# -------------------------------------------------------------------- admin
def admin_login() -> bool:
    if st.session_state.get("admin_ok"):
        return True
    st.subheader("Administrator login")
    with st.form("admin_login"):
        pw = st.text_input("Password", type="password")
        go = st.form_submit_button("LOGIN")
    if go:
        if pw == ADMIN_PASSWORD:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


def page_admin():
    hero("Admin Dashboard", "Review interview records, scores and verdicts.")
    if not admin_login():
        return

    if st.button("LOG OUT"):
        st.session_state.admin_ok = False
        st.rerun()

    df = load_all_records()
    if df.empty:
        st.info("No interview records yet.")
        return

    approved = df["verdict"].str.contains("Approved|Recommended").sum()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Interviews", len(df))
    with c2:
        card("Average score", round(df["total_score"].mean(), 1))
    with c3:
        card("Highest score", df["total_score"].max())
    with c4:
        card("Recommended", f"{approved} ({round(100 * approved / len(df))}%)")

    st.subheader("Verdict distribution")
    st.bar_chart(df["verdict"].value_counts())

    st.subheader("Records")
    f1, f2 = st.columns(2)
    search = f1.text_input("Search name or staff ID")
    verdict_filter = f2.selectbox("Filter by verdict", ["All"] + [v for _, v in VERDICTS])

    view = df
    if search:
        s = search.lower()
        view = view[view["full_name"].str.lower().str.contains(s)
                    | view["identifier"].str.lower().str.contains(s)]
    if verdict_filter != "All":
        view = view[view["verdict"] == verdict_filter]

    show_cols = ["id", "full_name", "identifier", "department_course",
                 "total_score", "verdict", "interview_date"]
    st.dataframe(view[show_cols], hide_index=True)
    st.download_button("EXPORT CSV", view[show_cols].to_csv(index=False).encode("utf-8"),
                       file_name="interview_records.csv", mime="text/csv")

    st.subheader("Record details")
    if view.empty:
        st.write("No matching records.")
        return
    choice = st.selectbox(
        "Select a record",
        view["id"].tolist(),
        format_func=lambda i: f"#{i} - {view.loc[view['id'] == i, 'full_name'].iloc[0]}",
    )
    row = view[view["id"] == choice].iloc[0]
    responses = json.loads(row["responses"])

    st.write(f"**Name:** {row['full_name']}  |  **Staff ID:** {row['identifier']}  |  "
             f"**Department:** {row['department_course']}")
    st.write(f"**Email:** {row['email']}  |  **Phone:** {row['phone']}  |  "
             f"**Date:** {row['interview_date']}")
    st.write(f"**Total:** {row['total_score']} / 100  |  **Verdict:** {row['verdict']}")
    for i, r in enumerate(responses, start=1):
        with st.expander(f"Q{i}. {r['area']} ({r['score']}/{QUESTION_WEIGHT})"):
            st.write(r["answer"])

    bio = {"name": row["full_name"], "staff_id": row["identifier"],
           "department": row["department_course"], "experience": row["experience_score"],
           "email": row["email"], "phone": row["phone"]}
    b1, b2 = st.columns(2)
    with b1:
        st.download_button(
            "DOWNLOAD THIS PDF REPORT",
            build_pdf(bio, responses, row["total_score"], row["verdict"]),
            file_name=f"promotion_report_{row['identifier']}.pdf",
            mime="application/pdf",
        )
    with b2:
        if st.checkbox("Confirm delete"):
            if st.button("DELETE RECORD"):
                delete_record(int(choice))
                st.rerun()


# ------------------------------------------------------------- sidebar / nav
SIDEBAR_CSS = f"""
<style>
/* our own button controls the menu, so hide Streamlit's arrows */
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {{ display: none !important; }}

section[data-testid="stSidebar"] {{ background: {GREEN}; box-shadow: 4px 0 18px rgba(0,0,0,.25); }}
section[data-testid="stSidebar"] > div {{ padding: 0 0 2rem; }}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding: 0 !important; }}
section[data-testid="stSidebar"] * {{ color: #ffffff !important; }}

.brand {{ background: {GREEN_LIGHT}; display: flex; align-items: center; gap: 1rem;
    padding: 1.1rem 1.2rem; border-bottom: 2px solid rgba(255,255,255,.18); margin-bottom: 1.4rem; }}
.brand .logo {{ width: 62px; height: 62px; border-radius: 50%; background: #ffffff; flex: none;
    display: flex; align-items: center; justify-content: center; overflow: hidden;
    border: 3px solid rgba(255,255,255,.55); }}
.brand .logo img {{ width: 46px; }}
.brand .t {{ font-size: 1.8rem; font-weight: 700; line-height: 1.1; }}
.brand .u {{ font-size: .8rem; font-weight: 500; opacity: .95; margin-top: .2rem; }}

section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: .6rem; }}
section[data-testid="stSidebar"] .stButton {{ padding: 0 1rem; }}
section[data-testid="stSidebar"] .stButton > button {{
    width: 100%; justify-content: flex-start; text-align: left; gap: 1.2rem;
    min-height: 4rem; padding: 0 1.2rem; border-radius: 14px; border: 0;
    background: transparent; font-size: 1.25rem; font-weight: 500;
    transition: background .2s ease, transform .2s ease;
}}
section[data-testid="stSidebar"] .stButton > button * {{ font-size: 1.25rem !important; font-weight: 500 !important; }}
section[data-testid="stSidebar"] .stButton > button:hover {{ background: rgba(255,255,255,.14); transform: translateX(6px); }}
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {{
    background: #26b585; border-right: 7px solid #ffffff; }}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] *,
section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] * {{ font-weight: 700 !important; }}
.st-key-menu_toggle_side .stButton > button, .st-key-menu_toggle_side button {{
    background: rgba(255,255,255,.16) !important; border: 1.5px solid rgba(255,255,255,.5) !important; }}
.navlabel {{ font-size: .9rem; font-weight: 700; letter-spacing: 4px; margin: .6rem 1.4rem .2rem; opacity: .85; }}
.sidefoot {{ margin: 2rem 1.2rem 0; padding-top: 1rem; border-top: 2px solid rgba(255,255,255,.3);
    font-size: .9rem; text-align: center; opacity: .95; }}
</style>
"""

HIDE_SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"] { display: none !important; }
</style>
"""

PAGES = [
    ("Portal Home", ":material/dashboard:"),
    ("Interactive Chatbot", ":material/chat:"),
    ("Admin Dashboard", ":material/admin_panel_settings:"),
]


def toggle_menu():
    st.session_state.sidebar_open = not st.session_state.sidebar_open
    st.rerun()


# --------------------------------------------------------------------- main
def main():
    st.set_page_config(page_title="NSUK Promotion Interview Portal", page_icon="🎓",
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS + SIDEBAR_CSS, unsafe_allow_html=True)
    init_db()

    st.session_state.setdefault("sidebar_open", True)
    st.session_state.setdefault("page", PAGES[0][0])

    if not st.session_state.sidebar_open:
        st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True)

    # header bar: menu button (hides / shows the sidebar) + portal name
    with st.container(key="topbar"):
        c_btn, c_brand = st.columns([1, 5])
        with c_btn:
            label = "✕" if st.session_state.sidebar_open else "☰"
            if st.button(label, key="menu_toggle_main"):
                toggle_menu()
        with c_brand:
            st.markdown(
                f'<div class="topbrand"><span class="nm">NSUK Portal</span>'
                f'<img src="{LOGO_IMG}" alt="NSUK"></div>',
                unsafe_allow_html=True,
            )

    with st.sidebar:
        st.markdown(
            f'<div class="brand"><div class="logo"><img src="{LOGO_IMG}" alt="NSUK"></div>'
            f'<div><div class="t">NSUK</div><div class="u">{UNIVERSITY}</div></div></div>',
            unsafe_allow_html=True,
        )
        for name, icon in PAGES:
            active = st.session_state.page == name
            if st.button(name, icon=icon, key=f"nav_{name}",
                         type="primary" if active else "secondary"):
                st.session_state.page = name
                st.rerun()

        st.markdown('<div class="sidefoot">Department of Computer Science<br>'
                    "Preliminary assessments only</div>", unsafe_allow_html=True)
        # same toggle inside the sidebar (needed on phones where the menu covers the screen)
        if st.button("Close menu", icon=":material/close:", key="menu_toggle_side"):
            toggle_menu()

    {"Portal Home": page_home, "Interactive Chatbot": page_chatbot,
     "Admin Dashboard": page_admin}[st.session_state.page]()


if __name__ == "__main__":
    main()
