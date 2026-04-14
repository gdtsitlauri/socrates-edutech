using System.Net.Http.Headers;
using System.Net.Http.Json;
using Xunit;

namespace SocratesTests;

public class StudentApiTests(TestWebApplicationFactory factory) : IClassFixture<TestWebApplicationFactory>
{
    private readonly HttpClient _client = factory.CreateClient();

    [Fact]
    public async Task StudentProgressEndpointRejectsAnonymousRequests()
    {
        var response = await _client.GetAsync("/students/1/progress");
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task StudentProgressEndpointReturnsPayload()
    {
        await AuthorizeAsync();
        var response = await _client.GetAsync("/students/1/progress");

        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();

        Assert.Contains("Ada Student", json);
        Assert.Contains("conceptMastery", json);
        Assert.Contains("upcomingReviews", json);
    }

    [Fact]
    public async Task SubmitAnswerEndpointGradesResponse()
    {
        await AuthorizeAsync();
        var response = await _client.PostAsJsonAsync("/students/1/submit_answer", new
        {
            assessmentId = 1,
            submittedAnswer = "3/4"
        });

        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();

        Assert.Contains("isCorrect", json);
        Assert.Contains("true", json, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("UpdatedConcept", json, StringComparison.OrdinalIgnoreCase);
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
