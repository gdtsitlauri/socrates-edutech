using System.Text.Json;
using Socrates.Api.Models;

namespace Socrates.Api.Data;

public static class SeedData
{
    public static void Initialize(SocratesDbContext db)
    {
        if (db.Students.Any())
        {
            return;
        }

        var algebraCourse = new Course
        {
            Id = 1,
            Title = "Adaptive Algebra",
            ModulesJson = JsonSerializer.Serialize(new[]
            {
                "numeracy",
                "fractions",
                "equations",
                "functions",
                "systems",
                "modeling"
            }),
            PrerequisitesJson = JsonSerializer.Serialize(Array.Empty<string>())
        };

        var numericalCourse = new Course
        {
            Id = 2,
            Title = "Numerical Methods",
            ModulesJson = JsonSerializer.Serialize(new[]
            {
                "matrix_ops",
                "ode_solvers",
                "eigenvalues"
            }),
            PrerequisitesJson = JsonSerializer.Serialize(new[] { "algebra" })
        };

        var student = new Student
        {
            Id = 1,
            Name = "Ada Student",
            LearningStyle = "causal-visual"
        };

        db.Courses.AddRange(algebraCourse, numericalCourse);
        db.Students.Add(student);
        db.StudentCourses.AddRange(
            new StudentCourse { StudentId = 1, CourseId = 1, Progress = 0.46 },
            new StudentCourse { StudentId = 1, CourseId = 2, Progress = 0.18 });

        db.Assessments.AddRange(
            new Assessment
            {
                Id = 1,
                CourseId = 1,
                ConceptId = "fractions",
                Difficulty = 2,
                QuestionText = "Compute 1/2 + 1/4.",
                ExpectedAnswer = "3/4"
            },
            new Assessment
            {
                Id = 2,
                CourseId = 1,
                ConceptId = "equations",
                Difficulty = 3,
                QuestionText = "Solve 2x + 3 = 11.",
                ExpectedAnswer = "4"
            },
            new Assessment
            {
                Id = 3,
                CourseId = 1,
                ConceptId = "functions",
                Difficulty = 4,
                QuestionText = "Evaluate f(x)=2x+1 at x=5.",
                ExpectedAnswer = "11"
            });

        db.AssessmentResponses.AddRange(
            new AssessmentResponse
            {
                StudentId = 1,
                AssessmentId = 1,
                SubmittedAnswer = "1",
                IsCorrect = false,
                SubmittedAtUtc = DateTime.UtcNow.AddDays(-3)
            },
            new AssessmentResponse
            {
                StudentId = 1,
                AssessmentId = 2,
                SubmittedAnswer = "4",
                IsCorrect = true,
                SubmittedAtUtc = DateTime.UtcNow.AddDays(-2)
            });

        db.SaveChanges();
    }
}
