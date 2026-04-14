from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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


def run_command(label: str, command: list[str], *, cwd: Path | None = None) -> bool:
    print(f"==> {label}")
    completed = subprocess.run(command, cwd=cwd or ROOT, check=False, env=tool_env())
    print()
    return completed.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SOCRATES checks across available toolchains.")
    parser.add_argument("--strict-tools", action="store_true", help="Fail when an expected toolchain is missing.")
    args = parser.parse_args(argv)

    failures = 0

    checks: list[tuple[str, list[str], Path | None, tuple[str, ...]]] = [
        ("Python tests", ["python3", "-m", "pytest"], ROOT, ("python3",)),
        ("Perl tests", ["prove", "-v", "tests/perl/content_processor.t"], ROOT, ("prove", "perl")),
        ("PHP syntax", ["php", "-l", "src/php/lms_api.php"], ROOT, ("php",)),
        ("Ruby specs", ["bundle", "exec", "rspec"], ROOT / "src/ruby", ("bundle", "ruby")),
        ("Swift tests", ["swift", "test"], ROOT / "src/swift", ("swift",)),
        (
            "Kotlin tests",
            [
                "bash",
                "-lc",
                "source ../../scripts/toolchain_env.sh && "
                "kotlinc QuizEngine.kt QuizEngineTest.kt QuizEngineTestRunner.kt "
                "-cp \"$CONDA_PREFIX/libexec/kotlin/lib/kotlin-test.jar\" "
                "-include-runtime -d ../../results/mobile/quiz-engine-check.jar && "
                "java -cp ../../results/mobile/quiz-engine-check.jar:$CONDA_PREFIX/libexec/kotlin/lib/kotlin-test.jar socrates.mobile.QuizEngineTestRunnerKt",
            ],
            ROOT / "src/kotlin",
            ("kotlinc", "java"),
        ),
        ("C# tests", ["dotnet", "test", "tests/SocratesTests/SocratesTests.csproj"], ROOT, ("dotnet",)),
        ("Fortran compile", ["gfortran", "-O2", "-c", "src/fortran/math_lib.f90", "-o", str(ROOT / "results/fortran/math_lib_check.o")], ROOT, ("gfortran",)),
    ]

    for label, command, cwd, required_tools in checks:
        env = tool_env()
        missing = [tool for tool in required_tools if shutil.which(tool, path=env.get("PATH")) is None]
        if missing:
            print(f"==> {label}\nskipped: missing {', '.join(missing)}\n")
            if args.strict_tools:
                failures += 1
            continue

        if not run_command(label, command, cwd=cwd):
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
