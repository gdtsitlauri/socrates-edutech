namespace Socrates.Api.Models;

public class Student
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string LearningStyle { get; set; } = "adaptive";
    public ICollection<StudentCourse> StudentCourses { get; set; } = new List<StudentCourse>();
    public ICollection<AssessmentResponse> AssessmentResponses { get; set; } = new List<AssessmentResponse>();
}

public class Course
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string ModulesJson { get; set; } = "[]";
    public string PrerequisitesJson { get; set; } = "[]";
    public ICollection<StudentCourse> StudentCourses { get; set; } = new List<StudentCourse>();
    public ICollection<Assessment> Assessments { get; set; } = new List<Assessment>();
}

public class StudentCourse
{
    public int StudentId { get; set; }
    public Student Student { get; set; } = null!;
    public int CourseId { get; set; }
    public Course Course { get; set; } = null!;
    public double Progress { get; set; }
}

public class Assessment
{
    public int Id { get; set; }
    public int CourseId { get; set; }
    public Course Course { get; set; } = null!;
    public string ConceptId { get; set; } = string.Empty;
    public string QuestionText { get; set; } = string.Empty;
    public string ExpectedAnswer { get; set; } = string.Empty;
    public int Difficulty { get; set; }
}

public class AssessmentResponse
{
    public int Id { get; set; }
    public int StudentId { get; set; }
    public Student Student { get; set; } = null!;
    public int AssessmentId { get; set; }
    public Assessment Assessment { get; set; } = null!;
    public string SubmittedAnswer { get; set; } = string.Empty;
    public bool IsCorrect { get; set; }
    public DateTime SubmittedAtUtc { get; set; }
}

public record AnswerSubmission(int AssessmentId, string SubmittedAnswer);

public record UpcomingReview(string ConceptId, DateOnly DueOn, int IntervalDays, double EaseFactor);

public record StudentProgressSnapshot(
    int StudentId,
    int CourseId,
    string LearningStyle,
    Dictionary<string, double> ConceptMastery,
    List<double> RecentScores,
    List<UpcomingReview> UpcomingReviews,
    DateTime UpdatedAt,
    double Ability = 0.0,
    List<string>? TargetConcepts = null);

public record LearningPathGap(
    string ConceptId,
    string Title,
    string Reason,
    double CausalEffect,
    double InstrumentStrength,
    double Mastery);

public record LearningPathStep(
    string ConceptId,
    string Title,
    double Priority,
    string CausalReason,
    string RecommendedDifficulty,
    double EstimatedMinutes,
    double CausalEffect,
    double InstrumentStrength,
    double Mastery);

public record LearningPathResponse(
    int StudentId,
    List<string> TargetConcepts,
    List<LearningPathGap> CausalGaps,
    List<LearningPathStep> OrderedSteps,
    double EstimatedGainPerHour,
    DateTime GeneratedAt);
