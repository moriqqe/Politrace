"""
Politrace — Capstone Project 3
Flask application serving two interactive dashboards over the Capstone 2 SQLite DB.

  Dashboard 1  /analytical   (Analytical)  — sentiment & discourse deep-dive
  Dashboard 2  /strategic    (Strategic)   — Obsidian-style co-mention network

Run:
    pip install -r requirements.txt
    python app.py
    open http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify

from backend import queries as Q

app = Flask(__name__)


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analytical")
def analytical():
    return render_template("analytical.html")


@app.route("/strategic")
def strategic():
    return render_template("strategic.html")


# --------------------------------------------------------------------------- #
# Shared helper: read the global filter bar from the query string
# --------------------------------------------------------------------------- #
def _args() -> dict:
    return {
        "platform": request.args.get("platform", "all"),
        "start": request.args.get("start"),
        "end": request.args.get("end"),
        "sentiment": request.args.get("sentiment", "all"),
        "q": request.args.get("q"),
    }


# --------------------------------------------------------------------------- #
# API — shared
# --------------------------------------------------------------------------- #
@app.route("/api/filters")
def api_filters():
    return jsonify(Q.filter_options())


# --------------------------------------------------------------------------- #
# API — Dashboard 1 (Analytical)
# --------------------------------------------------------------------------- #
@app.route("/api/analytical/kpis")
def api_a_kpis():
    return jsonify(Q.kpis(_args()))


@app.route("/api/analytical/timeseries")
def api_a_timeseries():
    return jsonify(Q.timeseries(_args()))


@app.route("/api/analytical/sentiment")
def api_a_sentiment():
    return jsonify(Q.sentiment_distribution(_args()))


@app.route("/api/analytical/platform")
def api_a_platform():
    return jsonify(Q.platform_compare(_args()))


@app.route("/api/analytical/channels")
def api_a_channels():
    return jsonify(Q.top_channels(_args()))


@app.route("/api/analytical/engagement")
def api_a_engagement():
    return jsonify(Q.engagement_scatter(_args()))


@app.route("/api/analytical/wordcount")
def api_a_wordcount():
    return jsonify(Q.wordcount_histogram(_args()))


@app.route("/api/analytical/posts")
def api_a_posts():
    return jsonify(Q.posts_table(_args()))


# --------------------------------------------------------------------------- #
# API — Dashboard 2 (Strategic)
# --------------------------------------------------------------------------- #
@app.route("/api/strategic/kpis")
def api_s_kpis():
    return jsonify(Q.strategic_kpis(_args()))


@app.route("/api/strategic/network")
def api_s_network():
    min_w = int(request.args.get("min_weight", 40))
    etype = request.args.get("type", "all")
    return jsonify(Q.network(_args(), min_weight=min_w, etype=etype))


@app.route("/api/strategic/entities")
def api_s_entities():
    etype = request.args.get("type", "all")
    return jsonify(Q.top_entities(_args(), etype=etype))


@app.route("/api/strategic/entity_sentiment")
def api_s_entity_sentiment():
    return jsonify(Q.entity_sentiment(_args()))


@app.route("/api/strategic/hotspots")
def api_s_hotspots():
    return jsonify(Q.hotspot_share(_args()))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
