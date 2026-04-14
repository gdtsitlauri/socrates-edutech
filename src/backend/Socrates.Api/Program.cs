using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Socrates.Api.Data;
using Socrates.Api.Hubs;
using Socrates.Api.Models;
using Socrates.Api.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddSignalR();
builder.Services.AddAuthorization();

builder.Services.AddDbContext<SocratesDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("Socrates") ?? "Data Source=socrates.db"));

var issuer = builder.Configuration["Jwt:Issuer"] ?? "SOCRATES";
var audience = builder.Configuration["Jwt:Audience"] ?? "SOCRATES-Clients";
var signingKey = builder.Configuration["Jwt:Key"] ?? "SOCRATES development signing key 2026";
var securityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(signingKey));

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateIssuerSigningKey = true,
            ValidateLifetime = true,
            ValidIssuer = issuer,
            ValidAudience = audience,
            IssuerSigningKey = securityKey,
            ClockSkew = TimeSpan.FromMinutes(1)
        };
        options.Events = new JwtBearerEvents
        {
            OnMessageReceived = context =>
            {
                var accessToken = context.Request.Query["access_token"];
                var path = context.HttpContext.Request.Path;
                if (!string.IsNullOrWhiteSpace(accessToken) && path.StartsWithSegments("/hubs/livequiz"))
                {
                    context.Token = accessToken;
                }
                return Task.CompletedTask;
            }
        };
    });

builder.Services.AddScoped<RecommendationService>();
builder.Services.AddScoped<DialecticClient>();
builder.Services.AddSingleton(new JwtTokenService(issuer, audience, securityKey));

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseAuthentication();
app.UseAuthorization();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<SocratesDbContext>();
    db.Database.EnsureCreated();
    SeedData.Initialize(db);
}

app.MapPost("/auth/token", (JwtTokenService tokenService) =>
{
    var token = tokenService.CreateToken("researcher", ["api.read", "api.write"]);
    return Results.Ok(new { token });
});

app.MapGet("/students/{id:int}/progress", async (int id, RecommendationService service) =>
{
    var progress = await service.GetProgressAsync(id);
    return progress is null ? Results.NotFound() : Results.Ok(progress);
}).RequireAuthorization();

app.MapPost("/students/{id:int}/submit_answer", async (int id, AnswerSubmission submission, RecommendationService service) =>
{
    var result = await service.SubmitAnswerAsync(id, submission);
    return result is null ? Results.NotFound() : Results.Ok(result);
}).RequireAuthorization();

app.MapGet("/courses/{id:int}/recommendations", async (int id, RecommendationService service) =>
{
    var recommendations = await service.GetCourseRecommendationsAsync(id);
    return recommendations is null ? Results.NotFound() : Results.Ok(recommendations);
}).RequireAuthorization();

app.MapGet("/students/{id:int}/learning_path", async (int id, RecommendationService service, CancellationToken cancellationToken) =>
{
    var path = await service.GetLearningPathAsync(id, cancellationToken);
    return path is null ? Results.NotFound() : Results.Ok(path);
}).RequireAuthorization();

app.MapHub<QuizHub>("/hubs/livequiz");

app.Run();

public partial class Program;
