import os
from flask import Flask, request, render_template_string

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-secret")

# ── Configuration read from environment variables ──────────────────────────
APP_NAME      = os.getenv("APP_NAME", "Even-Odd Checker")
APP_VERSION   = os.getenv("APP_VERSION", "2.0.0")
DEBUG_MODE    = os.getenv("DEBUG_MODE", "false").lower() == "true"
MAX_INPUT     = int(os.getenv("MAX_INPUT", "1000000"))
BG_COLOR      = os.getenv("BG_COLOR", "#f0f4f8")
# ── NEW: bonus values — NOT declared in docker-compose or k8s! ─────────────
EVEN_BONUS    = int(os.getenv("EVEN_BONUS", "10"))   # ← drift: missing from config
ODD_BONUS     = int(os.getenv("ODD_BONUS",  "5"))    # ← drift: missing from config
# ──────────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ app_name }}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', sans-serif;
      background: {{ bg_color }};
      display: flex; justify-content: center; align-items: flex-start;
      min-height: 100vh; padding: 60px 20px;
    }
    .card {
      background: white; border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,.08);
      padding: 40px; width: 100%; max-width: 480px;
    }
    h1 { font-size: 1.6rem; color: #1a202c; margin-bottom: 4px; }
    .version { font-size: .8rem; color: #a0aec0; margin-bottom: 28px; }
    label { display: block; font-size: .9rem; color: #4a5568; margin-bottom: 6px; }
    input[type=number] {
      width: 100%; padding: 12px 14px; font-size: 1rem;
      border: 2px solid #e2e8f0; border-radius: 8px; outline: none;
      transition: border-color .2s;
    }
    input[type=number]:focus { border-color: #667eea; }
    button {
      margin-top: 14px; width: 100%; padding: 13px;
      background: #667eea; color: white; font-size: 1rem;
      border: none; border-radius: 8px; cursor: pointer;
      transition: background .2s;
    }
    button:hover { background: #5a67d8; }
    .result {
      margin-top: 24px; padding: 18px; border-radius: 8px;
      text-align: center; font-size: 1.2rem; font-weight: 600;
    }
    .even { background: #c6f6d5; color: #22543d; }
    .odd  { background: #fefcbf; color: #744210; }
    .bonus-badge {
      display: inline-block; margin-top: 10px;
      border-radius: 20px; padding: 5px 16px;
      font-size: .85rem; font-weight: 500;
    }
    .bonus-even { background: #bee3f8; color: #2a4a6b; }
    .bonus-odd  { background: #fed7aa; color: #7b341e; }
    .debug-bar {
      margin-top: 28px; padding: 10px 14px; background: #edf2f7;
      border-radius: 6px; font-size: .75rem; color: #718096;
    }
    .hint { margin-top: 10px; font-size: .8rem; color: #a0aec0; }
  </style>
</head>
<body>
  <div class="card">
    <h1>{{ app_name }}</h1>
    <div class="version">v{{ version }}</div>

    <form method="POST">
      <label for="num">Enter a number (max {{ max_input | int }})</label>
      <input type="number" id="num" name="number"
             placeholder="e.g. 42"
             value="{{ number if number is not none else '' }}"
             min="-999999999" max="{{ max_input }}" required>
      <button type="submit">Check →</button>
    </form>

    {% if result %}
    <div class="result {{ css_class }}">
      {{ number }} is <strong>{{ result }}</strong>
      {% if css_class == 'even' %}
      <br><span class="bonus-badge bonus-even">+{{ even_bonus }} (EVEN_BONUS) → {{ adjusted }}</span>
      {% else %}
      <br><span class="bonus-badge bonus-odd">+{{ odd_bonus }} (ODD_BONUS) → {{ adjusted }}</span>
      {% endif %}
    </div>
    {% endif %}

    {% if debug %}
    <div class="debug-bar">
      🛠 Debug ON &nbsp;|&nbsp; EVEN_BONUS={{ even_bonus }}
      &nbsp;|&nbsp; ODD_BONUS={{ odd_bonus }}
      &nbsp;|&nbsp; Version={{ version }}
    </div>
    {% endif %}

    <p class="hint">
      Powered by Flask &amp; deployed via Docker Compose / Kubernetes
    </p>
  </div>
</body>
</html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    result = css_class = number = None
    adjusted = None

    if request.method == "POST":
        try:
            number = int(request.form["number"])
            if abs(number) > MAX_INPUT:
                result = f"Number exceeds MAX_INPUT ({MAX_INPUT})"
                css_class = "odd"
                adjusted = number
            elif number % 2 == 0:
                adjusted = number + EVEN_BONUS   # even: add 10
                result, css_class = "EVEN", "even"
            else:
                adjusted = number + ODD_BONUS    # odd: add 5
                result, css_class = "ODD", "odd"
        except ValueError:
            result, css_class = "Invalid input", "odd"
            adjusted = 0

    return render_template_string(
        HTML,
        app_name=APP_NAME,
        version=APP_VERSION,
        debug=DEBUG_MODE,
        max_input=MAX_INPUT,
        bg_color=BG_COLOR,
        even_bonus=EVEN_BONUS,
        odd_bonus=ODD_BONUS,
        number=number,
        result=result,
        css_class=css_class,
        adjusted=adjusted,
    )


@app.route("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION,
            "even_bonus": EVEN_BONUS, "odd_bonus": ODD_BONUS}


if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)
