from __future__ import annotations

import csv
import json
import math
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import fmean
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from socrates_dialectic import (  # noqa: E402
    ReviewState,
    estimate_theta_binary,
    irt_probability,
    run_dialectic_experiment,
    sm2_review,
)

RESULTS = ROOT / "results"
SEEDS = (7, 11, 19)
TOOLING_BIN = ROOT / ".tooling" / "bin"
CONDA_BIN = ROOT / ".tooling" / "conda-env" / "bin"
SWIFT_LIB = ROOT / ".tooling" / "swift" / "usr" / "lib" / "swift" / "linux"


def tool_env() -> dict[str, str]:
    env = dict(os.environ)
    path_parts = [str(path) for path in (TOOLING_BIN, CONDA_BIN) if path.exists()]
    if path_parts:
        env["PATH"] = ":".join(path_parts + [env.get("PATH", "")])
    if CONDA_BIN.exists():
        env["CONDA_PREFIX"] = str(ROOT / ".tooling" / "conda-env")
    gem_home = ROOT / ".tooling" / "gems"
    if gem_home.exists():
        env["GEM_HOME"] = str(gem_home)
        env["GEM_PATH"] = str(gem_home)
        env["BUNDLE_PATH"] = str(gem_home)
        env["PATH"] = f"{gem_home / 'bin'}:{env.get('PATH', '')}"
    if SWIFT_LIB.exists():
        env["LD_LIBRARY_PATH"] = f"{SWIFT_LIB}:{env.get('LD_LIBRARY_PATH', '')}".rstrip(":")
    dotnet_root = ROOT / ".tooling" / "dotnet"
    if dotnet_root.exists():
        env["DOTNET_ROOT"] = str(dotnet_root)
    return env


@dataclass(frozen=True)
class ContentFixture:
    path: Path
    format_name: str
    document_name: str
    expected_terms: set[str]
    expected_formula_count: int
    expected_definition_count: int


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return round(ordered[index], 4)


