using Microsoft.EntityFrameworkCore;
using Socrates.Api.Models;

namespace Socrates.Api.Data;

public class SocratesDbContext(DbContextOptions<SocratesDbContext> options) : DbContext(options)
{
    public DbSet<Student> Students => Set<Student>();
    public DbSet<Course> Courses => Set<Course>();
    public DbSet<StudentCourse> StudentCourses => Set<StudentCourse>();
    public DbSet<Assessment> Assessments => Set<Assessment>();
    public DbSet<AssessmentResponse> AssessmentResponses => Set<AssessmentResponse>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<StudentCourse>()
            .HasKey(studentCourse => new { studentCourse.StudentId, studentCourse.CourseId });

        modelBuilder.Entity<StudentCourse>()
            .HasOne(studentCourse => studentCourse.Student)
            .WithMany(student => student.StudentCourses)
            .HasForeignKey(studentCourse => studentCourse.StudentId);

        modelBuilder.Entity<StudentCourse>()
            .HasOne(studentCourse => studentCourse.Course)
            .WithMany(course => course.StudentCourses)
            .HasForeignKey(studentCourse => studentCourse.CourseId);
    }
}
