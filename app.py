from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, url_for

from repo_factory import NamingStrategy, RepositoryCreator


app = Flask(__name__)
app.secret_key = "repository-factory-secret-key"

creator = RepositoryCreator()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            count = int(request.form.get("count", "1"))
        except ValueError:
            flash("Count must be an integer", "error")
            return redirect(url_for("index"))

        prefix = request.form.get("prefix", "project").strip() or "project"
        naming_strategy = request.form.get("naming", NamingStrategy.SEQUENTIAL.value)
        start_index = request.form.get("start_index", "1")

        try:
            start_index_int = int(start_index)
        except ValueError:
            flash("Start index must be an integer", "error")
            return redirect(url_for("index"))

        try:
            strategy = NamingStrategy(naming_strategy)
        except ValueError:
            flash("Unsupported naming strategy", "error")
            return redirect(url_for("index"))

        try:
            specs = creator.create_repositories(
                count=count,
                naming=strategy,
                prefix=prefix,
                start_index=start_index_int,
            )
            flash(f"Created {len(specs)} repositories", "success")
            return render_template(
                "index.html",
                specs=_list_existing_specs(),
                created=[spec.name for spec in specs],
            )
        except FileExistsError as exc:
            flash(f"Repository already exists: {exc}", "error")
        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")
        return redirect(url_for("index"))

    specs = _list_existing_specs()
    return render_template("index.html", specs=specs, created=None)


def _list_existing_specs():
    existing = []
    for path in sorted(creator.root.iterdir()):
        if path.is_dir():
            existing.append(path.name)
    return existing


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