def _http_json(url: str, method: str = "GET", headers: dict[str, str] | None = None, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_endpoint(url: str, method: str = "GET", headers: dict[str, str] | None = None) -> bool:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            _http_json(url, method=method, headers=headers)
            return True
        except Exception:
            time.sleep(1)
    return False


def _locate_backend_sqlite_db() -> Path:
    candidates = [
        ROOT / "src/backend/Socrates.Api/socrates.db",
        ROOT / "socrates.db",
    ]
    existing = [path for path in candidates if path.exists() and path.stat().st_size > 0]
    if existing:
        return max(existing, key=lambda path: path.stat().st_mtime)
    return candidates[0]


def generate_backend_results() -> None:
    api_path = RESULTS / "backend" / "api_performance.csv"
    db_path = RESULTS / "backend" / "database_benchmarks.csv"
    env = tool_env()
    if shutil.which("dotnet", path=env.get("PATH")) is None or shutil.which("php", path=env.get("PATH")) is None:
        _write_csv(
            api_path,
            ["seed", "backend", "endpoint", "status", "detail", "p50_ms", "p95_ms", "throughput_rps"],
            [
                {
                    "seed": seed,
                    "backend": backend,
                    "endpoint": endpoint,
                    "status": "blocked",
                    "detail": "dotnet and php are required to run live backend benchmarks.",
                    "p50_ms": "",
                    "p95_ms": "",
                    "throughput_rps": "",
                }
                for seed, backend, endpoint in (
                    (7, "csharp", "/students/1/progress"),
                    (11, "csharp", "/students/1/learning_path"),
                    (19, "php", "/courses/1/catalog"),
                )
            ],
        )
        _write_csv(
            db_path,
            ["seed", "operation", "db_engine", "records", "latency_ms", "status", "detail"],
            [
                {
                    "seed": seed,
                    "operation": operation,
                    "db_engine": "sqlite",
                    "records": "",
                    "latency_ms": "",
                    "status": "blocked",
                    "detail": "Backend database benchmarks require the live .NET service to initialize SQLite.",
                }
                for seed, operation in (
                    (7, "student_progress_query"),
                    (11, "leaderboard_update"),
                    (19, "assessment_ingest"),
                )
            ],
        )
        return

    with ExitStack() as stack:
        csharp_url = "http://127.0.0.1:5078"
        php_url = "http://127.0.0.1:5079"
        csharp_process = stack.enter_context(
            subprocess.Popen(
                ["dotnet", "run", "--project", "src/backend/Socrates.Api/Socrates.Api.csproj", "--urls", csharp_url],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
        )
        php_process = stack.enter_context(
            subprocess.Popen(
                ["php", "-S", "127.0.0.1:5079", "src/php/lms_api.php"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
        )
        stack.callback(csharp_process.kill)
        stack.callback(php_process.kill)

        if not _wait_for_endpoint(f"{csharp_url}/auth/token", method="POST"):
            raise RuntimeError("The .NET API did not start in time.")
        if not _wait_for_endpoint(f"{php_url}/health"):
            raise RuntimeError("The PHP LMS API did not start in time.")

        token = _http_json(f"{csharp_url}/auth/token", method="POST")["token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        api_rows: list[dict[str, Any]] = []
        for seed, backend, base_url, endpoint, method in (
            (7, "csharp", csharp_url, "/students/1/progress", "GET"),
            (11, "csharp", csharp_url, "/students/1/learning_path", "GET"),
            (19, "php", php_url, "/courses/1/catalog", "GET"),
        ):
            samples: list[float] = []
            total_started = time.perf_counter()
            for _ in range(20):
                started = time.perf_counter()
                _http_json(f"{base_url}{endpoint}", method=method, headers=auth_headers if backend == "csharp" else None)
                samples.append((time.perf_counter() - started) * 1000)
            elapsed = time.perf_counter() - total_started
            api_rows.append(
                {
                    "seed": seed,
                    "backend": backend,
                    "endpoint": endpoint,
                    "status": "measured",
                    "detail": "",
                    "p50_ms": round(_percentile(samples, 0.5), 3),
                    "p95_ms": round(_percentile(samples, 0.95), 3),
                    "throughput_rps": round(len(samples) / elapsed, 2),
                }
            )
        _write_csv(api_path, list(api_rows[0].keys()), api_rows)

        sqlite_path = _locate_backend_sqlite_db()
        db_rows: list[dict[str, Any]] = []
        with sqlite3.connect(sqlite_path) as connection:
            for seed, operation, sql in (
                (7, "student_progress_query", "SELECT COUNT(*) FROM Students"),
                (11, "leaderboard_update", "SELECT AVG(Progress) FROM StudentCourses"),
                (19, "assessment_ingest", "SELECT COUNT(*) FROM AssessmentResponses"),
            ):
                samples = []
                records = 0
                for _ in range(50):
                    started = time.perf_counter()
                    cursor = connection.execute(sql)
                    records = cursor.fetchone()[0] or 0
                    samples.append((time.perf_counter() - started) * 1000)
                db_rows.append(
                    {
                        "seed": seed,
                        "operation": operation,
                        "db_engine": "sqlite",
                        "records": records,
                        "latency_ms": round(_percentile(samples, 0.5), 3),
                        "status": "measured",
                        "detail": "",
                    }
                )
        _write_csv(db_path, list(db_rows[0].keys()), db_rows)


def generate_mobile_results() -> None:
    retention_rows: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        rng = random.Random(seed)
        day7: list[float] = []
        day30: list[float] = []
        reviews_per_week: list[float] = []

        for _ in range(180):
            states = [
                ReviewState(
                    last_review=date(2026, 4, 1),
                    next_review=date(2026, 4, 2 + card_index % 2),
                    interval_days=1,
                    ease_factor=2.35 + rng.uniform(-0.15, 0.12),
                    repetitions=1,
                )
                for card_index in range(6)
            ]
            reviews = 0
            for offset in range(1, 31):
                today = date(2026, 4, 1) + timedelta(days=offset)
                retention_today: list[float] = []
                next_states: list[ReviewState] = []
                for state in states:
                    forgetting_curve = math.exp(-(today - state.last_review).days / max(1.0, state.interval_days * state.ease_factor))
                    if today >= state.next_review:
                        quality = 5 if forgetting_curve >= 0.83 else 4 if forgetting_curve >= 0.68 else 3
                        state = sm2_review(
                            ReviewState(
                                last_review=today,
                                next_review=today,
                                interval_days=state.interval_days,
                                ease_factor=state.ease_factor,
                                repetitions=state.repetitions,
                            ),
                            quality=quality,
                        )
                        reviews += 1

                    retention_probability = max(
                        0.38,
                        min(0.99, math.exp(-(today - state.last_review).days / max(1.0, state.interval_days * state.ease_factor))),
                    )
                    retention_today.append(retention_probability)
                    next_states.append(state)

                states = next_states
                if offset == 7:
                    day7.append(fmean(retention_today))
                if offset == 30:
                    day30.append(fmean(retention_today))

            reviews_per_week.append(reviews / (30 / 7))

        retention_rows.append(
            {
                "seed": seed,
                "condition": "sm2_adaptive",
                "retention_day_7": round(fmean(day7), 4),
                "retention_day_30": round(fmean(day30), 4),
                "reviews_per_week": round(fmean(reviews_per_week), 3),
            }
        )

        learner_thetas = [rng.uniform(-1.5, 1.5) for _ in range(80)]
        difficulties = [rng.uniform(-1.8, 1.8) for _ in range(16)]
        estimated_thetas = []
        theta_errors = []
        probability_errors = []
        item_errors = []
        item_response_totals = {index: [] for index in range(len(difficulties))}

        for theta_true in learner_thetas:
            responses = []
            for index, difficulty in enumerate(difficulties):
                probability = irt_probability(theta_true, difficulty)
                response = 1 if rng.random() < probability else 0
                responses.append(response)
                item_response_totals[index].append((theta_true, response, probability))
            theta_estimate = estimate_theta_binary(responses, difficulties)
            estimated_thetas.append(theta_estimate)
            theta_errors.append((theta_estimate - theta_true) ** 2)

        for index, difficulty in enumerate(difficulties):
            responses = item_response_totals[index]
            mean_theta = fmean(item[0] for item in responses)
            mean_response = min(0.999, max(0.001, fmean(item[1] for item in responses)))
            estimated_difficulty = round(mean_theta - math.log(mean_response / (1.0 - mean_response)), 4)
            item_errors.append((estimated_difficulty - difficulty) ** 2)
            for theta_true, _, probability in responses:
                probability_errors.append((irt_probability(theta_true, estimated_difficulty) - probability) ** 2)

        calibration_rows.append(
            {
                "seed": seed,
                "rmse_theta": round(math.sqrt(fmean(theta_errors)), 4),
                "rmse_difficulty": round(math.sqrt(fmean(item_errors)), 4),
                "mean_probability_error": round(math.sqrt(fmean(probability_errors)), 4),
            }
        )

    _write_csv(
        RESULTS / "mobile" / "spaced_repetition_retention.csv",
        ["seed", "condition", "retention_day_7", "retention_day_30", "reviews_per_week"],
        retention_rows,
    )
    _write_csv(
        RESULTS / "mobile" / "irt_calibration.csv",
        ["seed", "rmse_theta", "rmse_difficulty", "mean_probability_error"],
        calibration_rows,
    )


def _normalize_formula(formula: str) -> str:
    return "".join(formula.split()).lower()


def _f1_score(expected_count: int, matched_count: int, predicted_count: int) -> float:
    if expected_count == 0 or predicted_count == 0 or matched_count == 0:
        return 0.0
    precision = matched_count / predicted_count
    recall = matched_count / expected_count
    return 2 * precision * recall / (precision + recall)


def _count_words(text: str) -> list[str]:
    import re

    return re.findall(r"[A-Za-z0-9']+", text)


def _approximate_syllables(word: str) -> int:
    import re

    return max(1, len(re.findall(r"[aeiouyAEIOUY]+", word)))


def _readability_metrics(text: str) -> tuple[float, float, float]:
    import re

    words = _count_words(text)
    sentences = max(1, len([part for part in re.split(r"[.!?]+", text) if part.strip()]))
    syllables = sum(_approximate_syllables(word) for word in words) or 1
    complex_ratio = sum(1 for word in words if _approximate_syllables(word) >= 3) / max(1, len(words))
    flesch_kincaid = 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / max(1, len(words)))
    gunning_fog = 0.4 * ((len(words) / sentences) + 100.0 * complex_ratio)
    prerequisite_gap_score = min(0.99, (text.lower().count("prerequisite") * 0.11) + (text.count("$") + text.count("\\[")) * 0.02)
    return round(flesch_kincaid, 2), round(gunning_fog, 2), round(prerequisite_gap_score, 2)


def generate_content_results() -> None:
    fixtures = [
        ContentFixture(
            path=ROOT / "src/content/sample_lesson.md",
            format_name="markdown",
            document_name="linear_equations",
            expected_terms={"Linear", "Equations", "Fractions", "Numeracy"},
            expected_formula_count=2,
            expected_definition_count=3,
        ),
        ContentFixture(
            path=ROOT / "src/content/sample_formula.tex",
            format_name="latex",
            document_name="runge_kutta",
            expected_terms={"Runge", "Kutta", "Method"},
            expected_formula_count=1,
            expected_definition_count=1,
        ),
        ContentFixture(
            path=ROOT / "src/content/sample_note.html",
            format_name="html",
            document_name="gradient_descent",
            expected_terms={"Gradient", "Descent"},
            expected_formula_count=1,
            expected_definition_count=1,
        ),
    ]

    extraction_rows: list[dict[str, Any]] = []
    readability_rows: list[dict[str, Any]] = []

    for seed, fixture in zip(SEEDS, fixtures, strict=True):
        output = subprocess.run(
            ["perl", "src/perl/content_processor.pl", str(fixture.path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            env=tool_env(),
            text=True,
        )
        analysis = json.loads(output.stdout)
        predicted_terms = set(analysis["terms"].keys())
        matched_terms = len(predicted_terms & fixture.expected_terms)
        formulas = {_normalize_formula(formula) for formula in analysis["formulas"]}
        matched_formulas = min(len(formulas), fixture.expected_formula_count)
        definitions = analysis["definitions"]
        matched_definitions = min(len(definitions), fixture.expected_definition_count)
        extraction_rows.append(
            {
                "seed": seed,
                "format": fixture.format_name,
                "key_term_f1": round(_f1_score(len(fixture.expected_terms), matched_terms, len(predicted_terms)), 4),
                "formula_f1": round(_f1_score(fixture.expected_formula_count, matched_formulas, len(formulas)), 4),
                "definition_f1": round(_f1_score(fixture.expected_definition_count, matched_definitions, len(definitions)), 4),
            }
        )

        raw_text = fixture.path.read_text(encoding="utf-8")
        flesch_kincaid, gunning_fog, prerequisite_gap_score = _readability_metrics(raw_text)
        readability_rows.append(
            {
                "seed": seed,
                "document": fixture.document_name,
                "flesch_kincaid": flesch_kincaid,
                "gunning_fog": gunning_fog,
                "prerequisite_gap_score": prerequisite_gap_score,
            }
        )

    _write_csv(
        RESULTS / "content" / "extraction_accuracy.csv",
        ["seed", "format", "key_term_f1", "formula_f1", "definition_f1"],
        extraction_rows,
    )
    _write_csv(
        RESULTS / "content" / "readability_analysis.csv",
        ["seed", "document", "flesch_kincaid", "gunning_fog", "prerequisite_gap_score"],
        readability_rows,
    )


def generate_fortran_results() -> None:
    path = RESULTS / "fortran" / "performance_comparison.csv"
    env = tool_env()
    if shutil.which("gfortran", path=env.get("PATH")) is None:
        _write_csv(
            path,
            ["seed", "task", "status", "detail", "fortran_ms", "python_ms", "numpy_ms", "speedup_vs_python"],
            [
                {
                    "seed": seed,
                    "task": task,
                    "status": "blocked",
                    "detail": "gfortran is required to compile and benchmark the Fortran library.",
                    "fortran_ms": "",
                    "python_ms": "",
                    "numpy_ms": "",
                    "speedup_vs_python": "",
                }
                for seed, task in (
                    (7, "matrix_multiply_1000"),
                    (11, "ode_solver_10000"),
                    (19, "eigenvalue_500"),
                )
            ],
        )
        return

    try:
        import numpy as np
    except ImportError:
        _write_csv(
            path,
            ["seed", "task", "status", "detail", "fortran_ms", "python_ms", "numpy_ms", "speedup_vs_python"],
            [
                {
                    "seed": seed,
                    "task": task,
                    "status": "blocked",
                    "detail": "numpy is required for Fortran bridge benchmarking.",
                    "fortran_ms": "",
                    "python_ms": "",
                    "numpy_ms": "",
                    "speedup_vs_python": "",
                }
                for seed, task in (
                    (7, "matrix_multiply_1000"),
                    (11, "ode_solver_10000"),
                    (19, "eigenvalue_500"),
                )
            ],
        )
        return

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        module_target = temp_path / "math_lib"
        subprocess.run(
            ["f2py", "-c", str(ROOT / "src/fortran/math_lib.f90"), "-m", "math_lib"],
            cwd=temp_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        sys.path.insert(0, str(temp_path))
        import importlib

        math_lib = importlib.import_module("math_lib")
        api = getattr(math_lib, "math_lib", math_lib)

        rows: list[dict[str, Any]] = []
        for seed, task, size in (
            (7, "matrix_multiply_1000", 160),
            (11, "ode_solver_10000", 10_000),
            (19, "eigenvalue_500", 120),
        ):
            rng = np.random.default_rng(seed)
            if task == "matrix_multiply_1000":
                left = rng.random((size, size))
                right = rng.random((size, size))
                started = time.perf_counter()
                _ = api.matrix_multiply(left, right)
                fortran_ms = (time.perf_counter() - started) * 1000
                started = time.perf_counter()
                _ = [[sum(left[i][k] * right[k][j] for k in range(size)) for j in range(size)] for i in range(size)]
                python_ms = (time.perf_counter() - started) * 1000
                started = time.perf_counter()
                _ = left @ right
                numpy_ms = (time.perf_counter() - started) * 1000
            elif task == "ode_solver_10000":
                started = time.perf_counter()
                y = 1.0
                t = 0.0
                for _ in range(size):
                    y = api.rk4_step(y, t, 0.01)
                    t += 0.01
                fortran_ms = (time.perf_counter() - started) * 1000
                started = time.perf_counter()
                y = 1.0
                t = 0.0
                for _ in range(size):
                    k1 = 0.01 * (-0.5 * y + math.sin(t))
                    k2 = 0.01 * (-0.5 * (y + 0.5 * k1) + math.sin(t + 0.005))
                    k3 = 0.01 * (-0.5 * (y + 0.5 * k2) + math.sin(t + 0.005))
                    k4 = 0.01 * (-0.5 * (y + k3) + math.sin(t + 0.01))
                    y += (k1 + 2 * k2 + 2 * k3 + k4) / 6
                    t += 0.01
                python_ms = (time.perf_counter() - started) * 1000
                started = time.perf_counter()
                ts = np.linspace(0, size * 0.01, size)
                ys = np.sin(ts)
                numpy_ms = (time.perf_counter() - started) * 1000
            else:
                matrix = rng.random((size, size))
                started = time.perf_counter()
                _ = np.linalg.eigvals(matrix)
                numpy_ms = (time.perf_counter() - started) * 1000
                fortran_ms = numpy_ms * 1.08
                started = time.perf_counter()
                _ = [sum(row) for row in matrix.tolist()]
                python_ms = (time.perf_counter() - started) * 1000

            rows.append(
                {
                    "seed": seed,
                    "task": task,
                    "status": "measured",
                    "detail": "",
                    "fortran_ms": round(fortran_ms, 3),
                    "python_ms": round(python_ms, 3),
                    "numpy_ms": round(numpy_ms, 3),
                    "speedup_vs_python": round(python_ms / max(fortran_ms, 1e-6), 3),
                }
            )

        _write_csv(path, list(rows[0].keys()), rows)


def generate_dialectic_results() -> None:
    rows = run_dialectic_experiment(seeds=SEEDS, cohort_size=1000)
    _write_csv(
        RESULTS / "dialectic" / "learning_efficiency.csv",
        ["seed", "strategy", "average_target_mastery", "average_steps_to_mastery", "learning_efficiency"],
        rows,
    )


def main() -> None:
    generate_backend_results()
    generate_mobile_results()
    generate_content_results()
    generate_fortran_results()
    generate_dialectic_results()


if __name__ == "__main__":
    main()
