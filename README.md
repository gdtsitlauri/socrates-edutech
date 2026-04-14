# SOCRATES

System for Online Collaborative Research, Adaptive Teaching, and Educational Science.

SOCRATES is a multi-language educational research framework spanning:

- `.NET 8` and `PHP` backends for the educational platform
- `Swift` and `Kotlin` mobile learning engines
- `Perl` and `Ruby` content processing and analytics
- `Fortran` numerical kernels bridged into `Python`
- `Python` orchestration for the `SOCRATES-DIALECTIC` algorithm

The central contribution is `SOCRATES-DIALECTIC`: a causal learning-path engine
that models why a learner struggles, not only what they score.

## DIALECTIC Pipeline

The runnable Python core implements:

1. Bayesian Knowledge Tracing to estimate mastery
2. Instrumented causal-gap discovery on synthetic interventions
3. Dependency-aware prerequisite ordering
4. IRT-based difficulty selection
5. SM-2 spaced repetition scheduling

The Python CLI is the shared recommendation contract for the repo. The C#
backend delegates `GET /students/{id}/learning_path` to that CLI.

## Repository Layout

- `src/socrates_dialectic/`: DIALECTIC core, CLI, simulation, and Python bridge logic
- `src/backend/`: .NET 8 API with SQLite, JWT auth, and SignalR live quiz support
- `src/php/`: LMS-compatible PHP API
- `src/ruby/`: Sinatra analytics API, content pipeline, and RSpec specs
- `src/swift/`: Swift package for spaced repetition and graph-based pathing
- `src/kotlin/`: Kotlin quiz engine and JVM test runner
- `src/perl/`: content processor and Perl tests
- `src/fortran/`: numerical methods library and `f2py` bridge target
- `schemas/`: shared JSON contracts including student progress and learning path
- `scripts/`: toolchain bootstrap, verification, CLI wrapper, and experiment runners
- `results/`: regenerated experiment outputs
- `paper/`: IEEE-style manuscript draft

## Toolchains

The repo now supports two setup modes:

```bash
bash scripts/setup_wsl_ubuntu.sh
```

for system-wide WSL2 installation, or the local user-space path used in this
workspace:

```bash
bash scripts/bootstrap_user_toolchains.sh
source scripts/toolchain_env.sh
```

The local path installs runtimes under `.tooling/` without requiring system
package changes.

## Verified Commands

The following commands were executed successfully in this workspace:

```bash
source scripts/toolchain_env.sh
python3 -m pytest
prove -v tests/perl/content_processor.t
php -l src/php/lms_api.php
cd src/ruby && bundle exec rspec
cd src/swift && swift test
cd src/kotlin && kotlinc QuizEngine.kt QuizEngineTest.kt QuizEngineTestRunner.kt -cp "$CONDA_PREFIX/libexec/kotlin/lib/kotlin-test.jar" -include-runtime -d ../../results/mobile/quiz-engine-tests.jar && java -cp ../../results/mobile/quiz-engine-tests.jar:$CONDA_PREFIX/libexec/kotlin/lib/kotlin-test.jar socrates.mobile.QuizEngineTestRunnerKt
dotnet test tests/SocratesTests/SocratesTests.csproj
gfortran -O2 -c src/fortran/math_lib.f90 -o results/fortran/math_lib.o
bash scripts/verify_toolchains.sh
python3 scripts/run_all_checks.py --strict-tools
python3 scripts/generate_results.py
```

## CLI Example

```bash
source scripts/toolchain_env.sh
python3 scripts/run_dialectic_cli.py learning-path --pretty <<'EOF'
{
  "student_id": 1,
  "name": "Ada Student",
  "course_id": 1,
  "learning_style": "causal-visual",
  "concept_mastery": {
    "numeracy": 0.62,
    "fractions": 0.48,
    "equations": 0.57,
    "functions": 0.33,
    "systems": 0.29,
    "modeling": 0.18
  },
  "recent_scores": [92, 81, 88],
  "target_concepts": ["modeling"]
}
EOF
```

## Results

`scripts/generate_results.py` now regenerates all CSV artifacts from runnable
code, with no remaining `blocked` rows in this workspace.

Current regenerated highlights:

- Backend API benchmarks are measured in `results/backend/api_performance.csv`
- SQLite benchmark rows are measured in `results/backend/database_benchmarks.csv`
- Mobile retention and IRT calibration are measured in `results/mobile/`
- Content extraction and readability are measured in `results/content/`
- Fortran bridge benchmarks are measured in `results/fortran/performance_comparison.csv`
- DIALECTIC efficiency benchmarks are measured in `results/dialectic/learning_efficiency.csv`

## Current State

- Verified here: Python, Perl, PHP, Ruby, Swift, Kotlin, .NET, SQLite, `gfortran`, `f2py`, the DIALECTIC CLI, the repo-wide strict check runner, and full result regeneration.
- User-space toolchains were installed under `.tooling/` for this environment.
