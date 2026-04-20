using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Socrates.Api.Data;
using Socrates.Api.Models;

namespace Socrates.Api.Services;

public class RecommendationService(
    SocratesDbContext db,
    DialecticClient dialecticClient,
    ILogger<RecommendationService> logger)
{
    private static readonly Dictionary<string, string[]> KnowledgeGraph = new()
    {
        ["numeracy"] = [],
        ["fractions"] = ["numeracy"],
        ["equations"] = ["fractions"],
        ["functions"] = ["equations"],
        ["systems"] = ["equations"],
        ["modeling"] = ["functions", "systems"]
    };

    private static readonly Dictionary<string, double> BaselineMastery = new()
    {
        ["numeracy"] = 0.62,
        ["fractions"] = 0.48,
        ["equations"] = 0.57,
        ["functions"] = 0.33,
        ["systems"] = 0.29,
        ["modeling"] = 0.18
    };

    public async Task<object?> GetProgressAsync(int studentId)
    {
        var data = await LoadStudentSnapshotAsync(studentId);
        if (data is null)
        {
            return null;
        }

        var (student, snapshot) = data.Value;
        var averageScore = snapshot.RecentScores.Count == 0 ? 0.0 : snapshot.RecentScores.Average();
        return new
        {
            student.Id,
            student.Name,
            snapshot.CourseId,
            snapshot.LearningStyle,
            snapshot.ConceptMastery,
            snapshot.RecentScores,
            snapshot.UpcomingReviews,
            snapshot.UpdatedAt,
            snapshot.TargetConcepts,
            AverageScore = Math.Round(averageScore, 2),
            Courses = student.StudentCourses.Select(item => new
            {
                item.CourseId,
                item.Course.Title,
                Progress = Math.Round(item.Progress, 3)
            })
        };
    }

    public async Task<object?> SubmitAnswerAsync(int studentId, AnswerSubmission submission)
    {
        var student = await db.Students.SingleOrDefaultAsync(item => item.Id == studentId);
        var assessment = await db.Assessments.SingleOrDefaultAsync(item => item.Id == submission.AssessmentId);

        if (student is null || assessment is null)
        {
            return null;
        }

        var normalizedExpected = assessment.ExpectedAnswer.Trim().ToLowerInvariant();
        var normalizedSubmitted = submission.SubmittedAnswer.Trim().ToLowerInvariant();
        var isCorrect = normalizedExpected == normalizedSubmitted;

        db.AssessmentResponses.Add(new AssessmentResponse
        {
            StudentId = studentId,
            AssessmentId = submission.AssessmentId,
            SubmittedAnswer = submission.SubmittedAnswer,
            IsCorrect = isCorrect,
            SubmittedAtUtc = DateTime.UtcNow
        });

        await db.SaveChangesAsync();

        return new
        {
            StudentId = studentId,
            submission.AssessmentId,
            IsCorrect = isCorrect,
            Feedback = isCorrect
                ? "Correct. DIALECTIC will advance the learner to the next causal bottleneck."
                : $"Review the prerequisite chain for {assessment.ConceptId}.",
            UpdatedConcept = assessment.ConceptId
        };
    }

    public async Task<object?> GetCourseRecommendationsAsync(int courseId)
    {
        var course = await db.Courses
            .Include(item => item.Assessments)
            .SingleOrDefaultAsync(item => item.Id == courseId);

        if (course is null)
        {
            return null;
        }

        var modules = JsonSerializer.Deserialize<List<string>>(course.ModulesJson) ?? [];
        return new
        {
            course.Id,
            course.Title,
            Recommendations = modules.Select((module, index) => new
            {
                ConceptId = module,
                Priority = Math.Round(1.0 / (index + 1), 3),
                SuggestedAssessmentDifficulty = index < 2 ? "foundational" : "core",
                Prerequisites = KnowledgeGraph.GetValueOrDefault(module, Array.Empty<string>())
            })
        };
    }

    public async Task<object?> GetLearningPathAsync(int studentId, CancellationToken cancellationToken = default)
    {
        var data = await LoadStudentSnapshotAsync(studentId);
        if (data is null)
        {
            return null;
        }

        var (student, snapshot) = data.Value;
        try
        {
            return await dialecticClient.GenerateLearningPathAsync(snapshot, student.Name, cancellationToken);
        }
        catch (Exception exception)
        {
            logger.LogWarning(exception, "Falling back to in-process learning path generation for student {StudentId}", studentId);
            return BuildFallbackLearningPath(snapshot);
        }
    }

    private async Task<(Student Student, StudentProgressSnapshot Snapshot)?> LoadStudentSnapshotAsync(int studentId)
    {
        var student = await db.Students
            .Include(item => item.StudentCourses)
            .ThenInclude(item => item.Course)
            .Include(item => item.AssessmentResponses)
            .ThenInclude(item => item.Assessment)
            .SingleOrDefaultAsync(item => item.Id == studentId);

        if (student is null)
        {
            return null;
        }

        var courseId = student.StudentCourses
            .OrderByDescending(item => item.Progress)
            .Select(item => item.CourseId)
            .FirstOrDefault();
        if (courseId == 0)
        {
            courseId = 1;
        }

        var conceptMastery = BuildConceptMastery(student.AssessmentResponses);
        var recentScores = student.AssessmentResponses
            .OrderByDescending(item => item.SubmittedAtUtc)
            .Take(5)
            .OrderBy(item => item.SubmittedAtUtc)
            .Select(item => item.IsCorrect ? 100.0 : 40.0)
            .ToList();
        var targetConcept = DetermineTargetConcept(student.AssessmentResponses, conceptMastery);
        var updatedAt = student.AssessmentResponses.Count == 0
            ? DateTime.UtcNow
            : student.AssessmentResponses.Max(item => item.SubmittedAtUtc);
        var snapshot = new StudentProgressSnapshot(
            StudentId: student.Id,
            CourseId: courseId,
            LearningStyle: student.LearningStyle,
            ConceptMastery: conceptMastery,
            RecentScores: recentScores,
            UpcomingReviews: BuildUpcomingReviews(student.AssessmentResponses, conceptMastery),
            UpdatedAt: updatedAt,
            Ability: EstimateAbility(recentScores),
            TargetConcepts: [targetConcept]);
        return (student, snapshot);
    }

    private static Dictionary<string, double> BuildConceptMastery(IEnumerable<AssessmentResponse> responses)
    {
        var mastery = KnowledgeGraph.Keys.ToDictionary(
            conceptId => conceptId,
            conceptId => BaselineMastery.GetValueOrDefault(conceptId, 0.45));

        foreach (var response in responses.OrderBy(item => item.SubmittedAtUtc))
        {
            var conceptId = response.Assessment.ConceptId;
            if (!mastery.ContainsKey(conceptId))
            {
                mastery[conceptId] = 0.45;
            }

            mastery[conceptId] = Clamp(mastery[conceptId] + (response.IsCorrect ? 0.08 : -0.14));
            foreach (var prerequisite in KnowledgeGraph.GetValueOrDefault(conceptId, Array.Empty<string>()))
            {
                mastery[prerequisite] = Clamp(mastery.GetValueOrDefault(prerequisite, 0.45) + (response.IsCorrect ? 0.03 : -0.02));
            }
        }

        return mastery;
    }

    private static List<UpcomingReview> BuildUpcomingReviews(
        IEnumerable<AssessmentResponse> responses,
        IReadOnlyDictionary<string, double> conceptMastery)
    {
        var reviews = responses
            .Where(item => !item.IsCorrect)
            .OrderByDescending(item => item.SubmittedAtUtc)
            .Take(3)
            .Select(item => new UpcomingReview(
                ConceptId: item.Assessment.ConceptId,
                DueOn: DateOnly.FromDateTime(item.SubmittedAtUtc.Date.AddDays(2)),
                IntervalDays: 2,
                EaseFactor: 2.3))
            .ToList();

        if (reviews.Count > 0)
        {
            return reviews;
        }

        var weakestConcept = conceptMastery.OrderBy(item => item.Value).First();
        return
        [
            new UpcomingReview(
                ConceptId: weakestConcept.Key,
                DueOn: DateOnly.FromDateTime(DateTime.UtcNow.Date.AddDays(2)),
                IntervalDays: 2,
                EaseFactor: 2.4)
        ];
    }

    private static string DetermineTargetConcept(
        IEnumerable<AssessmentResponse> responses,
        IReadOnlyDictionary<string, double> conceptMastery)
    {
        var responsePenalty = responses
            .GroupBy(item => item.Assessment.ConceptId)
            .ToDictionary(
                group => group.Key,
                group => group.Count(item => !item.IsCorrect) + 0.2 * group.Count(item => item.IsCorrect));

        if (responsePenalty.Count > 0)
        {
            return responsePenalty.OrderByDescending(item => item.Value).First().Key;
        }

        return conceptMastery.OrderBy(item => item.Value).First().Key;
    }

    private static LearningPathResponse BuildFallbackLearningPath(StudentProgressSnapshot snapshot)
    {
        var targetConcept = snapshot.TargetConcepts?.FirstOrDefault() ?? "modeling";
        var orderedConcepts = ExpandLearningPath(targetConcept);
        var orderedSteps = orderedConcepts.Select((conceptId, index) => new LearningPathStep(
            ConceptId: conceptId,
            Title: ToTitle(conceptId),
            Priority: Math.Round(1.0 / (index + 1), 4),
            CausalReason: conceptId == targetConcept
                ? $"Direct remediation target: {targetConcept}"
                : $"Prerequisite support for {targetConcept}",
            RecommendedDifficulty: snapshot.Ability < -0.5 ? "foundational" : snapshot.Ability > 0.75 ? "stretch" : "core",
            EstimatedMinutes: 20 + 2 * index,
            CausalEffect: 0.0,
            InstrumentStrength: 0.0,
            Mastery: snapshot.ConceptMastery.GetValueOrDefault(conceptId, 0.0)))
            .ToList();

        return new LearningPathResponse(
            StudentId: snapshot.StudentId,
            TargetConcepts: [targetConcept],
            CausalGaps: orderedSteps
                .Where(step => step.ConceptId != targetConcept)
                .Select(step => new LearningPathGap(
                    step.ConceptId,
                    step.Title,
                    step.CausalReason,
                    step.CausalEffect,
                    step.InstrumentStrength,
                    step.Mastery))
                .ToList(),
            OrderedSteps: orderedSteps,
            EstimatedGainPerHour: Math.Round(orderedSteps.Sum(item => item.Priority) / Math.Max(1, orderedSteps.Count), 4),
            GeneratedAt: DateTime.UtcNow);
    }

    private static IReadOnlyList<string> ExpandLearningPath(string targetConcept)
    {
        var ordered = new List<string>();
        AddPrerequisites(targetConcept, ordered, new HashSet<string>());
        return ordered;
    }

    private static void AddPrerequisites(string conceptId, List<string> ordered, HashSet<string> seen)
    {
        if (seen.Contains(conceptId))
        {
            return;
        }

        seen.Add(conceptId);
        if (KnowledgeGraph.TryGetValue(conceptId, out var prerequisites))
        {
            foreach (var prerequisite in prerequisites)
            {
                AddPrerequisites(prerequisite, ordered, seen);
            }
        }

        ordered.Add(conceptId);
    }

    private static double Clamp(double value, double minimum = 0.05, double maximum = 0.99)
    {
        return Math.Max(minimum, Math.Min(maximum, value));
    }

    private static double EstimateAbility(IReadOnlyCollection<double> recentScores)
    {
        if (recentScores.Count == 0)
        {
            return 0.0;
        }

        var averageScore = recentScores.Average();
        return Math.Round(Math.Clamp((averageScore - 70.0) / 15.0, -3.0, 3.0), 4);
    }

    private static string ToTitle(string conceptId)
    {
        return string.Join(' ', conceptId.Split('_', StringSplitOptions.RemoveEmptyEntries))
            .Replace("numeracy", "Numeracy")
            .Replace("fractions", "Fractions")
            .Replace("equations", "Equations")
            .Replace("functions", "Functions")
            .Replace("systems", "Systems")
            .Replace("modeling", "Mathematical Modeling");
    }
}
