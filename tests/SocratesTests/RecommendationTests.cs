using System.Net.Http.Headers;
using System.Net.Http.Json;
using Xunit;

namespace SocratesTests;

public class RecommendationTests(TestWebApplicationFactory factory) : IClassFixture<TestWebApplicationFactory>
{
    private readonly HttpClient _client = factory.CreateClient();

    [Fact]
    public async Task LearningPathEndpointReturnsOrderedPath()
    {
        await AuthorizeAsync();
        var response = await _client.GetAsync("/students/1/learning_path");

        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();

        Assert.Contains("orderedSteps", json);
        Assert.Contains("fractions", json);
        Assert.Contains("instrumentStrength", json);
    }

    [Fact]
    public async Task CourseRecommendationsEndpointReturnsItems()
    {
        await AuthorizeAsync();
        var response = await _client.GetAsync("/courses/1/recommendations");

        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();

        Assert.Contains("recommendations", json);
        Assert.Contains("numeracy", json);
        Assert.Contains("prerequisites", json);
    }

    private async Task AuthorizeAsync()
    {
        var tokenResponse = await _client.PostAsync("/auth/token", null);
        tokenResponse.EnsureSuccessStatusCode();
        var payload = await tokenResponse.Content.ReadFromJsonAsync<TokenPayload>();
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", payload!.Token);
    }

    private sealed record TokenPayload(string Token);
}
