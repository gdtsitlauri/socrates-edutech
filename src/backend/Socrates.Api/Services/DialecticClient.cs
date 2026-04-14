using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Socrates.Api.Models;

namespace Socrates.Api.Services;

public class DialecticClient(IConfiguration configuration, ILogger<DialecticClient> logger)
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true
    };

    public async Task<LearningPathResponse> GenerateLearningPathAsync(
        StudentProgressSnapshot snapshot,
        string studentName,
        CancellationToken cancellationToken = default)
    {
        var repoRoot = FindRepoRoot()
            ?? throw new InvalidOperationException("Could not locate the SOCRATES repository root.");
        var pythonExecutable = configuration["Dialectic:PythonExecutable"] ?? "python3";
        var startInfo = new ProcessStartInfo
        {
            FileName = pythonExecutable,
            WorkingDirectory = repoRoot,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };
        startInfo.ArgumentList.Add("-m");
        startInfo.ArgumentList.Add("socrates_dialectic");
        startInfo.ArgumentList.Add("learning-path");
        startInfo.Environment["PYTHONPATH"] = BuildPythonPath(repoRoot);

        using var process = new Process { StartInfo = startInfo };
        if (!process.Start())
        {
            throw new InvalidOperationException("Failed to start the DIALECTIC Python process.");
        }

        var request = new
        {
            snapshot.StudentId,
            Name = studentName,
            snapshot.CourseId,
            snapshot.LearningStyle,
            snapshot.ConceptMastery,
            snapshot.RecentScores,
            snapshot.UpcomingReviews,
            snapshot.UpdatedAt,
            snapshot.Ability,
            snapshot.TargetConcepts
        };
        var requestJson = JsonSerializer.Serialize(request, JsonOptions);
        await process.StandardInput.WriteAsync(requestJson);
        await process.StandardInput.FlushAsync();
        process.StandardInput.Close();

        var stdoutTask = process.StandardOutput.ReadToEndAsync();
        var stderrTask = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync(cancellationToken);

        var stdout = await stdoutTask;
        var stderr = await stderrTask;
        if (process.ExitCode != 0)
        {
            logger.LogError("DIALECTIC CLI failed: {Error}", stderr);
            throw new InvalidOperationException($"DIALECTIC CLI failed: {stderr}");
        }

        var response = JsonSerializer.Deserialize<LearningPathResponse>(stdout, JsonOptions);
        return response ?? throw new InvalidOperationException("DIALECTIC CLI returned an empty response.");
    }

    private static string BuildPythonPath(string repoRoot)
    {
        var srcPath = Path.Combine(repoRoot, "src");
        var paths = new List<string>();
        if (Directory.Exists(srcPath))
        {
            paths.Add(srcPath);
        }

        var existing = Environment.GetEnvironmentVariable("PYTHONPATH");
        if (!string.IsNullOrWhiteSpace(existing))
        {
            paths.Add(existing);
        }

        return string.Join(Path.PathSeparator, paths);
    }

    private static string? FindRepoRoot()
    {
        foreach (var candidate in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
        {
            var directory = new DirectoryInfo(candidate);
            while (directory is not null)
            {
                if (File.Exists(Path.Combine(directory.FullName, "pyproject.toml")))
                {
                    return directory.FullName;
                }

                directory = directory.Parent;
            }
        }

        return null;
    }
}
